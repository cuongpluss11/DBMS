# Bảng 2×2 của TiDB với vị trí dữ liệu và tải từng node (θ=0,9, một kho, 64 client, lô mã 50)

Sinh bởi `scripts/placement_summary.py` từ `result.json` của 2.3 (AWS). CPU = % của một vCPU trung bình trong 60 giây đo (TiKV m6i.large có 2 vCPU nên tối đa 200%; TiDB server 16 vCPU nên tối đa 1.600%).

| TiKV | Thiết kế | TPS (trung vị) | Region `stock` theo store | Region `stock_slot` theo store | CPU PD | CPU TiDB | CPU từng TiKV |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | P1 (N=1) | 616 | s1:13 | n/a | 16% | 215% | tikv1=165% |
| 1 | P2 (N=27) | 845 | s1:13 | s1:136 | 20% | 301% | tikv1=200% |
| 1 | P2 (N=3) | 707 | s1:13 | s1:16 | 16% | 251% | tikv1=200% |
| 1 | P2 (N=9) | 849 | s1:13 | s1:46 | 18% | 299% | tikv1=200% |
| 3 | P1 (N=1) | 751 | s1:5/s2:4/s7:4 | n/a | 18% | 282% | tikv1=66%, tikv2=123%, tikv3=63% |
| 3 | P2 (N=27) | 2,121 | s1:7/s2:4/s7:4 | s1:46/s2:45/s7:45 | 31% | 844% | tikv1=138%, tikv2=199%, tikv3=190% |
| 3 | P2 (N=3) | 1,726 | s1:5/s2:4/s7:4 | s1:6/s2:5/s7:5 | 30% | 687% | tikv1=133%, tikv2=191%, tikv3=174% |
| 3 | P2 (N=9) | 2,087 | s1:7/s2:4/s7:4 | s1:16/s2:15/s7:15 | 30% | 822% | tikv1=140%, tikv2=199%, tikv3=179% |
