# Kết quả chính thức mục 2.1

Dữ liệu đo thật trên AWS EC2 `c6i.4xlarge` (Ubuntu 24.04, Docker 29.10.0), 51 lượt. Ngày 2026-11-19: Git commit `38dda58`. Ngày 2026-11-20 (các profile `performance-theta*`, `performance-hot-item`, `baseline-concurrency`, và idempotency-off trên MongoDB/TiDB): commit `3a5aded`, đã có phép kiểm chéo của tài liệu. Phân tích và khác biệt so với đề: [docs/acceptance-2.1.md](../../../docs/acceptance-2.1.md).

- `INDEX.csv`: một dòng mỗi lượt (hệ, profile, lần lặp, client, kiểu kho, θ, TPS, p50/p95/p99, hủy, hết hàng, retry, VALID/INVALID, commit). Định nghĩa trường: [experiment-2.1.md](../../../docs/experiment-2.1.md).
- `<run_id>/`: `manifest.json` (phiên bản, tài nguyên, EXPLAIN, Region TiDB), `result.json`, `result.csv`. Không kèm `successful_new_orders.json` (khoảng 5 MB, dùng để đối soát, nằm trên VM).
- `progress-*.log`: thời điểm từng bước.
- `vmstat-concurrency-N.txt`: CPU và đĩa của toàn VM trong lượt đo N client (cột `us`, `sy`, `wa`, `bo`).
- `validate-cli-output.json`: kết quả lệnh `flashsale validate`.

Ghi chú về các profile:
- `baseline-concurrency` là `configs/baseline.toml` với `--concurrency N` (8, 32, 64, 128, 256) và `max_connections=400`; xem cột `concurrency`.
- `performance-theta*` và `performance-hot-item` là `configs/performance.toml` với θ tương ứng hoặc chế độ một món, 8 client, 1 lần lặp (kiểm tra runner, không phải điểm đo chính thức).
- Các lượt `idempotency-off` cố ý tắt mã chống trùng; INVALID là dự kiến, không xếp hạng. Ở MySQL, các lượt timeout 0,2 s và 0,05 s dùng file cấu hình tạm giống `configs/idempotency-off.toml` trừ `client_timeout_seconds` (xem `manifest.json`, trường `config`).
- Mọi lượt `smoke` không nằm trong thư mục này.
