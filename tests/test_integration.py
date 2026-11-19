from pathlib import Path
import os

import pytest

from flashsale.adapters.base import open_adapter
from flashsale.cli import project_smoke
from flashsale.config import read_settings
from flashsale.data.loader import load, reset
from flashsale.infra import ENGINES, enforce_one, endpoint, project_lock
from flashsale.validation.checks import validate
from flashsale.workload.generator import Request
from flashsale.workload.retry import run_request

pytestmark = pytest.mark.integration


@pytest.fixture(params=ENGINES)
def engine(request):
    if os.getenv("FLASHSALE_TEST_ENGINE") != request.param:
        pytest.skip("Chạy với FLASHSALE_TEST_ENGINE trùng hệ đang chạy")
    return request.param


@pytest.fixture
def dataset(engine):
    config = read_settings(Path("configs/smoke.toml"))
    target = endpoint(engine)
    with project_lock():
        enforce_one(engine)
        db = open_adapter(target, admin=True)
        try:
            assert db.ping()["version"]
            db.create()
            counts = load(db, config.dataset, config.seed)
            yield db, config.dataset, counts
        finally:
            try:
                db.drop()
            finally:
                db.close()


def test_transaction_contract_and_validator(dataset):
    db, config, counts = dataset
    assert len(counts) == 9 and counts["stock"] == 40
    run_id = "a" * 32
    req = Request(run_id + "-first", run_id, "new_order", 1, 1, 1, ((1, 4), (2, 5)))
    assert run_request(db, req).status == "success"
    assert run_request(db, req).status == "success"
    assert db.count("orders") == counts["orders"] + 1
    stock1 = {"s_w_id": 1, "s_i_id": 1}
    stock2 = {"s_w_id": 1, "s_i_id": 2}
    assert db.one("stock", stock1)["s_quantity"] == 16
    assert db.one("stock", stock2)["s_quantity"] == 15
    failure = Request(run_id + "-failed", run_id, "new_order", 1, 1, 1, ((1, 7), (2, 16)))
    assert run_request(db, failure).status == "out_of_stock"
    assert db.one("stock", stock1)["s_quantity"] == 16
    assert db.one("stock", stock2)["s_quantity"] == 15
    assert db.one("district", {"d_w_id": 1, "d_id": 1})["d_next_o_id"] == config.initial_orders + 2
    assert db.count("order_line") == counts["order_line"] + 2

    customer = {"c_w_id": 1, "c_d_id": 1, "c_id": 1}
    warehouse = {"w_id": 1}
    original_ytd = db.one("warehouse", warehouse)["w_ytd"]
    payment = Request(run_id + "-payment", run_id, "payment", 1, 1, 1, amount=2599)
    assert run_request(db, payment).status == "success"
    assert run_request(db, payment).status == "success"
    assert db.one("customer", customer)["c_balance"] == -3599
    assert db.one("history", {"request_id": payment.request_id})["h_amount"] == 2599
    assert db.count("history") == counts["history"] + 1
    assert db.one("warehouse", warehouse)["w_ytd"] == original_ytd
    extra = Request(run_id + "-ytd", run_id, "payment", 1, 1, 1, amount=100, payment_ytd=True)
    assert run_request(db, extra).status == "success"
    assert db.one("warehouse", warehouse)["w_ytd"] == original_ytd + 100
    assert validate(db, config, run_id, [req.request_id])["status"] == "VALID"
    db.change("stock", stock1, set_values={"s_quantity": -1})
    db.change("stock", stock2, set_values={"s_quantity": 99})
    invalid = validate(db, config, run_id, [req.request_id, req.request_id])
    assert invalid["status"] == "INVALID"
    assert not any(invalid["rules"].values())
    reset(db, config)
    assert validate(db, config, "", [])["status"] == "VALID"
    assert {table: db.count(table) for table in counts} == counts
    assert db.one("customer", customer)["c_balance"] == -1000


def test_smoke_exports(engine):
    path = Path("configs/smoke.toml")
    with project_lock():
        reports = project_smoke(engine, read_settings(path), path, manage=False)
    assert reports[0]["validation"]["status"] == "VALID"
    folder = Path("results") / reports[0]["run_id"]
    assert (folder / "manifest.json").is_file() and (folder / "result.csv").is_file()


def test_replay_without_persisted_idempotency_is_rejected(dataset):
    db, config, counts = dataset
    run_id = "b" * 32
    req = Request(run_id + "-retry", run_id, "new_order", 1, 1, 1, ((1, 1),))
    assert run_request(db, req).status == "success"
    db.change("orders", {"request_id": req.request_id}, set_values={"request_id": None})
    assert run_request(db, req).status == "success"
    assert db.count("orders") == counts["orders"] + 2
    report = validate(db, config, run_id, [req.request_id], counts)
    assert report["status"] == "INVALID"
    assert report["rules"] == {"nonnegative": True, "reconciliation": True, "idempotency": False}


@pytest.fixture
def dataset_idempotency_off(engine):
    config = read_settings(Path("configs/smoke.toml"))
    target = endpoint(engine)
    with project_lock():
        enforce_one(engine)
        db = open_adapter(target, admin=True)
        try:
            db.create(idempotency=False)
            counts = load(db, config.dataset, config.seed)
            yield db, config.dataset, counts
        finally:
            try:
                db.drop()
            finally:
                db.close()


def test_idempotency_off_replay_creates_duplicate_order(dataset_idempotency_off):
    db, config, counts = dataset_idempotency_off
    run_id = "c" * 32
    req = Request(run_id + "-dup", run_id, "new_order", 1, 1, 1, ((1, 1),), idempotent=False)
    assert run_request(db, req).status == "success"
    assert run_request(db, req).status == "success"  # không có UNIQUE: được ghi lần hai
    assert db.count("orders") == counts["orders"] + 2
    report = validate(db, config, run_id, [req.request_id], counts)
    assert report["status"] == "INVALID" and report["rules"]["idempotency"] is False
