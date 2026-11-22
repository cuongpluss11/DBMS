"""Mục 2.3 (TiDB): đơn nhiều kho, khóa orders (nhóm D), đặt Region/leader và hệ số tăng tốc. Không cần DBMS: PD và
SHOW TABLE REGIONS được giả lập. Hành vi trên TiDB/PD thật chưa kiểm chứng (docs/experiment-2.3.md)."""
from dataclasses import replace
from pathlib import Path

import pytest

from flashsale.config import Dataset, read_settings
from flashsale.data import placement
from flashsale.data.placement import PD
from flashsale.data.schema import ddl
from flashsale.transactions import core
from flashsale.transactions.core import TxnContext, execute
from flashsale.workload.generator import Generator, Request, Zipf

from test_hotspot import MemDB, lookup_free


def settings(**kw):
    base = read_settings(Path("configs/smoke.toml"))
    dataset = Dataset(12, 2, 400, 10, 10, 10**9)
    values = dict(warehouse_mode="uniform", hot_item=False, theta=0, dataset=dataset)
    values.update(kw)
    return replace(base, **values)


def requests(cfg, count=400):
    zipf = Zipf(cfg.dataset.items, cfg.theta, cfg.seed, False)
    generator = Generator(cfg, zipf, "r" * 32, 1, 0, "measurement")
    return [r for r in (generator.next() for _ in range(count)) if r.kind == "new_order"]


def touched(req):
    return set(req.supply or (req.warehouse,))


def test_default_orders_touch_one_warehouse_and_keep_the_2_1_random_stream():
    cfg = settings()
    plain = requests(cfg)
    assert all(not r.supply for r in plain)
    older = Generator(read_settings(Path("configs/smoke.toml")), Zipf(20, 0, 2026, True), "r" * 32, 1, 0, "x")
    assert older.next().supply == ()


@pytest.mark.parametrize("low,high", [(2, 2), (3, 3), (4, 4), (3, 4)])
def test_multi_warehouse_orders_touch_exactly_the_requested_number_inside_the_group(low, high):
    cfg = settings(order_warehouses_min=low, order_warehouses_max=high, warehouse_groups=3)
    orders = requests(cfg)
    sizes = {len(touched(r)) for r in orders}
    assert sizes <= set(range(low, high + 1)) and max(sizes) == high
    for r in orders:
        assert len(r.supply) == len(r.items)
        groups = {placement.warehouse_group(w, 12, 3) for w in touched(r)}
        assert groups == {placement.warehouse_group(r.warehouse, 12, 3)}   # chỉ chọn kho cùng nhóm với kho nhà
        assert len(r.items) >= len(touched(r))


def test_multi_warehouse_order_debits_each_supply_warehouse_and_flags_all_local(monkeypatch):
    lookup_free(monkeypatch)
    db = MemDB()
    db.tables["stock"].extend(dict(s_w_id=2, s_i_id=i, s_quantity=10, s_ytd=0, s_order_cnt=0, s_dist_01="D" * 24)
                              for i in range(1, 6))
    req = Request("run-0", "run", "new_order", 1, 1, 1, ((1, 3), (2, 4)), (1, 1), idempotent=False, supply=(1, 2))
    execute(db, req, TxnContext("p1", lock_order=True))
    assert db.match("stock", {"s_w_id": 1, "s_i_id": 1})[0]["s_quantity"] == 7
    assert db.match("stock", {"s_w_id": 2, "s_i_id": 2})[0]["s_quantity"] == 6
    assert db.match("stock", {"s_w_id": 1, "s_i_id": 2})[0]["s_quantity"] == 10      # món 2 không lấy từ kho nhà
    assert [(row["ol_i_id"], row["ol_supply_w_id"]) for row in db.tables["order_line"]] == [(1, 1), (2, 2)]
    assert db.tables["orders"][0]["o_all_local"] == 0
    local = Request("run-1", "run", "new_order", 1, 1, 1, ((3, 1),), (1,), idempotent=False)
    execute(db, local, TxnContext("p1"))
    assert db.tables["orders"][1]["o_all_local"] == 1


def test_settings_reject_inconsistent_scaling_options():
    cfg = settings()
    for bad in (dict(order_warehouses_min=0), dict(order_warehouses_max=5), dict(order_warehouses_min=3,
                order_warehouses_max=2), dict(order_warehouses_max=2, hot_item=True),
                dict(order_warehouses_max=2, warehouse_mode="single-warehouse"), dict(orders_key="uuid"),
                dict(placement="group"), dict(placement="x"), dict(placement_scope="x"), dict(warehouse_groups=-1)):
        with pytest.raises(ValueError):
            replace(cfg, **bad)
    assert replace(cfg, placement="group", warehouse_groups=3, order_warehouses_max=3).placement == "group"


