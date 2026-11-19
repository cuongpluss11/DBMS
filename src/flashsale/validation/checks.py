from collections import Counter
from collections.abc import Iterable

from flashsale.adapters.base import Adapter, Row
from flashsale.config import Dataset

ORDER_FIELDS = ("o_w_id", "o_d_id", "o_id", "o_ol_cnt", "request_id", "run_id")
LINE_FIELDS = ("ol_w_id", "ol_d_id", "ol_o_id", "ol_number", "ol_supply_w_id",
               "ol_i_id", "ol_quantity", "run_id")
STOCK_FIELDS = ("s_w_id", "s_i_id", "s_quantity")


def check(dataset: Dataset, run_id: str, expected_requests: Iterable[str],
          stock: Iterable[Row], orders: Iterable[Row], lines: Iterable[Row]) -> dict:
    failures: dict[str, list] = {"nonnegative": [], "reconciliation": [], "idempotency": []}
    accounting = failures["reconciliation"]
    identity = failures["idempotency"]
    expected = Counter(expected_requests)
    actual: Counter[str] = Counter()
    committed: dict[tuple[int, int, int], tuple[str, int]] = {}
    order_rows = 0
    for row in orders:
        order_rows += 1
        key = (row["o_w_id"], row["o_d_id"], row["o_id"])
        if key in committed:
            identity.append({"duplicate_order_key": key})
        committed[key] = (row.get("run_id"), row["o_ol_cnt"])
        request = row.get("request_id")
        if row.get("run_id") != run_id or not request or not request.startswith(run_id + "-"):
            identity.append({"unexpected_order": key, "request_id": request, "run_id": row.get("run_id")})
        if request:
            actual[request] += 1
    for request in sorted(expected.keys() | actual.keys()):
        if expected[request] != 1 or actual[request] != 1:
            identity.append({"request_id": request, "client_successes": expected[request],
                             "committed_orders": actual[request]})

    sold: Counter[tuple[int, int]] = Counter()
    line_numbers: dict[tuple[int, int, int], set[int]] = {}
    line_rows = 0
    for row in lines:
        line_rows += 1
        key = (row["ol_w_id"], row["ol_d_id"], row["ol_o_id"])
        parent = committed.get(key)
        if parent is None or parent[0] != row.get("run_id"):
            accounting.append({"orphan_order_line": key, "line_number": row["ol_number"]})
            continue
        numbers = line_numbers.setdefault(key, set())
        if row["ol_number"] in numbers or row["ol_quantity"] <= 0:
            accounting.append({"invalid_line": key, "line_number": row["ol_number"],
                               "quantity": row["ol_quantity"]})
        numbers.add(row["ol_number"])
        sold[row["ol_supply_w_id"], row["ol_i_id"]] += row["ol_quantity"]
    for key, (_, count) in committed.items():
        if not 1 <= count <= 5 or line_numbers.get(key) != set(range(1, count + 1)):
            accounting.append({"order_key": key, "expected_lines": count,
                               "line_numbers": sorted(line_numbers.get(key, ()))})

    present = bytearray(dataset.warehouses * dataset.items)
    for row in stock:
        w, i, quantity = (row[field] for field in STOCK_FIELDS)
        if quantity < 0:
            failures["nonnegative"].append({"warehouse": w, "item": i, "stock_final": quantity})
        if not 1 <= w <= dataset.warehouses or not 1 <= i <= dataset.items:
            accounting.append({"stock_key_outside_dataset": (w, i)})
            continue
        offset = (w - 1) * dataset.items + i - 1
        if present[offset]:
            accounting.append({"duplicate_stock_key": (w, i)})
            continue
        present[offset] = 1
        units = sold.pop((w, i), 0)
        delta = dataset.inventory - quantity - units
        if delta:
            accounting.append({"warehouse": w, "item": i, "stock_initial": dataset.inventory,
                               "stock_final": quantity, "sold": units, "delta": delta})
    for offset, found in enumerate(present):
        if not found:
            w, i = divmod(offset, dataset.items)
            accounting.append({"missing_stock_key": (w + 1, i + 1), "sold": sold.pop((w + 1, i + 1), 0)})
    for key, quantity in sold.items():
        accounting.append({"sold_without_stock_key": key, "sold": quantity})

    return {"status": "INVALID" if any(failures.values()) else "VALID",
            "rules": {rule: not errors for rule, errors in failures.items()},
            "errors": failures, "committed_orders": sum(actual.values()),
            "tagged_rows": {"orders": order_rows, "order_line": line_rows}}


def validate(db: Adapter, dataset: Dataset, run_id: str, expected_requests: Iterable[str],
             baseline_counts: dict[str, int] | None = None) -> dict:
    report = check(dataset, run_id, expected_requests, db.rows("stock", STOCK_FIELDS),
                   db.rows("orders", ORDER_FIELDS, tagged=True), db.rows("order_line", LINE_FIELDS, tagged=True))
    if baseline_counts is not None:
        for table, rule in (("orders", "idempotency"), ("order_line", "reconciliation"),
                            ("new_order", "idempotency")):
            tagged = report["tagged_rows"].get(table, report["tagged_rows"]["orders"])
            expected = baseline_counts[table] + tagged
            actual = db.count(table)
            if actual != expected:
                report["errors"][rule].append({"table": table, "expected_rows": expected, "actual_rows": actual})
                report["rules"][rule] = False
                report["status"] = "INVALID"
    cross_check = getattr(db, "doc_reconciliation", None)
    if cross_check is not None:
        violations = cross_check(dataset.inventory, dataset.initial_orders)
        report["doc_check"] = {"violations": len(violations), "sample": violations[:5]}
        if violations:
            report["errors"]["reconciliation"].append({"doc_sql_check": violations[:5]})
            report["rules"]["reconciliation"] = False
            report["status"] = "INVALID"
    return report
