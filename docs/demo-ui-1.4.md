# Hướng dẫn Chi tiết Thực hiện & Chuẩn hóa Minh chứng Demo Mục 1.4 (Theo Góp ý Giảng viên)

Tài liệu này hướng dẫn từng bước thực hiện trên **MongoDB Compass** và **MySQL Workbench** (kèm **TiDB Dashboard**) để hoàn thiện bộ minh chứng **Mục 1.4**, **Phụ lục A.8** và **Phụ lục B.8** đáp ứng trọn vẹn các yêu cầu phản biện học thuật của giảng viên.

- **Mã nguồn MongoDB (`.js`):** [`scripts/demo/demo_mongo_1.4.js`](../scripts/demo/demo_mongo_1.4.js)
- **Mã nguồn TiDB (`.sql`):** [`scripts/demo/demo_tidb_1.4.sql`](../scripts/demo/demo_tidb_1.4.sql)

---

## 0. Năm yêu cầu cốt lõi từ Giảng viên cần tuân thủ khi chụp ảnh & viết báo cáo

1. **Mỗi kịch bản demo phải trả lời rõ 3 câu hỏi:**
   - **(1) Thực hiện gì?** (Câu lệnh hoặc thao tác cụ thể trên UI).
   - **(2) Quan sát được gì?** (Kết quả trả về, **dữ liệu trước và sau thao tác**, trạng thái nút/khóa).
   - **(3) Chứng minh điều gì?** (Xác nhận đúng một chức năng hoặc cơ chế cụ thể của DBMS).
2. **Luôn hiển thị trạng thái dữ liệu cuối cùng:** Không chỉ chụp thông báo lệnh chạy thành công (`acknowledged: true`, `modifiedCount`, hay `Running...`), mà **phải chụp kèm truy vấn kiểm tra dữ liệu cuối cùng** (ví dụ: `s_quantity` từ `5 → 2 → 2`; đơn `9001` tồn tại sau `Commit` và `9002` biến mất sau `Abort`; tồn kho về đúng `3` sau khi 2 phiên tranh chấp khóa hoàn tất).
3. **Đổi tiêu đề cột trong Bảng A.8 & B.8:** Bỏ tiêu đề *"Kết quả kỳ vọng & Bằng chứng"* (gây nhầm lẫn giữa dự kiến và thực đo), tách thành **4 cột rõ ràng**: `STT` | `Chức năng & Thao tác thực hiện` | **`Kết quả quan sát thực tế`** | **`Minh chứng`**.
4. **Không kết luận vượt quá phạm vi bằng chứng (3 điểm kỹ thuật bắt buộc sửa câu chữ):**
   - **Với A5 (MongoDB Schema Evolution):** Hình chụp 2 document cũ/mới chỉ chứng minh **tính linh hoạt của lược đồ (Flexible Schema)** và khả năng cập nhật bổ sung trường; **không khẳng định** *"Backfill không chặn đọc/ghi"* chỉ từ ảnh tĩnh này (tác động đồng thời dưới tải được đo riêng ở Phần 2.6).
   - **Với B4 (TiDB Cấu hình & Region):** Biến `tidb_enable_1pc = ON` và `tidb_enable_async_commit = ON` chỉ chứng minh **hai tối ưu được bật ở mức cấu hình**, **không chứng minh** một giao dịch cụ thể đã dùng 1PC hay Async Commit. Đồng thời giải thích rõ bảng demo nhỏ (1 dòng) hiện nằm trong 1 Region trên 1 TiKV, còn khi nhiều Region dữ liệu sẽ phân phối giữa các nút TiKV.
   - **Với B5 (TiDB Online DDL):** Đổi mục tiêu thành ***"Kiểm chứng thao tác Online DDL và quan sát sự phối hợp với giao dịch đang mở"***. Mô tả trung thực việc Phiên `T2` (`ALTER TABLE`) chờ *Metadata Lock* khi Phiên `T1` giữ giao dịch chưa `COMMIT`, hoàn tất ngay khi `T1` `COMMIT`, và kiểm tra cả **cột mới trên bảng** lẫn `STATE = synced`.
5. **Bổ sung đủ bằng chứng cho các bước chưa có hình riêng:** Bổ sung ảnh/output thực tế cho **CRUD (A2, B1)**, **Conditional UPDATE trên TiDB (B2)**, kết quả **`EXPLAIN` (B4)** và **kết quả tồn kho cuối cùng sau khi nhả khóa ở B6**.

