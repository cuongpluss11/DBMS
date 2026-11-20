# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | baseline | 8 | uniform | 0 | False | False | True |  | 3 | 3/3 | 258.6 (256.6–261.4) | 149.7 |
| mysql | baseline-1client | 1 | uniform | 0 | False | False | True |  | 3 | 3/3 | 184.7 (173.6–185.7) | 14.3 |
| mysql | baseline-cross | 8 | uniform | 0 | False | False | True |  | 3 | 3/3 | 256.6 (256.4–259.6) | 150.8 |
| mysql | baseline-cross-1client | 1 | uniform | 0 | False | False | True |  | 3 | 3/3 | 187.7 (181.2–190.6) | 13.9 |
| mysql | baseline-single-warehouse | 8 | single-warehouse | 0 | False | False | True |  | 3 | 3/3 | 381.1 (377.5–381.5) | 106.4 |
| mysql | baseline-tuned | 8 | uniform | 0 | False | False | True | mysql_tuned_3GiB | 3 | 3/3 | 438.2 (436.1–441.6) | 65.0 |
| mysql | correctness | 8 | single-warehouse | 0 | True | False | True |  | 3 | 3/3 | 399.2 (398.2–416.2) | 39.4 |
| mysql | idempotency-off | 64 | single-warehouse | 0 | True | False | False |  | 1 | 0/1 | 468.9 (468.9–468.9) | 467.0 |
| mysql | payment-ytd | 8 | uniform | 0 | False | True | True |  | 3 | 3/3 | 251.0 (249.9–251.3) | 160.8 |
| mysql | performance | 128 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 552.1 (551.4–557.7) | 781.1 |
| mysql | performance | 256 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 505.8 (498.4–507.8) | 2171.7 |
| mysql | performance | 32 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 412.3 (408.8–412.8) | 254.5 |
| mysql | performance | 64 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 496.0 (493.1–503.6) | 404.3 |
| mysql | performance | 8 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 257.1 (255.8–257.3) | 149.5 |
| mysql | performance | 8 | uniform | 0.3 | False | False | True |  | 3 | 3/3 | 254.9 (251.1–256.0) | 149.4 |
| mysql | performance | 8 | uniform | 0.5 | False | False | True |  | 3 | 3/3 | 256.6 (255.7–257.1) | 149.4 |
| mysql | performance | 8 | uniform | 0.5 | True | False | True |  | 3 | 3/3 | 497.7 (491.3–498.9) | 98.8 |
| mysql | performance | 8 | uniform | 0.7 | False | False | True |  | 3 | 3/3 | 259.3 (259.1–260.5) | 146.4 |
| mysql | performance | 8 | uniform | 0.9 | False | False | True |  | 3 | 3/3 | 270.9 (269.9–271.9) | 143.1 |

## Kiểm tra warmup 30 giây

55/55 lượt có chuỗi TPS theo giây; 3 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 47a7024ae39f432aaa8d0b7e9f8805f5 | mysql | baseline-1client | 1 | 0 | -17.2 |
| 5310e2b60bb646c5a540a8cd3425ce19 | mysql | performance | 64 | 0.0 | 13.0 |
| 97f226abb1944632afd80aefaf323c29 | mysql | performance | 8 | 0.3 | -10.3 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
