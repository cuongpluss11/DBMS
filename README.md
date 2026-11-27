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

Kho mã nguồn này lưu trữ bộ khung thực nghiệm khả lập lại (**reproducible benchmark suite**), kịch bản kiểm chứng giao diện và toàn bộ dữ liệu bằng chứng gốc cho báo cáo chính thức **Phân tích và tối ưu hiệu năng giao dịch Flash-sale trên MySQL, MongoDB và TiDB**. Kế thừa lược đồ 9 bảng/collection của chuẩn **TPC-C**, nhóm xây dựng kịch bản tải **Flash-sale tùy biến** (không phải phép đo chuẩn TPC-C chính thức) để đối chiếu ba kiến trúc cơ sở dữ liệu dưới cùng ngân sách phần cứng, cùng bộ nhớ đệm (`3 GiB`) và cùng mức ghi bền dữ liệu xuống ổ đĩa:
- **RDBMS truyền thống:** **MySQL InnoDB 8.4.8 LTS** (hệ đối chứng).
- **NoSQL hướng tài liệu:** **MongoDB Community 8.0.20** (*MongoDB giao dịch* dùng giao dịch nhiều tài liệu trên Replica Set và *MongoDB nhúng* dùng tài liệu đơn hàng nhúng).
- **NewSQL phân tán:** **TiDB / TiKV / PD v8.5.7 LTS** (kiến trúc phân tách SQL – lưu trữ phân tán Multi-Raft và giao dịch hai pha 2PC).

> **Quy mô bằng chứng thực nghiệm:** **839 lượt đo chính thức trên hạ tầng AWS đa máy ảo** (Mục 2.2–2.5, ngân sách `24 vCPU / 60 GiB RAM` mỗi hệ), **159 lượt đo `VALID` cho mở rộng đổi lược đồ** trên AWS Docker `c6i.4xlarge` (Mục 2.6 & Phụ lục D, nhãn *sơ bộ*) và **152 lượt đo nghiệm thu nền** (Mục 2.1 & Phụ lục C.1.1). Mọi con số trong báo cáo đều truy xuất trực tiếp về CSV/JSON trong [`results/official/`](results/official/) và được đối chiếu tự động qua [`scripts/verify_doc_numbers.py`](scripts/verify_doc_numbers.py) (**285 ô số liệu, 0 sai lệch**; xem [`results/official/VERIFY.md`](results/official/VERIFY.md)).

---

## 2. Tổng hợp kết quả nghiên cứu & Ma trận đánh đổi (Mục 2.7)

### 2.1. Tổng hợp trả lời các câu hỏi nghiên cứu (Bảng 2.7.1)