---

## Phần I. Hướng dẫn chi tiết 6 Demo MongoDB 8.0.20 trên **MongoDB Compass** (Phụ lục A.8)

### Bước chuẩn bị kết nối
```powershell
# Đảm bảo các hệ khác đang dừng, chỉ bật MongoDB:
docker compose -f docker/compose.tidb.yml stop
docker compose -f docker/compose.mysql.yml stop
docker compose -f docker/compose.mongo.yml up -d
```
- Mở **MongoDB Compass** → kết nối `mongodb://127.0.0.1:27018/?directConnection=true` → mở thanh **`>_ MONGOSH`** ở góc dưới. *(Gõ `cls` trước mỗi demo để màn hình đen gọn sạch khi chụp).*

---

### Demo A1 — Khởi tạo kết nối, phiên bản & Replica Set (**Hình A.1**)
- **Chạy trong `>_ MONGOSH`:**
  ```javascript
  db.version();
  rs.status().members.map(m => ({
    id: m._id, name: m.name, stateStr: m.stateStr, health: m.health
  }));
  ```
- **📸 Cách chụp Hình A.1:** Lấy cột trái `127.0.0.1:27018` và khung `mongosh` hiện rõ `8.0.20`, `stateStr: 'PRIMARY'`, `health: 1` *(crop bỏ khoảng đen thừa bên dưới)*.
- **Câu giải thích viết dưới Hình A.1:** *Xác nhận máy chủ chạy đúng phiên bản MongoDB 8.0.20 và Replica Set một nút `flashsale` đang hoạt động ở vai trò `PRIMARY` (`health: 1`), đủ điều kiện thực thi giao dịch nhiều tài liệu.*

---

### Demo A2 — CRUD cơ bản trên Document BSON (**Hình A.2 — Bổ sung mới theo góp ý GV**)
- **Gõ `cls` rồi chạy trong `>_ MONGOSH`:**
  ```javascript
  db = db.getSiblingDB("demo_flashsale");
  db.item.drop(); db.stock.drop(); db.orders.drop();

  // 1. CREATE
  db.item.insertOne({ i_id: 101, i_name: "Tai nghe Flash-Sale", i_price: 500000 });
  db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 });
  db.orders.insertOne({ o_id: 9000, o_i_id: 101, qty: 1, status: "TEST_CRUD" });

  // 2. READ (trước khi xóa đơn kiểm thử)
  db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 });
  db.orders.findOne({ o_id: 9000 }, { _id: 0 });

  // 3. DELETE & kiểm tra trạng thái sau xóa
  db.orders.deleteOne({ o_id: 9000 });
  db.orders.find().toArray();
  ```
- **📸 Cách chụp Hình A.2:** Chụp khung `mongosh` thấy đủ `acknowledged: true`, kết quả `findOne` trả về document `{ s_w_id: 1, s_i_id: 101, s_quantity: 5 }`, `deletedCount: 1` và mảng `orders` cuối cùng rỗng `[]`.
- **Câu giải thích viết dưới Hình A.2:** *Chứng minh khả năng khởi tạo, truy vấn theo bộ lọc và xóa tài liệu BSON trên các collection độc lập; dữ liệu nền `stock` (`s_quantity = 5`) sẵn sàng cho bước kiểm chứng tiếp theo.*

---

### Demo A3 — Cập nhật nguyên tử có điều kiện chống âm kho (**Hình A.3**)
- **Gõ `cls` rồi chạy trong `>_ MONGOSH` *(hiển thị đủ chuỗi trạng thái `5 → 2 → 2`)*:**
  ```javascript
  // 0. Tồn kho ban đầu (= 5)
  db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 });

  // 1. Mua 3 khi còn 5 -> thành công (modifiedCount: 1), tồn giảm còn 2
  db.stock.updateOne(
    { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
    { $inc: { s_quantity: -3 } }
  );
  db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 });

  // 2. Mua 4 khi chỉ còn 2 -> bị từ chối (modifiedCount: 0), tồn cuối cùng vẫn = 2
  db.stock.updateOne(
    { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 4 } },
    { $inc: { s_quantity: -4 } }
  );
  db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 });
  ```
