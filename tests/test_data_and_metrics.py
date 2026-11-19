import csv
import json

from flashsale.benchmark.metrics import Phase, write_result
from flashsale.config import Dataset
from flashsale.data.loader import rows_for
from flashsale.data.schema import TABLES, ddl
from flashsale.validation.checks import check
from flashsale.workload.generator import Request
from flashsale.workload.retry import Outcome


def test_nine_tables_and_initial_order_lines():
    cfg = Dataset(1, 2, 20, 20, 20, 1000)
    assert len(TABLES) == 9
    orders = list(rows_for("orders", cfg, 78))
    lines = list(rows_for("order_line", cfg, 78))
    assert len(orders) == 40
    assert 200 <= len(lines) <= 600
    assert len(list(rows_for("new_order", cfg, 78))) == 12
    for district in (1, 2):
        assert len({row["o_c_id"] for row in orders if row["o_d_id"] == district}) == 20
    for order in orders:
        expected = order["o_ol_cnt"]
        assert sum(o["ol_d_id"] == order["o_d_id"] and o["ol_o_id"] == order["o_id"]
                   for o in lines) == expected
    assert "SHARD_ROW_ID_BITS = 4 PRE_SPLIT_REGIONS = 4" in ddl("history", True)


def test_ddl_has_no_foreign_keys_by_default():
    assert all("FOREIGN KEY" not in ddl(name, False) for name in TABLES)
    assert "FOREIGN KEY" in ddl("history", False, foreign_keys=True)
    assert "UNIQUE KEY uq_request_id" in ddl("orders", False)


def test_cpu_warnings_only_for_sql_tier():
    from flashsale.benchmark.runner import cpu_warnings
    limits = {"tidb": {"cpus": 0.75}, "pd": {"cpus": 0.25}, "tikv1": {"cpus": 1}}
    assert cpu_warnings({"tidb": 70, "pd": 5, "tikv1": 99}, limits) == ["tidb_cpu_93pct_of_limit"]
    assert cpu_warnings({"tidb": None, "tikv1": 99}, limits) == []
    assert cpu_warnings({"mysql": 399}, {"mysql": {"cpus": 4}}) == []


def test_validator_distinguishes_two_directions_and_duplicates():
    cfg = Dataset(1, 1, 3, 1, 1, 10)
    stock = [dict(s_w_id=1, s_i_id=i, s_quantity=q) for i, q in enumerate((8, -1, 11), 1)]
    order = dict(o_w_id=1, o_d_id=1, o_id=2, o_ol_cnt=1, request_id="run-a", run_id="run")
    line = dict(ol_w_id=1, ol_d_id=1, ol_o_id=2, ol_number=1, ol_supply_w_id=1,
                ol_i_id=1, ol_quantity=2, run_id="run")
    assert check(cfg, "run", ["run-a"], [stock[0], *[dict(s_w_id=1, s_i_id=i, s_quantity=10)
                                                       for i in (2, 3)]], [order], [line])["status"] == "VALID"
    result = check(cfg, "run", ["run-a", "run-client-only"], stock,
                   [order, {**order, "o_id": 3}], [line])
    assert result["status"] == "INVALID"
    assert not any(result["rules"].values())
    assert {row["delta"] for row in result["errors"]["reconciliation"] if "delta" in row} == {11, -1}
    assert {entry["request_id"] for entry in result["errors"]["idempotency"]} == {"run-a", "run-client-only"}


def test_metrics_and_export(tmp_path):
    phase = Phase()
    req = Request("run-1", "run", "new_order", 1, 1, 1, ((1, 1),), (1,))
    for latency in range(1, 101):
        phase.record(req, Outcome("success", 1, {"deadlock": 1}, latency), True)
    phase.record(req, Outcome("out_of_stock", 0, {"out_of_stock": 1}, 7), True)
    phase.record(req, Outcome("success", 0, {}, 20), False)
    summary = phase.summary(5)
    assert (summary["p50_ms"], summary["p95_ms"], summary["p99_ms"], summary["tps"]) == (50, 95, 99, 20)
    assert summary["error_counts"]["deadlock"] == 100
    # Hết hàng là kết quả nghiệp vụ, không tính vào tỉ lệ hủy.
    assert summary["abort_pct"] == 0 and summary["out_of_stock_pct"] == 100 / 101
    assert summary["retry_pct"] == 10000 / 101
    aborted = Phase()
    aborted.record(req, Outcome("deadlock", 5, {"deadlock": 6}, 3), True)
    aborted.record(req, Outcome("success", 0, {}, 3), True)
    assert aborted.summary(1)["abort_pct"] == 50 and aborted.summary(1)["out_of_stock_pct"] == 0
    assert summary["drained_requests"] == 1
    result = dict(schema_version=1, run_id="run", engine="mysql", version="example", label="smoke",
                  inventory_mode="smoke", repetition=1, seed=4, concurrency=2, warehouse_mode="uniform",
                  theta=0, hot_item=False, resource_limits={}, warmup=Phase().summary(0), measurement=summary,
                  theoretical_selection=dict(rank1_pct=5, top100_pct=100), lock_wait_ms=None,
                  server_deadlocks=None, container_cpu_pct=None,
                  validation={"status": "VALID", "rules": {"nonnegative": True}})
    write_result(tmp_path, result)
    parsed = json.loads((tmp_path / "result.json").read_text())
    with (tmp_path / "result.csv").open(newline="") as stream:
        warmup, measurement = list(csv.DictReader(stream))
    assert parsed == result
    assert warmup["p50_ms"] == "null" and float(measurement["tps"]) == parsed["measurement"]["tps"]
    assert json.loads(measurement["error_counts"]) == parsed["measurement"]["error_counts"]


