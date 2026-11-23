# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 789.4 (723.6–856.1) | 749.2 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 2247.1 (1820.0–2282.4) | 75.6 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 1630.9 (1395.0–1757.6) | 424.6 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 2270.1 (1533.4–2278.1) | 118.3 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | tidb3-rf1 | 3 | 3/3 | 2232.0 (2226.2–2321.8) | 100.4 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | tidb3-rf3 | 3 | 3/3 | 1413.2 (1375.5–1871.8) | 160.8 |
| tidb | smoke | 2 | single-warehouse | 0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True |  | 1 | 1/1 | 175.5 (175.5–175.5) | 9.6 |
| tidb | smoke | 2 | single-warehouse | 0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | tidb-it-check | 1 | 1/1 | 176.0 (176.0–176.0) | 7.6 |

## Kiểm tra warmup 30 giây

18/20 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
