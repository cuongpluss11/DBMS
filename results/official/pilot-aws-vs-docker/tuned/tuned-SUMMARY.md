# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | ytd | idem | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | baseline-tuned | 8 | uniform | 0 | False | False | True | 3 | 3/3 | 394.7 (394.2–397.7) | 53.5 |

## Kiểm tra warmup 30 giây

3/3 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
