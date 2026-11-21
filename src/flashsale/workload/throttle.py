"""Mục 2.2: điều tiết thích ứng (P3) và tải vòng mở (T3). Chỉ là logic tầng ứng dụng, không đổi cách các DBMS
kiểm soát đồng thời (đề: "không phải triển khai trực tiếp DAF").

* `SharedThrottle`: giới hạn mức đồng thời L cho các giao dịch chạm món nóng, dùng chung mọi process của lượt
  chạy (mp.Value), kèm biểu đồ độ trễ dịch vụ theo từng giây để bộ điều khiển tính p99 và tỉ lệ hủy.
* `next_limit`: luật điều khiển của đề: p99 hoặc tỉ lệ hủy vượt ngưỡng thì giảm một nửa L (có sàn); cả hai dưới
  ngưỡng thì tăng thêm 1 (có trần).
* `ArrivalFeed`: tải vòng mở, yêu cầu đến theo lịch cố định, vào hàng đợi hữu hạn Q; đầy thì từ chối ngay ("busy").
"""
from bisect import bisect_left
import queue
import threading
import time

# Cận trên (ms) của các ô biểu đồ, tăng 20% mỗi ô từ 1 ms tới khoảng 56 giây; p99 ước lượng là cận trên của ô.
BIN_EDGES = [1.2 ** i for i in range(61)]
# Loại lỗi tính là "hủy hoặc timeout" cho bộ điều khiển (hết hàng là kết quả nghiệp vụ, không tính).
ABORT_CATEGORIES = ("deadlock", "write_conflict", "timeout", "transaction_abort")


def next_limit(limit: int, p99_ms: float | None, abort_pct: float | None, *, lowest: int, highest: int,
               p99_limit_ms: float, abort_limit_pct: float) -> int:
    if p99_ms is None or abort_pct is None:
        return limit  # giây không có giao dịch nóng nào hoàn tất: giữ nguyên
    if p99_ms > p99_limit_ms or abort_pct > abort_limit_pct:
        return max(lowest, limit // 2)
    return min(highest, limit + 1)


class SharedThrottle:
    def __init__(self, ctx, initial: int, lowest: int, highest: int, p99_limit_ms: float, abort_limit_pct: float):
        self.lowest, self.highest = lowest, highest
        self.p99_limit_ms, self.abort_limit_pct = p99_limit_ms, abort_limit_pct
        self.limit = ctx.Value("i", min(max(initial, lowest), highest))
        self.active = ctx.Value("i", 0)
        self.stats = ctx.Array("i", len(BIN_EDGES) + 2)  # [ô...], rồi [số giao dịch, số bị hủy]

    def acquire(self) -> None:
        while True:
            with self.active.get_lock():
                if self.active.value < self.limit.value:
                    self.active.value += 1
                    return
            time.sleep(0.0005)

    def release(self) -> None:
        with self.active.get_lock():
            self.active.value -= 1

    def observe(self, service_ms: float, aborted: bool) -> None:
        index = min(bisect_left(BIN_EDGES, service_ms), len(BIN_EDGES) - 1)
        with self.stats.get_lock():
            self.stats[index] += 1
            self.stats[-2] += 1
            self.stats[-1] += aborted

    def snapshot(self) -> tuple[int, float | None, float | None]:
        """(số giao dịch nóng hoàn tất, p99 dịch vụ ms, % hủy) từ lần gọi trước; đặt lại bộ đếm."""
        with self.stats.get_lock():
            bins, count, aborts = list(self.stats[:-2]), self.stats[-2], self.stats[-1]
            for i in range(len(self.stats)):
                self.stats[i] = 0
        if not count:
            return 0, None, None
        target, seen = 0.99 * count, 0
        for index, size in enumerate(bins):
            seen += size
            if seen >= target:
                return count, BIN_EDGES[index], 100 * aborts / count
        return count, BIN_EDGES[-1], 100 * aborts / count

    def adjust(self) -> dict:
        count, p99, abort = self.snapshot()
        before = self.limit.value
        after = next_limit(before, p99, abort, lowest=self.lowest, highest=self.highest,
                           p99_limit_ms=self.p99_limit_ms, abort_limit_pct=self.abort_limit_pct)
        self.limit.value = after
        return {"limit_before": before, "limit_after": after, "hot_completed": count, "p99_ms": p99,
                "abort_pct": abort}


def control_loop(throttle: SharedThrottle, stop: threading.Event, trace: list[dict], period: float = 1.0) -> None:
    started = time.monotonic()
    while not stop.wait(period):
        trace.append({"t": round(time.monotonic() - started, 1), **throttle.adjust()})


class ArrivalFeed:
    """Tải vòng mở của MỘT process trong một phase: yêu cầu đến mỗi 1/rate giây (theo lịch, không chờ hệ xử lý),
    vào hàng đợi hữu hạn; đầy thì từ chối ngay. Thời điểm đến là mốc theo lịch nên thời gian chờ hàng đợi (kể cả
    khi bộ phát bị trễ) nằm trong độ trễ đo, tránh bỏ sót do "coordinated omission"."""

    def __init__(self, generator, rate: float, size: int):
        self.generator, self.interval = generator, 1.0 / rate
        self.queue: queue.Queue = queue.Queue(size)
        self.rejected: list[tuple] = []
        self.start_time = 0.0
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self, start: float, deadline: float) -> None:
        with self._lock:
            if self._thread is None:
                self.start_time = start
                self._thread = threading.Thread(target=self._run, args=(start, deadline), daemon=True)
                self._thread.start()

    def _run(self, start: float, deadline: float) -> None:
        count = 0
        while True:
            arrival = start + count * self.interval
            if arrival >= deadline:
                return
            delay = arrival - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            req = self.generator.next()
            try:
                self.queue.put_nowait((req, arrival))
            except queue.Full:
                self.rejected.append((req, arrival))
            count += 1

    def get(self, deadline: float) -> tuple | None:
        while True:
            try:
                return self.queue.get(timeout=0.05)
            except queue.Empty:
                if time.monotonic() >= deadline:
                    return None