| Câu hỏi nghiên cứu | Kết quả thực nghiệm chính |
| :--- | :--- |
| **Nghẽn do đâu?** *(Mục 2.2)* | Nghẽn xuất phát trực tiếp từ **điểm nóng ghi** chứ không đơn thuần từ độ lệch Zipf `θ`: chế độ *"một món"* làm thông lượng ở `64 client` sụt **2,8–3,7 lần** trên cả ba hệ và tăng client từ `64` lên `256` không làm tăng đáng kể số đơn đặt hàng thành công (trên *MongoDB giao dịch*, `72%` yêu cầu `New-Order` ở `256 client` thất bại, phần TPS tăng chủ yếu từ `Payment`). Hai cơ chế đo trực tiếp là **chờ khóa dòng trên MySQL** (`97%` thời gian client) và **hủy rồi thử lại trên MongoDB** (`75.207` lỗi `write_conflict`/lượt, tỉ lệ retry `40,4%`); trên TiDB cơ chế được suy ra là xếp hàng ở Region nóng. |
| **Có bán vượt tồn kho không?** *(Mục 2.3)* | Trong **839 lượt đo chính thức trên AWS**, mọi phương pháp có bảo vệ (*trừ có điều kiện, chia slot, chia slot kèm điều tiết*) đều thỏa mãn cả ba luật (*không âm kho, khớp sổ, không trùng đơn*); **14 lượt `INVALID`** đều thuộc cách *đọc rồi ghi đè* (7 trên MySQL, 7 trên TiDB). *MongoDB giao dịch* không mất cập nhật ở 21 lượt *đọc rồi ghi đè* (bằng chứng gián tiếp qua `write_conflict`). Khi tiêm lỗi giết tiến trình, TiDB không vi phạm ở **76 và 95 lần trúng cửa sổ commit**; MySQL và MongoDB mới đo sơ bộ trên Docker. *MongoDB nhúng* vi phạm luật khớp sổ nếu ứng dụng chết giữa bước trừ kho và ghi đơn. |
| **Cách nào giảm nghẽn mà vẫn đúng?** *(Mục 2.4)* | **Chia slot tồn kho (`27` slot) kèm cấp mã đơn theo lô (`50` mã)** là đòn bẩy hiệu quả nhất, tăng TPS **5,9–8,5×** (**tính riêng đơn đặt thành công: 6,4–8,5×**) so với *trừ có điều kiện* (`64 client`, *"một món"*) và giữ `VALID` trên mọi lượt đo. **Cấp mã đơn theo lô** đóng góp lợi ích độc lập (tăng tới **2,5×** trên TiDB ở `θ = 0,9`). Ngược lại, **điều tiết thích ứng** chưa cho thấy lợi ích tổng quát: trên MongoDB giảm `p99` rõ ở `256 client`, còn trên MySQL phụ thuộc ngưỡng và ở ngưỡng cao chỉ ngang *chia slot*. |
| **Khi nào chi phí vượt lợi ích?** *(Mục 2.4)* | Trên MySQL từ mức tải `≥ 100%` với ngưỡng đặc tả `500 ms`, điều tiết làm TPS giảm **22–48%** (từ chối `21–51%` yêu cầu) do đặt ngưỡng thấp hơn độ trễ tự nhiên; khi nâng ngưỡng lên `1.000–2.000 ms` thì hiệu năng gần tương đương *chia slot*. Với cơ chế riêng từng hệ: trên MySQL, `Stored Procedure` tăng `69%` cả TPS lẫn đơn đặt, còn `NOWAIT` tăng `72%` TPS nhưng làm số đơn đặt thành công giảm `10%`; **MongoDB nhúng** đạt TPS gấp khoảng **9,9×** *MongoDB giao dịch* (**đơn đặt thành công gấp 15,2×**) nhưng đánh đổi tính nguyên tử giữa kho và đơn. |
| **Thêm TiKV, replication giúp gì và tốn gì?** *(Mục 2.5)* | Với hot SKU, bổ sung từ `1` lên `3` TiKV đơn lẻ chỉ tăng **`1,22–1,29×`** (qua hai lần dựng cụm), nhưng khi kết hợp **chia slot tồn kho** đạt hiệu ứng tương tác **`3,44–3,80×`**. Nâng hệ số sao chép từ `rf = 1` lên `rf = 3` (chu trình đảo thứ tự `rf=3 → rf=1 → rf=3`) làm giảm **25–47% TPS** ở các tải ghi lan rộng trên cấu hình `2 vCPU/TiKV`, trong khi ở tải hot SKU không chia slot biến động lớn nên chưa đủ cơ sở kết luận. Với đơn nhiều kho (`2–4` kho), chưa quan sát được chi phí liên phân vùng vượt khỏi mức nhiễu trong 3 lần lặp. |
| **Đổi lược đồ khi đang bán thế nào ít chặn nhất?** *(Mục 2.6 & Phụ lục D)* | `ADD COLUMN INSTANT` trên MySQL không gây treo khi tải thường (`0,05 s`), nhưng **1 giao dịch đọc mở `60 s`** làm treo cứng toàn bảng **57 s**; đặt `lock_wait_timeout = 3` kèm retry giảm đóng băng còn **2 s** (`2,54×` TPS). TiDB Online DDL không đóng băng (`0 s`); MongoDB không rơi về `0 TPS` nhưng giảm TPS khi giữ snapshot dài. Khi chuyển ~3 triệu dòng cũ ở `q = 25%`, **Batch lô `1.000`** giữ TPS cao nhất (TiDB ở tải cao gần ngang `Eager`: `710` vs `709 TPS`) và cắt **25,5×** gai `p99` của `Eager` trên MySQL; `Eager` xong nhanh nhất nhưng làm MySQL giảm `53,0%` TPS ở tải chuẩn (`62,8%` ở tải cao); `Lazy` [8] chỉ hơn `Batch` trên MySQL ở `q = 5%`. *(Số đo sơ bộ trên Docker).* |