- **📸 Cách chụp Hình A.3:** Lấy rõ cả 3 trạng thái `s_quantity: 5` → `modifiedCount: 1` (`s_quantity: 2`) → `modifiedCount: 0` (`s_quantity: 2`). *(Ảnh cũ của bạn đã có `modifiedCount: 1`, `0` và `s_quantity: 2` cuối cùng nên đã đạt yêu cầu; nếu chụp lại theo khối trên sẽ thấy rõ thêm mốc đầu `5`)*.
- **Câu giải thích viết dưới Hình A.3:** *Xác nhận tính nguyên tử ở cấp đơn tài liệu: điều kiện lọc `s_quantity >= qty` và phép giảm `$inc` được đánh giá trong cùng một thao tác, ngăn chặn phép trừ vượt tồn kho (`5 → 2 → 2`).*

---

### Demo A4 — Multi-document ACID Transaction: `Commit` & `Abort` (**Hình A.4 — Chụp rõ cả 2 trạng thái theo góp ý GV**)
- **Gõ `cls` rồi dán chạy trong `>_ MONGOSH`:**
  ```javascript
  // Phiên (a) COMMIT: Mua nốt 2 đơn vị (tồn 2 -> 0) và lưu đơn 9001
  const s1 = db.getMongo().startSession();
  s1.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority", j: true } });
  const d1 = s1.getDatabase("demo_flashsale");
  if (d1.stock.updateOne({ s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 2 } }, { $inc: { s_quantity: -2 } }).modifiedCount === 1) {
    d1.orders.insertOne({ o_id: 9001, o_i_id: 101, qty: 2, status: "COMMITTED" });
    s1.commitTransaction();
  }
  s1.endSession();
  print("1. SAU COMMIT:", tojson({ stock: db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }), orders: db.orders.find({}, { _id: 0 }).toArray() }));

  // Phiên (b) ABORT: Ghi đơn 9002 trước, trừ kho thất bại (tồn = 0) -> hủy giao dịch
  const s2 = db.getMongo().startSession();
  s2.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority", j: true } });
  const d2 = s2.getDatabase("demo_flashsale");
  d2.orders.insertOne({ o_id: 9002, o_i_id: 101, qty: 1, status: "SHOULD_ABORT" });
  if (d2.stock.updateOne({ s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 1 } }, { $inc: { s_quantity: -1 } }).modifiedCount === 0) {
    s2.abortTransaction();
  }
  s2.endSession();
  print("2. SAU ABORT:", tojson({ stock: db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }), orders: db.orders.find({}, { _id: 0 }).toArray() }));
  ```
- **📸 Cách chụp Hình A.4:** Chụp rõ 2 dòng kết quả `1. SAU COMMIT:` (thấy `s_quantity: 0` và đơn `9001` tồn tại) VÀ `2. SAU ABORT:` (thấy `s_quantity: 0` và mảng `orders` vẫn chỉ có đơn `9001`, đơn `9002` đã bị hủy sạch).
- **Câu giải thích viết dưới Hình A.4:** *Kiểm chứng Multi-document Transaction: giao dịch thành công lưu đơn hàng `9001` và cập nhật tồn kho về `0`; giao dịch bị hủy (`abortTransaction`) hoàn nguyên toàn bộ, không để lại đơn `9002` chưa commit.*

---

### Demo A5 — Schema Evolution: Linh hoạt lược đồ & Backfill (**Hình A.5**)
- **Chạy trong `>_ MONGOSH`:**
  ```javascript
  const dbOse = db.getSiblingDB("demo_ose");
  dbOse.order_line.drop();
  dbOse.order_line.insertMany([
    { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
    { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
  ]);
  dbOse.order_line.insertOne({
    ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
    ol_discount: 1200, ol_mig_state: "MIGRATED"
  });
  ```
- **📸 Chụp Hình A.5 (phần a - trước Backfill):** Bấm **Refresh** trên Compass → mở `demo_ose.order_line` để chụp 2 document cũ (thiếu `ol_discount`) và document mới (`3001` có `ol_discount: 1200`) cùng tồn tại *(ảnh bạn đã chụp rất đẹp)*. Sau đó chạy nốt lệnh backfill để ghi nhận kết quả thực tế vào bảng:
  ```javascript
  dbOse.order_line.updateMany(
    { ol_mig_state: { $ne: "MIGRATED" } },
    { $set: { ol_discount: 500, ol_mig_state: "MIGRATED" } }
  );
  dbOse.order_line.find({}, { _id: 0 }).toArray();
  ```
