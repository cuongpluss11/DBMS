# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2172.4 (2080.2–2186.8) | 162.3 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2088.7 (2062.0–2133.8) | 161.1 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1835.5 (1814.9–1950.3) | 162.6 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2829.7 (2810.4–2916.3) | 114.2 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1255.2 (1254.7–1349.5) | 578.2 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1104.8 (1094.2–1106.0) | 619.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 988.0 (979.5–1040.7) | 644.7 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1553.4 (1538.8–1571.4) | 559.5 |
| tidb | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 895.0 (753.7–918.5) | 340.4 |
| tidb | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 702.1 (523.4–748.0) | 506.4 |

## Kiểm tra warmup 30 giây

30/30 lượt có chuỗi TPS theo giây; 15 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 00c4275cac7442788a3ab57eab8a525b | mysql | migration | 64 | 0.5 | -18.3 |
| 066b1fefc6274f1a9965f85df3c1716c | tidb | migration | 64 | 0.5 | 93.7 |
| 1bbc40eaf013469dbdbd2788cafe64b1 | mysql | migration | 64 | 0.5 | -23.5 |
| 2a4efc312cda47c69c9e3dc356fd1403 | mongo | migration | 64 | 0.5 | -70.2 |
| 31a0061a68224e01b4e0778add7fda5b | tidb | migration | 64 | 0.5 | -23.5 |
| 41700bdb50244ecb93eb76d070d27d22 | mongo | migration | 64 | 0.5 | -47.4 |
| 4a0f0128fa2c4165b963ae3551105d14 | mysql | migration | 64 | 0.5 | -23.7 |
| 603a393e745f435cb58512971f5f21e8 | tidb | migration | 64 | 0.5 | -21.6 |
| 85640b6d58cc4acf833ff59e3363fc3c | mongo | migration | 64 | 0.5 | 46.2 |
| 9d8c1ff25483498493c2850212a3a179 | mysql | migration | 64 | 0.5 | -14.2 |
| a695847d4e234bafa7550a61998a7819 | tidb | migration | 64 | 0.5 | -26.4 |
| e0769c6950ac4e6c85f5a5b34b7afa8c | mysql | migration | 64 | 0.5 | -17.8 |
| e371ee0a7bc14528bacce5238de9f12d | mysql | migration | 64 | 0.5 | -25.2 |
| e87d477ee0fd45208fbab4b4d3f2f584 | mongo | migration | 64 | 0.5 | -20.0 |
| ea30af7f4ab244c88f34ddcc20d1c614 | mysql | migration | 64 | 0.5 | -24.1 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
