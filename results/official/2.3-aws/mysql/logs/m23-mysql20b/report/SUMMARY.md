# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | correctness | 8 | single-warehouse | 0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 457.8 (457.8–457.8) | 11.9 |
| mysql | correctness | 8 | single-warehouse | 0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 552.0 (549.8–556.1) | 10.8 |
| mysql | correctness | 8 | single-warehouse | 0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 402.5 (400.6–402.5) | 6.3 |
| mysql | correctness | 8 | single-warehouse | 0 | True | p3 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 398.6 (395.3–400.7) | 6.3 |
| mysql | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 375.0 (358.9–435.1) | 907.2 |
| mysql | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | True | False | True | m22-mysql | 3 | 3/3 | 633.2 (619.0–639.0) | 563.5 |
| mysql | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | True | default | a | False | False | True | m22-mysql | 3 | 3/3 | 644.3 (641.4–653.2) | 340.2 |
| mysql | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 378.9 (373.4–379.5) | 903.8 |
| mysql | hotspot | 128 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 424.9 (419.8–436.6) | 816.5 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1202.0 (1177.0–1254.4) | 582.7 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | True | False | True | m22-mysql | 3 | 3/3 | 1550.0 (1523.8–1554.7) | 579.6 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | True | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1234.8 (1229.9–1252.1) | 856.6 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1184.2 (1178.4–1185.7) | 583.7 |
| mysql | hotspot | 128 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1293.1 (1291.0–1299.4) | 584.6 |
| mysql | hotspot | 256 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1464.7 (1449.8–1553.0) | 1078.3 |
| mysql | hotspot | 256 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 427.4 (399.9–466.9) | 1484.2 |
| mysql | hotspot | 256 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1489.9 (1474.6–1501.0) | 1064.5 |
| mysql | hotspot | 256 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1458.7 (1450.6–1463.0) | 1065.5 |
| mysql | hotspot | 256 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1283.0 (1269.8–1327.9) | 726.1 |
| mysql | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 382.8 (363.1–413.0) | 324.0 |
| mysql | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | True | False | True | m22-mysql | 3 | 3/3 | 639.0 (624.6–640.8) | 201.0 |
| mysql | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | True | default | a | False | False | True | m22-mysql | 3 | 3/3 | 416.9 (408.5–417.1) | 332.1 |
| mysql | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 380.8 (379.3–387.1) | 332.6 |
| mysql | hotspot | 32 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 415.9 (409.8–427.9) | 298.8 |
| mysql | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 984.2 (971.3–994.9) | 359.9 |
| mysql | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | True | False | True | m22-mysql | 3 | 3/3 | 1467.0 (1452.8–1484.5) | 395.4 |
| mysql | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | True | default | a | False | False | True | m22-mysql | 3 | 3/3 | 953.6 (945.0–956.2) | 366.8 |
| mysql | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 988.5 (985.9–992.5) | 363.1 |
| mysql | hotspot | 32 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1127.5 (1126.1–1158.3) | 392.7 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 1313.7 (1313.7–1313.7) | 481.1 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1416.2 (1390.1–1504.2) | 500.0 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 458.6 (458.6–458.6) | 442.1 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 425.8 (411.9–459.1) | 473.6 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 425.1 (410.4–488.4) | 472.9 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 396.7 (390.7–452.7) | 370.9 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 2741.2 (2667.3–2761.9) | 487.0 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 992.3 (980.7–993.9) | 418.0 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1504.5 (1501.3–1539.8) | 337.1 |
| mysql | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1846.7 (1812.0–1883.8) | 437.7 |
| mysql | hotspot | 64 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1386.6 (1367.6–1395.7) | 518.4 |
| mysql | hotspot | 64 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1391.9 (1387.4–1406.6) | 512.5 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 1139.2 (1139.2–1139.2) | 475.0 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1252.3 (1242.4–1281.5) | 475.5 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1257.0 (1213.9–1270.5) | 474.9 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1226.7 (1224.0–1335.2) | 726.4 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1780.1 (1749.2–1781.1) | 603.0 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1810.7 (1775.4–1864.9) | 628.7 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1423.3 (1422.9–1426.6) | 496.2 |
| mysql | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 1785.5 (1761.8–1790.3) | 603.7 |
| mysql | hotspot | 8 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 503.8 (503.8–503.8) | 53.7 |
| mysql | hotspot | 8 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 652.6 (649.2–655.5) | 83.5 |
| mysql | hotspot | 8 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 384.2 (384.2–384.2) | 67.8 |
| mysql | hotspot | 8 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 412.0 (394.0–416.3) | 63.1 |
| mysql | hotspot | 8 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 656.2 (652.7–661.8) | 72.9 |
| mysql | hotspot | 8 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 655.2 (653.4–658.0) | 82.1 |
| mysql | hotspot | 8 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 1 | 0/1 | 507.8 (507.8–507.8) | 53.1 |
| mysql | hotspot | 8 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mysql | 3 | 3/3 | 659.1 (658.9–661.6) | 69.9 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 1304.1 (1289.4–1307.0) | 688.0 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1232.3 (1227.5–1236.6) | 731.3 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1808.4 (1797.2–1809.5) | 589.0 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1827.6 (1801.4–1893.7) | 628.5 |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1818.8 (1808.0–1820.6) | 591.2 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | mysql-20vcpu | 3 | 3/3 | 1222.2 (1215.6–1237.9) | 479.1 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | mysql-24vcpu | 3 | 3/3 | 1140.8 (1090.3–1143.3) | 709.2 |

