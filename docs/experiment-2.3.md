# Thực nghiệm 2.3 (TiDB: thêm máy có cứu được Flash-sale không?) — trạng thái mã nguồn Tầng 1

Chưa có số đo nào của mục 2.3 trong repo. Đối chiếu với `Btl_final.docx` (mục 2.3 và 2.3.1 trùng bản chốt `bao_cao_DBMS_ban_chot.docx`; hai bản chỉ khác một câu ở 2.5). Khác biệt: xem phần "mục 2.3" của `docs/assumptions.md`. Phạm vi mã: Tầng 1 của `docs/scope-2-weeks.md` (nhóm A, B, C, D, E.a, hệ số tăng tốc, mốc MySQL-chỉnh); **chưa làm** E.b (async commit/1PC), E.c, E.d, nhóm R (3 bản sao).

## Nhóm → cách chạy

`scripts/run-matrix-2.3.sh <tidb|mysql> [--tier a|b|c|d|e|all] [--dry-run]`, chạy một lần trên cụm 1 TiKV (stack `tidb1`) rồi một lần trên cụm 3 TiKV (`tidb3`) với cùng cấu hình; 64 client, 3 lần × (30 s + 60 s), profile `configs/scaling.toml` (W = 12, tồn 10^9).

| Nhóm | Điểm đo | Tùy chọn chính |
| --- | --- | --- |
| A | θ=0, kho đều | `--variant p1 --theta 0 --warehouse-mode uniform` |
| B | θ=0,9, một kho, cấp mã đơn theo lô | `--variant p1 --theta 0.9 --warehouse-mode single-warehouse --order-id-batch 50` |
| C | B + chia món nóng N = 3, 9, 27 slot | `--variant p2 --slots N` (slot được tách Region theo từng slot và rải leader) |
| D | khóa `orders` tự tăng so với `AUTO_RANDOM` (dataset riêng) | `configs/scaling-autoinc.toml`, `configs/scaling-autorandom.toml` (`orders_key`) |
| E.a | θ=0, đơn 1 / 2 / 3–4 kho × vị trí leader {PD, tách, chung theo nhóm} | `--order-warehouses-min/max`, `--warehouse-groups 3`, `--placement none|spread|group --placement-scope all` |
| MySQL mốc | A, B, C trên MySQL-chỉnh hai cỡ máy (20 vCPU/44 GiB và 24 vCPU/60 GiB, cùng tổng với cụm 1 và 3 TiKV khi TiDB server là c6i.4xlarge) | xem đầu `run-matrix-2.3.sh` (`m6i.8xlarge`, `FLASHSALE_REMOTE_BUDGET_*`) |

Mọi điểm đều chạy ba luật tồn kho và đối soát của đề; đơn nhiều kho đối soát theo `ol_supply_w_id`.

## Cấu hình hạ tầng đo chính thức của 2.3 (đã chốt 2026-11-21)

TiDB server **c6i.4xlarge** (16 vCPU/32 GiB) dùng chung cho cụm 1 và 3 TiKV (smoke cho thấy 4 vCPU nghẽn ở tầng SQL), PD c6i.large, TiKV m6i.large (nếu AWS hết capacity m6i.large ở us-east-1c thì dùng loại khác nhưng **cùng loại ở cả hai cụm** và ghi vào báo cáo), máy tải c6i.4xlarge (`FLASHSALE_LOADGEN_CPUS=16`). Tổng cụm TiDB: 20 vCPU/44 GiB (1 TiKV) và 24 vCPU/60 GiB (3 TiKV); `FLASHSALE_REMOTE_BUDGET_*` đặt theo đúng tổng đó. Quota vCPU 64 đủ: `tidb3` dùng 16 + 2 + 16 + 6 + 2 = 42; MySQL (`m6i.8xlarge` 32) + máy tải 16 = 48.

## Đơn nhiều kho (nhóm E)

