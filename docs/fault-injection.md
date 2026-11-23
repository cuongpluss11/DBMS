# Fault injection: kiểm chứng ba luật tồn kho khi có sự cố (mục 2.2)

## Mục tiêu và mô hình lỗi

Kiểm chứng rằng cơ chế idempotency và giao dịch giữ được INV1 (tồn không âm), INV2 (tồn đầu − tồn cuối = tổng số lượng trong đơn đã commit) và INV3 (mỗi yêu cầu thành công có đúng một đơn) khi **ứng dụng hoặc kết nối gặp sự cố**.

**Mô hình lỗi công bố:** tiến trình ứng dụng chết hoặc mất kết nối trong lúc một yêu cầu đang chạy; DBMS và mạng giữa các node vẫn sống. **Không** mô phỏng DBMS chết, mất đĩa hay chia cắt mạng. Kết luận chỉ có giá trị trong phạm vi này (AGENTS.md mục 10).

## Điểm ngắt

| Điểm | Ý nghĩa | Hiện thực |
| --- | --- | --- |
| `before_commit` | Mọi lệnh ghi đã chạy, chưa commit; giao dịch bị hủy | `FaultyAdapter` (`src/flashsale/faults.py`) |
| `crash_before_commit` | Như trên nhưng là tiến trình chết (`ProcessCrash`, BaseException); adapter đó không dùng lại được | `FaultyAdapter` |
| `after_commit` | Commit THÀNH CÔNG nhưng ứng dụng không nhận phản hồi (lỗi kết nối mơ hồ) | `FaultyAdapter` |
| `fail_reads` | Bước đối chiếu idempotency sau commit mơ hồ cũng bị lỗi N lần | `FaultyAdapter` (chỉ sau khi đã có `after_commit`, để lần kiểm tra trùng trong chính giao dịch không bị ảnh hưởng) |
| Giết tiến trình thật | SIGKILL/TerminateProcess ở thời điểm ngẫu nhiên, worker thay thế thử lại cùng `request_id` | `scripts/fault_kill_cycles.py` |
| `crash_on_insert` | Chết đúng giữa trừ kho và ghi đơn (MongoDB thiết kế (b)) | `FaultyAdapter` |

Lớp bọc cho phép đặt lỗi ở điểm xác định (tái lập được); script giết tiến trình bao phủ mọi điểm còn lại ở thời điểm ngẫu nhiên, gồm cả "chết khi đang retry".

## Giả thuyết (đặt trước khi chạy) và kết quả

| Kịch bản | Kỳ vọng | MySQL | MongoDB (a) | TiDB |
| --- | --- | --- | --- | --- |
| Chết/hủy trước commit, sau đó thử lại | Không dấu vết (không đơn, không trừ kho, mã đơn không nhích); thử lại tạo đúng một đơn; thử lần hai không tạo đơn thứ hai | PASS | PASS | PASS |
| Mất kết nối trước commit hai lần rồi thành công | Một đơn, `retries = 2` | PASS | PASS | PASS |
| Commit xong nhưng mất phản hồi (đơn và Payment) | Không gửi lại; một đơn, một dòng `history`, số dư cập nhật một lần | PASS | PASS | PASS |
| Sau commit mơ hồ, đọc đối chiếu lỗi 2 lần | Vẫn một đơn, kho trừ một lần | PASS | PASS | PASS |
| Sau commit mơ hồ, đọc đối chiếu không bao giờ thành công | Kết quả `unknown_commit` (không thử lại mù); DB có đúng một đơn; validator báo "thừa đơn chưa được xác nhận" (INV3) cho tới khi một lần đọc sau xác nhận được `request_id` | PASS | PASS | PASS |
| Đơn hết hàng rồi lỗi mất phản hồi | Kho và đơn không đổi; kết quả `out_of_stock` | PASS | PASS | PASS |
| Mongo (b): chết giữa trừ kho và ghi đơn | **Vi phạm INV2 là kết quả kỳ vọng** (giới hạn đã công bố của (b)): kho bị trừ, không có đơn, validator INVALID | không áp dụng | PASS (đúng như kỳ vọng) | không áp dụng |
| Giết worker ngẫu nhiên (xem bên dưới) | Ba luật VALID, đối soát của đề rỗng, số đơn/`history` trong DB = số yêu cầu đã xác nhận thành công | PASS | PASS | PASS |

Lệnh: `FLASHSALE_TEST_ENGINE=<mysql|mongo|tidb> pytest -m integration tests/test_fault_injection.py`. Kết quả: MySQL 6 PASS và MongoDB 7 PASS (Docker máy dev, nhãn **sơ bộ**); **TiDB 12 PASS** trên AWS (v8.5.7, 3 TiKV) cùng các test tích hợp khác (`results/official/fault-injection/tidb-integration-pytest.txt`).

## Giết tiến trình thật

`python scripts/fault_kill_cycles.py <mysql|mongo|tidb> --requests N --workers W --kill-every S --kills-per-round K --post-commit-delay-ms D [--idempotency-off] [--inventory I] --out results/official/fault-injection`

Mỗi worker chạy một lát yêu cầu (New-Order và Payment xen kẽ, 1–3 món); script giết ngẫu nhiên một số worker, khởi động worker thay thế thử lại cùng `request_id`, lặp cho tới khi mọi yêu cầu có kết quả cuối. Ack được ghi sau khi `run_request` trả về, nên yêu cầu đã commit mà chưa ack được nhận ra bằng đối chiếu idempotency.

