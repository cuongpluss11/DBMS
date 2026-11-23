# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2478.6 (2411.5–2547.0) | 304.2 |
| mongo | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2446.3 (2136.0–2490.7) | 306.4 |
| mongo | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2425.6 (2424.5–2562.3) | 309.2 |
| mongo | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1979.5 (1950.6–1994.1) | 322.4 |
| mongo | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2652.3 (2589.8–2703.7) | 298.9 |
| mysql | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1587.8 (1559.6–1614.0) | 789.6 |
| mysql | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1472.3 (1472.0–1474.4) | 817.7 |
| mysql | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 702.6 (656.4–831.9) | 999.1 |
| mysql | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1288.0 (1284.5–1288.2) | 779.8 |
| mysql | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1890.3 (1871.6–2164.8) | 728.2 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 710.4 (638.1–792.9) | 999.5 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 568.2 (551.7–615.4) | 1308.5 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 708.6 (668.1–723.4) | 1087.0 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 567.8 (524.6–610.6) | 1100.0 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1073.5 (1028.9–1086.1) | 667.2 |

## Kiểm tra warmup 30 giây

45/45 lượt có chuỗi TPS theo giây; 28 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 0135d9c47f934648afa9906dfbdf814e | tidb | migration | 128 | 0.9 | -26.8 |
| 0e2f02282689413f85775d2de2812ff5 | tidb | migration | 128 | 0.9 | -37.7 |
| 1195467442f34b2294e5f579de182177 | tidb | migration | 128 | 0.9 | -38.3 |
| 13f5a3e499dd4f2bb732c165db2b243b | tidb | migration | 128 | 0.9 | -18.8 |
| 13fcac39fc3f4824a25bd5357c4e459e | tidb | migration | 128 | 0.9 | -33.7 |
| 1bce9dd554524cea9bda565354ea884b | mongo | migration | 128 | 0.9 | -25.7 |
| 1dc439e19a4445c0a8ba96485c739e36 | mongo | migration | 128 | 0.9 | -25.9 |
| 29ed6a2fdf284d1cbb77ea46184ea479 | mysql | migration | 128 | 0.9 | -36.8 |
| 341a292f40024e508fc5813385bdfea3 | mysql | migration | 128 | 0.9 | -18.1 |
| 3c2f4dc1342d4716aaba029d85a3c8a3 | mysql | migration | 128 | 0.9 | -21.7 |
| 4b6933bc3cd94d4a9010cea9b75f6297 | tidb | migration | 128 | 0.9 | -38.7 |
| 6256a85ad9be45a7b2ba4a04710c37fc | mongo | migration | 128 | 0.9 | -23.8 |
| 6559527fbf554a08ba625a517395fe9d | mysql | migration | 128 | 0.9 | -23.2 |
| 79796ad53c384a2592bc1d79939ab9f3 | mysql | migration | 128 | 0.9 | -26.1 |
| 83de7f3d3a7f47bca11da9bde6119b81 | mysql | migration | 128 | 0.9 | -40.9 |
| a8d5aa02c0de40068ce8593d2b2dbcbe | mysql | migration | 128 | 0.9 | -34.3 |
| aa6ea43dc2c04eb290b1da920c9fb0fa | mysql | migration | 128 | 0.9 | -21.0 |
| ab3da9734eb34577bffa22260a1301ba | tidb | migration | 128 | 0.9 | -16.2 |
| b755dd063da8495dbe3c16a51268b4ae | mongo | migration | 128 | 0.9 | 95.4 |
| cb0e4adb929746d399e3720fb7732f27 | tidb | migration | 128 | 0.9 | -42.0 |
| cc9fe08c29c04f8f96d9dfcfe2fe8380 | mysql | migration | 128 | 0.9 | -13.9 |
| ce9cce1afe384adda5fdf0395099e9bd | tidb | migration | 128 | 0.9 | -32.8 |
| cec53ad581964917b5a92db4169eaec4 | tidb | migration | 128 | 0.9 | 33.1 |
| e56ebafe852e4088b6263496b46f6dc3 | mysql | migration | 128 | 0.9 | -25.4 |
| e800061d6f8b49ef93cbc5c5b29ef556 | mysql | migration | 128 | 0.9 | -33.8 |
| ece054b134aa4caa9cff09b71f47651e | mongo | migration | 128 | 0.9 | 43.2 |
| ed6c707dba1143f39f1823295d14d0e7 | tidb | migration | 128 | 0.9 | -24.0 |
| f6d6e4bf876f48daa340f2927c40bcb6 | mysql | migration | 128 | 0.9 | -20.4 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