`order_warehouses_min/max` (1–4) và `warehouse_groups`: kho nhà được chọn như thường; mỗi đơn lấy `k` kho khác nhau (k ngẫu nhiên trong [min, max]), kho còn lại chỉ chọn trong cùng nhóm với kho nhà (W chia đều thành các nhóm liên tiếp), mỗi kho khác cấp đúng một món (cần ít nhất k món khác nhau; hiếm khi trùng món thì chạm ít kho hơn k). `Request.supply` ghi kho cung cấp từng món; `o_all_local` = 0 nếu có món lấy từ kho khác. Cấu hình mặc định (một kho) giữ nguyên dãy số ngẫu nhiên của 2.1. Không dùng với `hot_item`, một kho, stored procedure hay MongoDB (b).

## Đặt Region/leader (`--placement`)

Chỉ TiDB. Trước warmup của mỗi lượt (ngoài thời gian đo): chia `stock` (và `stock_slot` khi dùng P2; với `--placement-scope all` thêm `district`, `customer`, `orders`, `new_order`, `order_line`) bằng `SPLIT TABLE t BY (w, 0, ...)` với đủ mọi cột khóa (yêu cầu của khóa cụm nhiều cột), chuyển leader bằng PD HTTP API (`transfer-peer` khi một bản sao, `transfer-leader` khi nhiều bản sao), tạm dừng `balance-leader/region/hot-region-scheduler` và đặt các giới hạn lập lịch (`leader/region/hot-region/merge-schedule-limit`) về 0, rồi **đọc lại `SHOW TABLE ... REGIONS` để xác nhận** (chờ tối đa 180 s; sai thì lượt bị INVALID `placement_failed`, không chạy tiếp). Sau lượt đo: ghi `TIDB_HOT_REGIONS`, khôi phục bộ lập lịch (kể cả khi lỗi). `spread`: leader kho `w` về TiKV `(w−1) mod n` ("tách": các kho cùng nhóm ở các TiKV khác nhau); `group`: cả nhóm kho về một TiKV ("chung theo nhóm"). Slot (nhóm C): mỗi (kho, món nóng, slot) của `--placement-slot-items` món đầu (mặc định 5) là một Region, slot `s` về TiKV `s mod n`. Bằng chứng nằm ở `result.json` (`placement_result`: số Region mỗi TiKV theo bảng, cấu hình Load Base Split `split.*`, Region nóng sau lượt) và `manifest.dbms.commit_options` (hai biến `tidb_enable_async_commit`, `tidb_enable_1pc`).

## Khóa orders (nhóm D)

`orders_key = autoinc | auto_random`: `orders` đổi sang khóa chính một cột `o_seq BIGINT` (`AUTO_INCREMENT` hoặc `AUTO_RANDOM`, clustered), `(o_w_id, o_d_id, o_id)` thành UNIQUE phụ; fingerprint dataset khác nên cần dataset riêng; chỉ TiDB.

## Hệ số tăng tốc

`flashsale report` có thêm mục "Hệ số tăng tốc": TPS trung vị của cụm 3 TiKV chia cho 1 TiKV (TiDB), hoặc cỡ vCPU lớn chia cho cỡ nhỏ (MySQL, 24 ÷ 20), ghép theo từng nhóm giống hệt nhau về mọi tham số khác; chỉ tính khi hai phía có lượt VALID. `INDEX.csv` có thêm `tikv_count`, `vcpus`, `orders_key`, `placement`, `placement_scope`, `order_warehouses`, `warehouse_groups`.

## Kết quả đo chính thức: cụm 1 TiKV (AWS, 2026-11-21)

`results/official/2.3-aws/tidb1/` (21 lượt, `INDEX.csv`, `SUMMARY.md`, `runs/`, `logs/` gồm `matrix.log` và `iostat`). Cấu hình: TiDB v8.5.7, TiDB server c6i.4xlarge (16 vCPU), PD c6i.large, **1 TiKV m6i.large**, máy tải c6i.4xlarge, đĩa gp3 3000 IOPS / 125 MB/s, W = 12, tồn 10^9, 64 client, 3 lần × (30 s + 60 s), P1 (B và C kèm cấp mã đơn theo lô 50), `--placement spread`. Cả 21 lượt VALID; không có cảnh báo CPU máy tải hay TiDB server (TiDB ≈ 28% CPU của 16 vCPU).

