# Phân tích warmup từ chuỗi TPS theo giây

45 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | 3 | 24.0 | 45 | 1.01 | 1 | 2 | 1.03 | 0.09 | -0.4 |

Lượt ngoài khoảng ramp 0,9–1,1: 3/45, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b0ef95d8ce9e48439e661b732a8650db | tidb | p1 | 0.9 | 64 | 3 | 535.1 | 1.26 | 0.24 | -23.7 | VALID |
| 941bab78c2304b978917c90f1b443e05 | tidb | p1 | 0.9 | 64 | 3 | 633.2 | 0.86 | 0.15 | 12.8 | VALID |
| f02f9be183564b139fe9c4dd269a38d7 | tidb | p1 | 0.9 | 64 | 3 | 637.1 | 1.12 | 0.14 | -3.3 | VALID |
