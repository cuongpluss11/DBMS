#!/usr/bin/env python3
"""Gom số liệu tranh chấp (RQ1) và kết quả P0 từ result.json của mục 2.2 (chỉ đọc, không chạm DBMS).

Ví dụ:
  python scripts/contention_summary.py --out results/official/2.2-aws/CONTENTION.md
"""
import argparse
import collections
import json
from pathlib import Path
import statistics
import sys

ENGINES = {"MySQL": "mysql", "MongoDB": "mongo", "TiDB": "tidb3"}
ROOT = Path("results/official/2.2-aws")


def load(engine_dir: str) -> list[dict]:
    rows = []
    for path in sorted((ROOT / engine_dir / "runs").glob("*/result.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        m = run["measurement"]
        if m.get("tps") is None:
            continue
        run["_m"] = m
        rows.append(run)
    return rows


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(value, digits=1):
    return "n/a" if value is None else f"{value:,.{digits}f}"


def share(wait_ms, run):
    """Tổng thời gian chờ khóa trong 60 s ÷ (số client × 60 s); >100% là có thể vì lock_wait cộng dồn từ mọi luồng server."""
    if wait_ms is None:
        return "n/a"
    return f"{100 * wait_ms / (run['concurrency'] * run['measurement']['seconds'] * 1000):.0f}%"


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    args = parser.parse_args()
    data = {name: load(directory) for name, directory in ENGINES.items()}
    lines = ["# Số liệu tranh chấp và kết quả P0 (mục 2.2, AWS)", "",
             "Sinh bởi `scripts/contention_summary.py` từ `result.json`; trung vị 3 lần lặp. `n/a` = hệ không cung cấp "
             "metric đó (không đưa về 0). Lỗi theo mỗi 100 yêu cầu = `request_error_pct`; `lock_wait_ms` chỉ có ở MySQL.", ""]

    lines += ["## P0 (đọc rồi ghi, không khóa) so với bất biến", "",
              "| Hệ | Lượt P0 | INVALID | Lỗi `write_conflict` mỗi lượt (min–max) | Deadlock (tổng) | Dòng lệch đối soát INV2 (tổng) |",
              "| --- | --- | --- | --- | --- | --- |"]
    for name, rows in data.items():
        p0 = [r for r in rows if r["variant"] == "p0"]
        invalid = [r for r in p0 if r["validation"]["status"] != "VALID"]
        wcs = [r["_m"]["error_counts"].get("write_conflict") or 0 for r in p0]
        wc = f"{min(wcs):,}–{max(wcs):,}" if wcs else "n/a"
        dead = sum(r["_m"]["error_counts"].get("deadlock") or 0 for r in p0)
        mism = sum(len(r["validation"]["errors"].get("reconciliation", [])) for r in p0)
        lines.append(f"| {name} | {len(p0)} | {len(invalid)} | {wc} | {dead} | {mism} |")
    lines += ["", "INV1 (tồn không âm) đúng ở mọi lượt P0 vì tồn đầu rất lớn; lỗi nằm ở INV2 (mất cập nhật).", ""]

    lines += ["## P1 một kho: tranh chấp theo mức tập trung (64 client)", "",
              "| Hệ | Cấu hình | TPS | p99 (ms) | Abort % | Retry % | Deadlock | `write_conflict` | Lock wait (ms) | Lock wait ÷ thời gian client |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, rows in data.items():
        groups = collections.defaultdict(list)
        for r in rows:
            if r["variant"] == "p1" and r["label"] == "hotspot" and r["concurrency"] == 64 and r["txn_mode"] == "default" \
                    and r["mongo_design"] != "b":
                groups[("một món" if r["hot_item"] else f"θ={r['theta']}")].append(r)
        order = sorted(groups, key=lambda k: (k == "một món", k))
        for key in order:
            rs = groups[key]
            lines.append(
                f"| {name} | {key} | {fmt(med([r['_m']['tps'] for r in rs]), 0)} | {fmt(med([r['_m']['p99_ms'] for r in rs]), 0)} | "
                f"{fmt(med([r['_m']['abort_pct'] for r in rs]))} | {fmt(med([r['_m']['retry_pct'] for r in rs]))} | "
                f"{fmt(med([r['_m']['error_counts'].get('deadlock') for r in rs]), 0)} | "
                f"{fmt(med([r['_m']['error_counts'].get('write_conflict') for r in rs]), 0)} | "
                f"{fmt(med([r.get('lock_wait_ms') if not isinstance(r.get('lock_wait_ms'), dict) else None for r in rs]), 0)} | "
                f"{share(med([r.get('lock_wait_ms') if not isinstance(r.get('lock_wait_ms'), dict) else None for r in rs]), rs[0])} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
