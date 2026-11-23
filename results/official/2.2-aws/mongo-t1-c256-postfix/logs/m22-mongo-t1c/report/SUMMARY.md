# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | correctness | 8 | single-warehouse | 0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 453.7 (453.6–455.3) | 10.3 |
| mongo | correctness | 8 | single-warehouse | 0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 458.3 (455.6–459.4) | 10.3 |
| mongo | correctness | 8 | single-warehouse | 0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 316.7 (314.1–317.0) | 10.6 |
| mongo | correctness | 8 | single-warehouse | 0 | True | p3 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 311.7 (311.3–313.5) | 10.8 |
| mongo | hotspot | 128 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 845.1 (842.0–845.6) | 341.3 |
| mongo | hotspot | 128 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | b | False | False | True | m22-mongo | 3 | 3/3 | 8354.0 (8331.1–8493.7) | 30.3 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2157.3 (2155.1–2167.5) | 348.7 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | b | False | False | True | m22-mongo | 3 | 3/3 | 5838.8 (5758.9–5872.4) | 52.4 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1500.0 (1500.0–1500.0) | 27.8 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2499.8 (2493.8–2499.9) | 250.7 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3097.1 (3089.1–3099.8) | 235.4 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3673.3 (3667.3–3682.5) | 380.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1500.0 (1500.0–1500.0) | 59.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2499.8 (2495.9–2499.9) | 240.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3099.8 (3099.4–3099.8) | 49.2 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3685.5 (3677.7–3692.3) | 320.2 |
| mongo | hotspot | 256 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2421.0 (2400.8–2432.1) | 345.2 |
| mongo | hotspot | 256 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2699.7 (2680.9–2722.1) | 353.5 |
| mongo | hotspot | 256 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 789.5 (784.4–795.2) | 339.8 |
| mongo | hotspot | 256 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 1152.8 (1149.7–1155.0) | 346.1 |
| mongo | hotspot | 256 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2397.7 (2387.4–2422.1) | 345.3 |
| mongo | hotspot | 256 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2681.8 (2664.0–2685.7) | 353.7 |
| mongo | hotspot | 256 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2373.2 (2372.1–2375.2) | 345.2 |
| mongo | hotspot | 256 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2679.2 (2672.8–2701.2) | 353.7 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2167.9 (2162.9–2174.1) | 345.4 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo-t1c256-postfix | 3 | 3/3 | 2563.9 (2536.6–2566.4) | 352.9 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1307.9 (1260.8–1395.7) | 24.0 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 1500.2 (1500.2–1500.3) | 27.9 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2256.3 (2091.8–2259.2) | 183.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 2500.0 (2499.9–2500.1) | 76.8 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2795.9 (2638.0–2860.3) | 126.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 3099.5 (3096.1–3100.0) | 315.1 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3209.5 (3066.2–3347.9) | 303.5 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3-postfix | 3 | 3/3 | 3698.7 (3670.4–3699.1) | 327.0 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 5 | 3/5 | 1500.2 (1500.2–1500.2) | 27.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 4 | 3/4 | 2500.1 (2500.0–2500.1) | 60.9 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 4 | 3/4 | 3099.9 (3099.9–3099.9) | 96.1 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 4 | 3/4 | 3699.7 (3697.2–3699.7) | 66.9 |
| mongo | hotspot | 32 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 560.2 (556.9–561.0) | 337.0 |
| mongo | hotspot | 32 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | b | False | False | True | m22-mongo | 3 | 3/3 | 2797.3 (2784.5–2799.8) | 20.4 |
| mongo | hotspot | 32 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1268.2 (1266.8–1268.7) | 195.6 |
| mongo | hotspot | 32 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | b | False | False | True | m22-mongo | 3 | 3/3 | 1977.4 (1975.0–1979.9) | 38.8 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1630.0 (1627.7–1643.3) | 347.6 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1883.7 (1883.1–1900.1) | 346.0 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 615.5 (614.9–616.2) | 340.4 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 672.7 (671.3–676.8) | 338.4 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 668.4 (667.7–668.5) | 338.7 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 807.5 (806.9–808.4) | 335.1 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 3954.8 (3954.8–3962.4) | 113.5 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1602.8 (1600.9–1606.5) | 338.6 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1892.8 (1884.2–1900.5) | 343.7 |
| mongo | hotspot | 64 | single-warehouse | 0.0 | True | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2854.0 (2849.8–2855.5) | 184.3 |
| mongo | hotspot | 64 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1879.8 (1876.9–1889.0) | 346.0 |
| mongo | hotspot | 64 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1867.0 (1866.8–1874.4) | 346.2 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1463.9 (1463.5–1465.3) | 347.7 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1698.1 (1696.8–1711.1) | 345.8 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1701.8 (1699.3–1702.1) | 346.2 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 1 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2638.4 (2616.2–2654.0) | 189.2 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 27 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 3169.4 (3167.7–3180.2) | 67.2 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 3 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 2996.6 (2995.0–3009.5) | 142.6 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 1874.4 (1857.4–1874.6) | 346.4 |
| mongo | hotspot | 64 | single-warehouse | 0.9 | False | p2 | 9 | 50 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 3059.6 (3048.4–3079.4) | 101.8 |
| mongo | hotspot | 8 | single-warehouse | 0.0 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 466.8 (463.2–467.8) | 110.0 |
| mongo | hotspot | 8 | single-warehouse | 0.0 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 538.5 (534.1–538.8) | 104.3 |
| mongo | hotspot | 8 | single-warehouse | 0.0 | True | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 363.7 (362.1–364.9) | 335.0 |
| mongo | hotspot | 8 | single-warehouse | 0.0 | True | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 402.9 (400.6–409.1) | 179.8 |
| mongo | hotspot | 8 | single-warehouse | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 538.8 (536.1–539.0) | 103.2 |
| mongo | hotspot | 8 | single-warehouse | 0.7 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 538.0 (532.7–544.9) | 103.5 |
| mongo | hotspot | 8 | single-warehouse | 0.9 | False | p0 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 451.1 (449.2–454.1) | 121.8 |
| mongo | hotspot | 8 | single-warehouse | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True | m22-mongo | 3 | 3/3 | 526.4 (525.9–527.0) | 109.4 |

## Kiểm tra warmup 30 giây

210/215 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
