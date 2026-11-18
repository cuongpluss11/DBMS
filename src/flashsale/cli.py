import argparse
from contextlib import contextmanager
from dataclasses import replace
import json
import logging
from pathlib import Path
import subprocess
import sys

from flashsale.adapters.base import Endpoint, open_adapter
from flashsale.benchmark.metrics import write_json
from flashsale.benchmark.runner import run_one
from flashsale.config import Settings, read_settings
from flashsale.data.loader import fingerprint, load, reset
from flashsale.infra import (ENGINES, ROOT, active_engines, container_limits, endpoint, enforce_one,
                            host_info, pd_status, project_lock, ready, source_hashes, start, stop)
from flashsale.validation.checks import validate

RESULTS = ROOT / "results"


@contextmanager
def connect(target: Endpoint, *, admin: bool = False):
    db = open_adapter(target, admin=admin)
    try:
        yield db
    finally:
        db.close()


def state_path(target: Endpoint) -> Path:
    return RESULTS / "datasets" / f"{target.engine}-{target.database}.json"


def load_dataset(target: Endpoint, cfg: Settings) -> dict:
    path = state_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {"engine": target.engine, "database": target.database,
             "fingerprint": fingerprint(cfg.dataset, cfg.seed), "status": "loading"}
    write_json(path, state)
    with connect(target, admin=True) as db:
        db.create()
        state["counts"] = load(db, cfg.dataset, cfg.seed)
    state["status"] = "ready"
    write_json(path, state)
    return state


def dataset_state(target: Endpoint, cfg: Settings) -> dict:
    path = state_path(target)
    if not path.is_file():
        raise ValueError("Dataset chưa được đăng ký bằng lệnh load của dự án")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state["fingerprint"] != fingerprint(cfg.dataset, cfg.seed):
        raise ValueError("Dataset hoặc seed của config khác lúc load")
    if "counts" not in state:
        raise ValueError("Dataset chưa nạp xong, hãy tạo dataset mới")
    return state


def restore(target: Endpoint, cfg: Settings, state: dict) -> dict:
    path = state_path(target)
    state = {**state, "status": "resetting"}
    write_json(path, state)
    with connect(target) as db:
        reset(db, cfg.dataset)
    state["status"] = "ready"
    write_json(path, state)
    return state


def assert_baseline(db, cfg: Settings, state: dict) -> None:
    if state["status"] != "ready":
        raise RuntimeError("Dataset đã sử dụng, cần reset có xác nhận trước khi chạy")
    counts = {table: db.count(table) for table in state["counts"]}
    if counts != state["counts"]:
        raise RuntimeError(f"Dataset khác số dòng sau load: {counts}")
    report = validate(db, cfg.dataset, "", [])
    if report["status"] != "VALID":
        raise RuntimeError("Dataset khác tồn đầu hoặc có dòng benchmark trước khi đo")


def run(target: Endpoint, cfg: Settings, config_path: Path, *, reset_between: bool) -> list[dict]:
    if cfg.repetitions > 1 and not reset_between:
        raise ValueError("Thêm --reset-between để cho phép khôi phục dataset giữa các lần lặp")
    if cfg.label == "baseline" and (target.engine != "mysql" or cfg.theta != 0 or cfg.hot_item):
        raise ValueError("Baseline dùng MySQL, theta=0 và tắt hot_item")
    state = dataset_state(target, cfg)
    environment = host_info()
    environment["source_sha256"] = source_hashes()
    if target.engine == "tidb":
        environment["pd"] = pd_status()
    limits = container_limits(target.engine)
    if environment["docker_cpu_count"] < 4 or environment["docker_memory_bytes"] < 6 * 1024 ** 3:
        raise RuntimeError("Docker cần ít nhất 4 CPU và 6 GiB RAM cho ngân sách container")
    reports = []
    for repetition in range(1, cfg.repetitions + 1):
        if repetition > 1:
            state = restore(target, cfg, state)
        with connect(target) as db:
            assert_baseline(db, cfg, state)
            db.ping(cfg.concurrency)
            write_json(state_path(target), {**state, "status": "dirty"})
            reports.append(run_one(target, cfg, db, repetition, RESULTS, environment,
                                   limits, str(config_path), state))
            if reports[-1]["validation"]["status"] == "INVALID":
                break
    return reports


