from dataclasses import dataclass
from pathlib import Path
import tomllib


VARIANTS = ("legacy", "p0", "p1", "p2")


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

    def __post_init__(self) -> None:
        if self.idempotency == (self.label == "idempotency_off"):
            raise ValueError("Chỉ profile có nhãn idempotency_off mới được đặt idempotency=false (và ngược lại)")
        if self.variant not in VARIANTS:
            raise ValueError(f"variant phải thuộc {VARIANTS}")
        if self.slots < 1 or self.hot_items < 1 or self.order_id_batch < 0:
            raise ValueError("slots và hot_items phải dương, order_id_batch không âm")
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
