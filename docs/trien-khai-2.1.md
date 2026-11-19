# Triển khai mục 2.1 cho nhóm ba người

Mỗi thành viên dùng một VM Ubuntu 24.04 LTS x86_64 để chạy DBMS được giao. Ba VM dùng cùng cấu hình và checkout cùng một Git commit từ repo của nhóm. Toàn bộ cụm TiDB ở trên VM của TV3.

## 1. Phân công và thứ tự bàn giao

| Người phụ trách | Việc cần làm | Bằng chứng bàn giao |
| --- | --- | --- |
| **TV1 · VM MySQL** | Chốt Git commit, thông số VM và cấu hình so sánh. Kiểm tra MySQL 8.4.8 dùng InnoDB và giữ cấu hình giao dịch mặc định. Chạy hai điểm baseline θ=0, uniform và single-warehouse. | `doctor.json`, phiên bản MySQL, log integration, hai nhóm run ID baseline và bảng kết quả chung. |
| **TV2 · VM MongoDB** | Kiểm tra MongoDB 8.0.20 ở mode A. Xác nhận replica set `flashsale` có primary, 9 collection logic và đường đi qua chỉ mục. Kiểm tra New-Order đa tài liệu, rollback khi thiếu hàng, Payment và gửi lại cùng request ID. | `doctor.json`, `status.json`, log integration, smoke run ID, manifest và kết quả của những profile nhóm giao. |
| **TV3 · VM TiDB** | Kiểm tra TiDB, PD và TiKV v8.5.7. Xác nhận 1 PD, 1 TiDB, 3 TiKV ở trạng thái Up và `max_replicas=1`. Kiểm tra DDL `history`, cấu hình cache TiKV và phân bố Region quan sát được. | `doctor.json`, `status.json`, log integration, smoke run ID, DDL `history` và Region `stock`/`history` trong manifest, cùng kết quả của những profile nhóm giao. |

Thứ tự làm việc là chốt commit và cấu hình → chuẩn bị ba VM → kiểm tra integration và smoke trên cả ba hệ → đo theo các profile đã thống nhất → gom kết quả. Mỗi người tự vận hành VM của mình. TV1 chia sẻ SHA, danh sách profile và mức client ngay từ đầu, rồi tổng hợp sau khi cả ba hoàn tất.

## 2. Chuẩn bị ba VM cùng cấu hình

1. TV1 chốt thông số vCPU, RAM và kiểu lưu trữ. Cả ba dùng Ubuntu 24.04 LTS x86_64, cùng phiên bản Python, Docker và Compose, và cùng tổng ngân sách container 8 CPU, 16 GiB RAM. Nếu các VM nằm trên những máy vật lý khác nhau, ghi lại model CPU và loại ổ đĩa của từng host khi có thông tin.
2. Cài công cụ trên từng VM theo [README](../README.md). TV1 gửi URL repo và SHA của commit đã có trên GitHub. Trên mỗi VM, thay URL và SHA trong ví dụ bằng giá trị của nhóm. Nếu đã clone, chạy từ gốc repo và bắt đầu ở `git fetch origin`.

```bash
git clone URL_REPO_NHOM DBMS
cd DBMS
git fetch origin
git checkout --detach SHA_COMMIT_NHOM
git rev-parse HEAD
git status --short
```

3. Cả ba xác nhận SHA trùng nhau và checkout sạch. Từ gốc checkout, tạo `.venv`, chạy unit test và lưu thông tin VM.

```bash
bash scripts/setup.sh
source .venv/bin/activate
mkdir -p .work/muc-2.1
flashsale doctor | tee .work/muc-2.1/doctor.json
lscpu > .work/muc-2.1/cpu.txt
lsblk -o NAME,SIZE,TYPE,ROTA > .work/muc-2.1/storage.txt
```

Trước khi đo, đối chiếu thông tin ba VM và xác nhận đĩa Docker đủ chỗ. Một lần nạp W=10 có 1.000.000 dòng `stock` và hàng triệu dòng `order_line`. Nếu VM chỉ đủ tài nguyên cho smoke, giữ profile W=10 và ghi các điểm chưa chạy là **NOT TESTED**. Nếu nhiều VM dùng chung một host vật lý, chạy các lượt đo lần lượt.

