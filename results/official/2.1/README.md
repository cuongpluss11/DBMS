# Kết quả chính thức mục 2.1

Dữ liệu đo thật trên AWS EC2 `c6i.4xlarge` (Ubuntu 24.04, Docker 29.10.0), Git commit `38dda58`, ngày 2026-11-19. Phân tích và khác biệt so với đề: [docs/acceptance-2.1.md](../../../docs/acceptance-2.1.md).

- `INDEX.csv`: một dòng mỗi lượt (hệ, profile, lần lặp, client, kiểu kho, θ, TPS, p50/p95/p99, hủy, hết hàng, retry, VALID/INVALID, commit). Định nghĩa trường: [experiment-2.1.md](../../../docs/experiment-2.1.md).
- `<run_id>/`: `manifest.json` (phiên bản, tài nguyên, EXPLAIN, Region TiDB), `result.json`, `result.csv`. Không kèm `successful_new_orders.json` (khoảng 5 MB, dùng để đối soát, nằm trên VM).
- `progress-*.log`: thời điểm từng bước.

Các lượt `idempotency-off` cố ý tắt mã chống trùng; kết quả INVALID ở timeout 0,02 s là dự kiến, không xếp hạng. Mọi lượt `smoke` không nằm trong thư mục này. Cấu hình lượt idempotency-off ở timeout 0,2 s và 0,05 s dùng file cấu hình tạm có cùng nội dung `configs/idempotency-off.toml` trừ `client_timeout_seconds` (xem `manifest.json`, trường `config`).
