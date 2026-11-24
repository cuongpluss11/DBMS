# Phân tích warmup từ chuỗi TPS theo giây

45 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql |  | 20.0 | 30 | 0.98 | 3 | 0 | 1.21 | 0.06 | -0.1 |
| mysql |  | 24.0 | 15 | 0.98 | 1 | 0 | 1.20 | 0.06 | -1.0 |

Lượt ngoài khoảng ramp 0,9–1,1: 4/45, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5eec23c1e6184f16b07ecac33d5347ba | mysql | p1 | 0.0 | 64 | 20.0 | 1324.7 | 0.77 | 0.13 | -9.7 | VALID |
| 04c4d39e842c4471ac224a390c802cd8 | mysql | p1 | 0.0 | 64 | 20.0 | 1180.7 | 0.87 | 0.08 | 0.3 | VALID |
| bb643eb0ee194ff5a0c75ad61ae92d01 | mysql | p1 | 0.9 | 64 | 20.0 | 1233.7 | 0.89 | 0.10 | 5.7 | VALID |
| 0dabc50a56eb41638c04241d0ea0d21d | mysql | p1 | 0.9 | 64 | 24.0 | 1218.0 | 0.89 | 0.11 | 7.0 | VALID |
