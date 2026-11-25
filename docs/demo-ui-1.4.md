# Hướng dẫn Kết nối UI & Kịch bản Demo Mục 1.4 (MongoDB Compass & MySQL Workbench)

Tài liệu này hướng dẫn từng bước **khởi động, kiểm chứng phiên bản, kết nối bằng giao diện trực quan (MongoDB Compass, MySQL Workbench, TiDB Dashboard)** và **thực thi đầy đủ các kịch bản demo** phục vụ **Mục 1.4**, **Phụ lục A.7–A.8** và **Phụ lục B.7–B.8**, đồng thời tạo tiền đề dẫn dắt sang **Phần 2 (Phân tích vấn đề chuyên sâu)** của báo cáo bài tập lớn Nhóm 16:

- **Phần 0:** Bảng ánh xạ Mục 1.4 ↔ Phụ lục A.8 / B.8 ↔ Tiền đề nối sang Phần 2.
- **Phần I (MongoDB 8.0.20 — MongoDB Compass):** Kiểm chứng phiên bản & Replica Set `flashsale`, cùng đầy đủ **6 kịch bản Phụ lục A.8** (*Hình 4.1, Hình A.1 → A.5*).
- **Phần II (TiDB v8.5.7 — MySQL Workbench & TiDB Dashboard):** Kiểm chứng phiên bản cụm 5 nút (`1 PD + 1 TiDB + 3 TiKV`), cấu hình cache/replica, cùng đầy đủ **6 kịch bản Phụ lục B.8** (*Hình 4.2, Hình B.5 → B.7*).
- **Phần III (MySQL 8.4.8 — MySQL Workbench):** Kiểm chứng nhanh phiên bản, buffer pool `3 GiB` và độ bền của hệ RDBMS đối chứng để khép kín **Bảng 5.1 (Mục 1.5)** và **Mục 2.1.3**.
- **Phần IV:** Khung lời dẫn trực tiếp từ kết quả quan sát trên UI Mục 1.4 sang các câu hỏi nghiên cứu ở **Phần 2 (Mục 2.1 → 2.6)**.

> **Nguyên tắc vận hành an toàn:**
> 1. Chỉ chạy **một hệ DBMS tại một thời điểm** trên Docker Desktop (`docker compose -f ... stop` hệ cũ trước khi `up -d` hệ mới; **không** dùng `down -v` để bảo toàn volume dữ liệu).
> 2. Toàn bộ kịch bản chỉ thao tác trên hai database riêng biệt là `demo_flashsale` và `demo_ose`, **không chạm vào dữ liệu benchmark TPC-C**.
> 3. **Lưu ý bắt buộc trên MySQL Workbench:** Khi chạy kịch bản cần **2 phiên giao dịch song song** (Kịch bản B.8-5 và B.8-6), phải bấm về màn hình **Home (🏠)** và nhấp đúp vào ô kết nối **2 lần** để mở **2 tab kết nối độc lập** (ví dụ `TiDB_Local` và `TiDB_Local (1)`). Không dùng 2 tab `SQL File` con nằm trong cùng một cửa sổ kết nối vì chúng dùng chung một session.

---

## 0. Chuẩn bị & Bảng ánh xạ Mục 1.4 ↔ Phụ lục A.8 / B.8 ↔ Phần 2

### 0.1. Thông số kết nối UI trên máy cá nhân (Windows + Docker Desktop)

| Hệ DBMS | File Docker Compose | Công cụ UI sử dụng | Địa chỉ kết nối (Docker local) |
| :--- | :--- | :--- | :--- |
| **MongoDB 8.0.20** | `docker/compose.mongo.yml` | **MongoDB Compass** *(kèm tab `>_ MONGOSH`)* | `mongodb://127.0.0.1:27018/?directConnection=true` |
| **TiDB v8.5.7** | `docker/compose.tidb.yml` | **MySQL Workbench** | Host `127.0.0.1`, Port **`14000`**, User `root`, mật khẩu trống |
| **TiDB v8.5.7** | `docker/compose.tidb.yml` | **TiDB Dashboard** *(trình duyệt Web)* | `http://127.0.0.1:12379/dashboard` *(User `root`, mật khẩu trống)* |
| **MySQL 8.4.8** *(đối chứng)* | `docker/compose.mysql.yml` | **MySQL Workbench** | Host `127.0.0.1`, Port **`13306`**, User `root`, mật khẩu trống |

### 0.2. Bảng ánh xạ kịch bản sang nội dung nghiên cứu Phần 2

