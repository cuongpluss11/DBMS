"""Fault injection (mục 2.2, kiểm chứng ba luật tồn kho khi có sự cố phía ứng dụng/kết nối).

Chạy trên DBMS thật như test integration khác: FLASHSALE_TEST_ENGINE=mysql|mongo|tidb pytest -m integration
tests/test_fault_injection.py. Mô hình lỗi công bố: xem `flashsale/faults.py` (không mô phỏng DBMS chết).
"""
from pathlib import Path
import os

import pytest

from flashsale.adapters.base import DBError, open_adapter
from flashsale.config import read_settings
from flashsale.data.loader import load
from flashsale.faults import FaultyAdapter, ProcessCrash
from flashsale.infra import ENGINES, enforce_one, endpoint, project_lock
from flashsale.transactions.core import TxnContext, execute, lookup
from flashsale.validation.checks import validate
from flashsale.workload.generator import Request
from flashsale.workload.retry import run_request

pytestmark = pytest.mark.integration
NO_SLEEP = lambda _: None  # noqa: E731


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
            db.create()
            counts = load(db, config.dataset, config.seed)
            yield db, config.dataset, counts, target
        finally:
            try:
                db.drop()
            finally:
                db.close()


def stock(db, item, warehouse=1):
    return db.one("stock", {"s_w_id": warehouse, "s_i_id": item})["s_quantity"]


def new_order(request_id, items=((1, 4), (2, 5))):
    run_id = "b" * 32
    return Request(f"{run_id}-{request_id}", run_id, "new_order", 1, 1, 1, items)


def assert_laws(db, dataset, req_ids, run_id="b" * 32):
    report = validate(db, dataset, run_id, req_ids)
    assert report["status"] == "VALID", report["errors"]
    assert db.doc_reconciliation(dataset.inventory, dataset.initial_orders) == []


def test_crash_before_commit_leaves_no_trace_then_retry_creates_one_order(dataset):
    db, config, counts, target = dataset
    req = new_order("f1")
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["crash_before_commit"])
    with pytest.raises(ProcessCrash):
        execute(faulty, req)
    # Giao dịch bị hủy: không đơn, không dòng đơn, không trừ kho, mã đơn không nhích.
    assert db.count("orders") == counts["orders"] and db.count("order_line") == counts["order_line"]
    assert stock(db, 1) == config.inventory and stock(db, 2) == config.inventory
    assert db.one("district", {"d_w_id": 1, "d_id": 1})["d_next_o_id"] == config.initial_orders + 1
    # Tiến trình mới thử lại cùng request_id: đúng một đơn.
    fresh = open_adapter(target)
    try:
        assert run_request(fresh, req).status == "success"
        assert run_request(fresh, req).status == "success"  # lặp lại không tạo đơn thứ hai
    finally:
        fresh.close()
    assert db.count("orders") == counts["orders"] + 1
    assert stock(db, 1) == config.inventory - 4 and stock(db, 2) == config.inventory - 5
    assert_laws(db, config, [req.request_id])


def test_connection_lost_before_commit_is_retried_to_exactly_one_order(dataset):
    db, config, counts, target = dataset
    req = new_order("f1b")
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["before_commit", "before_commit", None])
    try:
        outcome = run_request(faulty, req, sleep=NO_SLEEP)
    finally:
        faulty._inner.close()
    assert outcome.status == "success" and outcome.retries == 2 and outcome.errors["connection"] == 2
    assert db.count("orders") == counts["orders"] + 1
    assert stock(db, 1) == config.inventory - 4
    assert_laws(db, config, [req.request_id])


def test_commit_succeeds_but_ack_lost_is_not_resubmitted(dataset):
    db, config, counts, target = dataset
    new = new_order("f2")
    pay = Request("b" * 32 + "-f2pay", "b" * 32, "payment", 1, 1, 1, amount=2599)
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["after_commit", "after_commit"])
    try:
        assert run_request(faulty, new, sleep=NO_SLEEP).status == "success"
        assert run_request(faulty, pay, sleep=NO_SLEEP).status == "success"
    finally:
        faulty._inner.close()
    assert faulty.injected == ["after_commit", "after_commit"]
    assert db.count("orders") == counts["orders"] + 1  # không gửi lại sau commit mơ hồ
    assert stock(db, 1) == config.inventory - 4 and stock(db, 2) == config.inventory - 5
    assert db.count("history") == counts["history"] + 1
    assert db.one("customer", {"c_w_id": 1, "c_d_id": 1, "c_id": 1})["c_balance"] == -3599
    assert_laws(db, config, [new.request_id])


def test_failed_reads_during_ambiguous_retry_never_duplicate_the_order(dataset):
    db, config, counts, target = dataset
    req = new_order("f3")
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["after_commit"], fail_reads=2)
    try:
        assert run_request(faulty, req, sleep=NO_SLEEP).status == "success"
    finally:
        faulty._inner.close()
    assert faulty.injected.count("fail_read") == 2
    assert db.count("orders") == counts["orders"] + 1
    assert stock(db, 1) == config.inventory - 4
    assert_laws(db, config, [req.request_id])


def test_unknown_commit_is_resolved_by_reading_the_database_not_by_resubmitting(dataset):
    db, config, counts, target = dataset
    req = new_order("f4")
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["after_commit"], fail_reads=99)
    try:
        outcome = run_request(faulty, req, sleep=NO_SLEEP)
    finally:
        faulty._inner.close()
    assert outcome.status == "unknown_commit"
    assert db.count("orders") == counts["orders"] + 1  # thực tế đã commit đúng một đơn
    # Đơn "đã commit nhưng chưa được xác nhận" bị validator báo thừa khi chưa được giải quyết (idempotency)...
    pending = validate(db, config, "b" * 32, [])
    assert pending["status"] == "INVALID" and pending["rules"]["idempotency"] is False
    # ...và hợp lệ ngay khi một lần đọc sau đó xác nhận được request_id (đúng một đơn, không trừ kho hai lần).
    assert lookup(db, req) is not None
    assert_laws(db, config, [req.request_id])
    assert stock(db, 1) == config.inventory - 4


def test_out_of_stock_order_then_crash_keeps_stock_and_orders_untouched(dataset):
    db, config, counts, target = dataset
    req = new_order("f5", items=((1, 7), (2, config.inventory + 1)))
    faulty = FaultyAdapter(open_adapter(target), atomic_plan=["after_commit"])
    try:
        assert run_request(faulty, req, sleep=NO_SLEEP).status == "out_of_stock"
    finally:
        faulty._inner.close()
    assert db.count("orders") == counts["orders"] and stock(db, 1) == config.inventory
    assert_laws(db, config, [])


def test_mongo_design_b_crash_between_stock_and_order_write_breaks_law_2(dataset, engine):
    if engine != "mongo":
        pytest.skip("Thiết kế (b) chỉ có ở MongoDB")
    db, config, counts, target = dataset
    req = new_order("f6")
    ctx = TxnContext(variant="p1", design_b=True)
    faulty = FaultyAdapter(open_adapter(target), crash_on_insert="orders")
    with pytest.raises(ProcessCrash):
        execute(faulty, req, ctx)
    faulty._inner.close()
    # Giới hạn đã công bố của (b): kho đã bị trừ mà không có đơn (không hoàn lại được vì tiến trình đã chết).
    assert stock(db, 1) == config.inventory - 4 and stock(db, 2) == config.inventory - 5
    assert db.count("orders") == counts["orders"]
    report = validate(db, config, "b" * 32, [], embedded=True)
    assert report["status"] == "INVALID" and report["rules"]["reconciliation"] is False
