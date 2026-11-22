"""Thí nghiệm E1 của mục 2.4: Đổi lược đồ gốc dưới tải (DDL gốc + kẹt Metadata Lock).

Theo tài liệu ý tưởng (`bao_cao_DBMS_ban_chot.docx`, trang 21–22):
- Trong lúc tải nền chạy (`New-Order : Payment = 1 : 1` + `Xem đơn cũ` q=25%, θ=0.5, 64 client):
  - MySQL: thêm `ol_discount` và `ol_mig_state` bằng `ALGORITHM=INSTANT` và `COPY`;
    thêm chỉ mục `(ol_w_id, ol_i_id)` bằng `ALGORITHM=INPLACE`;
    kiểm chứng kẹt Metadata Lock khi có 1 giao dịch đọc `order_line` giữ mở 60s
    (cả không đặt `lock_wait_timeout` ngắn và có đặt `lock_wait_timeout=3` kèm retry).
  - MongoDB: không cần ALTER cho trường mới; đo `createIndex({"ol_w_id": 1, "ol_i_id": 1})`
    cả khi không có và khi có giao dịch đọc `order_line` giữ mở 60s.
- Xuất `tps_per_second.csv` (có đánh dấu lúc bắt đầu/kết thúc DDL), `result.json`
  (gồm `max_freeze_seconds`, `ddl_duration_seconds`, `metadata_locks_sample`, 3 luật tồn kho),
  và tổng hợp `E1_INDEX.csv` + `E1_SUMMARY.md`.
"""

from __future__ import annotations

import argparse
from contextlib import suppress
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import multiprocessing as mp
from pathlib import Path
from queue import Empty
import statistics
from threading import Event, Thread
import time
from typing import Any
from uuid import uuid4

from flashsale.adapters.base import Endpoint, open_adapter
from flashsale.benchmark.metrics import Phase, SCHEMA_VERSION, warmup_stability, write_json, write_series
from flashsale.benchmark.runner import get_counters, group, sample_cpu, start_phase
from flashsale.cli import dataset_state, restore
from flashsale.config import Settings, read_settings
from flashsale.infra import container_limits, endpoint as make_endpoint, host_info, ready
from flashsale.validation.checks import validate

E1_MYSQL_SCENARIOS = (
    "add_column_instant",
    "add_column_copy",
    "add_index_inplace",
    "mdl_freeze",
    "mdl_timeout_retry",
)

E1_MONGO_SCENARIOS = (
    "create_index",
    "create_index_long_txn",
)

E1_INDEX_NAME = "idx_e1_ol_w_i"


def compute_max_freeze_seconds(tps_measurement: list[float], threshold: float = 0.0) -> int:
    """Đếm số giây liên tiếp dài nhất trong pha đo có TPS <= threshold (đo thời gian đóng băng bảng)."""
    best = 0
    current = 0
    for value in tps_measurement:
        if value <= threshold:
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best


def _sql_columns(db: Any) -> set[str]:
    rows = db.query("SHOW COLUMNS FROM order_line")
    return {row.get("Field") or row.get("field") for row in rows}


def _sql_indexes(db: Any) -> set[str]:
    rows = db.query("SHOW INDEX FROM order_line")
    return {row.get("Key_name") or row.get("key_name") for row in rows}


def cleanup_e1_schema(db: Any) -> None:
    """Đưa lược đồ `order_line` về trạng thái gốc (không có cột/chỉ mục E1) để lặp độc lập."""
    if hasattr(db, "query"):
        cols = _sql_columns(db)
        drop_parts = []
        if "ol_discount" in cols:
            drop_parts.append("DROP COLUMN ol_discount")
        if "ol_mig_state" in cols:
            drop_parts.append("DROP COLUMN ol_mig_state")
        if drop_parts:
            db.query("ALTER TABLE order_line " + ", ".join(drop_parts))
        if E1_INDEX_NAME in _sql_indexes(db):
            db.query(f"ALTER TABLE order_line DROP INDEX {E1_INDEX_NAME}")
        return
    if hasattr(db, "db"):
        info = db.db["order_line"].index_information()
        if E1_INDEX_NAME in info:
            db.db["order_line"].drop_index(E1_INDEX_NAME)


