from pathlib import Path
import os

import pytest

from flashsale.adapters.base import open_adapter
from flashsale.cli import project_smoke
from flashsale.config import read_settings
from flashsale.data.loader import load, prepare_slots, reset
from flashsale.infra import ENGINES, enforce_one, endpoint, project_lock
from flashsale.transactions.core import TxnContext
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
    assert db.doc_reconciliation(config.inventory, config.initial_orders) == []  # SQL/aggregation của đề
    db.change("stock", stock1, set_values={"s_quantity": -1})
    db.change("stock", stock2, set_values={"s_quantity": 99})
    invalid = validate(db, config, run_id, [req.request_id, req.request_id])
    assert db.doc_reconciliation(config.inventory, config.initial_orders)
    assert invalid["status"] == "INVALID"
    assert not any(invalid["rules"].values())
    reset(db, config)
    assert validate(db, config, "", [])["status"] == "VALID"
    assert {table: db.count(table) for table in counts} == counts
    assert db.one("customer", customer)["c_balance"] == -1000


def test_hotspot_variants_p1_p2_contract(dataset):
    """Mục 2.2: P1 (cập nhật có điều kiện), lô mã đơn và P2 (slot) trên DBMS thật, rồi validator/đối soát của đề."""
    db, config, counts = dataset
    run_id = "b" * 32
    district = {"d_w_id": 1, "d_id": 1}
    p1 = TxnContext("p1", order_id_batch=3)
    ok = Request(run_id + "-p1", run_id, "new_order", 1, 1, 1, ((1, 4), (2, 5)))
    assert run_request(db, ok, ctx=p1).status == "success"
    assert db.one("stock", {"s_w_id": 1, "s_i_id": 1})["s_quantity"] == 16
    short = Request(run_id + "-p1-short", run_id, "new_order", 1, 1, 1, ((1, 7), (2, 16)))
    assert run_request(db, short, ctx=p1).status == "out_of_stock"
    assert db.one("stock", {"s_w_id": 1, "s_i_id": 1})["s_quantity"] == 16
    assert db.one("district", district)["d_next_o_id"] == config.initial_orders + 1 + 3  # một lô 3 mã

    assert prepare_slots(db, config, [3], 3)["slot_rows"] == config.warehouses * 3
    p2 = TxnContext("p2", 3, frozenset({3}), order_id_batch=3)
    sold = []
    for n in range(3):  # slot 7/7/6: mỗi đơn 6 cái vét đúng một slot, bất kể slot được chọn đầu tiên
        req = Request(f"{run_id}-p2-{n}", run_id, "new_order", 1, 1, 1, ((3, 6),))
        assert run_request(db, req, ctx=p2).status == "success"
        sold.append(req.request_id)
    over = Request(run_id + "-p2-over", run_id, "new_order", 1, 1, 1, ((3, 6),))
    assert run_request(db, over, ctx=p2).status == "out_of_stock"
    assert db.one("stock", {"s_w_id": 1, "s_i_id": 3})["s_quantity"] == 0
    report = validate(db, config, run_id, [ok.request_id, *sold], slots=True)
    assert report["status"] == "VALID", report["errors"]
    assert db.doc_reconciliation(config.inventory, config.initial_orders, slots=True) == []
    # Quên cộng slot (validate không slots) phải bị phát hiện: tồn nằm ngoài dòng stock.
    assert validate(db, config, run_id, [ok.request_id, *sold])["status"] == "INVALID"
    reset(db, config)
    assert validate(db, config, "", [])["status"] == "VALID"
    assert {table: db.count(table) for table in counts} == counts


def test_mongo_design_b_embedded_order_and_refund(dataset, engine):
    """MongoDB thiết kế (b) (T4): đơn nhúng order_lines, trừ kho từng món, hoàn kho khi hết hàng, ba luật VALID."""
    if engine != "mongo":
        pytest.skip("Thiết kế (b) chỉ có trên MongoDB")
    db, config, counts = dataset
    run_id = "c" * 32
    ctx = TxnContext("p1", design_b=True)
    ok = Request(run_id + "-b1", run_id, "new_order", 1, 1, 1, ((1, 4), (2, 5)))
    assert run_request(db, ok, ctx=ctx).status == "success"
    assert run_request(db, ok, ctx=ctx).status == "success"  # replay cùng request_id không tạo đơn thứ hai
    short = Request(run_id + "-b-short", run_id, "new_order", 1, 1, 1, ((1, 7), (2, 16)))
    assert run_request(db, short, ctx=ctx).status == "out_of_stock"
    assert db.one("stock", {"s_w_id": 1, "s_i_id": 1})["s_quantity"] == 16   # món 1 đã trừ rồi được hoàn lại
    assert db.one("stock", {"s_w_id": 1, "s_i_id": 2})["s_quantity"] == 15
    assert db.count("orders") == counts["orders"] + 1 and db.count("order_line") == counts["order_line"]
    assert db.db.orders.find_one({"request_id": ok.request_id})["order_lines"][0]["ol_quantity"] == 4
    report = validate(db, config, run_id, [ok.request_id], counts, embedded=True)
    assert report["status"] == "VALID", report["errors"]
    assert db.doc_reconciliation(config.inventory, config.initial_orders, embedded=True) == []
    db.change("stock", {"s_w_id": 1, "s_i_id": 1}, set_values={"s_quantity": 17})  # mất cập nhật cài chủ động
    assert validate(db, config, run_id, [ok.request_id], counts, embedded=True)["status"] == "INVALID"
    reset(db, config)
    assert validate(db, config, "", [])["status"] == "VALID"


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
