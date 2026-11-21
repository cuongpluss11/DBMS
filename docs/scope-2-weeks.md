# Phạm vi thực hiện trong 2 tuần (kế hoạch, chưa kiểm chứng)

Hạn nộp còn 2 tuần (tính từ 2026-11-20), nhóm 3 người (2 người cường độ cao). **Tài liệu ý tưởng vẫn là đặc tả nguồn và thắng mọi tài liệu khác**; file này chỉ ghi quyết định về thứ tự và phần cắt. Không sửa nội dung gốc của tài liệu. Mọi phần cắt phải được ghi vào báo cáo như một lựa chọn có lý do. Ước lượng giờ và chi phí là ước lượng của người lập kế hoạch, chưa đo.

## Nguyên tắc
1. **Hẹp mà chắc hơn rộng mà dở.** Mọi điểm đưa vào kết luận phải VALID (ba luật), có 3 lần lặp độc lập, máy tải không quá 80% CPU, và ghi giới hạn (đĩa 3000 IOPS giới hạn kết quả ≥64 client, máy ảo AWS cùng AZ).
2. **Cắt có thứ tự, mở rộng có ngưỡng.** Làm hết Tầng 1 trước; chỉ mở sang Tầng 2 theo thứ tự ghi dưới khi vượt các cổng kiểm. Tầng 3 chỉ làm nếu còn dư.
3. **Viết code và đo song song**, nhưng không đo thêm sau ngày 12.
4. Giữ Python cho script tải (quyết định của nhóm); máy tải mặc định `c6i.2xlarge`.

## Phạm vi theo hạng mục

| Mục | Tầng 1 (bắt buộc, làm trước) | Tầng 2 (mở rộng theo thứ tự 1→n) | Tầng 3 (nếu còn dư) |
| --- | --- | --- | --- |
| **2.1** | Ba hệ: baseline MySQL-mặc-định và MySQL-chỉnh, một kho, 1 client; baseline uniform và 1 client cho từng hệ; `payment-ytd`; `correctness` (có hết hàng thực); `idempotency-off`; θ ∈ {0; 0,3; 0,5; 0,7; 0,9; "1 món"} ở 8 client; 8/32/64/128/256 client ở θ=0 | — | Lưới đầy đủ θ × client |
| **2.2** | **T1:** P1 ở θ ∈ {0; 0,5; **0,7**; 0,9; "1 món"} × {8; 64; 256} client, ba hệ; P0 (đọc rồi ghi) ở θ ∈ {0; 0,9; "1 món"} × {8; 64}. **T2:** P1 so với P2 với N ∈ {1; 3; 9; 27} ở θ=0,9 và "1 món", có cấp mã theo lô; đối chứng không cấp mã ở N=1 và N=9. **T3:** P2 so với P3 ở 128 và 256 client, θ=0,9, tải vòng mở. **T4:** 5 đòn bẩy (MySQL stored procedure, MySQL NOWAIT, khóa theo thứ tự `i_id` trên MySQL và TiDB, MongoDB thiết kế (b), TiDB lạc quan so với bi quan) ở θ ∈ {0,9; "1 món"} × {32; 128} | (1) T1 thêm θ=0,3 và 32/128 client; (2) T3 thêm θ=0,5; (3) P0 thêm θ=0,5; 0,7 | `AUTO_RANDOM` ở bảng đơn (làm ở 2.3 nhóm D) |
| **2.3** (chỉ TiDB) | **A, B, C (N=3, 9, 27), D (khóa tự tăng so với `AUTO_RANDOM`), E.a (đơn 1/2/3–4 kho, chi phí 2PC)**, mỗi ô 1 TiKV và 3 TiKV, 64 client; MySQL-chỉnh hai cỡ máy làm mốc mở rộng dọc | (1) E.b (vị trí leader); (2) E.c (async commit, 1PC); (3) R (A và B với 3 bản sao) | MongoDB chia shard (tùy chọn theo tài liệu) |
| **2.4** | Giao dịch "Xem đơn cũ"; ba cách chuyển dữ liệu (Eager, Batch nền, Lazy) trên **MySQL** và **MongoDB**, q ∈ {5%; 50%}; kiểm tra đúng đắn migration; chuỗi TPS/p99 theo giây | (1) TiDB; (2) q=25%; | Thêm chỉ mục (nếu có trong E1) |
| **2.5** | Ma trận đánh đổi và câu trả lời cho câu hỏi tổng, dựa trên số đo của Tầng 1 | Bổ sung số đo của Tầng 2 | — |
| **Báo cáo** | Phần 1 (kiến trúc), kiểm trích dẫn, bảng kết quả từ `flashsale report`, mục "Phạm vi và lý do thu hẹp", giới hạn đã biết | — | — |

