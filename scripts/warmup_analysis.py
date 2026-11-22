#!/usr/bin/env python3
"""Phân tích độ đủ của warmup 30 giây từ tps_per_second.csv của các lượt đã đo (chỉ đọc, không chạm DBMS).

`warmup_drift_pct` trong INDEX.csv chỉ so hai cửa sổ 10 giây nên rất nhiễu khi TPS thấp. Script này kiểm ba điều:
  1. Có xu hướng hệ thống không: tỉ lệ TPS 10 giây cuối warmup / TPS trung vị của cả 60 giây đo. Nếu warmup quá ngắn,
     tỉ lệ này lệch cùng một phía (thấp hơn 1) ở đa số lượt; nếu chỉ là nhiễu thì hai phía cân bằng.
  2. Độ biến thiên theo giây (CV) của 60 giây đo, để thấy lượt lệch lớn có phải do TPS thấp/rất giật.
  3. Xu hướng trong chính 60 giây đo (nửa sau so với nửa đầu).

Ví dụ:
  python scripts/warmup_analysis.py results/official/2.2-aws/tidb3/runs results/official/2.3-aws/tidb3/runs \\
      --out results/official/warmup-analysis.md
"""
import argparse
import csv
from pathlib import Path
import statistics
import sys

HEAD = 10   # giây
LOW_TPS = 50.0


def load_series(path: Path) -> dict[str, list[int]]:
    series: dict[str, list[int]] = {}
    with path.open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            series.setdefault(row["phase"], []).append(int(row["successes"]))
    return series


def analyze(run_dir: Path) -> dict | None:
    import json
    series_path, result_path = run_dir / "tps_per_second.csv", run_dir / "result.json"
    if not (series_path.is_file() and result_path.is_file()):
        return None
    series = load_series(series_path)
    warmup, measurement = series.get("warmup", []), series.get("measurement", [])
    if len(warmup) < HEAD or len(measurement) < 2 * HEAD:
        return None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    measured = statistics.median(measurement)
    half = len(measurement) // 2
    first, second = statistics.mean(measurement[:half]), statistics.mean(measurement[half:])
    mean = statistics.mean(measurement)
    return {
        "run_id": result["run_id"], "engine": result["engine"], "label": result.get("label"),
        "variant": result.get("variant", "legacy"), "theta": result["theta"], "concurrency": result["concurrency"],
        "tikv": result.get("tikv_count"), "vcpus": (result.get("resource_limits") or {}).get("cpus"),
        "tps": result["measurement"]["tps"], "validation": result["validation"]["status"],
        "ramp_ratio": statistics.median(warmup[-HEAD:]) / measured if measured else None,
        "early_ratio": statistics.median(warmup[:HEAD]) / measured if measured else None,
        "cv": statistics.pstdev(measurement) / mean if mean else None,
        "trend_pct": 100 * (second - first) / first if first else None,
    }


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", help="thư mục runs/ (mỗi thư mục con là một lượt)")
    parser.add_argument("--out", help="ghi Markdown vào file (mặc định in ra màn hình)")
    args = parser.parse_args()
    rows = [item for runs in args.runs for folder in sorted(Path(runs).iterdir()) if folder.is_dir()
            for item in [analyze(folder)] if item]
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["engine"], row["tikv"] or "", row["vcpus"] or ""), []).append(row)
    lines = ["# Phân tích warmup từ chuỗi TPS theo giây", "",
             f"{len(rows)} lượt có chuỗi theo giây. `ramp` = TPS trung vị {HEAD} giây cuối warmup ÷ TPS trung vị 60 giây "
             f"đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = {HEAD} giây đầu warmup ÷ TPS đo. "
             "`CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.",
             "", "| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (engine, tikv, vcpus), items in sorted(groups.items(), key=lambda pair: str(pair[0])):
        ramp = [item["ramp_ratio"] for item in items if item["ramp_ratio"] is not None]
        lines.append(
            f"| {engine} | {tikv} | {vcpus} | {len(items)} | {statistics.median(ramp):.2f} | "
            f"{sum(value < 0.9 for value in ramp)} | {sum(value > 1.1 for value in ramp)} | "
            f"{statistics.median(item['early_ratio'] for item in items):.2f} | "
            f"{statistics.median(item['cv'] for item in items):.2f} | "
            f"{statistics.median(item['trend_pct'] for item in items):.1f} |")
    low = [item for item in rows if item["tps"] < LOW_TPS]
    off = [item for item in rows if item["ramp_ratio"] is not None and not 0.9 <= item["ramp_ratio"] <= 1.1]
    off_low = [item for item in off if item["tps"] < LOW_TPS]
    lines += ["", f"Lượt ngoài khoảng ramp 0,9–1,1: {len(off)}/{len(rows)}, trong đó {len(off_low)} lượt có TPS < {LOW_TPS:.0f} "
              f"(tổng {len(low)} lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).", ""]
    if off:
        lines += ["| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for item in sorted(off, key=lambda item: abs(item["ramp_ratio"] - 1), reverse=True):
            lines.append(f"| {item['run_id']} | {item['engine']} | {item['variant']} | {item['theta']} | "
                         f"{item['concurrency']} | {item['tikv'] or item['vcpus']} | {item['tps']:.1f} | "
                         f"{item['ramp_ratio']:.2f} | {item['cv']:.2f} | {item['trend_pct']:.1f} | {item['validation']} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
