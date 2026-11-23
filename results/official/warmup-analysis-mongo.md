# Phân tích warmup từ chuỗi TPS theo giây

135 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongo |  | 24.0 | 135 | 1.00 | 0 | 0 | 1.00 | 0.03 | 0.1 |

Lượt ngoài khoảng ramp 0,9–1,1: 0/135, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

