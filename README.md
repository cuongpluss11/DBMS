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

Kho mã nguồn này lưu trữ bộ khung thực nghiệm khả lập lại (**reproducible benchmark suite**), kịch bản kiểm chứng giao diện và toàn bộ dữ liệu kết quả cho báo cáo **Phân tích và tối ưu hiệu năng giao dịch Flash-sale trên MySQL, MongoDB và TiDB**. Kế thừa lược đồ 9 bảng/collection của chuẩn **TPC-C**, nhóm xây dựng kịch bản tải **Flash-sale tùy biến** (không phải phép đo chuẩn TPC-C chính thức) để đối chiếu ba kiến trúc cơ sở dữ liệu dưới cùng ngân sách phần cứng, cùng bộ nhớ đệm (`3 GiB`) và cùng mức ghi bền dữ liệu xuống ổ đĩa:
- **RDBMS truyền thống:** **MySQL InnoDB 8.4.8 LTS** (đối chứng).
- **NoSQL hướng tài liệu:** **MongoDB Community 8.0.20** (*MongoDB giao dịch* dùng giao dịch nhiều tài liệu trên Replica Set và *MongoDB nhúng* dùng tài liệu đơn hàng nhúng).
- **NewSQL phân tán:** **TiDB / TiKV / PD v8.5.7 LTS** (kiến trúc phân tách SQL – lưu trữ phân tán Multi-Raft và giao dịch hai pha 2PC).