- **Câu giải thích viết dưới Hình A.5 *(sửa đúng lưu ý học thuật của GV)*:** *Chứng minh tính linh hoạt lược đồ (Flexible Schema) của MongoDB: tài liệu mới có thêm trường `ol_discount` được ghi trực tiếp và cùng tồn tại với tài liệu lịch sử mà không cần lệnh `ALTER TABLE` (ảnh hưởng của quá trình backfill đối với tải đồng thời được đánh giá riêng tại Mục 2.6).*

---

### Demo A6 — Giám sát WiredTiger Cache & Kết nối (**Hình A.6**)
- **Chạy trong `>_ MONGOSH` và mở tab `Performance`:**
  ```javascript
  ({
    wiredTigerCacheBytes: db.serverStatus().wiredTiger.cache["maximum bytes configured"],
    connections: db.serverStatus().connections,
    activeOpsCount: db.currentOp({ active: true }).inprog.length
  })
  ```
- **📸 Giữ nguyên ảnh trang 11–12 Phụ lục A hiện tại của bạn** *(chỉ cần sửa lỗi chính tả `WiredTige` → `WiredTiger` dưới chú thích ảnh)*.
- **Câu giải thích viết dưới Hình A.6:** *Xác nhận bộ nhớ đệm WiredTiger được giới hạn đúng `3.221.225.472` byte (`3 GiB`) và khả năng giám sát kết nối, hoạt động hệ thống theo thời gian thực.*

---

## Phần II. Hướng dẫn chi tiết 6 Demo TiDB v8.5.7 trên **MySQL Workbench** & **TiDB Dashboard** (Phụ lục B.8)

### Bước chuẩn bị kết nối
```powershell
docker compose -f docker/compose.mongo.yml stop
docker compose -f docker/compose.tidb.yml up -d
```
- Mở **TiDB Dashboard** tại `http://127.0.0.1:12379/dashboard` (`root`, mật khẩu trống).
- Mở **MySQL Workbench** → kết nối `TiDB_Local` (`127.0.0.1:14000`, `root`). Nhớ kiểm tra **Edit → Preferences → SQL Editor → `DBMS connection read time out = 300`**, và bật đủ 3 khung **SQL Editor + Result Grid + Action Output**.

---

### Demo B1 — Kết nối cụm 5 nút, phiên bản & CRUD cơ bản (**Hình B.4 & Hình B.5**)
1. **Hình B.4 (TiDB Dashboard):** Giữ nguyên ảnh `Cluster Info → Instances` hiện đủ `1 PD`, `1 TiDB`, `3 TiKV` `v8.5.7` (`Up`).
2. **Trên MySQL Workbench (chuột phải `Action Output → Clear`, dán và bấm `Ctrl + Shift + Enter`):**
   ```sql
   SET SQL_SAFE_UPDATES = 0;
   SELECT VERSION() AS tidb_version;

   CREATE DATABASE IF NOT EXISTS demo_flashsale;
   USE demo_flashsale;
   DROP TABLE IF EXISTS orders;
   DROP TABLE IF EXISTS stock;
   DROP TABLE IF EXISTS item;

   CREATE TABLE item (i_id INT PRIMARY KEY, i_name VARCHAR(64) NOT NULL, i_price INT NOT NULL);
   CREATE TABLE stock (s_w_id INT NOT NULL, s_i_id INT NOT NULL, s_quantity INT NOT NULL, PRIMARY KEY (s_w_id, s_i_id));
   CREATE TABLE orders (o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */, o_i_id INT NOT NULL, qty INT NOT NULL, status VARCHAR(20) NOT NULL);

   INSERT INTO item VALUES (101, 'Tai nghe Flash-Sale', 500000);
   INSERT INTO stock VALUES (1, 101, 5);
   INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'TEST_CRUD');

   SELECT * FROM orders; -- Xem đơn TEST_CRUD có khóa o_id ngẫu nhiên 64-bit
   DELETE FROM orders WHERE status = 'TEST_CRUD';
   SELECT (SELECT VERSION()) AS tidb_version,
          (SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 101) AS init_stock,
          (SELECT COUNT(*) FROM orders) AS orders_after_delete;
   ```
