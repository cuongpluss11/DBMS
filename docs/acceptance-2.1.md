# Nghiệm thu mục 2.1

Ngày chạy: 2026-11-19 và 2026-11-20. Môi trường: AWS EC2 `c6i.4xlarge` (16 vCPU, 32 GiB, đĩa gp3 100 GiB), Ubuntu 24.04 LTS x86_64, Docker 29.10.0, Compose 5.8.0, Python 3.12.3. Mỗi hệ chạy riêng một thời điểm với ngân sách container chung **8 CPU / 16 GiB** ([assumptions.md](assumptions.md)). Dữ liệu thô nằm ở [results/official/2.1/](../results/official/2.1/) (xem `INDEX.csv`, 51 lượt). Các lượt chạy ngày 2026-11-19 dùng Git commit `38dda58` (`main`); các lượt bổ sung ngày 2026-11-20 (profile `performance-theta*`, `performance-hot-item`, `baseline-concurrency`, idempotency-off trên MongoDB/TiDB, `validate-cli-output.json`) dùng commit `3a5aded` của nhánh `complete-2.1`, đã gồm phép kiểm chéo của tài liệu. Không có thay đổi chưa commit ở cả hai.

## Nghiệm thu trên AWS theo bản chốt: DONE, kèm giới hạn ghi rõ

Ngày chạy 2026-11-20 và 2026-11-21 trên AWS `us-east-1c`, mỗi thành phần một VM riêng, một VM tải riêng (Python), Ubuntu 24.04, một DBMS tại một thời điểm. Dữ liệu thô: [results/official/2.1-aws/](../results/official/2.1-aws/INDEX.csv) (152 lượt, `INDEX.csv`, `SUMMARY.md`, `logs/` gồm log ma trận và `iostat`, `integration/` gồm các lượt smoke của integration test). Các lượt Docker cũ (51 lượt) ở [results/official/2.1/](../results/official/2.1/INDEX.csv) là **số đo sơ bộ**, không dùng để so sánh chính thức. Dựng lại: [infra/aws/README.md](../infra/aws/README.md), `scripts/run-matrix-2.1.sh`, `scripts/aws-tidb-up.sh`.

**Cấu hình đo chính thức (khác Docker):** MySQL và MongoDB là một VM `c6i.4xlarge` giới hạn còn **12 vCPU / 24 GiB** (cpuset 0–11); TiDB gồm PD `c6i.large` (2 vCPU), TiDB server `c6i.xlarge` (4 vCPU) và 3 TiKV `m6i.large` (2 vCPU, 8 GiB mỗi nút) = **12 vCPU / 36 GiB**; mọi ổ dữ liệu gp3 **3000 IOPS / 125 MB/s**, cùng AZ. Máy tải `c6i.2xlarge` (8 vCPU) cho MySQL và `c6i.4xlarge` (16 vCPU) cho MongoDB ở 64–256 client và TiDB. Phiên bản: MySQL 8.4.8, MongoDB 8.0.20, TiDB/PD/TiKV v8.5.7. Độ bền: MySQL `innodb_flush_log_at_trx_commit=1` và `sync_binlog=1`; MongoDB `{w:"majority", j:true}`, cache WiredTiger 3 GiB; TiKV giữ đồng bộ log Raft mặc định, block cache 1 GiB, `max-replicas=1`. MySQL-mặc-định có buffer pool 128 MiB; MySQL-chỉnh 3 GiB. Manifest ghi `source_sha256` của mã nguồn (VM không có `.git` nên không có `git_commit`).

