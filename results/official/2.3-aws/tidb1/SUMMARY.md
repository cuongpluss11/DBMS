# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 616.2 (588.5–634.2) | 912.1 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 845.2 (825.5–908.1) | 197.5 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 707.1 (704.7–1035.2) | 950.0 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 848.5 (743.8–923.4) | 286.6 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 1136.1 (956.2–1181.4) | 199.7 |
| tidb | scaling-autoinc | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 765.9 (719.6–861.5) | 308.8 |
| tidb | scaling-autorandom | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 788.1 (744.6–834.0) | 302.3 |

## Kiểm tra warmup 30 giây

21/21 lượt có chuỗi TPS theo giây; 7 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 186ce0dbc7a44eb18d38b58a24643470 | tidb | scaling | 64 | 0.0 | 11.7 |
| 2a26457611094feca1236f196cf6e2ad | tidb | scaling-autoinc | 64 | 0.0 | 29.2 |
| 3fd4b8437b7e442e8c49747bba38d06d | tidb | scaling | 64 | 0.9 | -11.0 |
| 5c9cd3f6941e4ee4a99d1f40aa478179 | tidb | scaling-autoinc | 64 | 0.0 | -28.5 |
| c374d504614549be81d4f3751ec2abe8 | tidb | scaling | 64 | 0.9 | -11.8 |
| cb53a517511b40b0b40d895be33be26c | tidb | scaling | 64 | 0.9 | 44.3 |
| d3f4b7c947f14de1993a87dac13a3178 | tidb | scaling-autorandom | 64 | 0.0 | -16.9 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
