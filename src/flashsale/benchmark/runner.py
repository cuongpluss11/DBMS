from contextlib import suppress
from dataclasses import asdict, replace
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
from flashsale.config import Settings, uses_migration, uses_slots
from flashsale.data.loader import prepare_slots
from flashsale.infra import cpu_sampler, setting
from flashsale.migration import load_item_prices, migrate_background, prepare_migration
from flashsale.validation.checks import validate
from flashsale.workload.generator import Generator, Zipf
from flashsale.transactions.core import TxnContext
from flashsale.workload.retry import Outcome, run_request
from flashsale.workload.throttle import ABORT_CATEGORIES, ArrivalFeed, SharedThrottle, control_loop
from .metrics import Phase, SCHEMA_VERSION, warmup_stability, write_json, write_result, write_series


def make_context(cfg: Settings, zipf: Zipf, repetition: int, worker: int,
                 item_prices: dict[int, int] | None = None) -> TxnContext | None:
    """None = đường chạy của 2.1 (legacy, không cấp mã theo lô, không migration): giữ nguyên hành vi và số đo cũ."""
    from random import Random

    ctx = TxnContext(cfg.variant, cfg.slots,
                     frozenset(zipf.item_ids[:cfg.hot_items]) if uses_slots(cfg.variant) else frozenset(),
                     cfg.order_id_batch, rng=Random(f"{cfg.seed}:{repetition}:{worker}:slots"),
                     migration_strategy=cfg.migration_strategy, item_prices=item_prices or {})
    return None if ctx.is_2_1 else ctx


def is_hot(req, ctx: TxnContext | None) -> bool:
    """Giao dịch đặt hàng chạm ít nhất một món nóng (đối tượng của bộ điều tiết P3)."""
    return bool(ctx and ctx.hot_items and req.kind == "new_order"
                and any(item in ctx.hot_items for item, _ in req.items))


def client(endpoint: Endpoint, cfg: Settings, zipf: Zipf, run_id: str, repetition: int,
           worker: int, barrier, deadlines, throttle=None, feeds=None,
           item_prices: dict[int, int] | None = None) -> tuple[Phase, Phase]:
    from random import Random

    db = None
    try:
        db = open_adapter(endpoint, timeout=cfg.client_timeout_seconds)
        jitter = Random(f"{cfg.seed}:{repetition}:{worker}:jitter") if cfg.jitter else None
        ctx = make_context(cfg, zipf, repetition, worker, item_prices=item_prices)
        phases = []
        for i, name in enumerate(("warmup", "measurement")):
            phase = Phase()
            seconds = cfg.warmup_seconds if i == 0 else cfg.measurement_seconds
            feed = feeds[i] if feeds else None
            gen = None if feed else Generator(cfg, zipf, run_id, repetition, worker, name)
            barrier.wait()
            barrier.wait()
            deadline = deadlines[i]
            start = deadline - seconds
            if feed:
                feed.start(start, deadline)
            attempts, items = (ctx.slot_attempts, ctx.slot_items) if ctx else (0, 0)
            on_demand, mig_conflicts = (ctx.migrated_on_demand, ctx.migration_conflicts) if ctx else (0, 0)
            while time.monotonic() < deadline:
                if feed:
                    item = feed.get(deadline)
                    if item is None:
                        break
                    req, arrival = item
                else:
                    req, arrival = gen.next(), time.monotonic()
                hot = throttle is not None and is_hot(req, ctx)
                if hot:
                    throttle.acquire()
                began = time.monotonic()
                try:
                    outcome = run_request(db, req, jitter=jitter, ctx=ctx)
                finally:
                    if hot:
                        throttle.release()
                now = time.monotonic()
                if hot:  # bộ điều khiển dùng độ trễ dịch vụ (không gồm hàng đợi) để không tự khuếch đại việc chờ
                    throttle.observe(outcome.latency_ms, any(outcome.errors.get(c) for c in ABORT_CATEGORIES))
                wait = None
                if feed or throttle is not None:
                    # Độ trễ tính từ lúc yêu cầu đến, gồm hàng đợi ứng dụng và cổng điều tiết (đề, mục 2.2).
                    wait = (began - arrival) * 1000
                    outcome = replace(outcome, latency_ms=(now - arrival) * 1000)
                phase.record(req, outcome, now <= deadline, int(now - start), wait,
                             bool(ctx and ctx.last_read_migrated))
            if ctx:
                phase.slot_attempts, phase.slot_items = ctx.slot_attempts - attempts, ctx.slot_items - items
                phase.migrated_on_demand = ctx.migrated_on_demand - on_demand
                phase.migration_conflicts = ctx.migration_conflicts - mig_conflicts
            phases.append(phase)
            barrier.wait()
        return phases[0], phases[1]
    except BaseException:
        barrier.abort()
        raise
    finally:
        if db is not None:
            db.close()