def sample_mysql_metadata_locks(target: Endpoint, delay_s: float, out: dict[str, Any]) -> None:
    """Lấy snapshot `performance_schema.metadata_locks` trên bảng `order_line` khi MDL đang xảy ra."""
    time.sleep(delay_s)
    conn = None
    try:
        conn = open_adapter(target, timeout=10.0)
        rows = conn.query(
            "SELECT OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE, LOCK_DURATION, LOCK_STATUS, COUNT(*) AS cnt "
            "FROM performance_schema.metadata_locks "
            "WHERE OBJECT_NAME = 'order_line' "
            "GROUP BY OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE, LOCK_DURATION, LOCK_STATUS"
        )
        out["metadata_locks"] = rows
    except Exception as exc:
        out["metadata_locks_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if conn is not None:
            conn.close()


def run_long_read_txn(target: Endpoint, hold_seconds: float, start_delay: float,
                      out: dict[str, Any]) -> None:
    """Mở một giao dịch đọc `order_line` và giữ mở `hold_seconds` giây để tái hiện điều kiện kẹt MDL."""
    time.sleep(start_delay)
    conn = None
    began = time.monotonic()
    try:
        conn = open_adapter(target, timeout=hold_seconds + 30.0)
        if target.engine == "mysql":
            with conn.connection.cursor() as cur:
                cur.execute("BEGIN")
                cur.execute("SELECT ol_o_id FROM order_line LIMIT 1")
                cur.fetchall()
            out["started"] = True
            time.sleep(hold_seconds)
            conn.connection.commit()
            out["committed"] = True
        elif target.engine == "mongo":
            with conn.client.start_session() as session:
                with session.start_transaction():
                    conn.db["order_line"].find_one({}, {"_id": 1}, session=session)
                    out["started"] = True
                    time.sleep(hold_seconds)
            out["committed"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        out["duration_seconds"] = round(time.monotonic() - began, 3)
        if conn is not None:
            conn.close()


def execute_ddl_action(db: Any, engine: str, scenario: str,
                       lock_wait_timeout: int | None = None,
                       max_retries: int = 5) -> dict[str, Any]:
    """Thực thi đúng lệnh DDL của kịch bản E1, hỗ trợ `lock_wait_timeout` ngắn + retry theo tài liệu."""
    began = time.monotonic()
    attempts = 0
    timeouts = 0
    errors: list[str] = []
    succeeded = False

    if engine == "mysql":
        if scenario in {"add_column_instant", "mdl_freeze", "mdl_timeout_retry"}:
            sql = (
                "ALTER TABLE order_line "
                "ADD COLUMN ol_discount BIGINT NULL, "
                "ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED', "
                "ALGORITHM=INSTANT"
            )
        elif scenario == "add_column_copy":
            sql = (
                "ALTER TABLE order_line "
                "ADD COLUMN ol_discount BIGINT NULL, "
                "ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED', "
                "ALGORITHM=COPY"
            )
        elif scenario == "add_index_inplace":
            sql = f"ALTER TABLE order_line ADD INDEX {E1_INDEX_NAME} (ol_w_id, ol_i_id), ALGORITHM=INPLACE"
        else:
            raise ValueError(f"Kịch bản MySQL E1 không hợp lệ: {scenario}")

        if lock_wait_timeout is not None:
            db.query(f"SET SESSION lock_wait_timeout = {int(lock_wait_timeout)}")

        retry_limit = max_retries if lock_wait_timeout is not None else 0
        while True:
            attempts += 1
            try:
                db.query(sql)
                succeeded = True
                break
            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                errors.append(msg)
                is_lock_timeout = "1205" in msg or "lock wait timeout" in msg.lower()
                if is_lock_timeout:
                    timeouts += 1
                if not is_lock_timeout or attempts > retry_limit:
                    break
                time.sleep(min(0.5 * (2 ** (attempts - 1)), 4.0))
    elif engine == "mongo":
        if scenario in {"create_index", "create_index_long_txn"}:
            attempts = 1
            try:
                db.db["order_line"].create_index([("ol_w_id", 1), ("ol_i_id", 1)], name=E1_INDEX_NAME)
                succeeded = True
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        else:
            raise ValueError(f"Kịch bản MongoDB E1 không hợp lệ: {scenario}")
    else:
        raise ValueError(f"E1 hiện hỗ trợ mysql và mongo, nhận: {engine}")

    return {
        "scenario": scenario,
        "succeeded": succeeded,
        "attempts": attempts,
        "lock_wait_timeouts": timeouts,
        "lock_wait_timeout_setting": lock_wait_timeout,
        "duration_seconds": round(time.monotonic() - began, 3),
        "errors": errors,
    }


def run_e1_once(target: Endpoint, cfg: Settings, scenario: str, repetition: int,
                out_dir: Path, long_txn_seconds: float = 60.0,
                ddl_delay_seconds: float = 5.0,
                short_lock_timeout: int = 3) -> dict[str, Any]:
    """Chạy 1 lượt thí nghiệm E1 hoàn chỉnh (warmup -> measurement + DDL -> validate -> cleanup)."""
    run_id = uuid4().hex
    directory = out_dir / run_id
    directory.mkdir(parents=True, exist_ok=True)

    uses_long_txn = scenario in {"mdl_freeze", "mdl_timeout_retry", "create_index_long_txn"}
    hold_s = long_txn_seconds if uses_long_txn else 0.0
    lock_timeout = short_lock_timeout if scenario == "mdl_timeout_retry" else None
    meas_seconds = max(cfg.measurement_seconds, hold_s + ddl_delay_seconds + 15.0) if uses_long_txn else cfg.measurement_seconds
    run_cfg = replace(cfg, migration_strategy="none", measurement_seconds=meas_seconds)

    state = dataset_state(target, run_cfg)
    limits = container_limits(target.engine)
    server = ready(target.engine, timeout=0)

    db = open_adapter(target, timeout=180.0)
    try:
        cleanup_e1_schema(db)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "experiment": "2.4-E1",
            "scenario": scenario,
            "run_id": run_id,
            "repetition": repetition,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "engine": target.engine,
            "database": target.database,
            "server": server,
            "host": host_info(),
            "resource_limits": limits,
            "config": asdict(run_cfg),
            "e1_params": {
                "scenario": scenario,
                "long_txn_seconds": hold_s,
                "ddl_delay_seconds": ddl_delay_seconds,
                "lock_wait_timeout": lock_timeout,
            },
        }
        write_json(directory / "manifest.json", manifest)

        ctx_mp = mp.get_context("spawn")
        per = max(1, run_cfg.workers_per_process)
        groups = [list(range(i, min(i + per, run_cfg.concurrency))) for i in range(0, run_cfg.concurrency, per)]
        barrier = ctx_mp.Barrier(run_cfg.concurrency + 1)
        deadlines = ctx_mp.Array("d", 2)
        queue = ctx_mp.Queue()
        processes = [
            ctx_mp.Process(target=group, args=(target, run_cfg, run_id, repetition, workers, barrier, deadlines, queue))
            for workers in groups
        ]
        stop = Event()
        samples: dict[str, list[float]] = {}
        ddl_box: dict[str, Any] = {"result": None, "start_second": None, "end_second": None}
        long_txn_box: dict[str, Any] = {"started": False, "committed": False}
        mdl_box: dict[str, Any] = {}

        def ddl_worker(meas_start: float) -> None:
            wait_s = (meas_start + ddl_delay_seconds) - time.monotonic()
            if wait_s > 0:
                time.sleep(wait_s)
            ddl_box["start_second"] = max(0, int(time.monotonic() - meas_start))
            ddl_conn = open_adapter(target, timeout=max(300.0, hold_s + 120.0))
            try:
                ddl_box["result"] = execute_ddl_action(ddl_conn, target.engine, scenario,
                                                       lock_wait_timeout=lock_timeout)
            finally:
                ddl_box["end_second"] = max(ddl_box["start_second"], int(time.monotonic() - meas_start))
                ddl_conn.close()

        sampler = None
        ddl_thread = None
        long_thread = None
        mdl_thread = None
        try:
            for p in processes:
                p.start()
            start_phase(barrier, deadlines, 0, run_cfg.warmup_seconds)
            barrier.wait(timeout=run_cfg.warmup_seconds + 120)
            initial = get_counters(db)
            start_phase(barrier, deadlines, 1, run_cfg.measurement_seconds)
            meas_start = deadlines[1] - run_cfg.measurement_seconds

            if uses_long_txn:
                long_thread = Thread(
                    target=run_long_read_txn,
                    args=(target, hold_s, max(0.5, ddl_delay_seconds - 2.0), long_txn_box),
                    daemon=True,
                )
                long_thread.start()
            ddl_thread = Thread(target=ddl_worker, args=(meas_start,), daemon=True)
            ddl_thread.start()
            if target.engine == "mysql" and scenario == "mdl_freeze":
                mdl_thread = Thread(
                    target=sample_mysql_metadata_locks,
                    args=(target, ddl_delay_seconds + 3.0, mdl_box),
                    daemon=True,
                )
                mdl_thread.start()
            sampler = Thread(target=sample_cpu, args=(limits, deadlines[1], stop, samples), daemon=True)
            sampler.start()

            barrier.wait(timeout=run_cfg.measurement_seconds + 180)
            ddl_thread.join(timeout=300)
            if long_thread is not None:
                long_thread.join(timeout=hold_s + 30)
            if mdl_thread is not None:
                mdl_thread.join(timeout=15)
            final = get_counters(db)
            stop.set()

            warm_phase, meas_phase = Phase(), Phase()
            for _ in processes:
                w, m, err = queue.get(timeout=60)
                if err:
                    raise RuntimeError(err)
                warm_phase.merge(w)
                meas_phase.merge(m)
        finally:
            stop.set()
            if sampler is not None:
                sampler.join(timeout=5)
            for p in processes:
                p.join(timeout=2)
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=5)
            with suppress(Empty):
                queue.close()

        counters = {
            name: (final[name] - val if val is not None and final[name] is not None and final[name] >= val else None)
            for name, val in initial.items()
        }
        cpu = {name: round(statistics.mean(vals), 2) if vals else None for name, vals in samples.items()}
        warm_summary = warm_phase.summary(run_cfg.warmup_seconds)
        meas_summary = meas_phase.summary(run_cfg.measurement_seconds)
        expected = sorted(warm_phase.successful_orders + meas_phase.successful_orders)
        tps_series = {
            "warmup": warm_phase.series_list(run_cfg.warmup_seconds),
            "measurement": meas_phase.series_list(run_cfg.measurement_seconds),
        }
        p99_series = {
            "warmup": warm_phase.p99_series_list(run_cfg.warmup_seconds),
            "measurement": meas_phase.p99_series_list(run_cfg.measurement_seconds),
        }
        ddl_win = (ddl_box["start_second"], ddl_box["end_second"])
        write_series(directory / "tps_per_second.csv", tps_series, p99_series, ddl_win)
        max_freeze = compute_max_freeze_seconds(tps_series["measurement"])
        peak_p99 = max((v for v in p99_series["measurement"] if v is not None), default=None)

        validation = validate(db, run_cfg.dataset, run_id, expected, state["counts"], migration=False)
        cleanup_e1_schema(db)

        result = {
            "schema_version": SCHEMA_VERSION,
            "experiment": "2.4-E1",
            "scenario": scenario,
            "run_id": run_id,
            "engine": target.engine,
            "version": server["version"],
            "repetition": repetition,
            "concurrency": run_cfg.concurrency,
            "theta": run_cfg.theta,
            "old_order_read_pct": run_cfg.old_order_read_pct,
            "warmup": warm_summary,
            "measurement": meas_summary,
            "warmup_stability": warmup_stability(tps_series["warmup"], tps_series["measurement"]),
            "ddl": {
                **(ddl_box["result"] or {}),
                "start_second": ddl_box["start_second"],
                "end_second": ddl_box["end_second"],
                "max_freeze_seconds": max_freeze,
                "peak_1s_p99_ms": round(peak_p99, 2) if peak_p99 is not None else None,
                "long_txn": long_txn_box if uses_long_txn else None,
                "metadata_locks_sample": mdl_box.get("metadata_locks"),
            },
            "lock_wait_ms": counters["lock_wait_ms"],
            "server_deadlocks": counters["server_deadlocks"],
            "container_cpu_pct": cpu,
            "tps_series": tps_series,
            "p99_series": p99_series,
            "validation": validation,
        }
        write_json(directory / "result.json", result)
        return result
    finally:
        with suppress(Exception):
            cleanup_e1_schema(db)
        db.close()


