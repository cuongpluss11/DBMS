from collections.abc import Iterator
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import logging
import random

from flashsale.adapters.base import Adapter, Row
from flashsale.config import Dataset
from .schema import TABLES

INITIAL_DATE = datetime(2020, 1, 1)
WAREHOUSE_YTD = 30_000_000
DISTRICT_YTD = 3_000_000
CUSTOMER_INITIAL = {"c_balance": -1000, "c_ytd_payment": 1000, "c_payment_cnt": 1}
STOCK_INITIAL = {"s_ytd": 0, "s_order_cnt": 0, "s_remote_cnt": 0}
SYLLABLES = ("BAR", "OUGHT", "ABLE", "PRI", "PRES", "ESE", "ANTI", "CALLY", "ATION", "EING")
LOADER_VERSION = 1
RESET_CHUNK = 10_000


def fingerprint(dataset: Dataset, seed: int, idempotency: bool = True, orders_key: str = "composite") -> str:
    # Lược đồ khác nhau (có/không UNIQUE request_id, khóa chính orders) thì dataset không dùng chung được.
    parts = ([LOADER_VERSION, asdict(dataset), seed] + ([] if idempotency else ["idempotency_off"])
             + ([] if orders_key == "composite" else [f"orders_key:{orders_key}"]))
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def text(rng: random.Random, minimum: int, maximum: int) -> str:
    return "".join(rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                               k=rng.randint(minimum, maximum)))


def address(rng: random.Random, prefix: str) -> Row:
    fields = {f"{prefix}_{key}": text(rng, 10, 20) for key in ("street_1", "street_2", "city")}
    fields[f"{prefix}_state"] = text(rng, 2, 2)
    fields[f"{prefix}_zip"] = f"{rng.randrange(10000):04}11111"
    return fields


def original(rng: random.Random, ids: set[int], row_id: int) -> str:
    value = text(rng, 26, 50)
    if row_id not in ids:
        return value
    start = rng.randrange(len(value) - 7)
    return value[:start] + "ORIGINAL" + value[start + 8:]


