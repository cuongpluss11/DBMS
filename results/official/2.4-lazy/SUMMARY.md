# Tổng hợp kết quả

Trung vị, min–max của TPS thành công và trung vị p99 trên các lần lặp cùng cấu hình. `valid` là số lượt VALID trên tổng số lượt; lượt INVALID không được xếp hạng.

| engine | profile | client | kho | θ | hot | biến thể | slot | lô mã | tốc độ đến | khóa thứ tự | nowait | chế độ giao dịch | Mongo | SP | ytd | idem | ghi chú | lượt | valid | TPS median (min–max) | p99 median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1755.2 (1720.6–1777.2) | 143.6 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1754.7 (1739.7–1784.0) | 157.6 |
| mongo | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1788.9 (1752.9–1829.5) | 107.3 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1069.8 (1066.6–1072.6) | 588.5 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1027.1 (1022.1–1106.2) | 603.8 |
| mysql | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 1165.4 (1152.3–1187.3) | 553.3 |
| tidb | migration | 64 | uniform | 0.5 | False | p1 |  | 0 | kín | False | False | default | a | False | False | True |  | 3 | 3/3 | 655.0 (628.2–660.4) | 311.8 |

## Kiểm tra warmup 30 giây

21/21 lượt có chuỗi TPS theo giây; 19 lượt lệch quá 10% giữa 10 giây cuối warmup và 10 giây đầu đo.

| run_id | engine | profile | client | θ | drift % |
| --- | --- | --- | --- | --- | --- |
| 0b202fd092b04bafb79c2e1050132dbf | mysql | migration | 64 | 0.5 | -46.5 |
| 1ba66aea4fb34edc9bb4a226b7a28f93 | mysql | migration | 64 | 0.5 | -43.4 |
| 1d3506bb32c94bcd8d19032009c82ff3 | mongo | migration | 64 | 0.5 | -43.5 |
| 3478cfd0ac1e49aeb123a727aa25d252 | mongo | migration | 64 | 0.5 | -46.2 |
| 3c67286d57a14e1fbf3ba49f2290333b | tidb | migration | 64 | 0.5 | -37.8 |
| 481c1fdbdc11489abfbe49be9cbd406e | mongo | migration | 64 | 0.5 | -22.4 |
| 4a48774f4bbb4e47827a6eb04f59fa80 | tidb | migration | 64 | 0.5 | 35.5 |
| 4e6385d0899345039566a0f8cf14c90a | mysql | migration | 64 | 0.5 | -20.8 |
| 62c78ed5415b4c89b9c5b51019ac1ef5 | mysql | migration | 64 | 0.5 | -38.3 |
| 6cd010e10edc4d5bbbdd300209b195c1 | mysql | migration | 64 | 0.5 | -40.7 |
| 6d4840ac4dfb4e70b41799c0cd093f6b | mongo | migration | 64 | 0.5 | -42.9 |
| 74476f0ba7d34d63bbdab2837889ddcb | tidb | migration | 64 | 0.5 | -63.8 |
| 7d222a568b3a455b957d3a56f454d8dd | mysql | migration | 64 | 0.5 | -11.5 |
| 81168b5d8f174b40977f001b4172abba | mysql | migration | 64 | 0.5 | -23.4 |
| 9a2f8e8424b1431f94ee947f4dec4fdb | mysql | migration | 64 | 0.5 | -18.3 |
| cd389ffc0e4f41189c7aa0e46021db7c | mysql | migration | 64 | 0.5 | -33.6 |
| dbbeb32fbe50449fa23924731bf0e58a | mongo | migration | 64 | 0.5 | -23.7 |
| e833fd35d27c4e65bfd8db18a40b5777 | mongo | migration | 64 | 0.5 | -42.5 |
| effda834ce8644feb5ca17b948c5ece3 | mongo | migration | 64 | 0.5 | 13.6 |

Nếu có lượt lệch: kéo dài warmup cho MỌI hệ (đề, mục 2.1) rồi đo lại.
