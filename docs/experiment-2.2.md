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

Đã có (mặc định tắt): `--lock-order` (khóa/cập nhật các món của đơn theo `i_id` tăng dần; MySQL, TiDB), `--nowait` (`SELECT ... FOR UPDATE NOWAIT` trên dòng stock rồi thử lại theo luật chung, lỗi 3572 phân loại `lock_nowait`; chỉ variant `legacy`, vì P1 là một lệnh cập nhật không có đọc khóa; MySQL, TiDB) và `--txn-mode optimistic|pessimistic` (TiDB, đặt `tidb_txn_mode` cho từng kết nối; giá trị thật vẫn ghi ở `manifest.dbms.transaction_mode`). `--mongo-design b` (MongoDB thiết kế (b), cần `--variant p1`): đơn là MỘT tài liệu `orders` có mảng `order_lines` nhúng (collection `order_line` giữ nguyên các dòng nạp sẵn), mã đơn lấy bằng `findOneAndUpdate $inc`, mỗi món trừ kho bằng một `update` có điều kiện `s_quantity >= n`, hoàn lại các món đã trừ khi gặp món hết hàng hoặc ghi đơn thất bại (trùng `request_id`), **không có giao dịch nhiều tài liệu**; ghi dùng `{w: majority, j: true}` như (a). Điểm cam kết là ghi tài liệu `orders` (UNIQUE `request_id`); Payment vẫn dùng giao dịch như (a). Validator đọc dòng đơn từ `orders.order_lines` và đối soát của đề dùng `$unwind`. **Giới hạn của (b) (đề đã nêu):** nếu tiến trình chết giữa lúc trừ kho và lúc ghi đơn, hoặc kết quả ghi đơn không xác định và không đọc lại được (khi đó mã giữ nguyên kho), kho bị trừ mà không có đơn: luật 2 sẽ báo lệch; chưa thử bằng cách giết tiến trình. `--stored-procedure` (chỉ MySQL, variant `legacy`): toàn bộ giao dịch đặt hàng là MỘT `CALL new_order_sp(...)` (thủ tục tự `START TRANSACTION`/`COMMIT`, ROLLBACK + RESIGNAL khi lỗi, hết hàng báo bằng `SIGNAL` mã 1644 'out_of_stock'), cùng logic khóa-rồi-ghi của `legacy` nhưng không giữ khóa trong lúc chờ mạng giữa ứng dụng và CSDL (bài L2B1); thủ tục được tạo trong database của lượt chạy trước warmup; có thể kèm `--lock-order`; TiDB không hỗ trợ stored procedure nên bị từ chối. Cả năm đòn bẩy T4 đã có mã. Thử thật trên Docker MySQL: `legacy` có deadlock, `--nowait` sinh `lock_nowait` thay vì chờ, `--lock-order` hết deadlock; Stored procedure trên Docker MySQL thật: test integration `test_mysql_stored_procedure_new_order` PASS (replay, rollback khi hết hàng, ba luật, đối soát) và smoke 16 client VALID (TPS 328 so với 220 của `legacy` ở smoke nhỏ, không phải số đo). TiDB (`--txn-mode`) NOT TESTED. MongoDB (b) trên Docker thật: test integration `test_mongo_design_b_embedded_order_and_refund` PASS (hoàn kho, replay, validator, đối soát, và phát hiện lệch cài chủ động) và smoke 16 client có hết hàng thực VALID (so (a): TPS 306 so với 198 ở smoke nhỏ, chỉ để kiểm đường chạy, không phải số đo).

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
- **TiDB:** trên Docker máy dev không chạy được (3,9 GiB RAM); đã thử trên AWS (v8.5.7, 3 TiKV) ngày 2026-11-23: `pytest -m integration` 12 PASS (gồm `test_hotspot_variants_p1_p2_contract`, `test_smoke_exports`; log `results/official/fault-injection/tidb-integration-pytest.txt`) và T1, T2, T4 (bi quan/lạc quan) đã đo ở `results/official/2.2-aws/tidb3/`. **`EXPLAIN` trên TiDB v8.5.7 (2026-11-24, `EXPLAIN FORMAT='brief'`, `results/official/explain-tidb.json`):** cả bốn câu lệnh chính đều dùng `Point_Get` đúng chỉ mục: `UPDATE stock` (P1) qua `clustered index:PRIMARY(s_w_id, s_i_id)`; `UPDATE stock_slot` (P2) qua `clustered index:PRIMARY(ss_w_id, ss_i_id, ss_slot)`; đọc bộ đếm `district` (`FOR UPDATE`) qua `clustered index:PRIMARY(d_w_id, d_id)`; tìm đơn theo `request_id` qua `index:uq_request_id(request_id)`. Hai câu `UPDATE` có thêm `Selection` điều kiện `s_quantity >= n`. Mô thức cùng một lược đồ trên dataset smoke tạm (không phải dataset đo). **Vẫn NOT TESTED:** truy vấn `stock_slot` chưa có EXPLAIN; ngưỡng P3 mặc định (500 ms, 10%) chưa được chỉnh bằng số đo.

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


