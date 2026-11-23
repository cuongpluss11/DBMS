# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1450.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1441.2 (1441.1–1450.1) | 440.9 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1778.3 (1774.2–1785.1) | 640.7 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1916.5 (1893.8–2009.3) | 694.8 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 900.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 900.0 (900.0–900.0) | 106.2 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1450.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1438.3 (1380.5–1450.1) | 496.9 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1296.8 (1155.9–1378.8) | 2075.7 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1144.4 (1122.5–1344.2) | 2602.5 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 900.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 900.0 (899.5–900.0) | 55.5 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1450.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1450.1 (1450.1–1450.1) | 93.0 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1798.4 (1790.4–1800.0) | 580.0 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 2055.2 (2003.4–2146.8) | 1750.4 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 900.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 900.3 (900.3–900.3) | 50.5 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1450.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1450.1 (1450.1–1450.1) | 74.2 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1800.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1302.7 (1160.7–1367.8) | 4796.2 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2200.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 1099.8 (1066.2–1100.8) | 4990.1 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 900.0 | False | False | default | a | False | False | True | m22-mysql-t3 | 3 | 3/3 | 900.3 (899.7–900.3) | 47.7 |

## Kiểm tra warmup 30 giây

48/48 lượt có chuỗi TPS theo giây; 6 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 014f1a3baa52480db16824043d7091a1 | mysql | hotspot | 256 | 0.9 | -48.4 |
| 0c8e8157a4ff47c0b2198abf624cc58b | mysql | hotspot | 128 | 0.9 | -35.4 |
| 3bef382e73b94168bcb426894dc347ad | mysql | hotspot | 128 | 0.9 | -13.1 |
| 4098e47689cf410189e7b2b96a95d5dc | mysql | hotspot | 128 | 0.9 | -10.0 |
| e01e9360323f4ebe9c20101ac67e3102 | mysql | hotspot | 128 | 0.9 | -27.7 |
| e8a76f478b314c1ab62546a4776fba0a | mysql | hotspot | 128 | 0.9 | 27.1 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
