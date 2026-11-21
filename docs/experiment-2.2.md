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

## T4: đòn bẩy riêng từng hệ

Đã có (mặc định tắt): `--lock-order` (khóa/cập nhật các món của đơn theo `i_id` tăng dần; MySQL, TiDB), `--nowait` (`SELECT ... FOR UPDATE NOWAIT` trên dòng stock rồi thử lại theo luật chung, lỗi 3572 phân loại `lock_nowait`; chỉ variant `legacy`, vì P1 là một lệnh cập nhật không có đọc khóa; MySQL, TiDB) và `--txn-mode optimistic|pessimistic` (TiDB, đặt `tidb_txn_mode` cho từng kết nối; giá trị thật vẫn ghi ở `manifest.dbms.transaction_mode`). `--mongo-design b` (MongoDB thiết kế (b), cần `--variant p1`): đơn là MỘT tài liệu `orders` có mảng `order_lines` nhúng (collection `order_line` giữ nguyên các dòng nạp sẵn), mã đơn lấy bằng `findOneAndUpdate $inc`, mỗi món trừ kho bằng một `update` có điều kiện `s_quantity >= n`, hoàn lại các món đã trừ khi gặp món hết hàng hoặc ghi đơn thất bại (trùng `request_id`), **không có giao dịch nhiều tài liệu**; ghi dùng `{w: majority, j: true}` như (a). Điểm cam kết là ghi tài liệu `orders` (UNIQUE `request_id`); Payment vẫn dùng giao dịch như (a). Validator đọc dòng đơn từ `orders.order_lines` và đối soát của đề dùng `$unwind`. **Giới hạn của (b) (đề đã nêu):** nếu tiến trình chết giữa lúc trừ kho và lúc ghi đơn, hoặc kết quả ghi đơn không xác định và không đọc lại được (khi đó mã giữ nguyên kho), kho bị trừ mà không có đơn: luật 2 sẽ báo lệch; chưa thử bằng cách giết tiến trình. **Chưa có:** MySQL stored procedure. Thử thật trên Docker MySQL: `legacy` có deadlock, `--nowait` sinh `lock_nowait` thay vì chờ, `--lock-order` hết deadlock; TiDB (`--txn-mode`) NOT TESTED. MongoDB (b) trên Docker thật: test integration `test_mongo_design_b_embedded_order_and_refund` PASS (hoàn kho, replay, validator, đối soát, và phát hiện lệch cài chủ động) và smoke 16 client có hết hàng thực VALID (so (a): TPS 306 so với 198 ở smoke nhỏ, chỉ để kiểm đường chạy, không phải số đo).

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

## Ma trận Tầng 1

`scripts/run-matrix-2.2.sh <mysql|mongo|tidb> [--tier t1|t2|t3|c|all] [--dry-run]` chạy trên VM `loadgen` (chế độ remote), cùng cách dùng như `run-matrix-2.1.sh`: T1 (P1 ở 15 điểm θ × client, P0 ở 6 điểm; P0 được phép INVALID), T2 (P2 N = 1, 3, 9, 27 có lô mã, đối chứng không lô ở N = 1 và 9, θ = 0,9 và "1 món", 64 client), T3 (P2 so với P3 ở 128/256 client, tải vòng mở; **chỉ chạy khi đặt `T3_RATES`** sau khi xem T1/T2), `c` (lượt kiểm luật có hết hàng thực). Tổng 37 điểm không kể T3, mỗi điểm 3 lần × (30 s + 60 s). Điểm P1 không lô mã của T2 lấy từ T1 (64 client). Đã `--dry-run` đủ tier và chạy thật thu nhỏ trên Docker MySQL (tier `c` và 3 điểm `t2`, remote mode giả lập): script, reset giữa điểm, P0 INVALID dự kiến và báo cáo tổng hợp hoạt động.

## Kết quả và trường mới