| Nhóm | TPS trung vị (min–max) | p99 trung vị (ms) |
| --- | --- | --- |
| A: θ=0, kho đều | 1.136 (956–1.181) | 200 |
| B: θ=0,9, một kho | 616 (589–634) | 912 |
| C: B + N = 3 slot | 707 (705–1.035) | 950 |
| C: N = 9 slot | 849 (744–923) | 287 |
| C: N = 27 slot | 845 (826–908) | 197 |
| D: `orders` khóa `o_seq` tự tăng (θ=0, đều) | 766 (720–862) | 309 |
| D: `orders` khóa `AUTO_RANDOM` (θ=0, đều) | 788 (745–834) | 302 |

Điều đọc được từ số đo (chưa có phía 3 TiKV nên **chưa có hệ số tăng tốc**): (1) tải đều (A) nhanh hơn tải dồn (B) 1,8 lần, p99 4,5 lần thấp hơn; (2) chia món nóng thành N slot (P2) cải thiện B: N = 9 và 27 đạt ≈ 1,4 lần TPS và p99 giảm từ 912 ms xuống 287 và 197 ms, còn N = 3 chưa cải thiện rõ (TPS trung vị 707, p99 950 ms); (3) ở 1 TiKV, TiKV duy nhất chạm 100% CPU của 2 vCPU ở nhóm A, tức nút thắt là TiKV, đúng điều kiện để thêm TiKV có tác dụng; (4) `AUTO_RANDOM` nhỉnh hơn khóa tự tăng chỉ ≈ 3% (788 so với 766), nằm trong nhiễu giữa các lần lặp, nên ở 1 TiKV chưa thấy tác dụng như dự đoán (dự đoán nói về điểm nóng khi thêm máy, cần so ở 3 TiKV); cả hai đều thấp hơn khóa TPC-C ghép (1.136), nên đổi lược đồ sang `o_seq` + UNIQUE phụ tự nó tốn thêm chi phí ghi chỉ mục. **Lưu ý chất lượng:** `warmup_drift_pct` vượt ±10% ở một số lượt (ví dụ nhóm D autoinc −28,5% và 29,2%; N = 27 lượt 3 là 44,3%; A lượt 1 là 11,7%) nên 30 giây warmup có thể chưa đủ cho TiDB ở các điểm đó; cần xem `tps_per_second.csv` trước khi dùng số của các lượt này làm kết luận, và `flashsale report` đã đánh dấu `WARMUP_MAY_BE_SHORT`.

## Kết quả đo chính thức: cụm 3 TiKV và hệ số tăng tốc (AWS, 2026-11-22)

`results/official/2.3-aws/tidb3/` (48 lượt, tất cả VALID) cùng cấu hình với cụm 1 TiKV (TiDB server c6i.4xlarge, 3 × TiKV m6i.large, W = 12, 64 client, 3 × (30 s + 60 s), `--placement spread`). Bảng ghép cặp ở `results/official/2.3-aws/SUMMARY-speedup.md`.

| Nhóm | TPS 1 TiKV | TPS 3 TiKV | Tăng tốc (3 là hoàn hảo) |
| --- | --- | --- | --- |
| A: θ=0, kho đều | 1.136 | 2.250 | 1,98 |
| B: θ=0,9, một kho | 616 | 751 | 1,22 |
| C: B + N = 3 slot | 707 | 1.726 | 2,44 |
| C: N = 9 slot | 849 | 2.087 | 2,46 |
| C: N = 27 slot | 845 | 2.121 | 2,51 |
| D: khóa `o_seq` tự tăng | 766 | 1.682 | 2,20 |
| D: khóa `AUTO_RANDOM` | 788 | 2.222 | 2,82 |