def test_idempotency_off_schema_and_fingerprint():
    from flashsale.data.loader import fingerprint
    off = ddl("orders", False, idempotency=False)
    assert "UNIQUE" not in off and "KEY ix_request_id (request_id)" in off
    assert "UNIQUE KEY uq_request_id" in ddl("history", True)
    assert "UNIQUE" not in ddl("history", True, idempotency=False)
    cfg = Dataset(1, 1, 3, 1, 1, 10)
    assert fingerprint(cfg, 1) == fingerprint(cfg, 1, True) != fingerprint(cfg, 1, False)


def test_every_profile_loads_and_matches_the_document():
    from pathlib import Path
    from flashsale.config import read_settings
    profiles = {path.stem: read_settings(path) for path in Path("configs").glob("*.toml")}
    assert {"baseline", "baseline-single-warehouse", "baseline-1client", "performance", "correctness",
            "payment-ytd", "idempotency-off", "smoke"} <= set(profiles)
    for name, cfg in profiles.items():
        if name == "smoke":
            continue
        assert (cfg.dataset.warehouses, cfg.dataset.districts, cfg.dataset.items) == (10, 10, 100000)
        assert (cfg.warmup_seconds, cfg.measurement_seconds) == (30, 60)
    assert profiles["baseline"].theta == 0 and profiles["baseline"].warehouse_mode == "uniform"
    assert profiles["baseline-single-warehouse"].warehouse_mode == "single-warehouse"
    assert profiles["baseline-1client"].concurrency == 1
    assert profiles["payment-ytd"].payment_ytd and not profiles["baseline"].payment_ytd
    assert profiles["correctness"].dataset.inventory == 1000
    assert profiles["performance"].dataset.inventory == 10**9
    assert all(profile.idempotency for name, profile in profiles.items() if name != "idempotency-off")


def test_compose_budgets_equal_across_engines():
    import re
    from pathlib import Path
    from flashsale.infra import BUDGET_CPUS, BUDGET_MEMORY_BYTES

    units = {"m": 1024 ** 2, "g": 1024 ** 3}

    def limits(text):
        return [(float(c), int(m) * units[u])
                for c, m, u in re.findall(r"cpus: ([\d.]+)\s+mem_limit: (\d+)([mg])", text)]

    def total(name):
        text = Path("docker", f"compose.{name}.yml").read_text(encoding="utf-8")
        head, _, services = text.partition("services:")
        copies = 3 if "x-tikv" in head else 1  # tikv1..3 kế thừa anchor
        pairs = [(c * copies, m * copies) for c, m in limits(head)] + limits(services)
        return sum(c for c, _ in pairs), sum(m for _, m in pairs)

    for name in ("mysql", "mongo", "tidb"):
        assert total(name) == (BUDGET_CPUS, BUDGET_MEMORY_BYTES), name


def test_validate_includes_document_cross_check():
    from flashsale.validation.checks import validate

    class FakeDB:
        def __init__(self, violations):
            self.violations = violations

        def rows(self, table, fields, *, tagged=False):
            return iter([dict(s_w_id=1, s_i_id=i, s_quantity=10) for i in (1, 2, 3)] if table == "stock" else [])

        def doc_reconciliation(self, inventory, initial_orders):
            assert (inventory, initial_orders) == (10, 1)
            return self.violations

    cfg = Dataset(1, 1, 3, 1, 1, 10)
    clean = validate(FakeDB([]), cfg, "run", [])
    assert clean["status"] == "VALID" and clean["doc_check"]["violations"] == 0
    bad = validate(FakeDB([{"s_w_id": 1, "s_i_id": 2, "sold": 3}]), cfg, "run", [])
    assert bad["status"] == "INVALID" and bad["rules"]["reconciliation"] is False
    assert bad["errors"]["reconciliation"][-1]["doc_sql_check"][0]["sold"] == 3