## Hệ số tăng tốc (TiDB: 3 TiKV ÷ 1 TiKV; MySQL: 12 vCPU ÷ 8 vCPU)

Chỉ ghép các nhóm giống hệt nhau về mọi tham số khác. 3 nghĩa là thêm máy hiệu quả hoàn hảo, 1 nghĩa là vô ích.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | vị trí | khóa orders | kho/đơn | TPS 1 TiKV | TPS 3 TiKV | tăng tốc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | none/stock | composite | 1-1 | 1304.1 | 1232.3 | 0.94 |
| mysql | scaling | 64 | uniform | 0.0 | False | p1 |  | 0 | none/stock | composite | 1-1 | 1222.2 | 1140.8 | 0.93 |

## Kiểm tra warmup 30 giây

178/178 lượt có chuỗi TPS theo giây; 15 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 1735b65a073d4db896fbf6fe5f850e66 | mysql | hotspot | 128 | 0.0 | 23.7 |
| 21f1405c9461433eb3806ac788f6103e | mysql | hotspot | 128 | 0.0 | -11.1 |
| 31fda3c6448a4a528d9d37004eb36863 | mysql | hotspot | 64 | 0.0 | -10.3 |
| 395b4d1897e1462a87adf7496459b346 | mysql | hotspot | 128 | 0.0 | 18.1 |
| 487d4c60a63f4021b4880c5388c4dcfa | mysql | hotspot | 32 | 0.0 | 10.5 |
| 6ac893554d2243d5bc3e7f3e1294bb6d | mysql | hotspot | 8 | 0.0 | -14.2 |
| 854161bb9f764656aff654b95314968c | mysql | scaling | 64 | 0.0 | -10.2 |
| a1408b26585b400985ba12ab0e75bdc3 | mysql | hotspot | 128 | 0.0 | -15.3 |
| b7f4d735f64c432ba0c0109504e6fcb6 | mysql | hotspot | 256 | 0.0 | 11.1 |
| bf41c2de53504efaa056e2acc131259c | mysql | hotspot | 8 | 0.0 | -10.9 |
| c3ee986af58a4cf2a533de94fbd1d872 | mysql | scaling | 64 | 0.9 | 10.7 |
| d155f603fa974341b26021295a39cda7 | mysql | hotspot | 32 | 0.0 | 12.4 |
| d243b856913d4804b9889b00466a53a3 | mysql | hotspot | 32 | 0.0 | 10.8 |
| dc651dcaf11e48509b40ae54e9a7e968 | mysql | hotspot | 128 | 0.0 | 10.2 |
| e30233b508a9416c845c5d2c6220e96e | mysql | hotspot | 32 | 0.0 | 15.8 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
