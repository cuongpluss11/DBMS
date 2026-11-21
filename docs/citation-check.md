# Kiểm tra trích dẫn trong tài liệu ý tưởng

Tài liệu ý tưởng yêu cầu đối chiếu các con số trong cột "Bài báo nói" (bảng dự đoán của mục 2.2 và 2.3) với bản gốc, ghi số trang hoặc bảng; **số nào không tìm lại được thì bỏ hoặc ghi "chưa kiểm chứng"**. Phụ trách: Duy Anh. Cập nhật bảng này bằng PR nhỏ.

**Cách ghi kết quả:** `Khớp` (đúng như tài liệu), `Lệch: <số đúng là ...>`, hoặc `Chưa kiểm chứng` (không tìm lại được trong bản gốc). Không chép nguyên văn dài từ bài báo; diễn đạt lại và ghi trang hoặc bảng. Không đưa số chưa kiểm chứng vào kết luận của báo cáo như thể đã có nguồn.

| # | Nguồn | Vị trí trong tài liệu | Khẳng định cần kiểm (theo tài liệu ý tưởng) | Trang / bảng trong bản gốc | Kết quả | Người kiểm | Ngày |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Harding et al. 2017 | 2.2 | Khóa kiểu "xung đột là hủy ngay" (NO_WAIT) hơn các cách khác tới 54% khi toàn ghi, tới 78% khi tranh chấp cao | | | | |
| 2 | Harding et al. 2017 | 2.2 | MVCC tụt mạnh từ θ ≈ 0,5 (đo trên bộ dữ liệu khác: YCSB, hàng triệu dòng) | | | | |
| 3 | Harding et al. 2017 | 2.2 | OCC tốn hơn 50% thời gian cho kiểm tra và sao chép | | | | |
| 4 | Huang et al. 2020 | 2.2 | TiDB lạc quan thường nhanh hơn bi quan, trừ khi dữ liệu nhỏ và rất nhiều client (1.024 client trên 50 hoặc 100 kho) | | | | |
| 5 | Huang et al. 2020 | 1.2 | Ở chế độ bi quan khóa được lấy ngay khi chạy lệnh, nên khi vào pha chốt giao dịch không còn bị hủy vì xung đột | | | | |
| 6 | Zamanian et al. 2016 | 2.2 | Dù mạng rất nhanh, nếu mọi giao dịch sửa cùng một bản ghi thì tỉ lệ hủy vẫn vọt lên | | | | |
| 7 | Heiss & Wagner 1991 | 2.2 và 1.2 | Giới hạn mức đồng thời theo số đo gần đây tránh được sụp hiệu năng do tranh chấp (thrashing) | | | | |
| 8 | Schroeder et al. 2006 | 2.2 và 1.2 | Kết quả đo ở tải vòng kín và vòng mở có thể lệch rất xa | | | | |
| 9 | Zhang et al. 2021 (DAF) | 2.2 | Hoãn bảo trì vật lý, để giao dịch tham gia xử lý kèm back-pressure; trên TPC-C (NoisePage) giữ thông lượng ổn định hơn cấu hình ít worker bảo trì chuyên dụng; bài không đề xuất cách giải quyết tranh chấp ghi trên cùng một bản ghi | | | | |
| 10 | Merhi & Haraty | 2.2 | Mục 10.B gọi đích danh Flash-sale và khóa tăng dần là kịch bản khó nhất | | | | |
| 11 | Zamanian et al. 2016 (Exp. 4) | 2.3 | Lệch cao thì tỉ lệ hủy vọt lên và không mở rộng được dù mạng rất nhanh (kèm Merhi & Haraty Mục 10.B) | | | | |
| 12 | Merhi & Haraty, Mục 10.B | 2.3 | Khóa tăng dần trên phân vùng theo dải làm mọi dòng mới rơi vào Region cuối | | | | |
| 13 | Harding et al. 2017 | 2.3 | Đơn chạm 2–4 kho trên các nút khác nhau làm thông lượng giảm khoảng 12–40% | | | | |
| 14 | Huang et al. 2020 | 2.3 | Kiến trúc Region/Raft: Region leader nằm rải trên nhiều nút nên tải đều thì thêm TiKV làm thông lượng tăng | | | | |
| 15 | Pavlo & Aslett 2016; Merhi & Haraty, Mục 1 | 1.1 | Lý do có NoSQL và NewSQL (căn cứ cho phần mở đầu) | | | | |
| 16 | Bhattacherjee et al. (BullFrog), SIGMOD 2021 | 1.4 và 2.4 | Đổi lược đồ logic ngay và chuyển dữ liệu vật lý khi giao dịch truy cập tới, trên nguyên mẫu mở rộng PostgreSQL | | | | |

Hai dòng "Dự đoán của nhóm" trong bảng 2.3 (chẳng hạn MySQL được cấp thêm lõi nhưng tải dồn vào một món thì tăng ít) không có nguồn bài báo và không cần kiểm ở đây; chỉ cần ghi rõ trong báo cáo đó là dự đoán của nhóm.

Ngoài ra tài liệu nhắc điểm gãy θ ≈ 0,5 của Harding et al. đo cho MVCC **trên bộ dữ liệu khác, chưa phải kết quả của nhóm**; khi có số đo thật thì sửa lại câu đó trong báo cáo.
