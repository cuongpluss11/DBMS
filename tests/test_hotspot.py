"""Mục 2.2, P0–P2: kiểm bằng adapter trong bộ nhớ (không cần DBMS). Hành vi trên MySQL/MongoDB/TiDB thật
được kiểm riêng bằng test integration và smoke; ở đây chứng minh logic giao dịch, slot, lô mã đơn và validator."""
from contextlib import contextmanager
import copy
import random

import pytest

from flashsale.adapters.base import DBError
from flashsale.config import Dataset, Settings
from flashsale.data.loader import prepare_slots, slot_quantities
from flashsale.transactions import core
from flashsale.transactions.core import TxnContext, execute
from flashsale.validation.checks import check
from flashsale.workload.generator import Request

DATASET = Dataset(1, 1, 5, 1, 1, 10)


class MemDB:
    """Đủ giao diện Adapter cho new_order/payment; `atomic` rollback bằng bản sao khi có lỗi."""

    def __init__(self, inventory=10, initial_next=2):
        self.tables = {name: [] for name in ("district", "stock", "item", "orders", "new_order", "order_line",
                                             "stock_slot", "history", "customer")}
        self.tables["district"].append(dict(d_w_id=1, d_id=1, d_next_o_id=initial_next))
        self.tables["stock"] = [dict(s_w_id=1, s_i_id=i, s_quantity=inventory, s_ytd=0, s_order_cnt=0,
                                     s_dist_01="D" * 24) for i in range(1, 6)]
        self.tables["item"] = [dict(i_id=i, i_price=100) for i in range(1, 6)]
        self.depth = 0
        self.calls = []

    @contextmanager
    def atomic(self):
        assert self.depth == 0, "giao dịch lồng nhau: BEGIN sẽ chốt giao dịch đang mở"
        saved = copy.deepcopy(self.tables)
        self.depth += 1
        self.calls.append("begin")
        try:
            yield
        except BaseException:
            self.tables = saved
            raise
        finally:
            self.depth -= 1

    def match(self, table, key):
        return [row for row in self.tables[table] if all(row.get(k) == v for k, v in key.items())]

    def one(self, table, key, *, lock=False):
        self.calls.append(("one", table, lock))
        rows = self.match(table, key)
        return dict(rows[0]) if rows else None

    def change(self, table, key, *, set_values=None, increment=None, at_least=None, **_):
        self.calls.append(("change", table, bool(at_least), bool(set_values)))
        rows = [row for row in self.match(table, key)
                if all(row[name] >= minimum for name, minimum in (at_least or {}).items())]
        for row in rows:
            row.update(set_values or {})
            for name, delta in (increment or {}).items():
                row[name] += delta
        return len(rows)

    def insert(self, table, row):
        self.tables[table].append(dict(row))

    def insert_many(self, table, rows):
        self.tables[table].extend(dict(row) for row in rows)

    def count(self, table):
        return len(self.tables[table])

    def create_slots(self):
        self.tables["stock_slot"] = []

    def drop_slots(self):
        self.tables["stock_slot"] = []

    def quantity(self, item):
        return self.match("stock", {"s_i_id": item})[0]["s_quantity"]


def order(items, n=0, **kw):
    return Request(f"run-{n}", "run", "new_order", 1, 1, 1, tuple(items), (1,) * len(items),
                   idempotent=False, **kw)


def lookup_free(monkeypatch):
    monkeypatch.setattr(core, "lookup", lambda db, req: None)


