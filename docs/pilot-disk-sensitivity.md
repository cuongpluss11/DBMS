# Thí nghiệm riêng: độ nhạy của đĩa EBS (MySQL-chỉnh, 3000 so với 10.000 IOPS)

Ngày chạy: 2026-11-20. **Thí nghiệm riêng, không so chéo giữa các hệ và không phải số đo chính thức của 2.1.** Dữ liệu thô: `results/official/pilot-disk-sensitivity/` (18 run, `INDEX.csv`, `SUMMARY.md`, `iostat-*.txt`).

## Thiết kế

- Một VM MySQL `c6i.2xlarge` (8 vCPU / 16 GiB, container cpuset 0–7) và một VM tải `c6i.xlarge` (4 vCPU), cùng AZ `us-east-1c`, MySQL 8.4.8 với **buffer pool 3 GiB** (MySQL-chỉnh), `flush_at_commit=1`, `sync_binlog=1`.
- **So cặp trên cùng VM và cùng dataset:** chạy hết các điểm ở 3000 IOPS / 125 MB/s, rồi nâng ổ gp3 tại chỗ lên **10.000 IOPS / 250 MB/s** bằng Terraform (`aws_ebs_volume` cập nhật tại chỗ, không thay ổ) và chạy lại đúng các điểm đó. Cách này loại sai khác giữa hai lần dựng VM.
- Điểm đo (`configs/performance.toml`, kho uniform, tồn 10^9): 8 client θ=0; 64 client θ=0; 64 client θ=0,9. Mỗi điểm 3 lần, 30 giây warmup + 60 giây đo, reset dataset giữa các lần. Script: `scripts/run-disk-sensitivity.sh`. Nhãn nhóm: `run_note` trong manifest.
- Cả 18 lượt VALID, không hủy, không deadlock phía client.

## Kết quả (trung vị 3 lần lặp)

| Điểm | IOPS ổ | TPS (3 lần) | p50 | p95 | p99 | Chờ khóa (cộng dồn) | CPU MySQL | CPU máy tải |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 client, θ=0 | 3000 | 399–402 | 14,7 ms | 44 ms | 52 ms | 7,8 giây | 66% | 133% |
| 8 client, θ=0 | 10.000 | 404–406 | 13,5 ms | 42 ms | 49 ms | 7,0 giây | 68% | 133% |
| 64 client, θ=0 | 3000 | 1.035 / 1.035 / 1.130 | 33,3 ms | 222 ms | 357 ms | 476 giây | 175% | 192% |
| 64 client, θ=0 | 10.000 | 2.134–2.160 | 20,1 ms | 74 ms | 106 ms | 596 giây | 361% | **393%** |
| 64 client, θ=0,9 | 3000 | 1.104–1.120 | 30,1 ms | 214 ms | 360 ms | 611 giây | 185% | 203% |
| 64 client, θ=0,9 | 10.000 | 2.130–2.159 | 19,8 ms | 76 ms | 111 ms | 692 giây | 357% | **394%** |

(CPU tính theo 100% = một lõi; máy tải có 4 vCPU = 400%.)

## Phát hiện

1. **Đĩa quyết định TPS khi có nhiều client đồng thời.** Ở 8 client, nâng IOPS chỉ tăng ~1% TPS (399,6 → 404,8). Ở 64 client TPS tăng khoảng **2,1 lần** (1.035 → 2.158) và p99 giảm từ 357 xuống 106 ms. Với 3000 IOPS, kết quả ở ≥64 client chủ yếu đo giới hạn ổ đĩa, không phải khả năng của MySQL. Đúng như bản chốt dự liệu, các số này phải báo cáo kèm p99 và thời gian chờ khóa, không chỉ TPS.
2. **Máy tải Python trở thành nút thắt ở 10.000 IOPS.** CPU máy tải đạt 393–394% trên 400% khả dụng; runner phát cảnh báo `loadgen_cpu_98pct_of_limit` / `loadgen_cpu_99pct_of_limit`, trong khi MySQL chỉ dùng ~45% CPU của VM (361% trên 800%). Vì vậy **TPS ở 10.000 IOPS (≈2.150) là cận dưới của khả năng MySQL**, không phải trần thật. Hệ quả cho đo chính thức ở 64–256 client: máy tải `c6i.xlarge` không đủ; cần VM tải lớn hơn hoặc nhiều VM tải, và phải kiểm `loadgen_cpu_pct` ở mọi điểm.
3. **θ=0,9 hầu như không làm giảm TPS ở 64 client trên kho uniform** (2.147 so với 2.158 ở 10.000 IOPS; 1.112 so với 1.035 ở 3000, nằm trong khoảng dao động). Thời gian chờ khóa cộng dồn tăng 16–28%, nhưng không đủ để làm tụt TPS vì nút thắt nằm ở đĩa hoặc máy tải. Phần điểm gãy theo θ là việc của 2.2 và cần kiểu "một kho"; kết quả này chỉ cho biết ở kho uniform thì chưa thấy.
4. **Độ trễ mạng giữa máy tải và DBMS rất nhỏ:** RTT TCP trung vị ~0,14–0,15 ms (min ~0,11 ms; có vài đỉnh ~1,1 ms). Với vài chục câu truy vấn mỗi giao dịch, mạng đóng góp khoảng vài mili giây vào p50 (phù hợp với chênh ~4 ms so với Docker ở lượt thử trước, nhưng đó là suy luận chưa kiểm chứng).

## Giới hạn và điều không kết luận được

- `iostat` được ghi liên tục cả pha (gồm reset dataset và đối soát, không chỉ 60 giây đo), nên số liệu trung bình ghi ở `iostat-*.txt` (A: ~2.900 ghi/s, util 87%, w_await 9,6 ms; B: ~4.500 ghi/s, w_await 1,1 ms) lẫn I/O của reset và không so được trực tiếp với trần EBS (EBS tính IOPS theo đơn vị 16 KiB, iostat tính sau khi gộp). Chỉ dùng để thấy xu hướng: độ trễ ghi giảm hơn 8 lần ở 10.000 IOPS.
- Một VM, một ngày, một cấu hình MySQL. Chưa lặp lại giữa các lần dựng VM; chưa có MongoDB/TiDB. Không dùng bảng này để xếp hạng hay so chéo.
- Chưa đo trực tiếp xem 8 client ở 3000 IOPS có bị fsync giới hạn hay không; kết quả chỉ ngụ ý nút thắt ở 8 client không nằm ở IOPS.

## Quyết định rút ra

- **Giữ 3000 IOPS cho mọi hệ ở các lượt chính** (xem `docs/pilot-aws-vs-docker.md`, vì c6i.large của TiKV chỉ duy trì 3.600 IOPS), và coi kết quả ≥64 client là bị đĩa giới hạn.
- **Nâng cỡ máy tải cho đo chính thức ở 64–256 client** (`loadgen_instance_type`, ví dụ `c6i.4xlarge`; chưa kiểm chứng mức nào đủ) và dùng cảnh báo `loadgen_cpu_*` để kiểm. Việc này cũng làm tăng nhu cầu quota vCPU.
- Đã sửa Terraform: `lifecycle { ignore_changes = [ami, user_data] }` cho VM, vì `most_recent` của AMI Ubuntu đã đổi giữa hai lần plan và sẽ làm Terraform **thay thế** VM đang đo khi chỉ định nâng IOPS.