Lý do giữ từng phần Tầng 1: T1 với θ=0,7 vì tài liệu dự đoán điểm gãy trong 0,5–0,7; P0 để thấy mất cập nhật; A/B/C là lõi câu hỏi 2; ba cách chuyển dữ liệu là lõi câu hỏi 3; 2.4 trên hai hệ đủ để so sánh giữa hệ. Lý do cắt Tầng 3: MongoDB chia shard là phần tùy chọn trong tài liệu; nhóm R và E.b/E.c bổ sung chi tiết cho chi phí Raft và vị trí dữ liệu nhưng không phải lõi của ba câu hỏi. *Cách hiểu E.a/E.b/E.c ở trên là suy từ bảng ma trận của mục 2.3, cần đối chiếu với mục 2.3.1 của tài liệu.*

## Cổng kiểm (go/no-go)

Ngày 1 là ngày bắt đầu 2.2 (2.1 đã nghiệm thu trên AWS); Ngày 14 là hạn nộp. Hạn nộp còn khoảng 14 ngày tính từ lúc 2.1 xong.

| Cổng | Khi nào | Điều kiện đạt | Nếu không đạt | Phụ trách |
| --- | --- | --- | --- | --- |
| **G0** | Đã xong | Quota AWS đã được duyệt (64 vCPU) | — | Lực |
| **G1** | Cuối Ngày 3 | Stack `mysql` dựng lại được và smoke P0–P2 chạy được trên AWS | Chậm 1 ngày chấp nhận được; chậm hơn thì cắt Tầng 2 sớm | Lực |
| **G2** | Cuối Ngày 7 | Code 2.2 chạy mức smoke trên AWS (Lực); code 2.4 trên MySQL chạy mức smoke trên môi trường dev Docker (Cường) | Bỏ toàn bộ Tầng 2. **Nếu Lực trễ so với kế hoạch, Cường nhận P3, tải vòng mở và T3 của 2.2 (chỉ khi cần, đã thống nhất trước)** | Lực, Cường |
| **G3** | Cuối Ngày 9 | 2.2 T1 và T2 xong và VALID; 2.3 nhóm A, B, C xong | Cắt T3 và T4 xuống đòn bẩy rẻ nhất (NOWAIT, khóa theo thứ tự) | Lực |
| **G4** | Ngày 12 | **Chốt số đo** | Không đo thêm; chỉ chạy lại lỗi nhỏ nếu cần | Cả ba |

## Lịch 14 ngày

**Slot AWS (một stack mỗi lúc, giữ đúng kế hoạch ban đầu):** `mysql` Ngày 3–4 (2.2) và Ngày 10 (T3, T4 và 2.4); `mongo` Ngày 5 (2.2) và Ngày 11 (T3, T4 và 2.4); `tidb3` Ngày 6–10 (2.2 TiDB và toàn bộ 2.3). Slot cùng ngày chia theo giờ, Lực điều phối. Phương án dự phòng chạy **hai stack song song** chỉ dùng khi thật sự cần (trễ lịch) và phải ghi thành khác biệt với tài liệu (câu "mỗi lúc chỉ đưa tải vào một hệ").

| Ngày | Lực | Cường | Duy Anh |
| --- | --- | --- | --- |
| 1 | Code P0, P1; cấu hình `--variant` | Thiết kế 2.4: lược đồ `ol_discount`, ba cách chuyển; giao dịch "Xem đơn cũ" | Dựng khung báo cáo; kiểm trích dẫn (Harding 2017, Huang 2020) |
| 2 | P2 (chia tồn kho, cấp mã đơn theo lô), test đơn vị | Eager và Batch trên MySQL (thử trên VM Docker dev) | Kiểm trích dẫn (Zamanian 2016, Heiss và Wagner 1991); bắt đầu Phần 1 |
| 3 | Dựng stack `mysql`; smoke P0–P2 trên AWS; **G1** | Lazy trên MySQL; kiểm tra đúng đắn | Phần 1; viết checklist chạy đo cho Lực |
| 4 | MySQL: 2.2 T1, T2 (qua đêm); code P3 | Migration trên MongoDB (dev Docker) | Theo dõi chạy; kiểm trích dẫn xong (Schroeder 2006, Zhang 2021) |
| 5 | Chuyển stack `mongo`: T1, T2; code tải vòng mở | Kiểm tra đúng đắn MongoDB | Bảng 2.2 MySQL; Phần 1 hoàn thiện |
| 6 | Chuyển stack `tidb3`: T1, T2; code T4 (MySQL, TiDB) | Hoàn thiện 2.4 trên MySQL và MongoDB; viết cấu hình đo (q 5% và 50%) | Bảng 2.2 MongoDB; hình Phần 1 |
| 7 | **G2** smoke 2.2; code script 2.3 (Region, leader), đơn nhiều kho, `AUTO_RANDOM` | **G2** smoke 2.4 trên môi trường dev; chuẩn bị chạy đo | Bảng 2.2 TiDB; kiểm chất lượng |
| 8 | 2.3 nhóm A, B (`tidb1`, `tidb3`) | Dự phòng: review PR của Lực; hướng dẫn chạy 2.4 | Hình 2.2 T1 |
| 9 | 2.3 nhóm C, D; **G3** | Phân tích sơ bộ 2.4 trên dev; chờ slot | Hình 2.2 T2; mục phạm vi và giới hạn |
| 10 | 2.3 nhóm E.a; rồi stack `mysql`: 2.2 T3, T4 | 2.4 đo chính thức trên MySQL | Hình 2.3 |
| 11 | Stack `mongo`: 2.2 T3, T4 | 2.4 đo chính thức trên MongoDB | Bảng 2.4; hướng dẫn tái hiện |
| 12 | **G4** chốt số đo; `terraform destroy`; phân tích 2.2 | Phân tích 2.4; 2.5 bản nháp | Bảng cuối; đối chiếu số trong báo cáo với `INDEX.csv` |
| 13 | Viết kết quả 2.2 và 2.3 | Viết 2.4 và kết luận 2.5 | Hiệu đính, mục lục, thuật ngữ |
| 14 | Cả ba: đọc lại toàn bộ, sửa lỗi cuối, nộp | Cả ba | Cả ba |