## Kết quả đo chính thức trên TiDB (AWS, 2026-11-22)

`results/official/2.2-aws/tidb3/`: 145 lượt trên cụm 3 TiKV (W = 10, `configs/hotspot.toml`): T1 (P1 ở 5 mức θ × 8/64/256 client và P0), T2 (P2 N ∈ {1,3,9,27} có/không cấp mã theo lô), lượt kiểm luật, T4 (đòn bẩy TiDB lạc quan/bi quan, khóa theo thứ tự). 138 lượt VALID; 7 lượt INVALID đều là P0 (đọc rồi ghi) vi phạm luật đối soát do mất cập nhật, đúng dự kiến và không xếp hạng. T3 (P3, tải vòng mở) chưa đo vì chờ chọn `T3_RATES`. Phân tích số liệu xem `SUMMARY.md` cùng thư mục; cảnh báo warmup (`WARMUP_MAY_BE_SHORT`) có ở nhiều lượt, cần xem trước khi kết luận.

## Kết quả đo chính thức trên MySQL (AWS, 2026-11-22)

`results/official/2.2-aws/mysql/`: 157 lượt trên MySQL-chỉnh 8.4.8 (m6i.8xlarge giới hạn 24 vCPU/60 GiB, buffer pool 3 GiB, `innodb_flush_log_at_trx_commit=1`, `sync_binlog=1`, W = 10, `configs/hotspot.toml`, warmup 30 s + đo 60 s, 3 lần lặp). Gồm T1 (P1 ở 5 mức θ × 8/64/256 client, P0), T2 (P2 N ∈ {1,3,9,27} có/không cấp mã theo lô), lượt kiểm luật, T4 (khóa theo thứ tự, `NOWAIT`, stored procedure). **150/157 lượt VALID; 7 lượt INVALID đều là P0** (mất cập nhật, đúng dự đoán của đề, `docs/assumptions.md`). Chưa có T3 (tải vòng mở; `T3_RATES` đặt sau khi có số này). Chạy 04:17–09:15 (giờ máy tải), CPU máy tải tối đa 386% trên 1600% (24%, dưới ngưỡng 80%).

TPS trung vị của ba lần lặp (p99 trung vị, ms trong ngoặc), một kho, P1 trừ khi ghi khác:

| Cấu hình | 8 client | 64 client | 256 client |
| --- | --- | --- | --- |
| θ = 0 | 652,6 (83) | 1.416,2 (500) | 1.464,7 (1.078) |
| θ = 0,5 | 656,2 (73) | 1.386,6 (518) | 1.489,9 (1.065) |
| θ = 0,7 | 655,2 (82) | 1.391,9 (513) | 1.458,7 (1.066) |
| θ = 0,9 | 659,1 (70) | 1.252,3 (476) | 1.283,0 (726) |
| một món (mọi yêu cầu chọn một mặt hàng) | 412,0 (63) | 425,8 (474) | 427,4 (1.484) |