Nghiên cứu giải quyết trọn vẹn hai phần của học phần:
- **Phần 1 (Mục 1.1 – 1.5 & Phụ lục A, B):** Phân tích kiến trúc, cơ chế kiểm soát đồng thời, khả năng mở rộng, thay đổi lược đồ và kiểm chứng thực tế 6 nhóm chức năng vận hành cơ bản trên **MongoDB Compass** và **MySQL Workbench / TiDB Dashboard**.
- **Phần 2 (Mục 2.1 – 2.7 & Phụ lục C, D):** Trả lời bằng thực nghiệm định lượng bốn câu hỏi chuyên sâu: **(1)** khi nhiều người cùng tranh mua một mặt hàng nóng (*hot SKU*) thì nghẽn do đâu (Mục 2.2); **(2)** cách nào giảm nghẽn mà không bán vượt tồn kho (*oversell*), kể cả khi tiến trình ứng dụng chết đột ngột giữa cửa sổ chốt đơn (Mục 2.3 và 2.4); **(3)** trên TiDB, thêm nút lưu trữ TiKV giúp được bao nhiêu và hệ số sao chép Raft `rf = 3` tốn thêm chi phí gì (Mục 2.5); **(4)** ở phần mở rộng, đổi lược đồ và chuyển đổi ~3 triệu dòng lịch sử khi đang bán hàng bằng cách nào ít chặn giao dịch nhất, đối chiếu với cơ chế *Lazy Evaluation* của **BullFrog (SIGMOD '21)** (Mục 2.6 & Phụ lục D).

> **Quy mô bằng chứng thực nghiệm:** **839 lượt đo chính thức trên hạ tầng AWS đa máy ảo** (Mục 2.2–2.5, ngân sách `24 vCPU / 60 GiB RAM` mỗi hệ), **159 lượt đo `VALID` cho mở rộng đổi lược đồ** trên AWS Docker `c6i.4xlarge` (Mục 2.6 & Phụ lục D, nhãn *sơ bộ*) và **152 lượt đo nghiệm thu nền** (Mục 2.1). Mọi con số trong báo cáo đều truy xuất trực tiếp về CSV/JSON trong [`results/official/`](results/official/) và được kiểm chứng tự động qua `scripts/verify_doc_numbers.py` (**285 ô số liệu, 0 sai lệch**; xem [`results/official/VERIFY.md`](results/official/VERIFY.md)).

---

## 2. Tổng hợp kết quả nghiên cứu & Ma trận đánh đổi

### 2.1. Tổng hợp trả lời sáu câu hỏi nghiên cứu (Mục 2.7.1)

| Câu hỏi nghiên cứu | Kết quả thực nghiệm chính |
| :--- | :--- |
| **Nghẽn do đâu?** *(Mục 2.2)* | Xuất phát trực tiếp từ **điểm nóng ghi** chứ không đơn thuần từ độ lệch Zipf `θ`: vùng `θ ≤ 0,7` chưa xuất hiện điểm gãy, nhưng chế độ *"một món"* làm thông lượng ở `64 client` sụt **2,8–3,7 lần** trên cả ba hệ và tăng lên `256 client` không cứu được TPS. Cơ chế nghẽn khác biệt rõ rệt: MySQL tốn **97% thời gian client chờ khóa dòng**; *MongoDB giao dịch* bùng phát **~75.207 lỗi `write_conflict`/lượt** (tỉ lệ retry `40,4%`); TiDB xếp hàng tại Region nóng. |
| **Có bán vượt tồn kho không?** *(Mục 2.3)* | Trong **839 lượt đo chính thức trên AWS**, các phương pháp có bảo vệ (*trừ có điều kiện*, *chia slot*, *chia slot kèm điều tiết*) đều thỏa mãn **cả ba luật tồn kho** (*không âm kho, khớp sổ sách, không trùng đơn*); **14 lượt `INVALID`** đều thuộc cách *đọc rồi ghi đè* không bảo vệ (7 trên MySQL, 7 trên TiDB). Khi tiêm lỗi giết tiến trình ngẫu nhiên, TiDB không vi phạm ở **76 và 95 lần rơi trúng cửa sổ `"đã commit, chưa ack"`**; *MongoDB nhúng* vi phạm luật khớp sổ nếu ứng dụng chết giữa bước trừ kho và bước ghi đơn. |
| **Cách nào giảm nghẽn mà vẫn đúng?** *(Mục 2.4)* | **Chia slot tồn kho (`27` slot) kèm cấp mã đơn theo lô (`50` mã)** là đòn bẩy mạnh nhất, tăng thông lượng **5,9–8,5 lần** so với *trừ có điều kiện* ở chế độ *"một món"* (`426 → 2.741` MySQL; `673 → 3.955` MongoDB; `255 → 2.157` TiDB) và giữ `VALID` trên mọi lượt đo. Riêng **cấp mã đơn theo lô** đóng góp lợi ích độc lập (tăng tới **2,5×** trên TiDB ở `θ = 0,9`). |
| **Khi nào chi phí vượt lợi ích?** *(Mục 2.4)* | Dưới tải vòng mở `≥ 100%` trên MySQL với ngưỡng đặc tả `p99 = 500 ms`, **bộ điều tiết thích ứng** làm giảm **22–48% TPS** (từ chối `21–51%` yêu cầu) do đặt ngưỡng thấp hơn độ trễ tự nhiên của hệ thống; khi nới ngưỡng lên `1.000–2.000 ms` thì hiệu năng ngang *chia slot*. Với cơ chế riêng từng hệ, **MongoDB nhúng** nhanh hơn *MongoDB giao dịch* khoảng **9,9×** (`8.354` so với `845 TPS`) nhưng đánh đổi tính nguyên tử giữa tồn kho và đơn hàng. |
| **Thêm TiKV, replication giúp gì và tốn gì?** *(Mục 2.5)* | Với hot SKU, tăng từ `1 → 3` nút TiKV đơn lẻ chỉ đạt **`1,22–1,29×`** (qua hai lần dựng cụm độc lập), nhưng khi kết hợp **chia slot (`27` slot)** tạo hiệu ứng tương tác đẩy TPS tăng **`3,44–3,80×`**. Nâng hệ số sao chép từ **`rf = 1` lên `rf = 3`** (kiểm soát đảo thứ tự đo `rf=3 → rf=1 → rf=3`) làm giảm **25–47% thông lượng** ở các tải ghi lan rộng do chạm trần CPU trên cấu hình `2 vCPU/TiKV`. |
| **Đổi lược đồ khi đang bán thế nào ít chặn nhất?** *(Mục 2.6 & Phụ lục D)* | `ADD COLUMN INSTANT` trên MySQL xong trong `0,05 s` (`0 s` treo) khi tải thường, nhưng chỉ **1 giao dịch đọc mở `60 s`** làm treo cứng toàn bảng **57 giây** do kẹt hàng đợi `EXCLUSIVE` MDL; đặt `lock_wait_timeout = 3` kèm retry giảm đóng băng còn **2 giây** (khôi phục TPS gấp **`2,54×`**). TiDB Online DDL đạt **`0 s` đóng băng** giao dịch mới. Khi chuyển ~3 triệu dòng cũ ở `q = 25%`, **Batch lô `1.000` dòng** đạt TPS cao nhất trên cả ba hệ và cắt **25,5×** gai `p99` của `Eager` ở tải cao; **Lazy** (kiểu BullFrog ở tầng ứng dụng) giữ `p99` toàn pha sát nền nhất nhưng chỉ thắng `Batch 1.000` về TPS trên MySQL khi tỉ lệ đọc đơn cũ thấp (`q = 5%`). *(Số đo sơ bộ trên Docker).* |

### 2.2. Ma trận đánh đổi cho bài toán triển khai thực tế (Mục 2.7.2)

| Kịch bản vận hành | Khuyến nghị kiến trúc | Đánh đổi cần lưu ý |
| :--- | :--- | :--- |
| **Hot SKU yêu cầu đúng đắn tuyệt đối** | Áp dụng *trừ có điều kiện* kết hợp **chia slot tồn kho** và **cấp mã đơn theo lô** trong cùng giao dịch nguyên tử. | Phức tạp hơn ở tầng ứng dụng khi gần hết hàng (cần quét tìm slot còn dư). |
| **Ưu tiên tốc độ tối đa trên MongoDB** | Sử dụng **MongoDB nhúng**, bỏ giao dịch nhiều tài liệu. | Nguy cơ lệch tồn kho/đơn hàng (vi phạm luật khớp sổ) nếu ứng dụng chết giữa bước trừ kho và ghi đơn; cần đối soát bù. |
| **Mở rộng ngang cụm TiDB** | Tối ưu mô hình dữ liệu (**chia slot**, `AUTO_RANDOM`, tách Region) **trước**, bổ sung nút **TiKV sau**. | Cấu hình chịu lỗi production (`rf = 3`) tiêu tốn khoảng `25–47%` thông lượng ghi trên cấu hình `2 vCPU/TiKV`. |
| **Đổi lược đồ bảng lớn khi đang có tải** | Kiểm tra giao dịch dài + `lock_wait_timeout = 3` → thêm cột bằng **`INSTANT` / Online DDL** → chuyển dữ liệu cũ bằng **Batch lô `1.000`** *(chỉ dùng `Lazy` khi `q ≤ 5%` hoặc ưu tiên `p99` sát nền)*. | Thời gian hoàn tất nền chậm hơn `Eager` khoảng `1,4–1,6×`, đổi lại tránh sụp TPS và tránh gai độ trễ `p99` hàng chục giây. |

---

## 3. Bản đồ Báo cáo & Phụ lục ↔ Mã nguồn, Kịch bản Demo & Dữ liệu

| Mục trong Báo cáo chính & Phụ lục | Tài liệu phân tích & Hướng dẫn Demo | Mã nguồn / Script thực thi | Dữ liệu kết quả & Biểu đồ |
| :--- | :--- | :--- | :--- |
| **Phần 1 (Mục 1.1 – 1.5) & Phụ lục A, B** *(Kiến trúc, cài đặt & 12 demo cơ bản MongoDB/TiDB)* | [`docs/demo-ui-1.4.md`](docs/demo-ui-1.4.md) | [`scripts/demo/demo_mongo_1.4.js`](scripts/demo/demo_mongo_1.4.js)<br/>[`scripts/demo/demo_tidb_1.4.sql`](scripts/demo/demo_tidb_1.4.sql) | Kiểm chứng phiên bản, Replica Set / 5 nút TiDB, CRUD, chống âm kho, ACID, Region & Online DDL trên **Compass** & **Workbench**. |
| **Phần 2 — Mục 2.1** *(Workload tùy biến, 3 luật tồn kho, hạ tầng & quy trình đo)* | [`docs/acceptance-2.1.md`](docs/acceptance-2.1.md)<br/>[`docs/experiment-2.1.md`](docs/experiment-2.1.md)<br/>[`docs/trien-khai-2.1.md`](docs/trien-khai-2.1.md) | [`src/flashsale/workload/`](src/flashsale/workload/)<br/>[`src/flashsale/validation/`](src/flashsale/validation/)<br/>[`infra/aws/`](infra/aws/) | [`results/official/2.1-aws/`](results/official/2.1-aws/)<br/>[`results/official/explain-tidb.json`](results/official/explain-tidb.json) |
| **Phần 2 — Mục 2.2, 2.3, 2.4 & Phụ lục C.1–C.3** *(Chẩn đoán nghẽn, Không oversell & tiêm lỗi, Chia slot & điều tiết)* | [`docs/experiment-2.2.md`](docs/experiment-2.2.md)<br/>[`docs/fault-injection.md`](docs/fault-injection.md)<br/>[`docs/demo-phan-2.md`](docs/demo-phan-2.md) | [`src/flashsale/transactions/`](src/flashsale/transactions/)<br/>[`scripts/run-matrix-2.2.sh`](scripts/run-matrix-2.2.sh)<br/>[`scripts/fault_kill_cycles.py`](scripts/fault_kill_cycles.py) | [`results/official/2.2-aws/`](results/official/2.2-aws/)<br/>[`results/official/fault-injection/`](results/official/fault-injection/)<br/>[`results/official/figures/`](results/official/figures/) |
| **Phần 2 — Mục 2.5 & Phụ lục C.4** *(Mở rộng TiKV, 2PC liên kho, Raft `rf=3` & Demo tách Region)* | [`docs/experiment-2.3.md`](docs/experiment-2.3.md)<br/>[`docs/huong-dan-quay-demo-2.5.md`](docs/huong-dan-quay-demo-2.5.md) | [`src/flashsale/data/placement.py`](src/flashsale/data/placement.py)<br/>[`scripts/run-matrix-2.3.sh`](scripts/run-matrix-2.3.sh)<br/>[`scripts/placement_summary.py`](scripts/placement_summary.py) | [`results/official/2.3-aws/`](results/official/2.3-aws/) |
| **Phần 2 — Mục 2.6 & Phụ lục D** *(Đổi lược đồ trực tuyến: MDL, Eager/Batch/Lazy & đối chiếu BullFrog)* | [`docs/report-2.6-and-appendix.md`](docs/report-2.6-and-appendix.md)<br/>[`docs/experiment-2.4.md`](docs/experiment-2.4.md)<br/>[`docs/demo-ui-2.6.md`](docs/demo-ui-2.6.md) | [`src/flashsale/e1_ddl.py`](src/flashsale/e1_ddl.py)<br/>[`src/flashsale/migration.py`](src/flashsale/migration.py)<br/>[`scripts/run-2.4-e1.sh`](scripts/run-2.4-e1.sh) · [`plot-2.4.py`](scripts/plot-2.4.py) | [`results/official/2.4-e1/`](results/official/2.4-e1/) · [`2.4-eager/`](results/official/2.4-eager/)<br/>[`results/official/2.4-batch/`](results/official/2.4-batch/) · [`2.4-lazy/`](results/official/2.4-lazy/)<br/>[`results/official/2.4-highload/`](results/official/2.4-highload/) · [`docs/figures/2.4/`](docs/figures/2.4/) |
| **Phần 2 — Mục 2.7 & Đối soát số liệu** *(Kết luận, giới hạn & kiểm soát chất lượng đo)* | [`docs/assumptions.md`](docs/assumptions.md)<br/>[`AGENTS.md`](AGENTS.md) | [`scripts/verify_doc_numbers.py`](scripts/verify_doc_numbers.py)<br/>[`scripts/verify_results.py`](scripts/verify_results.py) | [`results/official/VERIFY.md`](results/official/VERIFY.md) *(285 ô số liệu, 0 lệch)* |

---

## 4. Kiến trúc hệ thống & Thiết lập công bằng

### 4.1. Cấu trúc package `src/flashsale/`
- `adapters/`: Giao diện kết nối, quản lý giao dịch và truy vấn đồng nhất cho MySQL, MongoDB và TiDB (bảo toàn đúng ngữ nghĩa riêng của từng hệ).
- `workload/`: Bộ sinh tải Flash-sale theo phân phối xếp hạng Zipf (`θ ∈ {0; 0,3; 0,5; 0,7; 0,9}` và chế độ *"một món"* qua hoán vị cố định theo `seed`), định tuyến kho (`uniform`, `single-warehouse`, đơn nhiều kho), backoff lũy thừa khởi điểm `10 ms` (tối đa `5` lần thử lại).
- `transactions/`: Nghiệp vụ `New-Order` (1–5 mặt hàng với bốn phương pháp: *đọc rồi ghi đè* `p0`, *trừ có điều kiện* `p1`, *chia slot* `p2`, *chia slot kèm điều tiết* `p3`, tách riêng biến *cấp mã đơn theo lô*) và `Payment` tách biệt khỏi cơ chế kết nối.
- `e1_ddl.py` & `migration.py`: Mô-đun phát lệnh DDL gốc dưới tải, lấy mẫu `performance_schema.metadata_locks`, chạy chuyển đổi dữ liệu lịch sử theo ba chiến lược (`eager`, `batch`, `lazy`) kết hợp giao dịch đọc `"Xem đơn cũ"` và kiểm định 6 điều kiện chuyển đổi.
- `benchmark/`: Tiến trình sinh tải đa worker (vòng đóng & vòng mở), tách riêng `30 s` khởi động (*warmup*) và `60 s` đo chính thức, xuất `tps_per_second.csv`, độ trễ `p50/p95/p99` và chỉ số tài nguyên.
- `validation/`: Kiểm chứng độc lập **ba luật tồn kho** (*không âm kho*, *đối soát khớp sổ sách* từ `order_line`, *không trùng đơn* theo `request_id`) bằng cả validator Python lẫn truy vấn/aggregation kiểm chéo trên DBMS (`doc_reconciliation`).
- `data/`: Khởi tạo lược đồ 9 bảng/collection TPC-C, nạp dữ liệu (`W = 10` ở Mục 2.2–2.4 & 2.6; `W = 12` ở Mục 2.5; `100.000` mặt hàng/kho), lưu snapshot và khôi phục sạch trước mỗi lần chạy.

### 4.2. Hạ tầng và độ bền dữ liệu ngang nhau (Mục 2.1.3)

| Thành phần | Hạ tầng AWS chính thức (Mục 2.2–2.5) | Docker Compose (Mục 1.4 & sơ bộ Mục 2.6) | Cấu hình bộ nhớ đệm & Độ bền giao dịch |
| :--- | :--- | :--- | :--- |
| **MySQL 8.4.8** | `m6i.8xlarge` (giới hạn `24 vCPU / 60 GiB`) | `8 vCPU / 16 GiB` (`:13306`) | Buffer pool `3 GiB` (`baseline-tuned`), `innodb_flush_log_at_trx_commit = 1`, `sync_binlog = 1`. |
| **MongoDB 8.0.20** | `m6i.8xlarge` (giới hạn `24 vCPU / 60 GiB`) | `8 vCPU / 16 GiB` (`:27018`) | Replica Set 1 nút `flashsale`, WiredTiger cache `3 GiB`, `readConcern: "snapshot"`, `writeConcern: {w: "majority", j: true}`, `nofile = 64000`. |
| **TiDB v8.5.7** | TiDB `c6i.4xlarge` (`16 vCPU`) + PD `c6i.large` (`2 vCPU`) + `3 ×` TiKV `m6i.large` (`2 vCPU/8 GiB`) = `24 vCPU / 60 GiB` | `1 PD + 1 TiDB + 3 TiKV` (tổng `8 vCPU / 16 GiB`, SQL `:14000`, PD `:12379`) | Block cache `1 GiB × 3 TiKV = 3 GiB`, đồng bộ nhật ký Raft mặc định, giao dịch `pessimistic`, `rf = 1` (và `rf = 3` ở Mục 2.5.3). |
| **Máy tạo tải** | VM riêng `c6i.4xlarge` (`16 vCPU`), EBS `gp3` | Chạy trên `c6i.4xlarge` / máy dev (ghi nhãn *sơ bộ*) | Đa tiến trình Python 3.12 (CPU máy tải thực đo `27%` MySQL, `67%` MongoDB giao dịch, `78%` MongoDB nhúng, `16%` TiDB). |

---

## 5. Hướng dẫn Cài đặt, Chạy Demo & Vận hành Benchmark

### 5.1. Thiết lập môi trường (Ubuntu 24.04 LTS / WSL2)

Yêu cầu máy ảo `x86_64` có Python 3.12, `venv`, Docker Engine và Docker Compose V2 (khuyến nghị `≥ 12 vCPU, 20 GiB RAM` khi nạp dataset đầy đủ `W = 10`):

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv git

# Nếu máy ảo chưa cài Docker Engine & Compose V2 (tách riêng bước cần quyền quản trị):
sudo bash scripts/bootstrap-docker.sh --install
sudo usermod -aG docker "$USER"   # đăng nhập lại sau lệnh này
```

Khởi tạo môi trường ảo Python, chạy unit test và kiểm tra trạng thái Docker:

```bash
bash scripts/setup.sh
source .venv/bin/activate
flashsale doctor
```

### 5.2. Thực thi các kịch bản Demo trực quan (Mục 1.4, 2.5 & 2.6)

Thực hiện trên máy cá nhân có Docker Desktop (chỉ bật **1 hệ quản trị tại một thời điểm**):

```bash
# 1. Demo Mục 1.4 / Phụ lục A.8 trên MongoDB 8.0.20 (Compass: mongodb://127.0.0.1:27018/?directConnection=true)
docker compose -f docker/compose.mongo.yml up -d
docker exec -i flashsale-mongo-mongo-1 mongosh --quiet < scripts/demo/demo_mongo_1.4.js
docker compose -f docker/compose.mongo.yml stop

# 2. Demo Mục 1.4 / Phụ lục B.8 & Mục 2.5 (tách Region 3 TiKV) trên TiDB v8.5.7
#    Workbench: 127.0.0.1:14000 | TiDB Dashboard: http://127.0.0.1:12379/dashboard
docker compose -f docker/compose.tidb.yml up -d
# -> Mở scripts/demo/demo_tidb_1.4.sql hoặc xem docs/huong-dan-quay-demo-2.5.md & docs/demo-ui-2.6.md
docker compose -f docker/compose.tidb.yml stop
```

### 5.3. Kiểm tra nhanh một hệ DBMS (Integration Test & Smoke Benchmark)

Thay `mysql` bằng `mongo` hoặc `tidb` tùy hệ cần kiểm tra:

```bash
flashsale start mysql
flashsale status mysql
FLASHSALE_TEST_ENGINE=mysql python -m pytest -m integration -q
flashsale smoke mysql
flashsale stop mysql
```

*(Có thể chạy `bash scripts/setup.sh --smoke-all` để tải các image đã pin SHA256 và chạy smoke tuần tự cả ba hệ).*

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

Mỗi lần chạy sinh `run_id` riêng và lưu đầy đủ `manifest.json`, `result.json`, `result.csv` cùng `tps_per_second.csv` vào `results/<run_id>/`.

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
# Chạy lưới thực nghiệm chính (thêm --dry-run để xem trước danh sách cấu hình):
bash scripts/run-matrix-2.1.sh mysql --dry-run
bash scripts/run-matrix-2.2.sh mysql --dry-run
bash scripts/run-matrix-2.3.sh --dry-run

# Chạy các kịch bản Đổi lược đồ trực tuyến (Mục 2.6 & Phụ lục D) và sinh biểu đồ cột + chuỗi thời gian:
bash scripts/run-2.4-e1.sh mysql
bash scripts/run-2.4-eager.sh mysql
bash scripts/run-2.4-batch.sh mysql
Q_LIST="5 25 50" bash scripts/run-2.4-lazy.sh mysql
python scripts/plot-2.4.py

# Vẽ biểu đồ Phần 2 và đối chiếu tự động 285 con số trong tài liệu thực nghiệm với CSV gốc:
python scripts/make_figures.py
python scripts/verify_doc_numbers.py
```

---

## 6. Tài liệu tham chiếu bổ sung trong Repo

- [`AGENTS.md`](AGENTS.md): Quy tắc kỹ thuật, bất biến thực nghiệm và an toàn vận hành.
- [`infra/aws/README.md`](infra/aws/README.md): Cấu hình Terraform, TiUP topology và quy trình vận hành hạ tầng AWS nhiều máy ảo.
- [`docs/assumptions.md`](docs/assumptions.md): Các quyết định thiết kế có chủ đích và khác biệt so với TPC-C chuẩn.
- [`docs/cau-lenh-dbms-2.1.md`](docs/cau-lenh-dbms-2.1.md): Tập câu lệnh SQL / MongoDB mẫu giải thích cơ chế giao dịch và truy vấn đối soát.
