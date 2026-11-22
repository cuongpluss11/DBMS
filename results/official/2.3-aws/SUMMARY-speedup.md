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
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 616.2 (588.5–634.2) | 912.1 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 751.2 (732.9–754.0) | 754.0 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 845.2 (825.5–908.1) | 197.5 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2121.2 (1544.7–2187.9) | 73.3 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 707.1 (704.7–1035.2) | 950.0 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1725.5 (1319.0–1736.8) | 387.8 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 848.5 (743.8–923.4) | 286.6 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2086.5 (1643.3–2301.1) | 95.4 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 1136.1 (956.2–1181.4) | 199.7 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2021.6 (1664.3–2158.2) | 132.8 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1454.7 (1398.9–2045.7) | 202.3 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1462.4 (1456.1–1795.6) | 203.3 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1569.0 (1342.5–1828.7) | 163.1 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1746.5 (1520.4–1764.7) | 135.0 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1486.8 (1350.9–1789.2) | 157.5 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1458.9 (1281.5–1579.9) | 209.2 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1561.5 (1524.8–1620.2) | 189.0 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1538.9 (1370.6–1610.2) | 183.4 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2250.1 (2004.6–2323.4) | 102.3 |
| tidb | scaling-autoinc | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 765.9 (719.6–861.5) | 308.8 |
| tidb | scaling-autoinc | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1682.3 (1636.1–1736.7) | 127.8 |
| tidb | scaling-autorandom | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb1 | 3 | 3/3 | 788.1 (744.6–834.0) | 302.3 |
| tidb | scaling-autorandom | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2222.2 (1854.2–2227.1) | 104.2 |

## Hệ số tăng tốc (TiDB: 3 TiKV ÷ 1 TiKV; MySQL: cỡ vCPU lớn ÷ cỡ vCPU nhỏ)

Chỉ ghép các nhóm giống hệt nhau về mọi tham số khác. Cột "TPS nhỏ" là 1 TiKV (TiDB) hoặc cỡ vCPU nhỏ (MySQL); "TPS lớn" là 3 TiKV hoặc cỡ vCPU lớn. Tăng tốc bằng tỉ số cỡ (3 với TiDB; 24÷20 = 1,2 với MySQL) nghĩa là mở rộng hiệu quả hoàn hảo, bằng 1 nghĩa là thêm tài nguyên vô ích.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | vị trí | khóa orders | kho/đơn | TPS nhỏ | TPS lớn | tăng tốc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | none/stock | composite | 1-1 | 1304.1 | 1232.3 | 0.94 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | none/stock | composite | 1-1 | 2040.2 | 1808.4 | 0.89 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | none/stock | composite | 1-1 | 2041.8 | 1827.6 | 0.90 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | none/stock | composite | 1-1 | 2010.7 | 1818.8 | 0.90 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | none/stock | composite | 1-1 | 1222.2 | 1140.8 | 0.93 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | spread/stock | composite | 1-1 | 616.2 | 751.2 | 1.22 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | spread/stock | composite | 1-1 | 845.2 | 2121.2 | 2.51 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | spread/stock | composite | 1-1 | 707.1 | 1725.5 | 2.44 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | spread/stock | composite | 1-1 | 848.5 | 2086.5 | 2.46 |
| tidb | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | spread/stock | composite | 1-1 | 1136.1 | 2250.1 | 1.98 |
| tidb | scaling-autoinc | 64 | uniform | 0.0 | False | p1 |  | 0 | spread/stock | autoinc | 1-1 | 765.9 | 1682.3 | 2.20 |
| tidb | scaling-autorandom | 64 | uniform | 0.0 | False | p1 |  | 0 | spread/stock | auto_random | 1-1 | 788.1 | 2222.2 | 2.82 |

## Kiểm tra warmup 30 giây

99/99 lượt có chuỗi TPS theo giây; 20 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 102530d2954e4cbcbcb4ef1649ad76f9 | tidb | scaling | 64 | 0.0 | 21.9 |
| 186ce0dbc7a44eb18d38b58a24643470 | tidb | scaling | 64 | 0.0 | 11.7 |
| 2443655d560148dcad17f556119a401b | tidb | scaling | 64 | 0.0 | 24.4 |
| 2a26457611094feca1236f196cf6e2ad | tidb | scaling-autoinc | 64 | 0.0 | 29.2 |
| 2af4a415cedc4b0e8c0447128a187e17 | tidb | scaling | 64 | 0.0 | -20.3 |
| 3fd4b8437b7e442e8c49747bba38d06d | tidb | scaling | 64 | 0.9 | -11.0 |
| 5570624b6f2e4294b2ed956b4236857e | tidb | scaling | 64 | 0.0 | 21.7 |
| 5c9cd3f6941e4ee4a99d1f40aa478179 | tidb | scaling-autoinc | 64 | 0.0 | -28.5 |
| 6e640cbdf3fe4e319e4df95ba781f8bc | tidb | scaling | 64 | 0.0 | -16.1 |
| 854161bb9f764656aff654b95314968c | mysql | scaling | 64 | 0.0 | -10.2 |
| 864389e70d0d4c648085c1394936296b | mysql | scaling | 64 | 0.9 | -11.0 |
| 8f1ed34bfd7145d98365911c49a97076 | tidb | scaling | 64 | 0.0 | 17.7 |
| a53046f7d91b4dfea045bcc34872875e | tidb | scaling-autorandom | 64 | 0.0 | 14.8 |
| ac232efb220d4bf5840cf1f48eaece17 | mysql | scaling | 64 | 0.9 | 10.3 |
| c374d504614549be81d4f3751ec2abe8 | tidb | scaling | 64 | 0.9 | -11.8 |
| c3ee986af58a4cf2a533de94fbd1d872 | mysql | scaling | 64 | 0.9 | 10.7 |
| cb53a517511b40b0b40d895be33be26c | tidb | scaling | 64 | 0.9 | 44.3 |
| d3f4b7c947f14de1993a87dac13a3178 | tidb | scaling-autorandom | 64 | 0.0 | -16.9 |
| d96f9e6f08f243649ba97e6a9e22dab7 | tidb | scaling | 64 | 0.0 | 11.6 |
| e490a76b36ae4069a4ea7935bac1cc2c | tidb | scaling | 64 | 0.0 | -30.9 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
