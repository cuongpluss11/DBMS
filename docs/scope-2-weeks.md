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
| **G2** | Cuối Ngày 7 | Code 2.2 chạy mức smoke trên AWS (Lực); code 2.4 trên MySQL chạy mức smoke trên môi trường dev Docker (Cường) | Bỏ toàn bộ Tầng 2. **Nếu tiến độ 2.2 chậm so với kế hoạch, Cường nhận P3, tải vòng mở và T3 của 2.2 (chỉ khi cần, đã thống nhất trước)** | Lực, Cường |
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
| 8 | 2.3 nhóm A, B (`tidb1`, `tidb3`) | Review PR 2.2; hướng dẫn chạy 2.4 | Hình 2.2 T1 |
| 9 | 2.3 nhóm C, D; **G3** | Phân tích sơ bộ 2.4 trên dev; đối chiếu số liệu | Hình 2.2 T2; mục phạm vi và giới hạn |
| 10 | 2.3 nhóm E.a; rồi stack `mysql`: 2.2 T3, T4 | 2.4 đo chính thức trên MySQL | Hình 2.3 |
| 11 | Stack `mongo`: 2.2 T3, T4 | 2.4 đo chính thức trên MongoDB | Bảng 2.4; hướng dẫn tái hiện |
| 12 | **G4** chốt số đo; `terraform destroy`; phân tích 2.2 | Phân tích 2.4; 2.5 bản nháp | Bảng cuối; đối chiếu số trong báo cáo với `INDEX.csv` |
| 13 | Viết kết quả 2.2 và 2.3 | Viết 2.4 và kết luận 2.5 | Hiệu đính, mục lục, thuật ngữ |
| 14 | Cả ba: đọc lại toàn bộ, sửa lỗi cuối, nộp | Cả ba | Cả ba |

## Phân công (đã chốt 2026-11-21)

Quyết định của nhóm: **Lực làm toàn bộ 2.2 và 2.3** cùng việc vận hành AWS; **Cường chỉ làm 2.4**; **Duy Anh hỗ trợ Lực ở 2.2 và 2.3** và phụ trách báo cáo cùng việc tổng hợp kết quả. Giờ ước tính trong 14 ngày: Lực ~60, Cường ~50, Duy Anh ~55 (ước lượng chưa đo, sẽ điều chỉnh sau ba ngày đầu).

**Quy tắc chung.** Trợ lý AI viết phần lớn code và test đơn vị; người sở hữu mục đó review, chạy thử trên DBMS thật và sửa lỗi. Lực giữ quyền `terraform apply` và `destroy`; người khác đăng ký khung giờ với Lực. Cường phát triển và thử 2.4 trên môi trường dev Docker (VM `TestTiDB` cũ), không chiếm slot stack AWS cho đến khi đo chính thức; số đo từ Docker chỉ là sơ bộ. Mỗi người làm trên nhánh riêng, PR nhỏ mỗi ngày; file hay xung đột (`adapters/sql.py`, `adapters/mongo.py`, `workload/generator.py`, `cli.py`, `runner.py`) cần báo trước khi sửa.

| Người | Phụ trách | Giờ ước tính |
| --- | --- | --- |
| **Lực** | 2.2 code (P0–P3, tải vòng mở, 5 đòn bẩy T4) 20; vận hành AWS 6; 2.2 đo 8; 2.2 phân tích 8; 2.3 code (script Region/leader, đơn nhiều kho, `AUTO_RANDOM`) 8; 2.3 đo 6; 2.3 phân tích 4 | ~60 |
| **Cường** | "Xem đơn cũ" 4; 2.4 code (Eager, Batch nền, Lazy trên MySQL rồi MongoDB) 18; kiểm tra đúng đắn migration 8; 2.4 đo 8; 2.4 phân tích 6; 2.5 bản nháp 6 | ~50 |
| **Duy Anh** | Kiểm trích dẫn 8; Phần 1 báo cáo 10; theo dõi chạy đo 2.2 và 2.3 10; bảng và hình 2.2 và 2.3 8; theo dõi hằng ngày (trạng thái, chi phí) 5; kiểm chất lượng (`pytest`, `INDEX.csv`) 4; mục phạm vi và giới hạn 5; hiệu đính 5 | ~55 |

