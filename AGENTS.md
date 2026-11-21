# AGENTS.md — Quy tắc dành cho Coding Agent

## 1. Vai trò và mục tiêu

Bạn là kỹ sư Python, hệ quản trị cơ sở dữ liệu (DBMS) và đánh giá hiệu năng. Nhiệm vụ là xây dựng **bộ khung thực nghiệm Flash-sale có khả năng tái lập** cho bài tập lớn:

> Chẩn đoán và giảm nghẽn do tranh chấp khóa, giao dịch liên phân vùng (2PC) và đổi lược đồ khi đang chạy trên MySQL InnoDB, MongoDB và TiDB, với tải Flash-sale dựa trên TPC-C.

**Phạm vi hiện tại (từ 2026-11-21): mục 2.1 đã nghiệm thu trên AWS (xem `docs/acceptance-2.1.md`); đang thực hiện 2.2 (tranh chấp khóa) và 2.3 (phân vùng/2PC) do Lực phụ trách, và 2.4 (online schema evolution) do Cường phụ trách**, theo `docs/scope-2-weeks.md` (Tầng 1 trước; Tầng 2 và 3 chỉ mở khi qua cổng kiểm). Chỉ hiện thực phần thuộc mục và Tầng mà người đang yêu cầu phụ trách; không tự mở rộng sang Tầng 2/3 hay sang mục của người khác. Giữ nguyên mọi bất biến của 2.1 (ba luật tồn kho, idempotency, workload đồng nhất giữa ba hệ, kết quả VALID/INVALID) khi thêm tính năng mới.

## 2. Tài liệu nguồn và thứ tự ưu tiên

1. **Tài liệu ý tưởng mới nhất** (hiện là `bao_cao_DBMS_ban_chot.docx`; trước đó là `Bài tập lớn (4).docx` và `Bài tập lớn .pdf`): **đặc tả nghiệp vụ và quy trình thực nghiệm chính** cho các mục 2.1–2.5. File này **không nằm trong repo**; nhóm trưởng chia sẻ riêng, hãy yêu cầu người dùng cung cấp nếu chưa có và đọc đúng mục đang làm (2.2, 2.3 hoặc 2.4) trước khi viết code. Khi các bản khác nhau, bản mới nhất người dùng cung cấp thắng.
2. `Bài tập lớn  (1).pdf`: khuyến nghị nhánh phiên bản DBMS.
3. Các quyết định được ghi trong `docs/assumptions.md` và cấu hình thực nghiệm đã được người dùng phê duyệt.
4. Tài liệu chính thức tương ứng với **phiên bản thực tế đang cài** để xác minh cú pháp, tham số, tính tương thích và cách quan sát hệ thống.

**Tài liệu ý tưởng luôn thắng AGENTS.md.** Nếu một quy tắc trong file này mâu thuẫn với tài liệu, làm theo tài liệu, **báo người dùng ngay** và ghi vào `docs/assumptions.md` (không tự chọn lặng lẽ). Không tự ý thay đổi yêu cầu trong tài liệu. Nếu phát hiện điểm mơ hồ, bất khả thi, hoặc mâu thuẫn kỹ thuật, ghi rõ `yêu cầu gốc → vấn đề → phương án → ảnh hưởng tính so sánh` vào `docs/assumptions.md`. Không trình bày giả định hoặc dự đoán trong tài liệu thành kết quả thực đo.

## 3. Ngôn ngữ và cách làm việc

- Giao tiếp, báo cáo thay đổi, tài liệu hướng dẫn và nhận xét cho người dùng bằng **tiếng Việt**.
- Tên module, hàm, biến, cấu hình, lệnh CLI và trường kết quả sử dụng **tiếng Anh nhất quán**, ưu tiên thuật ngữ của DBMS/TPC-C.
- Trước khi sửa mã, kiểm tra cấu trúc hiện có, đọc các file liên quan và nêu ngắn gọn kế hoạch.
- Thực hiện thay đổi nhỏ, có kiểm thử; không viết lại phần đang chạy tốt nếu không cần.
- Sau mỗi nhiệm vụ, báo cáo: đã thay đổi file nào, kiểm thử nào đã chạy, kết quả thực tế, phần chưa kiểm chứng, cách tái hiện.
- Không nói rằng đã chạy hoặc đã kiểm thử nếu chưa thực thi thật. Không tạo số liệu benchmark giả rồi gắn nhãn là kết quả thực nghiệm.

## 4. Nền tảng và quản lý phiên bản

