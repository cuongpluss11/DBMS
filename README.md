# Phân tích và tối ưu hiệu năng giao dịch Flash-sale trên MySQL, MongoDB và TiDB

![MySQL InnoDB](https://img.shields.io/badge/MySQL_InnoDB-8.4.8_LTS-4479A1?style=flat&logo=mysql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-8.0.20-47A248?style=flat&logo=mongodb&logoColor=white)
![TiDB](https://img.shields.io/badge/TiDB_/_TiKV_/_PD-v8.5.7_LTS-E30C34?style=flat&logo=tidb&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)
![PyMySQL](https://img.shields.io/badge/PyMySQL-1.1.2-00758F?style=flat&logo=python&logoColor=white)
![PyMongo](https://img.shields.io/badge/PyMongo-4.15.5-00ED64?style=flat&logo=mongodb&logoColor=black)
<br/>
![AWS EC2](https://img.shields.io/badge/AWS-EC2_%26_EBS_gp3-FF9900?style=flat&logo=amazonwebservices&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?style=flat&logo=terraform&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04_LTS-E95420?style=flat&logo=ubuntu&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?style=flat&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?style=flat&logo=grafana&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Verified-0A9EDC?style=flat&logo=pytest&logoColor=white)

> **BÁO CÁO BÀI TẬP LỚN — HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU**
> **Trường Đại học Công nghệ – Đại học Quốc gia Hà Nội (UET – VNU) · Khoa Công nghệ thông tin**
> - **Giảng viên hướng dẫn:** TS. Nguyễn Thị Cẩm Vân
> - **Thực hiện — Nhóm 16:**
>   1. **Nguyễn Mạnh Cường** — `24020052`
>   2. **Hoàng Xuân Lực** — `24020214`
>   3. **Tạ Duy Anh** — `24020025`

---

## 1. Tổng quan đề tài

Bộ khung thực nghiệm có khả năng tái lập (**reproducible benchmark suite**) phục vụ chẩn đoán và giảm nghẽn giao dịch **Flash-sale** (dựa trên lược đồ 9 bảng/collection của **TPC-C**) trên ba đại diện kiến trúc cơ sở dữ liệu hiện đại: **RDBMS truyền thống (MySQL InnoDB 8.4.8)**, **NoSQL hướng tài liệu (MongoDB 8.0.20)** và **NewSQL phân tán (TiDB v8.5.7)**.

Nghiên cứu tập trung giải quyết bốn bài toán kỹ thuật cốt lõi dưới cùng ngân sách tài nguyên, bộ nhớ đệm (`3 GiB`) và mức bảo đảm độ bền giao dịch tương đương:
1. **Chẩn đoán điểm nóng ghi (Hot SKU):** Phân tích cơ chế sụp giảm thông lượng (chờ khóa dòng, bão `write_conflict` & thử lại, xếp hàng tại Region nóng) khi tải dồn vào một mặt hàng.
2. **Bảo toàn tính đúng đắn tồn kho dưới tải cao & sự cố:** Kiểm chứng độc lập hệ **ba luật bất biến (`INV1–INV3`)** và cơ chế chống trùng đơn (`request_id UNIQUE`) khi tiến trình ứng dụng chết đột ngột giữa cửa sổ commit.
3. **Giảm nghẽn và mở rộng ngang trên NewSQL:** Định lượng hiệu quả riêng rẽ và tương tác giữa **chia tồn kho thành `N` slot (`P2`)**, **cấp mã đơn theo lô**, **điều tiết thích ứng (`P3`)**, mở rộng nút lưu trữ **TiKV (`1 → 3` nút)**, giao dịch liên phân vùng (**2PC**) và hệ số sao chép **Raft (`rf = 1` vs `rf = 3`)**.
4. **Đổi lược đồ trực tuyến khi đang bán hàng (Online Schema Evolution):** Phân tích hiện tượng đóng băng toàn bảng do kẹt *Metadata Lock (MDL)* và đánh đổi giữa ba chiến lược chuyển đổi dữ liệu lịch sử (**Eager, Batch nền, Lazy**).

> **Quy mô bằng chứng thực nghiệm:** **839 lượt đo chính thức trên AWS đa máy ảo** (Mục 2.2–2.5), **159 lượt đo mở rộng đổi lược đồ** trên AWS Docker `c6i.4xlarge` (Mục 2.6) và **152 lượt đo nghiệm thu nền** (Mục 2.1). Toàn bộ con số trong báo cáo đều truy xuất trực tiếp về CSV trong [`results/official/`](results/official/) và được đối chiếu tự động qua `scripts/verify_doc_numbers.py` (**285 ô số liệu, 0 sai lệch**; xem [`results/official/VERIFY.md`](results/official/VERIFY.md)).

---

## 2. Tóm tắt các phát hiện chính & Ma trận đánh đổi

### 2.1. Trả lời các câu hỏi nghiên cứu (Mục 2.7.1)

| Câu hỏi nghiên cứu | Kết quả thực nghiệm chính |
| :--- | :--- |
| **RQ1:** Nghẽn Flash-sale xuất phát từ đâu? | Xuất phát từ **điểm nóng ghi**, không phải độ lệch Zipf thông thường (`θ ≤ 0,7` chưa gãy; chế độ *"một món"* làm TPS sụp **2,8–3,7 lần** ở cả ba hệ và tăng thêm client không cứu được). Cơ chế nghẽn khác nhau: MySQL tốn **97% thời gian chờ khóa dòng**; MongoDB (a) bùng phát **~75.207 lỗi `write_conflict`/lượt** (retry `40,4%`); TiDB xếp hàng tại Region nóng. |
| **RQ2:** Phương pháp nào giảm nghẽn mà vẫn đúng 3 luật? | **Chia tồn kho thành `N` slot (`P2`, `N=27`)** là đòn bẩy lớn nhất, tăng TPS **5,9–8,5 lần** ở kịch bản *"một món"* (`426 → 2.741` MySQL; `673 → 3.955` MongoDB; `255 → 2.157` TiDB) và **100% lượt chạy đều `VALID`**. **Cấp mã đơn theo lô (`50` mã/lần)** là nguồn lợi ích độc lập (tăng tới **2,5×** trên TiDB ở `θ = 0,9`). |
| **RQ3:** Khi nào cơ chế tối ưu gây tác dụng phụ hoặc đánh đổi? | **Điều tiết thích ứng (`P3`)** nhạy mạnh với ngưỡng cấu hình: ở ngưỡng `p99 = 500 ms` dưới tải `≥ 100%`, P3 làm giảm **27–50% TPS** trên MySQL do hạ giới hạn đồng thời quá thấp; ở ngưỡng `1.000–2.000 ms` thì ngang `P2`. **MongoDB thiết kế (b)** (bỏ giao dịch đa tài liệu) tăng tốc **~9,9×** (`8.354 TPS`) nhưng **vi phạm `INV2`** khi ứng dụng sập giữa bước trừ kho và ghi đơn. |
| **RQ4–RQ6:** Thêm nút TiKV, 2PC và sao chép Raft tác động thế nào? | Trên Hot SKU, thêm `1 → 3` TiKV một mình chỉ tăng **`1,22–1,29×`** vì tải dồn vào 1 Region; kết hợp với **chia slot (`P2 N=27`)** đạt **`3,44–3,80×`** (hiệu ứng tương tác). Tăng hệ số nhân bản **`rf = 1 → 3`** làm giảm **25–47% TPS** ở tải ghi phân tán do chi phí Raft/CPU trên nút TiKV `2 vCPU`. |
| **Mục 2.6:** Đổi lược đồ bảng `order_line` (~3 triệu dòng) dưới tải? | Trên MySQL, 1 giao dịch đọc dài `60 s` khiến `ALTER INSTANT` gây kẹt *Metadata Lock*, đóng băng toàn bảng **57 giây**; đặt `lock_wait_timeout = 3` kèm retry giảm đóng băng còn **2 giây** (giữ TPS gấp **2,54×**). TiDB Online DDL đạt **0 giây đóng băng** giao dịch mới. Ở bước chuyển dữ liệu cũ, **Batch lô `1.000`** đạt TPS cao nhất trên cả 3 hệ (`-16,3%` MySQL; `-0,6%` MongoDB; `-8,7%` TiDB so với nền). |

### 2.2. Ma trận khuyến nghị thiết kế (Mục 2.7.2)

| Tình huống vận hành | Khuyến nghị kiến trúc | Đánh đổi cần lưu ý |
| :--- | :--- | :--- |
| **Hot SKU, yêu cầu đúng đắn tuyệt đối** | `P1` + chia slot (`P2`) + cấp mã đơn theo lô trong giao dịch ACID | Logic ứng dụng phức tạp hơn khi tồn kho chạm đáy (cần quét các slot còn dư). |
| **Ưu tiên thông lượng tối đa trên MongoDB** | Thiết kế `(b)` (cập nhật đơn tài liệu + đơn nhúng) | Chấp nhận rủi ro lệch đối soát tồn kho (`INV2`) nếu tiến trình chết giữa chừng; cần cơ chế đối soát bù. |
| **Mở rộng ngang cụm NewSQL (TiDB)** | Phá điểm nóng dữ liệu (chia slot + `AUTO_RANDOM` + tách Region) **trước**, thêm nút TiKV **sau** | Bật độ bền production (`rf = 3`) tiêu tốn thêm `25–47%` thông lượng ghi trên cấu hình thử nghiệm. |
| **Đổi lược đồ bảng lớn đang bán hàng** | Kiểm tra giao dịch dài + `lock_wait_timeout` ngắn → `INSTANT` / Online DDL → **Batch lô `1.000`** | Thời gian hoàn tất migration dài hơn `Eager`, đổi lại tránh sụp TPS và tránh vọt đỉnh độ trễ `p99`. |

---

## 3. Bản đồ Báo cáo ↔ Mã nguồn, Demo UI & Dữ liệu thực nghiệm

| Phần trong Báo cáo | Tài liệu & Hướng dẫn chi tiết | Mã nguồn / Kịch bản thực thi | Dữ liệu kết quả & Biểu đồ |
| :--- | :--- | :--- | :--- |
| **Phần 1 — Mục 1.4 & Phụ lục A.8, B.8** *(Cài đặt, cấu hình & Demo UI)* | [`docs/demo-ui-1.4.md`](docs/demo-ui-1.4.md) | [`scripts/demo/demo_mongo_1.4.js`](scripts/demo/demo_mongo_1.4.js)<br/>[`scripts/demo/demo_tidb_1.4.sql`](scripts/demo/demo_tidb_1.4.sql) | Kịch bản kiểm chứng phiên bản, CRUD, chống âm kho, ACID, Region & Online DDL trên **Compass** & **Workbench**. |
| **Phần 2 — Mục 2.1** *(Workload, hạ tầng & phương pháp đo)* | [`docs/acceptance-2.1.md`](docs/acceptance-2.1.md)<br/>[`docs/experiment-2.1.md`](docs/experiment-2.1.md) | [`src/flashsale/workload/`](src/flashsale/workload/)<br/>[`src/flashsale/validation/`](src/flashsale/validation/)<br/>[`infra/aws/`](infra/aws/) | [`results/official/2.1-aws/`](results/official/2.1-aws/)<br/>[`results/official/explain-tidb.json`](results/official/explain-tidb.json) |
| **Phần 2 — Mục 2.2, 2.3 & 2.4** *(Nghẽn Hot SKU, Fault Injection, P0–P3 & T4)* | [`docs/experiment-2.2.md`](docs/experiment-2.2.md)<br/>[`docs/fault-injection.md`](docs/fault-injection.md)<br/>[`docs/demo-phan-2.md`](docs/demo-phan-2.md) | [`src/flashsale/transactions/`](src/flashsale/transactions/)<br/>[`scripts/run-matrix-2.2.sh`](scripts/run-matrix-2.2.sh)<br/>[`scripts/fault_kill_cycles.py`](scripts/fault_kill_cycles.py) | [`results/official/2.2-aws/`](results/official/2.2-aws/)<br/>[`results/official/fault-injection/`](results/official/fault-injection/)<br/>[`results/official/figures/`](results/official/figures/) |
| **Phần 2 — Mục 2.5** *(Mở rộng TiKV, 2PC liên kho & Raft `rf=3`)* | [`docs/experiment-2.3.md`](docs/experiment-2.3.md) | [`scripts/run-matrix-2.3.sh`](scripts/run-matrix-2.3.sh)<br/>[`scripts/placement_summary.py`](scripts/placement_summary.py) | [`results/official/2.3-aws/`](results/official/2.3-aws/) |
| **Phần 2 — Mục 2.6** *(Online Schema Evolution: E1, E2, E3)* | [`docs/experiment-2.4.md`](docs/experiment-2.4.md)<br/>[`docs/demo-ui-2.6.md`](docs/demo-ui-2.6.md) | [`scripts/run-2.4-e1.sh`](scripts/run-2.4-e1.sh)<br/>[`scripts/run-2.4-eager.sh`](scripts/run-2.4-eager.sh)<br/>[`scripts/run-2.4-batch.sh`](scripts/run-2.4-batch.sh)<br/>[`scripts/run-2.4-lazy.sh`](scripts/run-2.4-lazy.sh) | [`results/official/2.4-e1/`](results/official/2.4-e1/) · [`2.4-eager/`](results/official/2.4-eager/)<br/>[`results/official/2.4-batch/`](results/official/2.4-batch/) · [`2.4-lazy/`](results/official/2.4-lazy/)<br/>[`docs/figures/2.4/`](docs/figures/2.4/) |
| **Đối soát số liệu toàn báo cáo** | [`docs/assumptions.md`](docs/assumptions.md)<br/>[`AGENTS.md`](AGENTS.md) | [`scripts/verify_doc_numbers.py`](scripts/verify_doc_numbers.py)<br/>[`scripts/verify_results.py`](scripts/verify_results.py) | [`results/official/VERIFY.md`](results/official/VERIFY.md) *(285 ô số liệu, 0 lệch)* |

---

## 4. Kiến trúc hệ thống & Thiết lập công bằng

### 4.1. Cấu trúc package `src/flashsale/`
- `adapters/`: Giao diện kết nối, quản lý phiên giao dịch và truy vấn đồng nhất cho MySQL, MongoDB và TiDB (giữ nguyên ngữ nghĩa riêng của từng hệ).
- `workload/`: Bộ sinh tải Flash-sale theo phân phối Zipf (`θ ∈ {0; 0,3; 0,5; 0,7; 0,9}` và chế độ *"một món"* qua hoán vị cố định theo `seed`), chọn kho `uniform` / `single-warehouse` / đa kho, backoff lũy thừa tối đa 5 lần retry.
- `transactions/`: Nghiệp vụ `New-Order` (1–5 mặt hàng, các biến thể `P0`, `P1`, `P2` chia slot, `P3` điều tiết, cấp mã theo lô) và `Payment` tách biệt khỏi tầng kết nối.
- `benchmark/`: Tiến trình sinh tải đa worker (vòng đóng & vòng mở), tách riêng `30 s` warmup và `60 s` đo chính thức, thu thập `tps_per_second.csv`, độ trễ `p50/p95/p99` và chỉ số hệ thống.
- `validation/`: Kiểm chứng độc lập **ba luật tồn kho (`INV1` không âm kho, `INV2` đối soát tồn đầu − tồn cuối = tổng `order_line` đã commit, `INV3` không trùng `request_id`)** bằng cả Python lẫn câu truy vấn/aggregation chéo trên DBMS (`doc_reconciliation`).
- `data/`: Khởi tạo lược đồ 9 bảng/collection TPC-C, nạp dữ liệu (`W = 10` hoặc `W = 12`, `100.000` mặt hàng/kho), quản lý snapshot và khôi phục trạng thái sạch trước mỗi lần lặp.

### 4.2. Hạ tầng và độ bền tương đương (Mục 2.1.3)

| Thành phần | Hạ tầng AWS chính thức (Mục 2.2–2.5) | Docker Compose phát triển / Mục 1.4 & 2.6 | Cấu hình bộ nhớ đệm & Độ bền giao dịch |
| :--- | :--- | :--- | :--- |
| **MySQL 8.4.8** | `m6i.8xlarge` (giới hạn `24 vCPU / 60 GiB`) | `8 vCPU / 16 GiB` (`:13306`) | Buffer pool `3 GiB` (`baseline-tuned`), `innodb_flush_log_at_trx_commit = 1`, `sync_binlog = 1`. |
| **MongoDB 8.0.20** | `m6i.8xlarge` (giới hạn `24 vCPU / 60 GiB`) | `8 vCPU / 16 GiB` (`:27018`) | Replica Set 1 nút `flashsale`, WiredTiger cache `3 GiB`, `readConcern: "snapshot"`, `writeConcern: {w: "majority", j: true}`. |
| **TiDB v8.5.7** | TiDB `c6i.4xlarge` + PD `c6i.large` + `3 ×` TiKV `m6i.large` (tổng `24 vCPU / 60 GiB`) | `1 PD + 1 TiDB + 3 TiKV` (tổng `8 vCPU / 16 GiB`, SQL `:14000`, PD `:12379`) | Block cache `1 GiB × 3 TiKV = 3 GiB`, Raft log đồng bộ mặc định, `pessimistic`, `rf = 1` (và `rf = 3` ở nhóm R2). |
| **Máy sinh tải** | VM riêng `c6i.4xlarge` (`16 vCPU`), EBS `gp3` | Chạy cùng máy dev (ghi nhãn *sơ bộ*) | Đa tiến trình Python 3.12 (CPU máy tải thực đo `≤ 78%`, không là nút thắt). |

---

## 5. Hướng dẫn Cài đặt & Vận hành

### 5.1. Thiết lập môi trường (Ubuntu 24.04 LTS / WSL2)

Yêu cầu máy ảo `x86_64` có Python 3.12, `venv`, Docker Engine và Docker Compose V2 (khuyến nghị `≥ 12 vCPU, 20 GiB RAM` khi nạp dataset đầy đủ `W = 10`):

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv git

# Nếu máy ảo chưa cài Docker Engine & Compose V2 (tách riêng bước cần quyền quản trị):
sudo bash scripts/bootstrap-docker.sh --install
sudo usermod -aG docker "$USER"   # đăng nhập lại sau lệnh này
```

Khởi tạo môi trường ảo Python, chạy bộ unit test và kiểm tra trạng thái Docker:

```bash
bash scripts/setup.sh
source .venv/bin/activate
flashsale doctor
```

### 5.2. Chạy Demo UI Mục 1.4 (MongoDB Compass & MySQL Workbench)

Thực hiện trên máy cá nhân (Windows/macOS/Linux có Docker Desktop), chỉ bật **một hệ tại một thời điểm** (chi tiết từng bước chụp hình tại [`docs/demo-ui-1.4.md`](docs/demo-ui-1.4.md)):

```bash
# 1. Demo MongoDB 8.0.20 (Compass: mongodb://127.0.0.1:27018/?directConnection=true)
docker compose -f docker/compose.mongo.yml up -d
docker exec -i flashsale-mongo-mongo-1 mongosh --quiet < scripts/demo/demo_mongo_1.4.js
docker compose -f docker/compose.mongo.yml stop

# 2. Demo TiDB v8.5.7 (Workbench: 127.0.0.1:14000 | Dashboard: http://127.0.0.1:12379/dashboard)
docker compose -f docker/compose.tidb.yml up -d
# Mở scripts/demo/demo_tidb_1.4.sql trên MySQL Workbench để chạy kịch bản B.8-1 -> B.8-6
docker compose -f docker/compose.tidb.yml stop
```

### 5.3. Kiểm tra nhanh một hệ DBMS (Integration Test & Smoke Benchmark)

Thay `mysql` bằng `mongo` hoặc `tidb` tùy hệ cần kiểm tra (chỉ chạy 1 hệ tại một thời điểm):

```bash
flashsale start mysql
flashsale status mysql
FLASHSALE_TEST_ENGINE=mysql python -m pytest -m integration -q
flashsale smoke mysql
flashsale stop mysql
```

*(Có thể chạy `bash scripts/setup.sh --smoke-all` để tự động tải các image đã pin SHA256 và chạy smoke tuần tự cả ba hệ).*

### 5.4. Quy trình nạp dữ liệu, chạy Benchmark `W = 10` & Đối soát 3 luật

```bash
# 1. Khởi động MySQL (mặc định 128 MiB cho mốc baseline; đặt 3 GiB cho baseline-tuned)
FLASHSALE_MYSQL_BUFFER_POOL_BYTES=3221225472 flashsale start mysql
flashsale status mysql

# 2. Nạp dataset W=10 (9 bảng TPC-C) và lưu tên database
DATASET=$(flashsale load mysql --config configs/baseline-tuned.toml |
    python -c 'import json,sys; print(json.load(sys.stdin)["database"])')

# 3. Chạy 3 lần lặp độc lập (30s warmup + 60s đo), tự động khôi phục dataset giữa các lần
flashsale run mysql --config configs/baseline-tuned.toml --dataset "$DATASET" --reset-between

# 4. Đối soát độc lập lại 3 luật tồn kho (thay RUN_UUID_HEX bằng run_id thực tế) và dừng hệ
flashsale validate mysql --run-id RUN_UUID_HEX
flashsale stop mysql
```

Mỗi lần chạy xuất đầy đủ `manifest.json` (phiên bản, digest image, cấu hình cache/độ bền, Git commit), `result.json`, `result.csv` và `tps_per_second.csv` vào `results/<run_id>/`.

### 5.5. Bảng tra cứu lệnh CLI `flashsale`

| Lệnh CLI | Chức năng |
| :--- | :--- |
| `flashsale doctor` · `flashsale status ENGINE` | Kiểm tra môi trường chung và readiness thực tế của từng DBMS (`mysql`, `mongo`, `tidb`). |
| `flashsale start ENGINE` · `flashsale stop ENGINE` | Bật hoặc dừng container của hệ tương ứng (bảo toàn volume dữ liệu). |
| `flashsale smoke ENGINE [--variant p2 --slots 9]` | Nạp dataset thu gọn, kiểm thử tình huống hết hàng, đối soát 3 luật rồi tự dọn sạch. |
| `flashsale load ENGINE --config PROFILE` | Khởi tạo lược đồ, nạp dữ liệu TPC-C và xuất fingerprint dataset. |
| `flashsale reset ENGINE --config PROFILE --dataset NAME --confirm NAME` | Khôi phục tồn kho và bảng đơn hàng về trạng thái ban đầu trước lượt đo mới. |
| `flashsale run ENGINE --config PROFILE --dataset NAME --reset-between` | Thực thi điểm đo nhiều lần lặp, thu thập độ trễ, xung đột và tự động kiểm 3 luật. |
| `flashsale validate ENGINE --run-id ID` | Chạy kiểm tra độc lập 3 luật tồn kho + câu truy vấn đối soát chéo trên DB. |
| `flashsale report --results-dir DIR --out OUT` | Tổng hợp `INDEX.csv`, `SUMMARY.md` và phân tích độ ổn định warmup. |
| `flashsale drop ENGINE --dataset NAME --confirm NAME` | Xóa tường minh dataset đã đăng ký (yêu cầu tên xác nhận khớp tuyệt đối). |

### 5.6. Tái lập các ma trận thực nghiệm & Kiểm chứng số liệu báo cáo

```bash
# Chạy lưới thực nghiệm theo từng mục (thêm --dry-run để xem trước danh sách cấu hình):
bash scripts/run-matrix-2.1.sh mysql --dry-run
bash scripts/run-matrix-2.2.sh mysql --dry-run
bash scripts/run-matrix-2.3.sh --dry-run

# Chạy các kịch bản Online Schema Evolution (Mục 2.6: E1, E2, E3) & vẽ lại biểu đồ:
bash scripts/run-2.4-e1.sh mysql
bash scripts/run-2.4-eager.sh mysql
bash scripts/run-2.4-batch.sh mysql
Q_LIST="5 25 50" bash scripts/run-2.4-lazy.sh mysql
python scripts/plot-2.4.py

# Vẽ biểu đồ Phần 2 và đối chiếu tự động 285 con số trong báo cáo với CSV gốc:
python scripts/make_figures.py
python scripts/verify_doc_numbers.py
```

---

## 6. Tài liệu tham chiếu bổ sung trong Repo

- [`AGENTS.md`](AGENTS.md): Quy tắc kỹ thuật, bất biến thực nghiệm và an toàn vận hành.
- [`infra/aws/README.md`](infra/aws/README.md): Cấu hình Terraform, TiUP topology và quy trình vận hành hạ tầng AWS nhiều máy ảo.
- [`docs/assumptions.md`](docs/assumptions.md): Các quyết định thiết kế có chủ đích và khác biệt so với TPC-C chuẩn.
- [`docs/cau-lenh-dbms-2.1.md`](docs/cau-lenh-dbms-2.1.md): Tập câu lệnh SQL / MongoDB mẫu giải thích cơ chế giao dịch và truy vấn đối soát.