| Tiêu chí (AGENTS.md mục 14) | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Phiên bản thực tế ba hệ | PASS | `dbms.version` trong manifest; TiDB `Release Version: v8.5.7`, ba store TiKV `8.5.7` |
| Nạp và kiểm đếm 9 bảng/collection W=10 | PASS | `dataset_state.counts` giống nhau ở cả ba hệ: warehouse 10, item 100.000, district 100, stock 1.000.000, customer 300.000, history 300.000, orders 300.000, new_order 90.000, order_line 2.998.678 |
| New-Order và Payment đúng trên các adapter | PASS | `pytest -m integration` chạy **trên AWS** với DBMS ở VM riêng: 4 passed trên mỗi hệ (MySQL, MongoDB, TiDB); 152 lượt đo |
| Zipf/seed tái lập, uniform và single-warehouse | PASS | Unit test; các lượt θ và kiểu kho trong `INDEX.csv` |
| Baseline MySQL theo thông số 2.1 | PASS | MySQL-mặc-định, MySQL-chỉnh, một kho, 1 client: 3/3 VALID mỗi điểm |
| CSV/JSON, manifest phiên bản và tài nguyên | PASS | `result.csv`, `result.json`, `manifest.json` mỗi lượt; `tps_per_second.csv` |
| Tự kiểm ba luật sau mỗi lượt | PASS | 152 lượt; phép kiểm chéo SQL/aggregation của tài liệu `doc_check.violations = 0` ở mọi lượt có kết quả |
| EXPLAIN đúng chỉ mục | PASS | `access_paths.plans` và `indexed=true` trong manifest của cả ba hệ |
| Region TiDB | PASS (ghi nhận) | `stock` 5 Region, leader chỉ ở 2/3 store; `history` 16 Region (`SHARD_ROW_ID_BITS=4`, `PRE_SPLIT_REGIONS=4`), 1 peer mỗi Region |
| Lượt phụ: một kho, 1 client, `payment-ytd`, `idempotency-off` | PASS | Xem bảng dưới; `idempotency-off` INVALID luật 3 trên cả ba hệ (TiDB: 3 đơn trùng ở lần chạy lại, lần chạy đầu không sinh đơn trùng) |
| Các mức θ và số client 8–256 | PASS (lưới `evidence`) | Bảng dưới; lưới đầy đủ θ × client là NOT TESTED (thuộc 2.2) |
| Kiểm warmup | PASS (có lưu ý) | `warmup_stability`, `tps_per_second.csv` và hình [TPS mỗi giây, 8 client](../results/official/2.1-aws/plots/tps-per-second-8-client.svg), [64 và 256 client](../results/official/2.1-aws/plots/tps-per-second-64-256-client.svg) (`scripts/plot_tps_per_second.py`); xem lưu ý dưới |
| Nút thắt đĩa xác nhận bằng `iostat` | PASS | `logs/*/iostat-*.gz` cho từng hệ |

### Kết quả chính (TPS trung vị của 3 lần lặp, 8 client, θ=0, kho uniform, tồn 10^9)

| Điểm | MySQL | MongoDB | TiDB |
| --- | --- | --- | --- |
| Baseline (MySQL-mặc-định; cross cho hệ khác) | 259 (p99 150 ms) | 448 (p99 54 ms) | 447 (p99 46 ms) |
| MySQL-chỉnh (buffer pool 3 GiB) | 438 (p99 65 ms) | — | — |
| MySQL một kho / 1 client | 381 / 185 | — / 190 | — / 96 |
| `payment-ytd` | 251 | 410 | 417 |
| `correctness` (tồn 1.000, hết hàng thực) | 399 | 439 | 316 |

Số client (θ=0, uniform), TPS và p99:

| Client | MySQL | MongoDB (64–256 client: máy tải 16 vCPU) | TiDB |
| --- | --- | --- | --- |
| 8 | 257 (149 ms) | 458 (51 ms) | 400 (49 ms) |
| 32 | 412 (254 ms) | 1.186 (121 ms) | 911 (106 ms) |
| 64 | 496 (404 ms) | 2.119 (158 ms) | 946 (230 ms) |
| 128 | 552 (781 ms) | 3.053 (245 ms) | 930 (586 ms) |
| 256 | 506 (2.172 ms) | 2.968 (218 ms) | 948 (1.439 ms) |

Các mức θ ở 8 client (kho uniform) gần như không đổi TPS ở cả ba hệ (MySQL 255–271, MongoDB 452–458, TiDB 399–469 TPS); mức "mọi người mua một món" tăng TPS (MySQL 498, MongoDB 595, TiDB 544) vì dồn vào ít dữ liệu nóng hơn. Điểm gãy theo θ là việc của 2.2. Chi tiết từng nhóm: `results/official/2.1-aws/SUMMARY.md`.