### 2.2. Ma trận đánh đổi cho bài toán triển khai thực tế (Bảng 2.7.2)

| Kịch bản vận hành | Khuyến nghị kiến trúc | Đánh đổi tương ứng |
| :--- | :--- | :--- |
| **Hot SKU yêu cầu đúng đắn tuyệt đối** | Áp dụng cập nhật có điều kiện kết hợp **chia slot tồn kho** và **cấp mã đơn theo lô** trong cùng giao dịch nguyên tử. | Phức tạp hơn khi gần hết hàng (cần tìm slot còn hàng). |
| **Ưu tiên tốc độ tối đa trên MongoDB** | Sử dụng **MongoDB nhúng**, bỏ giao dịch nhiều tài liệu. | Có nguy cơ lệch tồn kho/đơn hàng (vi phạm luật khớp sổ) nếu ứng dụng chết giữa bước trừ kho và ghi đơn. |
| **Mở rộng ngang TiDB** | Tối ưu mô hình dữ liệu (**chia slot**, `AUTO_RANDOM`) **trước**, sau đó mới bổ sung nút TiKV. | Cấu hình chịu lỗi `rf = 3` tiêu tốn khoảng `25–47%` thông lượng ghi ở cấu hình `2 vCPU/TiKV`. |
| **Đổi lược đồ bảng lớn khi đang có tải** | Thêm cột bằng cơ chế ít chặn nhất (`INSTANT` / Online DDL, kèm `lock_wait_timeout = 3` trên MySQL), sau đó chuyển dữ liệu cũ bằng **Batch lô `1.000`**. | Thời gian hoàn tất chuyển dữ liệu chậm hơn `Eager`, đổi lại ít làm sụt TPS và `p99` hơn. |

---

## 3. Bản đồ Ánh xạ Từng Mục Báo cáo ↔ Bằng chứng Thực nghiệm trong Repo

Bảng dưới đây nối trực tiếp từng mục trong báo cáo chính thức và các **Phụ lục A, B, C, D** tới đúng tệp dữ liệu gốc (`INDEX.csv`, `result.json`), biểu đồ và kịch bản tái lập:

