# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | performance | 64 | uniform | 0.0 | False | False | True | ebs_iops=10000 | 3 | 3/3 | 2158.3 (2134.5–2160.1) | 106.1 |
| mysql | performance | 64 | uniform | 0.0 | False | False | True | ebs_iops=3000 | 3 | 3/3 | 1035.2 (1034.8–1130.1) | 356.7 |
| mysql | performance | 64 | uniform | 0.9 | False | False | True | ebs_iops=10000 | 3 | 3/3 | 2146.8 (2130.5–2158.6) | 111.1 |
| mysql | performance | 64 | uniform | 0.9 | False | False | True | ebs_iops=3000 | 3 | 3/3 | 1112.0 (1104.3–1120.5) | 359.8 |
| mysql | performance | 8 | uniform | 0.0 | False | False | True | ebs_iops=10000 | 3 | 3/3 | 404.8 (404.4–406.2) | 48.8 |
| mysql | performance | 8 | uniform | 0.0 | False | False | True | ebs_iops=3000 | 3 | 3/3 | 399.6 (398.5–401.9) | 52.3 |

## Kiểm tra warmup 30 giây

18/18 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