def group(endpoint, cfg, run_id, repetition, workers, barrier, deadlines, output, throttle=None) -> None:
    try:
        zipf = Zipf(cfg.dataset.items, cfg.theta, cfg.seed, cfg.hot_item)
        warmup, measurement = Phase(), Phase()
        item_prices = None
        if uses_migration(cfg.migration_strategy) or cfg.old_order_read_pct > 0:
            price_db = open_adapter(endpoint, timeout=max(cfg.client_timeout_seconds, 120.0))
            try:
                item_prices = load_item_prices(price_db)
            finally:
                price_db.close()
        feeds = None
        if cfg.arrival_rate > 0:
            # Một bộ phát yêu cầu mỗi process và phase; phần tốc độ đến tỉ lệ với số client của process.
            rate = cfg.arrival_rate * len(workers) / cfg.concurrency
            feeds = [ArrivalFeed(Generator(cfg, zipf, run_id, repetition, workers[0], name), rate, cfg.queue_size)
                     for name in ("warmup", "measurement")]
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            results = [executor.submit(client, endpoint, cfg, zipf, run_id, repetition,
                                       index, barrier, deadlines, throttle, feeds, item_prices) for index in workers]
            for result in results:
                warm, measured = result.result()
                warmup.merge(warm)
                measurement.merge(measured)
        for feed, phase in zip(feeds or (), (warmup, measurement)):
            for req, arrival in feed.rejected:
                phase.record(req, Outcome("busy", 0, {"busy": 1}, 0.0), True, int(arrival - feed.start_time))
            phase.unserved += feed.queue.qsize()
        output.put((warmup, measurement, None))
    except BaseException:
        output.put((None, None, traceback.format_exc()))
        barrier.abort()


def sample_cpu(limits: dict, deadline: float, stop: Event, samples: dict[str, list[float]]) -> None:
    sample_once = cpu_sampler(limits)
    while time.monotonic() < deadline and not stop.is_set():
        try:
            sample = sample_once()
            if time.monotonic() <= deadline:
                for name, value in sample.items():
                    samples.setdefault(name, []).append(value)
        except Exception as exc:
            logging.warning("CPU unavailable: %s", exc)
        stop.wait(4)


def get_counters(db: Adapter) -> dict:
    try:
        return db.counters()
    except Exception as exc:
        logging.warning("DBMS counters unavailable: %s", exc)
        return {"lock_wait_ms": None, "server_deadlocks": None}


