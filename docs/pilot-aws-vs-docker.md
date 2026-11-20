# Đo thử baseline MySQL: AWS nhiều VM so với Docker một VM

Ngày chạy: 2026-11-20. Đây là **phép đo thử một điểm**, không phải số đo chính thức của 2.1 (cấu hình 8 vCPU / 16 GiB khác ngân sách 12 vCPU / 24 GiB dự kiến cho AWS). Mục đích: xem hai môi trường cho số liệu khác nhau thế nào để quyết định đầu tư vào hạ tầng AWS.

## Cấu hình hai môi trường

| | Docker (một VM) | AWS (nhiều VM) |
| --- | --- | --- |
| DBMS | MySQL 8.4.8, container 8 CPU / 16 GiB | MySQL 8.4.8, container 8 CPU / 16 GiB (cpuset 0–7) trên VM `c6i.2xlarge` riêng |
| Máy tải | Chung VM `c6i.4xlarge` với DBMS | VM riêng `c6i.xlarge`, cùng AZ `us-east-1c`, qua mạng thật |
| Đĩa dữ liệu | gp3 100 GiB | gp3 100 GiB, 3000 IOPS, 125 MB/s |
| Cấu hình MySQL | mặc định (buffer pool 128 MiB, `flush_at_commit=1`, `sync_binlog=1`) | như vậy (đã xác nhận bằng `SELECT @@...`) |
| Profile | `baseline.toml`: 8 client, θ=0, uniform, tồn 10^9, 30 giây warmup + 60 giây đo, 3 lần lặp | như vậy |
| Mã | commit `38dda58` | commit `c2ad299` (chế độ remote, thêm `j:true` cho MongoDB không ảnh hưởng MySQL) |

Nguồn số Docker: `docs/acceptance-2.1.md` (51 lượt, trung vị 3 lần lặp). Nguồn số AWS: `results/official/pilot-aws-vs-docker/` (3 run, `SUMMARY.md`, `INDEX.csv`, `iostat-baseline.txt`).

## Kết quả (trung vị 3 lần lặp)

| | TPS (min–max) | p50 | p95 | p99 | Chờ khóa (cộng dồn) | Hủy | Hợp lệ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Docker | 261,3 (260,6–267,4) | 18,2 ms | 102 ms | 157 ms | ~6 giây | 0% | 3/3 |
| AWS | **247,1 (245,8–251,1)** | **22,3 ms** | 102,9 ms | 149,4 ms | 5,95–6,66 giây | 0% | 3/3 |

- TPS trên AWS thấp hơn khoảng 5,4%, và khoảng min–max của hai môi trường không chồng lên nhau. Chênh lệch nhỏ nhưng ổn định giữa các lần lặp.
- p50 cao hơn khoảng 4 ms trên AWS (có mạng thật giữa máy tải và DBMS, mỗi giao dịch cần nhiều vòng truy vấn). p95 và p99 gần như bằng nhau.
- Cả hai môi trường đều VALID, không hủy, không deadlock, thời gian chờ khóa giống nhau.

## Nút thắt: đĩa EBS (đã xác nhận bằng `iostat`)

Trên VM MySQL AWS, trong lúc đo (`iostat -x -d -t 1`, thiết bị dữ liệu `nvme1n1`, trung bình các giây có ghi đĩa): khoảng 2.281 lần ghi mỗi giây, 46 MB/s, độ trễ ghi 10,7 ms, hàng đợi trung bình 28, **%util 97%**. Ổ gp3 gần chạm mức 3000 IOPS. CPU MySQL chỉ ~40% của một lõi và máy tải ~72–76% của một lõi (khoảng 18% trên 4 vCPU), nên **máy tải không phải nút thắt**. Điều này xác nhận giả thuyết trước đây của `acceptance-2.1.md` (đĩa EBS là nút thắt) mà trước đó chỉ là suy luận.

Cụ thể hơn: với buffer pool mặc định 128 MiB (nhỏ hơn dữ liệu W=10), MySQL còn đọc khoảng 718 lần đọc mỗi giây (11 MB/s) cộng 2.281 lần ghi mỗi giây, tức **tổng khoảng 3.000 IOPS, đúng mức trần gp3**. Đọc đĩa là phần dư mà bộ đệm lớn hơn có thể loại bỏ.