**Đo trực tiếp việc cửa sổ nguy hiểm bị chạm:** khi worker mới nhận lại yêu cầu mà worker cũ đã bắt đầu, nó đọc DB TRƯỚC khi chạy lại: `rerun_found_committed` = đã commit trước khi chết (cửa sổ "commit xong, chưa ack"), `rerun_not_committed` = chết trước commit. `--post-commit-delay-ms` kéo dài nhân tạo cửa sổ sau commit (độ trễ ngay sau commit thành công, không đổi ngữ nghĩa giao dịch) để kill ngẫu nhiên rơi vào đó nhiều hơn.

**Tiêu chí đạt (chế độ thường):** ba luật VALID, `doc_reconciliation` rỗng, số đơn và `history` trong DB bằng đúng số yêu cầu đã ack thành công (không đơn ma, không đơn trùng), không yêu cầu nào kết thúc `unknown_commit`.

**Đối chứng âm (`--idempotency-off`):** cùng kịch bản trên dataset không UNIQUE và yêu cầu không idempotent; phải thấy đơn trùng và INVALID, nếu không thì kết quả PASS ở chế độ thường không có giá trị. Phải chạy với tồn đầu lớn (2.000): với tồn 30 phần lớn đơn kết thúc hết hàng nên gần như không có đơn commit để bị giết đúng lúc (lần thử đầu cho 0 đơn trùng vì lý do này).

Kết quả (`results/official/fault-injection/*.json`; TiDB trên AWS rf=3 sau nhóm R, MySQL/MongoDB trên Docker máy dev, **sơ bộ**):

| Hệ | Chế độ | Yêu cầu | Lần giết | Trúng cửa sổ "đã commit, chưa ack" | Chết trước commit | Đơn trong DB / đã ack | Payment trong DB / đã ack | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TiDB | thường, tồn 30 (có hết hàng) | 6.000 | 92 | 76 | 16 | 119 / 119 | 3.000 / 3.000 | VALID, PASS |
| TiDB | thường, tồn 2.000 | 6.000 | 128 | 95 | 33 | 3.000 / 3.000 | 3.000 / 3.000 | VALID, PASS |
| TiDB | đối chứng âm | 6.000 | 129 | 107 | 22 | 3.051 / 3.000 | 3.056 / 3.000 | **INVALID**: 51 đơn trùng, 56 payment trùng |
| MySQL | thường, tồn 30 | 1.500 | 28 | 20 | 8 | 112 / 112 | 750 / 750 | VALID, PASS |
| MySQL | đối chứng âm (tồn 2.000) | 1.500 | 32 | 27 | 4 | 762 / 750 | 765 / 750 | **INVALID**: 12 đơn trùng, 15 payment trùng |
| MongoDB (a) | thường, tồn 30 | 600 | 29 | 14 | 7 | 105 / 105 | 286 / 286 | VALID, PASS |
| MongoDB (a) | đối chứng âm (tồn 2.000) | 600 | 92 | 6 | 76 | 211 / 209 | 304 / 300 | **INVALID**: 2 đơn trùng, 4 payment trùng |

- **Cách đọc:** không vi phạm nào trong 76 và 95 lần trúng cửa sổ commit trên TiDB. Theo quy tắc ba, giới hạn trên của tỉ lệ vi phạm trong mô hình lỗi này là khoảng 3,9% và 3,2% (độ tin cậy 95%). Đây là bằng chứng thực nghiệm, không phải chứng minh: bảo đảm đến từ thiết kế (`request_id` UNIQUE và một giao dịch nguyên tử cho đơn và kho), thực nghiệm kiểm tra việc hiện thực đúng thiết kế đó.
- **Đối chứng âm cho thấy bộ kiểm tra phát hiện được lỗi:** cùng kịch bản, khi tắt idempotency xuất hiện đơn trùng và payment trùng ở cả ba hệ.
- Số lần trúng cửa sổ phụ thuộc hệ: trên MongoDB đối chứng âm chỉ 6 trong 82 yêu cầu bị gián đoạn trúng cửa sổ commit vì xung đột ghi làm nhiều giao dịch bị hủy trước commit (92 lần giết, 91 yêu cầu kết thúc `write_conflict`). Ở chế độ thường MongoDB có 15/600 yêu cầu kết thúc `write_conflict` sau 5 lần retry (nhiều worker cùng ghi bộ đếm mã đơn của hai district): thất bại rõ ràng, không commit, không phải lỗi tính đúng đắn.

## Giới hạn

- Chỉ lỗi phía ứng dụng/kết nối; chưa thử DBMS chết, failover hoặc chia cắt mạng.
- Số lần giết: TiDB 92–129 (AWS), MySQL/MongoDB chỉ 28–92 và trên Docker (sơ bộ). Là bằng chứng thực nghiệm, không phải chứng minh; mỗi lần giết chỉ có một số yêu cầu đang bay.
- Mô phỏng `after_commit` là lỗi do chèn ở tầng adapter, không phải mất gói thật.
- MySQL và MongoDB mới chạy trên Docker máy dev (chưa chạy trên AWS); TiDB chạy trên AWS ở rf=3 (cụm đã được nâng cho nhóm R).
- Độ trễ sau commit là nhân tạo (để tăng xác suất trúng cửa sổ), không phải phân phối thời gian thật của hệ.
- Thiết kế (b) của MongoDB vi phạm INV2 khi chết giữa chừng: không được tuyên bố đáp ứng ba luật trong mô hình lỗi này.
- Đối chứng "idempotency tắt" (lượt phụ `idempotency_off`, `test_idempotency_off_replay_creates_duplicate_order`) cho thấy khi không đối chiếu trước khi thử lại thì commit mơ hồ sinh đơn trùng.
