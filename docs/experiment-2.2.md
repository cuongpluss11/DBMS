# Thực nghiệm 2.2 (Flash-sale: tranh chấp khóa) — trạng thái mã nguồn P0–P2

Chưa có số đo nào của mục 2.2 trong repo. Tài liệu này mô tả phần đã có trong mã (P0, P1, P2, P3, cấp mã đơn theo lô, tải vòng mở); T4 (5 đòn bẩy) chưa làm. Khác biệt với tài liệu ý tưởng: xem phần "mục 2.2" của `docs/assumptions.md`.

## Biến thể trừ kho

| `--variant` | Hành vi | Ghi chú |
| --- | --- | --- |
| `legacy` (mặc định) | `SELECT ... FOR UPDATE` rồi cộng delta (cách của 2.1) | Số 2.1 không đổi |
| `p0` | Đọc `s_quantity` không khóa, kiểm tra ở ứng dụng, ghi giá trị tuyệt đối | Đối chứng mất cập nhật; validator/đối soát bắt lệch luật 2 |
| `p1` | `UPDATE ... SET s_quantity = s_quantity - n WHERE ... AND s_quantity >= n`; số dòng ≠ 1 là hết hàng | Baseline an toàn |
| `p2` | P1 trên `--slots N` dòng con cho `--hot-items K` món hạng đầu; món còn lại dùng P1 | Bảng phụ `stock_slot`; chuẩn bị trước warmup |
| `p3` | P2 + điều tiết thích ứng cho các đơn chạm món nóng | Xem phần P3 bên dưới |

`--order-id-batch B` (0 = như 2.1): mỗi worker xin lô B mã đơn cho mỗi (kho, quận) thay vì tăng `d_next_o_id` mỗi đơn. Độc lập với variant (T2 cần cả hai nhánh có/không).

## P3 (điều tiết thích thích ứng) và tải vòng mở

- **Giới hạn L:** một giới hạn mức đồng thời dùng chung mọi process cho các đơn chạm ít nhất một món nóng (thanh toán và đơn không nóng không bị chặn). Khởi đầu L = số client; sàn `--limit-min` (mặc định 1), trần = số client.
- **Bộ điều khiển (mỗi giây một bước):** p99 **độ trễ dịch vụ** (không gồm hàng đợi, để không tự khuếch đại việc chờ) hoặc tỉ lệ hủy (deadlock, write conflict, timeout, abort) trên các giao dịch nóng vượt `--p99-limit-ms` (500) hoặc `--abort-limit-pct` (10) thì L giảm một nửa (có sàn); cả hai dưới ngưỡng thì L tăng 1 (có trần). Giây không có giao dịch nóng thì giữ nguyên. p99 được ước lượng từ biểu đồ ô tăng 20% nên có thể cao hơn thực tối đa 20%.
- **Độ trễ báo cáo của P3** tính từ lúc yêu cầu đến (hoặc được sinh ra, ở vòng kín) tới khi xong, gồm thời gian chờ cổng điều tiết; `queue_wait_mean_ms` và `queue_wait_p99_ms` là phần chờ trước khi bắt đầu chạy.
- **Tải vòng mở:** `--arrival-rate R` (yêu cầu/giây, tổng, chia theo tỉ lệ client của từng process), `--queue-size Q` (hàng đợi hữu hạn mỗi process). Yêu cầu đến theo lịch cố định, độ trễ tính từ mốc theo lịch (không bỏ sót khi hệ chậm). Hàng đợi đầy thì từ chối ngay (`busy`, tính vào `rejected`/`rejected_pct`, không tính vào `abort_pct`); yêu cầu còn trong hàng đợi lúc hết phase ghi ở `unserved_at_deadline`. Chưa có chế độ "đợt bùng nổ" (chỉ tốc độ cố định).
- `result.json` có `throttle_result` (L đầu, L cuối, L thấp nhất, số lần điều chỉnh, chuỗi từng giây).

## Lệnh

Profile `configs/hotspot.toml` (W=10, tồn 10^9, một kho, θ=0,9, 64 client; mặc định P1). Dataset nạp bằng `flashsale load` như 2.1; mọi variant dùng chung một dataset (slot được tạo và xóa trong mỗi lượt).

```powershell
flashsale run mysql --config configs/hotspot.toml --dataset <ten-dataset> --reset-between --variant p0 --theta 0.9 --concurrency 64
flashsale run mysql --config configs/hotspot.toml --dataset <ten-dataset> --reset-between --variant p2 --slots 9 --order-id-batch 50 --hot-item
```

Smoke nhỏ (cần DBMS đang chạy): `flashsale smoke mysql --start --variant p2 --slots 3 --hot-items 5` (profile `smoke.toml`, tồn 20, có hết hàng). Lượt kiểm luật có hết hàng thực: `--config configs/correctness.toml --variant p2 --slots 9`.

## Kết quả và trường mới

`result.json`/`INDEX.csv` có thêm `variant`, `slots`, `order_id_batch` (lượt 2.1 cũ đọc là `legacy`, không slot, lô 0); `SCHEMA_VERSION = 4`. `measurement.slot_attempts_per_item` = số lần thử slot trung bình mỗi lần trừ một món nóng qua slot, kể cả lần hết hàng và lần retry (`null` nếu không phải p2). `variant_setup` trong `result.json` ghi số dòng slot và thời gian chuẩn bị. Báo cáo gộp (`flashsale report`) tách nhóm theo variant/slot/lô mã.

## Đã kiểm thử / chưa kiểm thử

- Đã chạy: unit test (`tests/test_hotspot.py`, `tests/test_throttle.py`) PASS; `pytest -m integration` trên **MySQL 8.4.8 thật (Docker máy dev, nhãn sơ bộ)**: 4 test PASS gồm `test_hotspot_variants_p1_p2_contract`; smoke ngoài chương trình (ngân sách RAM Docker bị bỏ qua cho smoke) trên MySQL: legacy, P1 + lô mã, P2 N=1 và N=3 VALID, P0 INVALID đúng như dự kiến (mất cập nhật, đối soát của đề báo 1 dòng lệch), P3 và tải vòng mở VALID với giới hạn L giảm 8→1 khi đặt ngưỡng p99 = 1 ms.
- Đã chạy thêm trên **MongoDB 8.0.20 thật (Docker máy dev, sơ bộ)**: 4 test integration PASS (gồm `test_hotspot_variants_p1_p2_contract`, tức aggregation đối soát có slot hoạt động); smoke legacy, P0, P1 + lô mã, P2 N=1 và N=3, P3, tải vòng mở đều VALID. **P0 trên MongoDB VALID, không bán vượt**: giao dịch snapshot hủy khi xung đột ghi nên không mất cập nhật (đề dự đoán trước điều này: "nếu ra vậy thì đó là kết quả"); smoke nhỏ chưa đủ để kết luận ở tải cao.
- **NOT TESTED:** TiDB thật (DDL `stock_slot` với `CLUSTERED`, `EXPLAIN UPDATE`, đối soát có slot, chế độ lạc quan/bi quan) vì Docker máy dev chỉ có 3,9 GiB RAM; `test_smoke_exports` vẫn cần Docker đủ 8 CPU/16 GiB; truy vấn `stock_slot` chưa có EXPLAIN; ngưỡng P3 mặc định (500 ms, 10%) chưa được chỉnh bằng số đo.
