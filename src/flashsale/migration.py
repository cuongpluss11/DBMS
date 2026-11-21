from threading import Event
import time
from typing import Any

from flashsale.adapters.base import Adapter, DBError
from flashsale.config import Dataset, Settings


def discount_rate(price: int) -> int:
    """Mục 2.4 (trang 20): r = 10 nếu i_price >= 5000, r = 5 nếu 2500 <= i_price < 5000, r = 0 nếu thấp hơn."""
    return 10 if price >= 5000 else (5 if price >= 2500 else 0)


def compute_discount(quantity: int, price: int) -> int:
    """ol_discount = floor(ol_quantity * i_price * r / 100), đơn vị cent, xác định và idempotent."""
    return (quantity * price * discount_rate(price)) // 100


SQL_DISCOUNT_EXPR = (
    "(ol.ol_quantity * i.i_price * "
    "(CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END)) DIV 100"
)


def load_item_prices(db: Adapter) -> dict[int, int]:
    """Nạp bảng giá item (i_id -> i_price) vào bộ nhớ (~100.000 dòng ở W=10) để tính ol_discount không cần đọc lặp lại."""
    if hasattr(db, "tables"):
        return {row["i_id"]: row["i_price"] for row in db.tables.get("item", ())}
    return {row["i_id"]: row["i_price"] for row in db.rows("item", ("i_id", "i_price"))}


def _sql_migration_columns(db: Any) -> set[str]:
    rows = db.query("SHOW COLUMNS FROM order_line")
    return {row.get("Field") or row.get("field") for row in rows}


def prepare_migration(db: Adapter, cfg: Dataset) -> dict[str, Any]:
    """Chuẩn bị lược đồ đích order_line (ol_discount, ol_mig_state) trước warmup, ngoài thời gian đo migration (trang 21)."""
    if hasattr(db, "query"):
        cols = _sql_migration_columns(db)
        if "ol_discount" not in cols:
            db.query("ALTER TABLE order_line ADD COLUMN ol_discount BIGINT NULL")
        if "ol_mig_state" not in cols:
            db.query("ALTER TABLE order_line ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED'")
        reset_migration(db, cfg)
        unmigrated = db.query(
            "SELECT COUNT(*) AS cnt FROM order_line WHERE ol_o_id <= %s AND ol_mig_state = 'UNMIGRATED'",
            (cfg.initial_orders,),
        )[0]["cnt"]
        return {"unmigrated_initial_rows": int(unmigrated)}
    if hasattr(db, "db"):
        reset_migration(db, cfg)
        unmigrated = db.db["order_line"].count_documents(
            {"ol_o_id": {"$lte": cfg.initial_orders}, "ol_mig_state": {"$ne": "MIGRATED"}}
        )
        return {"unmigrated_initial_rows": int(unmigrated)}
    if hasattr(db, "tables"):
        for row in db.tables.get("order_line", ()):
            if row["ol_o_id"] <= cfg.initial_orders:
                row["ol_discount"] = None
                row["ol_mig_state"] = "UNMIGRATED"
        unmigrated = sum(
            1 for row in db.tables.get("order_line", ())
            if row["ol_o_id"] <= cfg.initial_orders and row.get("ol_mig_state") != "MIGRATED"
        )
        return {"unmigrated_initial_rows": unmigrated}
    return {"unmigrated_initial_rows": None}


