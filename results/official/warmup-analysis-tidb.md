# Phân tích warmup từ chuỗi TPS theo giây

214 lượt có chuỗi theo giây. `ramp` = TPS trung vị 10 giây cuối warmup ÷ TPS trung vị 60 giây đo (1,00 = đã ổn định; thấp hơn 1 = còn đang tăng khi bắt đầu đo). `sớm` = 10 giây đầu warmup ÷ TPS đo. `CV` = độ lệch chuẩn ÷ trung bình theo giây trong 60 giây đo. `xu hướng` = nửa sau so với nửa đầu của 60 giây đo.

| engine | TiKV | vCPU | lượt | ramp trung vị | ramp <0,9 | ramp >1,1 | sớm trung vị | CV trung vị | xu hướng trung vị % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tidb | 1 | 20.0 | 21 | 1.00 | 3 | 5 | 1.01 | 0.12 | -0.8 |
| tidb | 3 | 24.0 | 193 | 1.01 | 19 | 25 | 1.01 | 0.08 | -0.5 |

Lượt ngoài khoảng ramp 0,9–1,1: 52/214, trong đó 7 lượt có TPS < 50 (tổng 8 lượt TPS thấp; số giao dịch mỗi giây nhỏ nên tỉ lệ rất giật).

| run_id | engine | biến thể | θ | client | TiKV/vCPU | TPS | ramp | CV | xu hướng % | validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7a2a06341b1045999010392582502e7f | tidb | p1 | 0.0 | 128 | 3 | 21.1 | 14.56 | 1.19 | 47.2 | VALID |
| f56cc2b42a1244fabb3e62c7349be234 | tidb | p1 | 0.0 | 128 | 3 | 22.1 | 6.50 | 1.20 | 62.8 | VALID |
| 64d7d027f130496c9b98ce44ca9a161e | tidb | p1 | 0.0 | 128 | 3 | 22.4 | 5.50 | 1.21 | -24.3 | VALID |
| baf3872b108e4bd8928b8412da26f3a2 | tidb | p1 | 0.0 | 32 | 3 | 34.5 | 2.85 | 1.04 | -48.1 | VALID |
| cb34eeebd40a4f63a5ef3d33c7518840 | tidb | p1 | 0.9 | 32 | 3 | 138.4 | 2.82 | 1.12 | 8.6 | VALID |
| 0ff08862f2804a7d9ae01dab93779ca8 | tidb | p1 | 0.0 | 32 | 3 | 33.3 | 2.24 | 1.03 | 12.6 | VALID |
| 5c9cd3f6941e4ee4a99d1f40aa478179 | tidb | p1 | 0.0 | 64 | 1 | 765.9 | 1.40 | 0.12 | 2.5 | VALID |
| c7dd38b2f9bb4555b56fd63a51a31faf | tidb | p1 | 0.0 | 32 | 3 | 35.5 | 0.62 | 1.01 | 48.2 | VALID |
| cb53a517511b40b0b40d895be33be26c | tidb | p2 | 0.9 | 64 | 1 | 908.1 | 0.66 | 0.11 | -0.7 | VALID |
| a53046f7d91b4dfea045bcc34872875e | tidb | p1 | 0.0 | 64 | 3 | 2222.2 | 0.66 | 0.11 | 12.4 | VALID |
| 1146b58e9ee547be92362fa3d437c356 | tidb | p1 | 0.5 | 64 | 3 | 930.5 | 0.68 | 0.05 | 1.9 | VALID |
| 62641e583e734f24ab5b92a059a929db | tidb | p1 | 0.0 | 64 | 3 | 1736.7 | 0.68 | 0.10 | 6.2 | VALID |
| 70c38a6956064dd6b8c4807abf37ed00 | tidb | p1 | 0.9 | 128 | 3 | 125.3 | 1.27 | 0.76 | 6.4 | VALID |
| 4aceb820b6fe4ca682bf049396b70444 | tidb | p1 | 0.9 | 128 | 3 | 144.2 | 0.75 | 0.74 | -9.1 | VALID |
| c156a8b5025b4e9a97c9a730e8537377 | tidb | p1 | 0.5 | 64 | 3 | 801.9 | 0.76 | 0.09 | 2.4 | VALID |
| e490a76b36ae4069a4ea7935bac1cc2c | tidb | p1 | 0.0 | 64 | 3 | 1486.8 | 1.24 | 0.11 | 10.3 | VALID |
| d6bd5767f1b748bca48b2bc953c3b253 | tidb | p1 | 0.9 | 64 | 3 | 744.7 | 1.23 | 0.11 | -14.6 | VALID |
| d049e19dcfd64f45be90769261a085a5 | tidb | legacy | 0.9 | 32 | 3 | 653.7 | 1.22 | 0.23 | -7.0 | VALID |
| 3dc56840e4f04996afcc99540683a969 | tidb | p1 | 0.9 | 32 | 3 | 151.5 | 0.78 | 1.12 | 28.1 | VALID |
| c28127e9ab5f4734b51f3558c10d54b9 | tidb | p1 | 0.5 | 256 | 3 | 867.8 | 1.21 | 0.12 | -14.0 | VALID |
| 794b1cfec3364a989b96c5d1dfb08bfa | tidb | p2 | 0.9 | 64 | 3 | 765.5 | 0.80 | 0.16 | -11.4 | VALID |
| 829ace59f6dd4e5db028dff35ceb9378 | tidb | p1 | 0.0 | 64 | 3 | 985.3 | 0.80 | 0.02 | 0.5 | VALID |
| 6e640cbdf3fe4e319e4df95ba781f8bc | tidb | p1 | 0.0 | 64 | 3 | 1458.9 | 1.20 | 0.05 | -1.4 | VALID |
| d3f4b7c947f14de1993a87dac13a3178 | tidb | p1 | 0.0 | 64 | 1 | 834.0 | 1.19 | 0.08 | 1.8 | VALID |
| d930846322734bf9a12b5525bd81e4ab | tidb | p2 | 0.9 | 64 | 3 | 2121.4 | 1.19 | 0.05 | -2.0 | VALID |
| 7a43622dad8a4d3a95070523e23ad33e | tidb | p1 | 0.0 | 64 | 3 | 1828.7 | 1.18 | 0.11 | -12.8 | VALID |
| b2e0fd0fd0a547a49bb6c3d06a64f7ec | tidb | legacy | 0.9 | 128 | 3 | 702.6 | 0.82 | 0.14 | 12.5 | VALID |
| 8f1ed34bfd7145d98365911c49a97076 | tidb | p1 | 0.0 | 64 | 3 | 1569.0 | 1.18 | 0.21 | -10.0 | VALID |
| 5570624b6f2e4294b2ed956b4236857e | tidb | p1 | 0.0 | 64 | 3 | 2323.4 | 0.82 | 0.06 | -5.9 | VALID |
| 1cd5af0151e3481f8b490e04c8b835fb | tidb | p1 | 0.0 | 64 | 3 | 1538.9 | 1.17 | 0.11 | -10.6 | VALID |
| 102530d2954e4cbcbcb4ef1649ad76f9 | tidb | p1 | 0.0 | 64 | 3 | 1610.2 | 0.84 | 0.10 | -15.2 | VALID |
| 4acc98a5f6334bba9db1b310d60a8fc0 | tidb | p2 | 0.9 | 64 | 3 | 2313.8 | 1.16 | 0.11 | -10.9 | VALID |
| 145224fe2d8d4dc5ac2476ea4fe68299 | tidb | p1 | 0.7 | 64 | 3 | 767.9 | 1.15 | 0.09 | -10.2 | VALID |
| 144543132aa14966853d21a3fe6b1503 | tidb | p2 | 0.9 | 64 | 1 | 825.5 | 1.15 | 0.17 | -17.1 | VALID |
| e66e586d7a18411590efcff3219fcbd3 | tidb | p1 | 0.9 | 256 | 3 | 799.8 | 1.15 | 0.12 | -16.0 | VALID |
| 2af4a415cedc4b0e8c0447128a187e17 | tidb | p1 | 0.0 | 64 | 3 | 1342.5 | 1.15 | 0.15 | 24.3 | VALID |
| 6f39d0f49fe54521a5a8d0ccf46aa569 | tidb | p1 | 0.9 | 64 | 3 | 807.4 | 1.14 | 0.14 | -5.6 | VALID |
| c374d504614549be81d4f3751ec2abe8 | tidb | p1 | 0.9 | 64 | 1 | 588.5 | 1.14 | 0.16 | -10.1 | VALID |
| 4a55e5181a094488b97d3b9b7662ce08 | tidb | p2 | 0.0 | 64 | 3 | 967.0 | 0.86 | 0.03 | -2.8 | VALID |
| c5ce938e57ee4c69bf3d7d4b232d0658 | tidb | p1 | 0.7 | 8 | 3 | 500.4 | 0.86 | 0.10 | -0.5 | VALID |
| 772907f55d404074b4341210d00269fa | tidb | p2 | 0.0 | 64 | 3 | 219.9 | 1.13 | 0.13 | 2.9 | VALID |
| d07f7cb41f784ed2918b95ea585a9818 | tidb | p1 | 0.7 | 64 | 3 | 983.1 | 0.88 | 0.03 | 0.7 | VALID |
| 41fb167c97f74104adf4df377c774e74 | tidb | legacy | 0.9 | 32 | 3 | 763.6 | 0.88 | 0.09 | 13.8 | VALID |
| a4c94d1d827e448e80b2141a4880c2fe | tidb | p2 | 0.9 | 64 | 1 | 845.2 | 0.88 | 0.12 | 6.4 | VALID |
| e2903417d8584967963067f5bac33e9e | tidb | p1 | 0.0 | 64 | 1 | 788.1 | 1.12 | 0.12 | -5.2 | VALID |
| 27b65016a8674c1ebf857171333bc7e4 | tidb | p1 | 0.9 | 128 | 3 | 730.0 | 1.12 | 0.21 | 4.4 | VALID |
| 233eae0af64142db8d38cb4f4024eb89 | tidb | p2 | 0.0 | 64 | 3 | 2221.9 | 1.11 | 0.11 | -13.3 | VALID |
| 68ed473c80d748048ce25c74ce22d6a7 | tidb | p2 | 0 | 8 | 3 | 49.1 | 1.11 | 0.16 | -17.4 | VALID |
| 369c79ab38b64a5593461680fa0246e7 | tidb | p2 | 0.9 | 64 | 1 | 743.8 | 0.89 | 0.16 | 8.7 | VALID |
| 1198fd0f8cc146a0bc2245ca1d4853e2 | tidb | p2 | 0.9 | 64 | 3 | 2495.1 | 0.90 | 0.07 | 6.1 | VALID |
| 624e22f667414e54affdc0562342ae8f | tidb | p2 | 0.9 | 64 | 3 | 1643.3 | 0.90 | 0.10 | 4.6 | VALID |
| 3702f347eafd4e1cb24e0fa609244f26 | tidb | legacy | 0.0 | 32 | 3 | 240.8 | 0.90 | 0.04 | 3.3 | VALID |
