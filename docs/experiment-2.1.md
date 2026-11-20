# Giao thức mục 2.1

## Chạy và tái hiện

Lệnh được ghi ở [README](../README.md). Mỗi điểm dùng seed cố định và 3 lần lặp. Seed con được dẫn xuất từ lần lặp, client và pha. Mỗi client luân phiên New-Order và Payment, với loại đầu do seed chọn. Ở một cửa sổ hữu hạn, mỗi client có thể lệch tối đa một yêu cầu đã sinh; retry và thời gian hoàn thành có thể làm tỉ lệ giao dịch thành công khác 1:1.

Runner chia client thành nhiều process, mỗi process dùng các luồng I/O. Cửa sổ dùng đồng hồ monotonic, kèm barrier trước khi bắt đầu và sau khi drain. Một client có một kết nối SQL hoặc một adapter MongoDB và session riêng cho từng transaction. Để so sánh trên ba VM, dùng cùng Git commit, cấu hình VM, ngân sách container và tham số workload. Ghi chênh lệch CPU hoặc ổ đĩa host nếu có. Năng lực của load generator ở 256 client cần kiểm chứng trên các VM đo. [Quy trình cho nhóm](trien-khai-2.1.md)

Mỗi request có tối đa sáu lần thực thi, gồm lần đầu và tối đa năm retry. Khoảng chờ mặc định là 10, 20, 40, 80 và 160 ms. Khi bật jitter, nhân khoảng chờ với hệ số từ 0,5 đến 1,5 sinh từ seed riêng của client. Khi chưa rõ commit, runner tra request ID đã lưu trước khi gửi lại. Trạng thái commit chưa phân giải làm lượt chạy INVALID.

