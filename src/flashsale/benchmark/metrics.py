from collections import Counter
import csv
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

from flashsale.workload.generator import Request
from flashsale.workload.retry import ERRORS, Outcome

SCHEMA_VERSION = 4


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
    # P2: tổng số lần thử slot và số lần trừ món nóng qua slot (kể cả hết hàng, retry và giao dịch sau đó bị hủy).
    slot_attempts: int = 0
    slot_items: int = 0
    # Tải vòng mở: yêu cầu bị từ chối vì hàng đợi đầy, yêu cầu còn trong hàng đợi lúc hết phase, thời gian chờ
    # (đến lúc bắt đầu chạy, gồm hàng đợi và cổng điều tiết) của các yêu cầu trong cửa sổ đo.
    rejected: int = 0
    unserved: int = 0
    queue_waits: list[float] = field(default_factory=list)
    successful_orders: list[str] = field(default_factory=list)
    # Số request thành công mỗi giây của phase (giây 0 = đầu phase); dùng kiểm tra warmup đã ổn định chưa.
    series: Counter[int] = field(default_factory=Counter)

    def record(self, req: Request, outcome: Outcome, in_window: bool, second: int | None = None,
               queue_wait_ms: float | None = None) -> None:
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
            if second is not None:
                self.series[second] += 1
        else:
            self.failures[outcome.status] += 1
        if queue_wait_ms is not None:
            self.queue_waits.append(queue_wait_ms)
        self.rejected += outcome.status == "busy"
        self.errors.update(outcome.errors)
        self.error_requests.update(outcome.errors.keys())
        self.retry_requests += outcome.retries > 0
        self.retry_attempts += outcome.retries
        self.draws += len(req.ranks)
        self.top100 += sum(rank <= 100 for rank in req.ranks)
        self.top1 += req.ranks.count(1)

    def merge(self, part: "Phase") -> None:
        for key in ("successes", "failures", "errors", "error_requests", "series"):
            getattr(self, key).update(getattr(part, key))
        self.latency.extend(part.latency)
        self.queue_waits.extend(part.queue_waits)
        self.successful_orders.extend(part.successful_orders)
        for key in ("retry_requests", "retry_attempts", "draws", "top100", "top1", "drained",
                    "out_of_stock_all", "unknown_commits", "slot_attempts", "slot_items", "rejected",
                    "unserved"):
            setattr(self, key, getattr(self, key) + getattr(part, key))

    def series_list(self, seconds: float) -> list[int]:
        return [self.series[i] for i in range(int(seconds))]

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
            "p99_ms": percentile(latency, 99), "abort_pct": percent(failed - self.failures["out_of_stock"] - self.failures["busy"], requests),
            "rejected": self.rejected, "rejected_pct": percent(self.failures["busy"], requests),
            "unserved_at_deadline": self.unserved,
            "queue_wait_mean_ms": sum(waits) / len(waits) if (waits := self.queue_waits) else None,
            "queue_wait_p99_ms": percentile(sorted(self.queue_waits), 99),
            "out_of_stock_pct": percent(self.failures["out_of_stock"], requests),
            "retry_pct": percent(self.retry_requests, requests), "retry_attempts": self.retry_attempts,
            "error_counts": {error: self.errors[error] for error in ERRORS},
            "failure_counts": {error: self.failures[error] for error in ERRORS},
            "request_error_pct": {error: percent(self.error_requests[error], requests)
                                  for error in ("timeout", "deadlock", "write_conflict")},
            "rank_draws": self.draws, "observed_rank1_pct": percent(self.top1, self.draws),
            "observed_top100_pct": percent(self.top100, self.draws),
            "out_of_stock_all": self.out_of_stock_all, "unknown_commits_all": self.unknown_commits,
            # Chỉ có nghĩa với variant p2 (null khi không có lần thử slot nào); đếm cả warmup-drain và lần retry.
            "slot_attempts": self.slot_attempts or None,
            "slot_attempts_per_item": self.slot_attempts / self.slot_items if self.slot_items else None,
        }


def warmup_stability(warmup: list[int], measurement: list[int], window: int = 10) -> dict[str, Any]:
    """So TPS trung vị `window` giây cuối của warmup với `window` giây đầu của đo.
    Lệch lớn nghĩa là 30 giây warmup chưa đủ (đề: kéo dài warmup cho mọi hệ). Thiếu dữ liệu → null."""
    if len(warmup) < window or len(measurement) < window:
        return {"window_seconds": window, "warmup_tail_tps": None, "measurement_head_tps": None, "drift_pct": None}
    # Trung vị, không phải trung bình: WiredTiger checkpoint định kỳ (~60 giây) làm TPS tụt vài giây và làm lệch
    # trung bình dù warmup đã ổn định.
    import statistics
    tail, head = statistics.median(warmup[-window:]), statistics.median(measurement[:window])
    return {"window_seconds": window, "warmup_tail_tps": tail, "measurement_head_tps": head,
            "drift_pct": 100 * (head - tail) / tail if tail else None}


def write_series(path: Path, series: dict[str, list[int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["phase", "second", "successes"])
        for phase, values in series.items():
            for second, count in enumerate(values):
                writer.writerow([phase, second, count])


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
            "idempotency": result.get("idempotency", True),
            "variant": result.get("variant", "legacy"), "slots": result.get("slots"),
            "arrival_rate": result.get("arrival_rate", 0.0),
            "order_id_batch": result.get("order_id_batch", 0),
            "client_timeout_seconds": result.get("client_timeout_seconds"),
            "phase": phase, **result[phase], **result["theoretical_selection"],
            "lock_wait_ms": result["lock_wait_ms"] if phase == "measurement" else None,
            "server_deadlocks": result["server_deadlocks"] if phase == "measurement" else None,
            "container_cpu_pct": result["container_cpu_pct"] if phase == "measurement" else None,
            "resource_warnings": result.get("resource_warnings") if phase == "measurement" else None,
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
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list))
                             else "null" if value is None else value for key, value in row.items()})