Đọc được: (1) điểm nóng chặn việc mở rộng: B chỉ tăng 1,22 lần khi thêm 2 TiKV, trong khi chia món nóng thành slot (P2) đưa hệ số lên ≈ 2,5; (2) tải đều (A) đạt 1,98, chưa tới 3 vì TiDB server và `history`/`orders` vẫn tranh chấp một phần; (3) `AUTO_RANDOM` đạt 2,82 so với 2,20 của khóa tự tăng: dự đoán về điểm nóng ghi `orders` khi thêm máy được ủng hộ ở 3 TiKV (ở 1 TiKV hai kiểu khóa gần như bằng nhau). Nhiều lượt có `warmup_drift_pct` vượt ±10% (16/69 lượt cả hai cụm; một số lên tới 44%), nên các hệ số này là mức ước lượng thô, cần xem `tps_per_second.csv` và có thể phải kéo dài warmup.

### Nhóm E.a (3 TiKV, đơn nhiều kho, `--placement-scope all`, θ=0, kho đều, 3 lần mỗi điểm)

| Vị trí leader | 1 kho/đơn | 2 kho/đơn | 3–4 kho/đơn |
| --- | --- | --- | --- |
| PD tự quyết (`none`) | 1.569 TPS, p99 163 | 1.746, 135 | 1.487, 158 |
| Tách (`spread`) | 1.459, 209 | 1.562, 189 | 1.539, 183 |
| Chung theo nhóm (`group`) | 2.022, 133 | 1.455, 202 | 1.462, 203 |

(TPS trung vị, p99 ms.) `group` nhanh nhất khi đơn chỉ chạm một kho (+29% so với `none`) nhưng mất lợi thế khi đơn trải 2–4 kho; chênh lệch giữa `none`, `spread` ở 2–4 kho nằm trong nhiễu giữa các lần lặp (min–max chồng nhau), nên chưa kết luận được ngoài mô thức trên. Điểm `e-spread-k3-4` đã đo lại sau khi sửa lỗi PD HTTP 500 (bản cũ nằm ngoài kết quả).

## Đã kiểm thử / chưa kiểm thử

- Unit test với PD và TiDB giả lập (`tests/test_scaling.py`; toàn bộ 75 test không cần DBMS PASS). Đơn nhiều kho trên MySQL 8.4.8 thật (Docker máy dev, sơ bộ): smoke 1, 2 và 3–4 kho/đơn đều VALID với hết hàng thực.
- **Smoke trên TiDB v8.5.7 thật, AWS 2026-11-21 (sơ bộ, 1 lần lặp, 10 s + 20 s; stack `tidb1` với TiKV `c6i.xlarge` thay cho `m6i.large` vì AWS hết capacity m6i.large/m5.large ở us-east-1c; đã `terraform destroy`; bằng chứng ở `.work/g23-smoke-aws/`):**
  - Dataset W = 12 nạp được (1,2 triệu dòng stock). Nhóm A với `--placement spread` VALID (≈1.100 TPS; `tidb_cpu_100pct_of_limit`: TiDB server 4 vCPU là nút thắt như 2.1).
  - Phát hiện và đã sửa: bảng lớn tự tách Region theo kích thước (13 Region thay vì 12) nên cách đếm Region ban đầu sai; nay giải mã `START_KEY` (`t_<id>_r_` + `03` + 8 byte đã lật bit dấu cho mỗi cột khóa) để ánh xạ mọi Region về kho và kiểm tra ranh giới tách có thật.
  - PD HTTP API xác nhận trên PD thật: `GET /stores`, `/config/replicate`, `/config/schedule`, `/schedulers`; tạm dừng 3 scheduler và đặt bốn giới hạn lập lịch về 0 rồi khôi phục (đã đọc lại: không scheduler nào còn tạm dừng, các giới hạn về 4, 2048, 4, 8, nên `delay: 0` tiếp tục được scheduler); `POST /operators` nhận đúng tên trường `name`, `region_id`, `to_store_id` (thiếu thì báo "missing store id", tên lạ thì "unknown operator", chuyển về chính leader hiện tại thì "no operator step is built").
  - `SPLIT TABLE ... BY (w, 0, ...)` (đủ cột khóa) hoạt động trên `stock`, `district`, `customer`, `new_order`, `order_line` (phạm vi `all`).
  - Nhóm D: `AUTO_RANDOM` (mặc định 5 bit shard, `o_seq` ngẫu nhiên) và `AUTO_INCREMENT` (`o_seq` tuần tự) cho `orders` đều VALID; `orders` không bị tách theo kho khi dùng `o_seq`; cấu hình Load Base Split (`split.*`) ghi được vào bằng chứng (đã sửa lỗi pymysql định dạng `%` làm trống trường này); `commit_options` ghi vào manifest.
