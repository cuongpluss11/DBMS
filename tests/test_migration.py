"""Mục 2.4 (Online Schema Evolution): kiểm đơn vị cho hàm ol_discount, giao dịch 'Xem đơn cũ',
ba chiến lược chuyển dữ liệu (Eager P1, Batch P2, Lazy P3), chuỗi p99 mỗi giây và validator migration."""
from collections import Counter
from contextlib import contextmanager
import copy
import csv
from dataclasses import replace
from pathlib import Path

import pytest

from flashsale.benchmark.metrics import Phase, write_series
from flashsale.config import Dataset, read_settings, uses_migration
from flashsale.data.loader import reset, rows_for
from flashsale.migration import (
    compute_discount,
    discount_rate,
    load_item_prices,
    migrate_background,
    prepare_migration,
    validate_migration,
)
from flashsale.transactions import core
from flashsale.transactions.core import TxnContext, execute
from flashsale.validation.checks import validate
from flashsale.workload.generator import Generator, Request, Zipf
from flashsale.workload.retry import Outcome


class MigrationMemDB:
    """Adapter trong bộ nhớ với dữ liệu đơn cũ nạp sẵn để kiểm thử đầy đủ mục 2.4 mà không cần DBMS."""

    def __init__(self, dataset: Dataset, seed: int = 42):
        self.tables = {
            name: list(rows_for(name, dataset, seed))
            for name in ("warehouse", "item", "district", "stock", "customer",
                         "history", "orders", "new_order", "order_line")
        }
        self.tables["stock_slot"] = []
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

    def many(self, table, key):
        self.calls.append(("many", table))
        return [dict(row) for row in self.match(table, key)]

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

    def rows(self, table, fields, *, tagged=False):
        for row in self.tables[table]:
            if tagged and not row.get("run_id"):
                continue
            yield {field: row.get(field) for field in fields}

    def delete_tagged(self, table, field):
        before = len(self.tables[table])
        self.tables[table] = [row for row in self.tables[table] if not row.get(field)]
        return before - len(self.tables[table])


def test_discount_rate_and_formula_across_three_price_tiers():
    assert discount_rate(100) == 0 and discount_rate(2499) == 0
    assert discount_rate(2500) == 5 and discount_rate(4999) == 5
    assert discount_rate(5000) == 10 and discount_rate(10000) == 10
    assert compute_discount(5, 2499) == 0
    assert compute_discount(3, 2500) == (3 * 2500 * 5) // 100 == 375
    assert compute_discount(7, 5000) == (7 * 5000 * 10) // 100 == 3500
    assert compute_discount(1, 3333) == (1 * 3333 * 5) // 100 == 166


def test_generator_old_order_read_pct_preserves_one_to_one_write_ratio():
    base = read_settings(Path("configs/smoke.toml"))
    zipf = Zipf(base.dataset.items, base.theta, base.seed, False)
    cfg = replace(base, old_order_read_pct=25.0)
    gen = Generator(cfg, zipf, "run", 1, 0, "measurement")
    reqs = [gen.next() for _ in range(2000)]
    counts = Counter(r.kind for r in reqs)
    assert 420 <= counts["old_order"] <= 580
    # Phần còn lại (100% - q) luôn chia đều 1:1 giữa new_order và payment.
    assert abs(counts["new_order"] - counts["payment"]) <= 1
    for r in reqs:
        if r.kind == "old_order":
            assert 1 <= r.warehouse <= base.dataset.warehouses
            assert 1 <= r.district <= base.dataset.districts
            assert 1 <= r.order_id <= base.dataset.initial_orders
            assert not r.idempotent


