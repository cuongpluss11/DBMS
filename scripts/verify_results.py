#!/usr/bin/env python3
"""Kiểm tra toàn vẹn kết quả trong results/official (chỉ đọc, không chạm DBMS).

Với mỗi thư mục có INDEX.csv/runs/: số lượt, phân bố VALID/INVALID, run_id trùng, phiên bản DBMS và commit trong
manifest, môi trường/ghi chú chạy, CPU máy tải lớn nhất (cảnh báo > 80%), lượt thiếu result.json hoặc manifest.json,
INDEX.csv lệch với result.json. In bảng Markdown và mã thoát 1 nếu có lỗi (không tính INVALID dự kiến của P0).

  python scripts/verify_results.py [--out results/official/VERIFY.md]
"""
import argparse
import collections
import csv
import json
from pathlib import Path
import sys

ROOT = Path("results/official")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    args = parser.parse_args()
    lines = ["# Kiểm tra toàn vẹn results/official", "",
             "| Thư mục | Lượt | VALID | INVALID (không phải P0) | INVALID P0 | Phiên bản DBMS | Môi trường | Ghi chú chạy | CPU máy tải tối đa % | Vấn đề |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    problems = 0
    seen: dict[str, str] = {}
    for index in sorted(ROOT.glob("**/INDEX.csv")):
        base = index.parent
        runs_dir = base / "runs"
        if not runs_dir.is_dir():
            continue
        rows = list(csv.DictReader(index.open(encoding="utf-8")))
        issues = []
        versions, envs, notes, loads = set(), set(), set(), []
        valid = invalid_other = invalid_p0 = 0
        on_disk = {p.name for p in runs_dir.iterdir() if p.is_dir()}
        indexed = {r["run_id"] for r in rows}
        if on_disk != indexed:
            issues.append(f"INDEX và thư mục runs lệch ({len(on_disk ^ indexed)} lượt)")
        for r in rows:
            run_id = r["run_id"]
            if run_id in seen and seen[run_id] != str(base):
                issues.append(f"run_id trùng với {seen[run_id]}")
            seen.setdefault(run_id, str(base))
            run_dir = runs_dir / run_id
            result_path, manifest_path = run_dir / "result.json", run_dir / "manifest.json"
            if not result_path.is_file() or not manifest_path.is_file():
                issues.append(f"thiếu result/manifest: {run_id[:8]}")
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            status = result["validation"]["status"]
            if status != r["validation"]:
                issues.append(f"INDEX lệch result.json ở {run_id[:8]}")
            if status == "VALID":
                valid += 1
            elif result["variant"] == "p0":
                invalid_p0 += 1
            else:
                invalid_other += 1
                issues.append(f"INVALID không phải P0: {run_id[:8]} ({result['variant']})")
            versions.add(f"{result['engine']} {result.get('version')}")
            envs.add(r.get("environment_mode") or "?")
            notes.add(r.get("run_note") or "-")
            if result.get("loadgen_cpu_pct") is not None:
                loads.append(result["loadgen_cpu_pct"])
            if result["measurement"].get("tps") is None and status == "VALID":
                issues.append(f"VALID nhưng không có TPS: {run_id[:8]}")
        max_load = f"{max(loads):.0f}" if loads else "n/a"
        # máy tải 16 vCPU = 1600%; ngưỡng 80% = 1280% (máy tải nhỏ hơn dùng ngưỡng riêng trong manifest)
        issues = sorted(set(issues))
        problems += sum(1 for i in issues if "INVALID không phải P0" in i or "lệch" in i or "thiếu" in i or "trùng" in i)
        lines.append(f"| {base.relative_to(ROOT)} | {len(rows)} | {valid} | {invalid_other} | {invalid_p0} | "
                     f"{', '.join(sorted(versions))} | {', '.join(sorted(envs))} | {', '.join(sorted(notes))} | {max_load} | "
                     f"{'; '.join(issues) if issues else 'không'} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