Preflight ghi EXPLAIN. MySQL có thể rút gọn tra cứu UNIQUE vắng mặt trong khi tối ưu hóa. Khi đó manifest lưu thêm EXPLAIN range trên cùng cột. TiDB ghi Region, phiên bản store, max-replicas và DDL history. DBMS được pin bằng cả tag và manifest Linux amd64. [MySQL Docker Official Image](https://hub.docker.com/_/mysql), [MongoDB Docker Official Image](https://hub.docker.com/_/mongo), [TiDB v8.5.7](https://docs.pingcap.com/tidb/stable/release-8.5.7/).

## Đầu ra

Mỗi lần lặp có thư mục `results/<run_id>/`. Manifest ghi cấu hình đã áp dụng, thời điểm UTC, seed, số dòng lúc nạp, dấu vân tay dataset, phiên bản DBMS/Python/Docker/Compose, tài nguyên host và Docker, giới hạn từng container, image/digest, Git commit nếu thư mục là gốc Git của dự án, hash tệp mã nguồn và EXPLAIN. `successful_new_orders.json` ghi request ID thành công của cả hai pha và drain.

| Trường hoặc nhóm | Định nghĩa |
| --- | --- |
| `seconds`, `tps`, `success`, `failed` | Thời lượng cấu hình và số request kết thúc trước deadline của pha. TPS bằng số request thành công chia thời lượng tính bằng giây. |
| `new_order_success`, `payment_success` | Số request thành công theo loại giao dịch. |
| `p50_ms`, `p95_ms`, `p99_ms` | Nearest-rank trên độ trễ request thành công, gồm thời gian thử lại, backoff và kiểm khóa idempotency. |
| `drained_requests` | Số request bắt đầu trong cửa sổ nhưng hoàn tất sau deadline. Được đối soát và báo riêng. |
| `abort_pct`, `out_of_stock_pct`, `retry_pct`, `retry_attempts` | `abort_pct`: phần trăm request kết thúc lỗi hệ thống (deadlock, timeout, write conflict, ...), **không** gồm hết hàng. `out_of_stock_pct`: phần trăm request kết thúc vì hết hàng (kết quả nghiệp vụ, vẫn nằm trong `failed`). `retry_pct`: phần trăm request thử lại ít nhất một lần. `retry_attempts`: tổng lượt thử lại trong pha. (Schema v2: trước đây hết hàng bị tính vào `abort_pct`.) |
| `error_counts`, `failure_counts`, `request_error_pct` | Sự kiện lỗi kể cả khi recover, kết quả lỗi cuối và phần trăm request gặp ít nhất một lỗi timeout/deadlock/write conflict tương ứng. |
| `rank_draws`, `observed_rank1_pct`, `observed_top100_pct` | Lượt rút rank của New-Order đã kết thúc trong cửa sổ, gồm request hết hàng. `rank1_pct` và `top100_pct` là xác suất lý thuyết. |
| `out_of_stock_all`, `unknown_commits_all` | Tổng kết quả hết hàng và commit chưa xác định của từng pha, gồm drain. |
| `tps_series` (chỉ `result.json`), `tps_per_second.csv` | Số request thành công mỗi giây của warmup và measurement (giây 0 = đầu phase), dùng kiểm tra 30 giây warmup có đủ không. `null` nếu runner lỗi. |
| `warmup_stability` (chỉ `result.json`) | `warmup_tail_tps` (10 giây cuối warmup), `measurement_head_tps` (10 giây đầu đo), `drift_pct`. Lệch lớn → kéo dài warmup cho mọi hệ rồi đo lại. |
| `dbms.sync_binlog`, `dbms.flush_at_commit`, `dbms.buffer_pool_bytes` (manifest MySQL) | Độ bền và buffer pool thực tế; `baseline` = 128 MiB, `baseline-tuned` > 128 MiB. |
| `dbms.transaction_write_journal`, `dbms.wiredtiger_cache_bytes` (manifest MongoDB) | writeConcern giao dịch `majority` + `j: true`; kích thước cache WiredTiger đã cấu hình (`null` nếu không đọc được). |
| `dbms.tikv_durability_config` (manifest TiDB) | `SHOW CONFIG` cho `storage.block-cache.capacity` và `raftstore.sync-log`; `null` nếu phiên bản không trả. |
| `lock_wait_ms`, `server_deadlocks` | Delta server counter MySQL từ sau khi drain warmup đến sau khi drain measurement: `Innodb_row_lock_time` và `information_schema.INNODB_METRICS.lock_deadlocks` (trả `null` nếu metric chưa bật). MongoDB và TiDB trả `null` cho hai trường này. Số deadlock phía client nằm ở `error_counts.deadlock`. |
| `idempotency`, `client_timeout_seconds` | Cờ idempotency (false chỉ ở profile `idempotency_off`) và timeout socket của client dùng trong lượt. Schema v3 thêm hai cột này; `null` ở timeout nghĩa là kết quả cũ không ghi. |
| `resource_warnings` | Danh sách cảnh báo khi `tidb` hoặc `pd` dùng quá 80% giới hạn CPU trong cửa sổ đo (ví dụ `tidb_cpu_93pct_of_limit`). Chỉ là cảnh báo, không đổi VALID/INVALID; lượt có cảnh báo cần xem xét có phải nghẽn tầng SQL trước khi dùng so sánh TiKV. |
| `container_cpu_pct` | Trung bình các mẫu Docker Stats hoàn tất trong cửa sổ đo, theo từng service. 100% tương ứng một CPU logic. Service thiếu mẫu có giá trị `null`. |
| `validation` | Trạng thái, ba kết quả luật, bằng chứng từng sai lệch và các lỗi giao thức. CSV có một hàng cho mỗi pha, ghi cờ VALID/INVALID, ba kết quả và số lỗi theo luật. JSON giữ bằng chứng chi tiết. |

Số liệu thiếu biểu diễn bằng `null` cả trong JSON và CSV. Giá trị 0 thể hiện phép đếm đã quan sát. Chỉ lấy các run `VALID` cùng profile, phiên bản và tài nguyên để so sánh. Smoke dùng quy mô nhỏ và gắn nhãn `smoke`.

Sau khi cài theo README, chạy CLI từ checkout dự án. Manifest có Git commit khi checkout này là gốc Git. Với thư mục chưa có commit riêng, trường đó là `null` và các hash mã nguồn vẫn xác định nội dung đã chạy.

## Trạng thái kiểm chứng

Kiểm chứng cục bộ ngày 18/11/2026 dùng Windows x86_64, Python 3.13.0, Docker Desktop với Engine Linux amd64 29.8.0 và Compose 5.5.1.

| Kiểm tra | Kết quả |
| --- | --- |
| `python -m pytest -m 'not integration' -q` | 10 PASS. Kiểm cú pháp Bash, ba tệp Compose, build wheel và kiểm tra skill cũng PASS. |
| MySQL 8.4.8 | 3 integration PASS, gồm smoke VALID `b1510ecbc43d493f98be4da8827ac933`. |
| MongoDB 8.0.20 | 2 integration PASS, gồm smoke VALID `30d71380e92249868754022133719c4f`. Bài đối chứng mất request ID được thêm sau lượt MongoDB này và còn NOT TESTED trên MongoDB. |
| TiDB, PD và ba TiKV v8.5.7 | 3 integration PASS, gồm smoke VALID `75144903d85643538c30970f550e8402`. PD báo ba TiKV Up và replica count 1. Smoke quan sát 18 Region history và 1 Region stock, với các leader trên cùng một store tại thời điểm lấy mẫu. |
| MySQL baseline W=10, 8 client, θ=0, uniform | Nạp và đếm đủ 9 bảng gồm 1.000.000 dòng stock, 300.000 đơn cơ sở, 90.000 new_order và 2.998.678 order_line. Ba lần lặp 30 giây warmup + 60 giây đo đều VALID. Run ID lần lượt là `e4fad7967b064bdeb8d19966f2e76b1d`, `cd61db467f0d44f0b63fd13a791fd613`, `a33052cddf24406f9693aaee0a6836a6`. |

Đầu ra thực đo ở `results/<run_id>/` trong checkout đã chạy. Các lượt trên xác nhận đường chạy cục bộ. Nghiệm thu trên VM Ubuntu 24.04/Python 3.12, điểm baseline single-warehouse và mức 256 client còn NOT TESTED. Dùng quy trình trong README để tự chạy trên máy đo.