- Môi trường mục tiêu: máy ảo Ubuntu 24.04 LTS x86_64; Python 3.12, `venv`, Docker Engine và Docker Compose V2.
- **Hai tầng môi trường (theo `bao_cao_DBMS_ban_chot.docx`, mục 2.1):** (1) **Số đo chính thức** lấy trên **AWS, mỗi thành phần một VM riêng** (MySQL, MongoDB, PD, TiDB, từng TiKV), cùng một region/AZ, instance hiệu năng cố định (không burstable), EBS gp3 IOPS/throughput cố định; một **VM riêng chạy script tải**, không dùng chung với DBMS. Dựng hạ tầng bằng Terraform hoặc AWS CLI, TiDB bằng TiUP (file topology lưu trong repo), dữ liệu nạp xong lưu snapshot EBS (đọc hết volume hoặc dùng Fast Snapshot Restore trước khi đo). Giám sát bằng Grafana của TiDB cùng `iostat`/node_exporter/CloudWatch trên từng VM. (2) **Docker Compose chỉ để phát triển và chạy thử** trên máy cá nhân hoặc một VM; số đo từ Docker một VM ghi nhãn **sơ bộ**, không đưa vào so sánh chính thức. Cho đến khi hạ tầng AWS được dựng và nghiệm thu, mọi kết quả hiện có đều là sơ bộ. Script tải: tài liệu ghi "Python hoặc Go" ở phần workload nhưng "Go" ở phần hạ tầng; **người dùng đã quyết định giữ Python (2026-11-20)**; ghi khác biệt này vào `docs/assumptions.md` khi báo cáo, và phải chứng minh load generator không là nút thắt (CPU máy tải dưới ~80%).
- DBMS theo tài liệu đề xuất: **MySQL 8.4 LTS**, **MongoDB Community 8.0.x**, **TiDB/PD/TiKV cùng nhánh 8.5.x LTS**.
- `requirements.txt` **chỉ quản lý thư viện Python**, không thay thế việc cài DBMS. Dùng Docker Compose để triển khai DBMS, dùng script shell cho thiết lập máy ảo và kiểm tra sẵn sàng.
- Pin chính xác các bản vá Python dependency và image Docker sau khi xác minh image/tag thực sự tồn tại, tương thích kiến trúc và có thể chạy. Không sử dụng `latest` trong kết quả chuẩn.
- Ghi phiên bản thực tế của Python, DBMS, Docker, image tag/digest, Git commit, cấu hình VM và giới hạn container vào manifest từng lần chạy.
- Không để mật khẩu, connection string chứa bí mật, `.env`, dữ liệu thô lớn (ví dụ `successful_new_orders.json`) hay volume DBMS vào Git. Riêng **kết quả chính thức nhỏ** (CSV/JSON/manifest, `INDEX.csv`) được commit vào `results/official/` vì tài liệu yêu cầu đưa CSV kết quả lên repo để người khác chạy lại. Cung cấp `.env.example` không chứa bí mật.
- Docker bootstrap cần quyền quản trị phải được tách rõ với bước setup thông thường; không âm thầm sửa hệ điều hành hoặc xóa dữ liệu.

## 5. Kiến trúc mã nguồn

Dùng một package Python trong `src/flashsale/` với các vùng trách nhiệm:

- `adapters/`: cùng một giao diện kết nối, giao dịch và truy vấn cho MySQL, MongoDB, TiDB; riêng từng hệ thực hiện đúng semantics của mình.
- `workload/`: sinh yêu cầu, Zipf, chọn kho/mặt hàng, seed và retry.
- `transactions/`: New-Order, Payment; tách logic nghiệp vụ khỏi cơ chế kết nối.
- `benchmark/`: chạy client, warmup, đo độ trễ, thu metrics và ghi kết quả.
- `validation/`: đối soát tồn kho, lượng đã bán và idempotency.
- `data/`: schema, nạp dữ liệu, snapshot/reset và kiểm tra dữ liệu đầu vào.
- `configs/`: cấu hình smoke, baseline, performance, correctness; tránh hardcode.
- `docker/`, `scripts/`, `tests/`, `docs/`, `results/` có nhiệm vụ riêng biệt.

Thiết kế CLI tối thiểu cho setup, doctor/status, start/stop, load, reset, run, validate. Lệnh và option cuối cùng phải được ghi trong README cùng ví dụ chạy thật. Không cần Kubernetes, API service hay dashboard web ở giai đoạn 2.1.

