# Hướng dẫn Khởi tạo, Thực hiện & Chụp Minh chứng Demo Phần 2 (Mục 2.1 – 2.4 → Chèn vào Phụ lục C)

Tài liệu này hướng dẫn chi tiết cách khởi tạo, thực thi và bấm chụp **7 tấm hình minh chứng UI (`Hình C.7.1` → `Hình C.7.7`)** phủ kín toàn bộ **4 cụm nội dung còn lại của Phần 2** (**Mục 2.1.4, Mục 2.2, Mục 2.3, Mục 2.4**), gồm:
- **Phần I:** Thứ tự bật/tắt Docker tối ưu (mỗi DBMS chỉ cần bật **đúng 1 lần**) và thiết lập MySQL Workbench / MongoDB Compass.
- **Phần II:** Từng bước chạy lệnh, chỉ rõ **thời điểm bấm chụp màn hình**, vùng giao diện cần lấy và **câu chú thích chuẩn** đặt dưới mỗi hình.
- **Phần III:** Khối văn bản học thuật ngắn gọn (**Mục C.7 + Bảng C.7**) để **copy–paste thẳng vào cuối Phụ lục C** (kèm bảng gợi ý nếu bạn muốn rải từng hình vào đúng các mục con `C.1.1`, `C.1.5`, `C.2`, `C.3.1`, `C.3.3`).

---

## Phần I. Thứ tự khởi tạo môi trường tối ưu (chỉ bật mỗi DBMS 1 lần)

Mở **PowerShell** tại thư mục gốc `e:\BTL-DBMS`. Toàn bộ demo dùng cơ sở dữ liệu độc lập **`demo_p2`**, không đụng tới dữ liệu benchmark. Thực hiện theo **3 đợt** dưới đây để không phải bật/tắt container lặp lại:

| Đợt chạy | Hệ quản trị | Lệnh bật container | Các hình chụp trong đợt này | Lệnh dừng khi xong đợt |
| :---: | --- | --- | --- | --- |
| **Đợt 1** | **MongoDB 8.0.20** | `docker compose -f docker/compose.mongo.yml up -d` | **`Hình C.7.3`** *(Mục 2.2: `WriteConflict code 112` & Retry)* | `docker compose -f docker/compose.mongo.yml stop` |
| **Đợt 2** | **MySQL 8.4.8** | `docker compose -f docker/compose.mysql.yml up -d` | **`Hình C.7.2`** *(Mục 2.2: `data_lock_waits`)*<br/>**`Hình C.7.4`** *(Mục 2.3.1: `Đọc rồi ghi đè` gây Lost Update)*<br/>**`Hình C.7.5`** *(Mục 2.3.2: `UNIQUE request_id` chống trùng đơn)*<br/>**`Hình C.7.6`** *(Mục 2.4.1: `Chia slot` chạy song song không chờ khóa)*<br/>**`Hình C.7.7`** *(Mục 2.4.4: `FOR UPDATE NOWAIT` báo lỗi tức thì)* | `docker compose -f docker/compose.mysql.yml stop` |
| **Đợt 3** | **TiDB v8.5.7** | `docker compose -f docker/compose.tidb.yml up -d` | **`Hình C.7.1`** *(Mục 2.1.4: `EXPLAIN FORMAT='brief'` xác nhận `Point_Get`)* | `docker compose -f docker/compose.tidb.yml stop` |

> **Nhắc lại 3 thao tác chuẩn trên MySQL Workbench (áp dụng cho Đợt 2 & Đợt 3):**
> 1. **Edit → Preferences → SQL Editor:** Đặt `DBMS connection read time out = 300`.
> 2. **Bật đủ 3 khung:** `SQL Editor` (trên) + `Result Grid` (giữa) + `Action Output` (dưới). Trước mỗi tấm hình mới, chuột phải vào **`Action Output → Clear`** để nhật ký sạch gọn.
> 3. **Mở 3 kết nối độc lập từ màn hình `🏠 Home`:** Ở Đợt 2 (MySQL `:13306`), bấm `🏠 Home` rồi nhấp đúp vào ô kết nối `MySQL_Local` **3 lần** để tạo **Kết nối 1, Kết nối 2, Kết nối 3** trên thanh tab trên cùng *(không dùng `Ctrl + T`)*.

---

## Phần II. Hướng dẫn thực hiện chi tiết & Thời điểm bấm chụp (`Hình C.7.1` – `Hình C.7.7`)

---

### ĐỢT 1: Trên MongoDB 8.0.20 (`mongodb://127.0.0.1:27018/?directConnection=true`)

#### Kịch bản Mục 2.2 (MongoDB) — Xung đột ghi `WriteConflict (code 112)` & Thử lại giao dịch (`Hình C.7.3`)