- **📸 Cách chụp Hình B.5 *(nâng cấp hơn ảnh `SELECT VERSION()` đơn lẻ cũ)*:** Chụp màn hình kết quả câu cuối cùng hiển thị đồng thời trên 1 bảng: `tidb_version = 8.0.11-TiDB-v8.5.7`, `init_stock = 5`, `orders_after_delete = 0`, kèm log `INSERT / SELECT / DELETE` tích xanh ở **Action Output** — chứng minh gọn cả **Version + CRUD** chỉ trong 1 tấm hình!

---

### Demo B2 — Cập nhật tồn kho có điều kiện chống âm kho (**Hình B.6 — Bổ sung hình riêng theo góp ý GV**)
- Mở tab SQL trắng mới (`Ctrl + T`), chuột phải `Action Output → Clear`, dán và bấm **`Ctrl + Shift + Enter`**:
  ```sql
  USE demo_flashsale;

  -- Lần (a): Mua 3 khi kho còn 5 -> 1 row(s) affected, tồn giảm còn 2
  UPDATE stock
  SET s_quantity = s_quantity - 3
  WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;

  -- Lần (b): Mua 4 khi kho chỉ còn 2 -> 0 row(s) affected, bị từ chối
  UPDATE stock
  SET s_quantity = s_quantity - 4
  WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

  -- Kiểm tra trạng thái tồn kho cuối cùng (s_quantity = 2 >= 0)
  SELECT s_w_id, s_i_id, s_quantity AS final_s_quantity
  FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
  ```
- **📸 Cách chụp Hình B.6 (MỚI):**
  - **SQL Editor (trên):** Hiện 2 câu `UPDATE` (`>= 3` và `>= 4`) + câu `SELECT` cuối.
  - **Result Grid (giữa):** Hiện `final_s_quantity = 2`.
  - **Action Output (dưới):** Dòng 1 báo **`1 row(s) affected`**, dòng 2 báo **`0 row(s) affected`**!
- **Câu giải thích viết dưới Hình B.6:** *Kiểm chứng cập nhật có điều kiện trên TiDB: yêu cầu mua 3 thành công (`1 row affected`, tồn còn `2`), yêu cầu mua tiếp 4 không thỏa điều kiện `s_quantity >= 4` nên không có dòng nào bị sửa (`0 rows affected`), bảo toàn tồn kho không âm.*

---

### Demo B3 — Giao dịch ACID: `COMMIT` & `ROLLBACK` (**Hình B.7**)
- Bạn có thể **giữ nguyên ảnh dưới trang 17 hiện tại** (đã rất tốt: thấy rõ đơn `'COMMITTED'` với `o_id` `AUTO_RANDOM`, `ROW_COUNT()`, `ROLLBACK` và không có `'SHOULD_ROLLBACK'`), hoặc chạy khối trong [`demo_tidb_1.4.sql`](../scripts/demo/demo_tidb_1.4.sql) nếu muốn chụp kèm cả cột `s_quantity = 0`.
- **Câu giải thích viết dưới Hình B.7:** *Kiểm chứng tính nguyên tử của giao dịch trên TiDB: giao dịch đủ hàng (`COMMIT`) lưu bền vững đơn `'COMMITTED'` với khóa `AUTO_RANDOM`; giao dịch phát hiện hết hàng (`ROW_COUNT() = 0` → `ROLLBACK`) hoàn nguyên hoàn toàn bản ghi `'SHOULD_ROLLBACK'`.*

---

### Demo B4 — Cấu hình giao dịch, `EXPLAIN` & Phân bố Region (**Hình B.8**)
- Để thấy **cả kết quả `EXPLAIN` (`Point_Get_1`) lẫn `REGION_ID / LEADER_STORE_ID`**, trên MySQL Workbench bạn có thể giữ nguyên ảnh Region hiện tại và bổ sung thêm 1 khung nhỏ chụp Result Grid của `EXPLAIN SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;` (trả về `id = Point_Get_1`, `access object = table:stock, clustered index:PRIMARY(s_w_id, s_i_id)`).
- **Câu giải thích viết dưới Hình B.8 *(sửa đúng lưu ý kỹ thuật số 2 của GV)*:** *Quan sát kế hoạch thực thi và định tuyến dữ liệu trên TiDB: truy vấn tồn kho đi trực tiếp qua khóa chính cụm (`Point_Get` trên `PRIMARY`), và bảng `stock` được ánh xạ vào Region (`REGION_ID = 2012`, `LEADER_STORE_ID = 4`). Các biến `tidb_enable_1pc = ON` và `tidb_enable_async_commit = ON` xác nhận hai tối ưu chốt giao dịch được bật ở mức cấu hình cụm (không khẳng định một giao dịch đơn lẻ đã thực thi theo 1PC/Async Commit).*

