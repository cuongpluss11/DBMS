# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | m23-tidb1-build2 | 3 | 3/3 | 631.0 (630.8–651.4) | 868.2 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1-build2 | 3 | 3/3 | 907.6 (859.2–925.7) | 183.1 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1-build2 | 3 | 3/3 | 849.5 (830.6–869.7) | 764.4 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1-build2 | 3 | 3/3 | 904.1 (867.6–917.2) | 276.5 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1-build2 | 3 | 3/3 | 1086.1 (1084.3–1169.2) | 217.3 |

## Kiểm tra warmup 30 giây

15/15 lượt có chuỗi TPS theo giây; 1 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 94e99ec074be47d08d26e7bc1b2c2e06 | tidb | scaling | 64 | 0.9 | -17.9 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