1. Khởi động MongoDB (đảm bảo MySQL và TiDB đang dừng):
   ```powershell
   docker compose -f docker/compose.mysql.yml stop
   docker compose -f docker/compose.tidb.yml stop
   docker compose -f docker/compose.mongo.yml up -d
   ```
2. Mở **MongoDB Compass** → kết nối `mongodb://127.0.0.1:27018/?directConnection=true` → mở thanh **`>_ MONGOSH`** ở góc dưới, gõ `cls` để xóa sạch màn hình.
3. Dán toàn bộ đoạn script mô phỏng 2 phiên giao dịch `snapshot` cùng mua mặt hàng nóng `(1, 101)` dưới đây vào `>_ MONGOSH` và bấm `Enter`:
   ```javascript
   db = db.getSiblingDB("demo_p2");
   db.stock.drop();
   db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 });

   const s1 = db.getMongo().startSession();
   const s2 = db.getMongo().startSession();
   s1.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority", j: true } });
   s2.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority", j: true } });

   // (1) Phiên s1 trừ 2 sản phẩm trên mặt hàng nóng (1, 101) nhưng chưa commit
   s1.getDatabase("demo_p2").stock.updateOne(
     { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 2 } },
     { $inc: { s_quantity: -2 } }
   );

   // (2) Phiên s2 đồng thời cập nhật cùng tài liệu (1, 101) -> WiredTiger hủy ngay với lỗi WriteConflict
   let conflictInfo = null;
   try {
     s2.getDatabase("demo_p2").stock.updateOne(
       { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
       { $inc: { s_quantity: -3 } }
     );
   } catch (err) {
     conflictInfo = { code: err.code, codeName: err.codeName, errorLabels: err.errorLabels };
     s2.abortTransaction();
   }

   // (3) Phiên s1 commit (tồn 5 -> 3); Phiên s2 thử lại (retry) giao dịch mới thành công (tồn 3 -> 0)
   s1.commitTransaction();
   s2.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority", j: true } });
   const retryRes = s2.getDatabase("demo_p2").stock.updateOne(
     { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
     { $inc: { s_quantity: -3 } }
   );
   s2.commitTransaction();
   s1.endSession(); s2.endSession();

   printjson({
     step1_conflict_caught: conflictInfo,
     step2_retry_modifiedCount: retryRes.modifiedCount,
     final_stock: db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 })
   });
   ```
4. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.3`:**
   - **Vùng cần lấy:** Khung `>_ MONGOSH` hiển thị rõ khối JSON kết quả in ra cuối cùng:
     - `step1_conflict_caught`: **`{ code: 112, codeName: 'WriteConflict', errorLabels: [ 'TransientTransactionError' ] }`**
     - `step2_retry_modifiedCount: 1`
     - `final_stock: { s_w_id: 1, s_i_id: 101, s_quantity: 0 }` *(tồn kho giảm chính xác `5 → 3 → 0` sau khi thử lại)*.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.3. Minh chứng cơ chế xung đột ghi trên MongoDB 8.0.20 (WiredTiger): khi hai giao dịch đa tài liệu cùng cập nhật mặt hàng `(1, 101)`, phiên đến sau bị hủy ngay với mã lỗi `WriteConflict (code 112, TransientTransactionError)` và hoàn tất chính xác (`s_quantity: 5 → 0`) ở lần thử lại.*

---

### ĐỢT 2: Trên MySQL 8.4.8 (`127.0.0.1:13306` — Chụp liên hoàn 5 hình `C.7.2`, `C.7.4`, `C.7.5`, `C.7.6`, `C.7.7`)

#### Bước chuẩn bị chung cho Đợt 2 (tạo DB `demo_p2` trên MySQL)
1. Chạy trong PowerShell:
   ```powershell
   docker compose -f docker/compose.mongo.yml stop
   docker compose -f docker/compose.mysql.yml up -d
   ```
2. Đợi ~15 giây cho MySQL sẵn sàng. Mở **MySQL Workbench**, từ màn hình **`🏠 Home`** nhấp đúp mở **3 tab kết nối độc lập** tới MySQL `127.0.0.1:13306` (**Kết nối 1, Kết nối 2, Kết nối 3**).
3. Tại **Kết nối 1**, dán và bấm `Ctrl + Shift + Enter` để khởi tạo toàn bộ bảng mẫu cho cả 5 kịch bản:
   ```sql
   SET SQL_SAFE_UPDATES = 0;
   CREATE DATABASE IF NOT EXISTS demo_p2;
   USE demo_p2;
   DROP TABLE IF EXISTS order_line_p0, orders, stock_slot, stock;

   CREATE TABLE stock (
     s_w_id INT NOT NULL, s_i_id INT NOT NULL, s_quantity INT NOT NULL,
     PRIMARY KEY (s_w_id, s_i_id)
   );
   CREATE TABLE stock_slot (
     ss_w_id INT NOT NULL, ss_i_id INT NOT NULL, ss_slot INT NOT NULL, ss_quantity INT NOT NULL,
     PRIMARY KEY (ss_w_id, ss_i_id, ss_slot)
   );
   CREATE TABLE orders (
     o_id INT PRIMARY KEY,
     request_id VARCHAR(64) NOT NULL,
     o_w_id INT NOT NULL, o_d_id INT NOT NULL,
     UNIQUE KEY uq_request_id (request_id)
   );
   CREATE TABLE order_line_p0 (
     ol_o_id INT PRIMARY KEY, ol_i_id INT NOT NULL, ol_quantity INT NOT NULL
   );

   INSERT INTO stock VALUES (1, 101, 5);
   INSERT INTO stock_slot VALUES (1, 101, 0, 5), (1, 101, 1, 5);
   ```

---

#### 2.1. Kịch bản Mục 2.2 (MySQL) — Hàng chờ khóa dòng trên Hot SKU (`Hình C.7.2`)

1. **Ở Kết nối 1 (khách 1 mua 3 sản phẩm và đang giữ khóa dòng):**
   ```sql
   USE demo_p2;
   BEGIN;
   UPDATE stock SET s_quantity = s_quantity - 3
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;
   -- KHÔNG CHẠY COMMIT! (Đang giữ khóa độc quyền trên dòng (1, 101))
   ```
2. **Ở Kết nối 2 (khách 2 cùng mua mặt hàng nóng `(1, 101)`):**
   ```sql
   USE demo_p2;
   BEGIN;
   UPDATE stock SET s_quantity = s_quantity - 3
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;
   ```
   → Kết nối 2 lập tức xoay vòng **`Running...`** (xếp hàng chờ khóa dòng của Kết nối 1).
3. **Ở Kết nối 3 (quan sát trực tiếp hàng đợi khóa dòng InnoDB):** Chuột phải `Action Output → Clear`, dán và chạy:
   ```sql
   SELECT
     dl.OBJECT_NAME AS table_name,
     dl.INDEX_NAME AS index_name,
     dl.LOCK_MODE AS lock_mode,
     dl.LOCK_DATA AS hot_sku_key,
     w.BLOCKING_ENGINE_TRANSACTION_ID AS blocking_trx,
     w.REQUESTING_ENGINE_TRANSACTION_ID AS waiting_trx,
     r.trx_query AS waiting_sql
   FROM performance_schema.data_lock_waits w
   JOIN performance_schema.data_locks dl
     ON dl.ENGINE_LOCK_ID = w.REQUESTING_ENGINE_LOCK_ID
   JOIN information_schema.innodb_trx r
     ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID;
   ```
4. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.2` (chụp màn hình Kết nối 3 ngay lúc Kết nối 2 đang quay vòng):**
   - **Vùng cần lấy:** `SQL Editor` hiện truy vấn `data_lock_waits` và `Result Grid` hiện rõ dòng trạng thái chờ khóa trên `table_name = stock`, `index_name = PRIMARY`, `lock_mode = X,REC_NOT_GAP`, **`hot_sku_key = 1, 101`**, cặp `blocking_trx` / `waiting_trx` và câu lệnh `waiting_sql` đang xếp hàng.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.2. Quan sát hàng chờ khóa dòng trên MySQL 8.4.8 qua `performance_schema.data_lock_waits`: giao dịch đến sau (`waiting_trx`) phải xếp hàng chờ khóa bản ghi `X,REC_NOT_GAP` trên khóa chính mặt hàng nóng `(1, 101)` đang do `blocking_trx` nắm giữ.*
5. **Giải phóng khóa để sang hình tiếp theo:** Qua **Kết nối 1** chạy `COMMIT;` (lập tức Kết nối 2 thoát chờ và báo `0 row(s) affected` vì tồn kho chỉ còn `2 < 3` — không âm kho!), sau đó qua **Kết nối 2** chạy `ROLLBACK;`.

---

#### 2.2. Kịch bản Mục 2.3.1 — *Đọc rồi ghi đè* gây Mất cập nhật / *Lost Update* (`Hình C.7.4`)

*(Kịch bản: Đặt lại tồn kho `= 5`. Hai khách cùng đọc thấy `5`, ứng dụng tự tính `5 - 3 = 2` rồi cùng ghi đè `s_quantity = 2` mà không đặt khóa và không kèm điều kiện ở câu `UPDATE`).*

1. **Ở Kết nối 1 (đặt lại tồn kho về `5`, khách 1 đọc tồn kho thấy `5`):**
   ```sql
   USE demo_p2;
   TRUNCATE TABLE order_line_p0;
   UPDATE stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;

   BEGIN;
   SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
   -- Kết quả đọc = 5 -> Ứng dụng khách 1 tự tính: 5 - 3 = 2 (chưa ghi)
   ```
