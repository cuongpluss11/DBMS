# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | hotspot | 256 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2699.7 (2680.9–2722.1) | 353.5 |
| mongo | hotspot | 256 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 1152.8 (1149.7–1155.0) | 346.1 |
| mongo | hotspot | 256 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2681.8 (2664.0–2685.7) | 353.7 |
| mongo | hotspot | 256 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2679.2 (2672.8–2701.2) | 353.7 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2563.9 (2536.6–2566.4) | 352.9 |

## Kiểm tra warmup 30 giây

15/15 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