- **Không có điểm gãy rõ trong θ ∈ [0, 0,7]**; TPS giảm khoảng 11% ở θ = 0,9 (64 client) và sụp xuống ~425 chỉ khi mọi yêu cầu chọn một món (một dòng tồn kho bị tuần tự hóa), gần như không đổi theo số client (412 → 427 khi 8 → 256 client) và p99 tăng tới 1,5 s.
- **T2 (một món, 64 client, lô mã 50):** P2 N=27 đạt 2.741 TPS (6,4 lần P1 = 425,8), N=9 đạt 1.847, N=3 đạt 992, N=1 đạt 397 (không hơn P1, vì cùng một dòng khóa). Ở θ = 0,9: N=27 đạt 1.780 (+42% so với P1 1.252), N=3 và N=9 đạt khoảng 1.810 và 1.786: phần còn lại bị chặn ở chỗ khác chứ không còn là dòng tồn kho nóng.
- **T4 (một món, 128 client, so với `legacy` 375):** stored procedure 633 (+69%), `NOWAIT` 644 (+72%), khóa theo thứ tự 379 (không khác `legacy`, vì đơn một món không có thứ tự khóa để sắp xếp). Ở θ = 0,9: `legacy` 1.202, stored procedure 1.550 (+29%), `NOWAIT` 1.235, khóa theo thứ tự 1.184. Mọi lượt T4 VALID.
- **Lượt kiểm luật:** P1, P2, P3 đều VALID (3/3); P0 INVALID (0/1).
- **Warmup:** `results/official/warmup-analysis-mysql.md`: 10/187 lượt ngoài khoảng ramp 0,9–1,1, không có lượt TPS thấp; trung vị ramp 0,99–1,03 nên giữ warmup 30 giây.
- **Giới hạn:** T3 ở mục riêng bên dưới (MySQL) và ở mục MongoDB; T3 trên TiDB chưa đo; số tuyệt đối không so với 2.1 (cùng W = 10 nhưng khác lượt chạy và cỡ máy).

## Kết quả đo chính thức trên MongoDB (AWS, 2026-11-22)

`results/official/2.2-aws/mongo/`: 135 lượt trên MongoDB 8.0.20, thiết kế (a) (giao dịch nhiều tài liệu, replica set một nút, `{w: majority, j: true}`), WiredTiger cache 3 GiB, m6i.8xlarge giới hạn 24 vCPU/60 GiB, W = 10, `configs/hotspot.toml`, warmup 30 s + đo 60 s, 3 lần lặp (chạy 11:37–16:25 giờ máy tải). **135/135 lượt VALID, kể cả P0** (khác MySQL, nơi 7 lượt P0 INVALID). Chưa có T3.

TPS trung vị ba lần lặp (p99 trung vị, ms), một kho, P1 thiết kế (a). **Cột 256 client là số đo lại sau khi nâng `nofile` của mongod** (mục T3 bên dưới), ở `mongo-t1-c256-postfix/`; số đo trước đó ở `mongo/` (θ = 0: 2.421; 0,5: 2.398; 0,7: 2.373; 0,9: 2.168; một món: 790) thấp hơn 12–46% do giới hạn fd:

| Cấu hình | 8 client | 64 client | 256 client |
| --- | --- | --- | --- |
| θ = 0 | 538,5 (104) | 1.883,7 (346) | 2.700 (353) |
| θ = 0,5 | 538,8 (103) | 1.879,8 (346) | 2.682 (354) |
| θ = 0,7 | 538,0 (104) | 1.867,0 (346) | 2.679 (354) |
| θ = 0,9 | 526,4 (109) | 1.698,1 (346) | 2.564 (353) |
| một món | 402,9 (180) | 672,7 (338) | 1.153 (346) |