2. **Ở Kết nối 2 (khách 2 đồng thời vào đọc tồn kho — MVCC đọc không chờ nên cũng thấy `5`!):** Chuột phải `Action Output → Clear`, chạy đoạn 1:
   ```sql
   USE demo_p2;
   BEGIN;
   SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
   -- Kết quả đọc cũng = 5 -> Ứng dụng khách 2 cũng tự tính: 5 - 3 = 2
   ```
3. Quay sang **Kết nối 1**, ghi đè `s_quantity = 2`, lưu chi tiết đơn `1` (mua `3` cái) và `COMMIT`:
   ```sql
   UPDATE stock SET s_quantity = 2 WHERE s_w_id = 1 AND s_i_id = 101;
   INSERT INTO order_line_p0 VALUES (1001, 101, 3);
   COMMIT;
   ```
4. Quay lại **Kết nối 2** *(giữ nguyên Action Output từ bước 2)*, gõ tiếp phần ghi đè của khách 2 + câu truy vấn **đối soát Luật khớp sổ** bên dưới rồi bôi đen chạy phần mới thêm:
   ```sql
   UPDATE stock SET s_quantity = 2 WHERE s_w_id = 1 AND s_i_id = 101;
   INSERT INTO order_line_p0 VALUES (1002, 101, 3);
   COMMIT;

   -- Truy vấn đối soát Luật 2 (Khớp sổ tồn kho vs Tổng lượng hàng đã bán trong đơn)
   SELECT 5 AS initial_stock,
          s.s_quantity AS final_stock,
          (5 - s.s_quantity) AS stock_deducted,
          SUM(ol.ol_quantity) AS total_sold_in_orders,
          CASE WHEN (5 - s.s_quantity) = SUM(ol.ol_quantity)
               THEN 'VALID' ELSE 'INVALID (LOST UPDATE!)' END AS reconciliation_status
   FROM stock s
   JOIN order_line_p0 ol ON ol.ol_i_id = s.s_i_id
   WHERE s.s_w_id = 1 AND s_i_id = 101
   GROUP BY s.s_quantity;
   ```
5. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.4` (chụp màn hình Kết nối 2):**
   - **Vùng cần lấy:** `Result Grid` hiển thị trực diện sai lệch đối soát: `initial_stock = 5` | `final_stock = 2` | **`stock_deducted = 3`** nhưng **`total_sold_in_orders = 6`** → **`reconciliation_status = INVALID (LOST UPDATE!)`**.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.4. Tái hiện lỗi mất cập nhật (Lost Update) của phương pháp đọc rồi ghi đè trên MySQL 8.4.8: hai phiên cùng đọc `s_quantity = 5`, tự trừ `3` và ghi đè `2`, dẫn tới tổng hàng đã bán trong đơn bằng `6` nhưng tồn kho chỉ giảm `3` (`INVALID` theo luật khớp sổ).*

---

#### 2.3. Kịch bản Mục 2.3.2 — Chống trùng đơn khi Retry bằng `UNIQUE (request_id)` & Đọc đối chiếu (`Hình C.7.5`)

1. Tại **Kết nối 1**: chuột phải `Action Output → Clear`, xóa chữ cũ.
2. Dán khối lệnh dưới đây vào SQL Editor:
   ```sql
   USE demo_p2;
   TRUNCATE TABLE orders;

   -- (1) Lần gửi đầu: giao dịch đã COMMIT lưu đơn 5001 nhưng giả sử mất mạng trước khi trả ACK
   INSERT INTO orders (o_id, request_id, o_w_id, o_d_id)
   VALUES (5001, 'req-flashsale-001', 1, 1);

   -- (2) Nếu thử chèn lại cùng request_id: ràng buộc UNIQUE chặn ngay bằng lỗi 1062
   INSERT INTO orders (o_id, request_id, o_w_id, o_d_id)
   VALUES (5002, 'req-flashsale-001', 1, 1);

   -- (3) Worker thay thế đọc đối chiếu theo request_id -> nhận lại đúng đơn 5001, không ghi trùng
   SELECT o_id, request_id, o_w_id, o_d_id,
          COUNT(*) OVER () AS committed_orders_count
   FROM orders
   WHERE request_id = 'req-flashsale-001';
   ```
3. **Cách bấm chạy để có cả dòng lỗi `1062` lẫn bảng kết quả đối chiếu trên cùng 1 màn hình:**
   - Bấm **`Ctrl + Shift + Enter`**: Workbench chạy câu (1) thành công (`1 row affected`) và dừng ở câu (2) với dòng ❌ đỏ **`Error Code: 1062. Duplicate entry 'req-flashsale-001' for key 'orders.uq_request_id'`**.
   - Ngay lập tức đặt con trỏ chuột vào câu `SELECT` số (3) ở cuối và bấm **`Ctrl + Enter`** *(không xóa Action Output!)* → `Result Grid` hiện bảng kết quả của câu (3)!
4. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.5`:**
   - **Vùng cần lấy:**
     - **Result Grid (giữa):** Hiện duy nhất đơn `o_id = 5001`, `request_id = 'req-flashsale-001'`, **`committed_orders_count = 1`**.
     - **Action Output (dưới):** Hiện đủ chuỗi 3 bước: ✅ `INSERT 5001 (1 row affected)` → ❌ `INSERT 5002 Error Code: 1062. Duplicate entry 'req-flashsale-001'` → ✅ `SELECT ... (1 row returned)`.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.5. Kiểm chứng cơ chế chống trùng đơn khi thử lại trên MySQL 8.4.8: chỉ mục duy nhất `uq_request_id` chặn thao tác chèn lặp cùng `request_id` (`Error 1062`), đồng thời bước truy vấn đối chiếu xác nhận chỉ tồn tại duy nhất một đơn đã chốt (`o_id = 5001`, `committed_orders_count = 1`).*

