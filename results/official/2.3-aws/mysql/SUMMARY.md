# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 1304.1 (1289.4–1307.0) | 688.0 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1232.3 (1227.5–1236.6) | 731.3 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 2040.2 (2022.5–2042.3) | 485.3 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1808.4 (1797.2–1809.5) | 589.0 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 2041.8 (2010.3–2055.7) | 553.4 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1827.6 (1801.4–1893.7) | 628.5 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 2010.7 (1977.0–2048.6) | 502.9 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1818.8 (1808.0–1820.6) | 591.2 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 1222.2 (1215.6–1237.9) | 479.1 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1140.8 (1090.3–1143.3) | 709.2 |

## Hệ số tăng tốc (TiDB: 3 TiKV ÷ 1 TiKV; MySQL: cỡ vCPU lớn ÷ cỡ vCPU nhỏ)

Chỉ ghép các nhóm giống hệt nhau về mọi tham số khác. Cột "TPS nhỏ" là 1 TiKV (TiDB) hoặc cỡ vCPU nhỏ (MySQL); "TPS lớn" là 3 TiKV hoặc cỡ vCPU lớn. Tăng tốc bằng tỉ số cỡ (3 với TiDB; 24÷20 = 1,2 với MySQL) nghĩa là mở rộng hiệu quả hoàn hảo, bằng 1 nghĩa là thêm tài nguyên vô ích.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | vị trí | khóa orders | kho/đơn | TPS nhỏ | TPS lớn | tăng tốc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | none/stock | composite | 1-1 | 1304.1 | 1232.3 | 0.94 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | none/stock | composite | 1-1 | 2040.2 | 1808.4 | 0.89 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | none/stock | composite | 1-1 | 2041.8 | 1827.6 | 0.90 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | none/stock | composite | 1-1 | 2010.7 | 1818.8 | 0.90 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | none/stock | composite | 1-1 | 1222.2 | 1140.8 | 0.93 |

## Kiểm tra warmup 30 giây

30/30 lượt có chuỗi TPS theo giây; 4 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 854161bb9f764656aff654b95314968c | mysql | scaling | 64 | 0.0 | -10.2 |
| 864389e70d0d4c648085c1394936296b | mysql | scaling | 64 | 0.9 | -11.0 |
| ac232efb220d4bf5840cf1f48eaece17 | mysql | scaling | 64 | 0.9 | 10.3 |
| c3ee986af58a4cf2a533de94fbd1d872 | mysql | scaling | 64 | 0.9 | 10.7 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
