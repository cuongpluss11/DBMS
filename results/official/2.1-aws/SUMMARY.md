# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | baseline-cross | 8 | uniform | 0 | False | False | True |  | 3 | 3/3 | 447.6 (437.3–449.1) | 54.2 |
| mongo | baseline-cross-1client | 1 | uniform | 0 | False | False | True |  | 3 | 3/3 | 189.8 (186.9–192.5) | 10.2 |
| mongo | correctness | 8 | single-warehouse | 0 | True | False | True |  | 3 | 3/3 | 438.6 (438.4–440.5) | 10.7 |
| mongo | idempotency-off | 64 | single-warehouse | 0 | True | False | False |  | 1 | 0/1 | 624.3 (624.3–624.3) | 340.9 |
| mongo | payment-ytd | 8 | uniform | 0 | False | True | True |  | 3 | 3/3 | 409.5 (405.9–412.5) | 58.1 |
| mongo | performance | 128 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 2506.6 (2481.2–2538.0) | 293.2 |
| mongo | performance | 128 | uniform | 0.0 | False | False | True | loadgen_c6i.4xlarge | 3 | 3/3 | 3052.7 (2977.9–3170.2) | 245.1 |
| mongo | performance | 256 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 2489.8 (2445.6–2532.2) | 239.7 |
| mongo | performance | 256 | uniform | 0.0 | False | False | True | loadgen_c6i.4xlarge | 3 | 3/3 | 2968.3 (2937.6–3100.1) | 218.0 |
| mongo | performance | 32 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 1186.2 (1135.9–1192.1) | 121.1 |
| mongo | performance | 64 | uniform | 0.0 | False | False | True |  | 4 | 3/4 | 2164.0 (2014.7–2266.0) | 147.0 |
| mongo | performance | 64 | uniform | 0.0 | False | False | True | loadgen_c6i.4xlarge | 3 | 3/3 | 2119.5 (2029.4–2172.5) | 157.9 |
| mongo | performance | 8 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 457.7 (456.4–460.8) | 50.9 |
| mongo | performance | 8 | uniform | 0.3 | False | False | True |  | 3 | 3/3 | 451.5 (449.8–456.2) | 52.7 |
| mongo | performance | 8 | uniform | 0.5 | False | False | True |  | 3 | 3/3 | 452.0 (450.6–452.1) | 53.3 |
| mongo | performance | 8 | uniform | 0.5 | True | False | True |  | 3 | 3/3 | 594.9 (575.5–595.8) | 73.0 |
| mongo | performance | 8 | uniform | 0.7 | False | False | True |  | 3 | 3/3 | 456.1 (430.4–461.9) | 52.3 |
| mongo | performance | 8 | uniform | 0.9 | False | False | True |  | 3 | 3/3 | 454.2 (446.4–458.9) | 57.8 |
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
| tidb | baseline-cross | 8 | uniform | 0 | False | False | True |  | 3 | 3/3 | 446.6 (427.5–470.8) | 46.3 |
| tidb | baseline-cross-1client | 1 | uniform | 0 | False | False | True |  | 3 | 3/3 | 95.9 (84.4–98.4) | 26.6 |
| tidb | correctness | 8 | single-warehouse | 0 | True | False | True |  | 3 | 3/3 | 316.2 (311.9–320.9) | 10.3 |
| tidb | idempotency-off | 64 | single-warehouse | 0 | True | False | False |  | 1 | 1/1 | 214.2 (214.2–214.2) | 474.9 |
| tidb | payment-ytd | 8 | uniform | 0 | False | True | True |  | 3 | 3/3 | 417.3 (323.3–419.9) | 45.4 |
| tidb | performance | 128 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 929.9 (928.1–959.1) | 586.0 |
| tidb | performance | 256 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 948.2 (939.6–950.3) | 1439.0 |
| tidb | performance | 32 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 910.8 (882.7–924.8) | 106.3 |
| tidb | performance | 64 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 946.2 (946.1–947.0) | 230.4 |
| tidb | performance | 8 | uniform | 0.0 | False | False | True |  | 3 | 3/3 | 399.6 (398.7–431.8) | 49.0 |
| tidb | performance | 8 | uniform | 0.3 | False | False | True |  | 3 | 3/3 | 468.5 (445.7–478.8) | 42.3 |
| tidb | performance | 8 | uniform | 0.5 | False | False | True |  | 3 | 3/3 | 435.4 (341.1–453.2) | 49.7 |
| tidb | performance | 8 | uniform | 0.5 | True | False | True |  | 3 | 3/3 | 544.1 (427.9–641.8) | 47.3 |
| tidb | performance | 8 | uniform | 0.7 | False | False | True |  | 3 | 3/3 | 422.9 (348.2–426.0) | 46.8 |
| tidb | performance | 8 | uniform | 0.9 | False | False | True |  | 3 | 3/3 | 399.0 (387.7–428.2) | 51.3 |