def test_old_order_dual_read_vs_lazy_on_demand_migration(monkeypatch):
    monkeypatch.setattr(core, "lookup", lambda db, req: None)
    ds = Dataset(1, 1, 10, 5, 3, 100)
    db = MigrationMemDB(ds)
    # Đặt giá 3 mặt hàng đại diện cho 3 bậc r = 0, 5, 10.
    for row in db.tables["item"]:
        row["i_price"] = 6000 if row["i_id"] % 3 == 0 else (3000 if row["i_id"] % 3 == 1 else 1000)
    prices = load_item_prices(db)
    prep = prepare_migration(db, ds)
    assert prep["unmigrated_initial_rows"] == len(db.tables["order_line"]) > 0

    req = Request("r-1", "run", "old_order", 1, 1, 0, order_id=1, idempotent=False)
    # Ở Eager (P1) hoặc Batch (P2): đọc đơn cũ trả về ol_discount tính tạm nhưng không ghi vào DB.
    eager_ctx = TxnContext("p1", migration_strategy="eager", item_prices=prices)
    execute(db, req, eager_ctx)
    assert eager_ctx.migrated_on_demand == 0 and not eager_ctx.last_read_migrated
    assert all(r["ol_mig_state"] == "UNMIGRATED" for r in db.match("order_line", {"ol_o_id": 1}))

    # Ở Lazy (P3): đọc đơn cũ gặp dòng UNMIGRATED sẽ cập nhật có điều kiện ngay vào DB.
    lazy_ctx = TxnContext("p1", migration_strategy="lazy", item_prices=prices)
    execute(db, req, lazy_ctx)
    order1_lines = db.match("order_line", {"ol_o_id": 1})
    assert lazy_ctx.migrated_on_demand == len(order1_lines) and lazy_ctx.last_read_migrated
    assert all(r["ol_mig_state"] == "MIGRATED" and r["ol_discount"] is not None for r in order1_lines)

    # Đọc lại đơn đã MIGRATED: không cần chuyển lại, last_read_migrated = False.
    execute(db, req, lazy_ctx)
    assert lazy_ctx.migrated_on_demand == len(order1_lines) and not lazy_ctx.last_read_migrated

    # Giả lập tranh chấp migration: một worker khác chuyển dòng ngay sau khi đọc nhưng trước khi change().
    real_change = db.change

    def racing_change(table, key, **kw):
        for r in db.match(table, {k: v for k, v in key.items() if k != "ol_mig_state"}):
            r["ol_mig_state"] = "MIGRATED"
        return real_change(table, key, **kw)

    monkeypatch.setattr(db, "change", racing_change)
    req2 = Request("r-2", "run", "old_order", 1, 1, 0, order_id=2, idempotent=False)
    execute(db, req2, lazy_ctx)
    assert lazy_ctx.migration_conflicts == len(db.match("order_line", {"ol_o_id": 2}))


@pytest.mark.parametrize("strategy", ["eager", "batch", "lazy"])
def test_migration_strategies_complete_and_pass_validator_and_reset(monkeypatch, strategy):
    monkeypatch.setattr(core, "lookup", lambda db, req: None)
    ds = Dataset(1, 2, 10, 5, 4, 100)
    db = MigrationMemDB(ds)
    baseline_counts = {name: db.count(name) for name in db.tables if name != "stock_slot"}
    prices = load_item_prices(db)
    prepare_migration(db, ds)

    base_cfg = read_settings(Path("configs/smoke.toml"))
    cfg = replace(base_cfg, dataset=ds, migration_strategy=strategy, old_order_read_pct=25.0,
                  migration_batch_size=20, migration_sleep_ms=0.0, migration_delay_seconds=0.0)
    ctx = TxnContext("p1", migration_strategy=strategy, item_prices=prices)

    # Chạy xen kẽ giao dịch Xem đơn cũ và Đặt hàng mới trước/trong lúc worker migration chạy.
    execute(db, Request("read-1", "run", "old_order", 1, 1, 0, order_id=1, idempotent=False), ctx)
    new_req = Request("run-new-1", "run", "new_order", 1, 1, 1, ((1, 2), (2, 3)), (1, 2))
    execute(db, new_req, ctx)

    mig_stats = migrate_background(db, cfg, prices)
    assert mig_stats["strategy"] == strategy
    total_old = baseline_counts["order_line"]
    assert mig_stats["migrated_background"] + ctx.migrated_on_demand == total_old
    if strategy == "lazy":
        assert ctx.migrated_on_demand > 0 and mig_stats["migrated_background"] < total_old
    else:
        assert ctx.migrated_on_demand == 0 and mig_stats["migrated_background"] == total_old

    report = validate(db, ds, "run", [new_req.request_id], baseline_counts, migration=True)
    assert report["status"] == "VALID", report["errors"]
    assert report["rules"]["migration"] is True
    assert report["migration_check"]["unmigrated_rows"] == 0
    assert report["migration_check"]["wrong_discount_rows"] == 0

    # Cài lỗi sai giá trị ol_discount -> validator phải bắt được INVALID.
    db.tables["order_line"][0]["ol_discount"] = -999
    bad = validate(db, ds, "run", [new_req.request_id], baseline_counts, migration=True)
    assert bad["status"] == "INVALID" and bad["rules"]["migration"] is False

    # Cài lỗi còn sót dòng UNMIGRATED -> validator phải bắt được INVALID.
    db.tables["order_line"][0]["ol_mig_state"] = "UNMIGRATED"
    unmig = validate_migration(db, ds, baseline_counts, tagged_lines=2)
    assert not unmig["valid"] and unmig["unmigrated_rows"] == 1

    # Reset khôi phục cả số dòng lẫn trạng thái UNMIGRATED ban đầu.
    reset(db, ds)
    assert db.count("order_line") == baseline_counts["order_line"]
    assert all(r["ol_mig_state"] == "UNMIGRATED" and r["ol_discount"] is None for r in db.tables["order_line"])