- **Smoke trên cụm 3 TiKV thật (stack `tidb3`, AWS 2026-11-21, sơ bộ, 1 lần lặp, 10 s + 20 s, TiKV `c6i.xlarge` ×3; đã `terraform destroy`; bằng chứng ở `.work/g23-tidb3-aws/`):** việc chuyển leader giữa nhiều TiKV bằng `transfer-peer` (một bản sao) **hoạt động trên PD thật** và `SHOW TABLE REGIONS` xác nhận đúng:
  - A với `--placement spread`: `stock` 13 Region về 3 TiKV (5/4/4), VALID.
  - E.a, đơn 3–4 kho, `--placement group --placement-scope all`: 6 bảng, mỗi bảng 4/4/4 Region lên ba TiKV (nhóm 4 kho cùng một TiKV), VALID; `--placement spread`: cũng 4/4/4 (các kho trong nhóm bị tách ra các TiKV), VALID.
  - C, P2 N=9 với `--placement spread`: `stock_slot` 46 Region rải 16/15/15 lên ba TiKV, VALID.
  - Sau cả bốn lượt PD trở lại đúng cấu hình ban đầu (không scheduler nào tạm dừng; giới hạn 4, 2048, 4, 8).
  - **Lưu ý quan trọng cho kết luận 2.3:** ở cả bốn điểm máy chủ TiDB (4 vCPU) chạm 100% CPU (`tidb_cpu_100pct_of_limit`) trong khi mỗi TiKV chỉ 55–141% trên 400%; TPS ≈ 800–1.000 gần như không đổi giữa 1 và 3 TiKV (1.100 ở cụm 1 TiKV, 1.000 ở cụm 3 TiKV, hai cấu hình khác lần chạy và TiKV nên chỉ tham khảo). Nghĩa là với TiDB server 4 vCPU hệ số tăng tốc sẽ ≈ 1 vì tầng SQL là nút thắt, không phải vì điểm nóng: đúng điều biên bản bàn giao đã chốt ("cách A": ở 2.3 dùng TiDB server cỡ đủ lớn, dùng chung cho cụm 1 và 3 TiKV, và ghi thành khác biệt). **Cần nâng `tidb_instance_type` (ví dụ c6i.4xlarge hoặc 8xlarge) trước khi đo hệ số tăng tốc chính thức**, và dùng cùng cỡ ở cả hai cụm.
- **Cập nhật 2026-11-23:** hệ số tăng tốc và nhóm A–C đã đo 3 lần lặp ở cả hai cụm (1 và 3 TiKV), nhóm E.a ở cụm 3 TiKV, đều với TiDB server c6i.4xlarge (xem các mục kết quả bên dưới); nhóm R đã đo (mục "Nhóm R"). **Chưa kiểm:** tác động riêng của chuyển leader lên TPS.
- Bài học hạ tầng: ở us-east-1c `m6i.large`, `m5.large` rồi cả `c6i.xlarge` đã hết capacity vào các thời điểm khác nhau (terraform thử lại tối đa 25 lần rồi báo lỗi; apply lại thì tạo nốt được; dry-run không phát hiện; xem lỗi bằng CloudTrail `RunInstances`); đĩa dữ liệu gắn trễ làm bootstrap PD lỗi sau 300 s (chạy lại `/var/lib/cloud/instance/scripts/part-001`); lỗi `env.sh` rỗng của `aws-tidb-up.sh` vẫn còn (viết tay).
- **Chưa làm (Tầng 2/3):** E.b/E.c (async commit, 1PC, độ phân tán), E.d, tùy chọn độ trễ mạng (nhóm R đã đo), MongoDB chia shard, thêm TiKV khi đang chạy.

