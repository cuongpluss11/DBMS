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
| MySQL mốc | A, B, C trên MySQL-chỉnh hai cỡ máy (8 vCPU/20 GiB và 12 vCPU/36 GiB) | xem đầu `run-matrix-2.3.sh` (`m6i.4xlarge`, `FLASHSALE_REMOTE_BUDGET_*`) |

Mọi điểm đều chạy ba luật tồn kho và đối soát của đề; đơn nhiều kho đối soát theo `ol_supply_w_id`.

## Đơn nhiều kho (nhóm E)

`order_warehouses_min/max` (1–4) và `warehouse_groups`: kho nhà được chọn như thường; mỗi đơn lấy `k` kho khác nhau (k ngẫu nhiên trong [min, max]), kho còn lại chỉ chọn trong cùng nhóm với kho nhà (W chia đều thành các nhóm liên tiếp), mỗi kho khác cấp đúng một món (cần ít nhất k món khác nhau; hiếm khi trùng món thì chạm ít kho hơn k). `Request.supply` ghi kho cung cấp từng món; `o_all_local` = 0 nếu có món lấy từ kho khác. Cấu hình mặc định (một kho) giữ nguyên dãy số ngẫu nhiên của 2.1. Không dùng với `hot_item`, một kho, stored procedure hay MongoDB (b).

## Đặt Region/leader (`--placement`)

Chỉ TiDB. Trước warmup của mỗi lượt (ngoài thời gian đo): chia `stock` (và `stock_slot` khi dùng P2; với `--placement-scope all` thêm `district`, `customer`, `orders`, `new_order`, `order_line`) bằng `SPLIT TABLE t BY (w, 0, ...)` với đủ mọi cột khóa (yêu cầu của khóa cụm nhiều cột), chuyển leader bằng PD HTTP API (`transfer-peer` khi một bản sao, `transfer-leader` khi nhiều bản sao), tạm dừng `balance-leader/region/hot-region-scheduler` và đặt các giới hạn lập lịch (`leader/region/hot-region/merge-schedule-limit`) về 0, rồi **đọc lại `SHOW TABLE ... REGIONS` để xác nhận** (chờ tối đa 180 s; sai thì lượt bị INVALID `placement_failed`, không chạy tiếp). Sau lượt đo: ghi `TIDB_HOT_REGIONS`, khôi phục bộ lập lịch (kể cả khi lỗi). `spread`: leader kho `w` về TiKV `(w−1) mod n` ("tách": các kho cùng nhóm ở các TiKV khác nhau); `group`: cả nhóm kho về một TiKV ("chung theo nhóm"). Slot (nhóm C): mỗi (kho, món nóng, slot) của `--placement-slot-items` món đầu (mặc định 5) là một Region, slot `s` về TiKV `s mod n`. Bằng chứng nằm ở `result.json` (`placement_result`: số Region mỗi TiKV theo bảng, cấu hình Load Base Split `split.*`, Region nóng sau lượt) và `manifest.dbms.commit_options` (hai biến `tidb_enable_async_commit`, `tidb_enable_1pc`).

## Khóa orders (nhóm D)

`orders_key = autoinc | auto_random`: `orders` đổi sang khóa chính một cột `o_seq BIGINT` (`AUTO_INCREMENT` hoặc `AUTO_RANDOM`, clustered), `(o_w_id, o_d_id, o_id)` thành UNIQUE phụ; fingerprint dataset khác nên cần dataset riêng; chỉ TiDB.

## Hệ số tăng tốc

`flashsale report` có thêm mục "Hệ số tăng tốc": TPS trung vị của cụm 3 TiKV chia cho 1 TiKV (TiDB), hoặc 12 vCPU chia cho 8 vCPU (MySQL), ghép theo từng nhóm giống hệt nhau về mọi tham số khác; chỉ tính khi hai phía có lượt VALID. `INDEX.csv` có thêm `tikv_count`, `vcpus`, `orders_key`, `placement`, `placement_scope`, `order_warehouses`, `warehouse_groups`.

