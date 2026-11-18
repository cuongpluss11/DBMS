from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timezone
import logging
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty
import statistics
from threading import Event, Thread
import time
import traceback
from uuid import uuid4

from flashsale.adapters.base import Adapter, Endpoint, open_adapter
from flashsale.config import Settings
from flashsale.infra import docker_cpu
from flashsale.validation.checks import validate
from flashsale.workload.generator import Generator, Zipf
from flashsale.workload.retry import run_request
from .metrics import Phase, SCHEMA_VERSION, write_json, write_result


def client(endpoint: Endpoint, cfg: Settings, zipf: Zipf, run_id: str, repetition: int,
           worker: int, barrier, deadlines) -> tuple[Phase, Phase]:
    from random import Random

    db = None
    try:
        db = open_adapter(endpoint, timeout=cfg.client_timeout_seconds)
        jitter = Random(f"{cfg.seed}:{repetition}:{worker}:jitter") if cfg.jitter else None
        phases = []
        for i, name in enumerate(("warmup", "measurement")):
            phase = Phase()
            gen = Generator(cfg, zipf, run_id, repetition, worker, name)
            barrier.wait()
            barrier.wait()
            deadline = deadlines[i]
            while time.monotonic() < deadline:
                req = gen.next()
                outcome = run_request(db, req, jitter=jitter)
                phase.record(req, outcome, time.monotonic() <= deadline)
            phases.append(phase)
            barrier.wait()
        return phases[0], phases[1]
    except BaseException:
        barrier.abort()
        raise
    finally:
        if db is not None:
            db.close()


def group(endpoint, cfg, run_id, repetition, workers, barrier, deadlines, output) -> None:
    try:
        zipf = Zipf(cfg.dataset.items, cfg.theta, cfg.seed, cfg.hot_item)
        warmup, measurement = Phase(), Phase()
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            results = [executor.submit(client, endpoint, cfg, zipf, run_id, repetition,
                                       index, barrier, deadlines) for index in workers]
            for result in results:
                warm, measured = result.result()
                warmup.merge(warm)
                measurement.merge(measured)
        output.put((warmup, measurement, None))
    except BaseException:
        output.put((None, None, traceback.format_exc()))
        barrier.abort()


def sample_cpu(limits: dict, deadline: float, stop: Event, samples: dict[str, list[float]]) -> None:
    while time.monotonic() < deadline and not stop.is_set():
        try:
            sample = docker_cpu(limits)
            if time.monotonic() <= deadline:
                for name, value in sample.items():
                    samples[name].append(value)
        except Exception as exc:
            logging.warning("CPU Docker unavailable: %s", exc)
        stop.wait(4)


def get_counters(db: Adapter) -> dict:
    try:
        return db.counters()
    except Exception as exc:
        logging.warning("DBMS counters unavailable: %s", exc)
        return {"lock_wait_ms": None, "server_deadlocks": None}


def phases(endpoint: Endpoint, cfg: Settings, db: Adapter, run_id: str,
           repetition: int, limits: dict) -> tuple[Phase, Phase, dict, dict]:
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(cfg.concurrency + 1, timeout=120)
    deadlines = ctx.Array("d", 2, lock=False)
    queue = ctx.Queue()
    processes = []
    samples: dict[str, list[float]] = {name: [] for name in limits}
    stop = Event()
    sampler = None
    try:
        for first in range(0, cfg.concurrency, cfg.workers_per_process):
            workers = range(first, min(cfg.concurrency, first + cfg.workers_per_process))
            process = ctx.Process(target=group, args=(endpoint, cfg, run_id, repetition, workers,
                                                       barrier, deadlines, queue))
            process.start()
            processes.append(process)
        # First rendezvous waits for all clients to be online before starting its timer.
        # The second rendezvous publishes the deadline to all clients.
        start_phase(barrier, deadlines, 0, cfg.warmup_seconds)
        barrier.wait(timeout=cfg.warmup_seconds + 120)
        initial = get_counters(db)
        start_phase(barrier, deadlines, 1, cfg.measurement_seconds)
        sampler = Thread(target=sample_cpu, args=(limits, deadlines[1], stop, samples), daemon=True)
        sampler.start()
        barrier.wait(timeout=cfg.measurement_seconds + 120)
        final = get_counters(db)
        stop.set()
        warmup, measurement = Phase(), Phase()
        for _ in processes:
            warm, measured, error = queue.get(timeout=60)
            if error:
                raise RuntimeError(error)
            warmup.merge(warm)
            measurement.merge(measured)
        counters = {name: (final[name] - value if value is not None and final[name] is not None
                           and final[name] >= value else None) for name, value in initial.items()}
        cpu = {name: statistics.mean(values) if values else None for name, values in samples.items()}
        return warmup, measurement, counters, cpu
    except Exception as exc:
        with suppress(Empty):
            _, _, error = queue.get(timeout=2)
            if error:
                raise RuntimeError(error) from exc
        raise RuntimeError(f"Runner gián đoạn: {exc!r}") from exc
    finally:
        stop.set()
        if sampler is not None:
            sampler.join(timeout=9)
        for process in processes:
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        queue.close()


def start_phase(barrier, deadlines, index: int, seconds: float) -> None:
    barrier.wait()
    deadlines[index] = time.monotonic() + seconds
    barrier.wait()