def project_smoke(engine: str, cfg: Settings, config: Path, *, manage: bool) -> list[dict]:
    if cfg.label != "smoke" or cfg.repetitions != 1:
        raise ValueError("Lệnh smoke yêu cầu cấu hình smoke với đúng một lần lặp")
    target = endpoint(engine)
    was_running = bool(active_engines()[engine])
    try:
        if manage and not was_running:
            start(engine)
        enforce_one(engine)
        try:
            load_dataset(target, cfg)
            return run(target, cfg, config, reset_between=False)
        finally:
            if state_path(target).is_file():
                with connect(target, admin=True) as db:
                    db.drop()
                state_path(target).unlink()
    finally:
        if manage and not was_running:
            stop(engine)


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="flashsale")
    commands = cli.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup")
    setup.add_argument("--smoke-all", action="store_true")
    commands.add_parser("doctor")
    for name in ("start", "stop", "status", "load", "reset", "run", "benchmark", "validate", "smoke", "drop"):
        command = commands.add_parser(name)
        command.add_argument("engine", choices=ENGINES)
        if name in {"load", "reset", "run", "benchmark", "smoke"}:
            command.add_argument("--config", type=Path, default=ROOT / "configs" /
                                 ("smoke.toml" if name == "smoke" else "baseline.toml"))
        if name in {"reset", "run", "benchmark", "drop"}:
            command.add_argument("--dataset", required=True)
        if name in {"reset", "drop"}:
            command.add_argument("--confirm", required=True)
        if name in {"run", "benchmark"}:
            command.add_argument("--reset-between", action="store_true")
            command.add_argument("--concurrency", type=int)
            command.add_argument("--warehouse-mode", choices=("uniform", "single-warehouse"))
            command.add_argument("--repetitions", type=int)
        if name == "validate":
            command.add_argument("--run-id", required=True)
        if name == "smoke":
            command.add_argument("--start", action="store_true")
    return cli


def execute_command(args) -> dict | list:
    command = args.command
    if command == "doctor":
        return {"environment": host_info(), "running": active_engines()}
    engine = args.engine
    if command == "start":
        return start(engine)
    if command == "stop":
        stop(engine)
        return {"status": "stopped"}
    if command == "status":
        return ready(engine, timeout=0) if active_engines()[engine] else {"status": "stopped"}
    if command == "smoke":
        return project_smoke(engine, read_settings(args.config), args.config, manage=args.start)
    enforce_one(engine)
    if command == "validate":
        from uuid import UUID
        if UUID(hex=args.run_id).hex != args.run_id:
            raise ValueError("run_id phải là UUID hex")
        folder = RESULTS / args.run_id
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["engine"] != engine:
            raise ValueError("DBMS khác manifest")
        from flashsale.config import Dataset
        target = endpoint(engine, manifest["database"])
        expected = json.loads((folder / "successful_new_orders.json").read_text(encoding="utf-8"))
        with connect(target) as db:
            return validate(db, Dataset(**manifest["config"]["dataset"]), args.run_id, expected,
                            manifest["dataset_state"]["counts"])

    target = endpoint(engine, getattr(args, "dataset", None))
    if command in {"reset", "drop"} and target.database != args.confirm:
        raise ValueError("--confirm phải khớp tên dataset Flash-sale")
    if command == "drop":
        if not state_path(target).is_file():
            raise ValueError("Dataset không thuộc registry của dự án")
        with connect(target, admin=True) as db:
            db.drop()
        state_path(target).unlink()
        return {"status": "dropped", "database": target.database}
    cfg = read_settings(args.config)
    if command == "load":
        return load_dataset(target, cfg)
    if command == "reset":
        return restore(target, cfg, dataset_state(target, cfg))
    cfg = replace(cfg, **{name: getattr(args, name) for name in ("concurrency", "warehouse_mode", "repetitions")
                          if getattr(args, name) is not None})
    return run(target, cfg, args.config, reset_between=args.reset_between)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parser().parse_args()
    if args.command == "setup":
        return subprocess.call(["bash", str(ROOT / "scripts" / "setup.sh"),
                                *(["--smoke-all"] if args.smoke_all else [])], cwd=ROOT)
    try:
        with project_lock():
            result = execute_command(args)
        print(json.dumps(result, indent=2, default=str))
        results = result if isinstance(result, list) else [result]
        return int(any(item.get("status") == "INVALID" or item.get("validation", {}).get("status") == "INVALID"
                       for item in results))
    except Exception as exc:
        logging.error("%s: %s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
