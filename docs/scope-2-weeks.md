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

| Cổng | Khi nào | Điều kiện | Nếu không đạt |
| --- | --- | --- | --- |
| **G0** | Hôm nay | Đã mở ticket thúc quota AWS (ticket `179516888700824`) | — |
| **G1** | Cuối ngày 3 | Quota vCPU ≥ 32 và 2.1 chạy xong trên MySQL | 2.3 chỉ làm `tidb1` với máy tải nhỏ (quota 16 không đủ `tidb3`); số đo MongoDB/MySQL tạm dùng Docker và ghi rõ là sơ bộ |
| **G2** | Cuối ngày 7 | Code 2.2 và 2.4 (MySQL) chạy được trên AWS ở mức smoke | Bỏ toàn bộ Tầng 2, dồn thời gian cho Tầng 1 |
| **G3** | Cuối ngày 9 | T1, T2 xong và VALID | Cắt T3 và T4 xuống đòn bẩy rẻ nhất (NOWAIT, khóa theo thứ tự) |
| **G4** | Ngày 12 | **Chốt số đo** | Không đo thêm; chỉ chạy lại lỗi nhỏ nếu cần |

## Lịch gợi ý

| Ngày | Đo trên AWS | Code |
| --- | --- | --- |
| 1–2 | Chờ quota; MySQL 2.1 khi có | 2.2: P0–P2, cấp mã theo lô, `--theta`/`--hot-item` đã có |
| 3–4 | MongoDB và TiDB cho 2.1 | 2.2: P3 và tải vòng mở |
| 5–7 | 2.2: T1, T2 | 2.3: script đặt Region/leader; 2.4: "Xem đơn cũ" và migration |
| 8–9 | 2.3: A, B, C, D, E.a | 2.4 hoàn thiện; T4 đòn bẩy |
| 10–11 | 2.4 và T3, T4 còn thiếu | Báo cáo |
| 12 | **Chốt số đo** | Kết luận 2.5 |
| 13–14 | Chỉ chạy lại khi lỗi nhỏ | Báo cáo, kiểm trích dẫn, nộp |

## Phân công vai trò gợi ý
- **Người 1 (cao):** vận hành AWS và chạy đo (Terraform, script ma trận, theo dõi `loadgen_cpu_*`, Budgets, destroy khi xong).
- **Người 2 (cao):** code 2.2 → 2.4 cùng trợ lý AI; chạy thử trên DBMS thật.
- **Người 3:** báo cáo (Phần 1, kiểm trích dẫn, hình và bảng từ `flashsale report`, 2.5).

## Ngân sách (ước lượng, chưa đo)
Phạm vi Tầng 1 ước khoảng 70–90 giờ máy bật (~80–120 USD với ~1 USD/giờ), dư cho vài lần chạy lại trong 200 USD. Đo chi phí thật sau điểm đầu tiên rồi cập nhật. Mở Tầng 2 và Tầng 3 chỉ khi còn dư cả giờ và tiền.

## Trạng thái
Cập nhật bảng này mỗi ngày: đánh `Chưa làm / Đang làm / Đã đo / Cắt` cho từng dòng và ghi run_id của các lượt đã chốt trong `results/official/`.