def summarize_e1(out_dir: Path) -> dict[str, Any]:
    """Tổng hợp tất cả các lượt E1 trong `out_dir` thành `E1_INDEX.csv` và `E1_SUMMARY.md`."""
    rows: list[dict[str, Any]] = []
    for path in sorted(out_dir.glob("*/result.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("experiment") != "2.4-E1":
            continue
        ddl = d.get("ddl") or {}
        meas = d.get("measurement") or {}
        warm = d.get("warmup") or {}
        rows.append({
            "run_id": d["run_id"],
            "engine": d["engine"],
            "scenario": d["scenario"],
            "repetition": d["repetition"],
            "status": (d.get("validation") or {}).get("status"),
            "warmup_tps": round(warm.get("tps") or 0.0, 2),
            "meas_tps": round(meas.get("tps") or 0.0, 2),
            "p99_ms": round(meas.get("p99_ms") or 0.0, 2),
            "peak_1s_p99_ms": ddl.get("peak_1s_p99_ms"),
            "ddl_succeeded": ddl.get("succeeded"),
            "ddl_duration_s": ddl.get("duration_seconds"),
            "ddl_attempts": ddl.get("attempts"),
            "ddl_lock_timeouts": ddl.get("lock_wait_timeouts"),
            "max_freeze_s": ddl.get("max_freeze_seconds"),
            "lock_wait_ms": d.get("lock_wait_ms"),
        })

    fieldnames = [
        "run_id", "engine", "scenario", "repetition", "status",
        "warmup_tps", "meas_tps", "p99_ms", "peak_1s_p99_ms",
        "ddl_succeeded", "ddl_duration_s", "ddl_attempts", "ddl_lock_timeouts",
        "max_freeze_s", "lock_wait_ms",
    ]
    with (out_dir / "E1_INDEX.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault((r["engine"], r["scenario"]), []).append(r)

    lines = [
        "# Tổng hợp thí nghiệm E1 – Đổi lược đồ gốc dưới tải & kẹt Metadata Lock",
        "",
        "| Hệ DBMS | Kịch bản E1 | Lượt VALID | TPS nền (warmup) | TPS đo (median) | p99 toàn pha (ms) | Đỉnh p99 1s (ms) | Thời gian DDL (s) | Đóng băng lâu nhất (s) | DDL thành công / timeout |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for (eng, scen), items in sorted(grouped.items()):
        valid_n = sum(1 for x in items if x["status"] == "VALID")
        med = lambda k: round(statistics.median([x[k] for x in items if x[k] is not None]), 2) if any(x[k] is not None for x in items) else None
        succ_n = sum(1 for x in items if x["ddl_succeeded"])
        to_sum = sum(int(x["ddl_lock_timeouts"] or 0) for x in items)
        lines.append(
            f"| {eng} | `{scen}` | {valid_n}/{len(items)} | {med('warmup_tps')} | **{med('meas_tps')}** | "
            f"{med('p99_ms')} | {med('peak_1s_p99_ms')} | {med('ddl_duration_s')} | **{med('max_freeze_s')}** | "
            f"{succ_n}/{len(items)} (timeout: {to_sum}) |"
        )
    (out_dir / "E1_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"runs": len(rows), "groups": len(grouped), "out_dir": str(out_dir)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Chạy thí nghiệm E1 (mục 2.4): DDL gốc dưới tải + kẹt Metadata Lock.")
    ap.add_argument("engine", choices=("mysql", "mongo"))
    ap.add_argument("--config", type=Path, default=Path("configs/migration.toml"))
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--scenarios", nargs="+", default=None)
    ap.add_argument("--repetitions", type=int, default=3)
    ap.add_argument("--long-txn-seconds", type=float, default=60.0)
    ap.add_argument("--ddl-delay-seconds", type=float, default=5.0)
    ap.add_argument("--short-lock-timeout", type=int, default=3)
    ap.add_argument("--out-dir", type=Path, default=Path("results/official/2.4-e1"))
    ap.add_argument("--no-reset", action="store_true")
    args = ap.parse_args()

    cfg = read_settings(args.config)
    target = make_endpoint(args.engine, args.dataset)
    scenarios = args.scenarios or (list(E1_MYSQL_SCENARIOS) if args.engine == "mysql" else list(E1_MONGO_SCENARIOS))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for scen in scenarios:
        for rep in range(1, args.repetitions + 1):
            if not args.no_reset:
                restore(target, cfg, dataset_state(target, cfg))
            res = run_e1_once(
                target, cfg, scen, rep, args.out_dir,
                long_txn_seconds=args.long_txn_seconds,
                ddl_delay_seconds=args.ddl_delay_seconds,
                short_lock_timeout=args.short_lock_timeout,
            )
            results.append({
                "run_id": res["run_id"],
                "engine": res["engine"],
                "scenario": res["scenario"],
                "repetition": rep,
                "status": res["validation"]["status"],
                "tps": round(res["measurement"]["tps"], 2),
                "p99_ms": round(res["measurement"]["p99_ms"], 2),
                "ddl_duration_s": res["ddl"]["duration_seconds"],
                "max_freeze_s": res["ddl"]["max_freeze_seconds"],
                "ddl_succeeded": res["ddl"]["succeeded"],
            })
    summary = summarize_e1(args.out_dir)
    print(json.dumps({"results": results, "summary": summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
