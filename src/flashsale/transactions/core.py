from dataclasses import dataclass, field
from datetime import datetime, timezone
import random

from flashsale.adapters.base import Adapter, DBError, Row
from flashsale.workload.generator import Request

# ol_dist_info của P0/P1/P2 là hằng: không đọc dòng stock chỉ để lấy chuỗi đệm (đọc thêm sẽ giữ khóa lâu hơn
# trên dòng nóng). Khác loader TPC-C chuẩn và khác `legacy`; ghi trong docs/assumptions.md.
DIST_FILLER = "FLASHSALE-NO-DIST-INFO"


@dataclass
class TxnContext:
    """Trạng thái của MỘT worker cho các biến thể mục 2.2 (mỗi worker có adapter riêng nên không chia sẻ)."""
    variant: str = "legacy"
    slots: int = 1
    hot_items: frozenset[int] = frozenset()
    order_id_batch: int = 0
    rng: random.Random = field(default_factory=random.Random)
    blocks: dict[tuple[int, int], list[int]] = field(default_factory=dict)
    slot_attempts: int = 0
    slot_items: int = 0
    lock_order: bool = False
    nowait: bool = False
    design_b: bool = False
    stored_procedure: bool = False

    @property
    def is_2_1(self) -> bool:
        return (self.variant == "legacy" and self.order_id_batch == 0 and not self.lock_order
                and not self.nowait and not self.design_b and not self.stored_procedure)


def lookup(db: Adapter, req: Request) -> Row | None:
    table = "orders" if req.kind == "new_order" else "history"
    return db.one(table, {"request_id": req.request_id})


def required(row: Row | None) -> Row:
    if row is None:
        raise DBError("application_error")
    return row


def execute(db: Adapter, req: Request, ctx: TxnContext | None = None) -> None:
    if ctx is not None and ctx.design_b and req.kind == "new_order":
        # Thiết kế (b): KHÔNG có giao dịch nhiều tài liệu (xem new_order_b).
        if not (req.idempotent and lookup(db, req) is not None):
            new_order_b(db, req)
        return
    if ctx is not None and ctx.stored_procedure and req.kind == "new_order":
        # T4 (MySQL): cả giao dịch là một CALL; thủ tục tự BEGIN/COMMIT nên không dùng db.atomic().
        if not (req.idempotent and lookup(db, req) is not None):
            items = sorted(req.items) if ctx.lock_order else req.items
            db.call_new_order(req.warehouse, req.district, req.customer, req.request_id, req.run_id, list(items),
                              datetime.now(timezone.utc).replace(tzinfo=None))
        return
    if ctx is not None and ctx.order_id_batch > 0 and req.kind == "new_order":
        # Xin lô mã đơn TRƯỚC khi mở giao dịch của đơn (giao dịch riêng, commit ngay): BEGIN lồng trong một
        # giao dịch đang mở sẽ chốt giao dịch đó.
        ensure_order_ids(db, ctx, req.warehouse, req.district)
    with db.atomic():
        if req.idempotent and lookup(db, req) is not None:
            return
        if req.kind == "new_order":
            if ctx is None or ctx.is_2_1:
                new_order(db, req)
            else:
                new_order(db, req, ctx)
        else:
            payment(db, req)


def ensure_order_ids(db: Adapter, ctx: TxnContext, w: int, d: int) -> None:
    block = ctx.blocks.get((w, d))
    if block is not None and block[0] < block[1]:
        return
    key = {"d_w_id": w, "d_id": d}
    with db.atomic():
        first = required(db.one("district", key, lock=True))["d_next_o_id"]
        db.change("district", key, increment={"d_next_o_id": ctx.order_id_batch})
    # Chỉ ghi nhận lô sau khi commit thành công; lỗi thì ném DBError ra cho vòng retry của runner.
    ctx.blocks[(w, d)] = [first, first + ctx.order_id_batch]


