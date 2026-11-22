# Flash-sale DBMS Benchmark

Bài tập lớn DBMS: chẩn đoán và giảm nghẽn do tranh chấp khóa, 2PC và đổi lược đồ khi đang chạy trên MySQL InnoDB, MongoDB và TiDB, với tải Flash-sale dựa trên TPC-C. Dự án nạp cùng dữ liệu TPC-C, chạy New-Order và Payment trên ba hệ, rồi xuất bằng chứng để tái hiện phép đo và đối soát tồn kho.

## Trạng thái và điểm vào (cập nhật 2026-11-21)

- **Mục 2.1 đã nghiệm thu trên AWS** (3 hệ, 152 lượt đo): [acceptance-2.1.md](docs/acceptance-2.1.md), kết quả ở `results/official/2.1-aws/`.
- **Đang làm 2.2, 2.3 và 2.4** theo [docs/scope-2-weeks.md](docs/scope-2-weeks.md): phạm vi theo tầng, cổng kiểm, lịch 14 ngày, phân công và bảng trạng thái.
- Quy tắc cho người và AI viết code: [AGENTS.md](AGENTS.md). Khác biệt so với tài liệu ý tưởng: [docs/assumptions.md](docs/assumptions.md).
- Tài liệu ý tưởng bản chốt (`bao_cao_DBMS_ban_chot.docx`) **không nằm trong repo**; nhóm trưởng chia sẻ riêng.

| Phụ trách | Phạm vi | Đọc trước |
| --- | --- | --- |
| Lực | 2.2, 2.3, vận hành AWS | `docs/scope-2-weeks.md`, `docs/acceptance-2.1.md`, `infra/aws/README.md` |
| Cường | 2.4 | `docs/scope-2-weeks.md` (mục "Ghi chú thiết kế 2.4"), mục 2.4 trong tài liệu ý tưởng |
| Duy Anh | Hỗ trợ 2.2 và 2.3, báo cáo | `docs/scope-2-weeks.md`, `docs/citation-check.md`, `docs/acceptance-2.1.md` |

Số đo chính thức lấy trên AWS nhiều VM ([infra/aws/README.md](infra/aws/README.md)); Docker một VM chỉ để phát triển và thử. Chỉ `terraform apply` và `destroy` do Lực thực hiện. Hướng dẫn triển khai Docker ba VM của giai đoạn 2.1 còn lưu ở [docs/trien-khai-2.1.md](docs/trien-khai-2.1.md) (đã hoàn thành, chỉ để tham khảo); giao thức thực nghiệm 2.1 ở [docs/experiment-2.1.md](docs/experiment-2.1.md).

## Cài đặt trên Ubuntu 24.04 LTS

Dùng VM x86_64 với ít nhất 12 vCPU, 20 GiB RAM cấp cho VM (ví dụ AWS `c6i.4xlarge`: 16 vCPU, 32 GiB) và 10 GiB đĩa trống. Chừa thêm dung lượng cho các volume W=10 và tài nguyên cho load generator.

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv git
```

Nếu VM chưa có Docker Engine và plugin Compose, chạy bước quản trị dưới đây rồi đăng nhập lại để quyền nhóm Docker có hiệu lực. [Hướng dẫn cài Docker chính thức](https://docs.docker.com/engine/install/ubuntu/)

```bash
sudo bash scripts/bootstrap-docker.sh --install
sudo usermod -aG docker "$USER"
```

Từ gốc checkout, tạo môi trường Python, chạy unit test và kiểm tra Docker. Có thể sao chép `.env.example` thành `.env` để đổi cổng loopback khi cần.

```bash
bash scripts/setup.sh
source .venv/bin/activate
flashsale doctor
```

## Kiểm tra nhanh một DBMS

Ví dụ dưới dùng MySQL. Trên VM của TV2 dùng `mongo`, còn trên VM của TV3 dùng `tidb`.

```bash
flashsale start mysql
flashsale status mysql
FLASHSALE_TEST_ENGINE=mysql python -m pytest -m integration -q
flashsale smoke mysql
flashsale stop mysql
```

Smoke tạo dataset nhỏ, kiểm tra tình huống hết hàng và dọn database tạm. Có thể dùng `flashsale smoke mysql --start` để CLI tự khởi động hệ đang dừng và dừng lại sau smoke. `bash scripts/setup.sh --smoke-all` cài môi trường, tải image đã pin và smoke tuần tự cả ba hệ.

## Tự chạy baseline MySQL W=10

Baseline mặc định có 8 client, θ=0, chọn kho uniform, 3 lần lặp, mỗi lần 30 giây warmup và 60 giây measurement. Chạy từng lệnh và kiểm tra kết quả trước khi sang bước tiếp theo.

```bash
flashsale start mysql
flashsale status mysql

