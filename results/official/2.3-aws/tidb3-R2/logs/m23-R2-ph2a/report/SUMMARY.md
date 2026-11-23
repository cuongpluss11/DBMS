# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | tidb3-ph1-rf3 | 3 | 3/3 | 667.1 (637.1–667.5) | 895.5 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | tidb3-ph1-rf3 | 3 | 3/3 | 1272.2 (1267.0–1279.1) | 127.7 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | tidb3-ph1-rf3 | 3 | 3/3 | 1029.7 (1027.3–1093.0) | 638.4 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | tidb3-ph1-rf3 | 3 | 3/3 | 1279.9 (1212.0–1293.7) | 179.9 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | tidb3-ph1-rf3 | 3 | 3/3 | 1597.3 (1259.7–1720.2) | 133.9 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | tidb3-ph2-rf1 | 3 | 3/3 | 2147.0 (1616.7–2197.2) | 101.7 |

## Kiểm tra warmup 30 giây

18/18 lượt có chuỗi TPS theo giây; 1 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 6cb90b6822c64f9fae59617b1eccb6b8 | tidb | scaling | 64 | 0.9 | 12.7 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
