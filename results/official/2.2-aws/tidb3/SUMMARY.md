# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | correctness | 8 | single-warehouse | 0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 369.6 (369.6–369.6) | 19.4 |
| tidb | correctness | 8 | single-warehouse | 0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 353.1 (345.3–354.6) | 10.0 |
| tidb | correctness | 8 | single-warehouse | 0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 49.1 (40.0–58.9) | 7.9 |
| tidb | correctness | 8 | single-warehouse | 0 | True | p3 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 87.8 (87.7–90.3) | 7.4 |
| tidb | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 241.0 (215.7–241.3) | 1130.6 |
| tidb | hotspot | 128 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 237.9 (235.4–241.5) | 1221.2 |
| tidb | hotspot | 128 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | optimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 22.1 (21.1–22.4) | 3790.3 |
| tidb | hotspot | 128 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | pessimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 250.3 (248.8–250.9) | 1044.8 |
| tidb | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 823.9 (789.9–831.1) | 696.2 |
| tidb | hotspot | 128 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 754.3 (702.6–839.9) | 711.4 |
| tidb | hotspot | 128 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | optimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 144.2 (125.3–154.6) | 4341.6 |
| tidb | hotspot | 128 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | pessimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 886.1 (730.0–899.0) | 649.1 |
| tidb | hotspot | 256 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 1040.4 (857.4–1055.7) | 1403.7 |
| tidb | hotspot | 256 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 260.4 (237.8–264.7) | 2267.9 |
| tidb | hotspot | 256 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 897.8 (867.8–1071.0) | 1642.2 |
| tidb | hotspot | 256 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 987.0 (938.4–1030.5) | 1424.0 |
| tidb | hotspot | 256 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 835.5 (799.8–856.7) | 1099.2 |
| tidb | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 242.5 (231.7–243.6) | 274.5 |
| tidb | hotspot | 32 | single-warehouse | 0.0 | True | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 240.8 (236.6–242.3) | 294.4 |
| tidb | hotspot | 32 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | optimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 34.5 (33.3–35.5) | 3684.7 |
| tidb | hotspot | 32 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | pessimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 249.4 (234.4–251.9) | 266.5 |
| tidb | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 763.6 (653.7–801.9) | 218.8 |
| tidb | hotspot | 32 | single-warehouse | 0.9 | False | legacy |  | 0 | kín | True | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 787.1 (701.0–805.3) | 218.5 |
| tidb | hotspot | 32 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | optimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 151.5 (138.4–157.9) | 3191.1 |
| tidb | hotspot | 32 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | pessimistic | a | False | False | True | m22-tidb3 | 3 | 3/3 | 798.5 (769.8–848.4) | 204.8 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 914.8 (914.8–914.8) | 457.5 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 955.6 (865.4–985.3) | 408.0 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 250.5 (250.5–250.5) | 524.4 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 255.4 (252.3–262.2) | 604.9 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 246.0 (235.4–247.6) | 650.6 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 229.1 (219.9–251.2) | 623.2 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 2156.9 (2001.2–2221.9) | 160.8 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 588.3 (555.6–592.9) | 549.9 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 957.5 (955.7–967.0) | 267.7 |
| tidb | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 1286.4 (1094.2–1335.0) | 352.1 |
| tidb | hotspot | 64 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 928.9 (801.9–930.5) | 434.5 |
| tidb | hotspot | 64 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 983.1 (767.9–1043.8) | 404.1 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 808.2 (808.2–808.2) | 446.4 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 807.4 (744.7–871.0) | 398.3 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 669.2 (663.9–848.6) | 549.5 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 765.5 (716.8–881.6) | 732.8 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 2313.8 (2055.8–2495.1) | 70.8 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 1776.4 (1501.8–1824.8) | 389.6 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 911.9 (845.5–988.7) | 438.5 |
| tidb | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 2276.1 (2121.4–2598.6) | 117.2 |
| tidb | hotspot | 8 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 454.1 (454.1–454.1) | 63.7 |
| tidb | hotspot | 8 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 515.0 (508.3–531.8) | 56.8 |
| tidb | hotspot | 8 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 258.7 (258.7–258.7) | 66.0 |
| tidb | hotspot | 8 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 261.8 (232.8–263.7) | 65.8 |
| tidb | hotspot | 8 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 496.9 (437.0–514.9) | 58.6 |
| tidb | hotspot | 8 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 509.7 (500.4–546.1) | 55.9 |
| tidb | hotspot | 8 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 1 | 0/1 | 415.1 (415.1–415.1) | 71.0 |
| tidb | hotspot | 8 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-tidb3 | 3 | 3/3 | 526.9 (501.6–540.0) | 57.3 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p1 |  | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 751.2 (732.9–754.0) | 754.0 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2121.2 (1544.7–2187.9) | 73.3 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1725.5 (1319.0–1736.8) | 387.8 |
| tidb | scaling | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2086.5 (1643.3–2301.1) | 95.4 |
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
| tidb | scaling-autoinc | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 1682.3 (1636.1–1736.7) | 127.8 |
| tidb | scaling-autorandom | 64 | uniform | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m23-tidb3 | 3 | 3/3 | 2222.2 (1854.2–2227.1) | 104.2 |