def phases(endpoint: Endpoint, cfg: Settings, db: Adapter, run_id: str,
           repetition: int, limits: dict) -> tuple[Phase, Phase, dict, dict, dict | None, dict | None]:
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(cfg.concurrency + 1, timeout=120)
    deadlines = ctx.Array("d", 2, lock=False)
    queue = ctx.Queue()
    processes = []
    samples: dict[str, list[float]] = {name: [] for name in limits}
    stop = Event()
    sampler = None
    controller = None
    mig_thread = None
    mig_box: dict = {"result": None, "error": None}
    # P3: một bộ điều tiết dùng chung mọi process; bộ điều khiển chạy ở process này, mỗi giây một bước.
    throttle = (SharedThrottle(ctx, cfg.concurrency, cfg.limit_min, cfg.concurrency, cfg.p99_limit_ms,
                               cfg.abort_limit_pct) if cfg.variant == "p3" else None)
    trace: list[dict] = []

    def run_migration_worker(measure_start: float, measure_deadline: float) -> None:
        mig_db = None
        try:
            mig_db = open_adapter(endpoint, timeout=max(cfg.client_timeout_seconds, 600.0))
            mig_box["result"] = migrate_background(
                mig_db, cfg, measure_start=measure_start, deadline=measure_deadline, stop=stop
            )
        except BaseException as exc:
            mig_box["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if mig_db is not None:
                mig_db.close()

    try:
        for first in range(0, cfg.concurrency, cfg.workers_per_process):
            workers = range(first, min(cfg.concurrency, first + cfg.workers_per_process))
            process = ctx.Process(target=group, args=(endpoint, cfg, run_id, repetition, workers,
                                                       barrier, deadlines, queue, throttle))
            process.start()
            processes.append(process)
        # First rendezvous waits for all clients to be online before starting its timer.
        # The second rendezvous publishes the deadline to all clients.
        start_phase(barrier, deadlines, 0, cfg.warmup_seconds)
        if throttle is not None:
            controller = Thread(target=control_loop, args=(throttle, stop, trace), daemon=True)
            controller.start()
        barrier.wait(timeout=cfg.warmup_seconds + 120)
        initial = get_counters(db)
        start_phase(barrier, deadlines, 1, cfg.measurement_seconds)
        if uses_migration(cfg.migration_strategy):
            mig_thread = Thread(
                target=run_migration_worker,
                args=(deadlines[1] - cfg.measurement_seconds, deadlines[1]),
                daemon=True,
            )
            mig_thread.start()
        sampler = Thread(target=sample_cpu, args=(limits, deadlines[1], stop, samples), daemon=True)
        sampler.start()
        barrier.wait(timeout=cfg.measurement_seconds + 120)
        if mig_thread is not None:
            mig_thread.join(timeout=600)
            if mig_box["error"]:
                raise RuntimeError(f"migration_worker_failed: {mig_box['error']}")
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
        for name in limits:
            cpu.setdefault(name, None)
        summary = None
        if throttle is not None:
            limits_seen = [step["limit_after"] for step in trace] or [throttle.limit.value]
            summary = {"initial_limit": cfg.concurrency, "final_limit": throttle.limit.value,
                       "min_limit": min(limits_seen), "adjustments": sum(
                           step["limit_after"] != step["limit_before"] for step in trace), "trace": trace}
        mig_result = mig_box["result"]
        if mig_result is not None:
            mig_result["migrated_on_demand"] = measurement.migrated_on_demand
            mig_result["client_conflicts"] = measurement.migration_conflicts
            mig_result["migration_conflicts"] = (
                mig_result.get("background_conflicts", 0) + measurement.migration_conflicts
            )
        return warmup, measurement, counters, cpu, summary, mig_result
    except Exception as exc:
        with suppress(Empty):
            _, _, error = queue.get(timeout=2)
            if error:
                raise RuntimeError(error) from exc
        raise RuntimeError(f"Runner gián đoạn: {exc!r}") from exc
    finally:
        stop.set()
        if mig_thread is not None:
            mig_thread.join(timeout=5)
        if controller is not None:
            controller.join(timeout=3)
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
    tps_series = None
    p99_series = None
    migration_result = None
    variant_setup = {"variant": cfg.variant, "slots": cfg.slots if uses_slots(cfg.variant) else None,
                     "hot_items": cfg.hot_items if uses_slots(cfg.variant) else None,
                     "order_id_batch": cfg.order_id_batch, "arrival_rate": cfg.arrival_rate,
                     "queue_size": cfg.queue_size if cfg.arrival_rate else None,
                     "throttle": ({"p99_limit_ms": cfg.p99_limit_ms, "abort_limit_pct": cfg.abort_limit_pct,
                                   "limit_min": cfg.limit_min, "limit_max": cfg.concurrency}
                                  if cfg.variant == "p3" else None), "prepare_seconds": None}
    throttle_summary = None
    if evidence["indexed"] and uses_slots(cfg.variant):
        began = time.monotonic()
        try:
            variant_setup.update(prepare_slots(db, cfg.dataset, zipf.item_ids[:cfg.hot_items], cfg.slots))
            variant_setup["prepare_seconds"] = time.monotonic() - began
        except Exception as exc:
            evidence = {**evidence, "indexed": False}
            protocol_errors.append(f"slot_prepare_failed: {type(exc).__name__}: {exc}")
    if evidence["indexed"] and uses_migration(cfg.migration_strategy):
        began = time.monotonic()
        try:
            variant_setup["migration_prepare"] = prepare_migration(db, cfg.dataset)
            variant_setup["migration_prepare_seconds"] = time.monotonic() - began
        except Exception as exc:
            evidence = {**evidence, "indexed": False}
            protocol_errors.append(f"migration_prepare_failed: {type(exc).__name__}: {exc}")
    if evidence["indexed"]:
        try:
            warm, measured, counters, cpu, throttle_summary, migration_result = phases(
                endpoint, cfg, db, run_id, repetition, limits
            )
        except Exception as exc:
            protocol_errors.append(f"runner_failed: {type(exc).__name__}: {exc}")
        else:
            warmup = warm.summary(cfg.warmup_seconds)
            measurement = measured.summary(cfg.measurement_seconds)
            expected = sorted(warm.successful_orders + measured.successful_orders)
            tps_series = {"warmup": warm.series_list(cfg.warmup_seconds),
                          "measurement": measured.series_list(cfg.measurement_seconds)}
            p99_series = {"warmup": warm.p99_series_list(cfg.warmup_seconds),
                          "measurement": measured.p99_series_list(cfg.measurement_seconds)}
            if uses_migration(cfg.migration_strategy):
                mig_win = ((migration_result or {}).get("start_second"), (migration_result or {}).get("end_second"))
                write_series(directory / "tps_per_second.csv", tps_series, p99_series, mig_win)
            else:
                write_series(directory / "tps_per_second.csv", tps_series)
            write_json(directory / "successful_new_orders.json", expected)
            if cfg.label in {"correctness", "smoke"} and not uses_migration(cfg.migration_strategy) and (
                    warm.out_of_stock_all + measured.out_of_stock_all == 0):
                protocol_errors.append("out_of_stock_not_observed")
            if measured.successes.total() == 0:
                protocol_errors.append("no_success_in_measurement")
            if warm.unknown_commits + measured.unknown_commits:
                protocol_errors.append("unresolved_commit")
    elif not protocol_errors:
        protocol_errors.append("indexed_access_not_confirmed")
    validation = {"status": "INVALID", "rules": dict.fromkeys(
        ("nonnegative", "reconciliation", "idempotency")), "errors": {}, "committed_orders": None}
    # With an incomplete client log, stock rules can still be checked and
    # unexpected DB rows retained as evidence. Exact client reconciliation is unavailable.
    if evidence["indexed"]:
        try:
            validation = validate(db, cfg.dataset, run_id, expected or (), dataset_state["counts"],
                                  slots=uses_slots(cfg.variant),
                                  migration=uses_migration(cfg.migration_strategy))
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
        "seed": cfg.seed, "idempotency": cfg.idempotency, "variant": cfg.variant, "slots": variant_setup["slots"],
        "hot_items": variant_setup["hot_items"], "order_id_batch": cfg.order_id_batch, "arrival_rate": cfg.arrival_rate,
        "migration_strategy": cfg.migration_strategy, "old_order_read_pct": cfg.old_order_read_pct,
        "migration": migration_result,
        "throttle_result": throttle_summary, "variant_setup": variant_setup,
        "client_timeout_seconds": cfg.client_timeout_seconds, "concurrency": cfg.concurrency, "warehouse_mode": cfg.warehouse_mode,
        "theta": cfg.theta, "hot_item": cfg.hot_item,
        "inventory_mode": "performance" if cfg.dataset.inventory == 1_000_000_000 else cfg.label,
        "resource_limits": {"cpus": sum(item["cpus"] for item in limits.values()),
                            "memory_bytes": sum(item["memory_bytes"] for item in limits.values())},
        "theoretical_selection": zipf.theoretical(),
        "warmup": warmup, "measurement": measurement,
        **counters, "container_cpu_pct": {name: cpu.get(name) for name in limits},
        "loadgen_cpu_pct": cpu.get("loadgen"),
        "resource_warnings": cpu_warnings(cpu, limits) + loadgen_warnings(cpu.get("loadgen")),
        "validation": validation,
        "tps_series": tps_series,
        "p99_series": p99_series,
        "warmup_stability": warmup_stability(**tps_series) if tps_series else None,
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


def loadgen_warnings(value: float | None) -> list[str]:
    """Máy tải (remote) trên ~80% tổng CPU của nó nghĩa là script tải là nút thắt: tăng cỡ VM hoặc chạy nhiều VM tải."""
    cpus = float(setting("FLASHSALE_LOADGEN_CPUS", "0") or 0)
    if value is None or cpus <= 0:
        return []
    utilization = value / (100 * cpus) * 100
    return [f"loadgen_cpu_{utilization:.0f}pct_of_limit"] if utilization > SQL_TIER_CPU_LIMIT_PCT else []


def unavailable_phase(seconds: float) -> dict:
    empty = Phase().summary(seconds)
    return {**dict.fromkeys(empty), "seconds": seconds}
