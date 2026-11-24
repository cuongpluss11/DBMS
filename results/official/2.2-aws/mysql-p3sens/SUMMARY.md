# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-p3sens | 3 | 3/3 | 1787.9 (1787.6–1800.0) | 554.7 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-p3sens | 3 | 3/3 | 2040.8 (2040.7–2129.8) | 1736.4 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-p3sens | 12 | 12/12 | 1690.5 (1169.5–1800.0) | 2293.3 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-p3sens | 12 | 12/12 | 1506.1 (970.7–2109.9) | 3504.5 |

## Kiểm tra warmup 30 giây

30/30 lượt có chuỗi TPS theo giây; 4 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 1bb7c6dc809c47b7b27ddf9544daf388 | mysql | hotspot | 256 | 0.9 | -40.3 |
| ac8eaaa40f544f46ab76ab72393752a0 | mysql | hotspot | 256 | 0.9 | -59.9 |
| d235ad66f8b24f80a4b9c059283d3686 | mysql | hotspot | 256 | 0.9 | -42.6 |
| dc0f89290d57442382839b13f2a66443 | mysql | hotspot | 256 | 0.9 | 10.2 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