---

#### 2.4. Kịch bản Mục 2.4.1 — Chia slot tồn kho (`stock_slot`) chạy song song không chặn nhau (`Hình C.7.6`)

*(Mặt hàng `(1, 101)` có tổng tồn `10`, đã chia thành `ss_slot = 0` (`5` cái) và `ss_slot = 1` (`5` cái)).*

1. **Ở Kết nối 1 (khách 1 mua 3 sản phẩm ở `slot 0` và giữ khóa chưa `COMMIT`):**
   ```sql
   USE demo_p2;
   UPDATE stock_slot SET ss_quantity = 5 WHERE ss_w_id = 1 AND ss_i_id = 101;

   BEGIN;
   UPDATE stock_slot SET ss_quantity = ss_quantity - 3
   WHERE ss_w_id = 1 AND ss_i_id = 101 AND ss_slot = 0 AND ss_quantity >= 3;
   -- KHÔNG CHẠY COMMIT! (Chỉ khóa dòng slot 0)
   ```
2. **Ở Kết nối 2 (khách 2 đồng thời mua 4 sản phẩm của CÙNG mặt hàng `101` nhưng định tuyến vào `slot 1`):** Chuột phải `Action Output → Clear`, dán và chạy:
   ```sql
   USE demo_p2;
   BEGIN;
   UPDATE stock_slot SET ss_quantity = ss_quantity - 4
   WHERE ss_w_id = 1 AND ss_i_id = 101 AND ss_slot = 1 AND ss_quantity >= 4;
   COMMIT;
   ```
   → Khác hẳn cảnh treo cứng ở `Hình C.7.2`, câu `UPDATE` ở Kết nối 2 **hoàn thành tích xanh ngay lập tức (`0.00x sec`, `1 row affected`)** dù Kết nối 1 vẫn chưa `COMMIT`!
3. Qua **Kết nối 1** chạy `COMMIT;` để chốt đơn của khách 1, rồi quay lại **Kết nối 2** *(giữ nguyên Action Output)* chạy thêm câu kiểm tra tổng tồn kho các slot bên dưới:
   ```sql
   SELECT ss_w_id, ss_i_id, ss_slot, ss_quantity,
          SUM(ss_quantity) OVER () AS total_remaining_stock
   FROM stock_slot
   WHERE ss_w_id = 1 AND ss_i_id = 101
   ORDER BY ss_slot;
   ```
4. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.6` (chụp màn hình Kết nối 2):**
   - **Vùng cần lấy:**
     - **Result Grid (giữa):** Hiện `ss_slot = 0` còn `2`, `ss_slot = 1` còn `1`, và **`total_remaining_stock = 3`** (`10 - 3 - 4 = 3`).
     - **Action Output (dưới):** Hiện dòng `UPDATE stock_slot ... ss_slot = 1` hoàn tất tức thì (`1 row affected`, `Duration ~0.000–0.015 sec`) không bị chờ khóa.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.6. Minh chứng cơ chế chia slot tồn kho (`stock_slot`): trong khi Phiên 1 đang giữ khóa cập nhật `ss_slot = 0`, Phiên 2 cập nhật `ss_slot = 1` của cùng mặt hàng `(1, 101)` hoàn tất tức thì không chờ khóa và bảo toàn chính xác tổng tồn kho còn lại (`10 - 3 - 4 = 3`).*

---

#### 2.5. Kịch bản Mục 2.4.4 — Cơ chế đặc thù `SELECT ... FOR UPDATE NOWAIT` (`Hình C.7.7`)

1. **Ở Kết nối 1 (giữ khóa dòng mặt hàng nóng `(1, 101)`):**
   ```sql
   USE demo_p2;
   UPDATE stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;
   BEGIN;
   SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101 FOR UPDATE;
   -- KHÔNG CHẠY COMMIT!
   ```
2. **Ở Kết nối 2 (yêu cầu khóa kèm cờ `NOWAIT`):** Chuột phải `Action Output → Clear`, dán và chạy:
   ```sql
   USE demo_p2;
   BEGIN;
   SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101 FOR UPDATE NOWAIT;
   ```
3. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.7` (chụp màn hình Kết nối 2):**
   - **Vùng cần lấy:** `SQL Editor` hiện câu `SELECT ... FOR UPDATE NOWAIT;` và `Action Output` hiện dòng ❌ đỏ báo lỗi ngay lập tức trong **`0.000 sec`**: **`Error Code: 3572. Statement aborted because lock(s) could not be acquired immediately and NOWAIT is set`**.
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.7. Kiểm chứng cơ chế `FOR UPDATE NOWAIT` trên MySQL 8.4.8: khi dòng `(1, 101)` đang bị khóa bởi giao dịch khác, hệ thống trả lỗi hủy câu lệnh tức thì (`Error 3572`, `0,000 s`) thay vì xếp hàng chờ khóa, giải thích việc giải phóng kết nối nhanh nhưng làm tăng tỉ lệ `New-Order` thất bại ở Bảng 2.4.5.*
4. Chạy `ROLLBACK;` ở cả Kết nối 1 và Kết nối 2 để đóng giao dịch sạch sẽ trước khi dừng MySQL.

---

### ĐỢT 3: Trên TiDB v8.5.7 (`127.0.0.1:14000`) — Mục 2.1.4: Kiểm chứng `EXPLAIN` chỉ mục (`Hình C.7.1`)

1. Dừng MySQL và khởi động TiDB:
   ```powershell
   docker compose -f docker/compose.mysql.yml stop
   docker compose -f docker/compose.tidb.yml up -d
   ```
2. Đợi ~15 giây cho cụm TiDB sẵn sàng. Mở **1 kết nối** tới `TiDB_Local` (`127.0.0.1:14000`, `root`) trên MySQL Workbench.
3. Chạy khối khởi tạo 4 bảng đúng cấu trúc khóa chính cụm & chỉ mục duy nhất của benchmark:
   ```sql
   CREATE DATABASE IF NOT EXISTS demo_p2;
   USE demo_p2;
   DROP TABLE IF EXISTS orders, district, stock_slot, stock;

   CREATE TABLE stock (
     s_w_id INT NOT NULL, s_i_id INT NOT NULL,
     s_quantity BIGINT NOT NULL, s_ytd BIGINT NOT NULL DEFAULT 0, s_order_cnt INT NOT NULL DEFAULT 0,
     PRIMARY KEY (s_w_id, s_i_id)
   );
   CREATE TABLE stock_slot (
     ss_w_id INT NOT NULL, ss_i_id INT NOT NULL, ss_slot INT NOT NULL,
     ss_quantity BIGINT NOT NULL, ss_ytd BIGINT NOT NULL DEFAULT 0, ss_order_cnt INT NOT NULL DEFAULT 0,
     PRIMARY KEY (ss_w_id, ss_i_id, ss_slot)
   );
   CREATE TABLE district (
     d_w_id INT NOT NULL, d_id INT NOT NULL, d_next_o_id INT NOT NULL,
     PRIMARY KEY (d_w_id, d_id)
   );
   CREATE TABLE orders (
     o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */,
     request_id VARCHAR(64) NOT NULL, o_w_id INT NOT NULL, o_d_id INT NOT NULL,
     UNIQUE KEY uq_request_id (request_id)
   );

   INSERT INTO stock VALUES (1, 101, 100, 0, 0);
   INSERT INTO stock_slot VALUES (1, 101, 0, 50, 0, 0), (1, 101, 1, 50, 0, 0);
   INSERT INTO district VALUES (1, 1, 3001);
   INSERT INTO orders (request_id, o_w_id, o_d_id) VALUES ('req-001', 1, 1);
   ```