DATASET=$(flashsale load mysql --config configs/baseline.toml |
    python -c 'import json,sys; print(json.load(sys.stdin)["database"])')
flashsale run mysql --config configs/baseline.toml --dataset "$DATASET" --reset-between
```

Lưu `run_id` của lần lặp cuối nếu muốn chạy lại đối soát khi database còn giữ nguyên trạng thái của lượt đó. Thay `RUN_UUID_HEX` bằng giá trị thực rồi dừng MySQL.

```bash
flashsale validate mysql --run-id RUN_UUID_HEX
flashsale stop mysql
```

Mỗi lần lặp có `manifest.json`, `result.json` và `result.csv` trong `results/<run_id>/`. Chỉ đưa các lượt `VALID` có cấu hình so sánh tương đương vào bảng hiệu năng. `results/examples/` chứa ví dụ định dạng.

**MySQL-chỉnh (`configs/baseline-tuned.toml`)**: đề yêu cầu thêm một mốc MySQL có buffer pool tương đương cache của TiKV/MongoDB (3 GiB = 3 TiKV x 1 GiB) để so công bằng. Đặt biến rồi khởi động lại MySQL (dữ liệu giữ nguyên trong volume; cần `load` lại nếu muốn dataset mới):

```bash
flashsale stop mysql
FLASHSALE_MYSQL_BUFFER_POOL_BYTES=3221225472 flashsale start mysql
flashsale run mysql --config configs/baseline-tuned.toml --dataset "$DATASET" --reset-between
```

Runner từ chối chạy nếu nhãn không khớp buffer pool thực (`baseline` bắt buộc 128 MiB, `baseline-tuned` bắt buộc lớn hơn). Mọi lần chạy MySQL ghi `buffer_pool_bytes`, `flush_at_commit`, `sync_binlog` vào manifest. MongoDB ghi `j: true` trong writeConcern giao dịch và `wiredtiger_cache_bytes` (đặt bằng `FLASHSALE_MONGO_CACHE_GB`, mặc định 3).

**Chạy cả ma trận 2.1 cho một hệ và tổng hợp:**

```bash
scripts/run-matrix-2.1.sh mysql --dry-run          # in danh sách điểm, không chạy
scripts/run-matrix-2.1.sh mysql                    # lưới evidence; --grid full cho toàn bộ θ × client
flashsale report --results-dir results --out results/report   # INDEX.csv, SUMMARY.md, kiểm warmup
```

`run`/`benchmark` có thêm `--theta` và `--hot-item`. Đặt `FLASHSALE_IOSTAT_SSH=ubuntu@<IP VM DBMS>` để ghi `iostat` mỗi điểm đo. Script dừng ngay khi một điểm lỗi hoặc INVALID (trừ `idempotency-off`, vốn dự kiến INVALID).

**Vẽ TPS theo giây để kiểm warmup** (không cần thư viện ngoài, ra file SVG):

```bash
python scripts/plot_tps_per_second.py --results-dir results/official/2.1-aws
```

**Kiểm warmup 30 giây**: mỗi lượt xuất `tps_per_second.csv` và `warmup_stability` trong `result.json` (TPS 10 giây cuối warmup so với 10 giây đầu đo; `drift_pct` lớn nghĩa là cần kéo dài warmup cho mọi hệ).

Các điểm đo phụ theo đề dùng cùng cách chạy, chỉ đổi `--config`: `configs/baseline-single-warehouse.toml` (θ=0, một kho), `configs/baseline-1client.toml` (1 client), `configs/payment-ytd.toml` (Payment bật `w_ytd`/`d_ytd`) và `configs/idempotency-off.toml` (tắt mã chống trùng, lược đồ và dataset riêng; INVALID luật 3 là kết quả dự kiến, không xếp hạng). Ba profile baseline dùng chung một dataset, chỉ cần `load` một lần.

## Lệnh vận hành

| Lệnh | Khi dùng |
| --- | --- |
| `flashsale doctor`, `flashsale status ENGINE` | Kiểm tra môi trường chung và trạng thái một hệ. |
| `flashsale start ENGINE`, `flashsale stop ENGINE` | Khởi động hoặc dừng container dự án. Dừng giữ volume và dữ liệu. |
| `flashsale load ENGINE --config PROFILE` | Tạo dataset UUID và in tên database, fingerprint và số dòng. |
| `flashsale reset ENGINE --config PROFILE --dataset NAME --confirm NAME` | Khôi phục dataset đã dùng. Tên xác nhận phải khớp tên dataset. |
| `flashsale run ENGINE --config PROFILE --dataset NAME --reset-between` | Chạy một điểm đo nhiều lần lặp. Có thể dùng `benchmark` thay `run`. |
| `flashsale validate ENGINE --run-id ID` | Chạy lại ba luật trên dataset của run khi dữ liệu còn ở trạng thái tương ứng. |
| `flashsale drop ENGINE --dataset NAME --confirm NAME` | Xóa đúng dataset đã đăng ký khi nhóm xác nhận cần xóa. |

**[Nghiệm thu mục 2.1](docs/acceptance-2.1.md)** có kết quả đo thật, khác biệt so với đề và danh sách NOT TESTED; dữ liệu chính thức ở [results/official/2.1/](results/official/2.1/INDEX.csv). [Hướng dẫn cho nhóm](docs/trien-khai-2.1.md) có lệnh baseline một kho, lượt kiểm luật, lượt so sánh ba hệ và cách bàn giao kết quả. Xem thêm [ánh xạ yêu cầu](docs/requirements-2.1.md), [các quyết định thực nghiệm](docs/assumptions.md) và [định nghĩa trường kết quả](docs/experiment-2.1.md). Mục 2.2 đang làm: biến thể trừ kho P0/P1/P2 và lệnh chạy ở [docs/experiment-2.2.md](docs/experiment-2.2.md) (mã và test đơn vị, chưa có số đo). Mục 2.3 (TiDB): nhóm A–E.a, đặt Region/leader, hệ số tăng tốc ở [docs/experiment-2.3.md](docs/experiment-2.3.md) (mã và test đơn vị, chưa có số đo).

## Mục 2.4 – Online Schema Evolution trên MySQL (Eager P1, Batch P2, Lazy P3)

Thực nghiệm đổi lược đồ khi đang bán hàng (thêm `ol_discount` và `ol_mig_state` vào ~3 triệu dòng `order_line` ở `W=10`, tải nền Flash-sale `64 client`, `θ=0,5` kèm giao dịch đọc `"Xem đơn cũ"` chiếm tỉ lệ `q`). Cách chạy:

```bash
bash scripts/run-2.4-eager.sh mysql                          # P1 – Eager (q=25%)
bash scripts/run-2.4-batch.sh mysql                          # P2 – Batch nền (lô 1.000 và 5.000 dòng, q=25%)
Q_LIST="5 25 50" bash scripts/run-2.4-lazy.sh mysql          # P3 – Lazy (quét q = 5%, 25%, 50%)
```

### Tổng quan kết quả thực nghiệm trên MySQL 8.4.8 (18/18 lượt VALID, 1 VM Docker `c6i.4xlarge`, MySQL-chỉnh 3 GiB buffer pool)

**1. So sánh 3 chiến lược chuyển dữ liệu ở cùng tải nền (`q = 25%`, thí nghiệm E2):**

| Chiến lược | TPS trung vị *(min–max)* | Giảm TPS so với nền *(~1.636 TPS)* | p99 toàn pha *(ms)* | Đỉnh p99 theo giây *(ms)* | Chờ khóa `lock_wait_ms` | `read_clean` / `read_migrated` p99 *(ms)* | Hoàn tất migration *(s)* |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **P1 – Eager** ([2.4-eager](results/official/2.4-eager/SUMMARY.md)) | **704,9** *(684,2–773,2)* | **-56,7%** | **896,6** | **8.202,9** | **2.047.178** *(~2.047 s)* | 13,8 / — | **71,3 s** |
| **P2 – Batch 5.000** ([2.4-batch](results/official/2.4-batch/SUMMARY.md)) | **1.104,8** *(1.094,2–1.106,0)* | **-31,3%** | **619,5** | **978,7** | **370.797** *(~371 s)* | 15,3 / — | **89,7 s** |
| **P2 – Batch 1.000** ([2.4-batch](results/official/2.4-batch/SUMMARY.md)) | **1.255,2** *(1.254,7–1.349,5)* | **-24,1%** | **578,2** | **743,5** | **360.239** *(~360 s)* | 15,4 / — | **106,5 s** |
| **P3 – Lazy (`q=25%`)** ([2.4-lazy](results/official/2.4-lazy/SUMMARY.md)) | **1.069,8** *(1.066,6–1.072,6)* | **-34,6%** | **588,5** | **736,1** | **220.298** *(~220 s)* | **16,5 / 575,0** | **97,6 s** |

**2. Ảnh hưởng của tỉ lệ truy cập dữ liệu cũ `q` trên Lazy P3 (thí nghiệm E3, [2.4-lazy](results/official/2.4-lazy/SUMMARY.md)):**

| Tỉ lệ `q` (`"Xem đơn cũ"`) | TPS warmup *(nền)* | TPS đo *(Lazy P3)* | Mức giảm TPS so với nền | p50 / p99 toàn pha *(ms)* | `read_clean` / `read_migrated` p99 *(ms)* | Dòng chuyển theo yêu cầu (`migrated_on_demand`) | Xung đột migration | Chờ khóa `lock_wait_ms` | Hoàn tất *(s)* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`q = 5%`** | 1.363,9 | **1.027,1** *(1.022,1–1.106,2)* | **-24,7%** | 20,1 / **603,8** | **15,1 / 608,7** | **27.515** *(0,92%)* | 12 | 361.890 | **99,2 s** |
| **`q = 25%`** | 1.636,3 | **1.069,8** *(1.066,6–1.072,6)* | **-34,6%** | 22,6 / **588,5** | **16,5 / 575,0** | **141.056** *(4,70%)* | 19 | 220.298 | **97,6 s** |
| **`q = 50%`** | 2.274,7 | **1.165,4** *(1.152,3–1.187,3)* | **-48,8%** | 24,3 / **553,3** | **17,2 / 535,1** | **294.463** *(9,82%)* | 95 | 109.690 | **95,6 s** |

**Góc nhìn tổng quan trên MySQL InnoDB:**
- **Eager (P1)** xong nhanh nhất (`71,3 s`) nhưng giữ khóa trên cả kho (`lock_wait_ms = 2.047 s`), làm sụt **56,7% TPS** và gây các đợt đóng băng độ trễ đuôi lên tới **8,2 giây**.
- **Batch nền (P2, lô `1.000` dòng)** đạt **thông lượng cao nhất (`1.255,2 TPS`, chỉ giảm `24,1%`)** và cắt hoàn toàn gai độ trễ (`p99 = 578,2 ms`), vì mỗi lô gom 1.000 dòng vào **1 lần `COMMIT` (`fsync`) duy nhất** ở nền trong khi giao dịch đọc `"Xem đơn cũ"` vẫn là truy vấn đọc thuần (`p99 = 15,4 ms`).
- **Lazy (P3)** có **thời gian chờ khóa thấp nhất (`lock_wait_ms = 220 s` ở `q=25%`, giảm 9,3 lần so với Eager)** vì mỗi lượt chuyển theo yêu cầu chỉ khóa ~10 dòng của đúng 1 đơn. Tuy nhiên, khi triển khai ở tầng ứng dụng với độ bền `flush_log_at_trx_commit=1` + `sync_binlog=1`, mỗi đơn cũ chưa chuyển bị đọc trúng phải chịu **1 lần `UPDATE + COMMIT` (`fsync`) ngay trên đường xử lý truy vấn** khiến `read_migrated_p99_ms` lên tới **535–609 ms** (gấp ~35 lần đọc sạch `15–17 ms`). Vì vậy Lazy rất hiệu quả khi tỉ lệ đọc đơn cũ thấp (`q = 5%`, giảm TPS `-24,7%`), nhưng khi `q` tăng lên `25%–50%` thì mức suy giảm so với nền lớn dần (`-34,6%` → `-48,8%`), nên trên MySQL InnoDB bị giới hạn bởi `fsync` đĩa, **Batch nền lô 1.000 dòng** vẫn nhỉnh hơn Lazy về TPS tổng thể.

[Câu lệnh SQL và MongoDB để trình bày](docs/cau-lenh-dbms-2.1.md) có ví dụ chép vào trình soạn truy vấn, gồm EXPLAIN, New-Order, Payment và rollback.