- **Không có điểm gãy rõ trong θ ∈ [0, 0,7]**; θ = 0,9 thấp hơn ~10% ở 64 client; "một món" thấp hơn θ = 0 khoảng 2,8 lần ở 64 client (673 so với 1.884).
- **T2 (một món, 64 client, lô mã 50):** P2 N=27 đạt 3.955 TPS (5,9 lần P1 = 672,7), N=9 đạt 2.854, N=3 đạt 1.603, N=1 đạt 807,5 (N=1 có lô mã hơn P1 một ít). Không lô mã ở N=9: 1.893, thấp hơn có lô (2.854): cấp mã đơn cũng là điểm nóng. Ở θ = 0,9: N=1 có lô 2.638 (+55% so với P1 1.698), N=3 2.997, N=9 3.060, N=27 3.169.
- **T4, MongoDB thiết kế (b) (không giao dịch nhiều tài liệu), P1:** một món 128 client 8.354 TPS (p99 30 ms) so với (a) 845 (p99 341 ms), gấp ~9,9 lần; 32 client 2.797 so với 560. θ = 0,9, 128 client: (b) 5.839 so với (a) 2.157 (2,7 lần); 32 client 1.977 so với 1.268. Mọi lượt (b) VALID. Giới hạn (b) đã nêu ở trên: chưa thử giết tiến trình giữa trừ kho và ghi đơn. **Lưu ý máy tải:** ở các lượt (b) 128 client CPU máy tải đạt 1.178–1.246% trên 1.600% (74–78%, sát ngưỡng 80% của AGENTS.md; `results/official/VERIFY.md`), nên 8.354 TPS có thể bị chặn một phần bởi load generator Python và là cận dưới của năng lực thật của (b); tỉ lệ 9,9× so với (a) vì vậy cũng là cận dưới.
- **P0 trên MongoDB:** cả 6 điểm P0 (θ = 0 và 0,9, 8 và 64 client; một món 8/64 client) VALID, lượt kiểm luật P0 cũng VALID. Giải thích có thể là giao dịch nhiều tài liệu của MongoDB phát hiện xung đột ghi (WriteConflict) khi hai giao dịch cùng sửa một dòng tồn kho, nên "đọc rồi ghi" không mất cập nhật; chưa kiểm chứng riêng (chưa đọc bộ đếm lỗi `write_conflict` theo lượt cho kết luận này).
- **Hằng số p99 ~340–350 ms của (a) là tổng thời gian chờ retry, không phải độ trễ của DBMS:** p99 là độ trễ end-to-end gồm cả backoff. Tổng chờ của 5 lần retry là 10·(1+2+4+8+16) = 310 ms; các yêu cầu hết 5 lần retry vì `write_conflict` (khoảng 1% yêu cầu trở lên) kéo p99 lên ~345 ms. Dữ liệu (các lượt (a) vòng kín, `results/official/2.2-aws/mongo/`): retry < 1% → p99 11 ms (6 lượt); retry 1–10% → trung vị 67 ms; retry 10–25% → 114 ms; retry ≥ 25% → trung vị 345 ms (184–349, 69 lượt). Thiết kế (b) không có retry xung đột nên p99 20–50 ms. Đây là giải thích suy từ phép tính và phân nhóm theo retry, chưa phải thí nghiệm đổi backoff.
- **Warmup:** `results/official/warmup-analysis-mongo.md`: 0/135 lượt ngoài khoảng ramp 0,9–1,1, trung vị ramp 1,00, CV trung vị 0,03; giữ warmup 30 giây.
- **Giới hạn:** số tuyệt đối không so với 2.1; so sánh giữa hệ dùng cỡ máy đã ghi ở `docs/assumptions.md`.

### T3 trên MongoDB (tải vòng mở, θ = 0,9, P2 so với P3)

`results/official/2.2-aws/mongo-t3/` (48 lượt VALID; P2 ở 256 client trong thư mục này đo trước khi sửa `nofile` nên bỏ qua) và `mongo-t3-p2-postfix/` (12 lượt, P2 ở 256 client đo lại sau khi sửa). Tải đặt 1.500, 2.500, 3.100, 3.700 yêu cầu/giây (xấp xỉ 50, 80, 100, 120% đỉnh P2 θ = 0,9 ở T2, ~3.100; `T3_RATES="1500 2500 3100 3700"`). Trung vị 3 lần lặp, TPS thực (p99 ms):

| Tải đặt | 128 client P2 | 128 client P3 | 256 client P2 (sau sửa) | 256 client P3 |
| --- | --- | --- | --- | --- |
| 1.500 | 1.500 (28) | 1.500 (60) | 1.500 (28) | 1.500 (28) |
| 2.500 | 2.500 (251) | 2.500 (240) | 2.500 (77) | 2.500 (61) |
| 3.100 | 3.097 (235) | 3.100 (49) | 3.099 (315) | 3.100 (96) |
| 3.700 | 3.673 (380) | 3.686 (320) | 3.699 (327) | 3.700 (67) |

