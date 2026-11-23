#!/usr/bin/env python3
"""Bảng 2×2 của TiDB kèm bằng chứng vị trí dữ liệu và tải từng node (chỉ đọc result.json đã commit, không đo thêm).

Với mỗi ô (số TiKV × P1/P2): TPS trung vị, số Region của `stock`/`stock_slot` trên từng store (replicas = 1 nên mỗi
Region có đúng một bản = leader), CPU trung vị của PD, TiDB server và từng TiKV (đơn vị % của một vCPU, trung bình
trong 60 giây đo). Dùng để kiểm tra giả thuyết "chia slot mới biến thêm TiKV thành lợi ích" trước khi kết luận.

  python scripts/placement_summary.py --out results/official/2.3-aws/PLACEMENT-2x2.md
"""
import argparse
import collections
import glob
import json
from pathlib import Path
import statistics
import sys


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    args = parser.parse_args()
    groups = collections.defaultdict(list)
    for stack in ("tidb1", "tidb3"):
        for path in glob.glob(f"results/official/2.3-aws/{stack}/runs/*/result.json"):
            run = json.loads(Path(path).read_text(encoding="utf-8"))
            if (run["theta"] != 0.9 or run["concurrency"] != 64 or run["order_warehouses"] != [1, 1]
                    or run["order_id_batch"] != 50 or run["validation"]["status"] != "VALID"):
                continue
            key = (run["tikv_count"], "P1 (N=1)" if run["variant"] == "p1" else f"P2 (N={run['slots']})")
            groups[key].append(run)
    lines = ["# Bảng 2×2 của TiDB với vị trí dữ liệu và tải từng node (θ=0,9, một kho, 64 client, lô mã 50)", "",
             "Sinh bởi `scripts/placement_summary.py` từ `result.json` của 2.3 (AWS). CPU = % của một vCPU trung bình trong 60 giây đo "
             "(TiKV m6i.large có 2 vCPU nên tối đa 200%; TiDB server 16 vCPU nên tối đa 1.600%).", "",
             "| TiKV | Thiết kế | TPS (trung vị) | Region `stock` theo store | Region `stock_slot` theo store | CPU PD | CPU TiDB | CPU từng TiKV |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for key in sorted(groups, key=lambda k: (k[0], k[1] != "P1 (N=1)", k[1])):
        runs = groups[key]
        tps = med([r["measurement"]["tps"] for r in runs])
        placement = runs[0].get("placement_result") or {}
        tables = placement.get("tables") or {}
        regions = lambda name: "/".join(f"s{store}:{count}" for store, count in (tables.get(name) or {}).items()) or "n/a"  # noqa: E731
        cpu = collections.defaultdict(list)
        for r in runs:
            for name, value in (r.get("container_cpu_pct") or {}).items():
                cpu[name].append(value)
        tikv = ", ".join(f"{name}={med(cpu[name]):.0f}%" for name in sorted(cpu) if name.startswith("tikv"))
        lines.append(f"| {key[0]} | {key[1]} | {tps:,.0f} | {regions('stock')} | {regions('stock_slot')} | "
                     f"{med(cpu['pd']):.0f}% | {med(cpu['tidb']):.0f}% | {tikv} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
