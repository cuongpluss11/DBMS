# Phân tích warmup từ chuỗi TPS theo giây

30 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | 3 | 24.0 | 30 | 1.02 | 3 | 1 | 1.03 | 0.10 | -0.5 |

Lượt ngoài khoảng ramp 0,9–1,1: 4/30, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6fbc1f1eb2c440d8b5385051ba6593d5 | tidb | p2 | 0.9 | 64 | 3 | 1820.0 | 0.70 | 0.14 | 16.9 | VALID |
| 8184b7b1fc6740f7a65e3959d50a7212 | tidb | p1 | 0.9 | 64 | 3 | 524.2 | 0.81 | 0.16 | -1.5 | VALID |
| 2045cad82cf24775bd391ed517d688d5 | tidb | p1 | 0.0 | 64 | 3 | 2226.2 | 0.81 | 0.11 | 2.8 | VALID |
| e414ad243c5c47b4b6f56f4ba9de7b0c | tidb | p2 | 0.9 | 64 | 3 | 1348.1 | 1.10 | 0.11 | -8.2 | VALID |
