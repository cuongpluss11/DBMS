"""Mục 2.3 (chỉ TiDB): đặt dữ liệu chủ động. Tách Region theo ranh giới kho (SPLIT TABLE), chuyển leader (hoặc peer,
khi chỉ có một bản sao) bằng PD HTTP API, tạm dừng bộ cân bằng của PD trong lúc đo, rồi KIỂM CHỨNG vị trí bằng
SHOW TABLE ... REGIONS. Mọi bước đều đọc lại trạng thái: nếu PD không làm đúng thì ném lỗi, không chạy tiếp một
lượt với bố trí sai. Chưa kiểm chứng trên PD thật (xem docs/experiment-2.3.md): các lệnh phụ thuộc phiên bản PD.
"""
from collections.abc import Callable
import json
import os
import time
from urllib.request import Request as HttpRequest, urlopen

from flashsale.config import Settings
from flashsale.data.schema import SLOT_TABLE

# Số cột khóa chính của các bảng bắt đầu bằng mã kho; `SPLIT TABLE ... BY` cần đủ mọi cột khóa (tài liệu TiDB,
# clustered indexes), nên các cột sau kho nhận giá trị nhỏ nhất 0.
WAREHOUSE_KEYED = {"stock": 2, "district": 2, "customer": 3, "orders": 3, "new_order": 3, "order_line": 4}
# Bộ lập lịch của PD bị tạm dừng và các giới hạn đặt về 0 trong lúc đo (để vị trí không đổi giữa lượt).
SCHEDULERS = ("balance-leader-scheduler", "balance-region-scheduler", "balance-hot-region-scheduler")
LIMITS = ("leader-schedule-limit", "region-schedule-limit", "hot-region-schedule-limit", "merge-schedule-limit")
PAUSE_SECONDS = 6 * 3600