| Mục 1.4 | Kịch bản Phụ lục A.8 (MongoDB Compass) | Kịch bản Phụ lục B.8 (MySQL Workbench + TiDB Dashboard) | Tiền đề mở ra Phần 2 (Nghiên cứu chuyên sâu) |
| :--- | :--- | :--- | :--- |
| **1.4.1 & 1.4.2** Triển khai, phiên bản & kết nối | **A.8-1:** Kiểm chứng `8.0.20`, kết nối Replica Set `flashsale` (*Hình 4.1, A.1*) | **B.8-1 & B.8-4:** Kiểm chứng `v8.5.7` trên 5 nút (`1 PD + 1 TiDB + 3 TiKV`), kết nối SQL & Dashboard (*Hình 4.2, B.6*) | Xác lập môi trường & cấu hình công bằng ở **Mục 2.1.3** (cache bộ nhớ đệm 3 GiB ngang nhau, độ bền tương đương). |
| **1.4.3** Chức năng cơ bản, chống âm kho & ACID | **A.8-2, A.8-3, A.8-4:** CRUD BSON, `updateOne` có `$gte` chống âm kho (*Hình A.2*), Multi-document Transaction `COMMIT`/`ABORT` (*Hình A.3*) | **B.8-1, B.8-3, B.8-2:** CRUD với `AUTO_RANDOM`, `UPDATE ... WHERE s_quantity >= qty`, Transaction `COMMIT`/`ROLLBACK` (*Hình B.5*) | Cơ sở cho **3 luật tồn kho (INV1–INV3)** ở **Mục 2.1.2**, baseline an toàn **P1 (Mục 2.2)** và đánh đổi thiết kế (a) vs (b) của MongoDB ở **Mục 2.3.3 & 2.4.4**. |
| **1.4.4** Giám sát, đồng thời & đổi lược đồ | **A.8-5 & A.8-6:** Linh hoạt lược đồ & backfill (*Hình A.4*); giám sát WiredTiger 3 GiB, `currentOp`, tab Performance (*Hình A.5*) | **B.8-4, B.8-5, B.8-6:** Phân bố Region (`SHOW TABLE ... REGIONS`), Online DDL không chặn tải (*Hình B.7*), chờ khóa `pessimistic` 2 phiên | Đặt vấn đề trực tiếp cho **Mục 2.2** (chờ khóa / write conflict / hot Region), **Mục 2.5** (thêm TiKV có cứu được hot SKU không) và **Mục 2.6** (Online Schema Evolution). |

---

## Phần I. Kịch bản Demo MongoDB 8.0.20 trên **MongoDB Compass** (Phụ lục A.7 & A.8)

### Kịch bản A.8-1: Khởi tạo, kết nối Replica Set & Kiểm chứng phiên bản (**Hình 4.1 & Hình A.1**)
1. Mở PowerShell tại thư mục repo `e:\BTL-DBMS`, bật container MongoDB:
   ```powershell
   docker compose -f docker/compose.mongo.yml up -d
   docker compose -f docker/compose.mongo.yml ps
   ```
   *(Đợi cột `STATUS` báo `Up (healthy)`.)*
2. Mở **MongoDB Compass** → bấm **New Connection** → dán chính xác chuỗi kết nối:
   ```text
   mongodb://127.0.0.1:27018/?directConnection=true
   ```
   > **Lưu ý giải thích khi trình bày:** Bắt buộc có `?directConnection=true` vì Replica Set 1 nút trong Docker khai báo hostname nội bộ `mongo:27017`; nếu bỏ tham số này client bên ngoài máy host sẽ không phân giải được tên `mongo`.
3. Bấm **Save & Connect**, mở thanh **`>_ MONGOSH`** ở góc dưới bên trái cửa sổ Compass và chạy lệnh kiểm chứng:
   ```javascript
   // 1. Kiểm chứng đúng phiên bản MongoDB Community 8.0.20 (Phụ lục A.7)
   db.version();

   // 2. Kiểm chứng Replica Set 1 nút "flashsale" ở trạng thái PRIMARY
   rs.status().members.map(m => ({
     id: m._id, name: m.name, stateStr: m.stateStr, health: m.health
   }));
   ```
   - **Kết quả kỳ vọng:** Trả về `"8.0.20"`, `stateStr: "PRIMARY"`, `health: 1`. *(Chụp **Hình 4.1 / Hình A.1**: giao diện Compass + output `rs.status()`)*.

---