4. Chuột phải `Action Output → Clear`, xóa chữ cũ trong SQL Editor, dán **4 câu `EXPLAIN FORMAT = 'brief'`** khớp với Mục 2.1.4 (và tệp `results/official/explain-tidb.json`) rồi bấm **`Ctrl + Shift + Enter`**:
   ```sql
   USE demo_p2;

   -- (1) Trừ tồn kho có điều kiện trên bảng stock
   EXPLAIN FORMAT='brief'
   UPDATE stock SET s_quantity = s_quantity - 4
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

   -- (2) Trừ tồn kho trên bảng chia slot stock_slot
   EXPLAIN FORMAT='brief'
   UPDATE stock_slot SET ss_quantity = ss_quantity - 4
   WHERE ss_w_id = 1 AND ss_i_id = 101 AND ss_slot = 0 AND ss_quantity >= 4;

   -- (3) Đọc khóa bộ đếm mã đơn hàng trên bảng district
   EXPLAIN FORMAT='brief'
   SELECT d_next_o_id FROM district WHERE d_w_id = 1 AND d_id = 1 FOR UPDATE;

   -- (4) Tra cứu chống trùng đơn theo chỉ mục duy nhất uq_request_id
   EXPLAIN FORMAT='brief'
   SELECT o_id FROM orders WHERE request_id = 'req-001';
   ```
5. **📸 THỜI ĐIỂM BẤM CHỤP `Hình C.7.1`:**
   - Bấm vào tab kết quả thứ 2 (`stock_slot`) hoặc thứ 4 (`uq_request_id`) trên thanh `Result Grid` (nơi thấy đủ 4 tab kết quả `Result 1..4` và 4 tích xanh ở `Action Output`), lấy rõ cột **`id = Point_Get`**, **`estRows = 1.00`** và **`access object = table:stock_slot, clustered index:PRIMARY(ss_w_id, ss_i_id, ss_slot)`** (hoặc `index:uq_request_id(request_id)`).
   - **Chú thích đặt dưới ảnh trong Phụ lục C:**
     > *Hình C.7.1. Kiểm tra kế hoạch thực thi bằng `EXPLAIN FORMAT='brief'` trên TiDB v8.5.7 trước khi đo: cả bốn câu lệnh cốt lõi (`UPDATE stock`, `UPDATE stock_slot`, `SELECT ... FOR UPDATE` trên `district` và tra cứu `orders.request_id`) đều truy cập trực tiếp một bản ghi qua chỉ mục (`Point_Get`, `estRows = 1.00`), không phát sinh quét toàn bảng.*
6. Dọn dẹp an toàn sau khi chụp xong:
   ```powershell
   docker compose -f docker/compose.tidb.yml stop
   ```

---

## Phần III. Nội dung gọn để Copy–Paste thẳng vào Phụ lục C (Mục C.7)

> **Cách đặt trong báo cáo:**
> - **Phương án gọn nhất (khuyên dùng):** Dán nguyên khối **Mục C.7 + Bảng C.7** dưới đây nối tiếp vào cuối **Phụ lục C** (ngay sau Mục C.6) để không làm xê dịch bất kỳ số thứ tự bảng/biểu đồ nào đang có ở `C.1 – C.6`.
> - **Phương án rải theo từng mục con:** Nếu muốn đặt ảnh ngay tại từng mục trong Phụ lục C, bạn chèn `Hình C.7.1` vào cuối **C.1.1**, `Hình C.7.2 & C.7.3` vào cuối **C.1.5**, `Hình C.7.4` vào **C.1.2**, `Hình C.7.5` vào **C.2**, `Hình C.7.6` vào **C.3.1** và `Hình C.7.7` vào **C.3.3**.

### C.7. Các kịch bản kiểm chứng trực quan cơ chế giao dịch Phần 2 (Mục 2.1 – 2.4)

Bên cạnh 839 lượt đo tự động trên hạ tầng AWS, nhóm thực hiện bảy kịch bản kiểm chứng trực quan trên cơ sở dữ liệu độc lập `demo_p2` (Docker Compose cục bộ, kết nối qua **MySQL Workbench** và **MongoDB Compass**) nhằm quan sát trực tiếp ở mức câu lệnh kế hoạch truy cập chỉ mục, cơ chế gây nghẽn, lỗi mất cập nhật, chống trùng đơn và giải pháp giảm tranh chấp đã phân tích ở Mục 2.1 – 2.4 (**Bảng C.7**).

**Bảng C.7:** *Tổng hợp bảy kịch bản kiểm chứng trực quan các cơ chế giao dịch ở Mục 2.1 – 2.4.*

