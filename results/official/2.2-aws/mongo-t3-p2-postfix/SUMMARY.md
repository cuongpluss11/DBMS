# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 1500.2 (1500.2–1500.3) | 27.9 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 2500.0 (2499.9–2500.1) | 76.8 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 3099.5 (3096.1–3100.0) | 315.1 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 3698.7 (3670.4–3699.1) | 327.0 |

## Kiểm tra warmup 30 giây

12/12 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