def run_one(endpoint: Endpoint, cfg: Settings, db: Adapter, repetition: int, output: Path,
            environment: dict, limits: dict, config_name: str, dataset_state: dict) -> dict:
    run_id = uuid4().hex
    directory = output / run_id
    directory.mkdir(parents=True)
    logging.info("Bắt đầu %s repetition=%s run_id=%s", endpoint.engine, repetition, run_id)
    zipf = Zipf(cfg.dataset.items, cfg.theta, cfg.seed, cfg.hot_item)
    server = db.ping(cfg.concurrency)
    try:
        evidence = db.evidence(zipf.item_ids[0])
    except Exception as exc:
        evidence = {"indexed": None, "error": f"{type(exc).__name__}: {exc}"}
    manifest = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "engine": endpoint.engine,
        "database": endpoint.database, "started_utc": datetime.now(timezone.utc).isoformat(),
        "repetition": repetition, "config_path": config_name, "config": asdict(cfg),
        "dataset_state": dataset_state, "environment": environment, "dbms": server,
        "containers": limits, "access_paths": evidence, "hot_item_id": zipf.item_ids[0],
    }
    write_json(directory / "manifest.json", manifest)
    protocol_errors = []
    counters = {"lock_wait_ms": None, "server_deadlocks": None}
    cpu = {name: None for name in limits}
    warmup = unavailable_phase(cfg.warmup_seconds)
    measurement = unavailable_phase(cfg.measurement_seconds)
    expected = None
    if evidence["indexed"]:
        try:
            warm, measured, counters, cpu = phases(endpoint, cfg, db, run_id, repetition, limits)
        except Exception as exc:
            protocol_errors.append(f"runner_failed: {type(exc).__name__}: {exc}")
        else:
            warmup = warm.summary(cfg.warmup_seconds)
            measurement = measured.summary(cfg.measurement_seconds)
            expected = sorted(warm.successful_orders + measured.successful_orders)
            write_json(directory / "successful_new_orders.json", expected)
            if cfg.label in {"correctness", "smoke"} and warm.out_of_stock_all + measured.out_of_stock_all == 0:
                protocol_errors.append("out_of_stock_not_observed")
            if measured.successes.total() == 0:
                protocol_errors.append("no_success_in_measurement")
            if warm.unknown_commits + measured.unknown_commits:
                protocol_errors.append("unresolved_commit")
    else:
        protocol_errors.append("indexed_access_not_confirmed")
    validation = {"status": "INVALID", "rules": dict.fromkeys(
        ("nonnegative", "reconciliation", "idempotency")), "errors": {}, "committed_orders": None}
    # With an incomplete client log, stock rules can still be checked and
    # unexpected DB rows retained as evidence. Exact client reconciliation is unavailable.
    if evidence["indexed"]:
        try:
            validation = validate(db, cfg.dataset, run_id, expected or (), dataset_state["counts"])
            if expected is None:
                validation["rules"]["idempotency"] = None
        except Exception as exc:
            protocol_errors.append(f"validation_failed: {type(exc).__name__}: {exc}")
    if protocol_errors:
        validation["status"] = "INVALID"
        logging.error("run_id=%s lỗi giao thức: %s", run_id, "; ".join(protocol_errors))
    validation["protocol_errors"] = protocol_errors
    result = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "engine": endpoint.engine,
        "version": server["version"], "label": cfg.label, "repetition": repetition,
        "seed": cfg.seed, "idempotency": cfg.idempotency,
        "client_timeout_seconds": cfg.client_timeout_seconds, "concurrency": cfg.concurrency, "warehouse_mode": cfg.warehouse_mode,
        "theta": cfg.theta, "hot_item": cfg.hot_item,
        "inventory_mode": "performance" if cfg.dataset.inventory == 1_000_000_000 else cfg.label,
        "resource_limits": {"cpus": sum(item["cpus"] for item in limits.values()),
                            "memory_bytes": sum(item["memory_bytes"] for item in limits.values())},
        "theoretical_selection": zipf.theoretical(),
        "warmup": warmup, "measurement": measurement,
        **counters, "container_cpu_pct": cpu, "resource_warnings": cpu_warnings(cpu, limits),
        "validation": validation,
    }
    write_result(directory, result)
    return result


SQL_TIER_CPU_LIMIT_PCT = 80


def cpu_warnings(cpu: dict, limits: dict) -> list[str]:
    """Cảnh báo khi tầng SQL/PD (không phải TiKV) vượt 80% giới hạn CPU: kết quả TPS của lượt đó
    phản ánh nút thắt của tầng SQL chứ không phải của lưu trữ. Docker: 100% = một lõi."""
    warnings = []
    for name in ("tidb", "pd"):
        value = cpu.get(name)
        if value is None or name not in limits or not limits[name]["cpus"]:
            continue
        utilization = 100 * value / (100 * limits[name]["cpus"])
        if utilization > SQL_TIER_CPU_LIMIT_PCT:
            warnings.append(f"{name}_cpu_{utilization:.0f}pct_of_limit")
    return warnings


def unavailable_phase(seconds: float) -> dict:
    empty = Phase().summary(seconds)
    return {**dict.fromkeys(empty), "seconds": seconds}
