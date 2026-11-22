# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1255.2 (1254.7–1349.5) | 578.2 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1104.8 (1094.2–1106.0) | 619.5 |

## Kiểm tra warmup 30 giây

6/6 lượt có chuỗi TPS theo giây; 4 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 4a0f0128fa2c4165b963ae3551105d14 | mysql | migration | 64 | 0.5 | -23.7 |
| 9d8c1ff25483498493c2850212a3a179 | mysql | migration | 64 | 0.5 | -14.2 |
| e0769c6950ac4e6c85f5a5b34b7afa8c | mysql | migration | 64 | 0.5 | -17.8 |
| e371ee0a7bc14528bacce5238de9f12d | mysql | migration | 64 | 0.5 | -25.2 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