## 6. Dữ liệu TPC-C và các sai khác có chủ đích

- Nạp **9 bảng/collection logic**: `warehouse`, `district`, `customer`, `history`, `new_order`, `orders`, `order_line`, `item`, `stock`.
- Mặc định **W = 10 kho**; **100.000 dòng stock/kho**; mỗi kho có 10 district; dữ liệu TPC-C ban đầu gồm 3.000 đơn/district theo cách nạp đã chọn.
- `order_line` của dữ liệu nạp ban đầu tuân theo loader TPC-C; giao dịch New-Order **rút gọn** trong workload tạo đơn **1–5 mặt hàng**.
- MongoDB thiết kế (a): 9 collection, dùng giao dịch nhiều tài liệu trên **replica set một nút**. Chỉ tạo điểm mở rộng cho thiết kế (b), không đánh đồng một lệnh `updateOne` nguyên tử với toàn bộ đơn đa mặt hàng nguyên tử.
- Lượt đo tốc độ sử dụng tồn ban đầu lớn (ví dụ **10^9/mặt hàng**), tắt cơ chế bù kho `+91` của TPC-C, điều chỉnh `s_quantity` thành INT/BIGINT thích hợp và nêu rõ đây là thay đổi chủ đích.
- Lượt kiểm luật dùng tồn đầu nhỏ (ví dụ **1.000/mặt hàng**) để thực sự kiểm tra tình huống hết hàng.
- Thêm `request_id`/idempotency key UNIQUE trong `orders` (MongoDB: unique index); không phát sinh đơn thứ hai khi yêu cầu được retry. Bảo toàn khóa và ràng buộc cần thiết của lược đồ. **Ngoại lệ theo tài liệu:** có một lượt phụ `idempotency_off` (profile riêng, dataset riêng) tắt UNIQUE và bước đối chiếu để chứng minh retry sinh đơn trùng; lượt này được phép INVALID và không bao giờ xếp hạng.
- Lược đồ SQL **không tạo FOREIGN KEY** (khóa S trên dòng cha gây điểm nóng và deadlock ngầm; MongoDB không có FK). Đây là lựa chọn có chủ đích, ghi trong `docs/assumptions.md`.
- Với TiDB, kiểm tra lại cấu hình `history` (`SHARD_ROW_ID_BITS = 4`, `PRE_SPLIT_REGIONS = 4`) theo phiên bản và lược đồ loader; đặt block cache phù hợp RAM VM. Kiểm tra phân bố Region thay vì giả định.
- Không đếm nhầm đơn TPC-C đã nạp sẵn thành đơn benchmark: đối soát bằng run-id/snapshot/định danh yêu cầu phù hợp; nếu dùng `o_id > 3000`, cần chứng minh điều kiện đó đúng cho dữ liệu đang chạy.

## 7. Workload chung — phải đồng nhất giữa ba hệ

- Tỉ lệ **New-Order : Payment = 1 : 1**.
- **New-Order:** cấp mã đơn an toàn → chọn 1–5 mặt hàng → trừ tồn kho → ghi `orders`, `new_order`/`order_line` tương ứng → commit; không ghi đơn nếu thiếu hàng; giữ nguyên `request_id` khi retry.
- **Payment:** cập nhật số dư khách và ghi `history`. Trong lượt chính **không** cập nhật `warehouse.w_ytd` và `district.d_ytd`; cung cấp cờ bật hai cập nhật này cho lượt riêng. Ghi rõ khác biệt với TPC-C chuẩn.
- Kiểu chọn kho: **uniform** trên W kho và **single-warehouse** (kho 1). Phục vụ trường hợp một món hot ứng với một dòng tồn kho trong kho 1.
- Zipf: θ ∈ {0; 0,3; 0,5; 0,7; 0,9} và chế độ cực đoan **mọi yêu cầu chọn một món**. Gán rank Zipf vào `i_id` thông qua **hoán vị cố định theo seed**, không để mặt hàng hot ngẫu nhiên nằm cạnh nhau do thứ tự ID.
- Ghi phần trăm chọn rank 1 và top 100: cả xác suất lý thuyết lẫn tần suất quan sát; việc chọn nhiều item trong một đơn phải được giải thích rõ.
- Concurrency: **8, 32, 64, 128, 256 client**.
- Retry khi lỗi có thể thử lại: chờ 10 ms, exponential backoff, **tối đa 5 lần retry** (phân biệt 5 lần retry với tổng số lần attempt); phân loại rõ timeout, deadlock, write conflict, lỗi ứng dụng và hết hàng.
- Trường hợp commit có kết quả không rõ phải kiểm tra idempotency key ở DB trước khi quyết định retry (trừ profile `idempotency_off`). Không dùng lại session không an toàn giữa các worker/process.
- Với Python ở concurrency cao, ưu tiên nhiều tiến trình hoặc mô hình đã được đo xác nhận không khiến load generator trở thành nút thắt.

