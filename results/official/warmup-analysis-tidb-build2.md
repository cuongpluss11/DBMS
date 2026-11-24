# Phân tích warmup từ chuỗi TPS theo giây

30 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | 1 | 20.0 | 15 | 1.01 | 1 | 1 | 1.02 | 0.08 | -1.8 |
| tidb | 3 | 24.0 | 15 | 1.01 | 0 | 1 | 0.99 | 0.09 | 2.3 |

Lượt ngoài khoảng ramp 0,9–1,1: 3/30, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cce6b52406044f30bf080e7eed480bdd | tidb | p1 | 0.0 | 64 | 1 | 1086.1 | 0.73 | 0.16 | 19.1 | VALID |
| 94e99ec074be47d08d26e7bc1b2c2e06 | tidb | p2 | 0.9 | 64 | 1 | 830.6 | 1.26 | 0.08 | -0.1 | VALID |
| 996a4e1517974d1896a5d2714a6f4525 | tidb | p1 | 0.0 | 64 | 3 | 2012.5 | 1.15 | 0.09 | 12.4 | VALID |