| Mục trong Báo cáo chính & Phụ lục | Tài liệu phân tích & Kịch bản Demo | Mã nguồn & Script tái lập | Bằng chứng Dữ liệu gốc (`results/official/`) & Biểu đồ |
| :--- | :--- | :--- | :--- |
| **Phần 1 — Mục 1.4 & Phụ lục A.7–A.8, B.7–B.8** *(Cài đặt, cấu hình & 12 demo cơ bản MongoDB/TiDB)* | [`docs/demo-ui-1.4.md`](docs/demo-ui-1.4.md) | [`scripts/demo/demo_mongo_1.4.js`](scripts/demo/demo_mongo_1.4.js)<br/>[`scripts/demo/demo_tidb_1.4.sql`](scripts/demo/demo_tidb_1.4.sql)<br/>[`docker/compose.mongo.yml`](docker/compose.mongo.yml)<br/>[`docker/compose.tidb.yml`](docker/compose.tidb.yml) | Kịch bản kiểm chứng phiên bản, Replica Set / 5 nút TiDB, CRUD, chống âm kho, ACID (`COMMIT`/`ROLLBACK`), Region & Online DDL trên **Compass** và **MySQL Workbench**. |
| **Phần 2 — Mục 2.1 & Phụ lục C.1.1** *(Workload tùy biến, 3 luật tồn kho, hạ tầng AWS, `EXPLAIN` & độ ổn định warmup)* | [`docs/acceptance-2.1.md`](docs/acceptance-2.1.md)<br/>[`docs/experiment-2.1.md`](docs/experiment-2.1.md)<br/>[`docs/trien-khai-2.1.md`](docs/trien-khai-2.1.md)<br/>[`docs/pilot-aws-vs-docker.md`](docs/pilot-aws-vs-docker.md)<br/>[`docs/pilot-disk-sensitivity.md`](docs/pilot-disk-sensitivity.md) | [`src/flashsale/workload/`](src/flashsale/workload/)<br/>[`src/flashsale/validation/`](src/flashsale/validation/)<br/>[`infra/aws/`](infra/aws/)<br/>[`scripts/run-matrix-2.1.sh`](scripts/run-matrix-2.1.sh) | • Mốc nền `12 vCPU` (C.1.1): [`results/official/2.1-aws/INDEX.csv`](results/official/2.1-aws/INDEX.csv), [`SUMMARY.md`](results/official/2.1-aws/SUMMARY.md)<br/>• Đối chứng Docker & EBS IOPS: [`pilot-aws-vs-docker/`](results/official/pilot-aws-vs-docker/), [`pilot-disk-sensitivity/`](results/official/pilot-disk-sensitivity/)<br/>• Kiểm tra chỉ mục TiDB: [`results/official/explain-tidb.json`](results/official/explain-tidb.json)<br/>• Phân tích warmup `30 s`: [`warmup-analysis-mysql.md`](results/official/warmup-analysis-mysql.md), [`warmup-analysis-mongo.md`](results/official/warmup-analysis-mongo.md), [`warmup-analysis-tidb.md`](results/official/warmup-analysis-tidb.md) |
| **Phần 2 — Mục 2.2 & Phụ lục C.1.2–C.1.5** *(Chẩn đoán nghẽn Hot SKU theo `θ` và `8/64/256` client; Bảng 2.2.1 – 2.2.2)* | [`docs/experiment-2.2.md`](docs/experiment-2.2.md) | [`src/flashsale/transactions/`](src/flashsale/transactions/)<br/>[`scripts/run-matrix-2.2.sh`](scripts/run-matrix-2.2.sh) | • Tổng hợp chờ khóa & `write_conflict`: [`results/official/2.2-aws/CONTENTION.md`](results/official/2.2-aws/CONTENTION.md)<br/>• Dữ liệu CSV theo hệ: [`2.2-aws/mysql/`](results/official/2.2-aws/mysql/), [`2.2-aws/mongo/`](results/official/2.2-aws/mongo/), [`2.2-aws/mongo-t1-c256-postfix/`](results/official/2.2-aws/mongo-t1-c256-postfix/), [`2.2-aws/tidb3/`](results/official/2.2-aws/tidb3/)<br/>• Biểu đồ: [`fig1_t1_theta.png`](results/official/figures/fig1_t1_theta.png) ([`CSV`](results/official/figures/fig1_t1_theta.csv)) |
| **Phần 2 — Mục 2.3 & Phụ lục C.1.2, C.2** *(Kiểm chứng không oversell: `P0` đọc rồi ghi đè, giết tiến trình ngẫu nhiên, đối chứng âm & giới hạn MongoDB nhúng; Bảng 2.3.1 – 2.3.2)* | [`docs/fault-injection.md`](docs/fault-injection.md)<br/>[`docs/experiment-2.2.md`](docs/experiment-2.2.md)<br/>[`docs/demo-phan-2.md`](docs/demo-phan-2.md) | [`scripts/fault_kill_cycles.py`](scripts/fault_kill_cycles.py)<br/>[`tests/`](tests/) | • Lượt `P0` (`14 INVALID` MySQL/TiDB, `21 VALID` Mongo): [`2.2-aws/mysql/`](results/official/2.2-aws/mysql/), [`2.2-aws/tidb3/`](results/official/2.2-aws/tidb3/), [`2.2-aws/mongo/`](results/official/2.2-aws/mongo/)<br/>• Tiêm lỗi & đối chứng âm: [`results/official/fault-injection/`](results/official/fault-injection/) ([`tidb-kill-stockout.json`](results/official/fault-injection/tidb-kill-stockout.json), [`tidb-kill-orders.json`](results/official/fault-injection/tidb-kill-orders.json), [`tidb-kill-idempotency-off.json`](results/official/fault-injection/tidb-kill-idempotency-off.json), [`mysql-kill.json`](results/official/fault-injection/mysql-kill.json), [`mongo-kill.json`](results/official/fault-injection/mongo-kill.json), [`tidb-integration-pytest.txt`](results/official/fault-injection/tidb-integration-pytest.txt)) |
| **Phần 2 — Mục 2.4 & Phụ lục C.3.1–C.3.3** *(Chia slot `N=1..27`, cấp mã đơn theo lô, tải vòng mở & độ nhạy ngưỡng điều tiết, cơ chế riêng từng DBMS; Bảng 2.4.1 – 2.4.5)* | [`docs/experiment-2.2.md`](docs/experiment-2.2.md) | [`src/flashsale/transactions/`](src/flashsale/transactions/)<br/>[`scripts/run-matrix-2.2.sh`](scripts/run-matrix-2.2.sh)<br/>[`scripts/make_figures.py`](scripts/make_figures.py) | • Tải vòng mở & độ nhạy ngưỡng `500/1000/2000 ms`: [`2.2-aws/mysql-t3/`](results/official/2.2-aws/mysql-t3/), [`2.2-aws/mysql-p3sens/`](results/official/2.2-aws/mysql-p3sens/), [`2.2-aws/mongo-t3/`](results/official/2.2-aws/mongo-t3/), [`2.2-aws/mongo-t3-p2-postfix/`](results/official/2.2-aws/mongo-t3-p2-postfix/)<br/>• Biểu đồ & CSV: [`fig2_p1_to_p2.png`](results/official/figures/fig2_p1_to_p2.png), [`fig3_batch_effect.png`](results/official/figures/fig3_batch_effect.png), [`fig5_t3_p99.png`](results/official/figures/fig5_t3_p99.png), [`fig6_t4.png`](results/official/figures/fig6_t4.png) |
| **Phần 2 — Mục 2.5 & Phụ lục C.4.1–C.4.4** *(Ma trận `2×2` `1→3` TiKV qua 2 lần dựng cụm, đơn nhiều kho `2PC`, sao chép Raft `rf=3 ↔ rf=1`; Bảng 2.5.1 – 2.5.3 & Hình 2.5.1a–b)* | [`docs/experiment-2.3.md`](docs/experiment-2.3.md)<br/>[`docs/huong-dan-quay-demo-2.5.md`](docs/huong-dan-quay-demo-2.5.md) | [`src/flashsale/data/placement.py`](src/flashsale/data/placement.py)<br/>[`scripts/placement_summary.py`](scripts/placement_summary.py)<br/>[`scripts/run-matrix-2.3.sh`](scripts/run-matrix-2.3.sh) | • Phân bố Region & CPU TiKV: [`2.3-aws/PLACEMENT-2x2.md`](results/official/2.3-aws/PLACEMENT-2x2.md), [`SUMMARY-speedup.md`](results/official/2.3-aws/SUMMARY-speedup.md)<br/>• Hai lần dựng cụm `1` & `3` TiKV: [`tidb1/`](results/official/2.3-aws/tidb1/), [`tidb1-build2/`](results/official/2.3-aws/tidb1-build2/), [`tidb3/`](results/official/2.3-aws/tidb3/), [`tidb3-build2/`](results/official/2.3-aws/tidb3-build2/)<br/>• Nhóm Replication `R` & `R2`: [`tidb3-R/`](results/official/2.3-aws/tidb3-R/), [`tidb3-R2/`](results/official/2.3-aws/tidb3-R2/)<br/>• Biểu đồ: [`fig4_tidb_2x2.png`](results/official/figures/fig4_tidb_2x2.png), [`fig7_replication.png`](results/official/figures/fig7_replication.png), [`fig8_replication_order.png`](results/official/figures/fig8_replication_order.png), [`fig9_speedup_two_builds.png`](results/official/figures/fig9_speedup_two_builds.png) |
| **Phần 2 — Mục 2.6 & Phụ lục D.1–D.5** *(Đổi lược đồ trực tuyến: DDL gốc & MDL, `Eager / Batch / Lazy` tải chuẩn & tải cao, quét `q`; Hình 2.6.1 – 2.6.2 & Bảng/Hình D.1 – D.5)* | [`docs/report-2.6-and-appendix.md`](docs/report-2.6-and-appendix.md)<br/>[`docs/experiment-2.4.md`](docs/experiment-2.4.md)<br/>[`docs/demo-ui-2.6.md`](docs/demo-ui-2.6.md) | [`src/flashsale/e1_ddl.py`](src/flashsale/e1_ddl.py)<br/>[`src/flashsale/migration.py`](src/flashsale/migration.py)<br/>[`scripts/run-2.4-e1.sh`](scripts/run-2.4-e1.sh)<br/>[`scripts/run-2.4-eager.sh`](scripts/run-2.4-eager.sh)<br/>[`scripts/run-2.4-batch.sh`](scripts/run-2.4-batch.sh)<br/>[`scripts/run-2.4-lazy.sh`](scripts/run-2.4-lazy.sh)<br/>[`scripts/plot-2.4.py`](scripts/plot-2.4.py) | • `159/159` lượt `VALID`: [`2.4-e1/`](results/official/2.4-e1/), [`2.4-baseline/`](results/official/2.4-baseline/), [`2.4-eager/`](results/official/2.4-eager/), [`2.4-batch/`](results/official/2.4-batch/), [`2.4-lazy/`](results/official/2.4-lazy/), [`2.4-highload/`](results/official/2.4-highload/)<br/>• Biểu đồ Báo cáo chính: [`fig6_bar_e1_mdl.png`](docs/figures/2.4/fig6_bar_e1_mdl.png), [`fig6_bar_e2_strategies.png`](docs/figures/2.4/fig6_bar_e2_strategies.png)<br/>• Biểu đồ Phụ lục D: [`fig6_e1_mdl_freeze.png`](docs/figures/2.4/fig6_e1_mdl_freeze.png), [`fig6_e2_strategies.png`](docs/figures/2.4/fig6_e2_strategies.png), [`fig6c_e2_highload.png`](docs/figures/2.4/fig6c_e2_highload.png), [`fig6_bar_e3_q_sweep.png`](docs/figures/2.4/fig6_bar_e3_q_sweep.png), [`fig6b_e3_q_sweep.png`](docs/figures/2.4/fig6b_e3_q_sweep.png) |
| **Phần 2 — Mục 2.7.3 & Phụ lục C.6** *(Giới hạn nghiên cứu, đo kiểm soát `20 ↔ 24 vCPU` MySQL, xử lý `nofile = 64000` MongoDB & kiểm chứng số liệu tự động)* | [`docs/assumptions.md`](docs/assumptions.md)<br/>[`docs/citation-check.md`](docs/citation-check.md)<br/>[`AGENTS.md`](AGENTS.md) | [`scripts/verify_doc_numbers.py`](scripts/verify_doc_numbers.py)<br/>[`scripts/verify_results.py`](scripts/verify_results.py) | • Báo cáo đối soát `285` ô số liệu: [`results/official/VERIFY.md`](results/official/VERIFY.md)<br/>• Đo kiểm soát `20 → 24 → 20 vCPU` MySQL: [`results/official/2.3-aws/mysql-ctl/`](results/official/2.3-aws/mysql-ctl/), [`warmup-analysis-mysql-ctl.md`](results/official/warmup-analysis-mysql-ctl.md)<br/>• Đo lại MongoDB `256 client` sau nâng `nofile`: [`2.2-aws/mongo-t1-c256-postfix/`](results/official/2.2-aws/mongo-t1-c256-postfix/), [`2.2-aws/mongo-t3-p2-postfix/`](results/official/2.2-aws/mongo-t3-p2-postfix/) |