### Kịch bản A.8-2: CRUD cơ bản trên mô hình Document BSON (`demo_flashsale`)
Chạy tiếp trong thanh **`>_ MONGOSH`** của Compass:
```javascript
use demo_flashsale;

// Làm sạch dữ liệu demo nếu chạy lại nhiều lần
db.item.drop();
db.stock.drop();
db.orders.drop();

// CREATE: Chèn sản phẩm (i_id: 101), tồn kho ban đầu (s_quantity: 5) và 1 đơn kiểm thử xóa
db.item.insertOne({ i_id: 101, i_name: "Tai nghe Flash-Sale", i_price: 500000 });
db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 });
db.orders.insertOne({ o_id: 9000, o_i_id: 101, qty: 1, status: "TEST_DELETE" });

// READ: Truy vấn lại document BSON vừa chèn
db.item.findOne({ i_id: 101 });
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });

// DELETE: Xóa sạch đơn kiểm thử 9000 (giữ tồn kho = 5 cho kịch bản A.8-3)
db.orders.deleteOne({ o_id: 9000 });
db.orders.find().toArray(); // []
```
*(Bấm nút **Refresh** ở cột trái Compass để thấy database `demo_flashsale` và các collection hiển thị trực quan).*

---

### Kịch bản A.8-3: Cập nhật nguyên tử có điều kiện — Chống âm kho (**Hình A.2**)
```javascript
// Lần (a): Mua 3 khi kho còn 5 -> thỏa s_quantity >= 3 -> modifiedCount: 1, tồn giảm còn 2
db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
  { $inc: { s_quantity: -3 } }
);

// Lần (b): Mua 4 khi kho chỉ còn 2 -> không thỏa s_quantity >= 4 -> modifiedCount: 0, từ chối trừ!
db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 4 } },
  { $inc: { s_quantity: -4 } }
);

// Kiểm chứng: s_quantity giữ nguyên là 2 (không phát sinh tồn kho âm)
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });
```
- **Chụp Hình A.2:** Output `mongosh` thể hiện rõ `modifiedCount: 1` ở lần (a) và `modifiedCount: 0` ở lần (b).
- **Ý nghĩa nối sang Phần 2:** `updateOne` chỉ đảm bảo nguyên tử trên **1 document** `stock`. Khi tạo đơn hàng cần đồng thời trừ `stock` và chèn `orders`/`order_line`, nếu không bọc trong Multi-document Transaction (như Thiết kế (b) ở **Mục 2.3.3**), ứng dụng sập giữa 2 lệnh sẽ làm mất tồn kho mà không có đơn (vi phạm `INV2`).

---

### Kịch bản A.8-4: Multi-document ACID Transaction — `COMMIT` & `ABORT` (**Hình A.3**)
```javascript
// --- Phiên (a) COMMIT: Mua nốt 2 đơn vị khi kho còn 2 -> tồn về 0 & lưu đơn 9001 ---
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
  print("==> Phiên (a): COMMIT thành công đơn 9001, tồn kho về 0.");
} else {
  s1.abortTransaction();
}
s1.endSession();

// --- Phiên (b) ABORT: Chèn trước đơn 9002 rồi trừ 1 khi tồn = 0 -> hoàn nguyên toàn bộ ---
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
  print("==> Phiên (b): Hết hàng -> ABORT giao dịch, hoàn nguyên đơn 9002!");
}
s2.endSession();

// Kiểm chứng (Chụp Hình A.3): tồn = 0 và db.orders.find() CHỈ còn đơn 9001
db.stock.findOne({ s_w_id: 1, s_i_id: 101 });
db.orders.find().toArray();
```

---

### Kịch bản A.8-5: Đổi lược đồ trực tuyến — Schema-on-read & Backfill (**Hình A.4**)
```javascript
use demo_ose;
db.order_line.drop();

// 1. Tạo các document order_line lịch sử (chưa có trường ol_discount và ol_mig_state)
db.order_line.insertMany([
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
]);

// 2. Chèn trực tiếp document đơn mới đã có sẵn ol_discount & ol_mig_state (không cần ALTER TABLE)
db.order_line.insertOne({
  ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
  ol_discount: 1200, ol_mig_state: "MIGRATED"
});
```
> **Dừng lại bấm Refresh trên giao diện Compass → mở `demo_ose.order_line` để chụp Hình A.4:** Cho thấy rõ document cũ (chưa có `ol_discount`) và document mới (`3001` có `ol_discount: 1200`, `ol_mig_state: "MIGRATED"`) cùng tồn tại song song mà không phát sinh khóa bảng/MDL. Sau đó chạy tiếp bước backfill:

