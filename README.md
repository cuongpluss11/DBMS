# Flash-sale DBMS Benchmark

Mục 2.1 của bài tập lớn DBMS. Dự án nạp cùng dữ liệu TPC-C, chạy New-Order và Payment trên MySQL InnoDB, MongoDB mode A và TiDB, rồi xuất bằng chứng để tái hiện phép đo và đối soát tồn kho.

## Bắt đầu cùng nhóm

**[Hướng dẫn triển khai mục 2.1 cho 3 thành viên](docs/trien-khai-2.1.md)** có phân công, cách checkout cùng Git commit trên ba VM và checklist nghiệm thu.

| Thành viên | DBMS phụ trách | Phần bàn giao chính |
| --- | --- | --- |
| TV1 | MySQL 8.4.8 | Chốt Git commit và cấu hình VM, chạy baseline uniform và single-warehouse |
| TV2 | MongoDB 8.0.20 | Replica set một nút, giao dịch nhiều tài liệu, bằng chứng rollback và replay |
| TV3 | TiDB, PD và TiKV v8.5.7 | Một PD, một TiDB, ba TiKV, replica count 1 và bằng chứng Region |

Mỗi người dùng một VM Ubuntu có cùng cấu hình và checkout cùng một Git commit. Mỗi VM chỉ chạy DBMS được giao, với tổng ngân sách container 8 CPU và 16 GiB RAM. Nếu nhiều VM nằm trên cùng một máy vật lý, nhóm đo lần lượt để tránh tranh tài nguyên. Kết quả kiểm chứng cục bộ được ghi trong [giao thức thực nghiệm](docs/experiment-2.1.md).

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

**[Nghiệm thu mục 2.1](docs/acceptance-2.1.md)** có kết quả đo thật, khác biệt so với đề và danh sách NOT TESTED; dữ liệu chính thức ở [results/official/2.1/](results/official/2.1/INDEX.csv). [Hướng dẫn cho nhóm](docs/trien-khai-2.1.md) có lệnh baseline một kho, lượt kiểm luật, lượt so sánh ba hệ và cách bàn giao kết quả. Xem thêm [ánh xạ yêu cầu](docs/requirements-2.1.md), [các quyết định thực nghiệm](docs/assumptions.md) và [định nghĩa trường kết quả](docs/experiment-2.1.md).

[Câu lệnh SQL và MongoDB để trình bày](docs/cau-lenh-dbms-2.1.md) có ví dụ chép vào trình soạn truy vấn, gồm EXPLAIN, New-Order, Payment và rollback.