def test_orders_primary_key_variants_for_group_d():
    plain = ddl("orders", True)
    assert "PRIMARY KEY (o_w_id,o_d_id,o_id) CLUSTERED" in plain and "o_seq" not in plain
    auto = ddl("orders", True, orders_key="autoinc")
    assert "o_seq BIGINT NOT NULL AUTO_INCREMENT" in auto and "PRIMARY KEY (o_seq) CLUSTERED" in auto
    assert "UNIQUE KEY uq_order_key (o_w_id,o_d_id,o_id)" in auto
    random = ddl("orders", True, orders_key="auto_random")
    assert "o_seq BIGINT AUTO_RANDOM" in random and "AUTO_INCREMENT" not in random
    assert ddl("district", True, orders_key="auto_random") == ddl("district", True)
    from flashsale.data.loader import fingerprint
    cfg = Dataset(1, 1, 3, 1, 1, 10)
    assert fingerprint(cfg, 1) == fingerprint(cfg, 1, True, "composite")
    assert len({fingerprint(cfg, 1, True, key) for key in ("composite", "autoinc", "auto_random")}) == 3


def encode(key):
    """START_KEY như TiDB v8.5.7 hiển thị: t_<id>_r_ + (03 + 8 byte big-endian lật bit dấu) cho từng cột."""
    return "t_120_r_" + "".join("03" + f"{(v ^ (1 << 63)) & (2**64 - 1):016x}" for v in key)


class FakeCluster:
    """PD + TiDB giả: SHOW TABLE REGIONS trả Region theo thứ tự khóa; operator đổi leader ngay lập tức."""

    def __init__(self, stores=(1, 2, 3), replicas=1):
        self.stores = list(stores)
        self.replicas = replicas
        self.regions: dict[str, list[dict]] = {}
        self.next_id = 100
        self.schedule = {"leader-schedule-limit": 4, "region-schedule-limit": 2048, "hot-region-schedule-limit": 4,
                         "merge-schedule-limit": 8}
        self.paused: dict[str, int] = {}
        self.operators: list[dict] = []
        self.statements: list[str] = []
        self.ignore_operators = False
        self.size_split = False

    # --- PD transport
    def transport(self, method, path, body):
        if path == "/stores":
            return {"stores": [{"store": {"id": s, "address": f"tikv{s}", "state_name": "Up"}} for s in self.stores]}
        if path == "/config/replicate":
            return {"max-replicas": self.replicas}
        if path == "/config/schedule":
            if method == "POST":
                self.schedule.update(body)
            return dict(self.schedule)
        if path.startswith("/schedulers/"):
            self.paused[path.rsplit("/", 1)[1]] = body["delay"]
            return None
        if path == "/operators":
            self.operators.append(body)
            if not self.ignore_operators:
                for rows in self.regions.values():
                    for row in rows:
                        if row["REGION_ID"] == body["region_id"]:
                            row["LEADER_STORE_ID"] = body["to_store_id"]
            return None
        raise AssertionError(path)

    # --- TiDB
    def query(self, statement, values=()):
        self.statements.append(statement)
        if statement.startswith("SPLIT TABLE"):
            table = statement.split()[2]
            import re
            keys = [tuple(int(x) for x in group.split(",")) for group in re.findall(r"\(([^)]*)\)", statement)]
            rows = [{"REGION_ID": self.alloc(), "START_KEY": "t_120_", "LEADER_STORE_ID": self.stores[0]}]
            for key in keys:
                rows.append({"REGION_ID": self.alloc(), "START_KEY": encode(key), "LEADER_STORE_ID": self.stores[0]})
            if self.size_split and table == "stock":      # Region TiDB tự tách theo kích thước trong kho 7
                rows.append({"REGION_ID": self.alloc(), "START_KEY": encode((7, 15679)),
                             "LEADER_STORE_ID": self.stores[0]})
                rows.sort(key=lambda row: (row["START_KEY"] != "t_120_", row["START_KEY"]))
            self.regions[table] = rows
            return [{"TOTAL_SPLIT_REGION": len(keys)}]
        if statement.startswith("SHOW CONFIG"):
            return [{"Instance": "tikv1", "Name": "split.qps-threshold", "Value": "3000"}]
        if statement.startswith("SHOW TABLE"):
            return [dict(row) for row in self.regions[statement.split()[2]]]
        raise AssertionError(statement)

    def alloc(self):
        self.next_id += 1
        return self.next_id