## MySQL-chỉnh (buffer pool 3 GiB), cùng VM, cùng dataset

Khởi động lại MySQL với `FLASHSALE_MYSQL_BUFFER_POOL_BYTES=3221225472` (3 GiB = 3 TiKV × 1 GiB block cache), giữ nguyên độ bền (`flush_at_commit=1`, `sync_binlog=1`), reset dataset rồi chạy `configs/baseline-tuned.toml` 3 lần (runner kiểm nhãn khớp buffer pool). Kết quả ở `results/official/pilot-aws-vs-docker/tuned/`.

| | TPS (min–max) | p50 | p95 | p99 | iostat (khi đo) |
| --- | --- | --- | --- | --- | --- |
| AWS, MySQL-mặc-định (128 MiB) | 247,1 (245,8–251,1) | 22,3 ms | 102,9 ms | 149,4 ms | 718 r/s + 2.281 w/s, util 97%, w_await 10,7 ms |
| AWS, **MySQL-chỉnh (3 GiB)** | **394,7 (394,2–397,7)** | **14,7 ms** | 44,9 ms | 53,5 ms | 113 r/s + 2.609 w/s, util 71,5%, w_await 2,8 ms |

- MySQL-chỉnh nhanh hơn khoảng **60%** về TPS và p99 giảm hơn 2,5 lần, cả 3 lần lặp VALID, không hủy, không cảnh báo tài nguyên. Máy tải dùng khoảng 133–136% của một lõi (khoảng 34% trên 4 vCPU), không phải nút thắt.
- Nguyên nhân phù hợp với `iostat`: buffer pool lớn bỏ gần hết đọc đĩa, ổ không còn chạm trần 3000 IOPS (util 71,5%, độ trễ ghi từ 10,7 xuống 2,8 ms). Phần ghi (fsync mỗi commit) vẫn còn và là giới hạn kế tiếp.
- **Hệ quả cho báo cáo:** mốc MySQL-mặc-định thấp một phần vì bộ đệm nhỏ, không chỉ vì MySQL chậm. Đúng như bản chốt, so sánh giữa các hệ ở 2.2–2.5 nên dùng MySQL-chỉnh. Cả hai mốc (mặc định và chỉnh) đều phải báo cáo.
- Chỉ một điểm đo trên một VM; chưa so với Docker ở MySQL-chỉnh (chưa chạy lại trên Docker).

## Kiểm tra warmup

Trung bình TPS 10 giây cuối warmup so với 10 giây đầu đo: lệch −3,6%, −7,1%, −3,2% (cả ba trong ngưỡng 10%), nên 30 giây warmup có vẻ đủ cho riêng điểm này. Đây là bằng chứng ở một cấu hình MySQL; chưa kiểm cho TiDB và các θ khác.

## Kết luận và giới hạn

- Với MySQL một nút, **hai môi trường cho kết quả gần nhau** (khác biệt TPS ~5%, p99 tương đương), vì đĩa là nút thắt chung. Nghĩa là các số Docker hiện có vẫn đáng tin về thứ hạng và độ lớn cho MySQL và (nhiều khả năng) MongoDB một nút, nhưng khác nhau về độ trễ trung vị do mạng.
- Chưa đo TiDB, nơi sự khác biệt (3 TiKV dùng chung CPU, đĩa và loopback trong Docker) được kỳ vọng lớn hơn nhiều; điểm này chưa kiểm chứng.
- Chỉ một điểm đo, 3 lần lặp, một cấu hình đĩa. VM AWS ở đây (8 vCPU) khác ngân sách dự kiến cho đo chính thức (12 vCPU), và kết quả có thể thay đổi giữa các lần dựng VM. Không dùng bảng này để xếp hạng.
- Chế độ remote lần đầu chạy trên máy thật: lỗi cấu hình override `ports` và `cpus` đã được sửa trong lúc chạy (xem commit); không có lỗi ở lõi benchmark.