## Kiểm tra warmup 30 giây

151/151 lượt có chuỗi TPS theo giây; 35 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 04f41b4c43204bc6ad256d1f4922cef2 | mongo | performance | 8 | 0.7 | 10.3 |
| 07aa7ed889894346a5279cb431e417fc | tidb | performance | 8 | 0.5 | -10.0 |
| 0faefedc7e334bdf87abcba68fe7aeb4 | tidb | performance | 8 | 0.3 | 10.5 |
| 11bae233963a4ec98e128b50e49cb93e | tidb | performance | 8 | 0.5 | -17.9 |
| 161879b98a9d4b0dadd10c216cdb89be | mongo | performance | 256 | 0.0 | 147.4 |
| 1a8920800cbf4fdd87f7b24d07fcaefd | mongo | performance | 64 | 0.0 | 61.0 |
| 1ac4ef8d55434bcc9618f00a4c7dd4c9 | mongo | performance | 256 | 0.0 | 172.7 |
| 2306ac2548e64f9aad69c70b18381e90 | mongo | performance | 256 | 0.0 | 63.7 |
| 2308dbb152504d12b95ecb8b56143a3a | tidb | performance | 8 | 0.7 | 10.5 |
| 3611b9e895264a54b846613576d9e479 | mongo | performance | 64 | 0.0 | 14.0 |
| 36b7bd4ca673440b9b782d0af9350988 | tidb | performance | 8 | 0.3 | 11.6 |
| 47a7024ae39f432aaa8d0b7e9f8805f5 | mysql | baseline-1client | 1 | 0 | -16.9 |
| 4e326852e3f04d12ba82a12402e6c19d | mongo | performance | 64 | 0.0 | 171.2 |
| 519d5031f86545debe33e3e93b7c0b42 | mongo | performance | 64 | 0.0 | 54.9 |
| 54cf88ecef6945958c10bf73814d1ae9 | tidb | baseline-cross | 8 | 0 | -25.5 |
| 59e2432cac294ffdb5f82c1de94e4719 | mongo | performance | 128 | 0.0 | 30.9 |
| 603837724427475da293cc2ae0457f1e | tidb | performance | 8 | 0.9 | -12.1 |
| 6317ed23c9d64efc8f88e3c31e72a3ae | mongo | performance | 256 | 0.0 | 94.4 |
| 6967571641da41c991315414186a321b | mongo | performance | 256 | 0.0 | 96.6 |
| 6fa27e4a96684f20abc34a0407978bcf | tidb | performance | 8 | 0.7 | -27.1 |
| 7034c14146674c898db3639ac338b1fd | tidb | baseline-cross-1client | 1 | 0 | 13.0 |
| 78d3b3524a87499894bf897bdf71c1bf | tidb | performance | 8 | 0.7 | 33.5 |
| 8a34965057984676a6db15948d351534 | mongo | performance | 128 | 0.0 | 80.1 |
| 8c3a0529097143aa8ffcddc7e261dc5c | mongo | performance | 128 | 0.0 | 97.1 |
| 97f226abb1944632afd80aefaf323c29 | mysql | performance | 8 | 0.3 | -10.7 |
| 990e68d1c0124ea4b5a2736017616c24 | tidb | performance | 8 | 0.0 | -10.5 |
| a2000f8daffd490baa8324305a53add7 | mongo | performance | 128 | 0.0 | 65.4 |
| abbfdf739f4e4c1592ecb9f41345c3b0 | mongo | performance | 64 | 0.0 | 85.5 |
| ad0ec026ab884c9aa61c80e4c537de45 | mysql | performance | 256 | 0.0 | 16.7 |
| c041c2bcc4e341f3a416d1c1a35d2083 | mongo | performance | 128 | 0.0 | 29.3 |
| c113ea98c7844c4ca54ac3ff9ea49a7f | tidb | correctness | 8 | 0 | 11.5 |
| c8157c5bbd84409b9190f25fe3e9c750 | mongo | performance | 128 | 0.0 | 36.3 |
| dc8e76b9580a4194a2617193c3aaf9b7 | tidb | payment-ytd | 8 | 0 | 11.1 |
| efcbe3d762e34fc88944a20931fe6151 | tidb | baseline-cross | 8 | 0 | -12.9 |
| f265ecdc0bb84d59abc3cecffec32b93 | tidb | performance | 8 | 0.9 | 11.4 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