```javascript
// 3. Cập nhật (backfill) có điều kiện các document cũ chưa chuyển đổi
db.order_line.updateMany(
  { ol_mig_state: { $ne: "MIGRATED" } },
  { $set: { ol_discount: 500, ol_mig_state: "MIGRATED" } }
);

// Kiểm tra sau backfill: mọi document đều đã có đủ ol_discount và ol_mig_state = "MIGRATED"
db.order_line.find().toArray();
```

---

### Kịch bản A.8-6: Giám sát vận hành — WiredTiger Cache & Connections (**Hình A.5**)
```javascript
// 1. Kiểm chứng bộ nhớ đệm WiredTiger đặt tường minh đúng 3 GiB = 3,221,225,472 byte
db.serverStatus().wiredTiger.cache["maximum bytes configured"];

// 2. Kiểm tra số kết nối hiện hành và các thao tác đang hoạt động
db.serverStatus().connections;
db.currentOp({ active: true });
```
- Bấm thêm vào tab **Performance** trên thanh điều hướng của Compass để quan sát metrics thời gian thực và chụp **Hình A.5**.

---

## Phần II. Kịch bản Demo TiDB v8.5.7 trên **MySQL Workbench** & **TiDB Dashboard** (Phụ lục B.7 & B.8)

### Bước chuẩn bị: Dừng MongoDB, bật cụm TiDB 5 nút & Kết nối UI (**Hình 4.2**)
1. Chạy trong PowerShell (`e:\BTL-DBMS`):
   ```powershell
   docker compose -f docker/compose.mongo.yml stop
   docker compose -f docker/compose.tidb.yml up -d
   docker compose -f docker/compose.tidb.yml ps
   ```
   *(Đợi ~15–20 giây để 3 nút TiKV đăng ký đầy đủ với PD.)*
2. **Mở TiDB Dashboard (Web UI — chụp Hình 4.2):**
   - Truy cập `http://127.0.0.1:12379/dashboard` → đăng nhập Username `root`, Password *(để trống)*.
   - Mở mục **Cluster Info → Instances**: hiển thị đủ 5 nút (`1 PD`, `1 TiDB`, `3 TiKV`) trạng thái `Up`.
3. **Kết nối MySQL Workbench tới TiDB:**
   - Mở **MySQL Workbench** → bấm dấu **`+`** cạnh *MySQL Connections*:
     - **Connection Name:** `TiDB_Local`
     - **Hostname:** `127.0.0.1` · **Port:** `14000`
     - **Username:** `root` *(Password để trống)*
   - Bấm **Test Connection** → khi hiện thông báo *"Incompatible/nonstandard server version or connection protocol detected (8.0.11-TiDB-v8.5.7)"*, bấm **Continue Anyway** → bấm **OK** rồi nhấp đúp mở `TiDB_Local`.

---

### Kịch bản B.8-1: Kiểm chứng phiên bản, DDL (`AUTO_RANDOM`) & CRUD cơ bản
Dán và chạy khối lệnh sau trong SQL Editor của **MySQL Workbench** (`Ctrl + Shift + Enter`):
```sql
-- Tắt Safe Updates mặc định của MySQL Workbench để tránh lỗi 1175 khi DELETE/UPDATE không theo PK
SET SQL_SAFE_UPDATES = 0;

-- 1. Kiểm chứng đúng nhánh phiên bản 8.5.7-TiDB (Phụ lục B.7)
SELECT VERSION() AS tidb_version;

-- 2. Tạo DB demo_flashsale và 3 bảng item, stock, orders (dùng AUTO_RANDOM chống điểm nóng ghi)
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

CREATE TABLE orders (
  o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */,
  o_i_id INT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(20) NOT NULL
);

-- 3. CRUD cơ bản: INSERT, SELECT (thấy o_id sinh khóa ngẫu nhiên phân tán) và DELETE
INSERT INTO item VALUES (101, 'Tai nghe Flash-Sale', 500000);
INSERT INTO stock VALUES (1, 101, 5);
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'TEST_DELETE');

SELECT * FROM item;
SELECT * FROM stock;
SELECT * FROM orders; -- Quan sát cột o_id sinh số ngẫu nhiên 64-bit bởi AUTO_RANDOM

DELETE FROM orders WHERE status = 'TEST_DELETE';
SELECT * FROM orders; -- Đã xóa đơn kiểm thử, tồn kho vẫn là 5
```

---

