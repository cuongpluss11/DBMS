#!/usr/bin/env python3
"""Fault injection thật: giết tiến trình worker (SIGKILL/TerminateProcess) giữa lúc đang chạy giao dịch, khởi động
lại worker thay thế thử lại CÙNG request_id, rồi kiểm ba luật tồn kho (mục 2.2).

Khác `tests/test_fault_injection.py` (lớp bọc chèn lỗi có kiểm soát tại điểm xác định), script này giết tiến trình
ở thời điểm ngẫu nhiên nên bao phủ cả "chết trước commit", "chết sau commit trước khi nhận phản hồi" và "chết khi
đang retry". Mô hình lỗi: tiến trình ứng dụng chết, DBMS và mạng vẫn sống.

Bằng chứng cửa sổ nguy hiểm được chạm: khi một worker mới nhận lại yêu cầu mà worker cũ đã bắt đầu, script đọc DB
TRƯỚC khi chạy lại và đếm `rerun_found_committed` (đã commit trước khi chết: cửa sổ "commit xong, chưa ack") và
`rerun_not_committed` (chết trước commit). `--post-commit-delay-ms` kéo dài nhân tạo cửa sổ sau commit để kill ngẫu
nhiên rơi vào đó nhiều hơn.

Đối chứng âm `--idempotency-off`: cùng kịch bản trên dataset không UNIQUE và yêu cầu không idempotent; phải thấy đơn
trùng và INVALID. Nếu đối chứng không phát hiện được lỗi thì kết quả PASS ở chế độ thường không có giá trị.

Ví dụ (DBMS đã chạy, một hệ tại một thời điểm):
  python scripts/fault_kill_cycles.py mysql --requests 3000 --workers 16 --post-commit-delay-ms 30 --out results/official/fault-injection
  python scripts/fault_kill_cycles.py mysql --requests 3000 --workers 16 --post-commit-delay-ms 30 --idempotency-off --out ...
"""
import argparse
import dataclasses
import json
from pathlib import Path
import multiprocessing as mp
import random
import sys
import tempfile
import time
import uuid

from flashsale.adapters.base import open_adapter
from flashsale.config import read_settings
from flashsale.data.loader import load
from flashsale.faults import CommitWindowAdapter
from flashsale.infra import enforce_one, endpoint, project_lock
from flashsale.transactions.core import lookup
from flashsale.validation.checks import validate
from flashsale.workload.generator import Request
from flashsale.workload.retry import run_request


def build_requests(run_id: str, count: int, items: int, seed: int, idempotent: bool) -> list[Request]:
    rng = random.Random(seed)
    requests = []
    for i in range(count):
        district, customer = rng.randint(1, 2), rng.randint(1, 10)
        if i % 2:
            requests.append(Request(f"{run_id}-k{i}", run_id, "payment", 1, district, customer,
                                    amount=rng.randint(100, 5000), idempotent=idempotent))
        else:
            picked = rng.sample(range(1, items + 1), rng.randint(1, 3))
            requests.append(Request(f"{run_id}-k{i}", run_id, "new_order", 1, district, customer,
                                    tuple((item, rng.randint(1, 5)) for item in picked), idempotent=idempotent))
    return requests


def read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def worker(target, requests: list[Request], ack_path: str, delay_ms: float) -> None:
    raw = open_adapter(target)
    db = CommitWindowAdapter(raw, delay_ms) if delay_ms > 0 else raw
    path = Path(ack_path)
    done = {line.split()[0] for line in read_lines(path)}
    prior_attempts = set(read_lines(Path(ack_path + ".attempts")))
    with path.open("a", encoding="utf-8") as ack, Path(ack_path + ".attempts").open("a", encoding="utf-8") as attempts, \
            Path(ack_path + ".rerun").open("a", encoding="utf-8") as rerun:
        for req in requests:
            if req.request_id in done:
                continue
            if req.request_id in prior_attempts:
                # Đọc DB trước khi chạy lại: yêu cầu này đã bị một worker trước bắt đầu rồi bị giết.
                found = lookup(raw, req) is not None
                rerun.write(f"{req.request_id} {'committed' if found else 'not_committed'}\n")
                rerun.flush()
            attempts.write(f"{req.request_id}\n")  # ghi TRƯỚC khi chạy
            attempts.flush()
            outcome = run_request(db, req)
            ack.write(f"{req.request_id} {outcome.status}\n")
            ack.flush()


