# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 710.4 (638.1–792.9) | 999.5 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 568.2 (551.7–615.4) | 1308.5 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 708.6 (668.1–723.4) | 1087.0 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 567.8 (524.6–610.6) | 1100.0 |
| tidb | migration | 128 | uniform | 0.9 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1073.5 (1028.9–1086.1) | 667.2 |

## Kiểm tra warmup 30 giây

15/15 lượt có chuỗi TPS theo giây; 11 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 0135d9c47f934648afa9906dfbdf814e | tidb | migration | 128 | 0.9 | -26.8 |
| 0e2f02282689413f85775d2de2812ff5 | tidb | migration | 128 | 0.9 | -37.7 |
| 1195467442f34b2294e5f579de182177 | tidb | migration | 128 | 0.9 | -38.3 |
| 13f5a3e499dd4f2bb732c165db2b243b | tidb | migration | 128 | 0.9 | -18.8 |
| 13fcac39fc3f4824a25bd5357c4e459e | tidb | migration | 128 | 0.9 | -33.7 |
| 4b6933bc3cd94d4a9010cea9b75f6297 | tidb | migration | 128 | 0.9 | -38.7 |
| ab3da9734eb34577bffa22260a1301ba | tidb | migration | 128 | 0.9 | -16.2 |
| cb0e4adb929746d399e3720fb7732f27 | tidb | migration | 128 | 0.9 | -42.0 |
| ce9cce1afe384adda5fdf0395099e9bd | tidb | migration | 128 | 0.9 | -32.8 |
| cec53ad581964917b5a92db4169eaec4 | tidb | migration | 128 | 0.9 | 33.1 |
| ed6c707dba1143f39f1823295d14d0e7 | tidb | migration | 128 | 0.9 | -24.0 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