### Kịch bản B.8-3 & B.8-2: Trừ tồn kho có điều kiện & Giao dịch ACID (**Hình B.5**)
> **Lưu ý thứ tự chạy:** Ta chạy **B.8-3** trước để tồn kho giảm từ `5 → 2`, rồi chạy ngay **B.8-2** để tồn kho giảm từ `2 → 0` (`COMMIT`) và chạm ngưỡng hết hàng (`ROW_COUNT() = 0` → `ROLLBACK`), khớp chính xác các con số trong bảng Phụ lục B.8.

#### (1) Kịch bản B.8-3 — Trừ tồn kho có điều kiện (chống âm kho)
```sql
USE demo_flashsale;

-- Lần (a): Mua 3 khi còn 5 -> Action Output báo "1 row(s) affected", tồn giảm còn 2
UPDATE stock
SET s_quantity = s_quantity - 3
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;

-- Lần (b): Mua 4 khi còn 2 -> Action Output báo "0 row(s) affected", tồn giữ nguyên 2 (không âm)
UPDATE stock
SET s_quantity = s_quantity - 4
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101; -- s_quantity = 2
```

#### (2) Kịch bản B.8-2 — Giao dịch ACID phân tán (`COMMIT` & `ROLLBACK`)
```sql
-- Phiên (a): Trừ nốt 2 đơn vị tồn kho (2 -> 0) và chèn đơn 'COMMITTED' -> COMMIT
BEGIN;
UPDATE stock
SET s_quantity = s_quantity - 2
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 2;

INSERT INTO orders (o_i_id, qty, status) VALUES (101, 2, 'COMMITTED');
COMMIT;

-- Phiên (b): Chèn đơn 'SHOULD_ROLLBACK' rồi trừ tồn khi đã về 0 -> ROW_COUNT() = 0 -> ROLLBACK
BEGIN;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'SHOULD_ROLLBACK');

UPDATE stock
SET s_quantity = s_quantity - 1
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;

SELECT ROW_COUNT() AS updated_rows; -- Hiển thị 0 (thiếu hàng)
ROLLBACK;

-- Kiểm chứng sau ROLLBACK (Chụp Hình B.5): tồn = 0, bảng orders CHỈ có đơn 'COMMITTED'
SELECT * FROM stock;
SELECT * FROM orders;
```

---

### Kịch bản B.8-4: Quan sát phân bố cụm PD / TiKV, cấu hình & Region (**Hình B.6**)
```sql
USE demo_flashsale;

-- 1. Kiểm chứng đủ 5 nút (1 pd, 1 tidb, 3 tikv) trạng thái Up và cùng phiên bản v8.5.7
SELECT TYPE, INSTANCE, STATUS_ADDRESS, VERSION
FROM information_schema.CLUSTER_INFO
ORDER BY TYPE, INSTANCE;

-- 2. Kiểm chứng cấu hình Phụ lục B.7: block-cache = 1GiB trên mỗi TiKV (tổng 3 GiB) & max-replicas = 1
SHOW CONFIG WHERE name IN ('storage.block-cache.capacity', 'replication.max-replicas');

-- 3. Kiểm chứng chế độ giao dịch mặc định (pessimistic) và tối ưu 2PC (async commit, 1PC)
SHOW VARIABLES WHERE Variable_name IN (
  'tidb_txn_mode', 'tidb_enable_async_commit', 'tidb_enable_1pc', 'transaction_isolation'
);

-- 4. Quan sát REGION_ID, LEADER_STORE_ID của bảng stock và kế hoạch thực thi đi đúng khóa chính
SHOW TABLE stock REGIONS;
EXPLAIN ANALYZE SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
```
- **Chụp Hình B.6:** Kết hợp màn hình **TiDB Dashboard → Cluster Info** và bảng kết quả `SHOW TABLE stock REGIONS`.

---

### Kịch bản B.8-5: Online DDL không chặn giao dịch đang hoạt động (**Hình B.7**)
1. Tại **Kết nối Workbench 1 (`TiDB_Local`)**, khởi tạo bảng `demo_ose.order_line` và giữ mở một giao dịch đọc:
   ```sql
   CREATE DATABASE IF NOT EXISTS demo_ose;
   USE demo_ose;
   DROP TABLE IF EXISTS order_line;

   CREATE TABLE order_line (
     ol_w_id INT NOT NULL,
     ol_d_id INT NOT NULL,
     ol_o_id INT NOT NULL,
     ol_number INT NOT NULL,
     ol_i_id INT NOT NULL,
     ol_quantity INT NOT NULL,
     PRIMARY KEY (ol_w_id, ol_d_id, ol_o_id, ol_number)
   );
   INSERT INTO order_line VALUES (1, 1, 1001, 1, 101, 2);

   -- Mở giao dịch đọc và GIỮ MỞ (chưa COMMIT)
   BEGIN;
   SELECT * FROM order_line LIMIT 1;
   ```
