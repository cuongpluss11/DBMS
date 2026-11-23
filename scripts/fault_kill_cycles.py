#!/usr/bin/env python3
"""Fault injection thật: giết tiến trình worker (SIGKILL/TerminateProcess) giữa lúc đang chạy giao dịch, khởi động
lại worker thay thế thử lại CÙNG request_id, rồi kiểm ba luật tồn kho (mục 2.2).

Khác `tests/test_fault_injection.py` (lớp bọc chèn lỗi có kiểm soát tại điểm xác định), script này giết tiến trình
ở thời điểm ngẫu nhiên nên bao phủ cả "chết trước commit", "chết sau commit trước khi nhận phản hồi" và "chết khi
đang retry". Mô hình lỗi: tiến trình ứng dụng chết, DBMS và mạng vẫn sống.

Mỗi worker xử lý một lát yêu cầu cố định; ack (request_id + kết quả) được ghi vào tệp SAU khi run_request trả về, nên
một yêu cầu đã commit nhưng chưa ack sẽ được worker thay thế thử lại và nhận ra bằng đối chiếu idempotency
(lookup) chứ không tạo đơn thứ hai.

Ví dụ (DBMS đã chạy, một hệ tại một thời điểm):
  python scripts/fault_kill_cycles.py mysql --requests 600 --workers 4 --out results/official/fault-injection
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
from flashsale.infra import enforce_one, endpoint, project_lock
from flashsale.validation.checks import validate
from flashsale.workload.generator import Request
from flashsale.workload.retry import run_request


def build_requests(run_id: str, count: int, items: int, seed: int) -> list[Request]:
    rng = random.Random(seed)
    requests = []
    for i in range(count):
        district, customer = rng.randint(1, 2), rng.randint(1, 10)
        if i % 2:
            requests.append(Request(f"{run_id}-k{i}", run_id, "payment", 1, district, customer, amount=rng.randint(100, 5000)))
        else:
            picked = rng.sample(range(1, items + 1), rng.randint(1, 3))
            requests.append(Request(f"{run_id}-k{i}", run_id, "new_order", 1, district, customer,
                                    tuple((item, rng.randint(1, 5)) for item in picked)))
    return requests


def worker(target, requests: list[Request], ack_path: str) -> None:
    db = open_adapter(target)
    done = set()
    path = Path(ack_path)
    if path.exists():
        done = {line.split()[0] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    with path.open("a", encoding="utf-8") as ack, Path(ack_path + ".attempts").open("a", encoding="utf-8") as attempts:
        for req in requests:
            if req.request_id in done:
                continue
            attempts.write(f"{req.request_id}\n")  # ghi TRƯỚC khi chạy: yêu cầu có ≥2 dòng = bị thử lại sau khi worker bị giết
            attempts.flush()
            outcome = run_request(db, req)
            ack.write(f"{req.request_id} {outcome.status}\n")
            ack.flush()


def read_acks(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    acks = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            acks[parts[0]] = parts[1]
    return acks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("engine", choices=("mysql", "mongo", "tidb"))
    parser.add_argument("--requests", type=int, default=600)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--kill-every", type=float, default=3.0, help="giây trung bình giữa hai lần giết (spawn Python mất ~1-2 s)")
    parser.add_argument("--inventory", type=int, default=30, help="tồn đầu nhỏ để có tình huống hết hàng thật")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--config", default="configs/smoke.toml")
    parser.add_argument("--out", help="thư mục ghi <engine>-kill.json")
    args = parser.parse_args()

    settings = read_settings(Path(args.config))
    dataset = dataclasses.replace(settings.dataset, inventory=args.inventory)
    target = endpoint(args.engine)
    run_id = uuid.uuid4().hex
    requests = build_requests(run_id, args.requests, dataset.items, args.seed)
    slices = [requests[i::args.workers] for i in range(args.workers)]
    ctx = mp.get_context("spawn")
    rng = random.Random(args.seed)
    kills = restarts = 0
    with project_lock():
        enforce_one(args.engine)
        db = open_adapter(target, admin=True)
        tmp = Path(tempfile.mkdtemp(prefix="fault-kill-"))
        try:
            db.create()
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
                        procs[i] = ctx.Process(target=worker, args=(target, slices[i], str(acks[i])))
                        procs[i].start()
                time.sleep(rng.uniform(0.5, 1.5) * args.kill_every)
                alive = [i for i in range(args.workers) if procs[i] is not None and procs[i].is_alive()]
                if alive:
                    victim = rng.choice(alive)
                    procs[victim].kill()
                    procs[victim].join()
                    kills += 1
            else:
                raise SystemExit("Hết thời gian chờ: còn yêu cầu chưa được giải quyết")
            for proc in procs:
                if proc is not None:
                    proc.join(timeout=30)
            final = {}
            for path in acks:
                final.update(read_acks(path))
            success_orders = [r.request_id for r in requests if r.kind == "new_order" and final.get(r.request_id) == "success"]
            success_pay = [r.request_id for r in requests if r.kind == "payment" and final.get(r.request_id) == "success"]
            statuses = {}
            for status in final.values():
                statuses[status] = statuses.get(status, 0) + 1
            report = validate(db, dataset, run_id, success_orders)
            history_rows = db.count("history") - counts["history"]
            orders_rows = db.count("orders") - counts["orders"]
            doc_violations = db.doc_reconciliation(dataset.inventory, dataset.initial_orders)
            result = {
                "engine": args.engine, "run_id": run_id, "requests": len(requests), "workers": args.workers,
                "kills": kills, "restarts": restarts, "statuses": statuses,
                "orders_committed_in_db": orders_rows, "orders_acked_success": len(success_orders),
                "payments_in_db": history_rows, "payments_acked_success": len(success_pay),
                "validation": report["status"], "rules": report["rules"], "doc_check_violations": len(doc_violations),
                "label": "fault-injection-docker-preliminary" if args.engine != "tidb" else "fault-injection",
            }
            attempt_counts: dict[str, int] = {}
            for path in acks:
                attempts_file = Path(str(path) + ".attempts")
                if attempts_file.exists():
                    for line in attempts_file.read_text(encoding="utf-8").splitlines():
                        attempt_counts[line] = attempt_counts.get(line, 0) + 1
            result["requests_reattempted_after_kill"] = sum(count > 1 for count in attempt_counts.values())
            # Đạt: ba luật VALID, đối soát của đề rỗng, số đơn/lịch sử trong DB khớp đúng số yêu cầu đã được xác nhận
            # thành công (không có đơn ma hay đơn trùng), và không có yêu cầu nào kết thúc ở trạng thái commit chưa xác định.
            ok = (report["status"] == "VALID" and orders_rows == len(success_orders) and history_rows == len(success_pay)
                  and not doc_violations and "unknown_commit" not in statuses)
            result["passed"] = ok
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if args.out:
                out = Path(args.out)
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{args.engine}-kill.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            sys.exit(0 if ok else 1)
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