def take_order_id(db: Adapter, req: Request, ctx: TxnContext | None) -> int:
    if ctx is not None and ctx.order_id_batch > 0:
        block = ctx.blocks[(req.warehouse, req.district)]
        order_id = block[0]
        # Mã đã lấy không trả lại nếu giao dịch bị hủy: chấp nhận khoảng trống mã, không bao giờ trùng mã.
        block[0] += 1
        return order_id
    key = {"d_w_id": req.warehouse, "d_id": req.district}
    order_id = required(db.one("district", key, lock=True))["d_next_o_id"]
    db.change("district", key, increment={"d_next_o_id": 1})
    return order_id


def take_stock(db: Adapter, req: Request, ctx: TxnContext, item: int, quantity: int,
               warehouse: int | None = None) -> None:
    """Trừ kho theo variant; hết hàng thì ném DBError('out_of_stock') để cả giao dịch rollback."""
    w = req.warehouse if warehouse is None else warehouse
    key = {"s_w_id": w, "s_i_id": item}
    stats = {"s_ytd": quantity, "s_order_cnt": 1}
    if ctx.variant == "p0":
        # Đọc rồi ghi: giá trị tuyệt đối tính ở ứng dụng, không khóa lúc đọc, nên hai giao dịch đồng thời
        # có thể ghi đè nhau (mất cập nhật) trên hệ không phát hiện được xung đột.
        current = required(db.one("stock", key))["s_quantity"]
        if current < quantity:
            raise DBError("out_of_stock")
        db.change("stock", key, set_values={"s_quantity": current - quantity}, increment=stats)
    elif ctx.variant == "p1" or item not in ctx.hot_items:
        if db.change("stock", key, increment={"s_quantity": -quantity, **stats},
                     at_least={"s_quantity": quantity}) != 1:
            raise DBError("out_of_stock")
    else:
        # P2, món nóng: chọn ngẫu nhiên một slot; slot không đủ thì thử lần lượt các slot còn lại.
        first = ctx.rng.randrange(ctx.slots)
        ctx.slot_items += 1  # đếm mọi lần trừ món nóng (kể cả thất bại hết hàng) làm mẫu số của số lần thử
        for step in range(ctx.slots):
            ctx.slot_attempts += 1
            slot = {"ss_w_id": w, "ss_i_id": item, "ss_slot": (first + step) % ctx.slots}
            if db.change("stock_slot", slot, increment={"ss_quantity": -quantity, "ss_ytd": quantity,
                                                        "ss_order_cnt": 1},
                         at_least={"ss_quantity": quantity}) == 1:
                return
        raise DBError("out_of_stock")


def new_order(db: Adapter, req: Request, ctx: TxnContext | None = None) -> None:
    w, d = req.warehouse, req.district
    legacy = ctx is None or ctx.variant == "legacy"
    order_id = take_order_id(db, req, ctx)
    lines = []
    # Kho cung cấp từng món (đơn nhiều kho, mục 2.3 nhóm E); không có `supply` thì mọi món lấy từ kho nhà.
    entries = [(item, quantity, req.supply[i] if req.supply else w) for i, (item, quantity) in enumerate(req.items)]
    # T4: khóa các món theo (kho, i_id) tăng dần để hai đơn không giữ khóa theo thứ tự ngược nhau (deadlock).
    if ctx is not None and ctx.lock_order:
        entries.sort(key=lambda entry: (entry[2], entry[0]))
    all_local = int(all(entry[2] == w for entry in entries))
    for line_number, (item, quantity, sw) in enumerate(entries, 1):
        if legacy:
            key = {"s_w_id": sw, "s_i_id": item}
            stock = required(db.one("stock", key, lock=True, **({"nowait": True} if ctx and ctx.nowait else {})))
            if stock["s_quantity"] < quantity:
                raise DBError("out_of_stock")
            price = required(db.one("item", {"i_id": item}))["i_price"]
            db.change("stock", key, increment={"s_quantity": -quantity,
                                               "s_ytd": quantity, "s_order_cnt": 1})
            dist_info = stock[f"s_dist_{d:02d}"]
        else:
            take_stock(db, req, ctx, item, quantity, sw)
            price = required(db.one("item", {"i_id": item}))["i_price"]
            dist_info = DIST_FILLER
        lines.append(dict(ol_w_id=w, ol_d_id=d, ol_o_id=order_id, ol_number=line_number,
                          ol_i_id=item, ol_supply_w_id=sw, ol_quantity=quantity, ol_delivery_d=None,
                          ol_amount=quantity * price, ol_dist_info=dist_info,
                          run_id=req.run_id))
    db.insert("orders", dict(o_w_id=w, o_d_id=d, o_id=order_id, o_c_id=req.customer,
                            o_entry_d=datetime.now(timezone.utc).replace(tzinfo=None),
                            o_carrier_id=None, o_ol_cnt=len(lines), o_all_local=all_local,
                            request_id=req.request_id, run_id=req.run_id))
    db.insert("new_order", dict(no_w_id=w, no_d_id=d, no_o_id=order_id, run_id=req.run_id))
    db.insert_many("order_line", lines)