def reset_migration(db: Adapter, cfg: Dataset) -> None:
    """Khôi phục các dòng order_line cũ (ol_o_id <= initial_orders) về trạng thái UNMIGRATED giữa các lượt đo."""
    if hasattr(db, "query"):
        cols = _sql_migration_columns(db)
        if "ol_mig_state" not in cols or "ol_discount" not in cols:
            return
        for w in range(1, cfg.warehouses + 1):
            for d in range(1, cfg.districts + 1):
                db.query(
                    "UPDATE order_line SET ol_discount = NULL, ol_mig_state = 'UNMIGRATED' "
                    "WHERE ol_w_id = %s AND ol_d_id = %s AND ol_o_id <= %s "
                    "AND (ol_mig_state <> 'UNMIGRATED' OR ol_discount IS NOT NULL)",
                    (w, d, cfg.initial_orders),
                )
        return
    if hasattr(db, "db"):
        db.db["order_line"].update_many(
            {"ol_o_id": {"$lte": cfg.initial_orders}, "ol_mig_state": "MIGRATED"},
            {"$unset": {"ol_discount": "", "ol_mig_state": ""}},
        )
        return
    if hasattr(db, "tables"):
        for row in db.tables.get("order_line", ()):
            if row.get("ol_o_id", 0) <= cfg.initial_orders and ("ol_mig_state" in row or "ol_discount" in row):
                row["ol_discount"] = None
                row["ol_mig_state"] = "UNMIGRATED"


def _sql_update_range(db: Any, w: int, d: int | None, low: int, high: int) -> tuple[int, int]:
    """Cập nhật có điều kiện một khoảng order_line trên MySQL/TiDB; tự retry khi gặp deadlock/timeout/write_conflict."""
    from flashsale.adapters.sql import classify
    import pymysql

    retries = 0
    while True:
        try:
            with db.connection.cursor() as cursor:
                if d is None:
                    affected = cursor.execute(
                        f"UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id "
                        f"SET ol.ol_discount = {SQL_DISCOUNT_EXPR}, ol.ol_mig_state = 'MIGRATED' "
                        f"WHERE ol.ol_w_id = %s AND ol.ol_o_id BETWEEN %s AND %s "
                        f"AND ol.ol_mig_state = 'UNMIGRATED'",
                        (w, low, high),
                    )
                else:
                    affected = cursor.execute(
                        f"UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id "
                        f"SET ol.ol_discount = {SQL_DISCOUNT_EXPR}, ol.ol_mig_state = 'MIGRATED' "
                        f"WHERE ol.ol_w_id = %s AND ol.ol_d_id = %s AND ol.ol_o_id BETWEEN %s AND %s "
                        f"AND ol.ol_mig_state = 'UNMIGRATED'",
                        (w, d, low, high),
                    )
            return int(affected), retries
        except pymysql.MySQLError as exc:
            err = classify(exc)
            if not err.retryable or retries >= 8:
                raise err from exc
            retries += 1
            time.sleep(0.01 * min(retries, 5))


def _mongo_update_range(db: Any, w: int, d: int, low: int, high: int,
                        item_prices: dict[int, int]) -> tuple[int, int, int]:
    """Cập nhật có điều kiện theo lô trên MongoDB bằng UpdateMany gom theo mức ol_discount (mỗi document nguyên tử)."""
    from pymongo import UpdateMany
    from pymongo.errors import PyMongoError
    from flashsale.adapters.mongo import classify

    retries = 0
    while True:
        try:
            cursor = db.db["order_line"].find(
                {"ol_w_id": w, "ol_d_id": d, "ol_o_id": {"$gte": low, "$lte": high},
                 "ol_mig_state": {"$ne": "MIGRATED"}},
                {"_id": 1, "ol_i_id": 1, "ol_quantity": 1},
            )
            groups: dict[int, list] = {}
            scanned = 0
            for doc in cursor:
                scanned += 1
                disc = compute_discount(doc["ol_quantity"], item_prices[doc["ol_i_id"]])
                groups.setdefault(disc, []).append(doc["_id"])
            if not groups:
                return 0, 0, retries
            ops = [
                UpdateMany(
                    {"_id": {"$in": ids}, "ol_mig_state": {"$ne": "MIGRATED"}},
                    {"$set": {"ol_discount": disc, "ol_mig_state": "MIGRATED"}},
                )
                for disc, ids in groups.items()
            ]
            res = db.db["order_line"].bulk_write(ops, ordered=False)
            migrated = int(res.modified_count)
            conflicts = max(0, scanned - migrated)
            return migrated, conflicts, retries
        except PyMongoError as exc:
            err = classify(exc)
            if not err.retryable or retries >= 8:
                raise err from exc
            retries += 1
            time.sleep(0.01 * min(retries, 5))