def run_layout(cluster, cfg, slots=None, hot=(1, 2, 3, 4, 5, 6)):
    pd = PD("http://pd", cluster.transport)
    return placement.apply_layout(cluster, pd, cfg, list(hot), slots, timeout=5, sleep=lambda s: None)


def leaders(cluster, table):
    return [row["LEADER_STORE_ID"] for row in cluster.regions[table]]


def test_spread_layout_splits_by_warehouse_boundary_and_round_robins_leaders():
    cluster = FakeCluster()
    cfg = settings(placement="spread")
    evidence = run_layout(cluster, cfg)
    assert any(st.startswith("SPLIT TABLE stock BY (2, 0), (3, 0)") for st in cluster.statements)     # đủ cột khóa, như tài liệu
    assert leaders(cluster, "stock") == [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3]  # kho w -> TiKV (w-1) mod 3
    assert evidence["tables"]["stock"] == {"1": 4, "2": 4, "3": 4}
    assert all(op["name"] == "transfer-peer" and "from_store_id" in op for op in cluster.operators)  # 1 bản sao
    assert set(cluster.paused) >= set(placement.SCHEDULERS) and all(v == 0 for k, v in cluster.schedule.items()
                                                                   if k in placement.LIMITS)


def test_size_split_regions_follow_their_warehouse_leader():
    cluster = FakeCluster()
    cluster.size_split = True
    run_layout(cluster, settings(placement="spread"))
    rows = cluster.regions["stock"]
    assert len(rows) == 13
    in_seven = [row["LEADER_STORE_ID"] for row in rows if row["START_KEY"] in (encode((7, 0)), encode((7, 15679)))]
    assert in_seven == [1, 1]                                # kho 7 -> TiKV (7-1) mod 3 + 1 = 1, cả hai Region


def test_region_key_decoding_matches_the_observed_tidb_format():
    from flashsale.data.placement import region_key
    assert region_key("t_120_") is None
    assert region_key("t_120_r_038000000000000002038000000000000000") == (2, 0)
    assert region_key("t_120_r_038000000000000007038000000000003d3f") == (7, 15679)
    assert region_key("t_120_r_0380000000000000010380000000000000030380000000000000ff") == (1, 3, 255)
    assert region_key("t_120_r_0bxyz") is None


def test_group_layout_puts_a_whole_warehouse_group_on_one_tikv_and_uses_transfer_leader_with_replicas():
    cluster = FakeCluster(replicas=3)
    cfg = settings(placement="group", warehouse_groups=3, placement_scope="all")
    run_layout(cluster, cfg)
    assert leaders(cluster, "stock") == [1] * 4 + [2] * 4 + [3] * 4
    assert leaders(cluster, "order_line") == [1] * 4 + [2] * 4 + [3] * 4
    assert any("SPLIT TABLE order_line BY (2, 0, 0, 0)" in s for s in cluster.statements)
    assert all(op["name"] == "transfer-leader" and "from_store_id" not in op for op in cluster.operators)


def test_orders_with_surrogate_key_are_not_split_by_warehouse():
    cluster = FakeCluster()
    run_layout(cluster, settings(placement="spread", placement_scope="all", orders_key="auto_random"))
    assert "orders" not in cluster.regions and "stock" in cluster.regions and "order_line" in cluster.regions


def test_slot_regions_are_split_per_slot_and_spread_across_tikv():
    cluster = FakeCluster()
    cfg = settings(placement="spread", warehouse_mode="single-warehouse", placement_slot_items=2, variant="p2", slots=3)
    run_layout(cluster, replace(cfg, order_warehouses_max=1), slots=3, hot=(7, 8, 9))
    assert "SPLIT TABLE stock_slot BY (1, 7, 0), (1, 7, 1), (1, 7, 2), (1, 8, 0), (1, 8, 1), (1, 8, 2)" \
        in " ".join(cluster.statements)
    assert leaders(cluster, "stock_slot") == [1, 1, 2, 3, 1, 2, 3]    # Region đầu + mỗi slot s về TiKV s mod 3


