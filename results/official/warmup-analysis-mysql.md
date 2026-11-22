# Phân tích warmup từ chuỗi TPS theo giây

187 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql |  | 20.0 | 15 | 1.03 | 0 | 1 | 1.12 | 0.09 | -2.4 |
| mysql |  | 24.0 | 172 | 0.99 | 5 | 4 | 1.09 | 0.08 | -0.4 |

Lượt ngoài khoảng ramp 0,9–1,1: 10/187, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6ac893554d2243d5bc3e7f3e1294bb6d | mysql | p1 | 0.0 | 8 | 24.0 | 416.3 | 1.23 | 0.10 | -6.6 | VALID |
| a1408b26585b400985ba12ab0e75bdc3 | mysql | legacy | 0.0 | 128 | 24.0 | 379.5 | 1.17 | 0.08 | 4.9 | VALID |
| 395b4d1897e1462a87adf7496459b346 | mysql | legacy | 0.0 | 128 | 24.0 | 639.0 | 0.87 | 0.10 | -4.8 | VALID |
| 2d05300f1bb24606a8825b302cc27baf | mysql | legacy | 0.0 | 32 | 24.0 | 382.8 | 0.88 | 0.10 | 5.1 | VALID |
| d155f603fa974341b26021295a39cda7 | mysql | legacy | 0.0 | 32 | 24.0 | 639.0 | 0.88 | 0.10 | 0.8 | VALID |
| e30233b508a9416c845c5d2c6220e96e | mysql | legacy | 0.0 | 32 | 24.0 | 380.8 | 0.88 | 0.10 | -0.9 | VALID |
| 9f7d1de9de944706acaf97bbf0a5d6f0 | mysql | p1 | 0.0 | 64 | 20.0 | 1222.2 | 1.11 | 0.08 | -3.9 | VALID |
| bf41c2de53504efaa056e2acc131259c | mysql | p0 | 0.0 | 8 | 24.0 | 384.2 | 1.11 | 0.12 | 0.8 | INVALID |
| 2b147d5759354abf8404f3cc0e343794 | mysql | legacy | 0.0 | 32 | 24.0 | 413.0 | 1.10 | 0.10 | -4.0 | VALID |
| c3ee986af58a4cf2a533de94fbd1d872 | mysql | p1 | 0.9 | 64 | 24.0 | 1227.5 | 0.90 | 0.10 | 4.8 | VALID |