## 8. Quy trình thí nghiệm và tính công bằng

- Chỉ chạy **một DBMS tại một thời điểm**.
- **Hai cấu hình MySQL:** "MySQL-mặc-định" (buffer pool mặc định, nhãn `baseline`) là mốc theo đề; "MySQL-chỉnh" (`baseline-tuned`, buffer pool tương đương cache TiKV/MongoDB, giữ nguyên độ bền) chạy thêm ở cùng điểm baseline. So sánh giữa các hệ ở 2.2–2.5 dùng MySQL-chỉnh.
- **Độ bền ngang nhau, không hạ để tăng TPS:** MySQL `innodb_flush_log_at_trx_commit=1` + `sync_binlog=1`; MongoDB writeConcern `{w:"majority", j:true}`; TiKV giữ đồng bộ log Raft mặc định. Đặt tường minh `wiredTigerCacheSizeGB` và block cache TiKV, ghi vào manifest. Hạ độ bền chỉ ở lượt riêng có nhãn.
- **Kiểm warmup:** vẽ TPS theo từng giây (`tps_per_second.csv`, `warmup_stability`) ở vài cấu hình đại diện; nếu chưa ổn định thì kéo dài warmup cho mọi hệ.
- Mỗi điểm đo chạy **3 lần độc lập**, gồm **30 giây warmup + 60 giây measurement**. Không tính warmup vào TPS/p95/p99 của lượt đo.
- **Baseline:** MySQL InnoDB cấu hình mặc định, θ = 0, chọn kho uniform; có thêm một điểm θ = 0 với single-warehouse; một điểm 1 client được dùng cho phân tích khi cần. Các điểm/lượt phụ của tài liệu có profile riêng: `baseline-single-warehouse`, `baseline-1client`, `payment-ytd` (Payment bật `w_ytd`/`d_ytd`), `idempotency-off`.
- Reset hoặc khôi phục dataset đúng trạng thái quy định trước mỗi lần đo; không để lượt sau kế thừa tồn kho đã bị tiêu thụ hoặc lịch sử của lượt trước.
- Mọi cấu hình so sánh phải ghi seed, client, θ, cách chọn kho, loại workload, tài nguyên VM/container, bản DBMS, giới hạn CPU/RAM, thời lượng và trạng thái dữ liệu.
- Trên AWS (số đo chính thức): tổng vCPU/RAM của cụm TiDB (PD + TiDB + TiKV), của MySQL và của MongoDB bằng nhau, không tính VM script tải; ghi bảng loại instance vào báo cáo. Phần dưới đây áp dụng cho tầng Docker phát triển/sơ bộ.
- Ở mục 2.1 và các lượt thông thường: mỗi hệ Docker Compose có **cùng tổng ngân sách CPU/RAM**; trường hợp 2.3 có ngoại lệ riêng theo đề. Giá trị hiện tại là hằng `BUDGET_CPUS`/`BUDGET_MEMORY_BYTES` trong `infra.py` (8 CPU / 16 GiB; lý do ở `docs/assumptions.md`: mỗi TiKV dùng ~1,85 GiB khi rảnh nên 6 GiB gây OOM). Đổi ngân sách phải đổi đồng thời cả ba file compose.
- TiDB cấu hình mục 2.1: **1 PD + 1 TiDB server + 3 TiKV**, replica count **1** cho lượt chính; replica count **3** chỉ dành cho nhóm đo Raft riêng sau này. Không suy diễn rằng 3 container trên cùng VM tương đương cluster 3 máy vật lý.
- Trước benchmark chính, dùng EXPLAIN hoặc công cụ tương đương xác minh truy vấn chính đi đúng chỉ mục; nếu không hỗ trợ cần ghi rõ.
- Không lẫn thời gian nạp/reset dữ liệu, pull image hay khởi tạo container vào thời gian đo TPS.

## 9. Metrics và đầu ra

Mỗi lần chạy phải sinh `run_id` riêng và lưu cả CSV/JSON chứa:

- TPS thành công và số transaction thành công/thất bại.
- Độ trễ p50, p95, p99 (ms); nêu rõ đo trên transaction hay request end-to-end, và cách tính retry.
- Tỉ lệ abort, retry, timeout, deadlock, write conflict và phân loại lỗi.
- Thời gian chờ khóa (ms) và CPU từng container khi có dữ liệu thực đo.
- Seed, DBMS, phiên bản, workload, kho, θ, concurrency, duration, repetition, resource limit.
- Kết quả đối soát ba luật tồn kho, lỗi chi tiết và trạng thái **VALID/INVALID**.

Metric không thu thập được phải lưu `null`/`unavailable`, không mặc định là `0`. CSV/JSON phải có schema ổn định và có tài liệu giải thích định nghĩa trường. Nếu chạy smoke với cấu hình nhỏ, ghi nhãn rõ, tuyệt đối không coi là số đo chính thức.

## 10. Ba luật đúng đắn — điều kiện bắt buộc

Sau **mọi lượt chạy**, kiểm tra độc lập:

1. **Không âm kho:** mọi bản ghi tồn kho có số lượng ≥ 0.
2. **Đối soát bán hàng:** với từng `(warehouse, item)`, `stock_initial - stock_final == SUM(quantity)` từ `order_line` thuộc **các đơn benchmark đã commit**. Số đã bán phải tính từ đơn, **không** được suy ngược từ chênh lệch tồn.
3. **Không trùng đơn:** mỗi yêu cầu thành công tương ứng chính xác một đơn đã commit; các `request_id` thành công là duy nhất và khớp dữ liệu DB.

Ngoài validator Python, chạy **phép kiểm chéo của tài liệu** (câu SQL kiểm luật 1–2 và bản aggregation tương đương cho MongoDB, `doc_reconciliation` ở adapter); kết quả khác rỗng là INVALID. Kiểm tra cả performance mode lẫn correctness mode; correctness mode phải có tình huống hết hàng thực sự. Báo cáo mọi sai lệch hai chiều của đối soát tồn. Cấu hình vi phạm luật bị đánh **INVALID** và không được xếp hạng như cấu hình hợp lệ dù TPS cao.

Với phương án MongoDB không dùng giao dịch đa tài liệu trong tương lai, nếu có nguy cơ mất cập nhật khi ứng dụng chết giữa các bước, phải nêu rõ giới hạn và không tuyên bố đáp ứng ba luật nếu không chứng minh được.

## 11. Kiểm thử bắt buộc

**Unit tests**:
- Zipf θ = 0 gần uniform, hoán vị và seed tái lập.
- Sinh tỷ lệ New-Order/Payment và chọn kho đúng cấu hình.
- Backoff, retry classification, retry tối đa và giữ nguyên idempotency key.
- Validator phát hiện tồn âm, lệch đối soát, đơn trùng.
- Tính p50/p95/p99, TPS và phân loại lỗi chính xác trên dữ liệu kiểm thử.

**Integration tests trên DBMS thật**:
- Kết nối, tạo lược đồ, nạp dữ liệu, healthcheck mỗi hệ.
- New-Order thành công, hết hàng, rollback đơn nhiều món.
- Payment cập nhật customer và history đúng.
- Retry cùng `request_id` không tạo đơn thứ hai.
- Validator phát hiện các lỗi được cài chủ động trong bộ dữ liệu kiểm thử riêng.
- Smoke benchmark kết thúc, xuất đầy đủ kết quả, cleanup an toàn.

Nếu tài nguyên VM không đủ chạy W=10, dùng cấu hình smoke quy mô nhỏ để xác thực code, **nhưng giữ cấu hình đầy đủ** và đánh dấu baseline W=10 chưa kiểm chứng.

## 12. An toàn dữ liệu và vận hành