**Phân quyền:** `terraform apply` và `destroy`, các lệnh đặt Region ở 2.3 và việc sửa code đo thuộc về Lực để có một đầu mối chịu trách nhiệm cho hạ tầng và số liệu.

**Rủi ro chính của cách chia này:** khối lượng 2.2, 2.3 và vận hành AWS lớn trong 14 ngày. Chia sẻ việc bằng cách để Duy Anh theo dõi chạy và xử lý kết quả, kiểm tra tiến độ tại G2, và nếu chậm thì Cường nhận P3, tải vòng mở và T3 (đã thống nhất trước, chỉ khi cần). Phương án chạy hai stack song song cũng chỉ dùng khi cần.

## Ngân sách (ước lượng, chưa đo)
Phạm vi Tầng 1 ước khoảng 70–90 giờ máy bật (~80–120 USD với ~1 USD/giờ), dư cho vài lần chạy lại trong 200 USD. Đo chi phí thật sau điểm đầu tiên rồi cập nhật. Mở Tầng 2 và Tầng 3 chỉ khi còn dư cả giờ và tiền.

## Định nghĩa xong cho một điểm đo

Một hạng mục chỉ được đánh **Đã đo** khi đủ bốn điều kiện:
1. Kết quả VALID: ba luật tồn kho đạt và phép kiểm chéo của tài liệu không có dòng sai lệch (riêng `idempotency-off` được phép INVALID và không xếp hạng).
2. Đủ 3 lần lặp độc lập, mỗi lần 30 giây warmup + 60 giây đo, dữ liệu được reset trước mỗi lần.
3. Không có cảnh báo `loadgen_cpu_*` (máy tải dưới ~80% CPU); `warmup_stability` và chuỗi `tps_per_second.csv` đã được xem; có `iostat` của điểm đó.
4. Đã đưa vào `results/official/` kèm `manifest.json` và `INDEX.csv`; nếu là kết quả sơ bộ (Docker) hoặc thí nghiệm riêng thì ghi nhãn rõ.

Phần nào chưa thử trên DBMS thật phải ghi NOT TESTED, không ghi là đã chạy.

## Trạng thái

Cập nhật bảng mỗi ngày: `Chưa làm / Đang làm / Đã đo / Cắt`, ghi run_id các lượt đã chốt trong `results/official/`. Ngày 1 là ngày bắt đầu 2.2; 2.1 đã xong.

