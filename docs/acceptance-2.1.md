# Nghiệm thu mục 2.1

Ngày chạy: 2026-11-19 và 2026-11-20. Môi trường: AWS EC2 `c6i.4xlarge` (16 vCPU, 32 GiB, đĩa gp3 100 GiB), Ubuntu 24.04 LTS x86_64, Docker 29.10.0, Compose 5.8.0, Python 3.12.3. Mỗi hệ chạy riêng một thời điểm với ngân sách container chung **8 CPU / 16 GiB** ([assumptions.md](assumptions.md)). Dữ liệu thô nằm ở [results/official/2.1/](../results/official/2.1/) (xem `INDEX.csv`, 51 lượt). Các lượt chạy ngày 2026-11-19 dùng Git commit `38dda58` (`main`); các lượt bổ sung ngày 2026-11-20 (profile `performance-theta*`, `performance-hot-item`, `baseline-concurrency`, idempotency-off trên MongoDB/TiDB, `validate-cli-output.json`) dùng commit `3a5aded` của nhánh `complete-2.1`, đã gồm phép kiểm chéo của tài liệu. Không có thay đổi chưa commit ở cả hai.

## Cập nhật theo bản chốt `bao_cao_DBMS_ban_chot.docx` (2026-11-20): PARTIAL
Các lượt bên dưới được chạy **trước** khi có bản chốt và chỉ là số đo **sơ bộ trên Docker**. Bản chốt thêm yêu cầu mà chưa được kiểm chứng trên DBMS thật: (1) MySQL-chỉnh (`configs/baseline-tuned.toml`) ở điểm baseline; (2) độ bền ngang nhau (`sync_binlog=1`, MongoDB `j:true`) và cache MongoDB đặt tường minh, nên các lượt MongoDB cũ cần chạy lại; (3) kiểm warmup bằng TPS theo giây; (4) baseline 1 client và baseline uniform trên mỗi hệ; (5) 3 lần lặp cho lưới θ × client; (6) hạ tầng AWS nhiều VM, script tải riêng, `iostat`, EBS snapshot. Mã và test đơn vị cho (1)–(3) đã có; (4)–(6) chưa làm. Chi tiết ở [assumptions.md](assumptions.md).

### Checklist để 2.1 thành DONE theo bản chốt (số đo chính thức trên AWS)

| # | Việc | Bằng chứng cần có | Cách tạo | Trạng thái |
| --- | --- | --- | --- | --- |
| 1 | Quota vCPU ≥ 32 và hạ tầng `stack` dựng được | `terraform plan/apply` thành công, ảnh Budgets | `infra/aws/README.md` | NOT DONE (quota `CASE_OPENED`) |
| 2 | TiDB 1 PD + 1 TiDB + 3 TiKV bằng TiUP, `max-replicas=1`, block cache như nhau | `manifest.json` (`pd`, `tikv_durability_config`), `SHOW TABLE stock REGIONS` | topology TiUP trong repo | NOT DONE |
| 3 | Tài nguyên ba hệ bằng nhau (12 vCPU / 24 GiB, không tính VM tải/monitor) | `resource_limits` và `remote_nodes` trong manifest | Terraform + `FLASHSALE_REMOTE_NODES` | NOT DONE |
| 4 | Độ bền ngang nhau: MySQL `flush=1`, `sync_binlog=1`; MongoDB `majority + j`; TiKV mặc định | `dbms` trong manifest cả ba hệ | compose override, `flashsale run` | NOT DONE |
| 5 | Máy tải không là nút thắt (kể cả ở 64–256 client, nơi `c6i.xlarge` đã bão hòa ở 64 client / 10.000 IOPS) | `loadgen_cpu_pct` và không có cảnh báo `loadgen_cpu_*pct_of_limit` | node_exporter trên `loadgen`; nâng `loadgen_instance_type` | Đã chọn mặc định `c6i.2xlarge` (8 vCPU), cần xác nhận ở các điểm 64–256 client |
| 6 | Baseline MySQL-mặc-định, MySQL-chỉnh, một kho, 1 client; uniform và 1 client cho từng hệ | `INDEX.csv`, `SUMMARY.md` | `scripts/run-matrix-2.1.sh` (MySQL-chỉnh chạy riêng) | NOT DONE trên AWS |
| 7 | `payment-ytd`, `correctness` (hết hàng thực), `idempotency-off` trên cả ba hệ | các lượt VALID; idempotency-off INVALID luật 3 đúng dự kiến | script ma trận | NOT DONE trên AWS |
| 8 | Các mức θ và số client (8–256) | lưới `evidence` (hoặc `full` nếu muốn) | `--grid evidence|full` | NOT DONE trên AWS |
| 9 | Kiểm warmup 30 giây có đủ không | mục "Kiểm tra warmup" trong `SUMMARY.md` | `flashsale report` | NOT DONE |
| 10 | Nút thắt đĩa EBS xác nhận bằng `iostat` | `iostat.txt` mỗi điểm | `FLASHSALE_IOSTAT_SSH` + script ma trận | NOT DONE |
| 11 | Ba luật + phép kiểm chéo VALID sau mọi lượt, EXPLAIN đúng chỉ mục trên cả ba hệ | `validation`, `access_paths` | tự động trong `flashsale run` | PASS trên Docker; NOT DONE trên AWS |
| 11b | Cấu hình đĩa ngang nhau và không phụ thuộc burst: mọi ổ gp3 cùng IOPS/throughput, không vượt IOPS cơ bản của instance nhỏ nhất | `terraform.tfvars`, manifest, [pilot-aws-vs-docker.md](pilot-aws-vs-docker.md) | mặc định 3000/125; thí nghiệm riêng 10.000 IOPS trên MySQL | Đề xuất, chờ xác nhận |
| 12 | Kết quả chính thức commit vào `results/official/2.1/` kèm manifest, INDEX | thư mục và `INDEX.csv` | `flashsale report --results-dir results --out results/official/2.1` sau khi chọn lượt | NOT DONE |

**Ước lượng thời gian và chi phí (chưa đo, chỉ là dự toán để hoạch định):** mỗi lần lặp tốn khoảng 90 giây đo cộng reset và đối soát, tạm tính 4–6 phút. Lưới `evidence` có khoảng 18 điểm × 3 lần cho MySQL (15 điểm cho MongoDB và TiDB), nên khoảng 4–5 giờ mỗi hệ, khoảng 13–16 giờ cho ba hệ. Cộng nạp dữ liệu W=10 (ba dataset mỗi hệ), dựng hạ tầng và debug, thực tế 30–40 giờ bật máy. Với 0,7–0,9 USD mỗi giờ, đó là khoảng 25–40 USD cho 2.1. Lưới `full` thêm khoảng 7 giờ đo cộng reset mỗi hệ; nên để 2.2. Con số có thể lệch nhiều, hãy đo thời gian một điểm đầu tiên rồi nhân lên.

## Kết luận (theo AGENTS.md trước bản chốt): DONE

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