| STT | Mục báo cáo & Thao tác thực hiện | Kết quả quan sát thực tế | Cơ chế được chứng minh & Minh chứng |
| :-: | :--- | :--- | :--- |
| 1 | **Mục 2.1.4 (`EXPLAIN` chỉ mục — TiDB v8.5.7):** Chạy `EXPLAIN FORMAT='brief'` cho 4 câu lệnh chính trên `stock`, `stock_slot`, `district` (`FOR UPDATE`) và `orders` (`request_id`). | Cả 4 kế hoạch thực thi đều dùng toán tử `Point_Get` (`estRows = 1.00`) đi thẳng vào `clustered index:PRIMARY` hoặc `index:uq_request_id`. | Xác nhận các thao tác giao dịch cốt lõi định vị trực tiếp bản ghi qua chỉ mục, loại trừ nhiễu do quét toàn bảng (**Hình C.7.1**). |
| 2 | **Mục 2.2 (Hàng chờ khóa dòng — MySQL 8.4.8):** Mở 2 phiên đồng thời chạy `UPDATE stock ... WHERE s_w_id=1 AND s_i_id=101 AND s_quantity>=3`; phiên 3 truy vấn `data_lock_waits`. | Phiên 2 chuyển sang chờ khóa (`Running...`); `data_lock_waits` ghi nhận `waiting_trx` chờ khóa `X,REC_NOT_GAP` trên khóa `(1, 101)` của `blocking_trx`; sau khi phiên 1 `COMMIT`, phiên 2 trả về `0 rows affected`. | Cơ chế xếp hàng chờ khóa bản ghi trên InnoDB giải thích con số `97%` thời gian chờ khóa ở Bảng 2.2.2 mà vẫn ngăn âm kho (**Hình C.7.2**). |
| 3 | **Mục 2.2 (Xung đột ghi — MongoDB 8.0.20):** Mở 2 session giao dịch `snapshot` đồng thời cập nhật cùng tài liệu `stock` `(1, 101)`, bắt ngoại lệ và thực hiện thử lại. | Phiên 2 bị WiredTiger hủy ngay lập tức với lỗi `WriteConflict (code: 112, TransientTransactionError)`; sau khi phiên 1 `commitTransaction()`, phiên 2 thử lại thành công (`s_quantity: 5 → 3 → 0`). | Cơ chế phát hiện xung đột ghi mức tài liệu và hủy–thử lại giải thích `75.207` lỗi `write_conflict`/lượt ở Bảng 2.2.2 (**Hình C.7.3**). |
| 4 | **Mục 2.3.1 (*Đọc rồi ghi đè* — MySQL 8.4.8):** Tồn đầu `= 5`; 2 phiên cùng `SELECT` thấy `5`, tự trừ `3` ở ứng dụng rồi cùng `UPDATE stock SET s_quantity = 2` và ghi 2 đơn. | Hai đơn đã chốt có tổng lượng bán `total_sold_in_orders = 6`, nhưng tồn kho cuối vẫn còn `2` (`stock_deducted = 3`), truy vấn đối soát báo `INVALID (LOST UPDATE!)`. | Minh họa trực tiếp hiện tượng mất cập nhật (*lost update*) làm sai lệch sổ tồn kho của 14 lượt `INVALID` ở Bảng 2.3.1 (**Hình C.7.4**). |
| 5 | **Mục 2.3.2 (Chống trùng đơn — MySQL 8.4.8):** Chèn đơn `5001` với `request_id = 'req-flashsale-001'`, thử chèn lặp đơn `5002` cùng `request_id` và chạy `SELECT` đối chiếu. | Lần chèn lặp bị chặn bởi lỗi `Error 1062: Duplicate entry 'req-flashsale-001' for key 'orders.uq_request_id'`; truy vấn đối chiếu xác nhận `committed_orders_count = 1`. | Ràng buộc `UNIQUE (request_id)` kết hợp bước đọc đối chiếu bảo vệ tuyệt đối luật không trùng đơn khi ứng dụng retry (**Hình C.7.5**). |
| 6 | **Mục 2.4.1 (Chia slot tồn kho — MySQL 8.4.8):** Chia mặt hàng `(1, 101)` (tồn `10`) thành `slot 0` (`5`) và `slot 1` (`5`); phiên 1 giữ khóa trừ `3` ở `slot 0`, phiên 2 đồng thời trừ `4` ở `slot 1`. | Phiên 2 hoàn tất ngay lập tức (`1 row affected`, không chờ khóa của phiên 1); sau khi cả hai chốt, tổng tồn các slot còn đúng `3` (`2 + 1 = 3`). | Tách một mặt hàng nóng thành nhiều dòng độc lập giúp phân tán khóa ghi song song mà vẫn bảo toàn tổng tồn kho (**Hình C.7.6**). |
| 7 | **Mục 2.4.4 (`FOR UPDATE NOWAIT` — MySQL 8.4.8):** Phiên 1 giữ khóa `FOR UPDATE` trên dòng `(1, 101)`; phiên 2 truy vấn cùng dòng kèm mệnh đề `FOR UPDATE NOWAIT`. | Phiên 2 không xếp hàng chờ mà nhận lỗi hủy ngay lập tức (`Error 3572: ... NOWAIT is set`, `0,000 s`). | Giải thích cơ chế thoát nhanh không giữ kết nối chờ khóa, giúp `Payment` tăng tốc nhưng làm `65%` `New-Order` thất bại ở Bảng 2.4.5 (**Hình C.7.7**). |