## 3. Từng thành viên kiểm chứng DBMS của mình

Chạy trong Bash ở gốc checkout. Đặt `DBMS=mysql` cho TV1, `DBMS=mongo` cho TV2 hoặc `DBMS=tidb` cho TV3. Chạy từng bước. Sửa lỗi readiness hoặc integration trước khi sang bước đo.

```bash
source .venv/bin/activate
set -o pipefail
DBMS=mysql
EVIDENCE="$PWD/.work/muc-2.1/$DBMS"
mkdir -p "$EVIDENCE"

flashsale doctor
flashsale start "$DBMS"
flashsale status "$DBMS" | tee "$EVIDENCE/status.json"
FLASHSALE_TEST_ENGINE="$DBMS" python -m pytest -m integration -q \
    2>&1 | tee "$EVIDENCE/integration.log"
flashsale smoke "$DBMS" | tee "$EVIDENCE/smoke.json"
```

- **MySQL** kiểm tra `version` và `storage_engine` trong kết quả trạng thái. Ghi nhận isolation và `max_connections` mặc định.
- **MongoDB** kiểm tra `replica_set=flashsale`. `status` chỉ thành công khi thấy primary. Đọc log integration để xác nhận giao dịch nhiều tài liệu và các bài rollback, replay.
- **TiDB** kiểm tra ba mục trong `store_versions` và `max_replicas=1`. Mở manifest của smoke hoặc lượt đo, xem `access_paths.regions` và `access_paths.history_ddl`. Ghi số Region và store giữ leader tại thời điểm quan sát. Đối chiếu `SHARD_ROW_ID_BITS=4`, `PRE_SPLIT_REGIONS=4` và block cache TiKV 512 MiB theo [cấu hình TiKV](../docker/tikv.toml).
- Với cả ba hệ, cần smoke `VALID`, có tình huống hết hàng và đủ bằng chứng EXPLAIN, CSV, JSON. Các ca integration của hai DBMS ngoài hệ đã chọn sẽ được pytest đánh dấu skipped.

Sau khi kiểm tra xong, gửi trạng thái cho nhóm và có thể dừng hệ bằng `flashsale stop "$DBMS"`. Khi cả ba hệ đã đạt integration và smoke, mỗi người đo trên VM của mình.

## 4. Chọn điểm đo trước khi chạy

| Profile | Ai chạy | Thiết lập mặc định và mục đích |
| --- | --- | --- |
| `configs/baseline.toml` | TV1 trên MySQL | W=10, 8 client, θ=0, kho uniform, tồn đầu 10^9. Chạy thêm một điểm single-warehouse. Điểm một client chỉ dùng khi cần chẩn đoán. |
| `configs/performance.toml` | Cả ba, trên VM riêng | W=10, 8 client, θ=0,5, kho uniform, tồn đầu 10^9. Dùng cùng cấu hình trên ba hệ nếu nhóm đo so sánh hiệu năng. |
| `configs/correctness.toml` | Cả ba, trên VM riêng | W=10, 8 client, kho 1 và một món hot, tồn đầu 1.000. Kiểm tra cả ba luật và có tình huống hết hàng thực tế. |
| `configs/baseline-single-warehouse.toml` | TV1 trên MySQL | Điểm θ=0 kiểu "một kho" của đề (cùng dataset với baseline, dùng chung một lần `load`). |
| `configs/baseline-1client.toml` | TV1 trên MySQL | Điểm 1 client dùng cho phân tích "việc có ích" ở 2.5. |
| `configs/payment-ytd.toml` | Cả ba | Lượt riêng bật cập nhật `w_ytd`, `d_ytd` ở Payment để thấy điểm nóng thứ ba (khác TPC-C chuẩn, ghi rõ trong báo cáo). |
| `configs/idempotency-off.toml` | Cả ba, tùy chọn | Lượt phụ tắt mã chống trùng của đề (dataset và lược đồ riêng, không UNIQUE). INVALID luật 3 là kết quả dự kiến; không xếp hạng. Cần tinh chỉnh `client_timeout_seconds` khi chạy thật. |
| `configs/smoke.toml` | Cả ba | Dữ liệu nhỏ để kiểm tra đường chạy, có nhãn `smoke`. |