- Mọi điểm: P2 và P3 đều theo kịp tải đặt (TPS ≈ tải), tỉ lệ hủy ≤ 0,03%. P3 **không tăng TPS**; lợi ích đo được chỉ là p99 thấp hơn ở 256 client khi tải cao (96 so với 315 ms ở 3.100; 67 so với 327 ms ở 3.700). Ở 128 client không có khác biệt rõ (p99 dao động giữa các lần lặp, ví dụ P3 3.100 có p99 26, 49, 232 ms).
- Tải đặt thấp hơn hoặc xấp xỉ năng lực của MongoDB nên chưa có điểm bão hòa; muốn thấy P3 giữ TPS khi quá tải cần tải trên ~4.000 (chưa đo).
- **Sự cố nofile.** mongod chạy với `nofile` mềm 1.024 (cảnh báo trong log khởi động; khuyến nghị 64.000). Ở P3 + 256 client, 4 điểm (10, 12, 14, 16) lỗi `BrokenBarrierError` (client không kịp khởi động trong 120 s; 5 lượt không có số đo, log ở `mongo-t3/logs/m22-mongo-t3/failed-*`); lúc điểm 16 log mongod ghi "Too many open files" rồi mongod crash (exit 139). Sau khi thêm `ulimits.nofile = 64000` vào `infra/aws/compose/mongo.aws.yml` và tạo lại container, cả 4 điểm chạy được. Chắc chắn: crash và lỗi ở điểm 16 do hết fd. Chưa chắc: với điểm 10, 12, 14 log mongod không ghi lỗi tương ứng (khả dĩ fd tích dần sau nhiều giờ chạy); chỉ biết sửa xong thì hết lỗi. Hệ quả: các lượt Mongo ở 256 client trước khi sửa bị hạ TPS (P2 mở vòng thiếu tải, 1.308/1.500); đã đo lại T1 ở 256 client và P2 ở T3. **Không cần đo lại các lượt ≤128 client** (T1 8/64, T2 64, T4 32/128, lượt kiểm luật): tổng lỗi `connection` và `timeout` ở 8/32/64/128 client (120 lượt) bằng 0, còn ở 256 client trước khi sửa (15 lượt) là 8.597 `connection` và 15.016 `timeout`; log mongod trước khi tạo lại container đã mất nên đây là bằng chứng gián tiếp từ bộ đếm lỗi phía client.

## Số liệu tranh chấp, kiểm chứng P0 và hình báo cáo (offline, 2026-11-23)

Sinh từ các `result.json`/`INDEX.csv` đã commit, không đo thêm: `scripts/contention_summary.py` → `results/official/2.2-aws/CONTENTION.md`; `scripts/make_figures.py` → `results/official/figures/` (6 hình PNG và CSV nguồn để đối chiếu số).

- **Mongo P0 VALID đã có bằng chứng ủng hộ:** mỗi lượt P0 ở 64 client ghi 74.000–79.000 lỗi `write_conflict` (khoảng 34% yêu cầu phải thử lại), 8 client 6.000–10.700 và không lượt nào mất cập nhật (0 INVALID, 21 lượt). MySQL và TiDB không có lỗi xung đột tương ứng ở P0 (đọc không khóa) và cả 7 + 7 lượt đều INVALID (INV2: tổng 1.335 và 1.038 dòng lệch). Lưu ý: đây là bằng chứng gián tiếp (đếm lỗi), chưa phải thí nghiệm riêng tắt phát hiện xung đột.
- **INV1 vẫn đúng ở mọi lượt P0** vì tồn đầu 10^9 và ứng dụng kiểm tra ở bước đọc; lỗi của P0 là mất cập nhật (INV2), không phải tồn âm.
- **MySQL nghẽn khóa ngay cả khi θ=0 (một kho):** tổng thời gian chờ khóa dòng chiếm khoảng 73% thời gian client (64 client × 60 s) ở θ=0 và 97% ở "một món". Vì vậy không có điểm gãy ở θ ≤ 0,7: một kho đã nghẽn ở các hàng dùng chung (nhiều khả năng bộ đếm `d_next_o_id`/hàng kho; **chưa xác nhận** bằng `data_locks`). Mongo (a) cho thấy tranh chấp qua `write_conflict` (retry 28–40%) thay vì chờ khóa.
- **Tách cấp mã theo lô khỏi chia slot (P2 N=9, 64 client, không lô → lô 50):** một món: MySQL 1.504 → 1.847, MongoDB 1.893 → 2.854, TiDB 958 → 1.286; θ=0,9: MySQL 1.423 → 1.786, MongoDB 1.874 → 3.060, TiDB 912 → 2.276 (TiDB gấp 2,5 lần: bộ đếm mã đơn là điểm nóng chính ở θ=0,9 trên TiDB). Lô mã là biến riêng, phải báo cáo riêng.
- **Bảng 2×2 TiDB (θ=0,9, 64 client, lô 50):** P1 616 (1 TiKV) → 751 (3 TiKV) = 1,22×; P2 N=27 845 → 2.121 = 2,51× (min–max 1.545–2.188 ở 3 TiKV); chia slot một mình: 1,37× (1 TiKV) và 2,82× (3 TiKV); cả hai: 3,44×. **Chưa xác nhận bằng vị trí Region/leader theo TiKV** nên chưa kết luận cơ chế.
- **T4 TiDB một món, 128 client:** bi quan 250 TPS so với lạc quan 22 (lạc quan sụp trên hot SKU vì xung đột commit).

