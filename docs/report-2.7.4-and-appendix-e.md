# Bản thảo rút gọn: Mục 2.7.4, Tài liệu tham khảo [12]–[17] & Phụ lục E (~1,5–2 trang)

> **Hướng dẫn sử dụng:**
> - **PHẦN A:** Hiệu đính gọn **Mục 2.7.4** trên trang 44 PDF (sửa 2 lỗi gõ máy `vấn về` → `vấn đề`, `Sotify` → `Shopify` và gắn trích dẫn `[12]–[17]`) kèm 6 tài liệu tham khảo chuẩn IEEE nối sau `[11]`.
> - **PHẦN B (Phụ lục E):** Đã cắt bỏ toàn bộ phần dẫn dắt dài dòng, sơ đồ phụ và bảng trùng lặp; chỉ giữ **3 mục ngắn (`E.1 – E.3`)** và **2 bảng cốt lõi (`Bảng E.1 – E.2`)** đi thẳng vào đối chiếu kỹ thuật và giới hạn áp dụng.

---

# PHẦN A — MỤC 2.7.4 & TÀI LIỆU THAM KHẢO [12]–[17] (TRANG 44 BÁO CÁO CHÍNH)

## 2.7.4. Liên hệ thực tiễn và khả năng ứng dụng

Các vấn đề khảo sát trong báo cáo tương đồng trực tiếp với thách thức vận hành của các nền tảng thương mại điện tử lớn. Các công bố kỹ thuật từ Shopify [12]–[15], Shopee [16] và Alibaba Cloud [17] đều cho thấy kiểm soát tranh chấp trên dữ liệu nóng, bảo toàn tính nhất quán tồn kho, điều tiết lưu lượng và tối ưu mô hình dữ liệu trước khi mở rộng ngang là những yếu tố quyết định dưới tải đột biến.

Kết quả thực nghiệm ở Mục 2.2–2.6 cung cấp cơ sở định lượng để tham khảo khi chọn cơ chế kiểm soát đồng thời, phân chia tồn kho kết hợp cấp mã đơn theo lô, chống trùng đơn khi ứng dụng lỗi, lập kế hoạch mở rộng cụm phân tán và đổi lược đồ trực tuyến.

Nghiên cứu không tái hiện toàn bộ kiến trúc Flash-sale của một doanh nghiệp cụ thể mà cô lập tầng giao dịch cơ sở dữ liệu bền vững. Việc áp dụng vào sản xuất cần đánh giá thêm cơ chế giữ và hoàn trả tồn kho theo thời hạn, thanh toán bất đồng bộ, hàng đợi thông điệp và khả năng chịu lỗi máy chủ cơ sở dữ liệu (*failover*). Chi tiết đối chiếu trình bày tại **Phụ lục E**.

---

## Bổ sung vào cuối mục Tài liệu tham khảo *(Nối tiếp sau [11] ở trang 44)*

[12] E. Noel, "We replaced Redis with MySQL for inventory reservations—and it scaled," *Shopify Engineering*, May 12, 2026. [Online]. Available: https://shopify.engineering/scaling-inventory-reservations [Accessed: Nov. 28, 2026].

[13] J. Neufeld, "Performance Testing At Scale—for BFCM and Beyond," *Shopify Engineering*, Jan. 27, 2023. [Online]. Available: https://shopify.engineering/scale-performance-testing [Accessed: Nov. 28, 2026].

[14] E. Stolarsky, "Surviving Flashes of High-Write Traffic Using Scriptable Load Balancers (Part I)," *Shopify Engineering*, 2017. [Online]. Available: https://shopify.engineering/surviving-flashes-of-high-write-traffic-using-scriptable-load-balancers-part-i [Accessed: Nov. 28, 2026].

[15] E. Stolarsky, "Surviving Flashes of High-Write Traffic Using Scriptable Load Balancers (Part II)," *Shopify Engineering*, Feb. 5, 2017. [Online]. Available: https://shopify.engineering/surviving-flashes-of-high-write-traffic-using-scriptable-load-balancers-part-ii [Accessed: Nov. 28, 2026].

[16] C. Liu and C. Hong, "How Shopee Chose the Right Database for Their Applications," *PingCAP Case Study*, 2020. [Online]. Available: https://www.pingcap.com/case-study/choosing-right-database-for-your-applications/ [Accessed: Nov. 28, 2026].

[17] Alibaba Cloud, "Build a business system that can handle flash sales," *Alibaba Cloud Tair (Redis OSS-Compatible) Documentation*. [Online]. Available: https://www.alibabacloud.com/help/en/redis/use-cases/use-apsaradb-for-redis-to-build-a-business-system-that-can-handle-flash-sales [Accessed: Nov. 28, 2026].

---
---

# PHẦN B — PHỤ LỤC E (BẢN RÚT GỌN TRỌNG TÂM)

