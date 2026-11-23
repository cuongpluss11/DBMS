# Phân tích warmup từ chuỗi TPS theo giây

48 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mysql |  | 24.0 | 48 | 1.00 | 1 | 9 | 1.01 | 0.04 | -0.1 |

Lượt ngoài khoảng ramp 0,9–1,1: 10/48, trong đó 0 lượt có TPS < 50 (tổng 0 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 014f1a3baa52480db16824043d7091a1 | mysql | p3 | 0.9 | 256 | 24.0 | 1066.2 | 1.94 | 0.33 | 8.6 | VALID |
| 75ac462754f94851a47e3e687cb9cbcd | mysql | p3 | 0.9 | 256 | 24.0 | 1160.7 | 1.68 | 0.36 | -10.6 | VALID |
| e8a76f478b314c1ab62546a4776fba0a | mysql | p3 | 0.9 | 128 | 24.0 | 1378.8 | 0.72 | 0.25 | -6.0 | VALID |
| 8ff61865b1dc415a80641630f1da7a70 | mysql | p3 | 0.9 | 256 | 24.0 | 1302.7 | 1.27 | 0.40 | -53.5 | VALID |
| 0c8e8157a4ff47c0b2198abf624cc58b | mysql | p3 | 0.9 | 128 | 24.0 | 1155.9 | 1.21 | 0.30 | -2.5 | VALID |
| 66e91a4e9d2c446e9b7c58afc28cb63f | mysql | p3 | 0.9 | 256 | 24.0 | 1100.8 | 1.20 | 0.29 | -22.2 | VALID |
| 3bef382e73b94168bcb426894dc347ad | mysql | p3 | 0.9 | 128 | 24.0 | 1296.8 | 1.18 | 0.21 | 9.0 | VALID |
| e01e9360323f4ebe9c20101ac67e3102 | mysql | p3 | 0.9 | 128 | 24.0 | 1122.5 | 1.17 | 0.28 | -3.1 | VALID |
| ca1ac0b7fbc4419d813459ba69a3b799 | mysql | p3 | 0.9 | 256 | 24.0 | 1367.8 | 1.13 | 0.35 | -46.0 | VALID |
| de82164dc04c41269b870e17d7d03b27 | mysql | p3 | 0.9 | 128 | 24.0 | 1144.4 | 1.11 | 0.27 | -5.4 | VALID |