| Mục | Hạng mục Tầng 1 | Phụ trách | Trạng thái | Ghi chú |
| --- | --- | --- | --- | --- |
| 2.1 | Nghiệm thu trên AWS (ba hệ) | Lực | Đã đo | `docs/acceptance-2.1.md`, `results/official/2.1-aws/` |
| 2.2 | P0, P1 (đọc rồi ghi, cập nhật có điều kiện) cả ba hệ | Lực | Đang làm | Mã xong; smoke G1 chạy trên MySQL AWS và Docker dev (MySQL, MongoDB) ngày 2026-11-21; TiDB NOT TESTED; xem `docs/experiment-2.2.md` |
| 2.2 | P2 (chia tồn kho N slot, cấp mã đơn theo lô) và validator cộng slot | Lực | Đang làm | Mã xong; smoke G1 trên MySQL AWS VALID (P2 N=9 + lô mã), chưa đo chính thức |
| 2.2 | T1 (P0 và P1 theo θ × client) | Lực | Đã đo (TiDB, MySQL, MongoDB) | `results/official/2.2-aws/tidb3/`, `mysql/`, `mongo/`; script `scripts/run-matrix-2.2.sh` sẵn sàng; slot AWS `mysql`, `mongo`, `tidb3` |
| 2.2 | T2 (P1 so với P2, N = 1, 3, 9, 27) | Lực | Đã đo (TiDB, MySQL, MongoDB) | `results/official/2.2-aws/mongo/` |
| 2.2 | P3 (điều tiết thích ứng), tải vòng mở, T3 | Lực | Đã đo T3 trên MongoDB (`results/official/2.2-aws/mongo-t3/`); chưa đo T3 trên MySQL và TiDB | Cường nhận nếu tiến độ chậm tại G2 |
| 2.2 | T4 (5 đòn bẩy) | Lực | Đã đo (TiDB, MySQL, MongoDB) | T4 đã đo trên cả ba hệ (`results/official/2.2-aws/tidb3/`, `mysql/`, `mongo/`). Mã xong 5/5 (khóa theo thứ tự, NOWAIT, TiDB lạc quan/bi quan, MongoDB (b), stored procedure; thử được trên Docker MySQL/MongoDB, TiDB NOT TESTED); chưa đo |
| 2.3 | Script đặt Region/leader, đơn nhiều kho, `AUTO_RANDOM` | Lực | Đang làm | Mã và unit test xong (PD/TiDB giả lập); đơn nhiều kho thử trên MySQL Docker; smoke TiDB 1 TiKV thật (AWS, sơ bộ): placement, PD API, AUTO_RANDOM/AUTO_INCREMENT hoạt động; chuyển leader giữa 3 TiKV cũng hoạt động (tidb3, sơ bộ); cần TiDB server lớn hơn trước khi đo hệ số tăng tốc; xem `docs/experiment-2.3.md` |
| 2.3 | Nhóm A, B, C, D, E.a (1 và 3 TiKV) | Lực | Đã đo (TiDB) | 1 TiKV (21 lượt) và 3 TiKV (48 lượt gồm E.a) đều VALID: `results/official/2.3-aws/tidb1/`, `tidb3/`, hệ số tăng tốc ở `SUMMARY-speedup.md`; mốc MySQL 24 và 20 vCPU đã đo (30 lượt VALID, `results/official/2.3-aws/mysql/`; hệ số 0,89–0,94, nguyên nhân chưa kiểm chứng) |
| 2.4 | Thiết kế (lược đồ đích, ba cách chuyển, kiểm tra đúng đắn) | Cường | Đã làm | Đã đối chiếu tài liệu chốt, hoàn thiện mã và kiểm chứng thực nghiệm trên MySQL (`18/18 VALID`) và MongoDB (`18/18 VALID`) |
| 2.4 | Giao dịch "Xem đơn cũ" | Cường | Đã đo trên MySQL & MongoDB (sơ bộ) | mặc định tắt (`old_order_read_pct = 0.0`); đã chạy W=10 với `q ∈ {5%, 25%, 50%}` trên MySQL 8.4.8 và MongoDB 8.0.20; TiDB `NOT TESTED` |
| 2.4 | Eager, Batch nền, Lazy trên MySQL rồi MongoDB; kiểm tra đúng đắn | Cường | Đã đo xong MySQL & MongoDB (sơ bộ, 24/24 VALID ở E2) | Trên 1 VM Docker `c6i.4xlarge` (`W=10, q=25%`, cache 3 GiB, độ bền ngang nhau): **MySQL** (`12/12 VALID`): Eager `704,9 TPS` (p99 `896,6 ms`, đỉnh `8,2 s`, `71,3 s`), Batch 1.000 `1.255,2 TPS` (`578,2 ms`, `106,5 s`), Batch 5.000 `1.104,8 TPS` (`619,5 ms`, `89,7 s`), Lazy `1.069,8 TPS` (`588,5 ms`, `97,6 s`); **MongoDB** (`12/12 VALID`): Eager `2.053,0 TPS` (p99 `201,5 ms`, đỉnh `479,8 ms`, `126,8 s`), Batch 1.000 `2.172,4 TPS` (`162,3 ms`, `207,8 s`), Batch 5.000 `2.088,7 TPS` (`161,1 ms`, `197,3 s`), Lazy `1.755,2 TPS` (`143,6 ms`, `202,0 s`). Kết quả ở `results/official/2.4-{eager,batch,lazy}/`; TiDB `NOT TESTED` |
| 2.4 | Đo chính thức (q = 5% và 50%) | Cường | Đang làm (đã đo Lazy MySQL & MongoDB ở q=5%, 25%, 50%, sơ bộ) | Lazy (`results/official/2.4-lazy/`, `18/18 VALID`): **MySQL** `q=5%` `1.027,1 TPS` (`-24,7%`), `q=25%` `1.069,8 TPS` (`-34,6%`), `q=50%` `1.165,4 TPS` (`-47,6%`); **MongoDB** `q=5%` `1.754,7 TPS` (`-6,4%`, on-demand `47.846`), `q=25%` `1.755,2 TPS` (`-20,5%`, on-demand `228.944`), `q=50%` `1.788,9 TPS` (`-38,7%`, on-demand `446.218`). Còn TiDB `NOT TESTED` (và đo chính thức đa VM AWS nếu mở) |
| 2.5 | Ma trận đánh đổi và câu trả lời câu hỏi tổng | Cường | Chưa làm | bản nháp Ngày 12 |
| Báo cáo | Kiểm trích dẫn (`docs/citation-check.md`) | Duy Anh | Chưa làm | |
| Báo cáo | Khung báo cáo, Phần 1 | Duy Anh | Chưa làm | |
| Báo cáo | Bảng và hình kết quả 2.2, 2.3 | Duy Anh | Chưa làm | sau khi có kết quả |

