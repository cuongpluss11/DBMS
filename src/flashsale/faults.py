"""Fault injection cho mục 2.2 (kiểm chứng không oversell, không mất đơn, không đơn trùng khi có sự cố).

Chỉ dùng trong kiểm thử/script thực nghiệm, không nằm trên đường chạy của benchmark. `FaultyAdapter` bọc một
Adapter thật và chèn lỗi tại các điểm của một giao dịch mà DBMS không tự tạo ra được theo ý muốn:

* `before_commit`  : ứng dụng bị ngắt sau khi mọi lệnh ghi đã chạy nhưng TRƯỚC commit (giao dịch bị hủy).
* `after_commit`   : commit THÀNH CÔNG nhưng ứng dụng không nhận được phản hồi (lỗi kết nối mơ hồ).
* `crash_before_commit`: như `before_commit` nhưng là ProcessCrash (BaseException, mô phỏng tiến trình chết):
  mọi lệnh sau đó trên adapter này cũng lỗi cho đến khi tạo adapter mới (kết nối đã mất).
* `fail_reads`     : N lần đọc `orders`/`history` theo `request_id` (bước đối chiếu idempotency) bị lỗi kết nối.
* `crash_on_insert`: chết đúng lúc ghi bảng chỉ định (thiết kế (b) của MongoDB: giữa trừ kho và ghi đơn).

Mô hình lỗi công bố: lỗi phía ứng dụng/kết nối; KHÔNG mô phỏng DBMS chết hay mất đĩa.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from flashsale.adapters.base import DBError


class ProcessCrash(BaseException):
    """Mô phỏng tiến trình ứng dụng chết: không bị bắt bởi `except Exception`."""


class FaultyAdapter:
    def __init__(self, inner, atomic_plan: list[str | None] | None = None, fail_reads: int = 0,
                 crash_on_insert: str | None = None):
        self._inner = inner
        self.atomic_plan = list(atomic_plan or [])
        self.fail_reads = fail_reads
        self.crash_on_insert = crash_on_insert
        self.dead = False
        self.injected: list[str] = []

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._inner, name)
        if not callable(target):
            return target

        def call(*args, **kwargs):
            self._check_alive()
            return target(*args, **kwargs)

        return call

    def _check_alive(self) -> None:
        if self.dead:
            raise ProcessCrash()

    def _crash(self, point: str) -> None:
        self.injected.append(point)
        self.dead = True
        raise ProcessCrash()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        self._check_alive()
        fault = self.atomic_plan.pop(0) if self.atomic_plan else None
        with self._inner.atomic():
            yield
            if fault == "before_commit":
                self.injected.append(fault)
                raise DBError("connection", retryable=True, ambiguous=False)
            if fault == "crash_before_commit":
                self._crash(fault)
        # Tới đây commit đã THÀNH CÔNG.
        if fault == "after_commit":
            self.injected.append(fault)
            raise DBError("connection", retryable=True, ambiguous=True)

    def one(self, table: str, key: dict, **kwargs):
        self._check_alive()
        # Chỉ làm hỏng bước đối chiếu SAU commit mơ hồ: lần đọc trong chính giao dịch (kiểm tra trùng) không bị chèn lỗi.
        if (self.fail_reads > 0 and "after_commit" in self.injected and table in ("orders", "history")
                and "request_id" in key and not kwargs.get("lock")):
            self.fail_reads -= 1
            self.injected.append("fail_read")
            raise DBError("connection", retryable=True, ambiguous=False)
        return self._inner.one(table, key, **kwargs)

    def insert(self, table: str, row: dict) -> None:
        self._check_alive()
        if self.crash_on_insert == table:
            self._crash(f"crash_on_insert:{table}")
        return self._inner.insert(table, row)


class CommitWindowAdapter(FaultyAdapter):
    """Kéo dài cửa sổ "đã commit, chưa trả phản hồi" bằng một độ trễ NHÂN TẠO ngay sau commit thành công, để việc giết
    tiến trình ngẫu nhiên có xác suất cao rơi đúng vào cửa sổ đó (cửa sổ thật chỉ vài mili-giây). Không đổi ngữ nghĩa
    giao dịch: commit đã xong trước khi chờ."""

    def __init__(self, inner, post_commit_delay_ms: float):
        super().__init__(inner)
        self.post_commit_delay = post_commit_delay_ms / 1000

    @contextmanager
    def atomic(self) -> Iterator[None]:
        import time

        self._check_alive()
        with self._inner.atomic():
            yield
        if self.post_commit_delay > 0:
            time.sleep(self.post_commit_delay)