class PD:
    """PD HTTP API tối thiểu. `transport(method, path, body)` có thể thay thế khi kiểm thử."""

    def __init__(self, base: str, transport: Callable | None = None):
        self.base = base.rstrip("/")
        self.transport = transport or self._http

    def _http(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        request = HttpRequest(self.base + path, data=data, method=method,
                              headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=10) as response:
            raw = response.read()
        return json.loads(raw) if raw else None

    def stores(self) -> list[dict]:
        """Các TiKV đang Up, xếp theo id (thứ tự cố định để bố trí tái lập)."""
        entries = self.transport("GET", "/stores", None)["stores"]
        return sorted((entry["store"] for entry in entries if entry["store"]["state_name"] == "Up"),
                      key=lambda store: store["id"])

    def replicas(self) -> int:
        return int(self.transport("GET", "/config/replicate", None)["max-replicas"])

    def schedule_config(self) -> dict:
        return self.transport("GET", "/config/schedule", None)

    def set_schedule(self, values: dict) -> None:
        self.transport("POST", "/config/schedule", values)

    def pause(self, name: str, seconds: int) -> None:
        self.transport("POST", f"/schedulers/{name}", {"delay": seconds})

    def move_leader(self, region: int, from_store: int, to_store: int, replicas: int) -> None:
        # Một bản sao: không có peer khác để nhận leader, nên chuyển cả peer (đề: transfer-peer).
        if replicas > 1:
            body = {"name": "transfer-leader", "region_id": region, "to_store_id": to_store}
        else:
            body = {"name": "transfer-peer", "region_id": region, "from_store_id": from_store,
                    "to_store_id": to_store}
        self.transport("POST", "/operators", body)


def warehouse_group(warehouse: int, warehouses: int, groups: int) -> int:
    return (warehouse - 1) * groups // warehouses if groups else 0


def plan_stores(cfg: Settings, stores: list[dict]) -> dict[int, int]:
    """Kho -> store id của leader: spread = kho w về TiKV (w-1) mod n (các kho cùng nhóm bị tách ra các TiKV);
    group = cả nhóm kho cùng một TiKV (mỗi nhóm một TiKV, luân phiên nếu nhóm nhiều hơn TiKV)."""
    n, warehouses = len(stores), cfg.dataset.warehouses
    if cfg.placement == "group":
        return {w: stores[warehouse_group(w, warehouses, cfg.warehouse_groups) % n]["id"]
                for w in range(1, warehouses + 1)}
    return {w: stores[(w - 1) % n]["id"] for w in range(1, warehouses + 1)}


def split_keys(table: str, cfg: Settings) -> list[tuple]:
    """Điểm tách của một bảng theo kho (kho 2..W), mỗi điểm đủ mọi cột khóa."""
    width = WAREHOUSE_KEYED[table]
    return [(w, *([0] * (width - 1))) for w in range(2, cfg.dataset.warehouses + 1)]


def slot_keys(cfg: Settings, hot_ids: list[int], slots: int) -> list[tuple]:
    """Điểm tách của stock_slot: mỗi (kho, món nóng, slot) của các món nóng đầu bảng hạng, theo thứ tự khóa."""
    warehouses = [1] if cfg.warehouse_mode == "single-warehouse" else range(1, cfg.dataset.warehouses + 1)
    return sorted((w, item, slot) for w in warehouses for item in hot_ids[:cfg.placement_slot_items]
                  for slot in range(slots))


def regions(db, table: str) -> list[dict]:
    """SHOW TABLE ... REGIONS theo thứ tự khóa (hàng đầu là Region chứa khóa nhỏ nhất)."""
    return db.query(f"SHOW TABLE {table} REGIONS")


def split(db, table: str, keys: list[tuple]) -> None:
    values = ", ".join("(" + ", ".join(str(part) for part in key) + ")" for key in keys)
    db.query(f"SPLIT TABLE {table} BY {values}")


def settle(db, table: str, wanted: list[int], pd: PD, replicas: int, timeout: float, sleep=time.sleep,
           clock=time.monotonic) -> list[dict]:
    """Chuyển leader của Region thứ i về store wanted[i] rồi chờ tới khi SHOW TABLE REGIONS xác nhận."""
    deadline = clock() + timeout
    asked: set[int] = set()
    while True:
        rows = regions(db, table)
        if len(rows) != len(wanted):
            raise RuntimeError(f"{table}: có {len(rows)} Region, kỳ vọng {len(wanted)} sau khi tách "
                               "(bảng đã bị tách trước đó hoặc PD đã gộp/tách thêm); tạo lại dataset")
        pending = [(row, store) for row, store in zip(rows, wanted) if int(row["LEADER_STORE_ID"]) != store]
        if not pending:
            return rows
        if clock() > deadline:
            raise RuntimeError(f"{table}: {len(pending)} Region chưa về đúng TiKV sau {timeout:.0f} giây; "
                               f"ví dụ Region {pending[0][0]['REGION_ID']} đang ở store "
                               f"{pending[0][0]['LEADER_STORE_ID']}, cần {pending[0][1]}")
        for row, store in pending:
            if int(row["REGION_ID"]) not in asked:
                asked.add(int(row["REGION_ID"]))
                pd.move_leader(int(row["REGION_ID"]), int(row["LEADER_STORE_ID"]), store, replicas)
        sleep(1)


def freeze_scheduling(pd: PD) -> dict:
    """Tạm dừng bộ cân bằng và đặt các giới hạn lập lịch về 0; trả về giá trị cũ để khôi phục."""
    previous = {key: value for key, value in pd.schedule_config().items() if key in LIMITS}
    for name in SCHEDULERS:
        pd.pause(name, PAUSE_SECONDS)
    pd.set_schedule(dict.fromkeys(LIMITS, 0))
    current = pd.schedule_config()
    stuck = [key for key in LIMITS if key in current and current[key] != 0]
    if stuck:
        raise RuntimeError(f"PD không nhận giới hạn lập lịch 0 cho {stuck}: {current}")
    return previous


def unfreeze_scheduling(pd: PD, previous: dict) -> None:
    for name in SCHEDULERS:
        pd.pause(name, 0)  # delay 0 = hết tạm dừng (xác nhận trên PD thật ở smoke đầu tiên)
    if previous:
        pd.set_schedule(previous)


def apply_layout(db, pd: PD, cfg: Settings, hot_ids: list[int], slots: int | None, timeout: float = 180.0,
                 sleep=time.sleep, clock=time.monotonic) -> dict:
    """Tách và đặt leader theo cfg.placement. Trả về bằng chứng (token khôi phục + leader mỗi bảng)."""
    stores = pd.stores()
    expected = int(os.environ.get("FLASHSALE_TIKV_COUNT", len(stores)))
    if len(stores) != expected:
        raise RuntimeError(f"PD báo {len(stores)} TiKV Up, kỳ vọng {expected}")
    replicas = pd.replicas()
    previous = freeze_scheduling(pd)
    evidence: dict = {"layout": cfg.placement, "scope": cfg.placement_scope, "stores": [s["id"] for s in stores],
                      "replicas": replicas, "previous_schedule": previous, "tables": {}}
    try:
        # Load Base Split có thể tự tách Region nóng theo tải: ghi lại để dùng cùng giá trị ở mọi cụm (đề 2.3).
        try:
            evidence["load_base_split"] = [(row["Instance"], row["Name"], row["Value"]) for row in db.query(
                "SHOW CONFIG WHERE type = 'tikv' AND name LIKE 'split.%'")]
        except Exception:
            evidence["load_base_split"] = None
        leaders = plan_stores(cfg, stores)
        tables = ["stock"] + (["district", "customer", "orders", "new_order", "order_line"]
                              if cfg.placement_scope == "all" else [])
        if cfg.orders_key != "composite" and "orders" in tables:
            tables.remove("orders")  # khóa chính o_seq: không bắt đầu bằng mã kho nên không tách theo kho
        for table in tables:
            split(db, table, split_keys(table, cfg))
            rows = settle(db, table, [leaders[w] for w in range(1, cfg.dataset.warehouses + 1)], pd, replicas,
                          timeout, sleep, clock)
            evidence["tables"][table] = _leaders(rows)
        if slots:
            keys = slot_keys(cfg, hot_ids, slots)
            split(db, SLOT_TABLE, keys)
            wanted = [stores[0]["id"]] + [stores[key[2] % len(stores)]["id"] for key in keys]
            evidence["tables"][SLOT_TABLE] = _leaders(settle(db, SLOT_TABLE, wanted, pd, replicas, timeout, sleep, clock))
    except BaseException:
        unfreeze_scheduling(pd, previous)
        raise
    return evidence


def _leaders(rows: list[dict]) -> dict[str, int]:
    count: dict[str, int] = {}
    for row in rows:
        count[str(row["LEADER_STORE_ID"])] = count.get(str(row["LEADER_STORE_ID"]), 0) + 1
    return count


def hot_regions(db) -> list[dict]:
    """Region nóng theo TIDB_HOT_REGIONS sau lượt đo (bằng chứng điểm nóng); rỗng nếu không đọc được."""
    try:
        return db.query("SELECT TABLE_NAME, TYPE, MAX_HOT_DEGREE, REGION_COUNT, FLOW_BYTES "
                        "FROM information_schema.TIDB_HOT_REGIONS LIMIT 20")
    except Exception:
        return []
