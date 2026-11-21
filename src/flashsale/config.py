from dataclasses import dataclass
from pathlib import Path
import tomllib


VARIANTS = ("legacy", "p0", "p1", "p2", "p3")


def uses_slots(variant: str) -> bool:
    """P2 và P3 chia tồn kho thành slot (P3 = P2 + điều tiết thích ứng)."""
    return variant in ("p2", "p3")


@dataclass(frozen=True)
class Dataset:
    warehouses: int
    districts: int
    items: int
    customers: int
    initial_orders: int
    inventory: int

    def __post_init__(self) -> None:
        if min(self.warehouses, self.districts, self.items, self.customers,
               self.initial_orders, self.inventory) < 1:
            raise ValueError("Kích thước dataset và tồn đầu phải dương")
        if self.districts > 10 or self.initial_orders > self.customers:
            raise ValueError("Tối đa 10 district và không vượt số customer khi nạp đơn")


@dataclass(frozen=True)
class Settings:
    label: str
    seed: int
    workers_per_process: int
    concurrency: int
    warehouse_mode: str
    theta: float
    hot_item: bool
    warmup_seconds: float
    measurement_seconds: float
    repetitions: int
    payment_ytd: bool
    jitter: bool
    dataset: Dataset
    # Mặc định giữ UNIQUE request_id + kiểm idempotency. Chỉ profile `idempotency_off`
    # (lượt phụ theo mục 2.1 của đề) mới tắt.
    idempotency: bool = True
    client_timeout_seconds: float = 15.0
    # Mục 2.2. `legacy` = cách trừ kho của 2.1 (khóa dòng bằng FOR UPDATE rồi ghi), giữ nguyên để số 2.1 không đổi.
    # p0 = đọc rồi ghi; p1 = cập nhật có điều kiện; p2 = p1 trên `slots` dòng con cho `hot_items` món đầu bảng hạng.
    variant: str = "legacy"
    slots: int = 1
    hot_items: int = 100
    # 0 = mỗi đơn tăng d_next_o_id (như 2.1); B > 0 = mỗi worker xin một lô B mã đơn cho mỗi (kho, quận).
    order_id_batch: int = 0
    # Tải vòng mở (T3): arrival_rate > 0 là số yêu cầu đến mỗi giây (tổng), vào hàng đợi hữu hạn `queue_size` mỗi
    # process; 0 = vòng kín như 2.1. P3: ngưỡng điều tiết (các thông số khởi đầu, chỉnh khi chạy thử).
    arrival_rate: float = 0.0
    queue_size: int = 64
    p99_limit_ms: float = 500.0
    abort_limit_pct: float = 10.0
    limit_min: int = 1
    # Mục 2.2, nhóm T4 (đòn bẩy riêng từng hệ; mặc định tắt = hành vi trước đó).
    # lock_order: khóa/cập nhật các món của một đơn theo i_id tăng dần (MySQL, TiDB: tránh deadlock).
    # nowait: SELECT ... FOR UPDATE NOWAIT trên dòng stock rồi thử lại (chỉ MySQL/TiDB, chỉ variant legacy).
    # txn_mode: chế độ giao dịch của TiDB (default | optimistic | pessimistic).
    lock_order: bool = False
    nowait: bool = False
    txn_mode: str = "default"
    # Thiết kế MongoDB (đề mục 2.1): "a" = 9 collection + giao dịch nhiều tài liệu; "b" = nhúng order_line vào orders,
    # trừ kho bằng một lệnh updateOne có điều kiện mỗi món, hoàn lại khi lỗi, KHÔNG có giao dịch nhiều tài liệu.
    mongo_design: str = "a"
    # T4 (MySQL): toàn bộ giao dịch đặt hàng trong MỘT stored procedure (một lần gọi qua mạng, khóa không bị giữ
    # trong lúc chờ ứng dụng). Cùng logic khóa-rồi-ghi của `legacy`, nên chỉ dùng với variant legacy.
    stored_procedure: bool = False
    # Mục 2.3 (chỉ TiDB). Đơn nhiều kho (nhóm E, như TPC-C): mỗi đơn chạm [min, max] kho; nếu warehouse_groups > 0
    # thì kho khác chỉ chọn trong cùng nhóm với kho nhà (W chia đều thành `warehouse_groups` nhóm liên tiếp).
    order_warehouses_min: int = 1
    order_warehouses_max: int = 1
    warehouse_groups: int = 0
    # Nhóm D: khóa chính của orders (composite = TPC-C; autoinc/auto_random = cột o_seq, UNIQUE phụ giữ khóa TPC-C).
    orders_key: str = "composite"
    # Đặt Region/leader: none (PD tự quyết) | spread (leader các kho rải đều các TiKV) | group (cả nhóm kho cùng một
    # TiKV). Phạm vi: stock (cộng stock_slot của P2) hoặc all (thêm district, customer, orders, new_order, order_line).
    placement: str = "none"
    placement_scope: str = "stock"
    placement_slot_items: int = 5

    def __post_init__(self) -> None:
        if self.idempotency == (self.label == "idempotency_off"):
            raise ValueError("Chỉ profile có nhãn idempotency_off mới được đặt idempotency=false (và ngược lại)")
        if self.variant not in VARIANTS:
            raise ValueError(f"variant phải thuộc {VARIANTS}")
        if self.slots < 1 or self.hot_items < 1 or self.order_id_batch < 0:
            raise ValueError("slots và hot_items phải dương, order_id_batch không âm")
        if (self.arrival_rate < 0 or self.queue_size < 1 or self.p99_limit_ms <= 0
                or not 0 <= self.abort_limit_pct <= 100 or self.limit_min < 1):
            raise ValueError("Tham số tải vòng mở hoặc điều tiết không hợp lệ")
        if self.txn_mode not in ("default", "optimistic", "pessimistic"):
            raise ValueError("txn_mode phải là default, optimistic hoặc pessimistic")
        if not 1 <= self.order_warehouses_min <= self.order_warehouses_max <= 4:
            raise ValueError("Cần 1 <= order_warehouses_min <= order_warehouses_max <= 4")
        if self.order_warehouses_max > 1 and (self.hot_item or self.stored_procedure or self.mongo_design != "a"
                                              or self.warehouse_mode != "uniform"):
            raise ValueError("Đơn nhiều kho cần kho nhà chọn đều (uniform), không hot_item, stored procedure hay (b)")
        if self.warehouse_groups < 0 or self.placement_slot_items < 1:
            raise ValueError("warehouse_groups không âm, placement_slot_items dương")
        if self.orders_key not in ("composite", "autoinc", "auto_random"):
            raise ValueError("orders_key phải là composite, autoinc hoặc auto_random")
        if self.placement not in ("none", "spread", "group") or self.placement_scope not in ("stock", "all"):
            raise ValueError("placement hoặc placement_scope không hợp lệ")
        if self.placement == "group" and self.warehouse_groups < 1:
            raise ValueError("placement group cần warehouse_groups >= 1")
        if self.mongo_design not in ("a", "b"):
            raise ValueError("mongo_design phải là a hoặc b")
        if self.mongo_design == "b" and self.variant != "p1":
            raise ValueError("Thiết kế (b) là P1 từng món không giao dịch: dùng variant p1")
        if self.stored_procedure and (self.variant != "legacy" or self.nowait or self.mongo_design != "a"
                                      or self.order_id_batch):
            raise ValueError("stored_procedure chỉ dùng với variant legacy, không kèm nowait, thiết kế (b) hay lô mã đơn")
        if self.nowait and self.variant != "legacy":
            raise ValueError("nowait chỉ có nghĩa với variant legacy (P1 là một lệnh cập nhật, không có đọc khóa)")
        if self.client_timeout_seconds <= 0:
            raise ValueError("client_timeout_seconds phải dương")
        if self.warehouse_mode not in {"uniform", "single-warehouse"}:
            raise ValueError("warehouse_mode không hợp lệ")
        if self.theta not in (0, .3, .5, .7, .9):
            raise ValueError("theta không hợp lệ")
        if not 1 <= self.concurrency <= 256 or not 1 <= self.workers_per_process <= 32:
            raise ValueError("Cần 1–256 client, với 1–32 client mỗi process")
        if self.warmup_seconds < 0 or self.measurement_seconds <= 0 or self.repetitions < 1:
            raise ValueError("Thời lượng hoặc số lần lặp không hợp lệ")


def read_settings(path: Path) -> Settings:
    with path.open("rb") as stream:
        values = tomllib.load(stream)
    return Settings(dataset=Dataset(**values.pop("dataset")), **values)
