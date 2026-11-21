"""Tổng hợp results/<run_id>/ thành INDEX.csv, SUMMARY.md và bảng kiểm tra warmup.

Không đọc DBMS; chỉ đọc manifest.json và result.json đã có. Metric thiếu giữ `null`/trống, không mặc định 0.
"""
import csv
from collections import defaultdict
import json
from pathlib import Path
import statistics
from typing import Any

from .metrics import warmup_stability

INDEX_COLUMNS = [
    "run_id", "engine", "version", "profile", "label", "repetition", "concurrency", "warehouse_mode", "theta",
    "hot_item", "variant", "slots", "order_id_batch", "arrival_rate", "migration_strategy", "old_order_read_pct",
    "migration_duration_seconds", "inventory_mode", "payment_ytd", "idempotency", "client_timeout_seconds",
    "tps", "p50_ms", "p95_ms", "p99_ms", "abort_pct", "out_of_stock_pct", "retry_pct", "validation", "git_commit",
    "warmup_drift_pct", "loadgen_cpu_pct", "environment_mode", "run_note"]
GROUP_KEYS = ("engine", "profile", "concurrency", "warehouse_mode", "theta", "hot_item", "variant", "slots",
              "order_id_batch", "arrival_rate", "migration_strategy", "old_order_read_pct", "payment_ytd",
              "idempotency", "run_note")
WARMUP_DRIFT_LIMIT_PCT = 10.0


def collect(results_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for folder in sorted(results_dir.iterdir()):
        manifest_path, result_path = folder / "manifest.json", folder / "result.json"
        if not (manifest_path.is_file() and result_path.is_file()):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        measurement = result["measurement"]
        series = result.get("tps_series")
        stability = (warmup_stability(**series) if series else result.get("warmup_stability")) or {}
        rows.append({
            "run_id": result["run_id"], "engine": result["engine"], "version": result["version"],
            "profile": Path(manifest.get("config_path", "")).stem or None, "label": result["label"],
            "repetition": result["repetition"], "concurrency": result["concurrency"],
            "warehouse_mode": result["warehouse_mode"], "theta": result["theta"], "hot_item": result["hot_item"],
            "inventory_mode": result["inventory_mode"],
            # Lượt 2.1 cũ không có các trường này: coi là legacy (cách trừ kho của 2.1), không có slot, không cấp mã theo lô.
            "variant": result.get("variant", "legacy"), "slots": result.get("slots"),
            "order_id_batch": result.get("order_id_batch", 0), "arrival_rate": result.get("arrival_rate", 0.0),
            "migration_strategy": result.get("migration_strategy", "none"),
            "old_order_read_pct": result.get("old_order_read_pct", 0.0),
            "migration_duration_seconds": (result.get("migration") or {}).get("duration_seconds"),
            "payment_ytd": manifest.get("config", {}).get("payment_ytd"),
            "idempotency": result.get("idempotency", True),
            "client_timeout_seconds": result.get("client_timeout_seconds"),
            "tps": measurement["tps"], "p50_ms": measurement["p50_ms"], "p95_ms": measurement["p95_ms"],
            "p99_ms": measurement["p99_ms"], "abort_pct": measurement["abort_pct"],
            "out_of_stock_pct": measurement["out_of_stock_pct"], "retry_pct": measurement["retry_pct"],
            "validation": result["validation"]["status"],
            "git_commit": manifest.get("environment", {}).get("git_commit"),
            "warmup_drift_pct": stability.get("drift_pct"), "loadgen_cpu_pct": result.get("loadgen_cpu_pct"),
            "environment_mode": manifest.get("environment", {}).get("mode", "docker"),
            "run_note": manifest.get("environment", {}).get("run_note"),
        })
    return rows


def _fmt(value: Any, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in GROUP_KEYS)].append(row)
    summary = []
    for key, items in sorted(groups.items(), key=lambda pair: tuple(str(part) for part in pair[0])):
        tps = [item["tps"] for item in items if item["tps"] is not None]
        p99 = [item["p99_ms"] for item in items if item["p99_ms"] is not None]
        summary.append({
            **dict(zip(GROUP_KEYS, key)), "runs": len(items),
            "valid": sum(item["validation"] == "VALID" for item in items),
            "tps_median": statistics.median(tps) if tps else None,
            "tps_min": min(tps) if tps else None, "tps_max": max(tps) if tps else None,
            "p99_median_ms": statistics.median(p99) if p99 else None,
        })
    return summary


def warmup_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mỗi lượt: drift giữa TPS cuối warmup và đầu đo. null = lượt cũ không có chuỗi theo giây."""
    table = []
    for row in rows:
        drift = row["warmup_drift_pct"]
        status = "no_series" if drift is None else ("WARMUP_MAY_BE_SHORT" if abs(drift) > WARMUP_DRIFT_LIMIT_PCT else "ok")
        table.append({"run_id": row["run_id"], "engine": row["engine"], "profile": row["profile"],
                      "concurrency": row["concurrency"], "theta": row["theta"], "drift_pct": drift, "status": status})
    return table


def markdown(summary: list[dict[str, Any]], warmup: list[dict[str, Any]]) -> str:
    lines = ["# Tổng hợp kết quả", "",
             "Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. "
             "`valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.", "",
             "| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for item in summary:
        lines.append(
            f"| {item['engine']} | {item['profile']} | {item['concurrency']} | {item['warehouse_mode']} | "
            f"{item['theta']} | {item['hot_item']} | {item['variant']} | {item['slots'] or ''} | {item['order_id_batch']} | {item['arrival_rate'] or 'kín'} | {item['payment_ytd']} | {item['idempotency']} | {item['run_note'] or ''} | {item['runs']} | "
            f"{item['valid']}/{item['runs']} | {_fmt(item['tps_median'])} ({_fmt(item['tps_min'])}–{_fmt(item['tps_max'])}) | "
            f"{_fmt(item['p99_median_ms'])} |")
    checked = [row for row in warmup if row["status"] != "no_series"]
    short = [row for row in warmup if row["status"] == "WARMUP_MAY_BE_SHORT"]
    lines += ["", "## Kiểm tra warmup 30 giây", "",
              f"{len(checked)}/{len(warmup)} lượt có chuỗi TPS theo giây; {len(short)} lượt lệch quá "
              f"{WARMUP_DRIFT_LIMIT_PCT:.0f}% giữa 10 giây cuối warmup và 10 giây đầu đo."]
    if short:
        lines += ["", "| run_id | engine | profile | client | θ | drift % |", "| --- | --- | --- | --- | --- | --- |"]
        lines += [f"| {row['run_id']} | {row['engine']} | {row['profile']} | {row['concurrency']} | {row['theta']} | "
                  f"{_fmt(row['drift_pct'])} |" for row in short]
        lines += ["", "Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại."]
    return "\n".join(lines) + "\n"


def write_report(results_dir: Path, out_dir: Path) -> dict[str, Any]:
    rows = collect(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "INDEX.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row[key] is None else round(row[key], 2) if isinstance(row[key], float)
                             else row[key] for key in INDEX_COLUMNS})
    summary = summarize(rows)
    warmup = warmup_table(rows)
    (out_dir / "SUMMARY.md").write_text(markdown(summary, warmup), encoding="utf-8")
    return {"runs": len(rows), "groups": len(summary),
            "invalid": sum(row["validation"] != "VALID" for row in rows),
            "warmup_may_be_short": sum(row["status"] == "WARMUP_MAY_BE_SHORT" for row in warmup),
            "out_dir": str(out_dir)}