def rows_for(table: str, cfg: Dataset, seed: int) -> Iterator[Row]:
    rng = random.Random(f"{seed}:{table}")
    warehouses = range(1, cfg.warehouses + 1)
    items = range(1, cfg.items + 1)
    districts = range(1, cfg.districts + 1)
    customers = range(1, cfg.customers + 1)
    if table == "warehouse":
        for w in warehouses:
            yield dict(w_id=w, w_name=text(rng, 6, 10), w_tax=rng.randrange(2001),
                       w_ytd=WAREHOUSE_YTD, **address(rng, "w"))
        return
    if table == "item":
        marked = set(rng.sample(items, len(items) // 10))
        for i in items:
            yield dict(i_id=i, i_im_id=rng.randint(1, 10000), i_name=text(rng, 14, 24),
                       i_price=rng.randint(100, 10000), i_data=original(rng, marked, i))
        return
    for w in warehouses:
        if table == "stock":
            marked = set(rng.sample(items, len(items) // 10))
            for i in items:
                info = {f"s_dist_{d:02d}": text(rng, 24, 24) for d in range(1, 11)}
                yield dict(s_w_id=w, s_i_id=i, s_quantity=cfg.inventory,
                           s_data=original(rng, marked, i), **STOCK_INITIAL, **info)
            continue
        for d in districts:
            if table == "district":
                yield dict(d_w_id=w, d_id=d, d_name=text(rng, 6, 10), d_tax=rng.randrange(2001),
                           d_ytd=DISTRICT_YTD, d_next_o_id=cfg.initial_orders + 1, **address(rng, "d"))
            elif table == "customer":
                bad_credit = set(rng.sample(customers, len(customers) // 10))
                for c in customers:
                    number = c - 1 if c <= 1000 else rng.randrange(1000)
                    last = "".join(SYLLABLES[int(digit)] for digit in f"{number:03}")
                    yield dict(c_w_id=w, c_d_id=d, c_id=c, c_first=text(rng, 8, 16), c_middle="OE",
                               c_last=last, c_phone=f"{rng.randrange(10**16):016}", c_since=INITIAL_DATE,
                               c_credit="BC" if c in bad_credit else "GC", c_credit_lim=5_000_000,
                               c_discount=rng.randrange(5001), c_delivery_cnt=0, c_data=text(rng, 300, 500),
                               **address(rng, "c"), **CUSTOMER_INITIAL)
            elif table == "history":
                for c in customers:
                    yield dict(h_c_w_id=w, h_c_d_id=d, h_c_id=c, h_w_id=w, h_d_id=d,
                               h_date=INITIAL_DATE, h_amount=1000, h_data=text(rng, 12, 24))
            else:
                yield from initial_orders(table, cfg, seed, w, d)


def initial_orders(table: str, cfg: Dataset, seed: int, w: int, d: int) -> Iterator[Row]:
    rng = random.Random(f"{seed}:orders:{w}:{d}")
    customers = rng.sample(range(1, cfg.customers + 1), cfg.initial_orders)
    delivered = cfg.initial_orders * 7 // 10
    for o, c in enumerate(customers, 1):
        count = rng.randint(5, 15)
        carrier = rng.randint(1, 10) if o <= delivered else None
        if table == "orders":
            yield dict(o_w_id=w, o_d_id=d, o_id=o, o_c_id=c, o_entry_d=INITIAL_DATE,
                       o_carrier_id=carrier, o_ol_cnt=count, o_all_local=1)
        elif table == "new_order" and carrier is None:
            yield dict(no_w_id=w, no_d_id=d, no_o_id=o)
        elif table == "order_line":
            line_rng = random.Random(f"{seed}:lines:{w}:{d}:{o}")
            for number in range(1, count + 1):
                yield dict(ol_w_id=w, ol_d_id=d, ol_o_id=o, ol_number=number,
                           ol_i_id=line_rng.randint(1, cfg.items), ol_supply_w_id=w,
                           ol_delivery_d=INITIAL_DATE if carrier else None, ol_quantity=5,
                           ol_amount=0 if carrier else line_rng.randint(1, 999999),
                           ol_dist_info=text(line_rng, 24, 24))


def load(db: Adapter, cfg: Dataset, seed: int, batch_size: int = 1000) -> dict[str, int]:
    districts = cfg.warehouses * cfg.districts
    expected = dict(warehouse=cfg.warehouses, item=cfg.items, district=districts,
                    stock=cfg.warehouses * cfg.items, customer=districts * cfg.customers,
                    history=districts * cfg.customers, orders=districts * cfg.initial_orders,
                    new_order=districts * (cfg.initial_orders - cfg.initial_orders * 7 // 10))
    counts = {}
    for table in TABLES:
        batch = []
        generated = 0
        for row in rows_for(table, cfg, seed):
            batch.append(row)
            generated += 1
            if len(batch) == batch_size:
                db.insert_many(table, batch)
                batch.clear()
        if batch:
            db.insert_many(table, batch)
        counts[table] = db.count(table)
        if counts[table] != generated or counts[table] != expected.get(table, generated):
            raise RuntimeError(f"Sai số dòng {table}: đã sinh {generated}, DB có {counts[table]}")
        logging.info("Đã nạp %s rows=%d", table, counts[table])
    return counts


def reset(db: Adapter, cfg: Dataset) -> None:
    db.drop_slots()  # bảng phụ của P2; dòng stock đã chuyển tồn sang slot được khôi phục ngay bên dưới
    for table in ("order_line", "new_order", "orders"):
        db.delete_tagged(table, "run_id")
    db.delete_tagged("history", "request_id")
    for warehouse in range(1, cfg.warehouses + 1):
        # Chia lô để không vượt giới hạn kích thước giao dịch (TiDB) khi nhiều dòng đã bị đổi.
        for first in range(1, cfg.items + 1, RESET_CHUNK):
            db.change("stock", {"s_w_id": warehouse},
                      set_values={"s_quantity": cfg.inventory, **STOCK_INITIAL}, changed_only=True,
                      between={"s_i_id": (first, min(first + RESET_CHUNK - 1, cfg.items))})
        db.change("customer", {"c_w_id": warehouse}, set_values=CUSTOMER_INITIAL, changed_only=True)
    db.change("district", {}, set_values={"d_next_o_id": cfg.initial_orders + 1, "d_ytd": DISTRICT_YTD},
              changed_only=True)
    db.change("warehouse", {}, set_values={"w_ytd": WAREHOUSE_YTD}, changed_only=True)


def slot_quantities(inventory: int, slots: int) -> list[int]:
    """Chia S0 thành `slots` phần nguyên, phần dư dồn vào các slot đầu; tổng luôn bằng S0."""
    base, extra = divmod(inventory, slots)
    return [base + (1 if slot < extra else 0) for slot in range(slots)]


def prepare_slots(db: Adapter, cfg: Dataset, hot_items: list[int], slots: int, batch_size: int = 1000) -> dict:
    """P2: với mỗi kho và mỗi món nóng, chuyển toàn bộ tồn của dòng stock sang `slots` dòng con (stock.s_quantity
    về 0). Tổng tồn (stock + slot) vẫn bằng S0 nên luật 2 tính trên tổng. Chạy trước warmup, ngoài thời gian đo."""
    db.create_slots()
    parts = slot_quantities(cfg.inventory, slots)
    rows = 0
    for warehouse in range(1, cfg.warehouses + 1):
        batch = []
        for item in hot_items:
            for slot, quantity in enumerate(parts):
                batch.append(dict(ss_w_id=warehouse, ss_i_id=item, ss_slot=slot, ss_quantity=quantity,
                                  ss_ytd=0, ss_order_cnt=0))
            db.change("stock", {"s_w_id": warehouse, "s_i_id": item}, set_values={"s_quantity": 0})
            if len(batch) >= batch_size:
                db.insert_many("stock_slot", batch)
                rows += len(batch)
                batch = []
        if batch:
            db.insert_many("stock_slot", batch)
            rows += len(batch)
    expected = cfg.warehouses * len(hot_items) * slots
    if rows != expected or db.count("stock_slot") != expected:
        raise RuntimeError(f"Sai số dòng stock_slot: kỳ vọng {expected}, đã chèn {rows}, DB có {db.count('stock_slot')}")
    return {"slot_rows": rows, "hot_items": len(hot_items), "slots": slots}
