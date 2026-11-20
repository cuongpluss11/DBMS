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
            "payment-ytd", "idempotency-off", "baseline-tuned", "baseline-cross",
            "baseline-cross-1client", "smoke"} <= set(profiles)
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


def test_warmup_series_and_stability():
    from flashsale.benchmark.metrics import warmup_stability
    req = Request("run-1", "run", "new_order", 1, 1, 1, ((1, 1),), (1,))
    phase = Phase()
    for second in (0, 0, 2):
        phase.record(req, Outcome("success", 0, {}, 1), True, second)
    phase.record(req, Outcome("success", 0, {}, 1), False, 1)
    assert phase.series_list(4) == [2, 0, 1, 0]
    other = Phase()
    other.record(req, Outcome("success", 0, {}, 1), True, 0)
    phase.merge(other)
    assert phase.series_list(1) == [3]
    steady = warmup_stability([100] * 10, [110] * 10)
    assert round(steady["drift_pct"], 6) == 10 and warmup_stability([1], [1])["drift_pct"] is None


def test_mysql_variant_label_matches_buffer_pool():
    import pytest
    from pathlib import Path
    from flashsale.cli import check_mysql_variant
    from flashsale.config import read_settings
    base, tuned = read_settings(Path("configs/baseline.toml")), read_settings(Path("configs/baseline-tuned.toml"))
    check_mysql_variant(base, {"buffer_pool_bytes": 128 * 1024 ** 2})
    check_mysql_variant(tuned, {"buffer_pool_bytes": 3 * 1024 ** 3})
    with pytest.raises(ValueError):
        check_mysql_variant(base, {"buffer_pool_bytes": 3 * 1024 ** 3})
    with pytest.raises(ValueError):
        check_mysql_variant(tuned, {"buffer_pool_bytes": 128 * 1024 ** 2})


def test_endpoint_host_and_remote_mode(monkeypatch):
    import json
    import pytest
    from flashsale import infra
    monkeypatch.delenv("FLASHSALE_DB_HOST", raising=False)
    monkeypatch.delenv("FLASHSALE_REMOTE_NODES", raising=False)
    assert infra.endpoint("mysql").host == "127.0.0.1" and infra.remote_nodes() is None
    monkeypatch.setenv("FLASHSALE_DB_HOST", "10.20.1.5")
    assert infra.endpoint("mysql").host == "10.20.1.5"
    nodes = {"mysql": {"host": "10.20.1.5", "cpus": 12, "memory_bytes": 24 * 1024 ** 3}}
    monkeypatch.setenv("FLASHSALE_REMOTE_NODES", json.dumps(nodes))
    limits = infra.container_limits("mysql")
    assert limits["mysql"]["cpus"] == 12 and limits["mysql"]["remote"] and not infra.active_engines()["mysql"]
    infra.enforce_one("mysql")  # remote: không kiểm Docker cục bộ
    with pytest.raises(RuntimeError):
        infra.start("mysql")
    bad = {"mysql": {"host": "10.20.1.5", "cpus": 8, "memory_bytes": 16 * 1024 ** 3}}
    monkeypatch.setenv("FLASHSALE_REMOTE_NODES", json.dumps(bad))
    with pytest.raises(RuntimeError):
        infra.container_limits("mysql")  # khác ngân sách 12 vCPU / 24 GiB
    monkeypatch.setenv("FLASHSALE_REMOTE_BUDGET_CPUS", "8")
    monkeypatch.setenv("FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES", str(16 * 1024 ** 3))
    assert infra.container_limits("mysql")["mysql"]["cpus"] == 8
    monkeypatch.setenv("FLASHSALE_REMOTE_NODES", json.dumps({"mysql": {"host": "x"}}))
    with pytest.raises(ValueError):
        infra.remote_nodes()


def test_node_exporter_cpu_sampling(monkeypatch):
    import json
    from flashsale import infra
    text = "\n".join([
        '# HELP node_cpu_seconds_total x',
        'node_cpu_seconds_total{cpu="0",mode="idle"} 900',
        'node_cpu_seconds_total{cpu="0",mode="iowait"} 50',
        'node_cpu_seconds_total{cpu="0",mode="user"} 30.5',
        'node_cpu_seconds_total{cpu="1",mode="system"} 19.5',
        'other_metric{mode="user"} 7'])
    assert infra.parse_node_cpu(text) == (50.0, 1000.0)
    monkeypatch.setenv("FLASHSALE_REMOTE_NODES", json.dumps(
        {"mysql": {"host": "h1", "cpus": 12, "memory_bytes": 24 * 1024 ** 3}}))
    readings = iter([(10.0, 0), (1.0, 0), (14.0, 0), (3.0, 0)])  # lần 1: mysql, loadgen; lần 2: mysql, loadgen
    monkeypatch.setattr(infra, "node_cpu_seconds", lambda host: next(readings))
    ticks = iter([100.0, 102.0])
    monkeypatch.setattr(infra.time, "monotonic", lambda: next(ticks))
    sample = infra.cpu_sampler(infra.container_limits("mysql"))
    assert sample() == {}  # lần đầu chỉ lấy mốc
    values = sample()
    assert values["mysql"] == 100 * 4 / 2 and values["loadgen"] == 100 * 2 / 2


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