### Khác biệt so với tài liệu ý tưởng và giới hạn (xem thêm [assumptions.md](assumptions.md))
- **TiDB bị nghẽn ở tầng SQL từ 32 client:** TiDB server (4 vCPU) đạt ~96–100% CPU nên TPS đứng quanh 910–950. Quyết định: giữ ngân sách 12 vCPU bằng nhau cho ba hệ và coi đây là kết quả ở ngân sách bằng nhau; **không dùng các điểm TiDB ≥32 client để kết luận khả năng mở rộng của TiKV** (làm rõ ở 2.3 với TiDB server cỡ đủ lớn).
- **RAM không bằng nhau:** cụm TiDB 36 GiB so với 24 GiB của MySQL/MongoDB, vì TiKV bị OOM-kill trên `c6i.large` (4 GiB, anon-rss 3,5 GB) nên dùng `m6i.large` (8 GiB). Bộ nhớ của MySQL (buffer pool) và MongoDB (cache) đặt tường minh nên không phụ thuộc giới hạn container, nhưng điều kiện "cùng tổng RAM" không được đáp ứng.
- **Máy tải:** MongoDB ở 64/128/256 client lần đầu chạy với máy tải 8 vCPU bị bão hòa (CPU 81–94%, TPS 2.150–2.500); đã chạy lại với 16 vCPU (TPS 2.100–3.050, không còn cảnh báo). Cả hai bộ đều ở `INDEX.csv`; bộ lần đầu có cảnh báo `loadgen_cpu_*` nên **bị thay thế**, nhóm bằng `run_note=loadgen_c6i.4xlarge`.
- **Lượt hỏng do lỗi công cụ, giữ lại để minh bạch:** 1 lượt MongoDB 64 client (`98b015c5…`) INVALID vì timeout 15 giây khi đối soát sau lượt 2.000 TPS; đã sửa (timeout 900 giây cho đối soát, nạp và reset) và chạy lại. Lần dựng TiDB đầu tiên (TiKV `c6i.large`) bị OOM giữa chừng; toàn bộ kết quả TiDB trong thư mục lấy từ lần dựng lại.
- `max_connections=400` cho MySQL ở toàn bộ lượt AWS (để 256 client kết nối được), thay vì 151 mặc định; buffer pool và các tham số khác của MySQL-mặc-định giữ nguyên.
- **Warmup:** 35/152 lượt bị đánh dấu `WARMUP_MAY_BE_SHORT` (chủ yếu MongoDB ở 64–256 client). Chuỗi theo giây cho thấy TPS đạt trạng thái ổn định trong vài giây đầu; độ lệch do **WiredTiger checkpoint định kỳ (~60 giây)** làm TPS tụt vài giây rơi vào cuối warmup hoặc đầu đo, không phải do chưa ổn định. 30 giây warmup được coi là đủ; số đo vẫn gồm các lần tụt này. Hình TPS theo giây cho thấy MySQL ổn định sau ~3 giây, MongoDB có các lần tụt định kỳ (ở 256 client kéo dài cỡ 10 giây và xuống dưới nửa mức bình thường), TiDB nhiễu hơn nhưng không có xu hướng tăng hay giảm.
- **`idempotency-off` trên TiDB:** lần chạy đầu (1 lần lặp) VALID, tức không có đơn trùng ngẫu nhiên; lần chạy lại (`run_note=idem_off_rerun`) INVALID luật 3 với 3 đơn trùng. Một điểm một lần lặp, không đủ để kết luận tần suất.
- **Dao động của TiDB ở 8 client lớn hơn:** cùng cấu hình (8 client, θ=0, uniform) cho 447 TPS ở profile `baseline-cross` và 400 TPS ở `performance` (khoảng min–max 341–471 giữa các lần lặp); chênh dưới ~15% ở 8 client nằm trong nhiễu.
- **Máy tải không có `.git`** nên manifest không ghi `git_commit` (có `source_sha256`).
- **Trước đây chưa đo `iostat` ở các lượt Docker**; trên AWS `iostat` ghi liên tục cả ma trận (gồm reset và đối soát), chỉ dùng để thấy xu hướng.

### NOT TESTED
- Lưới đầy đủ θ × số client (8–256) trên cả ba hệ (Tầng 3 / 2.2).
- Thời gian chờ khóa và số deadlock của MongoDB và TiDB (chỉ MySQL có; hai hệ kia lưu `null`).
- Grafana của cụm TiDB đã được dựng nhưng chưa dùng làm bằng chứng; tham số `raftstore.sync-log` không còn ở TiDB v8.5.7.
- Khôi phục dữ liệu bằng EBS snapshot (dùng `flashsale reset` thay thế).
- Bộ TPC-C chuẩn go-tpc để nạp dữ liệu và đo mốc (dùng loader Python thay thế).
- MySQL-chỉnh chỉ chạy trên MySQL; chưa có "MongoDB-chỉnh" hay TiDB-chỉnh (không yêu cầu).
- Lặp lại giữa các lần dựng VM (mọi lượt AWS cùng một lần dựng cho mỗi hệ, trừ MongoDB 64–256 client).
- Quy trình snapshot/khôi phục EBS cho dữ liệu (chỉ dùng reset bằng SQL/aggregation).
- Replica 3 của TiDB, pin leader/Region, `SPLIT TABLE` (thuộc 2.3).

