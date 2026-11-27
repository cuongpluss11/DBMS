# Hướng dẫn Khởi tạo, Thực hiện & Chụp Minh chứng Demo Mục 2.6 (Đưa vào Phụ lục D)

Tài liệu này gồm **3 phần** dành cho thành viên phụ trách **Mục 2.6 / Phụ lục D**:
- **Phần I:** Cách khởi tạo Docker, cấu hình **MySQL Workbench** và **MongoDB Compass** chi tiết để không bị lỗi dùng chung kết nối hoặc tự ngắt timeout khi demo.
- **Phần II:** Từng bước chạy 4 kịch bản (**D1 – D4**), chỉ rõ **thời điểm bấm chụp màn hình (`Hình D.6` → `Hình D.10`)**, vùng giao diện cần lấy và **câu chú thích chuẩn** đặt dưới mỗi ảnh.
- **Phần III:** Khối văn bản học thuật ngắn gọn (**Mục D.5.3 + Bảng D.6**) để **copy–paste thẳng nối tiếp sau Mục D.5.2** trong Phụ lục D.

---

## Phần I. Cách khởi tạo môi trường & Thiết lập công cụ chi tiết

### 1. Quy tắc bật/tắt container Docker cục bộ
Mở **PowerShell** tại thư mục gốc `e:\BTL-DBMS`. **Chỉ bật duy nhất 1 hệ quản trị tại một thời điểm** theo bảng sau (dữ liệu demo nằm trong database riêng `demo_ose`, hoàn toàn tách biệt với dữ liệu benchmark):

| Thứ tự chụp | Hệ quản trị | Lệnh khởi động container | Công cụ kết nối & Địa chỉ | Lệnh dừng sau khi chụp xong |
| :---: | --- | --- | --- | --- |
| **1** | **MySQL 8.4.8** *(Chụp Hình D.6, D.7, D.9)* | `docker compose -f docker/compose.mysql.yml up -d` | **MySQL Workbench**<br/>Host `127.0.0.1`, Port **`13306`**, User `root` (mật khẩu trống) | `docker compose -f docker/compose.mysql.yml stop` |
| **2** | **TiDB v8.5.7** *(Chụp Hình D.8)* | `docker compose -f docker/compose.tidb.yml up -d` | **MySQL Workbench** (`127.0.0.1`, Port **`14000`**, `root`)<br/>*Tuỳ chọn:* TiDB Dashboard `http://127.0.0.1:12379/dashboard` | `docker compose -f docker/compose.tidb.yml stop` |
| **3** | **MongoDB 8.0.20** *(Chụp Hình D.10)* | `docker compose -f docker/compose.mongo.yml up -d` | **MongoDB Compass** + thanh `>_ MONGOSH`<br/>`mongodb://127.0.0.1:27018/?directConnection=true` | `docker compose -f docker/compose.mongo.yml stop` |

> **Kiểm tra container đã sẵn sàng (healthy) trước khi kết nối:** Sau lệnh `up -d`, chờ khoảng `10–20 giây` rồi chạy `docker ps` — thấy cột `STATUS` báo `Up ... (healthy)` (với MySQL/Mongo) hoặc đủ 5 container `pd, tidb, tikv1..3` đang `Up` (với TiDB) là bắt đầu kết nối được.

### 2. Ba thiết lập bắt buộc trên MySQL Workbench trước khi chạy D1 & D2
1. **Tăng ngưỡng timeout đọc của Workbench (tránh bị tự ngắt sau 30 giây khi thử treo khóa):**
   - Vào menu **Edit → Preferences... → SQL Editor** → đặt **`DBMS connection read time out (in seconds)` = `300`** → bấm **OK**.
2. **Hiển thị đủ 3 khung trên giao diện để ảnh chụp có đủ bằng chứng:**
   - Góc trên bên phải cửa sổ truy vấn có 3 nút bật/tắt khung (trái, dưới, phải) → bật sao cho màn hình hiện đủ: **SQL Editor** *(khung gõ lệnh ở trên)* + **Result Grid** *(bảng dữ liệu ở giữa)* + **Action Output** *(nhật ký dòng tích xanh / báo lỗi ở dưới cùng)*.
   - Trước mỗi tấm hình mới, click chuột phải vào khung **Action Output → `Clear`** để nhật ký bên dưới gọn sạch, chỉ hiện đúng các lệnh của kịch bản đang chụp.
