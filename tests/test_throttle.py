"""Mục 2.2, P3 và tải vòng mở: logic điều tiết và hàng đợi (không cần DBMS)."""
"""Mục 2.2, P3 và tải vòng mở: logic điều tiết và hàng đợi (không cần DBMS)."""
import multiprocessing as mp
import threading
import time

import pytest

from flashsale.workload.throttle import ArrivalFeed, SharedThrottle, next_limit

RULE = dict(lowest=1, highest=16, p99_limit_ms=100.0, abort_limit_pct=10.0)


def test_next_limit_halves_on_either_breach_and_grows_by_one_otherwise():
    assert next_limit(16, 150.0, 0.0, **RULE) == 8     # p99 vượt ngưỡng
    assert next_limit(16, 10.0, 20.0, **RULE) == 8     # tỉ lệ hủy vượt ngưỡng
    assert next_limit(9, 10.0, 0.0, **RULE) == 10      # cả hai dưới ngưỡng: +1
    assert next_limit(16, 10.0, 0.0, **RULE) == 16     # có trần
    assert next_limit(1, 500.0, 50.0, **RULE) == 1     # có sàn
    assert next_limit(3, 500.0, 50.0, **RULE) == 1
    assert next_limit(7, None, None, **RULE) == 7      # giây không có giao dịch nóng: giữ nguyên


def test_throttle_adjust_uses_service_p99_and_abort_rate_then_resets():
    throttle = SharedThrottle(mp.get_context("spawn"), 16, 1, 16, 100.0, 10.0)
    for _ in range(95):
        throttle.observe(5.0, False)
    for _ in range(5):
        throttle.observe(900.0, True)   # 5% chậm và bị hủy: p99 rơi vào nhóm chậm
    step = throttle.adjust()
    assert step["hot_completed"] == 100 and step["p99_ms"] >= 900 and step["abort_pct"] == 5.0
    assert (step["limit_before"], step["limit_after"]) == (16, 8) and throttle.limit.value == 8
    quiet = throttle.adjust()           # không có dữ liệu mới: giữ nguyên và không chia cho 0
    assert quiet["hot_completed"] == 0 and quiet["limit_after"] == 8
    for _ in range(50):
        throttle.observe(3.0, False)
    assert throttle.adjust()["limit_after"] == 9


def test_gate_never_exceeds_the_limit_and_blocks_until_release():
    throttle = SharedThrottle(mp.get_context("spawn"), 2, 1, 4, 100.0, 10.0)
    inside, peak, lock = [0], [0], threading.Lock()

    def worker():
        throttle.acquire()
        with lock:
            inside[0] += 1
            peak[0] = max(peak[0], inside[0])
        time.sleep(0.02)
        with lock:
            inside[0] -= 1
        throttle.release()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert peak[0] <= 2 and throttle.active.value == 0


class Counter:
    def __init__(self):
        self.n = 0

    def next(self):
        self.n += 1
        return f"req-{self.n}"


def test_open_loop_feed_keeps_schedule_rejects_when_queue_is_full_and_stamps_arrival():
    start = time.monotonic() + 0.05
    feed = ArrivalFeed(Counter(), rate=200.0, size=3)  # 200 yêu cầu/giây vào hàng đợi chứa 3, không ai lấy ra
    feed.start(start, start + 0.5)
    time.sleep(0.8)
    assert feed.queue.qsize() == 3
    assert len(feed.rejected) >= 80                      # ~100 yêu cầu đến, 3 nằm trong hàng đợi
    first, arrival = feed.queue.get_nowait()
    assert first == "req-1" and arrival == pytest.approx(start)
    assert [round(t - start, 3) for _, t in feed.rejected[:2]] == [0.015, 0.02]  # lịch cố định 5 ms


def test_open_loop_get_returns_none_after_deadline():
    feed = ArrivalFeed(Counter(), rate=1.0, size=1)
    assert feed.get(time.monotonic()) is None


def test_settings_and_context_for_p3_and_open_loop():
    from dataclasses import replace
    from pathlib import Path
    from flashsale.benchmark.runner import is_hot, make_context
    from flashsale.config import read_settings, uses_slots
    from flashsale.workload.generator import Request, Zipf
    base = read_settings(Path("configs/smoke.toml"))
    assert (base.arrival_rate, base.queue_size) == (0.0, 64)
    assert uses_slots("p2") and uses_slots("p3") and not uses_slots("p1")
    for bad in (dict(arrival_rate=-1), dict(queue_size=0), dict(p99_limit_ms=0), dict(abort_limit_pct=101),
                dict(limit_min=0)):
        with pytest.raises(ValueError):
            replace(base, variant="p3", **bad)
    zipf = Zipf(base.dataset.items, 0, base.seed, False)
    ctx = make_context(replace(base, variant="p3", slots=3, hot_items=2), zipf, 1, 0)
    assert ctx.hot_items == frozenset(zipf.item_ids[:2])
    hot, cold = zipf.item_ids[0], zipf.item_ids[-1]
    assert is_hot(Request("a", "r", "new_order", 1, 1, 1, ((cold, 1), (hot, 1))), ctx)
    assert not is_hot(Request("b", "r", "new_order", 1, 1, 1, ((cold, 1),)), ctx)
    assert not is_hot(Request("c", "r", "payment", 1, 1, 1), ctx)
    assert not is_hot(Request("d", "r", "new_order", 1, 1, 1, ((hot, 1),)), None)


def test_phase_reports_rejections_queue_wait_and_excludes_busy_from_abort_pct():
    from flashsale.benchmark.metrics import Phase
    from flashsale.workload.generator import Request
    from flashsale.workload.retry import Outcome
    req = Request("x", "r", "new_order", 1, 1, 1, ((1, 1),), (1,))
    phase = Phase()
    phase.record(req, Outcome("success", 0, {}, 30.0), True, 0, 10.0)
    phase.record(req, Outcome("success", 0, {}, 50.0), True, 0, 30.0)
    phase.record(req, Outcome("busy", 0, {"busy": 1}, 0.0), True, 0)
    phase.record(req, Outcome("deadlock", 5, {"deadlock": 6}, 9.0), True, 0)
    phase.unserved = 4
    summary = phase.summary(1)
    assert summary["rejected"] == 1 and summary["rejected_pct"] == 25.0
    assert summary["abort_pct"] == 25.0          # chỉ deadlock; "busy" tách riêng
    assert summary["queue_wait_mean_ms"] == 20.0 and summary["queue_wait_p99_ms"] == 30.0
    assert summary["unserved_at_deadline"] == 4