def _mem_update_range(db: Any, w: int, d: int, low: int, high: int,
                      item_prices: dict[int, int]) -> tuple[int, int]:
    """Cập nhật có điều kiện cho MemDB (unit test)."""
    candidates = [
        (row["ol_w_id"], row["ol_d_id"], row["ol_o_id"], row["ol_number"], row["ol_i_id"], row["ol_quantity"])
        for row in db.tables.get("order_line", ())
        if (row["ol_w_id"] == w and row["ol_d_id"] == d and low <= row["ol_o_id"] <= high
            and row.get("ol_mig_state") != "MIGRATED")
    ]
    migrated = 0
    conflicts = 0
    for rw, rd, ro, rn, item_id, qty in candidates:
        disc = compute_discount(qty, item_prices[item_id])
        changed = db.change(
            "order_line",
            {"ol_w_id": rw, "ol_d_id": rd, "ol_o_id": ro, "ol_number": rn, "ol_mig_state": "UNMIGRATED"},
            set_values={"ol_discount": disc, "ol_mig_state": "MIGRATED"},
        )
        if changed == 1:
            migrated += 1
        else:
            conflicts += 1
    return migrated, conflicts


def migrate_background(db: Adapter, cfg: Settings, item_prices: dict[int, int] | None = None, *,
                       measure_start: float | None = None, deadline: float | None = None,
                       stop: Event | None = None, migrating_flag: list[bool] | None = None) -> dict[str, Any]:
    """Thực thi chuyển dữ liệu cũ cho P1 (eager), P2 (batch) hoặc luồng nền của P3 (lazy)."""
    strategy = cfg.migration_strategy
    if strategy == "none":
        return {}
    ds = cfg.dataset
    if item_prices is None and not hasattr(db, "query"):
        item_prices = load_item_prices(db)
    if measure_start is not None and cfg.migration_delay_seconds > 0:
        wait_until = measure_start + cfg.migration_delay_seconds
        while time.monotonic() < wait_until:
            if stop is not None and stop.is_set():
                break
            time.sleep(min(0.05, max(0.0, wait_until - time.monotonic())))
    began = time.monotonic()
    if migrating_flag is not None:
        migrating_flag[0] = True
    migrated = 0
    conflicts = 0
    retries = 0
    batches = 0
    try:
        if strategy == "eager":
            # P1 (Eager): chuyển tập trung toàn bộ dữ liệu cũ, không điều tiết tốc độ (sleep = 0).
            if hasattr(db, "query") and not getattr(db, "tidb", False):
                # MySQL InnoDB: chạy câu UPDATE tập trung lớn theo từng kho; nếu kẹt khóa lặp lại thì hạ xuống theo quận.
                for w in range(1, ds.warehouses + 1):
                    try:
                        aff, ret = _sql_update_range(db, w, None, 1, ds.initial_orders)
                        migrated += aff
                        retries += ret
                        batches += 1
                    except DBError:
                        retries += 1
                        for d in range(1, ds.districts + 1):
                            aff, ret = _sql_update_range(db, w, d, 1, ds.initial_orders)
                            migrated += aff
                            retries += ret
                            batches += 1
            elif hasattr(db, "query"):
                # TiDB: chia thành các giao dịch lớn nhất được phép (~1.000 đơn = ~10.000 dòng), chạy liên tiếp không nghỉ.
                step = max(1, min(ds.initial_orders, 1000))
                for w in range(1, ds.warehouses + 1):
                    for d in range(1, ds.districts + 1):
                        for low in range(1, ds.initial_orders + 1, step):
                            high = min(low + step - 1, ds.initial_orders)
                            aff, ret = _sql_update_range(db, w, d, low, high)
                            migrated += aff
                            retries += ret
                            batches += 1
            elif hasattr(db, "db"):
                for w in range(1, ds.warehouses + 1):
                    for d in range(1, ds.districts + 1):
                        aff, conf, ret = _mongo_update_range(db, w, d, 1, ds.initial_orders, item_prices or {})
                        migrated += aff
                        conflicts += conf
                        retries += ret
                        batches += 1
            else:
                for w in range(1, ds.warehouses + 1):
                    for d in range(1, ds.districts + 1):
                        aff, conf = _mem_update_range(db, w, d, 1, ds.initial_orders, item_prices or {})
                        migrated += aff
                        conflicts += conf
                        batches += 1
        else:
            # P2 (Batch) và P3 (Lazy luồng nền): chia theo khoảng khóa chính (~10 dòng/đơn), nghỉ giữa các lô.
            orders_step = max(1, cfg.migration_batch_size // 10)
            if ds.initial_orders < orders_step:
                orders_step = max(1, ds.initial_orders // 2)
            sleep_s = cfg.migration_sleep_ms / 1000.0
            for w in range(1, ds.warehouses + 1):
                for d in range(1, ds.districts + 1):
                    for low in range(1, ds.initial_orders + 1, orders_step):
                        high = min(low + orders_step - 1, ds.initial_orders)
                        if hasattr(db, "query"):
                            aff, ret = _sql_update_range(db, w, d, low, high)
                            migrated += aff
                            retries += ret
                        elif hasattr(db, "db"):
                            aff, conf, ret = _mongo_update_range(db, w, d, low, high, item_prices or {})
                            migrated += aff
                            conflicts += conf
                            retries += ret
                        else:
                            aff, conf = _mem_update_range(db, w, d, low, high, item_prices or {})
                            migrated += aff
                            conflicts += conf
                        batches += 1
                        # Khi còn trong cửa sổ đo thì nghỉ theo cấu hình; hết cửa sổ đo thì vét nốt không nghỉ để hoàn tất 100%.
                        if sleep_s > 0 and (deadline is None or time.monotonic() < deadline):
                            time.sleep(sleep_s)
    finally:
        if migrating_flag is not None:
            migrating_flag[0] = False
    ended = time.monotonic()
    base_time = measure_start if measure_start is not None else began
    return {
        "strategy": strategy,
        "old_order_read_pct": cfg.old_order_read_pct,
        "batch_size": cfg.migration_batch_size if strategy in ("batch", "lazy") else None,
        "sleep_ms": cfg.migration_sleep_ms if strategy in ("batch", "lazy") else 0.0,
        "start_second": max(0, int(began - base_time)),
        "end_second": max(0, int(ended - base_time)),
        "duration_seconds": round(ended - began, 4),
        "completed_in_window": True if deadline is None else ended <= deadline,
        "batches": batches,
        "migrated_background": migrated,
        "background_conflicts": conflicts,
        "migration_retries": retries,
    }


def validate_migration(db: Adapter, cfg: Dataset, baseline_counts: dict[str, int] | None = None,
                       tagged_lines: int = 0) -> dict[str, Any]:
    """Kiểm tra đúng đắn của migration (trang 21–22):
    1. Không còn dòng UNMIGRATED (unmigrated_rows == 0).
    2. Mọi dòng MIGRATED có ol_discount đúng hàm biến đổi (wrong_discount_rows == 0).
    3. Không mất hoặc nhân đôi dòng order_line."""
    errors: list[dict[str, Any]] = []
    expected_old = baseline_counts["order_line"] if baseline_counts and "order_line" in baseline_counts else None
    if hasattr(db, "query"):
        cols = _sql_migration_columns(db)
        if "ol_mig_state" not in cols or "ol_discount" not in cols:
            return {
                "valid": False,
                "unmigrated_rows": None,
                "wrong_discount_rows": None,
                "old_rows_count": None,
                "expected_old_rows": expected_old,
                "errors": [{"missing_migration_columns": sorted({"ol_discount", "ol_mig_state"} - cols)}],
            }
        summary = db.query(
            f"SELECT "
            f"SUM(CASE WHEN ol.ol_o_id <= %s THEN 1 ELSE 0 END) AS old_rows, "
            f"SUM(CASE WHEN ol.ol_mig_state IS NULL OR ol.ol_mig_state <> 'MIGRATED' THEN 1 ELSE 0 END) AS unmigrated, "
            f"SUM(CASE WHEN ol.ol_mig_state = 'MIGRATED' AND (ol.ol_discount IS NULL OR i.i_price IS NULL "
            f"OR ol.ol_discount <> {SQL_DISCOUNT_EXPR}) THEN 1 ELSE 0 END) AS wrong_discount "
            f"FROM order_line ol LEFT JOIN item i ON i.i_id = ol.ol_i_id",
            (cfg.initial_orders,),
        )[0]
        old_rows = int(summary["old_rows"] or 0)
        unmigrated = int(summary["unmigrated"] or 0)
        wrong_discount = int(summary["wrong_discount"] or 0)
        if unmigrated > 0 or wrong_discount > 0:
            samples = db.query(
                f"SELECT ol.ol_w_id, ol.ol_d_id, ol.ol_o_id, ol.ol_number, ol.ol_quantity, "
                f"i.i_price, ol.ol_discount, ol.ol_mig_state, {SQL_DISCOUNT_EXPR} AS expected_discount "
                f"FROM order_line ol LEFT JOIN item i ON i.i_id = ol.ol_i_id "
                f"WHERE ol.ol_mig_state IS NULL OR ol.ol_mig_state <> 'MIGRATED' "
                f"OR ol.ol_discount IS NULL OR i.i_price IS NULL "
                f"OR ol.ol_discount <> {SQL_DISCOUNT_EXPR} LIMIT 10"
            )
            errors.extend(samples)
    else:
        prices = load_item_prices(db)
        fields = ("ol_w_id", "ol_d_id", "ol_o_id", "ol_number", "ol_i_id",
                  "ol_quantity", "ol_discount", "ol_mig_state")
        rows = db.tables.get("order_line", ()) if hasattr(db, "tables") else db.rows("order_line", fields)
        old_rows = 0
        unmigrated = 0
        wrong_discount = 0
        for row in rows:
            if row["ol_o_id"] <= cfg.initial_orders:
                old_rows += 1
            state = row.get("ol_mig_state")
            if state != "MIGRATED":
                unmigrated += 1
                if len(errors) < 10:
                    errors.append({
                        "key": (row["ol_w_id"], row["ol_d_id"], row["ol_o_id"], row["ol_number"]),
                        "ol_mig_state": state,
                    })
                continue
            price = prices.get(row["ol_i_id"])
            expected_disc = compute_discount(row["ol_quantity"], price) if price is not None else None
            if price is None or row.get("ol_discount") != expected_disc:
                wrong_discount += 1
                if len(errors) < 10:
                    errors.append({
                        "key": (row["ol_w_id"], row["ol_d_id"], row["ol_o_id"], row["ol_number"]),
                        "ol_discount": row.get("ol_discount"),
                        "expected_discount": expected_disc,
                    })
    if expected_old is not None and old_rows != expected_old:
        errors.append({"old_order_line_count": old_rows, "expected_old_rows": expected_old})
    total_actual = db.count("order_line")
    if expected_old is not None and total_actual != expected_old + tagged_lines:
        errors.append({"total_order_line_count": total_actual, "expected_total": expected_old + tagged_lines})
    return {
        "valid": unmigrated == 0 and wrong_discount == 0 and not errors,
        "unmigrated_rows": unmigrated,
        "wrong_discount_rows": wrong_discount,
        "old_rows_count": old_rows,
        "expected_old_rows": expected_old,
        "errors": errors[:10],
    }
