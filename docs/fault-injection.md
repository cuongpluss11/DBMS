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
| Chết/hủy trước commit, sau đó thử lại | Không dấu vết (không đơn, không trừ kho, mã đơn không nhích); thử lại tạo đúng một đơn; thử lần hai không tạo đơn thứ hai | PASS | PASS | NOT TESTED |
| Mất kết nối trước commit hai lần rồi thành công | Một đơn, `retries = 2` | PASS | PASS | NOT TESTED |
| Commit xong nhưng mất phản hồi (đơn và Payment) | Không gửi lại; một đơn, một dòng `history`, số dư cập nhật một lần | PASS | PASS | NOT TESTED |
| Sau commit mơ hồ, đọc đối chiếu lỗi 2 lần | Vẫn một đơn, kho trừ một lần | PASS | PASS | NOT TESTED |
| Sau commit mơ hồ, đọc đối chiếu không bao giờ thành công | Kết quả `unknown_commit` (không thử lại mù); DB có đúng một đơn; validator báo "thừa đơn chưa được xác nhận" (INV3) cho tới khi một lần đọc sau xác nhận được `request_id` | PASS | PASS | NOT TESTED |
| Đơn hết hàng rồi lỗi mất phản hồi | Kho và đơn không đổi; kết quả `out_of_stock` | PASS | PASS | NOT TESTED |
| Mongo (b): chết giữa trừ kho và ghi đơn | **Vi phạm INV2 là kết quả kỳ vọng** (giới hạn đã công bố của (b)): kho bị trừ, không có đơn, validator INVALID | không áp dụng | PASS (đúng như kỳ vọng) | không áp dụng |
| Giết worker ngẫu nhiên (xem bên dưới) | Ba luật VALID, đối soát của đề rỗng, số đơn/`history` trong DB = số yêu cầu đã xác nhận thành công | PASS | PASS | NOT TESTED |

Lệnh: `FLASHSALE_TEST_ENGINE=<mysql|mongo|tidb> pytest -m integration tests/test_fault_injection.py`. Đã chạy trên Docker cục bộ (nhãn **sơ bộ**): MySQL 6 test PASS, MongoDB 7 test PASS (có test (b)).

## Giết tiến trình thật

`python scripts/fault_kill_cycles.py <mysql|mongo|tidb> --requests N --workers W --kill-every S --out results/official/fault-injection`

Mỗi worker chạy một lát yêu cầu (New-Order và Payment xen kẽ, 1–3 món); script giết ngẫu nhiên một worker, khởi động worker thay thế thử lại cùng `request_id`, lặp cho tới khi mọi yêu cầu có kết quả cuối. Ack được ghi sau khi `run_request` trả về, nên yêu cầu đã commit mà chưa ack sẽ được nhận ra bằng đối chiếu idempotency. Tồn đầu nhỏ (30) để có hết hàng thật. Tiêu chí đạt: ba luật VALID, `doc_reconciliation` rỗng, số đơn và `history` trong DB bằng đúng số yêu cầu đã ack thành công (không đơn ma, không đơn trùng), không yêu cầu nào kết thúc `unknown_commit`.

Kết quả (Docker cục bộ, sơ bộ; `results/official/fault-injection/*.json`):

| Hệ | Yêu cầu | Lần giết | Yêu cầu bị thử lại sau giết | Đơn trong DB / đã ack | Payment trong DB / đã ack | Hết hàng | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MySQL | 2.000 | 7 | 7 | 119 / 119 | 1.000 / 1.000 | 881 | VALID, PASS |
| MongoDB (a) | 300 | 6 | 6 | 63 / 63 | 150 / 150 | 10 | VALID, PASS |
| TiDB | — | — | — | — | — | — | NOT TESTED (Docker máy dev không đủ RAM; chạy trên stack `tidb3`) |

Lưu ý: ở MongoDB 77/300 yêu cầu kết thúc `write_conflict` sau 5 lần retry (bốn worker cùng ghi bộ đếm mã đơn của hai district); đây là thất bại rõ ràng, không commit (số đơn trong DB khớp số ack), không phải lỗi tính đúng đắn.

## Giới hạn

- Chỉ lỗi phía ứng dụng/kết nối; chưa thử DBMS chết, failover hoặc chia cắt mạng.
- Số lần giết nhỏ (6–7): là bằng chứng hỗ trợ, không phải chứng minh. Mỗi lần giết chỉ có một số yêu cầu đang bay.
- Mô phỏng `after_commit` là lỗi do chèn ở tầng adapter, không phải mất gói thật.
- TiDB chưa thử; kết quả trên là Docker máy dev.
- Thiết kế (b) của MongoDB vi phạm INV2 khi chết giữa chừng: không được tuyên bố đáp ứng ba luật trong mô hình lỗi này.
- Đối chứng "idempotency tắt" (lượt phụ `idempotency_off`, `test_idempotency_off_replay_creates_duplicate_order`) cho thấy khi không đối chiếu trước khi thử lại thì commit mơ hồ sinh đơn trùng.