### T3 trên MySQL (tải vòng mở, θ = 0,9, P2 so với P3; AWS, 2026-11-23)

`results/official/2.2-aws/mysql-t3/`: 48 lượt VALID (MySQL-chỉnh 8.4.8, 24 vCPU/60 GiB, buffer pool 3 GiB; tải đặt 900, 1.450, 1.800, 2.200 yêu cầu/giây ≈ 50/80/100/120% đỉnh P2 θ = 0,9 ở T2 là ~1.810; `T3_RATES="900 1450 1800 2200"`). Trung vị 3 lần lặp, TPS thực (p99 ms):

| Tải đặt | 128 client P2 | 128 client P3 | 256 client P2 | 256 client P3 |
| --- | --- | --- | --- | --- |
| 900 | 900 (106) | 900 (56) | 900 (50) | 900 (48) |
| 1.450 | 1.441 (441) | 1.438 (497) | 1.450 (93) | 1.450 (74) |
| 1.800 | 1.778 (641) | 1.297 (2.076) | 1.798 (580) | 1.303 (4.796) |
| 2.200 | 1.917 (695) | 1.144 (2.603) | 2.055 (1.750) | 1.100 (4.990) |

- **Dưới ~80% năng lực (≤ 1.450), P2 và P3 như nhau. Từ 100% trở lên P3 KÉM hơn P2** trên MySQL: ở 1.800 TPS đạt 1.297 so với 1.778 (−27%) và p99 2.076 so với 641 ms; ở 2.200: 1.144 so với 1.917 (−40%).
- **Nguyên nhân (đọc từ `throttle_result`):** bộ điều tiết P3 hạ giới hạn đồng thời xuống 2–3 (`min_limit`) vì p99 của giao dịch nóng vượt ngưỡng 500 ms của đặc tả (p99 của chính P2 ở tải này đã 580–700 ms), nên nó liên tục chia đôi L; 23–49% yêu cầu bị từ chối do hàng đợi đầy (`rejected_pct`), thời gian chờ chuyển từ DBMS sang tầng ứng dụng. Đây trả lời trực tiếp câu hỏi của đề: trên MySQL ở tải này P3 **chỉ chuyển thời gian chờ** chứ không giảm sụp hiệu năng, và còn làm giảm throughput.
- **Giới hạn quan trọng:** chỉ thử một bộ ngưỡng (p99 500 ms, abort 10%, theo đặc tả); kết quả phụ thuộc ngưỡng, chưa thử ngưỡng khác (đặt cao hơn p99 bình thường của hệ có thể đổi kết luận). Trái lại trên MongoDB ngưỡng này không bị chạm (p99 thấp hơn) nên P3 không có hại, chỉ giảm p99 ở 256 client.
- **Warmup:** `results/official/warmup-analysis-mysql-t3.md`: 10/48 lượt ngoài khoảng ramp 0,9–1,1 (9 lượt ramp > 1,1), không lượt nào TPS thấp; trung vị ramp 1,00.


### Độ nhạy của P3 theo ngưỡng p99 trên MySQL (AWS, 2026-11-24)

