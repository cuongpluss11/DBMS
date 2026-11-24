# Khung báo cáo cuối kỳ

Hạn nộp **28/11/2026** (một file PDF `NhomXX_TenDeTai_BaoCao.pdf` vào SharePoint); đường dẫn mã nguồn, dữ liệu, kịch bản demo (GitHub/Drive, **đã cấp quyền truy cập**) điền vào file tổng hợp của lớp trưởng; câu hỏi phản biện chéo hạn **29/11**; thuyết trình tối đa 15 phút (10–12 phút trình bày, 2–3 phút hỏi đáp).

Mọi con số dưới đây truy được về CSV/JSON đã commit trong `results/official/` (kiểm bằng `scripts/verify_doc_numbers.py`, 235 ô khớp). Nguyên tắc ngôn ngữ: gọi workload là **"flash-sale tùy biến dựa trên TPC-C"**, không phải kết quả TPC-C chuẩn.

## Tên và câu hỏi nghiên cứu

**Tên:** Chẩn đoán và giảm nghẽn tranh chấp khóa trong Flash-sale trên MySQL InnoDB, MongoDB và TiDB, kiểm chứng không oversell, và đánh giá mở rộng của TiDB (phụ: đổi lược đồ khi đang chạy).

- **RQ1:** Khi nhiều giao dịch cùng mua một mặt hàng, mức độ tập trung và số client ảnh hưởng thế nào đến TPS, p99, tranh chấp và abort trên ba DBMS?
- **RQ2:** Cập nhật có điều kiện (P1), chia tồn kho N slot (P2) và điều tiết thích ứng (P3) cải thiện được bao nhiêu mà vẫn giữ ba luật tồn kho?
- **RQ3:** Đóng góp riêng của từng phương pháp (kể cả cấp mã đơn theo lô) là bao nhiêu và khi nào chi phí vượt lợi ích?
- **RQ4–RQ6 (TiDB):** thêm TiKV, chia tồn kho và replication ảnh hưởng thế nào; chi phí đóng góp của từng yếu tố.

## Cấu trúc và nguồn bằng chứng

### Phần 1. Giới thiệu và cài đặt (khoảng 1,5–2 trang)
| Mục | Nội dung | Nguồn |
| --- | --- | --- |
| 1.1 | Ba hệ và đúng những cơ chế Phần 2 đo: khóa dòng 2PL (InnoDB), giao dịch nhiều tài liệu (MongoDB), Region/Raft/2PC và lạc quan/bi quan (TiDB) | Btl_final, mục "Phần 1 – Kiến trúc" |
| 1.2 | Cài đặt: MySQL 8.4.8, MongoDB 8.0.20 (replica set một nút), TiDB/PD/TiKV v8.5.7; AWS mỗi thành phần một VM, máy tải riêng; độ bền ngang nhau (`flush=1`, `sync_binlog=1`; `w:majority, j:true`; Raft mặc định) | `docs/acceptance-2.1.md`, `infra/aws/README.md` |
| 1.3 | Demo cơ bản: nạp 9 bảng TPC-C, một New-Order, `EXPLAIN`, bảng khóa | `README.md` |

### Phần 2. Phân tích chuyên sâu
| Mục | Nội dung chính | Bảng/hình | Nguồn |
| --- | --- | --- | --- |
| **2.0** Workload và phương pháp | New-Order : Payment = 1 : 1, 1–5 mặt hàng, Zipf θ, "một món"; W1 (đo tốc độ) và W2 (kiểm luật, có hết hàng); ba luật INV1–3; 3 lần × (30 s warmup + 60 s đo); VALID/INVALID; sai khác với TPC-C chuẩn; máy tải <80% CPU | Bảng sai khác | `docs/assumptions.md`, `docs/experiment-2.1.md` |
| **2.1** RQ1: chẩn đoán | T1: TPS/p99 theo θ ở ba hệ (hình 1); không có điểm gãy ở θ≤0,7; "một món" sụp 3–4 lần; **MySQL chờ khóa 73% thời gian client ngay ở θ=0** (nghẽn ở hàng dùng chung); số tranh chấp | Hình 1, `CONTENTION.md` | `results/official/2.2-aws/*/` |
| **2.2** Không oversell (trục chính) | P0 INVALID trên MySQL và TiDB (14 lượt, mất cập nhật INV2); Mongo P0 VALID kèm ~75.000 lỗi `write_conflict` mỗi lượt; fault injection: kết quả TiDB (92/128 lần giết, 76/95 lần trúng cửa sổ commit, 0 vi phạm) và đối chứng âm (51 đơn trùng) | Bảng P0, bảng fault | `docs/fault-injection.md`, `results/official/fault-injection/` |
| **2.3** RQ2–RQ3: giảm nghẽn | P1 → P2 ở ba hệ (hình 2); tách cấp mã theo lô (hình 3); T3 P2 so với P3 (hình 5: MySQL, MongoDB); T4 đòn bẩy riêng từng hệ (hình 6) | Hình 2, 3, 5, 6 | `docs/experiment-2.2.md` |
| **2.4** RQ4–RQ6: TiDB mở rộng | Bảng 2×2 số TiKV × chia slot (hình 4) kèm Region và CPU từng node; nhóm R2 (rf=3 → rf=1 → rf=3, hình 8) kèm metric Raft và iostat; chi phí 2PC nhiều kho (E.a) | Hình 4, 7, 8, `PLACEMENT-2x2.md` | `docs/experiment-2.3.md` |
| **2.5** Demo mở rộng: đổi lược đồ | Eager, Batch nền, Lazy trên MySQL/MongoDB (Docker, **sơ bộ**), video demo | Hình của Cường | `docs/experiment-2.4.md` (Cường) |
| **2.6** Kết luận và giới hạn | Ma trận đánh đổi, câu trả lời câu hỏi tổng, danh sách giới hạn | Bảng tổng hợp | tất cả |