def test_layout_fails_loudly_when_pd_does_not_move_the_leader_or_regions_differ():  # noqa: C901
    stuck = FakeCluster()
    stuck.ignore_operators = True
    clock = iter(range(0, 1000, 2))
    pd = PD("http://pd", stuck.transport)
    with pytest.raises(RuntimeError, match="chưa về đúng TiKV"):
        placement.apply_layout(stuck, pd, settings(placement="spread"), [1], None, timeout=5, sleep=lambda s: None,
                               clock=lambda: next(clock))
    assert stuck.paused and stuck.paused[placement.SCHEDULERS[0]] == 0      # lỗi thì bộ lập lịch được trả lại
    merged = FakeCluster()
    original = merged.query

    def drop_boundary(statement, values=()):
        rows = original(statement, values)
        if statement.startswith("SHOW"):
            rows = [row for row in rows if row["START_KEY"] != encode((5, 0))]   # PD đã gộp Region lại
        return rows

    merged.query = drop_boundary
    with pytest.raises(RuntimeError, match="thiếu ranh giới"):
        run_layout(merged, settings(placement="spread"))
    wrong = FakeCluster(stores=(1, 2))
    with pytest.raises(RuntimeError, match="kỳ vọng 3"):
        import os
        os.environ["FLASHSALE_TIKV_COUNT"] = "3"
        try:
            run_layout(wrong, settings(placement="spread"))
        finally:
            del os.environ["FLASHSALE_TIKV_COUNT"]


def test_transient_pd_errors_are_retried_until_the_leader_moves():
    cluster = FakeCluster()
    failures = {"left": 3}
    original = cluster.transport

    def flaky(method, path, body):
        if path == "/operators" and failures["left"] > 0:
            failures["left"] -= 1
            raise placement.PDError("PD POST /operators -> HTTP 500: region has an operator")
        return original(method, path, body)

    pd = PD("http://pd", flaky)
    placement.apply_layout(cluster, pd, settings(placement="spread"), [1], None, timeout=60, sleep=lambda s: None)
    assert leaders(cluster, "stock") == [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3] and failures["left"] == 0


def test_persistent_pd_error_is_reported_with_pd_message():
    cluster = FakeCluster()
    original = cluster.transport

    def broken(method, path, body):
        if path == "/operators":
            raise placement.PDError("PD POST /operators -> HTTP 500: no operator step is built")
        return original(method, path, body)

    clock = iter(range(0, 1000, 2))
    with pytest.raises(RuntimeError, match="no operator step is built"):
        placement.apply_layout(cluster, PD("http://pd", broken), settings(placement="spread"), [1], None, timeout=5,
                               sleep=lambda s: None, clock=lambda: next(clock))


def test_unfreeze_restores_the_previous_scheduling_limits():
    cluster = FakeCluster()
    pd = PD("http://pd", cluster.transport)
    before = placement.freeze_scheduling(pd)
    assert before["leader-schedule-limit"] == 4 and cluster.schedule["leader-schedule-limit"] == 0
    placement.unfreeze_scheduling(pd, before)
    assert cluster.schedule["leader-schedule-limit"] == 4 and cluster.paused["balance-leader-scheduler"] == 0


def test_speedup_pairs_matching_groups_and_ignores_invalid_or_unpaired():
    from flashsale.benchmark.report import GROUP_KEYS, speedups

    def row(tikv, tps, valid=1, **kw):
        base = dict.fromkeys(GROUP_KEYS, None)
        base.update(engine="tidb", profile="scaling", concurrency=64, theta=0.9, tikv_count=tikv, run_note=f"n{tikv}",
                    runs=3, valid=valid, tps_median=tps, p99_median_ms=10.0 * tikv)
        base.update(kw)
        return base

    summary = [row(1, 400), row(3, 480), row(1, 900, theta=0), row(3, 2400, theta=0), row(1, 50, theta=0.5),
               row(3, 99, valid=0, theta=0.5), row(3, 7, theta=0.7)]
    result = speedups(summary)
    assert [(r["theta"], round(r["speedup"], 2)) for r in result] == [(0, 2.67), (0.9, 1.2)]
    assert result[1]["tps_1"] == 400 and result[1]["p99_3"] == 30.0


def test_mysql_vertical_speedup_pairs_8_and_12_vcpus():
    from flashsale.benchmark.report import GROUP_KEYS, speedups

    def row(vcpus, tps):
        base = dict.fromkeys(GROUP_KEYS, None)
        base.update(engine="mysql", profile="scaling", concurrency=64, theta=0.9, vcpus=vcpus, tikv_count=None,
                    run_note=f"mysql-{vcpus}", runs=3, valid=3, tps_median=tps, p99_median_ms=5.0)
        return base

    result = speedups([row(8.0, 500), row(12.0, 600)])
    assert len(result) == 1 and round(result[0]["speedup"], 2) == 1.2
    result = speedups([row(24.0, 900), row(20.0, 600)])   # cỡ 20 và 24 vCPU (TiDB server lớn)
    assert len(result) == 1 and result[0]["tps_1"] == 600 and result[0]["tps_3"] == 900


def test_layout_evidence_records_load_base_split_config():
    cluster = FakeCluster()
    evidence = run_layout(cluster, settings(placement="spread"))
    assert evidence["load_base_split"] == [("tikv1", "split.qps-threshold", "3000")]