## Phân công (đã chốt 2026-11-21)

Quyết định của nhóm: **Lực làm toàn bộ 2.2 và 2.3** cùng việc vận hành AWS; **Cường chỉ làm 2.4**; **Duy Anh làm phụ, hỗ trợ Lực ở 2.2 và 2.3** bằng các việc đơn giản, ít cẩn thận và tốn thời gian. Giờ ước tính trong 14 ngày: Lực ~60, Cường ~50, Duy Anh ~55 (ước lượng chưa đo; Lực là người nặng nhất).

**Quy tắc chung.** Trợ lý AI viết phần lớn code và test đơn vị; người sở hữu mục đó review, chạy thử trên DBMS thật và sửa lỗi. Lực giữ quyền `terraform apply` và `destroy`; người khác đăng ký khung giờ với Lực. Cường phát triển và thử 2.4 trên môi trường dev Docker (VM `TestTiDB` cũ), không chiếm slot stack AWS cho đến khi đo chính thức; số đo từ Docker chỉ là sơ bộ. Mỗi người làm trên nhánh riêng, PR nhỏ mỗi ngày; file hay xung đột (`adapters/sql.py`, `adapters/mongo.py`, `workload/generator.py`, `cli.py`, `runner.py`) cần báo trước khi sửa.

| Người | Phụ trách | Giờ ước tính |
| --- | --- | --- |
| **Lực** | 2.2 code (P0–P3, tải vòng mở, 5 đòn bẩy T4) 20; vận hành AWS 6; 2.2 đo 8; 2.2 phân tích 8; 2.3 code (script Region/leader, đơn nhiều kho, `AUTO_RANDOM`) 8; 2.3 đo 6; 2.3 phân tích 4 | ~60 |
| **Cường** | "Xem đơn cũ" 4; 2.4 code (Eager, Batch nền, Lazy trên MySQL rồi MongoDB) 18; kiểm tra đúng đắn migration 8; 2.4 đo 8; 2.4 phân tích 6; 2.5 bản nháp 6 | ~50 |
| **Duy Anh** | Kiểm trích dẫn 8; Phần 1 báo cáo 10; theo dõi chạy đo 2.2 và 2.3 10; bảng và hình 2.2 và 2.3 8; theo dõi hằng ngày (trạng thái, chi phí) 5; kiểm chất lượng (`pytest`, `INDEX.csv`) 4; mục phạm vi và giới hạn 5; hiệu đính 5 | ~55 |

**Không giao cho Duy Anh:** `terraform apply` và `destroy`, các lệnh đặt Region ở 2.3, sửa code đo (dễ làm sai số liệu mà không ai biết).

**Rủi ro chính của cách chia này:** Lực là nút thắt (2.2 + 2.3 + AWS). Giảm bằng cách để Duy Anh theo dõi chạy và xử lý kết quả, kiểm tra tại G2, và nếu trễ thì Cường nhận P3, tải vòng mở và T3 (đã thống nhất trước, chỉ khi cần). Phương án chạy hai stack song song cũng chỉ dùng khi cần.

## Ngân sách (ước lượng, chưa đo)
Phạm vi Tầng 1 ước khoảng 70–90 giờ máy bật (~80–120 USD với ~1 USD/giờ), dư cho vài lần chạy lại trong 200 USD. Đo chi phí thật sau điểm đầu tiên rồi cập nhật. Mở Tầng 2 và Tầng 3 chỉ khi còn dư cả giờ và tiền.

## Trạng thái
Cập nhật bảng này mỗi ngày: đánh `Chưa làm / Đang làm / Đã đo / Cắt` cho từng dòng và ghi run_id của các lượt đã chốt trong `results/official/`.
