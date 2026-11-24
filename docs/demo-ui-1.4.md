# Hướng dẫn Kết nối UI & Kịch bản Demo Mục 1.4 (MongoDB & TiDB)

Tài liệu này hướng dẫn từng bước **khởi động, kết nối bằng giao diện trực quan (UI)** và **chạy kịch bản demo** phục vụ **Mục 1.4 (Cài đặt, cấu hình và minh họa vận hành)** trong báo cáo bài tập lớn Nhóm 16:
- **1.4.1 & 1.4.2:** Kết nối bằng **MongoDB Compass**, **DBeaver / MySQL Workbench** và **TiDB Dashboard** (chụp **Hình 4.1**, **Hình 4.2**).
- **1.4.3:** Minh họa CRUD, cập nhật tồn kho có điều kiện (chống âm kho / oversell), và giao dịch nguyên tử nhiều thao tác (**COMMIT** & **ROLLBACK/ABORT**).
- **1.4.4:** Giám sát và kiểm tra trạng thái vận hành (Replica Set, WiredTiger cache, cụm PD/TiDB/3 TiKV, phân bố Region).

> **Nguyên tắc vận hành:** Chỉ chạy **một DBMS tại một thời điểm** (`docker compose stop` hệ cũ trước khi bật hệ mới). Toàn bộ kịch bản dưới đây tạo database riêng `demo_flashsale` nên **không làm thay đổi dữ liệu benchmark TPC-C** của nhóm.

---

## 1. Chuẩn bị trên máy cá nhân (Windows + Docker Desktop)

1. Mở **Docker Desktop** và đợi báo **Engine running**.
2. Mở PowerShell tại thư mục repo `e:\BTL-DBMS`.
3. Cài sẵn công cụ UI tương ứng (chỉ dùng **Docker Compose local**, kết nối thẳng qua `127.0.0.1`):

| Hệ DBMS | Công cụ UI sử dụng | Địa chỉ kết nối (Docker local) |
| --- | --- | --- |
| **MongoDB 8.0.20** | **MongoDB Compass** *(có sẵn tab `>_ MONGOSH` tích hợp)* | `mongodb://127.0.0.1:27018/?directConnection=true` |
| **TiDB 8.5.7** | **DBeaver Community** *(hoặc MySQL Workbench)* | `127.0.0.1:14000` *(user: `root`, mật khẩu trống)* |
| **TiDB 8.5.7** | **TiDB Dashboard** *(mở trực tiếp trên trình duyệt web)* | `http://127.0.0.1:12379/dashboard` *(user: `root`, mật khẩu trống)* |

---

## 2. Kịch bản Demo MongoDB 8.0.20 trên **MongoDB Compass**

### Bước 2.1: Khởi động MongoDB và kết nối Compass (**Hình 4.1**)
1. Khởi động container MongoDB (replica set 1 nút `flashsale`, cache WiredTiger 3 GiB):
   ```bash
   docker compose -f docker/compose.mongo.yml up -d
   docker compose -f docker/compose.mongo.yml ps
   ```
   *(Đợi cột `STATUS` báo `Up (healthy)`.)*
2. Mở **MongoDB Compass** → bấm **New Connection** → dán chính xác chuỗi kết nối:
   ```text
   mongodb://127.0.0.1:27018/?directConnection=true
   ```
   > **Lưu ý:** Bắt buộc phải có `?directConnection=true` vì Replica Set trong Docker khai báo hostname nội bộ `mongo:27017`; nếu bỏ tham số này Compass sẽ không phân giải được tên máy chủ `mongo`.
3. Bấm **Save & Connect**.
4. **Chụp Hình 4.1:** Màn hình Compass đang kết nối `127.0.0.1:27018`, hiển thị danh sách database bên trái và các collection/document BSON ở khung chính.

---

### Bước 2.2: Kịch bản 1.4.3 — CRUD, Cập nhật tồn kho có điều kiện & Giao dịch ACID (chạy trong `>_ MONGOSH`)
Bấm vào thanh **`>_ MONGOSH`** ở góc dưới bên trái cửa sổ MongoDB Compass, dán và chạy lần lượt từng khối:

#### (a) Khởi tạo & CRUD cơ bản (Create / Read / Update)
```javascript
use demo_flashsale;

// Dọn sạch nếu chạy lại demo nhiều lần
db.item.drop();
db.stock.drop();
db.orders.drop();

// CREATE: Thêm sản phẩm Flash-sale và bản ghi tồn kho ban đầu (s_quantity = 5)
db.item.insertOne({ i_id: 101, i_name: "Tai nghe Flash-Sale", i_price: 500000 });
db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 });

// READ: Kiểm tra dữ liệu vừa tạo
db.item.findOne({ i_id: 101 });
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });
```

#### (b) Cập nhật tồn kho có điều kiện (Chống âm kho / Oversell)
```javascript
// Trường hợp 1: Đủ hàng (5 >= 3) -> thành công (modifiedCount: 1), tồn kho giảm còn 2
db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
  { $inc: { s_quantity: -3 } }
);

// Trường hợp 2: Thiếu hàng (2 < 4) -> bị từ chối (modifiedCount: 0), tồn kho KHÔNG bị âm
db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 4 } },
  { $inc: { s_quantity: -4 } }
);

// Xác nhận tồn kho vẫn là 2 (>= 0)
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });
```

#### (c) Giao dịch nhiều tài liệu (Multi-document ACID Transaction) — COMMIT & ABORT
```javascript
// MongoDB yêu cầu collection orders tồn tại trước khi mở multi-document transaction
db.createCollection("orders");

// --- Kịch bản COMMIT: Mua 2 sản phẩm (đủ hàng: 2 >= 2) -> trừ kho về 0 & ghi đơn 9001 ---
const s1 = db.getMongo().startSession();
s1.startTransaction({
  readConcern: { level: "snapshot" },
  writeConcern: { w: "majority", j: true }
});
const d1 = s1.getDatabase("demo_flashsale");
const res1 = d1.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 2 } },
  { $inc: { s_quantity: -2 } }
);
if (res1.modifiedCount === 1) {
  d1.orders.insertOne({ o_id: 9001, o_i_id: 101, qty: 2, status: "COMMITTED" });
  s1.commitTransaction();
  print("==> COMMIT thành công: đã trừ kho và tạo đơn 9001.");
} else {
  s1.abortTransaction();
}
s1.endSession();

// Quan sát sau COMMIT: stock.s_quantity = 0 và có đơn 9001
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });
db.orders.find().toArray();
```

```javascript
// --- Kịch bản ABORT / ROLLBACK: Ghi trước đơn 9002 rồi trừ kho thất bại (tồn = 0) -> hủy cả giao dịch ---
const s2 = db.getMongo().startSession();
s2.startTransaction({
  readConcern: { level: "snapshot" },
  writeConcern: { w: "majority", j: true }
});
const d2 = s2.getDatabase("demo_flashsale");
d2.orders.insertOne({ o_id: 9002, o_i_id: 101, qty: 1, status: "SHOULD_ABORT" });
const res2 = d2.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 1 } },
  { $inc: { s_quantity: -1 } }
);
if (res2.modifiedCount === 0) {
  s2.abortTransaction();
  print("==> Hết hàng -> ABORT giao dịch! Đơn 9002 đã bị hoàn nguyên.");
}
s2.endSession();

// Quan sát sau ABORT: chỉ còn đơn 9001, đơn 9002 KHÔNG tồn tại (đảm bảo tính nguyên tử ACID)
db.orders.find().toArray();
```

#### (d) DELETE (hoàn tất đủ 4 thao tác CRUD)
```javascript
db.orders.deleteOne({ o_id: 9001 });
db.orders.find().toArray(); // []
```
*(Bấm nút **Refresh** trên giao diện Compass để thấy collection `item`, `stock`, `orders` cập nhật trực quan.)*

---

### Bước 2.3: Kịch bản 1.4.4 — Giám sát & kiểm tra trạng thái vận hành MongoDB
Chạy trong **`>_ MONGOSH`** và mở thêm tab **Performance** trên Compass để chụp ảnh:
```javascript
// 1. Kiểm tra trạng thái Replica Set (bắt buộc để chạy Multi-document Transaction)
rs.status().members.map(m => ({ name: m.name, stateStr: m.stateStr, health: m.health }));

// 2. Kiểm tra số kết nối và dung lượng bộ nhớ đệm WiredTiger (3 GiB)
db.serverStatus().connections;
db.serverStatus().wiredTiger.cache["maximum bytes configured"];

// 3. Kiểm tra các thao tác đang chạy (tương đương bảng khóa)
db.currentOp({ active: true }).inprog.length;
```