3. **Cách mở nhiều kết nối độc lập (RẤT QUAN TRỌNG cho kịch bản kẹt khóa D1, D2):**
   - **KHÔNG** bấm `Ctrl + T` (mở nhiều tab `SQL File 1, 2...` bên trong cùng 1 tab kết nối sẽ dùng chung 1 phiên TCP nên tự thấy khóa của chính mình, không tạo được hiện tượng chờ khóa!).
   - **Cách làm đúng:** Bấm biểu tượng **🏠 (Home)** ở góc trên cùng bên trái Workbench → nhấp đúp vào ô kết nối `MySQL_Local` **4 lần liên tiếp** để thanh tab trên cùng mở ra **4 tab kết nối độc lập** (ta gọi lần lượt là **Kết nối 1, Kết nối 2, Kết nối 3, Kết nối 4**).

---

## Phần II. Hướng dẫn thực hiện từng bước & Thời điểm chụp 5 tấm hình (`Hình D.6` – `Hình D.10`)

### Kịch bản D1 — Hiện tượng kẹt dây chuyền Metadata Lock & Giải pháp `lock_wait_timeout = 3` trên MySQL 8.4.8 (`Hình D.6` & `Hình D.7`)

#### Bước khởi tạo dữ liệu mẫu `demo_ose` trên MySQL
1. Chạy trong PowerShell:
   ```powershell
   docker compose -f docker/compose.tidb.yml stop
   docker compose -f docker/compose.mongo.yml stop
   docker compose -f docker/compose.mysql.yml up -d
   ```
2. Mở **4 tab kết nối độc lập** tới MySQL (`127.0.0.1:13306`) từ màn hình **🏠 Home**.
3. Tại **Kết nối 1**, dán khối khởi tạo dữ liệu mẫu dưới đây và bấm **`Ctrl + Shift + Enter`** (chạy toàn bộ):
   ```sql
   SET SQL_SAFE_UPDATES = 0;
   CREATE DATABASE IF NOT EXISTS demo_ose;
   USE demo_ose;
   DROP TABLE IF EXISTS order_line, item;

   CREATE TABLE item (i_id INT PRIMARY KEY, i_price INT NOT NULL);
   CREATE TABLE order_line (
     ol_w_id INT NOT NULL, ol_d_id INT NOT NULL,
     ol_o_id INT NOT NULL, ol_number INT NOT NULL,
     ol_i_id INT NOT NULL, ol_quantity INT NOT NULL,
     PRIMARY KEY (ol_w_id, ol_d_id, ol_o_id, ol_number)
   );

   INSERT INTO item VALUES (1, 6000), (2, 3000), (3, 1500);
   INSERT INTO order_line VALUES
     (1, 1, 1001, 1, 1, 2),  -- đơn cũ 1001 (chiết khấu đúng = 1200)
     (1, 1, 1002, 1, 2, 3),  -- đơn cũ 1002 (chiết khấu đúng = 450)
     (1, 1, 1003, 1, 3, 4);  -- đơn cũ 1003 (chiết khấu đúng = 0)
   ```

#### Thực hiện & chụp **Hình D.6** (Chứng minh `ALGORITHM=INSTANT` vẫn gây treo dây chuyền cả bảng)
1. **Ở Kết nối 1 (giả lập giao dịch đọc dài quên `COMMIT`):** Xóa chữ cũ, dán và chạy (`Ctrl + Shift + Enter`):
   ```sql
   USE demo_ose;
   BEGIN;
   SELECT * FROM order_line LIMIT 1;
   -- DỪNG LẠI TẠI ĐÂY: KHÔNG CHẠY COMMIT!
   ```