## Phụ lục E: Đối chiếu với kiến trúc Flash-sale thực tế và khả năng ứng dụng kết quả nghiên cứu

Phụ lục này đối chiếu kết quả thực nghiệm ở Mục 2.2–2.6 với các báo cáo kỹ thuật công khai của **Shopify [12]–[15]**, **Shopee [16]** và **Alibaba Cloud [17]** nhằm xác định vị trí của tầng giao dịch CSDL trong hệ thống Flash-sale thực tế và phạm vi áp dụng của nghiên cứu. Trong mỗi mục, phần tóm tắt nguồn công bố được tách riêng với phần phân tích đối chiếu của nhóm; các bài kỹ thuật doanh nghiệp không phải là benchmark cùng cấu hình và số TPS trong báo cáo không dùng để dự báo năng lực hệ thống sản xuất.

### E.1. Đối chiếu với Shopify: Phân tách tồn kho, kiểm thử tải và điều tiết [12]–[15]

- **Giữ hàng bằng MySQL và phân tách điểm nóng [12]:** Năm 2026, Shopify công bố chuyển hệ thống giữ hàng (*inventory reservations*) từ Redis về cùng cơ sở dữ liệu MySQL với sổ tồn kho để bảo đảm giao dịch ACID. Để tránh nghẽn khóa trên một dòng bộ đếm, mỗi đơn vị hàng khả dụng được tách thành một dòng trong *pool* tối đa `1.000` dòng cho mỗi cặp *(sản phẩm, địa điểm)*, kết hợp `SELECT ... FOR UPDATE SKIP LOCKED`, khóa chính ghép và mức cô lập `READ COMMITTED`; khi pool cạn, hệ thống bổ sung từ sổ kho dưới khóa. Đây là trường hợp thực tế gần nhất với chẩn đoán chờ khóa dòng `97%` trên MySQL (Mục 2.2) và giải pháp chia slot của nhóm (Mục 2.4), với các điểm giống và khác cốt lõi tại **Bảng E.1**.

**Bảng E.1:** *Đối chiếu cơ chế giữ hàng trên MySQL của Shopify [12] và thiết kế chia slot của nhóm (Mục 2.4).*

| Khía cạnh | Shopify [12] | Nhóm 16 (Mục 2.4) |
| --- | --- | --- |
| **Đơn vị chia nhỏ** | `1` dòng / đơn vị hàng trong pool (`≤ 1.000` dòng). | `1` slot chứa nhiều đơn vị hàng (`N ∈ {1, 3, 9, 27}`). |
| **Cách chọn & né khóa** | `SKIP LOCKED` bỏ qua dòng đang khóa; có nạp bù pool. | Chọn slot ngẫu nhiên, thử slot kế tiếp nếu thiếu; phân bổ tĩnh. |
| **Tính đúng đắn** | Giữ hàng tạm thời và đối chiếu sổ kho trong giao dịch ACID. | Trừ kho và ghi đơn nguyên tử; kiểm tra 3 luật tồn kho (`100% VALID`). |
| **Đánh đổi ở biên** | Pool cạn phải nạp bù đồng bộ dưới khóa, tăng độ trễ. | Có thể báo thiếu hàng cục bộ khi tổng các slot còn ít. |

Từ số liệu Mục 2.4, cần lưu ý hai điểm khi liên hệ với thiết kế của Shopify:
1. *Tách đóng góp của bộ đếm mã đơn:* Ở `64 client`, chế độ `"một món"`, chia `27 slot` kèm cấp mã đơn theo lô `50` tăng TPS `5,9–8,5 lần` (`426 → 2.741` trên MySQL; `673 → 3.955` trên MongoDB; `255 → 2.157` trên TiDB). Tuy nhiên, Mục 2.4.2 chỉ ra riêng cấp mã theo lô đã đóng góp `1,2–2,5 lần` khi `N = 9` (nhưng không giúp MySQL/TiDB khi `N = 1`), chứng tỏ sau khi tách dòng tồn kho nóng, điểm nghẽn sẽ dồn sang các bộ đếm tuần tự dùng chung.
2. *Khác biệt giữa `NOWAIT` và `SKIP LOCKED`:* Thử nghiệm `FOR UPDATE NOWAIT` trên một dòng tồn kho (Mục 2.4.4, `128 client`) làm tăng `72%` TPS tổng nhờ `Payment` nhưng số đơn đặt thành công **giảm `10%`** (`~65%` `New-Order` bị hủy ngay), khác bản chất với `SKIP LOCKED` vốn bỏ qua dòng bận để lấy ứng viên rảnh khác trong pool. Nhóm chưa đo `SKIP LOCKED` nên không đánh đồng hai cơ chế.