---

## 3. Kịch bản Demo TiDB 8.5.7 trên **DBeaver** và **TiDB Dashboard**

### Bước 3.1: Dừng MongoDB, bật TiDB & kết nối UI (**Hình 4.2**)
1. Dừng MongoDB và khởi động cụm TiDB (**1 PD + 1 TiDB Server + 3 TiKV**):
   ```bash
   docker compose -f docker/compose.mongo.yml stop
   docker compose -f docker/compose.tidb.yml up -d
   docker compose -f docker/compose.tidb.yml ps
   ```
   *(Đợi ~15–20 giây để 3 TiKV đăng ký đầy đủ với PD.)*

2. **Mở TiDB Dashboard (Web UI — chụp Hình 4.2):**
   - Truy cập trên trình duyệt: **`http://127.0.0.1:12379/dashboard`**
   - Đăng nhập: Username **`root`**, Password *(để trống)* → bấm **Sign In**.
   - Vào **Cluster Info → Instances** để chụp **Hình 4.2** (hiển thị đầy đủ 5 nút: `1 PD`, `1 TiDB`, `3 TiKV` đều `Up`).
   - Có thể chụp thêm mục **SQL Statements** và **Key Visualizer** cho phần **1.4.4**.

3. **Kết nối SQL Client (DBeaver Community hoặc MySQL Workbench):**
   - Mở **DBeaver** → **Database → New Database Connection** → chọn **TiDB** (hoặc **MySQL**):
     - **Server Host:** `127.0.0.1`
     - **Port:** `14000`
     - **Database:** *(để trống)*
     - **Username:** `root`
     - **Password:** *(để trống)*
   - Bấm **Test Connection** → thấy `Connected` → bấm **Finish** → chuột phải vào kết nối chọn **SQL Editor → New SQL Script**.

---

### Bước 3.2: Kịch bản 1.4.3 — CRUD, Cập nhật có điều kiện & Giao dịch ACID phân tán
Dán và chạy từng khối trong **SQL Editor** của DBeaver (dùng phím `Ctrl + Enter` cho từng câu hoặc bôi đen cả khối rồi bấm `Alt + X`):

#### (a) Khởi tạo bảng & CRUD cơ bản (Create / Read)
```sql
CREATE DATABASE IF NOT EXISTS demo_flashsale;
USE demo_flashsale;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS stock;
DROP TABLE IF EXISTS item;

CREATE TABLE item (
  i_id INT PRIMARY KEY,
  i_name VARCHAR(64) NOT NULL,
  i_price INT NOT NULL
);

CREATE TABLE stock (
  s_w_id INT NOT NULL,
  s_i_id INT NOT NULL,
  s_quantity INT NOT NULL,
  PRIMARY KEY (s_w_id, s_i_id)
);

-- Dùng AUTO_RANDOM của TiDB (bọc trong /*T![auto_rand] ... */ để MySQL Workbench không báo gạch đỏ)
CREATE TABLE orders (
  o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */,
  o_i_id INT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(16) NOT NULL
);

-- CREATE & READ
INSERT INTO item (i_id, i_name, i_price) VALUES (101, 'Tai nghe Flash-Sale', 500000);
INSERT INTO stock (s_w_id, s_i_id, s_quantity) VALUES (1, 101, 5);

SELECT * FROM item;
SELECT * FROM stock;
```

#### (b) Cập nhật tồn kho có điều kiện (Chống âm kho / Oversell)
```sql
-- Trường hợp 1: Đủ hàng (5 >= 3) -> Updated Rows = 1, tồn kho giảm còn 2
UPDATE stock
SET s_quantity = s_quantity - 3
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;

-- Trường hợp 2: Thiếu hàng (2 < 4) -> Updated Rows = 0, tồn kho giữ nguyên 2 (không âm)
UPDATE stock
SET s_quantity = s_quantity - 4
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
```