## Kiểm tra warmup 30 giây

193/193 lượt có chuỗi TPS theo giây; 36 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 0ff08862f2804a7d9ae01dab93779ca8 | tidb | hotspot | 32 | 0.0 | -51.3 |
| 102530d2954e4cbcbcb4ef1649ad76f9 | tidb | scaling | 64 | 0.0 | 21.9 |
| 1146b58e9ee547be92362fa3d437c356 | tidb | hotspot | 64 | 0.5 | 30.7 |
| 145224fe2d8d4dc5ac2476ea4fe68299 | tidb | hotspot | 64 | 0.7 | -10.4 |
| 2443655d560148dcad17f556119a401b | tidb | scaling | 64 | 0.0 | 24.4 |
| 25cf2607710849a1b5de4cb45e177816 | tidb | hotspot | 256 | 0.5 | -18.3 |
| 2af4a415cedc4b0e8c0447128a187e17 | tidb | scaling | 64 | 0.0 | -20.3 |
| 3dc56840e4f04996afcc99540683a969 | tidb | hotspot | 32 | 0.9 | -21.1 |
| 4a55e5181a094488b97d3b9b7662ce08 | tidb | hotspot | 64 | 0.0 | 21.1 |
| 4aceb820b6fe4ca682bf049396b70444 | tidb | hotspot | 128 | 0.9 | 26.8 |
| 4de05534702d466d940ac6fc3cdc4dc7 | tidb | hotspot | 64 | 0.9 | 12.5 |
| 5570624b6f2e4294b2ed956b4236857e | tidb | scaling | 64 | 0.0 | 21.7 |
| 64d7d027f130496c9b98ce44ca9a161e | tidb | hotspot | 128 | 0.0 | -72.7 |
| 6e640cbdf3fe4e319e4df95ba781f8bc | tidb | scaling | 64 | 0.0 | -16.1 |
| 703d5f3e5f75463f98c5753486624ab2 | tidb | correctness | 8 | 0 | -12.7 |
| 70c38a6956064dd6b8c4807abf37ed00 | tidb | hotspot | 128 | 0.9 | -70.7 |
| 7795191e7f6c435996e10080b10d1a10 | tidb | hotspot | 8 | 0.7 | -10.9 |
| 794b1cfec3364a989b96c5d1dfb08bfa | tidb | hotspot | 64 | 0.9 | 32.2 |
| 7a2a06341b1045999010392582502e7f | tidb | hotspot | 128 | 0.0 | -100.0 |
| 829ace59f6dd4e5db028dff35ceb9378 | tidb | hotspot | 64 | 0.0 | 22.7 |
| 8f1ed34bfd7145d98365911c49a97076 | tidb | scaling | 64 | 0.0 | 17.7 |
| a53046f7d91b4dfea045bcc34872875e | tidb | scaling-autorandom | 64 | 0.0 | 14.8 |
| b2e0fd0fd0a547a49bb6c3d06a64f7ec | tidb | hotspot | 128 | 0.9 | 11.5 |
| baf3872b108e4bd8928b8412da26f3a2 | tidb | hotspot | 32 | 0.0 | -64.2 |
| c156a8b5025b4e9a97c9a730e8537377 | tidb | hotspot | 64 | 0.5 | 41.4 |
| c7dd38b2f9bb4555b56fd63a51a31faf | tidb | hotspot | 32 | 0.0 | 22.2 |
| cad8a46310aa438e950a95c3c64dae85 | tidb | hotspot | 256 | 0.7 | 19.2 |
| cb34eeebd40a4f63a5ef3d33c7518840 | tidb | hotspot | 32 | 0.9 | -22.4 |
| cb500dfecf384da88f4d5d6253fd9418 | tidb | hotspot | 64 | 0.9 | -11.0 |
| d07f7cb41f784ed2918b95ea585a9818 | tidb | hotspot | 64 | 0.7 | 11.7 |
| d786d8b675a5487d8b0666dd40a910ae | tidb | hotspot | 32 | 0.9 | 86.3 |
| d930846322734bf9a12b5525bd81e4ab | tidb | hotspot | 64 | 0.9 | -14.1 |
| d96f9e6f08f243649ba97e6a9e22dab7 | tidb | scaling | 64 | 0.0 | 11.6 |
| e490a76b36ae4069a4ea7935bac1cc2c | tidb | scaling | 64 | 0.0 | -30.9 |
| f56cc2b42a1244fabb3e62c7349be234 | tidb | hotspot | 128 | 0.0 | -97.8 |
| f67137189d1342f0a9abbb5ab21bcb14 | tidb | hotspot | 32 | 0.9 | -31.5 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