## Số đo sơ bộ trước bản chốt (Docker một VM): giữ để tham khảo

| Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Xác nhận phiên bản thực tế cả ba hệ | PASS | MySQL 8.4.8, MongoDB 8.0.20, TiDB v8.5.7 (3 TiKV cùng 8.5.7, `max_replicas=1`) trong manifest |
| Nạp và kiểm đếm 9 bảng/collection W=10 | PASS | Cả ba hệ: warehouse 10, item 100.000, district 100, stock 1.000.000, customer 300.000, history 300.000, orders 300.000, new_order 90.000, order_line 2.998.678 (khớp nhau) |
| New-Order và Payment đúng trên các adapter | PASS | Integration test 4/4 trên mỗi hệ; các lượt đo VALID |
| Zipf/seed tái lập, uniform và single-warehouse | PASS | Unit test; trên DB thật tần suất quan sát khớp lý thuyết ở θ=0,3; 0,5; 0,7; 0,9 và mức một món (bảng dưới) |
| Baseline MySQL theo thông số 2.1 | PASS | 3 điểm x 3 lần, tất cả VALID |
| Xuất CSV/JSON và manifest phiên bản/tài nguyên | PASS | `result.csv`, `result.json`, `manifest.json` mỗi lượt |
| Tự kiểm ba luật sau mỗi lượt | PASS | 51 lượt: 48 VALID; 3 INVALID đều là lượt idempotency-off, vi phạm luật 3 theo đúng dự kiến |
| Phép kiểm chéo bằng câu SQL / aggregation của tài liệu | PASS | Chạy trên cả ba DBMS thật (integration: rỗng khi sạch, khác rỗng khi cài lỗi); `doc_check.violations = 0` ở mọi lượt chạy từ commit `3a5aded` |
| `flashsale validate` chạy lại đối soát trên run đã lưu | PASS | `validate-cli-output.json`: VALID, 11.498 đơn đã commit |
| Test trên DBMS thật PASS | PASS | `pytest -m integration`: 4 passed trên mỗi hệ; smoke VALID cả ba |
| Lượt phụ của tài liệu: một kho, 1 client, Payment bật YTD, tắt idempotency | PASS | Có kết quả (bảng dưới); idempotency-off tái hiện đơn trùng trên cả ba DBMS |

## Kết quả

Số là trung vị 3 lần lặp (khoảng min–max của TPS), 30 giây warmup cộng 60 giây đo, 8 client trừ khi ghi khác. p50/p95/p99 tính trên request thành công, gồm retry và backoff. Hủy không gồm hết hàng.

### Baseline MySQL (dữ liệu tồn 10^9, θ=0)
| Điểm đo | TPS | p50 | p95 | p99 | Hủy |
| --- | --- | --- | --- | --- | --- |
| Kho uniform (**baseline**) | 261,3 (260,6–267,4) | 18,2 ms | 102 ms | 157 ms | 0% |
| Một kho | 399,4 (399,0–434,3) | 12,7 ms | 48 ms | 96 ms | 0% |
| 1 client, uniform | 163,4 (161,5–170,8) | 5,6 ms | 11 ms | 14 ms | 0% |
| Payment bật `w_ytd`/`d_ytd` (lượt riêng) | 256,4 (254,7–265,8) | 18,7 ms | 105 ms | 160 ms | 0% |

### Số client trên MySQL (θ=0, uniform, `max_connections=400`)
`max_connections` nâng từ 151 lên 400 vì 256 client cần thêm kết nối; mức 8 client chạy lại trong cùng điều kiện (266,5 TPS, lệch 2% so với baseline).

