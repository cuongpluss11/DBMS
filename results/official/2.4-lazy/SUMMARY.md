# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1069.8 (1066.6–1072.6) | 588.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1027.1 (1022.1–1106.2) | 603.8 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1165.4 (1152.3–1187.3) | 553.3 |

## Kiểm tra warmup 30 giây

9/9 lượt có chuỗi TPS theo giây; 9 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 0b202fd092b04bafb79c2e1050132dbf | mysql | migration | 64 | 0.5 | -46.5 |
| 1ba66aea4fb34edc9bb4a226b7a28f93 | mysql | migration | 64 | 0.5 | -43.4 |
| 4e6385d0899345039566a0f8cf14c90a | mysql | migration | 64 | 0.5 | -20.8 |
| 62c78ed5415b4c89b9c5b51019ac1ef5 | mysql | migration | 64 | 0.5 | -38.3 |
| 6cd010e10edc4d5bbbdd300209b195c1 | mysql | migration | 64 | 0.5 | -40.7 |
| 7d222a568b3a455b957d3a56f454d8dd | mysql | migration | 64 | 0.5 | -11.5 |
| 81168b5d8f174b40977f001b4172abba | mysql | migration | 64 | 0.5 | -23.4 |
| 9a2f8e8424b1431f94ee947f4dec4fdb | mysql | migration | 64 | 0.5 | -18.3 |
| cd389ffc0e4f41189c7aa0e46021db7c | mysql | migration | 64 | 0.5 | -33.6 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
