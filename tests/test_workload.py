from collections import Counter
from dataclasses import replace
from pathlib import Path
import random

import pytest

from flashsale.adapters.base import DBError
from flashsale.config import read_settings
from flashsale.workload import retry
from flashsale.workload.generator import Generator, Zipf


def settings():
    return read_settings(Path("configs/smoke.toml"))


def test_zipf_uniformity_and_seed():
    distribution = Zipf(20, 0, 7, False)
    rng = random.Random(42)
    counts = Counter(distribution.draw(rng)[0] for _ in range(20000))
    assert set(counts) == set(range(1, 21))
    assert all(880 < count < 1120 for count in counts.values())
    assert distribution.theoretical() == {"rank1_pct": 5, "top100_pct": 100}
    assert distribution.item_ids == Zipf(20, .9, 7, False).item_ids
    assert distribution.item_ids != Zipf(20, 0, 8, False).item_ids
    assert sorted(distribution.item_ids) == list(range(1, 21))


@pytest.mark.parametrize("mode", ["uniform", "single-warehouse"])
def test_mix_reproducibility_and_warehouse(mode):
    cfg = replace(settings(), warehouse_mode=mode, hot_item=False)
    distribution = Zipf(cfg.dataset.items, cfg.theta, cfg.seed, cfg.hot_item)
    first = Generator(cfg, distribution, "run", 1, 0, "warmup")
    second = Generator(cfg, distribution, "run", 1, 0, "warmup")
    requests = [first.next() for _ in range(2000)]
    assert requests == [second.next() for _ in requests]
    assert Counter(req.kind for req in requests) == {"new_order": 1000, "payment": 1000}
    warehouses = Counter(req.warehouse for req in requests)
    if mode == "uniform":
        assert 900 < warehouses[1] < 1100 and sum(warehouses.values()) == 2000
    else:
        assert warehouses == {1: 2000}
    for req in requests:
        if req.kind == "new_order":
            assert 1 <= len(req.items) <= len(req.ranks) <= 5
            assert len(dict(req.items)) == len(req.items)


def test_hot_item_and_retry_limit(monkeypatch):
    cfg = settings()
    zipf = Zipf(cfg.dataset.items, 0, cfg.seed, True)
    generator = Generator(cfg, zipf, "a" * 32, 1, 0, "warmup")
    req = next(req for req in (generator.next(), generator.next()) if req.kind == "new_order")
    assert req.ranks == (1,) and req.items[0][0] == zipf.item_ids[0]
    calls, delays = [], []

    def deadlock(db, request):
        calls.append(request)
        raise DBError("deadlock", True)

    monkeypatch.setattr(retry, "execute", deadlock)
    outcome = retry.run_request(None, req, sleep=delays.append)
    assert calls == [req] * 6
    assert delays == [.01, .02, .04, .08, .16]
    assert (outcome.status, outcome.retries, outcome.errors) == ("deadlock", 5, {"deadlock": 6})


def test_commit_ambiguity_reconciles_before_replay(monkeypatch):
    cfg = settings()
    req = Generator(cfg, Zipf(20, 0, 4, True), "run", 1, 1, "measurement").next()
    calls = []

    def execute(db, request):
        calls.append(request.request_id)
        raise DBError("connection", True, True)

    monkeypatch.setattr(retry, "execute", execute)
    monkeypatch.setattr(retry, "lookup", lambda db, request: {"request_id": request.request_id})
    assert retry.run_request(None, req).status == "success"
    assert calls == [req.request_id]


def test_unreachable_reconciliation_prevents_resubmission(monkeypatch):
    cfg = settings()
    req = Generator(cfg, Zipf(20, 0, 4, True), "run", 1, 1, "measurement").next()
    calls = []

    def execute(db, request):
        calls.append(request.request_id)
        raise DBError("connection", True, True)

    def lookup(db, request):
        raise DBError("connection", True)

    monkeypatch.setattr(retry, "execute", execute)
    monkeypatch.setattr(retry, "lookup", lookup)
    assert retry.run_request(None, req, sleep=lambda _: None).status == "unknown_commit"
    assert calls == [req.request_id]


def test_error_classification():
    from pymongo.errors import OperationFailure
    from pymysql.err import OperationalError
    from flashsale.adapters import mongo, sql

    assert sql.classify(OperationalError(1213, "deadlock")).category == "deadlock"
    assert sql.classify(OperationalError(1205, "timeout")).category == "timeout"
    assert sql.classify(OperationalError(2013, "lost"), True).ambiguous
    assert mongo.classify(OperationFailure("conflict", 112)).category == "write_conflict"
    assert not mongo.classify(OperationFailure("bad", 2)).retryable


def test_idempotency_off_profile_resubmits_without_reconciliation(monkeypatch):
    cfg = read_settings(Path("configs/idempotency-off.toml"))
    assert cfg.idempotency is False and cfg.label == "idempotency_off"
    req = Generator(cfg, Zipf(20, 0, 4, True), "run", 1, 1, "measurement").next()
    assert req.idempotent is False
    calls = []

    def execute(db, request):
        calls.append(request.request_id)
        if len(calls) < 3:
            raise DBError("timeout", True, True)

    def lookup(db, request):
        raise AssertionError("lượt idempotency_off không được đối chiếu DB trước khi gửi lại")

    monkeypatch.setattr(retry, "execute", execute)
    monkeypatch.setattr(retry, "lookup", lookup)
    assert retry.run_request(None, req, sleep=lambda _: None).status == "success"
    assert calls == [req.request_id] * 3  # cùng request_id gửi lại 3 lần


def test_execute_skips_idempotency_lookup_only_when_off(monkeypatch):
    from contextlib import nullcontext
    from flashsale.transactions import core

    seen = []

    class FakeDB:
        def atomic(self):
            return nullcontext()

    monkeypatch.setattr(core, "lookup", lambda db, req: seen.append(req.request_id) or {"found": True})
    monkeypatch.setattr(core, "new_order", lambda db, req: seen.append("executed:" + req.request_id))
    base = dict(request_id="r", run_id="x", kind="new_order", warehouse=1, district=1, customer=1)
    core.execute(FakeDB(), core.Request(**base))
    core.execute(FakeDB(), core.Request(**base, idempotent=False))
    assert seen == ["r", "executed:r"]


def test_idempotency_flag_must_match_label():
    cfg = settings()
    with pytest.raises(ValueError):
        replace(cfg, idempotency=False)
    with pytest.raises(ValueError):
        replace(cfg, label="idempotency_off")
    with pytest.raises(ValueError):
        replace(cfg, client_timeout_seconds=0)