def new_order_b(db: Adapter, req: Request) -> None:
    """MongoDB thiết kế (b), đề mục 2.1/2.2: đơn nhúng order_lines trong một tài liệu orders; mỗi món trừ kho bằng một
    updateOne có điều kiện (nguyên tử trên MỘT tài liệu stock); hoàn lại các món đã trừ nếu gặp món hết hàng hoặc
    không ghi được đơn. Mã đơn lấy bằng findOneAndUpdate $inc. Điểm cam kết là việc ghi tài liệu orders (khóa UNIQUE
    request_id). Giới hạn đã biết của (b): nếu tiến trình chết giữa lúc trừ kho và lúc ghi đơn (hoặc kết quả ghi đơn
    không xác định và không đọc lại được), kho bị trừ mà không có đơn; validator luật 2 sẽ báo lệch."""
    try:
        _new_order_b(db, req)
    except DBError:
        raise
    except Exception as exc:
        converted = db.as_db_error(exc)
        if converted is exc:
            raise
        raise converted from exc


def _new_order_b(db: Adapter, req: Request) -> None:
    w, d = req.warehouse, req.district
    order_id = db.take_counter("district", {"d_w_id": w, "d_id": d}, "d_next_o_id", 1)
    deducted: list[tuple[int, int]] = []
    keep_stock = False
    try:
        lines = []
        for line_number, (item, quantity) in enumerate(req.items, 1):
            if db.change("stock", {"s_w_id": w, "s_i_id": item},
                         increment={"s_quantity": -quantity, "s_ytd": quantity, "s_order_cnt": 1},
                         at_least={"s_quantity": quantity}) != 1:
                raise DBError("out_of_stock")
            deducted.append((item, quantity))
            price = required(db.one("item", {"i_id": item}))["i_price"]
            lines.append(dict(ol_number=line_number, ol_i_id=item, ol_supply_w_id=w, ol_quantity=quantity,
                              ol_amount=quantity * price, ol_dist_info=DIST_FILLER))
        try:
            db.insert("orders", dict(o_w_id=w, o_d_id=d, o_id=order_id, o_c_id=req.customer,
                                    o_entry_d=datetime.now(timezone.utc).replace(tzinfo=None),
                                    o_carrier_id=None, o_ol_cnt=len(lines), o_all_local=1,
                                    request_id=req.request_id, run_id=req.run_id, order_lines=lines))
        except Exception as exc:
            if getattr(db.as_db_error(exc), "category", None) == "duplicate_key":
                raise  # chắc chắn không phải tài liệu của lần này: hoàn kho rồi để vòng retry đối chiếu
            try:
                present = lookup(db, req) is not None
            except Exception:
                keep_stock = True  # không xác định được: giữ nguyên, tránh hoàn kho cho một đơn có thể đã ghi
                raise
            if not present:
                raise
        keep_stock = True  # từ đây đơn đã cam kết: lỗi ở bước sau không được hoàn kho
        db.insert("new_order", dict(no_w_id=w, no_d_id=d, no_o_id=order_id, run_id=req.run_id))
    except BaseException:
        if not keep_stock:
            for item, quantity in reversed(deducted):
                for _ in range(3):  # hoàn kho tốt nhất có thể; thất bại hẳn thì luật 2 sẽ phát hiện
                    try:
                        db.change("stock", {"s_w_id": w, "s_i_id": item},
                                  increment={"s_quantity": quantity, "s_ytd": -quantity, "s_order_cnt": -1})
                        break
                    except Exception:
                        continue
        raise


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
