# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1500.0 (1500.0–1500.0) | 27.8 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2499.8 (2493.8–2499.9) | 250.7 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3097.1 (3089.1–3099.8) | 235.4 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3673.3 (3667.3–3682.5) | 380.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1500.0 (1500.0–1500.0) | 59.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2499.8 (2495.9–2499.9) | 240.5 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3099.8 (3099.4–3099.8) | 49.2 |
| mongo | hotspot | 128 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3685.5 (3677.7–3692.3) | 320.2 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1307.9 (1260.8–1395.7) | 24.0 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2256.3 (2091.8–2259.2) | 183.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2795.9 (2638.0–2860.3) | 126.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p2 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3209.5 (3066.2–3347.9) | 303.5 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 1500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 1500.2 (1500.2–1500.2) | 27.6 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 2500.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 2500.1 (2500.0–2500.1) | 60.9 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3100.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3099.9 (3099.9–3099.9) | 96.1 |
| mongo | hotspot | 256 | single-warehouse | 0.9 | False | p3 | 9 | 50 | 3700.0 | False | False | default | a | False | False | True | m22-mongo-t3 | 3 | 3/3 | 3699.7 (3697.2–3699.7) | 66.9 |

## Kiểm tra warmup 30 giây

48/48 lượt có chuỗi TPS theo giây; 0 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.