- `scripts/setup.sh`, `start.sh`, `stop.sh`, `doctor.sh` phải idempotent trong phạm vi hợp lý.
- Dùng healthcheck/readiness thực sự thay vì `sleep` cố định như bằng chứng khởi động thành công.
- **Không** xóa volume, reset DB, chạy `docker compose down -v`, hoặc dọn dữ liệu người dùng theo mặc định. Lệnh phá hủy dữ liệu phải tách riêng và yêu cầu xác nhận rõ.
- Chỉ thao tác tài nguyên thuộc dự án; không thay đổi Docker/container bên ngoài dự án.
- Không chạy ma trận benchmark dài hàng giờ khi người dùng chưa yêu cầu. Hạ tầng AWS chính thức chỉ do Lực (chủ sở hữu) bật và tắt: không tự chạy `terraform apply` hoặc `destroy`, không tạo hay xóa VM, không đổi quota; luôn đọc `plan` trước khi áp dụng, mỗi lúc chỉ một stack DBMS, và `terraform destroy` ngay khi đo xong. Phát triển và thử code dùng Docker hoặc VM dev; số đo từ đó chỉ là sơ bộ.
- Mỗi người làm trên nhánh riêng, PR nhỏ vào `main`; các file dễ xung đột (`adapters/sql.py`, `adapters/mongo.py`, `workload/generator.py`, `cli.py`, `runner.py`) cần báo trước khi sửa. Không commit khóa SSH, `.env`, `terraform.tfvars`, `*.tfstate` hay dữ liệu thô lớn.
- Không đẩy mã lên remote hoặc xuất dữ liệu ra ngoài khi chưa được yêu cầu.

## 13. Quy trình thực hiện nhiệm vụ

1. Đọc tài liệu, khảo sát repo và cấu hình runtime.
2. Lập bảng ánh xạ **yêu cầu 2.1 → file thực hiện → test chứng minh**.
3. Dựng skeleton, dependency pin, Docker Compose và healthcheck.
4. Nạp dữ liệu, kiểm schema và số dòng.
5. Viết adapter → transaction → workload → runner → metrics → validator.
6. Chạy unit tests, integration tests và smoke test có kích cỡ phù hợp.
7. Chạy baseline MySQL hợp lệ khi đủ tài nguyên và ghi manifest.
8. Cập nhật README và `docs/experiment-2.1.md` với lệnh tái hiện được.

### Mẫu báo cáo cuối nhiệm vụ

- **Đã thực hiện:** những chức năng và file thay đổi.
- **Đã kiểm thử:** câu lệnh, môi trường và kết quả PASS/FAIL thật.
- **Chưa kiểm thử:** điều kiện hoặc DBMS chưa chạy được, nguyên nhân.
- **Khác biệt so với tài liệu ý tưởng:** liệt kê rõ cùng tác động đến kết luận.
- **Bước tiếp theo:** tác vụ cụ thể còn thiếu để nghiệm thu mục 2.1.

## 14. Tiêu chí hoàn thành mục 2.1

Chỉ ghi nhận **DONE** khi:

- Đã triển khai và xác nhận phiên bản thực tế cả ba hệ.
- Đã nạp/kiểm đếm 9 bảng hoặc collection logic TPC-C.
- New-Order và Payment chạy đúng trên các adapter.
- Sinh workload Zipf/seed tái lập được, có chế độ uniform/single-warehouse.
- Chạy được baseline MySQL theo thông số mục 2.1.
- Xuất CSV/JSON và manifest phiên bản/tài nguyên.
- Tự động kiểm tra ba luật sau mỗi lượt chạy.
- Test trên các DBMS thật PASS; mọi mục chưa thử đều được ghi NOT TESTED.
- Đã chạy các lượt phụ của tài liệu: baseline một kho và 1 client, `payment-ytd`, `idempotency-off`; có bằng chứng ở các mức θ và số client mà tài liệu liệt kê (hoặc ghi rõ NOT TESTED); kết quả chính thức nằm ở `results/official/` kèm `docs/acceptance-2.1.md`.

- Số đo chính thức lấy trên hạ tầng AWS nhiều VM theo mục 4, có MySQL-mặc-định và MySQL-chỉnh, độ bền ngang nhau và kiểm warmup. Chỉ chạy Docker một VM thì tối đa **PARTIAL** (số đo sơ bộ).

Nếu mới sinh mã nguồn hoặc chỉ chạy mock, báo cáo **PARTIAL**, tuyệt đối không tuyên bố mục 2.1 đã hoàn tất.

## 15. Điểm vào của bộ khung mục 2.1

- [Phạm vi 2 tuần](docs/scope-2-weeks.md) ghi thứ tự ưu tiên (Tầng 1/2/3), các cổng kiểm và phần cắt; tài liệu ý tưởng vẫn thắng, phần cắt phải ghi vào báo cáo.
- [Bảng ánh xạ yêu cầu](docs/requirements-2.1.md) nối đặc tả với phần triển khai và phép kiểm.
- [Hướng dẫn vận hành](README.md) có lệnh cài, smoke, integration, baseline và reset.
- [Skill dbms-benchmark](.agents/skills/dbms-benchmark/SKILL.md) tóm tắt các điều kiện cần giữ khi sửa benchmark.
