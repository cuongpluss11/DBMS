from datetime import datetime, timezone

from flashsale.adapters.base import Adapter, DBError, Row
from flashsale.workload.generator import Request


def lookup(db: Adapter, req: Request) -> Row | None:
    table = "orders" if req.kind == "new_order" else "history"
    return db.one(table, {"request_id": req.request_id})


def required(row: Row | None) -> Row:
    if row is None:
        raise DBError("application_error")
    return row


def execute(db: Adapter, req: Request) -> None:
    with db.atomic():
        if req.idempotent and lookup(db, req) is not None:
            return
        if req.kind == "new_order":
            new_order(db, req)
        else:
            payment(db, req)


def new_order(db: Adapter, req: Request) -> None:
    w, d = req.warehouse, req.district
    district_key = {"d_w_id": w, "d_id": d}
    district = required(db.one("district", district_key, lock=True))
    order_id = district["d_next_o_id"]
    db.change("district", district_key, increment={"d_next_o_id": 1})
    lines = []
    for line_number, (item, quantity) in enumerate(req.items, 1):
        key = {"s_w_id": w, "s_i_id": item}
        stock = required(db.one("stock", key, lock=True))
        if stock["s_quantity"] < quantity:
            raise DBError("out_of_stock")
        price = required(db.one("item", {"i_id": item}))["i_price"]
        db.change("stock", key, increment={"s_quantity": -quantity,
                                           "s_ytd": quantity, "s_order_cnt": 1})
        lines.append(dict(ol_w_id=w, ol_d_id=d, ol_o_id=order_id, ol_number=line_number,
                          ol_i_id=item, ol_supply_w_id=w, ol_quantity=quantity, ol_delivery_d=None,
                          ol_amount=quantity * price, ol_dist_info=stock[f"s_dist_{d:02d}"],
                          run_id=req.run_id))
    db.insert("orders", dict(o_w_id=w, o_d_id=d, o_id=order_id, o_c_id=req.customer,
                            o_entry_d=datetime.now(timezone.utc).replace(tzinfo=None),
                            o_carrier_id=None, o_ol_cnt=len(lines), o_all_local=1,
                            request_id=req.request_id, run_id=req.run_id))
    db.insert("new_order", dict(no_w_id=w, no_d_id=d, no_o_id=order_id, run_id=req.run_id))
    db.insert_many("order_line", lines)


def payment(db: Adapter, req: Request) -> None:
    w, d, amount = req.warehouse, req.district, req.amount
    if req.payment_ytd:
        db.change("warehouse", {"w_id": w}, increment={"w_ytd": amount})
        db.change("district", {"d_w_id": w, "d_id": d}, increment={"d_ytd": amount})
    changed = db.change("customer", {"c_w_id": w, "c_d_id": d, "c_id": req.customer},
                        increment={"c_balance": -amount, "c_ytd_payment": amount, "c_payment_cnt": 1})
    if changed != 1:
        raise DBError("application_error")
    db.insert("history", dict(h_c_w_id=w, h_c_d_id=d, h_c_id=req.customer, h_w_id=w, h_d_id=d,
                             h_date=datetime.now(timezone.utc).replace(tzinfo=None),
                             h_amount=amount, h_data="FLASHSALE", request_id=req.request_id))
