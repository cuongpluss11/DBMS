# Hạ tầng AWS cho số đo chính thức (mục 2.1)

Theo bản chốt `bao_cao_DBMS_ban_chot.docx`: mỗi thành phần một VM riêng, một VM riêng chạy script tải, cùng một region và một AZ (`us-east-1`, `us-east-1c`), EBS gp3 cố định giống nhau cho mọi hệ. Docker Compose trong `docker/` vẫn dùng để phát triển và chạy thử.

**Trạng thái: CHƯA CHẠY.** Các file này chưa được `terraform init/plan/apply` trên tài khoản thật, nên mọi chi tiết đều là NOT TESTED cho đến khi bạn chạy thử.

## Những gì Terraform tạo

| `stack` | VM (mỗi cái một máy) | vCPU DBMS (không tính tải/monitor) |
| --- | --- | --- |
| `none` | `loadgen` (c6i.xlarge) | 0 |
| `mysql` | `loadgen` + `mysql` (c6i.4xlarge, giới hạn còn 12 vCPU/24 GiB bằng cpuset và mem_limit) | 12 |
| `mongo` | `loadgen` + `mongo` (như `mysql`) | 12 |
| `tidb3` | `loadgen`, `pd` (c6i.large), `tidb` (c6i.xlarge), 3 × `tikv` (c6i.large), `monitor` (c6i.large) | 2 + 4 + 6 = 12 |
| `tidb1` | như `tidb3` nhưng 1 TiKV | 8 |

Chỉ một `stack` DBMS tồn tại tại một thời điểm. Quota hiện xin là 64 vCPU (xem trạng thái ở `aws service-quotas`). Cụm `tidb3` dùng 12 + 4 (tải) + 2 (monitor) = 18 vCPU; `mysql` dùng 16 + 4 = 20 vCPU.

Mặc định: một VPC, một subnet ở một AZ, cluster placement group, security group chỉ cho SSH từ IP của bạn và mọi lưu lượng nội bộ trong nhóm. Mọi VM có IP công cộng (không dùng NAT gateway vì đắt hơn); SSH bị giới hạn bằng security group. Mỗi VM dữ liệu có một EBS gp3 riêng (100 GiB, 3000 IOPS, 125 MB/s là mức cơ bản, giống nhau ở mọi hệ).

**Giới hạn EBS của instance (đã kiểm tra bằng `aws ec2 describe-instance-types`):** `c6i.large` 3.600 IOPS cơ bản (650 Mbps), `c6i.xlarge` 6.000, `c6i.2xlarge` 12.000, `c6i.4xlarge` 20.000. Mức tối đa 40.000 IOPS chỉ là đợt burst ngắn (tín chỉ cỡ 30 phút mỗi ngày). TiKV trên `c6i.large` không giữ được quá ~3.600 IOPS, nên đặt ổ 10.000 IOPS cho cụm TiDB chỉ có tác dụng trong đợt burst rồi bị giảm, làm số đo không lặp lại được. Vì vậy mặc định giữ **3.000 IOPS / 125 MB/s cho mọi ổ ở mọi hệ**. Mức 10.000 IOPS chỉ dùng cho thí nghiệm riêng "độ nhạy của đĩa" trên một hệ (MySQL trên `c6i.2xlarge` trở lên), ghi rõ là thí nghiệm riêng và không so chéo giữa các hệ. Manifest ghi `db_tcp_rtt_ms` (RTT TCP tới DBMS) khi chạy remote.

**Điểm tương đương tài nguyên.** MySQL/MongoDB không có instance c6i đúng 12 vCPU, nên dùng c6i.4xlarge và giới hạn bằng cpuset `0-11` và 24 GiB. Đây là cách tài liệu cho phép, phải ghi vào báo cáo. VM monitor của TiDB và VM tải không tính vào ngân sách.

## Quy trình

### 0. Một lần
```powershell
cd infra/aws
copy terraform.tfvars.example terraform.tfvars   # sửa allowed_ssh_cidr = IP công cộng của bạn /32
terraform init
terraform validate
terraform fmt -check
```

### 1. Chỉ máy tải (rẻ nhất, để kiểm tra mạng và cài đặt)
```powershell
terraform plan -out plan.out    # kiểm tra số tài nguyên và loại instance
terraform apply plan.out
```
Cần bạn xem plan trước khi `apply`. Dừng hoặc `terraform destroy` khi không đo (đĩa EBS vẫn tính phí khi VM dừng).

### 2. MySQL hoặc MongoDB
Đặt `stack = "mysql"` (hoặc `mongo`) trong `terraform.tfvars`, `plan` và `apply`. Trên VM DBMS:
```bash
git clone <repo> && cd DBMS
# MySQL-mặc-định (mốc theo đề); với MySQL-chỉnh thêm FLASHSALE_MYSQL_BUFFER_POOL_BYTES=3221225472
docker compose -f docker/compose.mysql.yml -f infra/aws/compose/mysql.aws.yml up -d
```
Mở cổng cho máy tải đã được cấu hình trong file override. Ổ dữ liệu EBS đã được mount ở `/data` và Docker lưu volume ở `/data/docker`.