**Chi phí AWS (ghi mỗi ngày từ trang Billing):** chưa có số. Budgets đã đặt ở 100 và 150 USD.

## Ghi chú thiết kế 2.4 (đã chốt trước đó, cần đối chiếu với tài liệu gốc)

Các quyết định dưới đây đã được thống nhất trong các buổi trước; chúng xuất phát từ tab "Đề xuất sửa phần evolution" (Lazy Migration, tab Ver 1.2) của Google Doc nhóm và **chưa được đối chiếu lại với mục 2.4 của `bao_cao_DBMS_ban_chot.docx`** (cần đọc mục đó trước khi code). Chỗ nào lệch thì ghi vào `docs/assumptions.md` và báo Lực.

- Thí nghiệm chính so sánh Eager, Batch nền (lô 1.000 và 5.000) và Lazy (ý tưởng từ BullFrog, SIGMOD 2021) khi thêm `ol_discount` vào `order_line` dưới tải Flash-sale.
- Phép biến đổi dẫn xuất, không dùng giá trị mặc định 0: `ol_discount = floor(ol_quantity * i_price * r / 100)`, với r = 10 nếu `i_price >= 5000`, r = 5 nếu `2500 <= i_price < 5000`, ngược lại r = 0 (ngưỡng có thể chỉnh).
- Lược đồ đích chung: `ol_discount` và `ol_mig_state` (UNMIGRATED / MIGRATED); không dùng IN_PROGRESS vì hàm xác định cộng cập nhật có điều kiện. Dữ liệu cũ là các dòng `order_line` do loader 2.1 nạp (~3 triệu dòng với W=10).
- Giao dịch đọc thứ ba "Xem đơn cũ" mặc định tắt (0%) để 2.1–2.3 không đổi; ở 2.4 chiếm tỉ lệ q của tổng yêu cầu.
- Cần làm trong code: loại giao dịch đọc, bộ chuyển dữ liệu, khôi phục lược đồ sau mỗi lượt (reset hiện chưa gỡ cột), chuỗi TPS và p99 theo giây, mở rộng validator.
- **Chỗ lệch cần chốt:** ghi chú cũ nêu q ∈ {5%, 25%, 50%} (25% là mức chính) và thí nghiệm E1 (thêm cột và thêm chỉ mục bằng DDL gốc, kẹt MDL), còn kế hoạch 2 tuần đặt Tầng 1 là q ∈ {5%, 50%}, 25% ở Tầng 2 và chưa có E1. Cường xác nhận với tài liệu gốc rồi cập nhật bảng phạm vi.