---

## 4. Kiến trúc hệ thống & Thiết lập công bằng

### 4.1. Cấu trúc package `src/flashsale/`
- `adapters/`: Giao diện kết nối, quản lý giao dịch và truy vấn đồng nhất cho MySQL, MongoDB và TiDB (bảo toàn đúng ngữ nghĩa riêng của từng hệ).
- `workload/`: Bộ sinh tải Flash-sale theo phân phối xếp hạng Zipf (`θ ∈ {0; 0,3; 0,5; 0,7; 0,9}` và chế độ *"một món"* qua hoán vị cố định theo `seed`), định tuyến kho (`uniform`, `single-warehouse`, đơn nhiều kho `1–4` kho), backoff lũy thừa khởi điểm `10 ms` (tối đa `5` lần thử lại).
- `transactions/`: Nghiệp vụ `New-Order` (`1–5` mặt hàng với bốn phương pháp: *đọc rồi ghi đè* `p0`, *trừ có điều kiện* `p1`, *chia slot* `p2`, *chia slot kèm điều tiết* `p3`, tách riêng biến *cấp mã đơn theo lô*) và `Payment` tách biệt khỏi cơ chế kết nối.
- `e1_ddl.py` & `migration.py`: Mô-đun phát lệnh DDL gốc dưới tải, lấy mẫu `performance_schema.metadata_locks`, chạy chuyển đổi dữ liệu lịch sử theo ba chiến lược (`eager`, `batch`, `lazy`) kết hợp giao dịch đọc `"Xem đơn cũ"` và kiểm định 6 điều kiện chuyển đổi.
- `benchmark/`: Tiến trình sinh tải đa worker (vòng đóng & vòng mở), tách riêng `30 s` khởi động (*warmup*) và `60 s` đo chính thức, xuất `tps_per_second.csv`, độ trễ `p50/p95/p99` và chỉ số tài nguyên.
- `validation/`: Kiểm chứng độc lập **ba luật tồn kho** (*không âm kho*, *đối soát khớp sổ sách* từ `order_line`, *không trùng đơn* theo `request_id`) bằng cả validator Python lẫn truy vấn/aggregation kiểm chéo trên DBMS (`doc_reconciliation`).
- `data/`: Khởi tạo lược đồ 9 bảng/collection TPC-C, nạp dữ liệu (`W = 10` ở Mục 2.2–2.4 & 2.6; `W = 12` ở Mục 2.5; `100.000` mặt hàng/kho), đặt chủ động Region/Leader trên TiDB (`placement.py`), lưu snapshot và khôi phục sạch trước mỗi lần chạy.