### 3. TiDB bằng TiUP
Đặt `stack = "tidb1"` hoặc `"tidb3"`. Terraform ghi `generated/topology-<stack>.yaml` với IP nội bộ thật. Từ VM `loadgen` (đóng vai máy điều khiển TiUP):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
tiup cluster check topology.yaml --user ubuntu -i ~/.ssh/flashsale_aws --apply   # kiểm tra và áp dụng cấu hình hệ điều hành
tiup cluster deploy flashsale v8.5.7 topology.yaml --user ubuntu -i ~/.ssh/flashsale_aws
tiup cluster start flashsale
```
Phiên bản v8.5.7 trùng với `docker/compose.tidb.yml`. Topology đặt `replication.max-replicas: 1`, `storage.block-cache.capacity: "1GiB"` (cùng giá trị ở cả hai cụm) và giữ mặc định đồng bộ log Raft. Grafana của cụm chạy trên VM `monitor` (cổng 3000): truy cập bằng SSH tunnel, không mở cổng ra Internet.

### 4. EBS snapshot và khôi phục
Sau khi nạp dữ liệu xong và dừng DBMS, tạo snapshot của ổ dữ liệu (`aws ec2 create-snapshot --volume-id ...`). Lần sau đặt `data_snapshot_id` (chỉ áp dụng cho `mysql`/`mongo`) và chạy `scripts/initialize-volume.sh` trên VM trước khi đo để đọc hết volume. Cụm TiDB dựng lại bằng TiUP và nạp lại dữ liệu, chưa có quy trình snapshot cho TiDB.

### 5. iostat khi đo
```bash
infra/aws/scripts/iostat-capture.sh results/<run>/io 100
```
Ghi `iostat -x` và `vmstat` mỗi giây trên VM DBMS để xác nhận nút thắt đĩa. VM MySQL/MongoDB/loadgen còn có `prometheus-node-exporter` (cổng 9100); VM TiDB dùng node_exporter do TiUP triển khai.

## Chạy script tải (Python) trên VM `loadgen` — chế độ remote
Code đã hỗ trợ chế độ remote (có unit test, **chưa thử trên AWS thật**). Trên `loadgen`:
```bash
git clone <repo> && cd DBMS
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pip install -e .
export FLASHSALE_DB_HOST=<IP nội bộ VM DBMS, hoặc IP TiDB server>
export FLASHSALE_REMOTE_NODES='<đầu ra terraform: flashsale_remote_nodes>'   # host, vCPU, RAM từng VM DBMS
export FLASHSALE_LOADGEN_CPUS=4          # để cảnh báo khi máy tải vượt 80% CPU
# TiDB: export FLASHSALE_PD_PORT=2379 FLASHSALE_TIDB_PORT=4000 FLASHSALE_TIKV_COUNT=3 (hoặc 1)
# MySQL/MongoDB: cổng theo compose override (FLASHSALE_MYSQL_PORT/FLASHSALE_MONGO_PORT, mặc định 13306/27018)
flashsale load mysql --config configs/baseline.toml
```
Khác với Docker cục bộ: `start`/`stop` bị chặn (dùng Terraform/TiUP/compose), kiểm tra Docker cục bộ bị bỏ qua, CPU lấy từ node_exporter (cổng 9100) của từng VM DBMS và của chính `loadgen`, ngân sách kiểm theo tổng vCPU/RAM các VM DBMS (mặc định 12 vCPU / 24 GiB; cụm 1 TiKV của 2.3 đặt `FLASHSALE_REMOTE_BUDGET_CPUS=8` và `FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES=17179869184`). Manifest ghi `mode: remote`, `db_host`, `remote_nodes`; `result.json` có `loadgen_cpu_pct` và cảnh báo `loadgen_cpu_*pct_of_limit` nếu máy tải quá tải.

## Chưa có
- Quy trình snapshot/khôi phục riêng cho dữ liệu TiDB (dựng lại bằng TiUP và nạp lại).
- `flashsale reset` vẫn khôi phục dataset bằng SQL/aggregation; EBS snapshot chỉ dùng để dựng lại stack MySQL/MongoDB nhanh, không thay `reset`.
- Mọi thứ trong thư mục này chưa được chạy trên AWS (NOT TESTED).

## Chi phí và dọn dẹp
Ước tính 0,7–0,9 USD mỗi giờ khi chạy một stack (giá on-demand, chưa tra giá hiện tại). Luôn `terraform destroy` khi không đo (xóa cả EBS, nên snapshot trước nếu cần giữ dữ liệu). Đã có AWS Budgets 150 USD. Không bao giờ commit `terraform.tfvars`, `*.tfstate` hay khóa SSH riêng.