def test_per_second_p99_and_read_split_metrics(tmp_path):
    phase = Phase()
    r_mig = Request("r1", "run", "old_order", 1, 1, 0, order_id=1, idempotent=False)
    r_clean = Request("r2", "run", "old_order", 1, 1, 0, order_id=2, idempotent=False)
    phase.record(r_mig, Outcome("success", 0, {}, 45.0), True, second=0, read_migrated=True)
    phase.record(r_clean, Outcome("success", 0, {}, 8.0), True, second=1, read_migrated=False)
    summary = phase.summary(2)
    assert summary["old_order_success"] == 2
    assert summary["read_migrated_p99_ms"] == 45.0
    assert summary["read_clean_p99_ms"] == 8.0
    assert phase.p99_series_list(3) == [45.0, 8.0, None]

    csv_path = tmp_path / "tps_per_second.csv"
    write_series(
        csv_path,
        {"warmup": [1], "measurement": [1, 1, 0]},
        {"warmup": [5.0], "measurement": [45.0, 8.0, None]},
        migration_window=(0, 1),
    )
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert rows[0]["phase"] == "warmup" and rows[0]["migrating"] == "0"
    assert rows[1]["phase"] == "measurement" and rows[1]["p99_ms"] == "45.0" and rows[1]["migrating"] == "1"
    assert rows[3]["p99_ms"] == "null" and rows[3]["migrating"] == "0"


def test_migration_settings_validation():
    base = read_settings(Path("configs/migration.toml"))
    assert uses_migration(base.migration_strategy) and base.migration_strategy == "eager"
    assert base.old_order_read_pct == 25.0
    for bad in (
        dict(migration_strategy="unknown"),
        dict(old_order_read_pct=-1.0),
        dict(old_order_read_pct=101.0),
        dict(migration_batch_size=0),
        dict(migration_sleep_ms=-0.1),
        dict(migration_delay_seconds=-1.0),
    ):
        with pytest.raises(ValueError):
            replace(base, **bad)


def test_sql_eager_path_uses_warehouse_transaction_and_primary_key_prefix():
    """Kiểm chứng nhánh SQL MySQL của prepare_migration, migrate_background(eager) và validate_migration."""
    queries = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, statement, params=()):
            queries.append((statement, params))
            return 30

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    class FakeSQL:
        tidb = False
        connection = FakeConn()

        @contextmanager
        def atomic(self):
            queries.append(("BEGIN", ()))
            yield
            queries.append(("COMMIT", ()))

        def query(self, statement, params=()):
            queries.append((statement, params))
            if "SHOW COLUMNS" in statement:
                return [{"Field": "ol_w_id"}] if "ALTER TABLE" not in str(queries) else [
                    {"Field": "ol_discount"}, {"Field": "ol_mig_state"}
                ]
            if "COUNT(*)" in statement:
                return [{"cnt": 0 if "ol_mig_state <> 'UNMIGRATED'" in statement else 60}]
            if "SUM(" in statement:
                return [{"old_rows": 60, "unmigrated": 0, "wrong_discount": 0}]
            return []

        def count(self, table):
            return 60

    db = FakeSQL()
    ds = Dataset(1, 2, 10, 5, 3, 100)
    prep = prepare_migration(db, ds)
    assert prep["unmigrated_initial_rows"] == 60
    assert any("ALTER TABLE order_line ADD COLUMN ol_discount" in q[0] for q in queries)

    cfg = replace(read_settings(Path("configs/smoke.toml")), dataset=ds,
                  migration_strategy="eager", migration_delay_seconds=0.0)
    stats = migrate_background(db, cfg)
    assert stats["migrated_background"] == 60 and stats["batches"] == 1
    assert any("ol.ol_w_id = %s AND ol.ol_d_id = %s" in q[0] for q in queries)

    check = validate_migration(db, ds, {"order_line": 60}, tagged_lines=0)
    assert check["valid"] and check["unmigrated_rows"] == 0 and check["wrong_discount_rows"] == 0