#### (c) Giao dịch ACID phân tán — COMMIT & ROLLBACK
```sql
-- --- Kịch bản COMMIT: Mua 2 cái cuối cùng (tồn 2 -> 0) và tạo đơn hàng ---
BEGIN;
UPDATE stock
SET s_quantity = s_quantity - 2
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 2;

INSERT INTO orders (o_i_id, qty, status) VALUES (101, 2, 'COMMITTED');
COMMIT;

-- Quan sát sau COMMIT: tồn kho = 0, bảng orders có 1 đơn (o_id sinh ngẫu nhiên bởi AUTO_RANDOM)
SELECT * FROM stock;
SELECT * FROM orders;
```

```sql
-- --- Kịch bản ROLLBACK: Ghi đơn tạm rồi trừ kho thất bại (tồn = 0) -> hoàn nguyên toàn bộ ---
BEGIN;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'SHOULD_ROLLBACK');

UPDATE stock
SET s_quantity = s_quantity - 1
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;
-- Quan sát thấy Updated Rows = 0 (hết hàng) -> hủy giao dịch:
ROLLBACK;

-- Quan sát sau ROLLBACK: bản ghi 'SHOULD_ROLLBACK' KHÔNG tồn tại trong bảng orders
SELECT * FROM orders;
```

#### (d) DELETE (hoàn tất đủ 4 thao tác CRUD)
```sql
DELETE FROM orders WHERE status = 'COMMITTED';
SELECT * FROM orders;
```

---

### Bước 3.3: Kịch bản 1.4.4 — Giám sát & kiểm tra trạng thái vận hành TiDB
Chạy trên **DBeaver** (kết hợp chụp **TiDB Dashboard** tại `http://127.0.0.1:12379/dashboard`):
```sql
-- 1. Kiểm tra tất cả các thành phần trong cụm (1 PD, 1 TiDB Server, 3 TiKV)
SELECT TYPE, INSTANCE, STATUS_ADDRESS, VERSION
FROM information_schema.CLUSTER_INFO
ORDER BY TYPE, INSTANCE;

-- 2. Kiểm tra chế độ giao dịch mặc định (pessimistic) và tối ưu bước chốt (async commit / 1PC)
SHOW VARIABLES WHERE Variable_name IN (
  'tidb_txn_mode', 'tidb_enable_async_commit', 'tidb_enable_1pc'
);

-- 3. Xem phân bố Region của bảng stock trên các nút TiKV
SHOW TABLE stock REGIONS;

-- 4. Xem kế hoạch thực thi thực tế (EXPLAIN ANALYZE)
EXPLAIN ANALYZE SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
```

---

## 4. Checklist ảnh chụp cần đưa vào Mục 1.4 của Báo cáo

| Hình trong báo cáo | Nguồn chụp | Nội dung cần hiện rõ trên ảnh |
| --- | --- | --- |
| **Hình 4.1** *(Mục 1.4.2)* | **MongoDB Compass** | Chuỗi kết nối `127.0.0.1:27018`, danh sách collection (`item`, `stock`, `orders`) và dữ liệu document BSON. |
| **Hình 4.2** *(Mục 1.4.2 & 1.4.4)* | **TiDB Dashboard** (`127.0.0.1:12379/dashboard`) | Mục **Cluster Info → Instances** hiển thị đủ `1 PD`, `1 TiDB`, `3 TiKV` đều `Up`. |
| **Ảnh minh họa 1.4.3 (MongoDB)** | Tab **`>_ MONGOSH`** trong Compass | Kết quả `modifiedCount: 1` / `0` (cập nhật có điều kiện) và `abortTransaction()` không tạo đơn 9002. |
| **Ảnh minh họa 1.4.3 (TiDB)** | **DBeaver SQL Editor** | Kết quả khối `BEGIN ... ROLLBACK` và `SELECT * FROM orders` chứng minh không có bản ghi `SHOULD_ROLLBACK`. |
| **Ảnh minh họa 1.4.4** | **MONGOSH** + **DBeaver / TiDB Dashboard** | `rs.status()` (`PRIMARY`) của MongoDB; `CLUSTER_INFO` và `SHOW TABLE stock REGIONS` của TiDB. |

---

## 5. Dọn dẹp sau khi demo xong
```bash
# Dừng TiDB (giữ nguyên volume, không xóa dữ liệu)
docker compose -f docker/compose.tidb.yml stop
```
*(Nếu muốn xóa hẳn database demo `demo_flashsale`: chạy `db.dropDatabase()` trên MongoDB hoặc `DROP DATABASE demo_flashsale;` trên TiDB trước khi stop.)*