`results/official/2.2-aws/mysql-p3sens/`: 30 lượt VALID, **cùng phiên, cùng máy ảo và dataset** với cấu hình T3 trước (MySQL-chỉnh 24 vCPU/60 GiB, buffer pool 3 GiB, `configs/hotspot.toml`, 256 client, θ = 0,9, N = 9, lô mã 50, tải vòng mở, hàng đợi 64, 3 lần lặp). Chỉ đổi ngưỡng p99 của bộ điều tiết P3 (`--p99-limit-ms`; ngưỡng abort giữ 10%); ngưỡng 500 ms (mặc định theo đặc tả) được đo hai lần (đầu và cuối mỗi mức tải) để kiểm trôi.

| Tải đặt | Cấu hình | TPS thực trung vị (min–max) | p99 trung vị (ms) | Yêu cầu bị từ chối (%) |
| --- | --- | --- | --- | --- |
| 1.800 | P2 | 1.788 (1.788–1.800) | 555 | 0,0 |
| 1.800 | P3, ngưỡng 500 ms | 1.399 (1.285–1.505) | 4.712 | 20,7 |
| 1.800 | P3, ngưỡng 500 ms (lặp lại) | 1.383 (1.169–1.596) | 4.216 | 21,6 |
| 1.800 | P3, ngưỡng 1000 ms | 1.800 (1.790–1.800) | 598 | 0,0 |
| 1.800 | P3, ngưỡng 2000 ms | 1.799 (1.786–1.800) | 608 | 0,0 |
| 2.200 | P2 | 2.041 (2.041–2.130) | 1.736 | 5,7 |
| 2.200 | P3, ngưỡng 500 ms | 1.071 (971–1.074) | 5.172 | 50,5 |
| 2.200 | P3, ngưỡng 500 ms (lặp lại) | 1.070 (1.056–1.159) | 5.005 | 50,5 |
| 2.200 | P3, ngưỡng 1000 ms | 1.908 (1.853–2.099) | 2.128 | 12,8 |
| 2.200 | P3, ngưỡng 2000 ms | 2.034 (1.984–2.110) | 1.634 | 5,9 |

- **Kết quả:** với ngưỡng 1.000 hoặc 2.000 ms, **P3 không còn kém P2**: ở 1.800 yêu cầu/giây P3 đạt 1.800 và 1.799 TPS (P2: 1.788), p99 598 và 608 ms (P2: 555); ở 2.200, P3 ngưỡng 2.000 ms đạt 2.034 TPS (P2: 2.041) với p99 1.634 ms (P2: 1.736), P3 ngưỡng 1.000 ms đạt 1.908 TPS (thấp hơn P2 khoảng 7%) với p99 2.128 ms. Với ngưỡng 500 ms, P3 giảm TPS xuống 1.399 và 1.383 (hai lần đo) ở 1.800, và 1.071 và 1.070 ở 2.200 (tái hiện kết quả T3 trước: 1.303 và 1.100) và từ chối khoảng 21% và 51% yêu cầu.
- **Diễn giải:** ngưỡng 500 ms thấp hơn p99 tự nhiên của MySQL ở các mức tải này (p99 của P2 là 555 ms ở 1.800 và 1.736 ms ở 2.200), nên bộ điều khiển liên tục chia đôi giới hạn đồng thời (`min_limit` trung vị 1–1,5) và từ chối yêu cầu. Khi ngưỡng cao hơn p99 tự nhiên thì giới hạn đồng thời giữ ở 256 (ngưỡng 1.000 và 2.000 ms ở 1.800) hoặc tụt vừa phải (21 và 64 ở 2.200) và P3 gần bằng P2. Kết luận "P3 làm giảm TPS trên MySQL" của T3 vì vậy chỉ đúng khi ngưỡng thấp hơn p99 tự nhiên của hệ; **đây là hiệu ứng của ngưỡng, không phải của P3 nói chung**, và P3 ở ngưỡng cao chưa cho thấy lợi ích nào so với P2 trên MySQL (TPS và p99 tương đương).
- **Giới hạn:** chỉ ba ngưỡng (500, 1.000, 2.000 ms) và hai mức tải ở 256 client; chưa đo ngưỡng abort khác; trôi giữa hai lần đo ngưỡng 500 ms khá lớn ở 1.800 (1.169–1.596 TPS giữa các lần lặp). Warmup: 4/30 lượt có cảnh báo `warmup_may_be_short`.