2. **Ở Kết nối 2 (phát lệnh DDL mặc định không đặt timeout ngắn):** Dán và chạy:
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED',
     ALGORITHM=INSTANT;
   ```
   → Thấy Kết nối 2 lập tức xoay vòng **`Running...`** (đang xếp hàng xin khóa `EXCLUSIVE`).
3. **Ở Kết nối 3 (khách hàng mới vào đọc đơn hàng):** Dán và chạy:
   ```sql
   USE demo_ose;
   SELECT * FROM order_line WHERE ol_o_id = 1001;
   ```
   → Thấy Kết nối 3 cũng lập tức xoay vòng **`Running...`** bị treo cứng theo dù chỉ là câu `SELECT`!
4. **Ở Kết nối 4 (truy vấn bằng chứng khóa siêu dữ liệu):** Chuột phải `Action Output → Clear`, dán và chạy:
   ```sql
   SELECT OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE, LOCK_STATUS, OWNER_THREAD_ID
   FROM performance_schema.metadata_locks
   WHERE OBJECT_SCHEMA = 'demo_ose' AND OBJECT_NAME = 'order_line';
   ```
5. **📸 THỜI ĐIỂM BẤM CHỤP `Hình D.6` (chụp màn hình Kết nối 4 ngay lúc Kết nối 2 và 3 vẫn đang quay vòng):**
   - **Vùng cần lấy:** Cửa sổ Kết nối 4 hiện rõ thanh tab trên cùng (thấy icon đang quay ở tab 2 & tab 3 càng tốt), khung **SQL Editor** chứa câu truy vấn `metadata_locks`, và đặc biệt là **Result Grid** hiện đủ **3 dòng trạng thái khóa**:
     - Dòng 1: `SHARED_READ` | **`GRANTED`** *(phiên đọc mở ở Kết nối 1)*
     - Dòng 2: `EXCLUSIVE` | **`PENDING`** *(lệnh `ALTER TABLE` ở Kết nối 2)*
     - Dòng 3: `SHARED_READ` | **`PENDING`** *(lệnh `SELECT` mới ở Kết nối 3 bị chặn dây chuyền phía sau!)*
   - **Chú thích đặt dưới ảnh trong Phụ lục D:**
     > *Hình D.6. Quan sát `performance_schema.metadata_locks` trên MySQL 8.4.8: một phiên giữ `SHARED_READ (GRANTED)` khiến lệnh `ALTER TABLE ... ALGORITHM=INSTANT` kẹt ở `EXCLUSIVE (PENDING)` và chặn dây chuyền cả truy vấn đọc mới `SHARED_READ (PENDING)`.*

#### Thực hiện & chụp **Hình D.7** (Chứng minh `lock_wait_timeout = 3` tự thoát sau 3s và retry thành công)
1. Chuyển sang **Kết nối 2**, bấm nút **Stop the statement being executed (biểu tượng 🛑 màu đỏ trên thanh công cụ SQL Editor)** để hủy lệnh `ALTER` đang treo → lập tức bên Kết nối 3 câu `SELECT` thoát treo và trả kết quả ngay! *(Kết nối 1 vẫn đang giữ giao dịch `BEGIN` mở chưa `COMMIT`)*.
2. Vẫn ở **Kết nối 2**: chuột phải vào **Action Output → `Clear`** cho sạch, rồi dán khối có gắn `lock_wait_timeout = 3` dưới đây và bấm `Ctrl + Shift + Enter`:
   ```sql
   USE demo_ose;
   SET SESSION lock_wait_timeout = 3;

   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED',
     ALGORITHM=INSTANT;
   ```
   → Đợi đúng **3 giây**: **Action Output** ở Kết nối 2 tự động hiện dấu ❌ đỏ **`Error Code: 1205. Lock wait timeout exceeded; try restarting transaction`** với cột `Duration` xấp xỉ **`3.000 sec`** (nhả hàng đợi ngay, không giữ treo hệ thống!).
3. Bây giờ chuyển qua **Kết nối 1**, gõ `COMMIT;` và bấm `Ctrl + Enter` để đóng phiên đọc dài.
4. Quay lại **Kết nối 2** *(KHÔNG xóa Action Output để giữ nguyên dòng lỗi `Error 1205` làm đối chứng!)*, bôi đen riêng câu `ALTER TABLE order_line ... ALGORITHM=INSTANT;` và bấm `Ctrl + Enter` để thử lại (retry), sau đó chạy thêm `SELECT * FROM order_line;` ngay bên dưới.
5. **📸 THỜI ĐIỂM BẤM CHỤP `Hình D.7` (chụp màn hình Kết nối 2):**
   - **Vùng cần lấy:**
     - **SQL Editor (trên):** Hiện rõ `SET SESSION lock_wait_timeout = 3;` và câu `ALTER TABLE ... ALGORITHM=INSTANT;`.
     - **Result Grid (giữa):** Hiện bảng `order_line` đã có thêm 2 cột mới `ol_discount = NULL` và `ol_mig_state = 'UNMIGRATED'`.
     - **Action Output (dưới):** Hiện nối tiếp **cả 2 khoảnh khắc trên cùng 1 khung**: dòng ❌ đỏ `Error Code: 1205. Lock wait timeout exceeded` (`~3.00 sec` khi còn phiên đọc mở) nằm ngay trên dòng ✅ tích xanh `ALTER TABLE ... 0 row(s) affected` (`~0.015 sec` ở lần retry sau khi phiên đọc `COMMIT`)!
   - **Chú thích đặt dưới ảnh trong Phụ lục D:**
     > *Hình D.7. Cơ chế bảo vệ bằng `SET SESSION lock_wait_timeout = 3` trên MySQL 8.4.8: khi còn phiên đọc mở, lệnh `ALTER` tự hủy sau `3 s` (`Error 1205`) để giải phóng hàng đợi MDL; ngay khi phiên đọc `COMMIT`, lần thử lại hoàn tất tức thì và bổ sung thành công hai cột mới.*

---

### Kịch bản D3 *(chạy luôn trên MySQL đang bật)* — Chuyển đổi *Lazy*, tính lũy đẳng, *Batch* & Đối soát (`Hình D.9`)

> **Mẹo tiết kiệm thời gian:** Vì MySQL đang bật sẵn và bảng `demo_ose.order_line` vừa thêm xong 2 cột ở cuối Bước D1, bạn chạy và chụp luôn **Hình D.9** ngay tại đây trước khi tắt MySQL sang TiDB!

1. Tại **Kết nối 1** trên MySQL Workbench: chuột phải vào **Action Output → `Clear`**, xóa chữ cũ trong SQL Editor, dán toàn bộ khối dưới đây và bấm **`Ctrl + Shift + Enter`**:
   ```sql
   SET SQL_SAFE_UPDATES = 0;
   USE demo_ose;

   -- (1) Đơn hàng mới (ol_o_id > 3000) ghi sẵn chiết khấu và trạng thái MIGRATED
   INSERT INTO order_line VALUES (1, 1, 3002, 1, 1, 2, 1200, 'MIGRATED');

   -- (2a) Chuyển lười (Lazy) lần 1 khi khách xem đơn 1001 -> cập nhật 1 dòng
   UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id
   SET ol.ol_discount = (ol.ol_quantity * i.i_price *
         CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100,
       ol.ol_mig_state = 'MIGRATED'
   WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id = 1001
     AND ol.ol_mig_state = 'UNMIGRATED';

   -- (2b) Chạy lặp lại đúng câu Lazy cho đơn 1001 lần 2 -> 0 dòng bị sửa (chứng minh lũy đẳng)
   UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id
   SET ol.ol_discount = (ol.ol_quantity * i.i_price *
         CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100,
       ol.ol_mig_state = 'MIGRATED'
   WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id = 1001
     AND ol.ol_mig_state = 'UNMIGRATED';

   -- (3) Batch nền: quét dải khóa chính chuyển nốt các đơn còn UNMIGRATED (1002, 1003)
   UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id
   SET ol.ol_discount = (ol.ol_quantity * i.i_price *
         CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100,
       ol.ol_mig_state = 'MIGRATED'
   WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id BETWEEN 1001 AND 3000
     AND ol.ol_mig_state = 'UNMIGRATED';

   -- (4) Kiểm tra trạng thái dữ liệu cuối cùng kèm đối soát công thức trong cùng 1 bảng
   SELECT ol.*,
          (SELECT COUNT(*) FROM order_line ol2 JOIN item i2 ON i2.i_id = ol2.ol_i_id
           WHERE ol2.ol_mig_state <> 'MIGRATED' OR ol2.ol_discount IS NULL
              OR ol2.ol_discount <> (ol2.ol_quantity * i2.i_price *
                 CASE WHEN i2.i_price >= 5000 THEN 10 WHEN i2.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100
          ) AS invalid_rows
   FROM order_line ol
   ORDER BY ol.ol_o_id;
   ```
2. **📸 THỜI ĐIỂM BẤM CHỤP `Hình D.9` (ngay sau khi khối lệnh chạy xong):**
   - **Vùng cần lấy (đủ cả 3 phần trong 1 ảnh duy nhất):**
     - **Result Grid (giữa):** Hiện đủ 4 dòng (`ol_o_id = 1001, 1002, 1003, 3002`), cột `ol_discount` = **`1200, 450, 0, 1200`**, cột `ol_mig_state` đều là **`MIGRATED`**, và cột ngoài cùng **`invalid_rows = 0`**!
     - **Action Output (dưới):** Hiện rõ chuỗi 4 dòng `affected` chứng minh từng cơ chế:
       - `INSERT ... 3002` → **`1 row(s) affected`**
       - `UPDATE ... ol_o_id = 1001` *(lần 1)* → **`1 row(s) affected`**
       - `UPDATE ... ol_o_id = 1001` *(lần 2 — lũy đẳng)* → **`0 row(s) affected`**
       - `UPDATE ... BETWEEN 1001 AND 3000` *(Batch)* → **`2 row(s) affected`** *(tự bỏ qua đơn `1001` đã chuyển!)*
   - **Chú thích đặt dưới ảnh trong Phụ lục D:**
     > *Hình D.9. Kiểm chứng quy trình chuyển đổi dữ liệu có điều kiện và đối soát cuối cùng: cập nhật Lazy đơn `1001` (`1 row affected`), chạy lặp lần hai trả về `0 rows affected` (lũy đẳng), Batch cập nhật nốt 2 đơn còn lại (`2 rows affected`), và bảng kết quả cuối xác nhận toàn bộ đạt `MIGRATED` với `invalid_rows = 0`.*

---

### Kịch bản D2 — Online DDL không chặn giao dịch mới trên TiDB v8.5.7 (`Hình D.8`)

#### Bước dừng MySQL, bật TiDB & tạo dữ liệu `demo_ose`
1. Chạy trong PowerShell:
   ```powershell
   docker compose -f docker/compose.mysql.yml stop
   docker compose -f docker/compose.tidb.yml up -d
   ```
2. Đợi ~15 giây cho cụm TiDB sẵn sàng. Từ màn hình **🏠 Home** của MySQL Workbench, mở **3 tab kết nối độc lập** tới `TiDB_Local` (`127.0.0.1:14000`, `root`, mật khẩu trống).
3. Tại **Kết nối 1 (TiDB)**, dán và chạy lại khối tạo bảng `demo_ose` (cùng khối 15 dòng SQL khởi tạo ở đầu kịch bản D1).

#### Thực hiện & chụp **Hình D.8**
1. **Ở Kết nối 1 (TiDB):** Giữ mở phiên đọc dài chưa `COMMIT`:
   ```sql
   USE demo_ose;
   BEGIN;
   SELECT * FROM order_line LIMIT 1;
   -- KHÔNG CHẠY COMMIT!
   ```
2. **Ở Kết nối 2 (TiDB):** Phát lệnh Online DDL thêm 2 cột:
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';
   ```
   → Kết nối 2 đứng chờ (`Running...`) để đợi Kết nối 1 kết thúc phiên đọc cũ.
3. **Ở Kết nối 3 (TiDB — kiểm chứng giao dịch đọc/ghi mới KHÔNG bị chặn):** Chuột phải vào **Action Output → `Clear`**, dán 2 câu đọc + ghi dưới đây và bấm `Ctrl + Shift + Enter` **ngay trong lúc Kết nối 2 vẫn đang quay vòng chờ**:
   ```sql
   USE demo_ose;
   SELECT * FROM order_line WHERE ol_o_id = 1001;
   INSERT INTO order_line VALUES (1, 1, 3001, 1, 1, 1);
   ```
   → Thấy cả `SELECT` lẫn `INSERT` ở Kết nối 3 **chạy xong tích xanh ngay lập tức (`0.00x sec`)**, không hề bị treo dây chuyền như MySQL!
4. Sang **Kết nối 1 (TiDB)** gõ `COMMIT;` và chạy để Kết nối 2 hoàn tất lệnh `ALTER TABLE`.
5. Quay lại **Kết nối 3 (TiDB)** *(giữ nguyên 2 dòng tích xanh `SELECT` và `INSERT` vừa chạy trong Action Output!)*, gõ thêm câu kiểm tra trạng thái Online DDL ngay bên dưới rồi bôi đen chạy riêng câu này:
   ```sql
   SELECT JOB_ID, TABLE_NAME, JOB_TYPE, SCHEMA_STATE, STATE
   FROM information_schema.DDL_JOBS
   WHERE DB_NAME = 'demo_ose' AND TABLE_NAME = 'order_line'
   ORDER BY JOB_ID DESC LIMIT 1;
   ```
6. **📸 THỜI ĐIỂM BẤM CHỤP `Hình D.8` (chụp màn hình Kết nối 3 của TiDB):**
   - **Vùng cần lấy:**
     - **SQL Editor (trên):** Hiện rõ 2 câu `SELECT` / `INSERT` thử tải đồng thời và câu truy vấn `information_schema.DDL_JOBS`.
     - **Result Grid (giữa):** Hiện công việc Online DDL của bảng `order_line` với `SCHEMA_STATE = public`, **`STATE = synced`**.
     - **Action Output (dưới):** Hiện các dòng tích xanh liên tiếp xác nhận `SELECT` (`1 row returned`) và `INSERT` (`1 row affected`) hoàn thành tức thì khi DDL đang chờ, tiếp nối bằng kết quả `DDL_JOBS`.
   - **Chú thích đặt dưới ảnh trong Phụ lục D:**
     > *Hình D.8. Kiểm chứng Online DDL trên TiDB v8.5.7: trong lúc lệnh `ALTER TABLE` chờ phiên đọc cũ kết thúc, các giao dịch `SELECT` và `INSERT` mới ở phiên độc lập vẫn hoàn thành tức thì (`0 s` đóng băng) và công việc DDL chốt ở trạng thái `STATE = synced`.*

---

### Kịch bản D4 — Linh hoạt lược đồ & `bulkWrite` có điều kiện trên MongoDB 8.0.20 (`Hình D.10`)

#### Bước dừng TiDB, bật MongoDB & mở Compass
1. Chạy trong PowerShell:
   ```powershell
   docker compose -f docker/compose.tidb.yml stop
   docker compose -f docker/compose.mongo.yml up -d
   ```
2. Mở **MongoDB Compass** → kết nối `mongodb://127.0.0.1:27018/?directConnection=true` → bấm mở thanh **`>_ MONGOSH`** ở mép dưới cửa sổ Compass, gõ `cls` để xóa sạch màn hình đen.

#### Thực hiện & chụp **Hình D.10** (Lấy cả khung Documents lẫn `mongosh` trong 1 tấm hình)
1. **Bước 1 (Tạo tài liệu cũ & chèn tài liệu mới không cần DDL):** Dán đoạn 1 vào `>_ MONGOSH` và bấm `Enter`:
   ```javascript
   db = db.getSiblingDB("demo_ose");
   db.item.drop(); db.order_line.drop();
   db.item.insertMany([{ i_id: 1, i_price: 6000 }, { i_id: 2, i_price: 3000 }]);
   db.order_line.insertMany([
     { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
     { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
   ]);
   db.order_line.insertOne({
     ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
     ol_discount: 1200, ol_mig_state: "MIGRATED"
   });
   db.order_line.createIndex({ ol_w_id: 1, ol_i_id: 1 }, { name: "idx_ol_w_i" });
   ```
2. Ở cột trái của **MongoDB Compass**, bấm nút **Refresh** cạnh `Databases` → mở **`demo_ose` → `order_line`** (chuyển sang chế độ xem **List** hoặc **Table** ở nửa trên màn hình): bạn sẽ thấy trực quan **2 tài liệu cũ `1001, 1002` (chưa có trường `ol_discount`)** nằm ngay cạnh **tài liệu mới `3001` (có sẵn `ol_discount: 1200, ol_mig_state: "MIGRATED"`)**! *(Đừng bấm Refresh nửa trên nữa để giữ nguyên hình ảnh 2 phiên bản lược đồ cùng tồn tại ở nửa trên màn hình)*.
3. **Bước 2 (Chạy `bulkWrite` chuyển đổi có điều kiện & in đối soát ở nửa dưới):** Gõ `cls` trong khung `>_ MONGOSH` ở nửa dưới cho gọn, rồi dán đoạn 2 và bấm `Enter`:
   ```javascript
   const prices = { 1: 6000, 2: 3000 };
   const calc = (q, id) => Math.floor(q * prices[id] * (prices[id] >= 5000 ? 10 : 5) / 100);
   const ops = db.order_line.find({ ol_mig_state: { $ne: "MIGRATED" } }).toArray().map(d => ({
     updateOne: {
       filter: { _id: d._id, ol_mig_state: { $ne: "MIGRATED" } },
       update: { $set: { ol_discount: calc(d.ol_quantity, d.ol_i_id), ol_mig_state: "MIGRATED" } }
     }
   }));
   db.order_line.bulkWrite(ops, { ordered: false, writeConcern: { w: "majority", j: true } });
   printjson({
     unmigrated: db.order_line.countDocuments({ ol_mig_state: { $ne: "MIGRATED" } }),
     docs: db.order_line.find({}, { _id: 0, ol_o_id: 1, ol_discount: 1, ol_mig_state: 1 }).toArray()
   });
   ```
4. **📸 THỜI ĐIỂM BẤM CHỤP `Hình D.10` (chụp toàn cửa sổ MongoDB Compass):**
   - **Vùng cần lấy:**
     - **Nửa trên (khung `Documents` của `demo_ose.order_line`):** Hiện trực quan các document cũ (thiếu `ol_discount`) và document mới `3001` (có `ol_discount: 1200`) cùng tồn tại trước khi backfill.
     - **Nửa dưới (khung `>_ MONGOSH`):** Hiện kết quả sau khi chạy `bulkWrite` với **`unmigrated: 0`** và danh sách `docs` cả 3 đơn (`1001, 1002, 3001`) đều đạt `ol_mig_state: 'MIGRATED'`, `ol_discount` lần lượt `1200, 450, 1200`!
   - **Chú thích đặt dưới ảnh trong Phụ lục D:**
     > *Hình D.10. Kiểm chứng trên MongoDB 8.0.20 (Compass & `mongosh`): tài liệu mới có sẵn `ol_discount` cùng tồn tại với tài liệu lịch sử mà không cần lệnh `ALTER TABLE` (khung trên); sau bước `bulkWrite` có điều kiện, toàn bộ tài liệu đạt trạng thái `MIGRATED` với `unmigrated = 0` (khung dưới).*

5. **Dọn dẹp sau khi chụp xong hết:**
   ```powershell
   docker compose -f docker/compose.mongo.yml stop
   ```

---

## Phần III. Nội dung gọn để Copy–Paste thẳng vào Phụ lục D (Mục D.5.3)

*(Dán nối tiếp ngay bên dưới **Mục D.5.2. Giới hạn của thực nghiệm Mục 2.6** trong báo cáo Word/Google Docs, và chèn 5 tấm ảnh `Hình D.6` – `Hình D.10` vừa chụp vào dưới bảng hoặc dưới từng ý tương ứng):*

### D.5.3. Kịch bản kiểm chứng trực quan cơ chế đổi lược đồ

Bên cạnh 159 lượt đo tự động dưới tải ở Mục D.2–D.4 (tái lập qua bộ script `scripts/run-2.4-*.sh` và `scripts/plot-2.4.py` tại `https://github.com/cuongpluss11/DBMS`), nhóm thực hiện bốn kịch bản kiểm chứng trực quan trên cơ sở dữ liệu độc lập `demo_ose` (Docker Compose cục bộ) nhằm quan sát trực tiếp ở mức câu lệnh các cơ chế khóa siêu dữ liệu, Online DDL, tính lũy đẳng và đối soát dữ liệu như tổng hợp tại **Bảng D.6**.

**Bảng D.6:** *Tổng hợp bốn kịch bản kiểm chứng trực quan cơ chế đổi lược đồ trên MySQL, TiDB và MongoDB.*

| Mã | Hệ DBMS & Thao tác thực hiện | Kết quả quan sát thực tế | Cơ chế được chứng minh & Minh chứng |
| :---: | --- | --- | --- |
| **D1** | **MySQL 8.4.8:** Mở 1 phiên đọc chưa `COMMIT`, phát `ALTER TABLE ... ALGORITHM=INSTANT` ở phiên 2, chạy `SELECT` ở phiên 3; lặp lại với `SET SESSION lock_wait_timeout = 3`. | Khi mặc định: `metadata_locks` ghi nhận `EXCLUSIVE (PENDING)` chặn dây chuyền cả `SELECT` mới (`SHARED_READ PENDING`). Khi đặt `timeout = 3`: `ALTER` tự thoát sau `3 s` (`Error 1205`), phiên `SELECT` đọc bình thường; khi phiên 1 `COMMIT`, lần thử lại hoàn tất tức thì. | Bẫy hàng đợi *Metadata Lock* trên MySQL và cơ chế giải phóng hàng đợi bằng `lock_wait_timeout` ngắn (**Hình D.6, Hình D.7**). |
| **D2** | **TiDB v8.5.7:** Mở 1 phiên đọc chưa `COMMIT`, phát `ALTER TABLE ... ADD COLUMN` ở phiên 2, đồng thời chạy `SELECT` và `INSERT` ở phiên 3. | Phiên 2 tự đợi phiên 1 kết thúc, nhưng phiên 3 vẫn đọc và chèn dòng mới thành công tức thì (`0 s` đóng băng); khi phiên 1 `COMMIT`, `DDL_JOBS` ghi nhận `STATE = synced`. | Cơ chế *Online DDL* đa phiên bản phối hợp với giao dịch đang mở mà không chặn giao dịch mới (**Hình D.8**). |
| **D3** | **MySQL / TiDB:** Chèn đơn mới (`MIGRATED`), chạy `UPDATE` có điều kiện cho đơn `1001` (*Lazy*, lặp 2 lần), quét dải khóa chính (*Batch*) và chạy SQL đối soát. | Đơn mới và đơn cũ cùng tồn tại hợp lệ; chạy lặp lần 2 trả về `0 rows affected`; bước *Batch* cập nhật đúng `2` đơn còn lại; truy vấn cuối xác nhận cả 4 dòng đạt `MIGRATED` và `invalid_rows = 0`. | Tính tương thích hai phiên bản, tính lũy đẳng (*idempotent*) của điều kiện `UNMIGRATED` và bảo toàn công thức chiết khấu (**Hình D.9**). |
| **D4** | **MongoDB 8.0.20:** Chèn tài liệu mới `3001` có sẵn `ol_discount` vào collection cũ, dựng chỉ mục phụ, chạy `bulkWrite` có điều kiện và kiểm đếm. | Tài liệu cũ (thiếu trường) và tài liệu mới cùng tồn tại không cần `ALTER`; sau `bulkWrite`, `unmigrated = 0` và cả 3 tài liệu khớp giá trị chiết khấu (`1200, 450, 1200`). | Tính linh hoạt của lược đồ BSON (*Flexible Schema*) và cập nhật bổ sung trường có điều kiện (**Hình D.10**; tác động dưới tải đồng thời đo tại Mục D.2–D.4). |