### 4.2. Hạ tầng và độ bền dữ liệu ngang nhau (Bảng 2.1.3)

| Hệ quản trị / Máy tải | Hạ tầng AWS chính thức (Mục 2.2–2.5) | Docker Compose (Mục 1.4 & sơ bộ Mục 2.6) | Cấu hình bộ nhớ đệm & Độ bền giao dịch |
| :--- | :--- | :--- | :--- |
| **MySQL 8.4.8 (InnoDB)** | `m6i.8xlarge`, giới hạn `24 vCPU / 60 GiB` | `8 vCPU / 16 GiB` (`:13306`) | Buffer pool `3 GiB`, `innodb_flush_log_at_trx_commit = 1`, `sync_binlog = 1` (đẩy nhật ký xuống đĩa mỗi lần chốt đơn). |
| **MongoDB 8.0.20** | `m6i.8xlarge`, giới hạn `24 vCPU / 60 GiB` | `8 vCPU / 16 GiB` (`:27018`) | Replica Set 1 nút `flashsale`, WiredTiger cache `3 GiB`, `readConcern: "snapshot"`, `{w: "majority", j: true}`, `nofile = 64000`. |
| **TiDB v8.5.7** | TiDB `c6i.4xlarge` (`16 vCPU/32 GiB`) + PD `c6i.large` + `3 ×` TiKV `m6i.large` (`2 vCPU/8 GiB`) = `24 vCPU / 60 GiB` | `1 PD + 1 TiDB + 3 TiKV` (tổng `8 vCPU / 16 GiB`, SQL `:14000`, PD `:12379`) | Block cache `1 GiB × 3 TiKV = 3 GiB`, đồng bộ nhật ký Raft mặc định, giao dịch `pessimistic`, lượt chính `rf = 1` (đo `rf = 3` ở Mục 2.5.3). |
| **Máy tải** | `c6i.4xlarge` (`16 vCPU`), EBS `gp3` | Chạy trên `c6i.4xlarge` / máy dev (ghi nhãn *sơ bộ*) | Script Python 3.12 đa tiến trình; CPU tối đa thực đo: `27%` (MySQL), `67%` (MongoDB giao dịch), `78%` (MongoDB nhúng), `16%` (TiDB). |

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

# Chạy các kịch bản Đổi lược đồ trực tuyến (Mục 2.6 & Phụ lục D) và sinh biểu đồ:
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
