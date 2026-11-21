from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
import random
import time

from flashsale.adapters.base import Adapter, DBError
from flashsale.transactions.core import TxnContext, execute, lookup
from .generator import Request

MAX_RETRIES = 5
ERRORS = ("timeout", "deadlock", "write_conflict", "connection", "duplicate_key",
          "transaction_abort", "database_error", "application_error", "out_of_stock",
          "unknown_commit", "busy")


@dataclass(frozen=True)
class Outcome:
    status: str
    retries: int
    errors: dict[str, int]
    latency_ms: float


def run_request(db: Adapter, req: Request, *, jitter: random.Random | None = None,
                sleep: Callable[[float], None] = time.sleep, ctx: TxnContext | None = None) -> Outcome:
    start = time.monotonic()
    errors: Counter[str] = Counter()

    def finish(status: str, retries: int) -> Outcome:
        return Outcome(status, retries, dict(errors), (time.monotonic() - start) * 1000)

    unresolved = False
    for retry in range(MAX_RETRIES + 1):
        try:
            # After an ambiguous commit, require a successful read before resubmission.
            if not unresolved or lookup(db, req) is None:
                # ctx=None giữ nguyên đường chạy của 2.1 (và chữ ký execute mà test thay thế).
                execute(db, req) if ctx is None else execute(db, req, ctx)
            return finish("success", retry)
        except DBError as exc:
            errors[exc.category] += 1
            # Lượt idempotency_off: cố ý KHÔNG đối chiếu DB trước khi gửi lại, để thấy retry sau
            # commit mơ hồ sinh đơn trùng (đề mục 2.1).
            unresolved = unresolved or (exc.ambiguous and req.idempotent)
            if req.idempotent and (unresolved or exc.category in {"duplicate_key", "out_of_stock"}):
                try:
                    persisted = lookup(db, req)
                except DBError as read_error:
                    errors[read_error.category] += 1
                    if unresolved and retry == MAX_RETRIES:
                        errors["unknown_commit"] += 1
                        return finish("unknown_commit", retry)
                else:
                    if persisted is not None:
                        return finish("success", retry)
                    # A missing row might still be committed by an in-flight
                    # server operation. Keep the ambiguity until a successful replay.
            if not exc.retryable or retry == MAX_RETRIES:
                if unresolved:
                    errors["unknown_commit"] += 1
                    return finish("unknown_commit", retry)
                return finish(exc.category, retry)
            delay = .010 * (2 ** retry)
            sleep(delay if jitter is None else delay * jitter.uniform(.5, 1.5))
    raise AssertionError("Vòng retry phải trả về kết quả")
