# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | mysql-ctl-ph1-20vcpu | 3 | 3/3 | 1233.7 (1210.0–1241.4) | 688.5 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | mysql-ctl-ph1-20vcpu | 3 | 3/3 | 1938.0 (1927.8–1973.0) | 552.8 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | mysql-ctl-ph1-20vcpu | 3 | 3/3 | 1901.4 (1894.0–2002.5) | 597.5 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | mysql-ctl-ph1-20vcpu | 3 | 3/3 | 1919.8 (1900.0–1927.1) | 559.6 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | mysql-ctl-ph1-20vcpu | 3 | 3/3 | 1201.0 (1192.9–1324.7) | 672.2 |

## Kiểm tra warmup 30 giây

15/15 lượt có chuỗi TPS theo giây; 3 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 5eec23c1e6184f16b07ecac33d5347ba | mysql | scaling | 64 | 0.0 | 40.1 |
| bb643eb0ee194ff5a0c75ad61ae92d01 | mysql | scaling | 64 | 0.9 | 14.8 |
| d000ab9748464e1baf522a594f59e76e | mysql | scaling | 64 | 0.0 | 10.4 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