def test_legacy_context_none_keeps_the_2_1_path(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    execute(db, order([(1, 3)]))
    assert db.quantity(1) == 7
    assert ("one", "stock", True) in db.calls  # FOR UPDATE như 2.1
    assert db.match("district", {})[0]["d_next_o_id"] == 3


def test_p1_is_one_conditional_statement_without_reading_stock(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    execute(db, order([(1, 3), (2, 4)]), TxnContext("p1"))
    assert (db.quantity(1), db.quantity(2)) == (7, 6)
    assert not any(c[:2] == ("one", "stock") for c in db.calls if isinstance(c, tuple))
    assert ("change", "stock", True, False) in db.calls
    stock = db.match("stock", {"s_i_id": 1})[0]
    assert (stock["s_ytd"], stock["s_order_cnt"]) == (3, 1)
    assert db.match("order_line", {})[0]["ol_dist_info"] == core.DIST_FILLER


def test_p1_out_of_stock_rolls_back_the_whole_multi_item_order(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB(inventory=5)
    with pytest.raises(DBError) as error:
        execute(db, order([(1, 3), (2, 6)]), TxnContext("p1"))
    assert error.value.category == "out_of_stock"
    assert (db.quantity(1), db.quantity(2)) == (5, 5)
    assert db.count("orders") == 0 and db.count("order_line") == 0
    assert db.match("district", {})[0]["d_next_o_id"] == 2


def test_p0_reads_without_lock_and_writes_an_absolute_value(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    execute(db, order([(1, 3)]), TxnContext("p0"))
    assert ("one", "stock", False) in db.calls and ("one", "stock", True) not in db.calls
    assert ("change", "stock", False, True) in db.calls  # set_values tuyệt đối, không điều kiện


def test_p0_demonstrates_lost_update_when_reads_interleave():
    """Hai giao dịch cùng đọc 10, mỗi giao dịch ghi 10 - 3 = 7: kho chỉ giảm 3 dù đã bán 6 (mất cập nhật);
    P1 trong cùng lịch giao tranh vẫn trừ đủ."""
    class Stale(MemDB):
        def one(self, table, key, *, lock=False):
            row = super().one(table, key, lock=lock)
            if table == "stock":
                self.stale = row["s_quantity"]
            return row

    db = Stale()
    ctx = TxnContext("p0")
    first = Request("a", "run", "new_order", 1, 1, 1, ((1, 3),), (1,))
    second = Request("b", "run", "new_order", 1, 1, 1, ((1, 3),), (1,))
    read_a = core.required(db.one("stock", {"s_w_id": 1, "s_i_id": 1}))["s_quantity"]
    read_b = core.required(db.one("stock", {"s_w_id": 1, "s_i_id": 1}))["s_quantity"]
    db.change("stock", {"s_w_id": 1, "s_i_id": 1}, set_values={"s_quantity": read_a - 3})
    db.change("stock", {"s_w_id": 1, "s_i_id": 1}, set_values={"s_quantity": read_b - 3})
    assert db.quantity(1) == 7  # đã bán 6 nhưng kho chỉ giảm 3
    fresh = MemDB()
    for request in (first, second):
        core.take_stock(fresh, request, TxnContext("p1"), 1, 3)
    assert fresh.quantity(1) == 4
    assert ctx.variant == "p0"


def test_p2_hot_item_uses_slots_and_falls_through_to_the_remaining_ones(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB(inventory=9)
    assert prepare_slots(db, Dataset(1, 1, 5, 1, 1, 9), [1], 3) == {"slot_rows": 3, "hot_items": 1,
                                                                                 "slots": 3}
    assert db.quantity(1) == 0 and [r["ss_quantity"] for r in db.tables["stock_slot"]] == [3, 3, 3]
    ctx = TxnContext("p2", 3, frozenset({1}), rng=random.Random(1))
    for n in range(3):
        execute(db, order([(1, 3)], n), ctx)  # mỗi đơn vét cạn đúng một slot, dù slot chọn đầu tiên đã hết
    assert [r["ss_quantity"] for r in db.tables["stock_slot"]] == [0, 0, 0]
    assert ctx.slot_items == 3 and ctx.slot_attempts >= 3
    with pytest.raises(DBError) as error:
        execute(db, order([(1, 1)], 9), ctx)
    assert error.value.category == "out_of_stock"
    assert db.quantity(1) == 0  # món nóng không đụng tới dòng stock


def test_p2_non_hot_items_use_the_plain_conditional_update(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    ctx = TxnContext("p2", 3, frozenset({1}))
    execute(db, order([(2, 4)]), ctx)
    assert db.quantity(2) == 6 and ctx.slot_attempts == 0


def test_slot_quantities_sum_to_inventory():
    for inventory, slots in ((1000, 1), (1000, 3), (1000, 27), (10**9, 9), (5, 27)):
        parts = slot_quantities(inventory, slots)
        assert sum(parts) == inventory and len(parts) == slots and min(parts) >= 0


def test_order_id_batch_reserves_outside_the_order_transaction(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB(initial_next=3001)
    ctx = TxnContext("p1", order_id_batch=4)
    for n in range(9):
        execute(db, order([(1, 1)], n), ctx)  # MemDB.atomic khẳng định không có giao dịch lồng nhau
    ids = [row["o_id"] for row in db.tables["orders"]] if db.tables["orders"] and "o_id" in db.tables["orders"][0] \
        else [row["o_id"] for row in db.tables["orders"]]
    assert ids == list(range(3001, 3010))
    assert db.match("district", {})[0]["d_next_o_id"] == 3001 + 12  # 3 lô x 4 mã
    reservations = sum(1 for c in db.calls if c == ("one", "district", True))
    assert reservations == 3  # 9 đơn, lô 4: đúng 3 lần chạm vào dòng district


def test_order_id_batch_gap_after_abort_never_reuses_an_id(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB(inventory=1, initial_next=10)
    ctx = TxnContext("p1", order_id_batch=5)
    with pytest.raises(DBError):
        execute(db, order([(1, 2)]), ctx)  # hết hàng: rollback, mã 10 bị bỏ
    execute(db, order([(1, 1)], 1), ctx)
    assert [row["o_id"] for row in db.tables["orders"]] == [11]


def test_without_batch_every_order_touches_the_district_row(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    for n in range(3):
        execute(db, order([(1, 1)], n), TxnContext("p1"))
    assert sum(1 for c in db.calls if c == ("one", "district", True)) == 3
    assert db.match("district", {})[0]["d_next_o_id"] == 5


def test_validator_sums_slots_and_flags_a_negative_slot_or_missing_units():
    stock = [dict(s_w_id=1, s_i_id=i, s_quantity=10) for i in (2, 3, 4, 5)]
    stock.append(dict(s_w_id=1, s_i_id=1, s_quantity=0))
    order_row = dict(o_w_id=1, o_d_id=1, o_id=2, o_ol_cnt=1, request_id="run-a", run_id="run")
    line = dict(ol_w_id=1, ol_d_id=1, ol_o_id=2, ol_number=1, ol_supply_w_id=1, ol_i_id=1, ol_quantity=3,
                run_id="run")
    slots = [dict(ss_w_id=1, ss_i_id=1, ss_slot=0, ss_quantity=4), dict(ss_w_id=1, ss_i_id=1, ss_slot=1, ss_quantity=3)]
    good = check(DATASET, "run", ["run-a"], stock, [order_row], [line], slots)
    assert good["status"] == "VALID", good["errors"]
    lost = check(DATASET, "run", ["run-a"], stock, [order_row], [line],
                 [slots[0], dict(slots[1], ss_quantity=5)])
    assert lost["rules"]["reconciliation"] is False
    negative = check(DATASET, "run", ["run-a"], stock, [order_row], [line],
                     [dict(slots[0], ss_quantity=-1), dict(slots[1], ss_quantity=8)])
    assert negative["rules"]["nonnegative"] is False
    # Không truyền slot khi tồn nằm ở slot nghĩa là mất hàng: phải bị phát hiện.
    assert check(DATASET, "run", ["run-a"], stock, [order_row], [line])["status"] == "INVALID"


def test_settings_validate_hotspot_fields():
    from dataclasses import replace
    from flashsale.config import read_settings
    from pathlib import Path
    base = read_settings(Path("configs/smoke.toml"))
    assert (base.variant, base.slots, base.order_id_batch) == ("legacy", 1, 0)
    assert replace(base, variant="p2", slots=9, order_id_batch=50).variant == "p2"
    for bad in (dict(variant="p9"), dict(slots=0), dict(hot_items=0), dict(order_id_batch=-1)):
        with pytest.raises(ValueError):
            replace(base, **bad)
    assert isinstance(base, Settings)


def test_runner_context_is_none_for_2_1_and_hot_set_only_for_p2():
    from dataclasses import replace
    from flashsale.benchmark.runner import make_context
    from flashsale.config import read_settings
    from flashsale.workload.generator import Zipf
    from pathlib import Path
    base = read_settings(Path("configs/smoke.toml"))
    zipf = Zipf(base.dataset.items, 0, base.seed, False)
    assert make_context(base, zipf, 1, 0) is None
    p1 = make_context(replace(base, variant="p1"), zipf, 1, 0)
    assert p1.variant == "p1" and p1.hot_items == frozenset()
    p2 = make_context(replace(base, variant="p2", slots=3, hot_items=4), zipf, 1, 0)
    assert p2.hot_items == frozenset(zipf.item_ids[:4])
    assert make_context(replace(base, order_id_batch=10), zipf, 1, 0).order_id_batch == 10
    # Cùng seed, repetition, worker: cùng dãy chọn slot (tái lập được).
    again = make_context(replace(base, variant="p2", slots=3, hot_items=4), zipf, 1, 0)
    assert [p2.rng.random() for _ in range(3)] == [again.rng.random() for _ in range(3)]


def test_slot_ddl_and_extra_table_do_not_change_the_nine_tables():
    from flashsale.data.schema import TABLES, ddl
    assert len(TABLES) == 9 and "stock_slot" not in TABLES
    statement = ddl("stock_slot", True)
    assert "PRIMARY KEY (ss_w_id,ss_i_id,ss_slot) CLUSTERED" in statement
    assert "FOREIGN KEY" not in statement


def test_summary_reports_slot_attempts_per_item():
    from flashsale.benchmark.metrics import Phase
    phase = Phase()
    assert phase.summary(1)["slot_attempts_per_item"] is None
    phase.slot_attempts, phase.slot_items = 30, 20
    assert phase.summary(1)["slot_attempts_per_item"] == 1.5