- **Kiểm thử tải cực đoan [13] và điều tiết lưu lượng (*backpressure*) [14], [15]:**
  - *Kiểm thử Flash-sale:* Khi kiểm thử quy mô BFCM, Shopify xây dựng luồng riêng mô phỏng nhiều người cùng mua một sản phẩm nóng `[13]`. Tương ứng, Mục 2.2 cho thấy nếu chỉ đo tới `θ = 0,7` thì TPS cả ba hệ gần như đi ngang; điểm gãy `2,8–3,7 lần` chỉ lộ diện ở chế độ `"một món"`.
  - *Điều tiết theo phản hồi tải:* Shopify đặt bộ giới hạn bằng Nginx/Lua ở biên mạng kèm hàng đợi ưu tiên theo thời điểm đến `[14], [15]`, trong khi nhóm điều tiết số giao dịch chạm món nóng ở tầng ứng dụng theo `p99`/tỉ lệ hủy (Mục 2.4.3). Dưới tải vòng mở `256 client` (`θ = 0,9`), bộ điều tiết giúp MongoDB hạ `p99` từ `327` xuống `67 ms` (tải `3.700/s`, chưa quá tải), nhưng trên MySQL ngưỡng `500 ms` thấp hơn `p99` tự nhiên (`555 ms`) làm TPS sụt `1.788 → 1.399` và `p99` vọt lên `4.712 ms`; chỉ khi nới ngưỡng lên `1.000–2.000 ms` hiệu năng mới khôi phục ngang chia slot. Điều này khẳng định ngưỡng điều tiết phải hiệu chỉnh theo độ trễ nền từng DBMS *(chưa đo vòng mở trên TiDB)*.

### E.2. Đối chiếu với Shopee và Alibaba Cloud: Mở rộng ngang và ranh giới nguyên tử [16], [17]

- **Shopee — Mở rộng ngang TiDB phụ thuộc mô hình truy cập [16]:** Case study trên PingCAP (số liệu cuối 2019) cho biết Shopee dùng MySQL cho tải chuẩn, Redis đệm tải đột biến và TiDB (`>20` cụm, `>400` nút) cho dữ liệu lớn cần mở rộng ngang hoặc Online DDL; một lần gộp `1.000` bảng MySQL sang TiDB từng làm truy vấn quét rộng trở nên đắt, buộc đội ngũ phải đổi cấu trúc phục vụ truy vấn. Kết quả Mục 2.5 định lượng quy luật tương tự cho tải ghi nóng: ở `θ = 0,9, 64 client`, tăng `1 → 3 TiKV` với một dòng tồn kho chỉ cải thiện `1,22–1,29×`, nhưng kết hợp chia `27 slot` đạt hiệu ứng tương tác `3,44–3,80×` (`AUTO_RANDOM` nâng hệ số mở rộng từ `2,20×` lên `2,82×`), đồng thời `rf=3` tiêu tốn `25–47%` TPS ở tải ghi lan rộng trên nút `2 vCPU/TiKV`. *(Lưu ý: `[16]` không xác nhận Shopee dùng TiDB trực tiếp trừ tồn kho Flash-sale).*
- **Alibaba Cloud — Kiến trúc nhiều lớp và khoảng hở nguyên tử [17]:** Kiến trúc tham khảo Tair tách tải qua CDN, lớp lọc yêu cầu (`>600.000 QPS`), Lua script kiểm tra–trừ tồn nguyên tử trong bộ nhớ (`>100.000 QPS`) và hàng đợi ghi đơn bất đồng bộ xuống CSDL. Khác với QPS trong bộ nhớ ở lớp lọc, nhóm đo trực tiếp TPS giao dịch bền vững xuống đĩa EBS. Về tính đúng đắn, một Lua script nguyên tử trong Redis/Tair không tự tạo giao dịch nguyên tử xuyên qua hàng đợi và CSDL đơn hàng nếu thiếu đối soát/phục hồi thông điệp — tương tự khoảng hở ở **MongoDB nhúng** (Mục 2.3.3 & 2.4.4: đạt cận dưới `8.354 TPS`, gấp `9,9×` MongoDB giao dịch nhưng vi phạm luật khớp sổ `INVALID` khi ứng dụng chết giữa bước trừ kho và bước ghi đơn).

### E.3. Ma trận khả năng ứng dụng và giới hạn ngoại suy

Trong chuỗi xử lý thực tế (*Người mua → CDN/Lọc biên → Lớp đệm/Hàng đợi [tùy kiến trúc] → Dịch vụ đặt hàng → DBMS bền vững → Đối soát*), nghiên cứu của nhóm bao phủ trực tiếp ba khâu cuối. **Bảng E.2** tổng hợp giá trị tham khảo và giới hạn của từng kết quả.

**Bảng E.2:** *Ma trận khả năng ứng dụng và điều kiện giới hạn của các kết quả nghiên cứu (Mục 2.2–2.6).*