---

### Demo B5 — Kiểm chứng Online DDL & sự phối hợp Metadata Lock (**Hình B.9 — Sửa diễn giải theo lưu ý kỹ thuật số 1 của GV**)
- **Ảnh chụp:** Ảnh dưới trang 18 hiện tại của bạn (`ALTER TABLE ... 14.297 sec` + `DDL_JOBS` hiện `STATE = synced` trên 2 tab kết nối) **khớp chính xác 100%** với hiện tượng kỹ thuật mà giảng viên chỉ ra! Nếu muốn đầy đủ hơn nữa theo bước 5 của giảng viên, bạn chỉ cần chạy thêm `SELECT * FROM demo_ose.order_line;` ngay bên dưới để thấy rõ 2 cột mới `ol_discount = NULL` và `ol_mig_state = 'UNMIGRATED'` đã xuất hiện trên bảng.
- **Câu giải thích viết dưới Hình B.9 *(viết đúng bản chất Metadata Lock)*:** *Kiểm chứng thao tác Online DDL và sự phối hợp Metadata Lock trên TiDB: khi Phiên `T1` đang giữ giao dịch đọc mở trên `order_line`, lệnh `ALTER TABLE ... ADD COLUMN` ở Phiên `T2` tạm chờ phối hợp phiên bản lược đồ (`14,3 s` trong lần chạy) và hoàn tất chuyển sang trạng thái `STATE = synced` ngay sau khi `T1` `COMMIT`, bổ sung thành công hai cột mới mà không làm hỏng giao dịch đang mở.*

---

### Demo B6 — Kiểm soát tranh chấp ghi bằng Pessimistic Lock (**Hình B.10 — Bổ sung trạng thái dữ liệu cuối `s_quantity = 3`**)
- Giảng viên lưu ý ở B6: ***"T2 chờ T1, sau đó hoàn tất"*** và ***"cần chụp hoặc xuất cả trạng thái dữ liệu cuối cùng"***.
- Ngoài ảnh chụp khoảnh khắc `T2` đang `Running...` (trang 19 hiện tại), bạn thực hiện nốt bước chốt để chụp (hoặc ghép ngay bên dưới) **kết quả sau khi cả 2 phiên hoàn tất**:
  1. Ở **Kết nối `T1`**: chạy `COMMIT;` → lập tức ở **Kết nối `T2`** dòng `UPDATE` chuyển từ `Running...` sang tích xanh **`1 row(s) affected`**!
  2. Ở **Kết nối `T2`**: gõ thêm 2 dòng dưới câu `UPDATE` rồi bôi đen chạy 2 dòng đó:
     ```sql
     COMMIT;
     SELECT s_w_id, s_i_id, s_quantity AS final_stock_after_2_txns
     FROM demo_flashsale.stock WHERE s_w_id = 1 AND s_i_id = 101;
     ```
  3. **📸 Chụp màn hình Kết nối `T2` sau khi hoàn tất:**
     - **Action Output (dưới):** Thấy đủ 3 tích xanh liên tiếp: `BEGIN` → `UPDATE ... 1 row(s) affected` *(có thời gian chờ `Duration` vài giây lúc đợi T1!)* → `COMMIT`.
     - **Result Grid (giữa):** Hiện rõ **`final_stock_after_2_txns = 3`** (`5 - 1 - 1 = 3`)!
- **Câu giải thích viết dưới Hình B.10:** *Kiểm chứng khóa bi quan (`pessimistic`) trên TiDB: Phiên `T2` phải chờ khóa (`Running...`) khi Phiên `T1` chưa chốt (trên); ngay sau khi `T1` `COMMIT`, `T2` tiếp tục thực thi trên giá trị mới và cập nhật tồn kho chính xác từ `5` về `3`, ngăn chặn hiện tượng mất cập nhật (dưới).*

---

## Phần III. Bản hoàn thiện Bảng A.8 & Bảng B.8 theo mẫu 4 cột của Giảng viên *(Copy-paste vào Word)*