## Đã kiểm thử / chưa kiểm thử

- Unit test với PD và TiDB giả lập (`tests/test_scaling.py`; toàn bộ 75 test không cần DBMS PASS). Đơn nhiều kho trên MySQL 8.4.8 thật (Docker máy dev, sơ bộ): smoke 1, 2 và 3–4 kho/đơn đều VALID với hết hàng thực.
- **Smoke trên TiDB v8.5.7 thật, AWS 2026-11-21 (sơ bộ, 1 lần lặp, 10 s + 20 s; stack `tidb1` với TiKV `c6i.xlarge` thay cho `m6i.large` vì AWS hết capacity m6i.large/m5.large ở us-east-1c; đã `terraform destroy`; bằng chứng ở `.work/g23-smoke-aws/`):**
  - Dataset W = 12 nạp được (1,2 triệu dòng stock). Nhóm A với `--placement spread` VALID (≈1.100 TPS; `tidb_cpu_100pct_of_limit`: TiDB server 4 vCPU là nút thắt như 2.1).
  - Phát hiện và đã sửa: bảng lớn tự tách Region theo kích thước (13 Region thay vì 12) nên cách đếm Region ban đầu sai; nay giải mã `START_KEY` (`t_<id>_r_` + `03` + 8 byte đã lật bit dấu cho mỗi cột khóa) để ánh xạ mọi Region về kho và kiểm tra ranh giới tách có thật.
  - PD HTTP API xác nhận trên PD thật: `GET /stores`, `/config/replicate`, `/config/schedule`, `/schedulers`; tạm dừng 3 scheduler và đặt bốn giới hạn lập lịch về 0 rồi khôi phục (đã đọc lại: không scheduler nào còn tạm dừng, các giới hạn về 4, 2048, 4, 8, nên `delay: 0` tiếp tục được scheduler); `POST /operators` nhận đúng tên trường `name`, `region_id`, `to_store_id` (thiếu thì báo "missing store id", tên lạ thì "unknown operator", chuyển về chính leader hiện tại thì "no operator step is built").
  - `SPLIT TABLE ... BY (w, 0, ...)` (đủ cột khóa) hoạt động trên `stock`, `district`, `customer`, `new_order`, `order_line` (phạm vi `all`).
  - Nhóm D: `AUTO_RANDOM` (mặc định 5 bit shard, `o_seq` ngẫu nhiên) và `AUTO_INCREMENT` (`o_seq` tuần tự) cho `orders` đều VALID; `orders` không bị tách theo kho khi dùng `o_seq`; cấu hình Load Base Split (`split.*`) ghi được vào bằng chứng (đã sửa lỗi pymysql định dạng `%` làm trống trường này); `commit_options` ghi vào manifest.
- **NOT TESTED:** việc chuyển leader/peer **thật** giữa nhiều TiKV (cụm `tidb1` chỉ có một store nên `transfer-peer`/`transfer-leader` chưa từng chạy; chỉ biết PD nhận tên trường), cụm `tidb3`, nhóm B, C, E.a trên TiDB, và mọi hệ số tăng tốc. Chưa có số đo chính thức nào.
- Bài học hạ tầng: ở us-east-1c `m6i.large` và `m5.large` đã hết capacity (terraform thử lại mãi, dry-run không phát hiện); đĩa dữ liệu gắn trễ làm bootstrap PD lỗi sau 300 s (chạy lại `/var/lib/cloud/instance/scripts/part-001`); lỗi `env.sh` rỗng của `aws-tidb-up.sh` vẫn còn (viết tay).
- **Chưa làm (Tầng 2/3):** E.b/E.c (async commit, 1PC, độ phân tán), E.d, nhóm R, tùy chọn độ trễ mạng, MongoDB chia shard, thêm TiKV khi đang chạy.
