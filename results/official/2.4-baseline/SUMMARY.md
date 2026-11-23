# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2185.4 (2153.0–2277.5) | 140.7 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1882.9 (1874.7–1906.9) | 152.5 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 3044.2 (2890.4–3107.6) | 101.0 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1499.5 (1483.2–1543.5) | 457.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1262.0 (1204.7–1270.8) | 501.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 2011.8 (1941.4–2024.4) | 386.1 |

## Kiểm tra warmup 30 giây

18/18 lượt có chuỗi TPS theo giây; 9 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 130ddf8c69ae4ca6b69f5060848db905 | mongo | migration | 64 | 0.5 | 44.2 |
| 36b52ec6f28a4609a25de37fa598a2a2 | mongo | migration | 64 | 0.5 | 22.3 |
| 52c07e7c848244b4826b5a321018f05e | mongo | migration | 64 | 0.5 | 19.1 |
| 6804465ea66a4f8396468d4ff619e9d8 | mongo | migration | 64 | 0.5 | -20.3 |
| a303bebcfc4d42128146eee7c395a52e | mongo | migration | 64 | 0.5 | 21.3 |
| a3ac8ddd102a435c8b7df0a655a2b922 | mongo | migration | 64 | 0.5 | 23.9 |
| c457e9051f2949a88d93087b17eed409 | mongo | migration | 64 | 0.5 | 111.1 |
| cd4a701ab1ac487b949c7c36bb3f0658 | mongo | migration | 64 | 0.5 | 82.3 |
| f5695d9a0db749d785b19fc4a0e6853a | mongo | migration | 64 | 0.5 | 115.4 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