### 1. Bảng A.8 (Phụ lục A — Đã đổi sang kết quả thực tế & bỏ khẳng định quá phạm vi ở STT 5)

| STT | Chức năng & Thao tác thực hiện | Kết quả quan sát thực tế | Minh chứng |
| :-: | :--- | :--- | :--- |
| 1 | **Kết nối DBMS & Replica Set:** Bật `compose.mongo.yml`; kết nối Compass (`:27018`, `directConnection=true`); chạy `db.version()` và `rs.status()`. | Máy chủ trả về phiên bản `8.0.20`; nút `mongo:27017` thuộc Replica Set `flashsale` ở trạng thái `stateStr: "PRIMARY"`, `health: 1`. | Hình A.1, `demo_mongo_1.4.js` |
| 2 | **CRUD Document BSON:** Trên `demo_flashsale`, thực hiện `insertOne` (`item`, `stock` tồn `5`, đơn nháp `9000`), `findOne` và `deleteOne` đơn nháp. | Ba lệnh chèn trả về `acknowledged: true`; `findOne` hiển thị đúng tài liệu BSON (`s_quantity: 5`); `deleteOne` trả về `deletedCount: 1`, `orders` rỗng `[]`. | Hình A.2 (hoặc Output A2), `demo_mongo_1.4.js` |
| 3 | **Cập nhật nguyên tử có điều kiện:** Chạy `updateOne` kèm điều kiện `s_quantity: { $gte: qty }` và `$inc`: (a) mua `3` khi tồn `5`; (b) mua `4` khi tồn `2`. | Chuỗi tồn kho thực tế `5 → 2 → 2`: lần (a) trả về `modifiedCount: 1` (`s_quantity` còn `2`); lần (b) trả về `modifiedCount: 0`, `findOne` xác nhận tồn kho giữ nguyên `2`. | Hình A.3, `demo_mongo_1.4.js` |
| 4 | **Multi-document Transaction:** Mở session (`snapshot`, `w: "majority", j: true`): (a) trừ `2` tồn kho + chèn đơn `9001` → `commitTransaction()`; (b) chèn đơn `9002` + trừ kho khi tồn `= 0` → `abortTransaction()`. | Sau `Commit`: `s_quantity = 0` và `orders` lưu đơn `9001`. Sau `Abort`: `s_quantity` vẫn bằng `0` và `orders` chỉ còn đơn `9001` (đơn `9002` bị hoàn nguyên hoàn toàn). | Hình A.4, `demo_mongo_1.4.js` |
| 5 | **Schema Evolution (Linh hoạt lược đồ):** Trên `demo_ose.order_line` có sẵn 2 tài liệu cũ thiếu `ol_discount`, chèn tài liệu `3001` có `ol_discount: 1200` (`MIGRATED`), sau đó chạy `updateMany` backfill. | Tài liệu mới được ghi trực tiếp không cần `ALTER TABLE`, hiển thị song song cùng 2 tài liệu cấu trúc cũ trên Compass; lệnh `updateMany` cập nhật nốt `modifiedCount: 2` tài liệu cũ sang `MIGRATED`. | Hình A.5, `demo_mongo_1.4.js` |
| 6 | **Giám sát vận hành:** Truy vấn `serverStatus().wiredTiger.cache`, `connections`, `currentOp` và mở tab **Performance** trên Compass. | Tham số `wiredTigerCacheBytes` ghi nhận đúng `3221225472` byte (`3 GiB`); hiển thị số kết nối hiện hành (`current`, `available`) và biểu đồ tải thời gian thực. | Hình A.6, `demo_mongo_1.4.js` |

---

### 2. Bảng B.8 (Phụ lục B — Đã sửa chuẩn kỹ thuật B4, B5, B6 & đổi sang kết quả thực tế)