Mỗi điểm đầy đủ có 3 lần lặp, mỗi lần gồm 30 giây warmup và 60 giây đo. Các cấu hình dùng New-Order và Payment theo tỉ lệ 1:1, tắt cập nhật YTD của warehouse và district ở Payment. Dùng `--concurrency` khi nhóm thống nhất mức khác với 8. Giữ cùng số client cho các điểm đem so sánh. Với MySQL ở 256 client, dùng `FLASHSALE_MYSQL_MAX_CONNECTIONS=258 flashsale start mysql` và ghi giá trị thực trong manifest. Chạy các mức client còn lại theo kế hoạch nhóm đã chốt.

### Nạp và chạy một điểm

Dùng terminal đã đặt `DBMS` và `EVIDENCE` ở bước 3. Chạy `flashsale start "$DBMS"` nếu hệ đang dừng. Chọn đúng một cặp `POINT` và `PROFILE`. TV1 dùng `POINT=baseline-uniform` và `PROFILE=configs/baseline.toml` cho điểm mốc. Cả nhóm dùng `POINT=correctness` và `PROFILE=configs/correctness.toml` cho lượt kiểm luật.

```bash
POINT=performance
PROFILE=configs/performance.toml

flashsale load "$DBMS" --config "$PROFILE" | tee "$EVIDENCE/$POINT-load.json"
DATASET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' \
    "$EVIDENCE/$POINT-load.json")

flashsale run "$DBMS" --config "$PROFILE" --dataset "$DATASET" --reset-between \
    | tee "$EVIDENCE/$POINT-runs.json"
```

Sau `load`, xác nhận `status=ready` và đủ chín bảng hoặc collection. Profile W=10 có 10 warehouse, 100 district, 100.000 item, 1.000.000 stock, 300.000 customer, 300.000 history, 300.000 orders và 90.000 new_order. Đối chiếu số dòng `order_line` từ loader theo cùng seed, với 5–15 dòng mỗi đơn cơ sở.

Lưu tên `DATASET` và log nạp tương ứng. `--reset-between` khôi phục dataset giữa các lần lặp trong cùng lệnh. Sau khi lệnh kết thúc, dataset đã qua sử dụng. Muốn chạy một điểm mới bằng cùng dataset, lấy đúng tên dataset đã nạp và reset có xác nhận. Khi đổi kích thước, tồn đầu hoặc seed nạp, tạo dataset riêng bằng profile mới.

### TV1 chạy baseline MySQL single-warehouse

Hoàn tất điểm uniform, lưu đủ ba run ID và, nếu cần, chạy lại validator trước khi reset. Sau đó đọc tên dataset từ log nạp baseline uniform. Chạy điểm một kho với cùng profile, chỉ đổi cách chọn kho.

```bash
BASELINE_DATASET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["database"])' \
    "$EVIDENCE/baseline-uniform-load.json")

flashsale reset mysql --config configs/baseline.toml \
    --dataset "$BASELINE_DATASET" --confirm "$BASELINE_DATASET"
flashsale run mysql --config configs/baseline.toml \
    --dataset "$BASELINE_DATASET" --warehouse-mode single-warehouse --reset-between \
    | tee "$EVIDENCE/baseline-single-warehouse-runs.json"
```

Dùng `--concurrency 1 --repetitions 1` cho điểm chẩn đoán một client sau khi khôi phục dataset, nếu nhóm cần điểm đó. Ghi riêng vì số client và số lần lặp khác các điểm chính.

## 5. Kiểm tra và bàn giao bằng chứng

Mỗi người đối chiếu từng `results/<run_id>/`:

