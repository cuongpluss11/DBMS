# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 2232.0 (2226.2–2321.8) | 100.4 |
| tidb | smoke | 2 | single-warehouse | 0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True |  | 1 | 1/1 | 175.5 (175.5–175.5) | 9.6 |
| tidb | smoke | 2 | single-warehouse | 0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | tidb-it-check | 1 | 1/1 | 176.0 (176.0–176.0) | 7.6 |

## Kiểm tra warmup 30 giây

3/5 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