def read_acks(path: Path) -> dict[str, str]:
    acks = {}
    for line in read_lines(path):
        parts = line.split()
        if len(parts) == 2:
            acks[parts[0]] = parts[1]
    return acks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("engine", choices=("mysql", "mongo", "tidb"))
    parser.add_argument("--requests", type=int, default=600)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--kill-every", type=float, default=1.0, help="giây trung bình giữa hai đợt giết")
    parser.add_argument("--kills-per-round", type=int, default=1, help="số worker bị giết mỗi đợt")
    parser.add_argument("--post-commit-delay-ms", type=float, default=0.0,
                        help="độ trễ nhân tạo SAU commit để kill rơi vào cửa sổ 'đã commit, chưa ack'")
    parser.add_argument("--idempotency-off", action="store_true", help="đối chứng âm: không UNIQUE, yêu cầu không idempotent")
    parser.add_argument("--inventory", type=int, default=30, help="tồn đầu nhỏ để có tình huống hết hàng thật")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--config", default="configs/smoke.toml")
    parser.add_argument("--out", help="thư mục ghi <engine>-kill[-idempotency-off].json")
    args = parser.parse_args()

    settings = read_settings(Path(args.config))
    dataset = dataclasses.replace(settings.dataset, inventory=args.inventory)
    target = endpoint(args.engine)
    run_id = uuid.uuid4().hex
    requests = build_requests(run_id, args.requests, dataset.items, args.seed, not args.idempotency_off)
    slices = [requests[i::args.workers] for i in range(args.workers)]
    ctx = mp.get_context("spawn")
    rng = random.Random(args.seed)
    kills = restarts = 0
    with project_lock():
        enforce_one(args.engine)
        db = open_adapter(target, admin=True)
        tmp = Path(tempfile.mkdtemp(prefix="fault-kill-"))
        try:
            db.create(idempotency=not args.idempotency_off)
            counts = load(db, dataset, settings.seed)
            acks = [tmp / f"ack-{i}.txt" for i in range(args.workers)]
            procs = [None] * args.workers
            started = time.monotonic()
            while time.monotonic() - started < args.timeout:
                complete = [len(read_acks(acks[i])) >= len(slices[i]) for i in range(args.workers)]
                if all(complete):
                    break
                for i in range(args.workers):
                    if not complete[i] and (procs[i] is None or not procs[i].is_alive()):
                        restarts += procs[i] is not None
                        procs[i] = ctx.Process(target=worker, args=(target, slices[i], str(acks[i]),
                                                                     args.post_commit_delay_ms))
                        procs[i].start()
                time.sleep(rng.uniform(0.5, 1.5) * args.kill_every)
                alive = [i for i in range(args.workers) if procs[i] is not None and procs[i].is_alive()]
                for victim in rng.sample(alive, min(args.kills_per_round, len(alive))):
                    procs[victim].kill()
                    procs[victim].join()
                    kills += 1
            else:
                raise SystemExit("Hết thời gian chờ: còn yêu cầu chưa được giải quyết")
            for proc in procs:
                if proc is not None:
                    proc.join(timeout=60)
            final = {}
            for path in acks:
                final.update(read_acks(path))
            success_orders = [r.request_id for r in requests if r.kind == "new_order" and final.get(r.request_id) == "success"]
            success_pay = [r.request_id for r in requests if r.kind == "payment" and final.get(r.request_id) == "success"]
            statuses: dict[str, int] = {}
            for status in final.values():
                statuses[status] = statuses.get(status, 0) + 1
            report = validate(db, dataset, run_id, success_orders)
            history_rows = db.count("history") - counts["history"]
            orders_rows = db.count("orders") - counts["orders"]
            doc_violations = db.doc_reconciliation(dataset.inventory, dataset.initial_orders)
            attempt_counts: dict[str, int] = {}
            rerun = {"committed": 0, "not_committed": 0}
            for path in acks:
                for line in read_lines(Path(str(path) + ".attempts")):
                    attempt_counts[line] = attempt_counts.get(line, 0) + 1
                for line in read_lines(Path(str(path) + ".rerun")):
                    rerun[line.split()[1]] += 1
            result = {
                "engine": args.engine, "run_id": run_id, "mode": "idempotency_off_control" if args.idempotency_off else "normal",
                "requests": len(requests), "workers": args.workers, "post_commit_delay_ms": args.post_commit_delay_ms,
                "kills": kills, "restarts": restarts, "statuses": statuses,
                "requests_reattempted_after_kill": sum(count > 1 for count in attempt_counts.values()),
                "rerun_found_committed": rerun["committed"], "rerun_not_committed": rerun["not_committed"],
                "orders_committed_in_db": orders_rows, "orders_acked_success": len(success_orders),
                "payments_in_db": history_rows, "payments_acked_success": len(success_pay),
                "duplicate_orders": max(orders_rows - len(success_orders), 0),
                "duplicate_payments": max(history_rows - len(success_pay), 0),
                "validation": report["status"], "rules": report["rules"], "doc_check_violations": len(doc_violations),
            }
            if args.idempotency_off:
                # Đối chứng âm: phải PHÁT HIỆN lỗi (đơn trùng, INVALID); không có thì bộ kiểm tra vô giá trị.
                result["passed"] = (report["status"] == "INVALID" and result["duplicate_orders"] + result["duplicate_payments"] > 0)
                result["meaning"] = "control detected duplicates" if result["passed"] else "CONTROL FAILED: no duplicate detected"
            else:
                # Đạt: ba luật VALID, đối soát của đề rỗng, số đơn/lịch sử trong DB bằng đúng số yêu cầu đã ack thành công
                # (không đơn ma, không đơn trùng), không yêu cầu nào kết thúc ở trạng thái commit chưa xác định.
                result["passed"] = (report["status"] == "VALID" and orders_rows == len(success_orders)
                                    and history_rows == len(success_pay) and not doc_violations
                                    and "unknown_commit" not in statuses)
                hits = result["rerun_found_committed"]
                result["rule_of_three_upper_bound_pct"] = round(300 / hits, 2) if hits and result["passed"] else None
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if args.out:
                out = Path(args.out)
                out.mkdir(parents=True, exist_ok=True)
                name = f"{args.engine}-kill{'-idempotency-off' if args.idempotency_off else ''}.json"
                (out / name).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            sys.exit(0 if result["passed"] else 1)
        finally:
            # Giao dịch của worker bị giết có thể còn giữ khóa tới khi server tự hủy (MongoDB: transactionLifetimeLimit 60 s).
            for attempt in range(5):
                try:
                    db.drop()
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt == 4:
                        print(f"CẢNH BÁO: chưa drop được {target.database}: {exc}", file=sys.stderr)
                    else:
                        time.sleep(20)
            db.close()


if __name__ == "__main__":
    main()
