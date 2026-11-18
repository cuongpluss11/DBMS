from collections import Counter
import csv
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

from flashsale.workload.generator import Request
from flashsale.workload.retry import ERRORS, Outcome

SCHEMA_VERSION = 1


def percentile(sorted_values: list[float], pct: int) -> float | None:
    if not sorted_values:
        return None
    return sorted_values[max(0, math.ceil(len(sorted_values) * pct / 100) - 1)]


@dataclass
class Phase:
    successes: Counter[str] = field(default_factory=Counter)
    failures: Counter[str] = field(default_factory=Counter)
    errors: Counter[str] = field(default_factory=Counter)
    error_requests: Counter[str] = field(default_factory=Counter)
    latency: list[float] = field(default_factory=list)
    retry_requests: int = 0
    retry_attempts: int = 0
    draws: int = 0
    top100: int = 0
    top1: int = 0
    drained: int = 0
    out_of_stock_all: int = 0
    unknown_commits: int = 0
    successful_orders: list[str] = field(default_factory=list)

    def record(self, req: Request, outcome: Outcome, in_window: bool) -> None:
        success = outcome.status == "success"
        if success and req.kind == "new_order":
            self.successful_orders.append(req.request_id)
        self.out_of_stock_all += outcome.status == "out_of_stock"
        self.unknown_commits += outcome.status == "unknown_commit"
        if not in_window:
            self.drained += 1
            return
        if success:
            self.successes[req.kind] += 1
            self.latency.append(outcome.latency_ms)
        else:
            self.failures[outcome.status] += 1
        self.errors.update(outcome.errors)
        self.error_requests.update(outcome.errors.keys())
        self.retry_requests += outcome.retries > 0
        self.retry_attempts += outcome.retries
        self.draws += len(req.ranks)
        self.top100 += sum(rank <= 100 for rank in req.ranks)
        self.top1 += req.ranks.count(1)

    def merge(self, part: "Phase") -> None:
        for key in ("successes", "failures", "errors", "error_requests"):
            getattr(self, key).update(getattr(part, key))
        self.latency.extend(part.latency)
        self.successful_orders.extend(part.successful_orders)
        for key in ("retry_requests", "retry_attempts", "draws", "top100", "top1", "drained",
                    "out_of_stock_all", "unknown_commits"):
            setattr(self, key, getattr(self, key) + getattr(part, key))

    def summary(self, seconds: float) -> dict[str, Any]:
        success, failed = self.successes.total(), self.failures.total()
        requests = success + failed
        latency = sorted(self.latency)

        def percent(numerator: int, denominator: int) -> float | None:
            return 100 * numerator / denominator if denominator else None

        return {
            "seconds": seconds, "tps": success / seconds if seconds else None,
            "success": success, "failed": failed, "drained_requests": self.drained,
            "new_order_success": self.successes["new_order"], "payment_success": self.successes["payment"],
            "p50_ms": percentile(latency, 50), "p95_ms": percentile(latency, 95),
            "p99_ms": percentile(latency, 99), "abort_pct": percent(failed, requests),
            "retry_pct": percent(self.retry_requests, requests), "retry_attempts": self.retry_attempts,
            "error_counts": {error: self.errors[error] for error in ERRORS},
            "failure_counts": {error: self.failures[error] for error in ERRORS},
            "request_error_pct": {error: percent(self.error_requests[error], requests)
                                  for error in ("timeout", "deadlock", "write_conflict")},
            "rank_draws": self.draws, "observed_rank1_pct": percent(self.top1, self.draws),
            "observed_top100_pct": percent(self.top100, self.draws),
            "out_of_stock_all": self.out_of_stock_all, "unknown_commits_all": self.unknown_commits,
        }


def write_json(path: Path, data: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str, allow_nan=False) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def write_result(directory: Path, result: dict) -> None:
    write_json(directory / "result.json", result)
    rows = []
    for phase in ("warmup", "measurement"):
        rows.append({
            **{key: result[key] for key in ("schema_version", "run_id", "engine", "version", "label",
                                            "inventory_mode", "repetition", "seed", "concurrency",
                                            "warehouse_mode", "theta", "hot_item", "resource_limits")},
            "phase": phase, **result[phase], **result["theoretical_selection"],
            "lock_wait_ms": result["lock_wait_ms"] if phase == "measurement" else None,
            "server_deadlocks": result["server_deadlocks"] if phase == "measurement" else None,
            "container_cpu_pct": result["container_cpu_pct"] if phase == "measurement" else None,
            "validation_status": result["validation"]["status"],
            "validation_error_counts": {rule: len(errors) for rule, errors in
                                        result["validation"].get("errors", {}).items()},
            "protocol_errors": {"errors": result["validation"].get("protocol_errors", [])},
            **result["validation"]["rules"],
        })
    with (directory / "result.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, dict)
                             else "null" if value is None else value for key, value in row.items()})
