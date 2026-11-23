# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2053.0 (2036.8–2062.0) | 201.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 704.9 (684.2–773.2) | 896.6 |
| tidb | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 568.5 (532.8–619.7) | 588.5 |

## Kiểm tra warmup 30 giây

9/9 lượt có chuỗi TPS theo giây; 6 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 69951e0b70ee425580b975bb5c0e7304 | mysql | migration | 64 | 0.5 | -49.7 |
| 8ac1530ebd024e278910b14d2b5e2c01 | mysql | migration | 64 | 0.5 | -28.8 |
| c61b51d100eb48cdb177ef66432e19fc | tidb | migration | 64 | 0.5 | -57.9 |
| e7f98b40739c4854b735976e0a6abcc9 | tidb | migration | 64 | 0.5 | -59.5 |
| ef36d16e56b549c288696686176a2d29 | tidb | migration | 64 | 0.5 | -58.9 |
| f3f544f26e9e4b3e8c74416587d2b015 | mysql | migration | 64 | 0.5 | -54.6 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