## Kết quả đo chính thức: MySQL hai cỡ vCPU (AWS, 2026-11-22)

`results/official/2.3-aws/mysql/`: 30 lượt VALID trên MySQL-chỉnh 8.4.8 (nhóm A, B, C; W = 12, `configs/scaling.toml`, 64 client, P1/P2, 3 lần lặp), mỗi cỡ 15 lượt: 24 vCPU/60 GiB (buffer pool 3 GiB, đo trước) rồi 20 vCPU/44 GiB (buffer pool 1 GiB, đo sau, cùng dataset, đổi cỡ bằng `docker compose up --force-recreate`). Không có nhóm D, E (chỉ có ý nghĩa với TiDB). Báo cáo gộp cả TiDB: `results/official/2.3-aws/SUMMARY-speedup.md`.

| Cấu hình | TPS 20 vCPU | TPS 24 vCPU | 24 ÷ 20 |
| --- | --- | --- | --- |
| A: kho đều, θ = 0 | 1.222,2 | 1.140,8 | 0,93 |
| B: một kho, θ = 0,9 | 1.304,1 | 1.232,3 | 0,94 |
| C: P2 N=3 | 2.041,8 | 1.827,6 | 0,90 |
| C: P2 N=9 | 2.010,7 | 1.818,8 | 0,90 |
| C: P2 N=27 | 2.040,2 | 1.808,4 | 0,89 |

- **MySQL không tăng tốc khi thêm CPU:** hệ số 0,89–0,94 (ngược lại: cỡ 24 vCPU chậm hơn cỡ 20 vCPU 6–11%, p99 cao hơn 7–58% tùy nhóm). So với TiDB 3 TiKV ÷ 1 TiKV: 1,98–2,82. Lượt 24 vCPU nằm trong cùng khoảng ba lần lặp chặt (chênh nội bộ vài %), nên khác biệt giữa hai cỡ lớn hơn nhiễu lặp.
- **Nguyên nhân chưa được kiểm chứng.** Giả thuyết: MySQL bị chặn bởi ghi log bền (`sync_binlog=1` + `innodb_flush_log_at_trx_commit=1` trên một EBS), không phải CPU, nên thêm vCPU không giúp. Chưa giải thích được vì sao cỡ lớn chậm hơn; hai yếu tố gây nhiễu chưa tách được: (1) buffer pool khác nhau (3 GiB so với 1 GiB, cố ý theo cache TiKV, `docs/assumptions.md`) và (2) **thứ tự đo** (24 vCPU đo trước, 20 vCPU đo sau trên cùng dataset). Cần một lượt đối chứng (đo lại 24 vCPU sau 20 vCPU, hoặc cùng buffer pool) trước khi kết luận về nguyên nhân.
- **Warmup:** `results/official/warmup-analysis-mysql.md`; trung vị ramp 1,03 (20 vCPU) và 0,99 (24 vCPU).

## Nhóm R: chi phí replication (rf=1 so với rf=3, AWS, 2026-11-23)