| Client | TPS | p50 | p95 | p99 | CPU người dùng + hệ thống của cả VM | iowait |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 266,5 (265,8–267,3) | 18,3 ms | 102 ms | 154 ms | 5,2% (~0,8 vCPU) | 13,9% |
| 32 | 414,2 (414,2–414,6) | 69,5 ms | 175 ms | 244 ms | 7,1% (~1,1 vCPU) | 24,9% |
| 64 | 521,6 (500,9–528,0) | 112,7 ms | 258 ms | 364 ms | 8,2% (~1,3 vCPU) | 29,3% |
| 128 | 553,9 (552,4–558,5) | 183,5 ms | 526 ms | 795 ms | 8,3% (~1,3 vCPU) | 34,8% |
| 256 | 503,5 (503,1–507,4) | 331,1 ms | 1472 ms | 2306 ms | 7,8% (~1,2 vCPU) | 41,7% |

Cả 15 lượt VALID, hủy 0%. TPS tăng đến khoảng 128 client rồi đi ngang và giảm nhẹ ở 256 (p99 tăng gần 3 lần). **Script tải không phải nút thắt:** ở cả 5 mức, tổng CPU người dùng cộng hệ thống của toàn bộ VM (gồm MySQL, Docker và script tải) chỉ khoảng 1 đến 1,3 vCPU trên 16, trong khi iowait tăng đều và thông lượng ghi đĩa đi ngang quanh 35–40 MB/s. Số liệu thô: `vmstat-concurrency-*.txt`. Suy ra nút thắt nhiều khả năng là đĩa EBS (fsync mỗi commit); chưa đo `iostat` nên đây vẫn là suy luận.

### Các mức θ trên MySQL (8 client, 1 lần lặp mỗi mức, tồn 10^9)
Đây là kiểm tra runner chịu được tải lệch và tần suất chọn khớp lý thuyết, không phải điểm đo chính thức (1 lần lặp).

| Điều kiện | TPS | p99 | Rank 1 quan sát / lý thuyết | Top 100 quan sát / lý thuyết | Chờ khóa (cộng dồn) |
| --- | --- | --- | --- | --- | --- |
| θ=0 (baseline) | 261,3 | 157 ms | 0,000% / 0,001% | 0,11% / 0,10% | 6 giây |
| θ=0,3 | 272,6 | 153 ms | 0,032% / 0,022% | 0,80% / 0,78% | 6,8 giây |
| θ=0,7 | 269,6 | 152 ms | 1,022% / 0,974% | 10,29% / 10,24% | 6,5 giây |
| θ=0,9 | 280,9 | 147 ms | 4,590% / 4,506% | 28,95% / 28,96% | 7,3 giây |
| Mọi yêu cầu một món (một kho) | 269,4 | 99 ms | 100% / 100% | 100% / 100% | **366 giây** |

Tất cả VALID, hủy 0%, không có deadlock. Ở 8 client và W=10, tải lệch hầu như không làm giảm TPS trừ khi dồn vào một dòng (thời gian chờ khóa tăng khoảng 60 lần nhưng TPS gần như đứng yên vì nút thắt nằm ở đĩa). Điểm gãy theo θ là việc của 2.2.

### Lượt kiểm luật (tồn đầu 1.000, kho 1, một món hot)
| Hệ | TPS | p50 | p99 | Hết hàng | Retry |
| --- | --- | --- | --- | --- | --- |
| MySQL 8.4.8 | 420,4 | 9,5 ms | 15,1 ms | 50% request | 0% |
| MongoDB 8.0.20 | 390,4 | 8,0 ms | 12,6 ms | 50% | 5,4% (write conflict) |
| TiDB v8.5.7 | 261,8 (247,4–293,4) | 7,4 ms | 17,3 ms (lượt 1: 49 ms) | 50% | 0% |

Cả ba hệ giữ ba luật qua mỗi lần lặp có 15.000–25.000 request hết hàng. Các số này chỉ so được trong cùng một workload (mọi request dồn vào một dòng tồn kho), không dùng để xếp hạng hệ.

### Lượt đo tốc độ (tồn 10^9, θ=0,5, uniform)
| Hệ | TPS | p50 | p95 | p99 | Retry |
| --- | --- | --- | --- | --- | --- |
| MongoDB | 392,7 (385,2–403,1) | 14,7 ms | 41 ms | 79 ms | 2,1% (write conflict) |
| TiDB | 307,1 (289,0–310,0) | 20,2 ms | 59 ms | 93 ms | 0% |

### Lượt phụ tắt idempotency (64 client, một món hot, 1 lần lặp)
Timeout socket ngắn buộc client mất kết quả commit; không có UNIQUE và không đối chiếu DB nên retry ghi đơn lần hai. "Mất xác nhận" là đơn đã commit nhưng client không ghi nhận thành công.