## Câu được phép và không được phép (kỷ luật khẳng định)

| Chủ đề | Được viết | Không được viết |
| --- | --- | --- |
| Nhóm R (replication) | rf=3 thấp hơn rf=1 ở A và P2 (−25% đến −47%), lặp lại ở cả hai thứ tự đo; **nhất quán với** việc TiKV (2 vCPU) là giới hạn | "rf=3 làm chậm 33% ở hot SKU" (R2 bác bỏ); "do" replication khi chưa tách Raft; một con số duy nhất (hai pha rf=3 lệch tới 29%) |
| P3 | Ở ngưỡng theo đặc tả (p99 500 ms, abort 10%), P3 trên MySQL giảm TPS 27–40% khi tải ≥100%; trên MongoDB chỉ giảm p99 | "P3 có hại" hoặc "P3 giảm sụp" nói chung; kết luận cho TiDB (không đo) |
| Hệ số TiKV 1→3 | 1,22× (P1), 2,51× (P2 N=27), 3,44× kết hợp; kèm khoảng min–max (P2 N=27 ở 3 TiKV: 1.545–2.188) | Cơ chế như chứng minh; hai cụm 1 và 3 TiKV là hai lần dựng riêng |
| Mongo (b) | Nhanh hơn (a) (cận dưới 9,9×) nhưng **vi phạm INV2 khi chết giữa chừng** (đã chứng minh bằng test) | "(b) an toàn"; 8.354 TPS là giá trị thật (máy tải 74–78% CPU: là cận dưới) |
| Mongo P0 VALID | Bằng chứng gián tiếp: `write_conflict` ~75.000 lượt | Đã kiểm chứng bằng thí nghiệm tắt phát hiện xung đột |
| p99 Mongo (a) ~345 ms | Tổng backoff 5 retry (310 ms) + xử lý; p99 theo nhóm retry: <1% → 11 ms, ≥25% → 345 ms | Độ trễ của DBMS |
| Fault injection | Giới hạn trên tỉ lệ vi phạm ~3–4% (quy tắc ba, 95%) trong mô hình lỗi **ứng dụng chết**; có đối chứng âm | "Đảm bảo/chứng minh"; kết luận cho DBMS chết hoặc chia cắt mạng; MySQL/Mongo ở mức AWS (mới Docker) |
| MySQL 24 so với 20 vCPU | Đo kiểm soát (cùng buffer pool, đảo thứ tự): TPS không đổi (−0,8% đến +2,2%); MySQL chỉ dùng 1,1–1,9 vCPU | Dùng kết quả 22/11 (0,89–0,94) |

## Bảng "chưa đo", viết thẳng vào giới hạn
T3 trên TiDB; (MySQL 24 so với 20 vCPU đã đo kiểm soát 2026-11-24: không khác biệt); metric Raft theo từng điểm đo; vị trí Region nóng ở B; fault injection MySQL/Mongo trên AWS; DBMS chết/failover; T2 chưa đo không lô ở N=3 và N=27; 2.4 mới ở mức sơ bộ trên Docker.

## Phân công viết và hạn
| Phần | Người | Hạn |
| --- | --- | --- |
| Phần 1, 2.0, trích dẫn (`docs/citation-check.md`) | Duy Anh | 25/11 |
| 2.1–2.4 (đoạn phân tích nguyên nhân trên bảng/hình đã có) | Lực + Duy Anh ghép | 26/11 |
| 2.5 (demo đổi lược đồ, video 1,5 phút) | Cường | 25/11 |
| 2.6 kết luận, ma trận đánh đổi, giới hạn | Duy Anh, Lực duyệt | 26/11 |
| Đối chiếu số trong PDF với CSV, xuất PDF | Lực | 27/11 |
| Nộp PDF và đường dẫn có quyền truy cập | Lực | 28/11 |

## Bố cục thuyết trình (10–12 phút)
1. Bài toán, workload và ba luật tồn kho (1,5 phút).
2. P0 INVALID, rồi P1 (2 phút): hình 1 và bảng P0.
3. Chia slot và cấp mã theo lô (2,5 phút): hình 2 và 3.
4. TiDB: 2×2 và replication (2,5 phút): hình 4 và 8.
5. Fault injection và đối chứng âm (1 phút).
6. Demo 2.4 bằng video (1 phút).
7. Kết luận và giới hạn (1,5 phút).

## Danh sách kiểm trước khi nộp
- [ ] PDF đúng tên `NhomXX_TenDeTai_BaoCao.pdf`, Phần 1 ngắn gọn, Phần 2 chiếm phần lớn.
- [ ] Mỗi con số trong PDF truy được về một CSV (chạy `scripts/verify_doc_numbers.py`, `scripts/verify_results.py`).
- [ ] Đường dẫn GitHub/Drive đã cấp quyền cho giảng viên và các nhóm phản biện.
- [ ] Mọi câu "chưa đo" nằm trong mục giới hạn; không có câu kết luận mạnh nằm ngoài bảng "Được/Không được".
- [ ] Nhãn "sơ bộ" cho mọi số từ Docker (fault injection MySQL/Mongo, 2.4).
- [ ] Slide sẵn sàng (chưa cần nộp); video demo đã quay phòng khi demo thật tốn thời gian khởi tạo.