`results/official/2.3-aws/tidb3-R/`: 30 lượt VALID trên cụm 3 TiKV (m6i.large, TiDB c6i.4xlarge, PD c6i.large, block cache 1 GiB), cùng dataset `configs/scaling.toml`, một kho, 64 client, lô mã 50, 3 lần lặp, 30 s warmup + 60 s đo. **Cùng một phiên:** đo rf=1 trước (`tidb3-rf1`), rồi nâng `max-replicas` lên 3 bằng PD API, chờ PD hội tụ (mọi store 638 Region, không còn miss-peer/pending-peer, leader 216/207/215), rồi đo rf=3 (`tidb3-rf3`, biến `FLASHSALE_TIDB_REPLICAS=3`). Giá trị `max_replicas` thật của PD được ghi trong manifest từng lượt (15 lượt = 1, 15 lượt = 3).

**Giả thuyết đặt trước khi đo** (viết trong kế hoạch phiên; chưa kịp ghi vào tài liệu này trước khi chạy): H-R1: với P1 trên hot SKU rf=3 giảm TPS ít (nút cổ chai là một Region leader) nhưng tăng p99; H-R2: với P2 N=27 rf=3 giảm TPS rõ (TiKV đã gần 200% CPU); H-R3: tải đều bị ảnh hưởng nhỏ hơn.

| Cấu hình | TPS rf=1 | TPS rf=3 | Thay đổi | p99 rf=1 → rf=3 (ms) |
| --- | --- | --- | --- | --- |
| A: P1, θ=0 (tải đều) | 2.232 | 1.413 | −37% | 100 → 161 |
| B: P1, θ=0,9 | 789 | 529 | −33% | 749 → 1.069 |
| C: P2 N=3, θ=0,9 | 1.631 | 1.086 | −33% | 425 → 600 |
| C: P2 N=9, θ=0,9 | 2.270 | 1.348 | −41% | 118 → 159 |
| C: P2 N=27, θ=0,9 | 2.247 | 1.319 | −41% | 76 → 116 |

(TPS trung vị của 3 lần lặp; khoảng min–max trong `INDEX.csv`; hệ số dao động ở N=27 rf=3 là 1.279–1.707.)

- **Kết quả:** rf=3 giảm TPS 33–41% ở mọi cấu hình và tăng p99 đồng thời. Mức giảm **không nhỏ ở hot SKU** như H-R1 dự đoán (B: −33%, không phải "ít"); H-R2 đúng về chiều (−41% ở N=27) và H-R3 **sai** (tải đều A giảm −37%, gần như bằng các ô khác).
- **Bằng chứng về nguyên nhân (CPU từng TiKV, % của một vCPU; TiKV m6i.large chỉ có 2 vCPU nên trần 200%):** ở rf=3 cả ba TiKV gần trần ở mọi cấu hình (A: 198/198/199; N=27: 195/189/200). Ở rf=1, cấu hình B có TiKV còn dư CPU (126/61/107) nhưng rf=3 đẩy lên 173/143/190 trong khi TPS giảm: mỗi ghi phải nhân ba (log Raft và apply), nên TiKV trở thành nút cổ chai ở mọi ô; thêm vòng quorum Raft làm p99 tăng. Đây là bằng chứng nhất quán với cơ chế, chưa phải chứng minh: không đo metric Raft (commit/apply latency) và không tách riêng I/O.
- **Giới hạn:** rf=1 đo trước rf=3 trong cùng phiên nên thứ tự có thể lẫn với trôi hệ thống (chưa đo lại rf=1 sau rf=3). Đối chiếu gián tiếp: rf=1 của phiên này khớp phiên 22/11 (B 789 so với 751; N=27 2.247 so với 2.121), nên rf=1 không trôi giữa hai phiên, nhưng không chứng minh rf=3 không bị ảnh hưởng thứ tự. Chỉ 3 lần lặp mỗi ô, TiKV chỉ 2 vCPU (kết luận về mức giảm chỉ đúng cho cỡ máy này). rf=1 không đại diện độ bền production (mục "Nguyên tắc kiểm soát biến"). Warmup: `results/official/warmup-analysis-tidb3-R.md`: 4/30 lượt ngoài khoảng ramp 0,9–1,1, trung vị ramp 1,02.