2. Bấm về màn hình **Home (🏠)** của Workbench → nhấp đúp vào `TiDB_Local` để mở **Kết nối độc lập số 2 (`TiDB_Local (1)`)** và chạy Online DDL:
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';
   ```
   > **Lưu ý cơ chế Metadata Lock của TiDB v8.5.7:** Nếu Kết nối 2 đợi phiên đọc cũ ở Kết nối 1 kết thúc, bạn có thể mở thêm **Kết nối 3** chạy `SELECT * FROM demo_ose.order_line;` hoặc `INSERT` đơn mới — Kết nối 3 vẫn thực thi **xong ngay tức thì (0 giây đóng băng)**, không hề bị chặn dây chuyền toàn bảng như Exclusive MDL của MySQL (sẽ phân tích sâu ở **Mục 2.6.1**). Sau khi chạy `COMMIT;` ở Kết nối 1, lệnh `ALTER TABLE` hoàn tất ngay trong vài trăm ms.
3. Trên **Kết nối 2**, kiểm tra lịch sử Online DDL (*chụp **Hình B.7***):
   ```sql
   ADMIN SHOW DDL JOBS 5; -- Thấy JOB_TYPE = add column, STATE = synced
   SELECT * FROM order_line;
   ```

---

### Kịch bản B.8-6: Tranh chấp đồng thời 2 phiên trên cùng 1 dòng `stock` (`pessimistic`)
1. Ở **Kết nối Workbench 1 (`TiDB_Local`)**, đặt lại tồn kho `= 5` rồi mở giao dịch trừ 1 sản phẩm và **giữ khóa chưa `COMMIT`**:
   ```sql
   SET SQL_SAFE_UPDATES = 0;
   USE demo_flashsale;
   UPDATE stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;

   BEGIN;
   UPDATE stock
   SET s_quantity = s_quantity - 1
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;
   -- DỪNG LẠI, CHƯA CHẠY COMMIT! (Phiên 1 đang giữ khóa bi quan trên dòng 1, 101)
   ```
2. Chuyển sang **Kết nối Workbench 2 (`TiDB_Local (1)`)**, chạy cùng lệnh cập nhật đó:
   ```sql
   USE demo_flashsale;
   BEGIN;
   UPDATE stock
   SET s_quantity = s_quantity - 1
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;
   ```
   - **Quan sát trực quan trên UI:** Tab Kết nối 2 chuyển sang xoay vòng **`Running...`** (bị xếp hàng `lock wait` chờ Phiên 1 giải phóng khóa).
3. Quay lại **Kết nối 1** chạy `COMMIT;` → lập tức **Kết nối 2** chạy xong (`1 row(s) affected`). Chạy tiếp `COMMIT;` ở **Kết nối 2** rồi đối soát kết quả:
   ```sql
   SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
   -- Kết quả: s_quantity = 3 (giảm chính xác 2 đơn vị từ 5 -> 3, không xảy ra Lost Update)
   ```

---

## Phần III. Kiểm chứng nhanh hệ đối chứng **MySQL 8.4.8** trên MySQL Workbench

Để khép kín **Bảng 5.1 (Mục 1.5)** và chứng minh cả 3 hệ DBMS đều được cấu hình bộ nhớ đệm **3 GiB** và **độ bền ngang nhau** trước khi bước sang **Phần 2 (Mục 2.1.3)**:

1. Dừng TiDB và bật container MySQL đối chứng với `innodb_buffer_pool_size = 3 GiB` (`3221225472` byte):
   ```powershell
   docker compose -f docker/compose.tidb.yml stop
   $env:FLASHSALE_MYSQL_BUFFER_POOL_BYTES="3221225472"
   docker compose -f docker/compose.mysql.yml up -d
   docker compose -f docker/compose.mysql.yml ps
   ```
2. Trong **MySQL Workbench**, tạo kết nối `MySQL_Local` tới `127.0.0.1:13306` (`root`, mật khẩu trống) và chạy:
   ```sql
   -- 1. Kiểm chứng đúng phiên bản MySQL 8.4.8 LTS
   SELECT VERSION() AS mysql_version;

   -- 2. Kiểm chứng Buffer Pool 3 GiB (= WiredTiger 3 GiB = 3 x 1 GiB TiKV) và độ bền chuẩn ACID
   SHOW VARIABLES WHERE Variable_name IN (
     'innodb_buffer_pool_size',          -- 3221225472 (3 GiB)
     'innodb_flush_log_at_trx_commit',   -- 1
     'sync_binlog',                      -- 1
     'transaction_isolation'             -- REPEATABLE-READ
   );
   ```

---

## Phần IV. Khung lời dẫn từ Demo Mục 1.4 sang trình bày **Phần 2 (Nghiên cứu chuyên sâu)**

Khi kết thúc phần demo UI Mục 1.4, người thuyết trình dùng chính 4 hiện tượng vừa quan sát trực tiếp trên Compass & Workbench để đặt vấn đề cho **Phần 2**:

1. **Từ A.8-3 / B.8-3 & A.8-4 / B.8-2 → Mục 2.1 & 2.3 (Ba luật tồn kho & Kiểm chứng dưới tải/sự cố):**
   - *Điều vừa thấy trên UI:* Ở quy mô 1–2 phiên thủ công, cập nhật có điều kiện (`P1`) kết hợp giao dịch ACID bảo vệ tồn kho không âm và hoàn nguyên đơn khi hết hàng.
   - *Vấn đề nghiên cứu Phần 2:* Khi đẩy lên **64–256 client** đồng thời và tiến trình ứng dụng bị giết đột ngột ngay cửa sổ *"đã commit nhưng chưa kịp nhận phản hồi"* (**Mục 2.3**), phương pháp ngây thơ đọc-rồi-ghi (`P0`) làm MySQL và TiDB mất cập nhật hàng nghìn đơn (`INVALID`), còn thiết kế bỏ giao dịch đa tài liệu của MongoDB (`Thiết kế b`) làm lệch tồn kho ngay khi sập tiến trình dù tốc độ tăng ~9,9 lần.
2. **Từ B.8-6 (chờ khóa dòng) & A.8-4 (MVCC snapshot) → Mục 2.2 & 2.4 (Chẩn đoán & giảm nghẽn Hot SKU):**
   - *Điều vừa thấy trên UI:* Trên Workbench ở Kịch bản B.8-6, Phiên 2 chạm cùng mặt hàng `(1, 101)` đã phải đứng chờ khóa của Phiên 1; trên MongoDB, hai giao dịch snapshot chạm cùng document sẽ nảy sinh `WriteConflict`.
   - *Vấn đề nghiên cứu Phần 2:* Khi mọi yêu cầu Flash-sale dồn vào **1 mặt hàng nóng (Hot SKU)** ở **Mục 2.2**, TPS cả 3 hệ sụp **2,8–3,7 lần** theo 3 cơ chế nghẽn khác nhau (MySQL tốn **97% thời gian chờ khóa dòng**; MongoDB nổ **~75.200 lỗi `write_conflict`/lượt**; TiDB xếp hàng ở Region nóng), khiến việc tăng thêm client hoàn toàn vô tác dụng. Điều này dẫn tới giải pháp **chia tồn kho thành `N` slot (`P2`)** và **cấp mã đơn theo lô** ở **Mục 2.4** giúp tăng thông lượng **5,9–8,5 lần** mà vẫn `VALID` tuyệt đối.
3. **Từ B.8-4 (`SHOW TABLE stock REGIONS`) → Mục 2.5 (Mở rộng ngang, 2PC & Replication trên TiDB):**
   - *Điều vừa thấy trên UI:* Cụm TiDB có tới **3 nút TiKV**, nhưng `SHOW TABLE stock REGIONS` cho thấy mặt hàng nóng mặc định chỉ nằm trong **1 Region duy nhất** do 1 nút TiKV giữ Leader.
   - *Vấn đề nghiên cứu Phần 2:* Trả lời câu hỏi lớn ở **Mục 2.5** *"Thêm TiKV có cứu được Flash-sale không?"* — nếu giữ nguyên 1 dòng tồn kho (`P1`), tăng từ 1 lên 3 TiKV chỉ đạt `1,22×` vì 1 store gánh hết tải; chỉ khi kết hợp **chia slot (`P2 N=27`) + tách Region** rải đều qua 3 TiKV thì TPS mới vọt lên **`3,44×`** (hiệu ứng tương tác), đồng thời định lượng chi phí giao dịch liên phân vùng (2PC) và chi phí sao chép Raft (`rf=3` giảm `25–47%` ở tải ghi lan rộng).
4. **Từ A.8-5 (Schemaless backfill) & B.8-5 (Online DDL) → Mục 2.6 (Đổi lược đồ khi đang bán hàng):**
   - *Điều vừa thấy trên UI:* Trên vài dòng demo, MongoDB thêm trường mới tức thì và TiDB chạy `ADD COLUMN` không chặn giao dịch mới, nhưng các dòng cũ vẫn cần bước cập nhật dữ liệu lịch sử (`backfill`).
   - *Vấn đề nghiên cứu Phần 2:* Trên bảng `order_line` **3 triệu dòng** đang gánh tải bán hàng trực tiếp (**Mục 2.6**), MySQL có thể bị đóng băng toàn bảng suốt **57 giây** chỉ vì 1 giao dịch đọc dài gây kẹt *Metadata Lock* (hóa giải còn 2 giây nhờ `lock_wait_timeout = 3`), và phép đo đối đầu giữa 3 chiến lược chuyển dữ liệu (**Eager, Batch 1.000, Lazy**) chỉ ra **Batch 1.000** là điểm cân bằng tối ưu trên cả ba hệ.

*(Xem tiếp kịch bản demo chi tiết cho các mục thuộc Phần 2 tại [demo-phan-2.md](demo-phan-2.md) và [demo-ui-2.6.md](demo-ui-2.6.md)).*

---

## 5. Checklist ảnh chụp báo cáo (Mục 1.4 & Phụ lục A, B)

| Ký hiệu Hình | Vị trí trong báo cáo | Nguồn chụp trên UI | Nội dung cần hiện rõ trên ảnh |
| :--- | :--- | :--- | :--- |
| **Hình 4.1 / Hình A.1** | Mục 1.4.2 & Phụ lục A.8-1 | **MongoDB Compass** + `>_ MONGOSH` | Kết nối `127.0.0.1:27018`, output `db.version()` = `8.0.20` và `rs.status()` báo `PRIMARY`, `health: 1`. |
| **Hình A.2** | Phụ lục A.8-3 | Tab `>_ MONGOSH` trong Compass | Hai lệnh `db.stock.updateOne` trả về `modifiedCount: 1` (mua 3 còn 2) và `modifiedCount: 0` (mua 4 bị từ chối). |
| **Hình A.3** | Phụ lục A.8-4 | Tab `>_ MONGOSH` trong Compass | Sau `commitTransaction()` (đơn 9001) và `abortTransaction()` (đơn 9002), `db.orders.find()` chỉ còn đơn `9001`. |
| **Hình A.4** | Phụ lục A.8-5 | Giao diện Document **Compass** | Collection `demo_ose.order_line` hiển thị song song document cũ (chưa có `ol_discount`) và document mới (`MIGRATED`). |
| **Hình A.5** | Phụ lục A.8-6 | `>_ MONGOSH` + tab **Performance** | `wiredTiger.cache` = `3221225472` byte (3 GiB), `connections`, `currentOp` và biểu đồ Performance. |
| **Hình 4.2 / Hình B.6** | Mục 1.4.2, 1.4.4 & Phụ lục B.8-4 | **TiDB Dashboard** + **MySQL Workbench** | Dashboard **Cluster Info → Instances** đủ 5 nút `v8.5.7` (`Up`) + kết quả `SHOW TABLE stock REGIONS`. |
| **Hình B.5** | Phụ lục B.8-2 | **MySQL Workbench** | Kết quả `SELECT * FROM orders` sau `ROLLBACK` chỉ có dòng `'COMMITTED'`, không có `'SHOULD_ROLLBACK'`. |
| **Hình B.7** | Phụ lục B.8-5 | **MySQL Workbench** (2 tab kết nối) | Lệnh `ALTER TABLE order_line ADD COLUMN ...` hoàn tất (`ADMIN SHOW DDL JOBS 5` báo `synced`) song song giao dịch mở. |

---

## 6. Dọn dẹp an toàn sau khi demo xong

```powershell
# Dừng các container (giữ nguyên toàn bộ volume dữ liệu, KHÔNG dùng cờ -v)
docker compose -f docker/compose.mysql.yml stop
docker compose -f docker/compose.tidb.yml stop
docker compose -f docker/compose.mongo.yml stop
```
*(Tùy chọn: nếu muốn xóa riêng 2 database nháp trước khi stop, chạy `db.getSiblingDB("demo_flashsale").dropDatabase(); db.getSiblingDB("demo_ose").dropDatabase();` trên MongoDB hoặc `DROP DATABASE IF EXISTS demo_flashsale; DROP DATABASE IF EXISTS demo_ose;` trên TiDB/MySQL).*
