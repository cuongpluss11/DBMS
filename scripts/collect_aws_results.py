#!/usr/bin/env python3
"""Gom kết quả đo AWS từ máy tải về repo (không đọc DBMS, không sinh số liệu).

Ba lệnh con:

  pull     tải ~/DBMS/results (bỏ successful_new_orders.json và examples) cùng các thư mục log ma trận
           từ máy tải về một thư mục tạm; chỉ đọc, không xóa gì trên máy tải.
  split    lọc các lượt theo `run_note` trong manifest, chép vào results/official/<đích>/runs, chép log ma trận
           tương ứng và sinh INDEX.csv, SUMMARY.md (cùng cách bố trí với results/official/2.2-aws/tidb3).
  combine  gộp nhiều thư mục runs/ (ví dụ MySQL 24 và 20 vCPU cùng TiDB 1 và 3 TiKV) thành một báo cáo tăng tốc.

Ví dụ cho chuỗi đo MySQL (khớp ~/run_mysql_all.sh):

  python scripts/collect_aws_results.py pull --host <IP máy tải> --key ~/.ssh/flashsale_aws --dest .work/pull-mysql
  python scripts/collect_aws_results.py split --src .work/pull-mysql --note m22-mysql \\
      --logs m22-mysql --out results/official/2.2-aws/mysql
  python scripts/collect_aws_results.py split --src .work/pull-mysql --note mysql-24vcpu --note mysql-20vcpu \\
      --logs m23-mysql24a m23-mysql24b m23-mysql24c m23-mysql20a m23-mysql20b m23-mysql20c \\
      --out results/official/2.3-aws/mysql
  python scripts/collect_aws_results.py combine --runs results/official/2.3-aws/mysql/runs \\
      results/official/2.3-aws/tidb1/runs results/official/2.3-aws/tidb3/runs \\
      --out results/official/2.3-aws/SUMMARY-speedup.md

Không bao giờ chép successful_new_orders.json (dữ liệu thô lớn, AGENTS.md mục 4).
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from flashsale.benchmark import report  # noqa: E402

RAW_NAME = "successful_new_orders.json"
RUN_FILES = ("manifest.json", "result.json", "result.csv", "tps_per_second.csv")


def _ssh_tar(args: argparse.Namespace, remote_command: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    command = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", str(Path(args.key).expanduser()),
               f"{args.user}@{args.host}", remote_command]
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        with tarfile.open(fileobj=process.stdout, mode="r|gz") as archive:
            for member in archive:
                if Path(member.name).name == RAW_NAME:
                    continue
                archive.extract(member, dest)
        if process.wait() != 0:
            raise SystemExit(f"ssh/tar thất bại (mã {process.returncode}): {remote_command}")


def pull(args: argparse.Namespace) -> None:
    dest = Path(args.dest)
    _ssh_tar(args, f"cd ~/DBMS/results && tar czf - --exclude={RAW_NAME} --exclude=examples .", dest / "results")
    for pattern in args.log_glob:
        listing = subprocess.run(
            ["ssh", "-n", "-o", "BatchMode=yes", "-i", str(Path(args.key).expanduser()), f"{args.user}@{args.host}",
             f"cd ~ && ls -d {pattern} 2>/dev/null"], capture_output=True, text=True)
        for name in listing.stdout.split():
            _ssh_tar(args, f"cd ~/{name} && tar czf - .", dest / "logs" / name)
    print(f"Đã tải về {dest} ({sum(1 for _ in (dest / 'results').iterdir())} thư mục kết quả)")


def split(args: argparse.Namespace) -> None:
    source, out = Path(args.src) / "results", Path(args.out)
    notes = set(args.note)
    rows = [row for row in report.collect(source) if row["run_note"] in notes]
    if not rows:
        raise SystemExit(f"Không có lượt nào có run_note thuộc {sorted(notes)} trong {source}")
    (out / "runs").mkdir(parents=True, exist_ok=True)
    for row in rows:
        target = out / "runs" / row["run_id"]
        target.mkdir(exist_ok=True)
        for name in RUN_FILES:
            if (source / row["run_id"] / name).is_file():
                shutil.copy2(source / row["run_id"] / name, target / name)
    for log in args.logs:
        log_source = Path(args.src) / "logs" / log
        if log_source.is_dir():
            shutil.copytree(log_source, out / "logs" / log, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(RAW_NAME))
        else:
            print(f"CẢNH BÁO: không thấy log {log_source}", file=sys.stderr)
    summary = report.write_report(out / "runs", out)
    print(summary)
    by_note = {note: sum(row["run_note"] == note for row in rows) for note in sorted(notes)}
    print("Số lượt theo run_note:", by_note)
    invalid = [row for row in rows if row["validation"] != "VALID"]
    for row in invalid:
        print(f"INVALID {row['run_id']} variant={row['variant']} theta={row['theta']} note={row['run_note']}")


def combine(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        merged = Path(tmp) / "merged"
        merged.mkdir()
        for runs_dir in args.runs:
            for folder in Path(runs_dir).iterdir():
                if (folder / "result.json").is_file() and (folder / "manifest.json").is_file():
                    target = merged / folder.name
                    target.mkdir(exist_ok=True)
                    for name in ("manifest.json", "result.json"):
                        shutil.copy2(folder / name, target / name)
        report.write_report(merged, Path(tmp) / "out")
        text = (Path(tmp) / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"Đã ghi {args.out}")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):    # Windows: cp1252 không in được tiếng Việt
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_pull = sub.add_parser("pull")
    p_pull.add_argument("--host", required=True)
    p_pull.add_argument("--key", required=True)
    p_pull.add_argument("--user", default="ubuntu")
    p_pull.add_argument("--dest", required=True)
    p_pull.add_argument("--log-glob", nargs="*", default=["m22-mysql", "m23-mysql*[abc]"],
                        help="mẫu tên thư mục log ma trận trong ~ (bỏ file .out)")
    p_pull.set_defaults(func=pull)
    p_split = sub.add_parser("split")
    p_split.add_argument("--src", required=True, help="thư mục đã `pull` (chứa results/ và logs/)")
    p_split.add_argument("--note", action="append", required=True, help="run_note cần lấy (lặp được)")
    p_split.add_argument("--logs", nargs="*", default=[], help="tên thư mục log trong <src>/logs")
    p_split.add_argument("--out", required=True)
    p_split.set_defaults(func=split)
    p_combine = sub.add_parser("combine")
    p_combine.add_argument("--runs", nargs="+", required=True)
    p_combine.add_argument("--out", required=True)
    p_combine.set_defaults(func=combine)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