| STT | Chức năng & Thao tác thực hiện | Kết quả quan sát thực tế | Minh chứng |
| :-: | :--- | :--- | :--- |
| 1 | **Kết nối cụm & CRUD cơ bản:** Bật cụm `compose.tidb.yml`; kiểm tra TiDB Dashboard (`:12379`), chạy `SELECT VERSION()`, tạo bảng (`orders` dùng `AUTO_RANDOM`) và thực thi `INSERT / SELECT / DELETE`. | Dashboard xác nhận đủ 5 nút (`1 PD`, `1 TiDB`, `3 TiKV` nhánh `v8.5.7`) trạng thái `Up`; Workbench trả về `8.0.11-TiDB-v8.5.7`; đơn kiểm thử sinh khóa `o_id` 64-bit ngẫu nhiên, xóa thành công và giữ `stock = 5`. | Hình B.4, Hình B.5, `demo_tidb_1.4.sql` |
| 2 | **Cập nhật tồn kho có điều kiện:** Thực thi `UPDATE stock SET s_quantity = s_quantity - qty WHERE ... AND s_quantity >= qty`: (a) mua `3` khi còn `5`; (b) mua `4` khi còn `2`, rồi `SELECT s_quantity`. | Lần (a) ghi nhận `1 row(s) affected`, tồn kho giảm từ `5` xuống `2`. Lần (b) ghi nhận `0 row(s) affected`, truy vấn cuối xác nhận `s_quantity = 2` (không bị trừ dưới `0`). | Hình B.6, `demo_tidb_1.4.sql` |
| 3 | **Giao dịch ACID (`COMMIT` & `ROLLBACK`):** Phiên (a) trừ `2` tồn kho + chèn đơn `'COMMITTED'` → `COMMIT`; Phiên (b) chèn `'SHOULD_ROLLBACK'` + trừ kho khi tồn `= 0` (`ROW_COUNT() = 0`) → `ROLLBACK`. | Sau `COMMIT`: tồn kho về `0`, lưu đơn `'COMMITTED'`. Sau `ROLLBACK`: `ROW_COUNT()` trả về `0`, truy vấn `SELECT * FROM orders` xác nhận chỉ tồn tại đơn `'COMMITTED'`, đơn `'SHOULD_ROLLBACK'` bị hủy bỏ. | Hình B.7, `demo_tidb_1.4.sql` |
| 4 | **Cấu hình, `EXPLAIN` & Region:** Truy vấn `CLUSTER_INFO`, `CLUSTER_CONFIG`, `SHOW VARIABLES`, `EXPLAIN SELECT` trên `stock` và `TIKV_REGION_STATUS` / `TIKV_REGION_PEERS`. | Cấu hình đang bật `pessimistic`, `tidb_enable_1pc = ON`, `tidb_enable_async_commit = ON` và `max-replicas = 1` (xác nhận mức cấu hình); `EXPLAIN` dùng `Point_Get` trên `PRIMARY`; bảng `stock` (1 dòng) nằm tại `REGION_ID = 2012`, `LEADER_STORE_ID = 4`. | Hình B.8, `demo_tidb_1.4.sql` |
| 5 | **Online DDL & phối hợp giao dịch mở:** Phiên `T1` mở `BEGIN; SELECT * FROM order_line;`; Phiên `T2` chạy `ALTER TABLE ... ADD COLUMN ol_discount, ol_mig_state`; sau đó `COMMIT` `T1` và kiểm tra `DDL_JOBS` + bảng. | Khi `T1` chưa chốt, `ALTER TABLE` ở `T2` chờ phối hợp *Metadata Lock*; ngay khi `T1` `COMMIT`, lệnh DDL hoàn tất (`14,3 s`), `DDL_JOBS` ghi nhận `STATE = synced` và bảng `order_line` có đủ 2 cột mới. | Hình B.9, `demo_tidb_1.4.sql` |
| 6 | **Khóa bi quan (`Pessimistic Lock`):** Khởi tạo `s_quantity = 5`; mở 2 phiên độc lập cùng chạy `BEGIN; UPDATE stock SET s_quantity = s_quantity - 1 ...`: `T1` giữ khóa, `T2` chạy sau, rồi lần lượt `COMMIT` cả hai. | Khi `T1` chưa `COMMIT`, `T2` chuyển sang chờ khóa (`Running...`); ngay khi `T1` `COMMIT`, `T2` hoàn tất (`1 row affected`). Truy vấn cuối sau khi `T2` `COMMIT` xác nhận `s_quantity = 3` (`5 → 3`, không mất cập nhật). | Hình B.10, `demo_tidb_1.4.sql` |

---

## Phần IV. Dọn dẹp an toàn sau khi chụp xong

```powershell
docker compose -f docker/compose.tidb.yml stop
docker compose -f docker/compose.mongo.yml stop
docker compose -f docker/compose.mysql.yml stop
```