1. **Manifest** có phiên bản DBMS, image/digest, Git commit, CPU/RAM, dataset, seed, kiểu chọn kho, θ, số client và thời lượng. Kiểm tra `access_paths.indexed` và kế hoạch truy vấn. TV3 kiểm thêm Region và DDL `history`.
2. **Đối soát** mở `result.json` và kiểm tra `validation.status=VALID` cùng ba luật. Tồn cuối luôn không âm. Chênh lệch tồn của từng kho–món bằng số bán tính từ `order_line` của đơn đã commit. Mỗi request New-Order thành công khớp đúng một đơn. Với correctness, kiểm thêm số lượt hết hàng trong `out_of_stock_all` của các pha.
3. **Số đo** dùng pha `measurement` trong `result.csv` hoặc `result.json`. Ghi TPS thành công, p50/p95/p99, abort, retry, phân loại lỗi, phần trăm rank 1 và top 100, CPU và lock wait nếu có. Giữ giá trị `null` khi metric không thu được. Giữ từng lần lặp để kiểm tra độ dao động. [Định nghĩa trường kết quả](experiment-2.1.md)
4. **Trạng thái** giữ lại mọi lượt `INVALID` để truy nguyên và để riêng khỏi bảng so sánh. Khi runner dừng sớm vì INVALID, ghi số lần thực tế và lý do. Các điểm chỉ có smoke hoặc chưa chạy đầy đủ được ghi đúng phạm vi.

Runner đã tự đối soát sau mỗi lần lặp. Nếu cần xác nhận lại lượt cuối của một dataset, thay `RUN_UUID_HEX` bằng `run_id` thực và chạy khi hệ còn hoạt động, trước lần reset tiếp theo.

```bash
flashsale validate "$DBMS" --run-id RUN_UUID_HEX
flashsale stop "$DBMS"
```

Mỗi người bàn giao bảng ngắn có **VM, DBMS, Git SHA, profile, dataset, số lần lặp, run ID, trạng thái và vấn đề phát hiện**. Tạo ba thư mục `mysql/`, `mongo/` và `tidb/` trong nơi lưu kết quả của nhóm. Mỗi người chép `doctor.json`, thông tin CPU/đĩa, log, và các thư mục `results/<run_id>/` vào thư mục của hệ mình. Giữ volume, `.env` và dữ liệu thực nghiệm lớn tại VM. Repo Git chứa mã, cấu hình và tài liệu dùng chung.

TV1 đối chiếu Git commit, cấu hình VM, ngân sách container và tham số workload trước khi gộp. Nếu host khác CPU hoặc ổ đĩa, ghi chênh lệch trong báo cáo vì chúng có thể ảnh hưởng TPS và độ trễ. Hai điểm baseline MySQL θ=0 được ghi riêng. Bảng so sánh ba hệ dùng các run cùng profile performance, θ, kiểu chọn kho và số client.

## 6. Xử lý vướng mắc khi triển khai

| Hiện tượng | Cách xử lý |
| --- | --- |
| Docker không truy cập được | Kiểm tra Docker Engine, quyền nhóm Docker và chạy lại `bash scripts/doctor.sh --vm`. |
| Hệ khác của dự án đang chạy trên VM | Dừng đúng hệ đó bằng `flashsale stop ENGINE`, rồi kiểm tra lại bằng `flashsale doctor`. |
| `load` báo thiếu tài nguyên hoặc chưa tạo xong dataset | Giữ log, kiểm tra đĩa Docker và tạo dataset mới sau khi khắc phục. Có thể dùng smoke để chứng minh đường chạy trong lúc chờ tài nguyên W=10. |
| Dataset khác seed/kích thước hoặc đã dùng | Dùng profile khớp lúc nạp và reset đúng UUID khi muốn dùng lại. Với profile khác seed hay dữ liệu, nạp dataset mới. |
| EXPLAIN hoặc validator báo `INVALID` | Đọc manifest, mục `validation.errors` và `validation.protocol_errors`. Lưu run ID và nguyên nhân trước khi khắc phục, khôi phục dữ liệu rồi chạy lại theo cùng cấu hình. |
| Cần dọn môi trường khi kết thúc | Dùng `flashsale stop ENGINE` để giữ volume. Chỉ gọi `drop` khi nhóm đã xác nhận đúng dataset cần xóa. |

Mục 2.1 được nghiệm thu khi ba hệ có phiên bản và bằng chứng integration/smoke, kiểm đếm dữ liệu theo quy mô được giao, baseline MySQL có kết quả hợp lệ, các lần đo có manifest và đủ ba luật. Ghi rõ các điểm chưa kiểm chứng theo [bảng ánh xạ yêu cầu](requirements-2.1.md) và [các quyết định thực nghiệm](assumptions.md).