`result.json`/`INDEX.csv` có thêm `variant`, `slots`, `order_id_batch` (lượt 2.1 cũ đọc là `legacy`, không slot, lô 0); `SCHEMA_VERSION = 4`. `measurement.slot_attempts_per_item` = số lần thử slot trung bình mỗi lần trừ một món nóng qua slot, kể cả lần hết hàng và lần retry (`null` nếu không phải p2). `variant_setup` trong `result.json` ghi số dòng slot và thời gian chuẩn bị. Báo cáo gộp (`flashsale report`) tách nhóm theo variant/slot/lô mã.

## Đã kiểm thử / chưa kiểm thử

- Đã chạy: unit test (`tests/test_hotspot.py`, `tests/test_throttle.py`) PASS; `pytest -m integration` trên **MySQL 8.4.8 thật (Docker máy dev, nhãn sơ bộ)**: 4 test PASS gồm `test_hotspot_variants_p1_p2_contract`; smoke ngoài chương trình (ngân sách RAM Docker bị bỏ qua cho smoke) trên MySQL: legacy, P1 + lô mã, P2 N=1 và N=3 VALID, P0 INVALID đúng như dự kiến (mất cập nhật, đối soát của đề báo 1 dòng lệch), P3 và tải vòng mở VALID với giới hạn L giảm 8→1 khi đặt ngưỡng p99 = 1 ms.
- Đã chạy thêm trên **MongoDB 8.0.20 thật (Docker máy dev, sơ bộ)**: 4 test integration PASS (gồm `test_hotspot_variants_p1_p2_contract`, tức aggregation đối soát có slot hoạt động); smoke legacy, P0, P1 + lô mã, P2 N=1 và N=3, P3, tải vòng mở đều VALID. **P0 trên MongoDB VALID, không bán vượt**: giao dịch snapshot hủy khi xung đột ghi nên không mất cập nhật (đề dự đoán trước điều này: "nếu ra vậy thì đó là kết quả"); smoke nhỏ chưa đủ để kết luận ở tải cao.
- **NOT TESTED:** TiDB thật (DDL `stock_slot` với `CLUSTERED`, `EXPLAIN UPDATE`, đối soát có slot, chế độ lạc quan/bi quan) vì Docker máy dev chỉ có 3,9 GiB RAM; `test_smoke_exports` vẫn cần Docker đủ 8 CPU/16 GiB; truy vấn `stock_slot` chưa có EXPLAIN; ngưỡng P3 mặc định (500 ms, 10%) chưa được chỉnh bằng số đo.

## Smoke G1 trên AWS (2026-11-21, sơ bộ, không phải số đo chính thức)

Stack `mysql` (MySQL-chỉnh, buffer pool 3 GiB, c6i.4xlarge giới hạn 12 vCPU/24 GiB; máy tải c6i.xlarge, CPU máy tải ≤ 154% trên 400%), W=10, tồn 10^9, một kho, θ=0,9, 32 client, warmup 10 s + đo 20 s, **1 lần lặp** (không đạt định nghĩa "Đã đo": thiếu 3 lần lặp, warmup/đo ngắn). Đã `terraform destroy`.

| Điểm | TPS (đo) | p99 ms | Kết quả |
| --- | --- | --- | --- |
| P0, 1 món | 429 | 292 | **INVALID** (luật 2: mất cập nhật) |
| P1, 1 món | 422 | 293 | VALID |
| P2 N=9 + lô mã 50, 1 món | 1.801 | 176 | VALID (1,0 lần thử slot/lần trừ) |
| P3 N=9 + lô mã 50, 1 món | 1.766 | 201 | VALID; L không giảm (32→32), vì p99 dịch vụ < 500 ms |
| P1, θ=0,9 (không "1 món") | 1.167 | 277 | VALID |

Chỉ chứng minh mã chạy đúng trên AWS; chưa kết luận về hiệu quả (cần T1/T2 đủ 3 lần lặp 30 + 60 s). Bằng chứng lưu ở `.work/g1-smoke-aws/` (không đưa lên Git).
