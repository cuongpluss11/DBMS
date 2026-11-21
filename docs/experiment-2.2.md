# Thực nghiệm 2.2 (Flash-sale: tranh chấp khóa) — trạng thái mã nguồn P0–P2

Chưa có số đo nào của mục 2.2 trong repo. Tài liệu này mô tả phần đã có trong mã (P0, P1, P2, cấp mã đơn theo lô); P3, tải vòng mở và T4 chưa làm. Khác biệt với tài liệu ý tưởng: xem phần "mục 2.2" của `docs/assumptions.md`.

## Biến thể trừ kho

| `--variant` | Hành vi | Ghi chú |
| --- | --- | --- |
| `legacy` (mặc định) | `SELECT ... FOR UPDATE` rồi cộng delta (cách của 2.1) | Số 2.1 không đổi |
| `p0` | Đọc `s_quantity` không khóa, kiểm tra ở ứng dụng, ghi giá trị tuyệt đối | Đối chứng mất cập nhật; validator/đối soát bắt lệch luật 2 |
| `p1` | `UPDATE ... SET s_quantity = s_quantity - n WHERE ... AND s_quantity >= n`; số dòng ≠ 1 là hết hàng | Baseline an toàn |
| `p2` | P1 trên `--slots N` dòng con cho `--hot-items K` món hạng đầu; món còn lại dùng P1 | Bảng phụ `stock_slot`; chuẩn bị trước warmup |

`--order-id-batch B` (0 = như 2.1): mỗi worker xin lô B mã đơn cho mỗi (kho, quận) thay vì tăng `d_next_o_id` mỗi đơn. Độc lập với variant (T2 cần cả hai nhánh có/không).

## Lệnh

Profile `configs/hotspot.toml` (W=10, tồn 10^9, một kho, θ=0,9, 64 client; mặc định P1). Dataset nạp bằng `flashsale load` như 2.1; mọi variant dùng chung một dataset (slot được tạo và xóa trong mỗi lượt).

```powershell
flashsale run mysql --config configs/hotspot.toml --dataset <ten-dataset> --reset-between --variant p0 --theta 0.9 --concurrency 64
flashsale run mysql --config configs/hotspot.toml --dataset <ten-dataset> --reset-between --variant p2 --slots 9 --order-id-batch 50 --hot-item
```

Smoke nhỏ (cần DBMS đang chạy): `flashsale smoke mysql --start --variant p2 --slots 3 --hot-items 5` (profile `smoke.toml`, tồn 20, có hết hàng). Lượt kiểm luật có hết hàng thực: `--config configs/correctness.toml --variant p2 --slots 9`.

## Kết quả và trường mới

`result.json`/`INDEX.csv` có thêm `variant`, `slots`, `order_id_batch` (lượt 2.1 cũ đọc là `legacy`, không slot, lô 0); `SCHEMA_VERSION = 4`. `measurement.slot_attempts_per_item` = số lần thử slot trung bình mỗi món hàng trừ được qua slot (`null` nếu không phải p2). `variant_setup` trong `result.json` ghi số dòng slot và thời gian chuẩn bị. Báo cáo gộp (`flashsale report`) tách nhóm theo variant/slot/lô mã.

## Đã kiểm thử / chưa kiểm thử

- Đã chạy: unit test (adapter trong bộ nhớ): `tests/test_hotspot.py`, toàn bộ `pytest -m "not integration"` PASS (xem báo cáo phiên làm việc).
- **NOT TESTED:** mọi hành vi trên MySQL, MongoDB, TiDB thật (câu SQL đối soát có slot, aggregation MongoDB, DDL `stock_slot` trên TiDB, `update_many` với `$gte`), smoke và `tests/test_integration.py::test_hotspot_variants_p1_p2_contract`. EXPLAIN của câu P1 và truy vấn slot chưa có.