| Hệ | `client_timeout_seconds` | Kết quả | Đơn trùng | Mất xác nhận | Hủy |
| --- | --- | --- | --- | --- | --- |
| MySQL | 0,2 s | VALID | 0 | 0 | 0,5% |
| MySQL | 0,05 s | VALID | 0 | 0 | 17,2% |
| MySQL | **0,02 s** | **INVALID luật 3** | **1** | 2 | 33,7% |
| MongoDB | **0,02 s** | **INVALID luật 3** | **8** | 16 | 17,9% (70.831 write conflict) |
| TiDB | **0,02 s** | **INVALID luật 3** | **7** | 50 | 52,7% |

Một lần lặp mỗi điểm nên chưa kết luận được tần suất; mục đích chỉ là chứng minh mã chống trùng có tác dụng. Lượt này không được xếp hạng.

## Quan sát cần lưu ý (chưa đủ chứng cứ để kết luận)
- **Kiểu một kho nhanh hơn uniform** (399 so với 261 TPS) dù thời gian chờ khóa lớn hơn khoảng 10 lần. Giả thuyết: dữ liệu W=10 lớn hơn buffer pool mặc định 128 MiB nên uniform bị trượt bộ nhớ đệm. Chưa đo I/O đĩa để xác nhận.
- CPU MySQL chỉ dùng 42–90% của một lõi trên hạn mức 8 ở mọi mức client; TPS giới hạn bởi đĩa (xem trên), nên **mọi số TPS phụ thuộc loại đĩa EBS gp3**.
- Payment bật `w_ytd`/`d_ytd` làm thời gian chờ khóa tăng khoảng 6 lần nhưng TPS giảm chỉ khoảng 2% ở 8 client uniform.
- TiDB: `stock` nằm trong 2 Region, `history` có 16 Region (đúng `SHARD_ROW_ID_BITS=4`, `PRE_SPLIT_REGIONS=4`). Leader của Region `stock` đổi giữa các lượt (PD đang cân bằng); cần ghim bộ cân bằng ở 2.3.
- CPU TiDB server khoảng 140–170% của hạn mức 3 CPU, không vượt ngưỡng cảnh báo 80%.

## Khác biệt so với tài liệu
Chi tiết ở [assumptions.md](assumptions.md). Tóm tắt: loader Python thay go-tpc; đối soát chính bằng `run_id`, kiểm chéo bằng câu SQL/aggregation của tài liệu với điều kiện `ol_o_id > initial_orders`; không có FOREIGN KEY; ngân sách chung 8 CPU / 16 GiB (không phải 4 / 6); block cache TiKV 1 GiB; tách `out_of_stock` khỏi tỉ lệ hủy; lượt idempotency-off dùng timeout 0,02 s để gây commit mơ hồ; `max_connections=400` chỉ ở lưới số client MySQL.

## NOT TESTED
- Các mức θ khác 0 và mức "một món" chỉ chạy 1 lần lặp trên MySQL; trên MongoDB và TiDB chỉ có θ=0,5.
- Lưới số client (8 đến 256) chỉ chạy trên MySQL ở θ=0; MongoDB và TiDB chỉ 8 client (và 64 ở lượt idempotency-off). Lưới đầy đủ θ × số client trên cả ba hệ thuộc mục 2.2.
- Baseline uniform trên MongoDB và TiDB (đề chỉ yêu cầu baseline MySQL).
- Các lượt idempotency-off chỉ 1 lần lặp mỗi điểm.
- I/O đĩa (`iostat`) để xác nhận nút thắt EBS; giả thuyết cache của kiểu một kho.
- Pin leader/Region, `SPLIT TABLE`, replica 3 của TiDB (thuộc 2.3).

## Tái hiện
Xem [README](../README.md) và [trien-khai-2.1.md](trien-khai-2.1.md). Ví dụ baseline MySQL:

```bash
flashsale start mysql
DATASET=$(flashsale load mysql --config configs/baseline.toml | python -c 'import json,sys; print(json.load(sys.stdin)["database"])')
flashsale run mysql --config configs/baseline.toml --dataset "$DATASET" --reset-between
```

Lưới số client: thêm `--concurrency N` và đặt `FLASHSALE_MYSQL_MAX_CONNECTIONS=400` trước `flashsale start mysql`.
