"""Unit test cho thí nghiệm E1 (mục 2.4): DDL gốc dưới tải & kẹt Metadata Lock."""

from pathlib import Path
import json

from flashsale.e1_ddl import (
    E1_INDEX_NAME,
    cleanup_e1_schema,
    compute_max_freeze_seconds,
    execute_ddl_action,
    summarize_e1,
)


class FakeSQLAdapter:
    def __init__(self, fail_times: int = 0) -> None:
        self.cols = {"ol_w_id", "ol_d_id", "ol_o_id", "ol_number"}
        self.indexes = {"PRIMARY"}
        self.fail_times = fail_times
        self.executed: list[str] = []

    def query(self, sql: str, params=()):
        self.executed.append(sql)
        if sql.startswith("SHOW COLUMNS"):
            return [{"Field": c} for c in self.cols]
        if sql.startswith("SHOW INDEX"):
            return [{"Key_name": idx} for idx in self.indexes]
        if sql.startswith("SET SESSION lock_wait_timeout"):
            return []
        if "ADD COLUMN" in sql:
            if self.fail_times > 0:
                self.fail_times -= 1
                raise RuntimeError("(1205, 'Lock wait timeout exceeded; try restarting transaction')")
            self.cols.update({"ol_discount", "ol_mig_state"})
            return []
        if "ADD INDEX" in sql:
            self.indexes.add(E1_INDEX_NAME)
            return []
        if "DROP COLUMN" in sql:
            self.cols.discard("ol_discount")
            self.cols.discard("ol_mig_state")
            return []
        if "DROP INDEX" in sql:
            self.indexes.discard(E1_INDEX_NAME)
            return []
        return []


class FakeMongoCollection:
    def __init__(self) -> None:
        self.indexes = {"_id_": {}, "logical_pk": {}}

    def index_information(self):
        return dict(self.indexes)

    def create_index(self, keys, name: str):
        self.indexes[name] = {"key": keys}
        return name

    def drop_index(self, name: str):
        self.indexes.pop(name, None)


class FakeMongoAdapter:
    def __init__(self) -> None:
        self.db = {"order_line": FakeMongoCollection()}


def test_compute_max_freeze_seconds() -> None:
    from flashsale.benchmark.metrics import warmup_stability

    assert compute_max_freeze_seconds([1200.0, 1150.0, 0.0, 0.0, 0.0, 900.0, 0.0, 0.0]) == 3
    assert compute_max_freeze_seconds([500.0, 600.0, 700.0]) == 0
    assert compute_max_freeze_seconds([]) == 0
    ws = warmup_stability([100.0] * 10, [100.0] * 10)
    assert ws["drift_pct"] == 0.0


def test_mysql_e1_instant_copy_index_and_cleanup() -> None:
    db = FakeSQLAdapter()
    r1 = execute_ddl_action(db, "mysql", "add_column_instant")
    assert r1["succeeded"] is True and r1["attempts"] == 1
    assert {"ol_discount", "ol_mig_state"}.issubset(db.cols)

    r2 = execute_ddl_action(db, "mysql", "add_index_inplace")
    assert r2["succeeded"] is True
    assert E1_INDEX_NAME in db.indexes

    cleanup_e1_schema(db)
    assert "ol_discount" not in db.cols
    assert "ol_mig_state" not in db.cols
    assert E1_INDEX_NAME not in db.indexes


def test_mysql_e1_short_lock_timeout_retries(monkeypatch) -> None:
    monkeypatch.setattr("flashsale.e1_ddl.time.sleep", lambda _: None)
    db = FakeSQLAdapter(fail_times=2)
    res = execute_ddl_action(db, "mysql", "mdl_timeout_retry", lock_wait_timeout=3, max_retries=5)
    assert res["succeeded"] is True
    assert res["attempts"] == 3
    assert res["lock_wait_timeouts"] == 2
    assert any("SET SESSION lock_wait_timeout = 3" in s for s in db.executed)


def test_mongo_e1_create_index_and_cleanup() -> None:
    db = FakeMongoAdapter()
    res = execute_ddl_action(db, "mongo", "create_index")
    assert res["succeeded"] is True
    assert E1_INDEX_NAME in db.db["order_line"].indexes
    cleanup_e1_schema(db)
    assert E1_INDEX_NAME not in db.db["order_line"].indexes


def test_summarize_e1_generates_csv_and_md(tmp_path: Path) -> None:
    run_dir = tmp_path / "abc123"
    run_dir.mkdir()
    (run_dir / "result.json").write_text(json.dumps({
        "experiment": "2.4-E1",
        "run_id": "abc123",
        "engine": "mysql",
        "scenario": "mdl_freeze",
        "repetition": 1,
        "validation": {"status": "VALID"},
        "warmup": {"tps": 1600.0},
        "measurement": {"tps": 420.5, "p99_ms": 58000.0},
        "ddl": {
            "succeeded": True,
            "duration_seconds": 60.2,
            "attempts": 1,
            "lock_wait_timeouts": 0,
            "max_freeze_seconds": 58,
            "peak_1s_p99_ms": 60100.0,
        },
        "lock_wait_ms": 120000,
    }), encoding="utf-8")

    summary = summarize_e1(tmp_path)
    assert summary["runs"] == 1
    assert (tmp_path / "E1_INDEX.csv").is_file()
    md = (tmp_path / "E1_SUMMARY.md").read_text(encoding="utf-8")
    assert "mdl_freeze" in md and "58" in md