| Vấn đề & Nguồn liên hệ | Kết quả chính của Nhóm 16 | Giá trị ứng dụng tham khảo | Giới hạn phạm vi cần lưu ý |
| --- | --- | --- | --- |
| **Hot SKU** `[12], [13]` | **Mục 2.2:** Sụt `2,8–3,7×` TPS ở `"một món"` (`64 client`); MySQL chờ khóa `97%`, MongoDB retry `40,4%`. | Quy trình kiểm thử điểm gãy cực đoan; phân biệt nghẽn chờ khóa (2PL) và hủy–thử lại (MVCC). | TiDB mới suy luận xếp hàng ở Region nóng, chưa đo trực tiếp thời gian chờ khóa. |
| **Chia tồn kho & bộ đếm** `[12], [17]` | **Mục 2.4.1–2, 2.4.4:** `27 slot` + lô mã `50` tăng `5,9–8,5×` TPS (`100% VALID`); riêng lô mã tăng `1,2–2,5×` ở `N = 9`. | Tách dòng nóng kết hợp cấp ID theo lô ngay trong giao dịch ACID khi không muốn tách sang Redis. | Cần xử lý thêm báo hết hàng giả cục bộ, cân bằng lại slot hoặc thử nghiệm `SKIP LOCKED`. |
| **Đúng đắn khi lỗi** `[12], [17]` | **Mục 2.3:** `14` lượt đọc–ghi đè `INVALID`; `UNIQUE(request_id)` + đọc đối chiếu giữ `0` vi phạm khi giết worker TiDB (`76` & `95` lần trúng cửa sổ commit). | Mẫu chuẩn chống âm kho, lệch sổ và trùng đơn khi mạng đứt hoặc ứng dụng chết giữa yêu cầu. | Giết tiến trình MySQL/MongoDB mới đo **sơ bộ Docker**; chưa kiểm chứng sập nút DBMS (*failover*). |
| **Điều tiết tải** `[14], [15]` | **Mục 2.4.3:** Hạ `p99` trên MongoDB (`327 → 67 ms`); MySQL sụt `22–48%` TPS ở ngưỡng `500 ms`, khôi phục ở `1.000–2.000 ms`. | Phải đặt ngưỡng cắt cao hơn `p99` tự nhiên của từng DBMS để tránh từ chối sớm gây ứ hàng đợi. | Chưa đo vòng mở trên TiDB; chưa có hàng đợi công bằng theo thứ tự đến như tầng biên `[15]`. |
| **Mở rộng TiDB** `[16]` | **Mục 2.5:** `1 → 3 TiKV` đơn lẻ tăng `1,22–1,29×`, kèm chia slot đạt `3,44–3,80×`; `rf=3` giảm `25–47%` TPS tải ghi rộng. | Phải khử điểm nóng dữ liệu/khóa tự tăng trước khi thêm nút lưu trữ và tính trước chi phí CPU của Raft `rf=3`. | Cụm `1` và `3 TiKV` dựng riêng; mức giảm `25–47%` gắn với cấu hình `2 vCPU/TiKV`. |
| **Đổi lược đồ** *(mở rộng, liên hệ `[16]`)* | **Mục 2.6 *(sơ bộ Docker)*:** MySQL `INSTANT` treo `57 s` nếu gặp đọc dài (`lock_wait_timeout=3` còn `2 s`); TiDB `0 s`. `Batch 1.000` giữ TPS cao nhất ở `q ≥ 25%`. | Đặt `lock_wait_timeout` ngắn kèm retry trước DDL trên MySQL; tránh `Eager` giờ cao điểm, chọn `Batch 1.000`/`Lazy` theo `q`. | Số đo **sơ bộ 1 VM Docker**; chưa quét `q = 5%, 50%` trên TiDB; không gắn với doanh nghiệp cụ thể. |

**Bốn giới hạn khi ngoại suy sang hệ thống sản xuất:** *(1)* Nghiên cứu gộp trừ kho và chốt đơn trong một giao dịch ngắn, chưa mô hình hóa giữ hàng có thời hạn (*TTL*), chờ cổng thanh toán và hoàn tồn khi hết hạn; *(2)* Tắt mọi lớp cache ngoài DBMS và cố định bộ đệm `3 GiB`, khác với kiến trúc sản xuất nhiều lớp dùng CDN/Redis và phần cứng lớn; *(3)* Tương quan giữa ba hệ phụ thuộc cách chia `24 vCPU` (TiDB Server giữ `16 vCPU`, 3 nút TiKV chỉ có `6 vCPU`, mốc chính `rf=1`); *(4)* Mới kiểm chứng sự cố tiến trình ứng dụng chết, chưa bao phủ chuyển đổi dự phòng khi sập máy chủ DBMS hoặc chia cắt mạng.
