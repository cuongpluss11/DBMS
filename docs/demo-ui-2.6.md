# Hướng dẫn Demo UI Chi tiết – Mục 2.6 (Đổi lược đồ khi đang bán hàng / Online Schema Evolution)

Tài liệu này hướng dẫn demo trực quan trên **Docker Desktop local (Windows)** cho **Mục 2.6** trong báo cáo Nhóm 16 (ứng với mục 2.4 của đặc tả), gồm 3 kịch bản cốt lõi:
1. **E1 – Kẹt Metadata Lock (MDL) & Online DDL:** Chứng minh trực tiếp trên 4 tab SQL cảnh MySQL bị **treo cứng cả bảng** chỉ vì 1 giao dịch đọc quên chốt, cách hóa giải bằng **`lock_wait_timeout = 3`**, và so sánh trực tiếp với **TiDB Online DDL (không chặn tải mới)** và **MongoDB (schemaless + `createIndex`)**.
2. **E2 / E3 – Chuyển dữ liệu cũ (`ol_discount`, `ol_mig_state`):** Minh họa cập nhật có điều kiện (`WHERE ol_mig_state = 'UNMIGRATED'`) theo kiểu **Lazy** (chuyển đúng 1 đơn khi đọc) và **Batch** (chuyển theo lô), kèm tính **idempotent** (chạy lại lần 2 không sửa trùng).
3. **Kiểm tra đúng đắn sau chuyển đổi:** Câu SQL / Aggregation đối soát đảm bảo `0` dòng `UNMIGRATED` và `0` dòng sai công thức `ol_discount = ⌊ol_quantity × i_price × r / 100⌋`.

> **Nguyên tắc:** Chỉ bật **1 DBMS tại một thời điểm** trên Docker Desktop. Kịch bản dùng database riêng `demo_ose` (chỉ tạo dữ liệu mẫu nhỏ, chạy tức thì trong vài giây, không cần nạp bộ `W = 10` và không đụng vào dữ liệu benchmark).

---

## 0. Bảng thông số kết nối Docker local (Windows)

| Hệ DBMS | Lệnh bật container (`e:\BTL-DBMS`) | Công cụ UI | Thông số kết nối |
| --- | --- | --- | --- |
| **MySQL 8.4.8** | `docker compose -f docker/compose.mysql.yml up -d` | **DBeaver** / MySQL Workbench | Host `127.0.0.1`, Port **`13306`**, User `root`, mật khẩu trống |
| **TiDB 8.5.7** | `docker compose -f docker/compose.tidb.yml up -d` | **DBeaver** + **TiDB Dashboard** | SQL: `127.0.0.1:14000` (`root`, trống) · Web: `http://127.0.0.1:12379/dashboard` |
| **MongoDB 8.0.20** | `docker compose -f docker/compose.mongo.yml up -d` | **MongoDB Compass** (`>_ MONGOSH`) | `mongodb://127.0.0.1:27018/?directConnection=true` |

---

## 1. Demo trên MySQL 8.4.8 (DBeaver / MySQL Workbench)

### Bước 1.1: Bật MySQL và tạo dữ liệu mẫu `demo_ose`
1. Chạy trong PowerShell (`e:\BTL-DBMS`):
   ```powershell
   docker compose -f docker/compose.mysql.yml up -d
   ```
2. Mở **DBeaver** → kết nối MySQL `127.0.0.1:13306` (`root`, mật khẩu trống).
3. Mở **Tab 1 (Setup)** và chạy khối khởi tạo bảng `item` và `order_line` (lược đồ gốc chưa có `ol_discount`, `ol_mig_state`):
   ```sql
   CREATE DATABASE IF NOT EXISTS demo_ose;
   USE demo_ose;

   DROP TABLE IF EXISTS order_line;
   DROP TABLE IF EXISTS item;

   CREATE TABLE item (
     i_id INT PRIMARY KEY,
     i_price INT NOT NULL
   );

   CREATE TABLE order_line (
     ol_w_id INT NOT NULL,
     ol_d_id INT NOT NULL,
     ol_o_id INT NOT NULL,
     ol_number INT NOT NULL,
     ol_i_id INT NOT NULL,
     ol_quantity INT NOT NULL,
     PRIMARY KEY (ol_w_id, ol_d_id, ol_o_id, ol_number)
   );

   -- 3 mức giá đại diện cho 3 mức chiết khấu: r=10 (>=5000), r=5 (2500..4999), r=0 (<2500)
   INSERT INTO item (i_id, i_price) VALUES (1, 6000), (2, 3000), (3, 1500);

   -- 4 dòng đơn cũ (ol_o_id <= 3000)
   INSERT INTO order_line (ol_w_id, ol_d_id, ol_o_id, ol_number, ol_i_id, ol_quantity) VALUES
     (1, 1, 1001, 1, 1, 2),  -- discount đúng = floor(2 * 6000 * 10 / 100) = 1200
     (1, 1, 1001, 2, 2, 3),  -- discount đúng = floor(3 * 3000 * 5 / 100)  = 450
     (1, 1, 1002, 1, 3, 4),  -- discount đúng = floor(4 * 1500 * 0 / 100)  = 0
     (1, 1, 1003, 1, 1, 5);  -- discount đúng = floor(5 * 6000 * 10 / 100) = 3000

   SELECT * FROM order_line;
   ```

---

### Bước 1.2: Demo E1 — Kẹt Metadata Lock (MDL) trực tiếp trên **4 tab SQL**
> **Mục tiêu cho người xem thấy:** Dù dùng `ALGORITHM=INSTANT`, chỉ 1 giao dịch đọc quên chốt cũng làm treo cứng cả bảng; đặt `lock_wait_timeout = 3` giải cứu ngay lập tức.

Mở sẵn **4 tab SQL Editor riêng biệt** (4 kết nối độc lập tới `demo_ose` trên MySQL — lưu ý trong DBeaver tắt *Auto-Commit* ở Tab 1 hoặc dùng `BEGIN;` tường minh):

1. **Ở Tab 1 (Giao dịch đọc dài quên chốt):**
   ```sql
   USE demo_ose;
   BEGIN;
   SELECT * FROM order_line LIMIT 1;
   -- KHÔNG CHẠY COMMIT! Giữ nguyên giao dịch đang mở.
   ```
2. **Ở Tab 2 (Chạy DDL thêm cột không đặt timeout ngắn):**
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED',
     ALGORITHM=INSTANT;
   ```
   → **Quan sát UI:** Tab 2 lập tức **quay vòng treo cứng** (đang chờ vé `EXCLUSIVE` MDL).
3. **Ở Tab 3 (Khách hàng mới xem đơn / đặt hàng):**
   ```sql
   USE demo_ose;
   SELECT * FROM order_line WHERE ol_o_id = 1001;
   ```
   → **Quan sát UI:** Tab 3 cũng **bị treo cứng theo** dù chỉ là câu `SELECT` đọc thuần!
4. **Ở Tab 4 (Bằng chứng `performance_schema.metadata_locks`):**
   ```sql
   SELECT OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE, LOCK_STATUS, OWNER_THREAD_ID
   FROM performance_schema.metadata_locks
   WHERE OBJECT_SCHEMA = 'demo_ose' AND OBJECT_NAME = 'order_line';
   ```
   → **Chụp ảnh màn hình:** Thấy rõ 3 dòng:
   - Tab 1: `SHARED_READ` — **`GRANTED`**
   - Tab 2 (`ALTER`): `EXCLUSIVE` — **`PENDING`**
   - Tab 3 (`SELECT`): `SHARED_READ` — **`PENDING`** *(bị chặn oan phía sau `ALTER`!)*
5. **Giải phóng & chứng minh cách sửa (`lock_wait_timeout = 3`):**
   - Bấm **Cancel** ở Tab 2 (hoặc chạy `COMMIT;` ở Tab 1 để Tab 2 & Tab 3 chạy xong, rồi chạy `ALTER TABLE order_line DROP COLUMN ol_discount, DROP COLUMN ol_mig_state;`).
   - Giữ lại Tab 1 đang mở `BEGIN; SELECT * FROM order_line LIMIT 1;`.
   - Chạy ở **Tab 2** với timeout ngắn:
     ```sql
     USE demo_ose;
     SET SESSION lock_wait_timeout = 3;
     ALTER TABLE order_line
       ADD COLUMN ol_discount BIGINT NULL,
       ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED',
       ALGORITHM=INSTANT;
     ```
   → **Quan sát UI:** Sau đúng **3 giây**, Tab 2 tự báo lỗi `Error 1205: Lock wait timeout exceeded` và **nhả hàng chờ**, còn **Tab 3 vẫn `SELECT` trả kết quả tức thì không bị treo!**
6. Cuối bước 1.2, chạy `COMMIT;` ở Tab 1 rồi chạy lại lệnh `ALTER TABLE ... ADD COLUMN ... ALGORITHM=INSTANT;` ở Tab 2 → thấy hoàn tất trong **~0,01–0,05 giây**!

---

### Bước 1.3: Demo E2 / E3 — Chuyển dữ liệu Lazy, Batch & Đối soát đúng đắn
Chạy trong 1 tab SQL trên `demo_ose`:
```sql
USE demo_ose;

-- Xem trạng thái trước khi chuyển: cả 4 dòng cũ đều là UNMIGRATED, ol_discount = NULL
SELECT * FROM order_line;

-- 1. Đơn MỚI phát sinh trong lúc chuyển (ol_o_id > 3000): ứng dụng ghi sẵn ol_discount và MIGRATED
INSERT INTO order_line (ol_w_id, ol_d_id, ol_o_id, ol_number, ol_i_id, ol_quantity, ol_discount, ol_mig_state)
VALUES (1, 1, 3001, 1, 1, 2, 1200, 'MIGRATED');

-- 2. Chuyển LƯỜI (Lazy P3): Khách xem đúng đơn 1001 -> chỉ chuyển có điều kiện các dòng của đơn 1001
UPDATE order_line ol
JOIN item i ON i.i_id = ol.ol_i_id
SET ol.ol_discount = (ol.ol_quantity * i.i_price *
      (CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END)) DIV 100,
    ol.ol_mig_state = 'MIGRATED'
WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id = 1001
  AND ol.ol_mig_state = 'UNMIGRATED';
-- Kết quả: Updated Rows = 2 (đơn 1001 chuyển thành 1200 và 450)

-- Kiểm tra tính IDEMPOTENT: chạy lại đúng câu UPDATE trên cho đơn 1001 -> Updated Rows = 0!
UPDATE order_line ol
JOIN item i ON i.i_id = ol.ol_i_id
SET ol.ol_discount = (ol.ol_quantity * i.i_price *
      (CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END)) DIV 100,
    ol.ol_mig_state = 'MIGRATED'
WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id = 1001
  AND ol.ol_mig_state = 'UNMIGRATED';

-- Quan sát trạng thái trung gian (tương thích 2 phiên bản): đơn 1001 & 3001 là MIGRATED; 1002 & 1003 vẫn UNMIGRATED
SELECT * FROM order_line ORDER BY ol_o_id, ol_number;

-- 3. Chuyển THEO LÔ NỀN (Batch P2): quét phần còn lại theo khoảng khóa chính (ol_o_id BETWEEN 1001 AND 2000)
UPDATE order_line ol
JOIN item i ON i.i_id = ol.ol_i_id
SET ol.ol_discount = (ol.ol_quantity * i.i_price *
      (CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END)) DIV 100,
    ol.ol_mig_state = 'MIGRATED'
WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id BETWEEN 1001 AND 2000
  AND ol.ol_mig_state = 'UNMIGRATED';
-- Kết quả: Updated Rows = 2 (chỉ chạm 1002 và 1003, tự bỏ qua 1001 đã MIGRATED)

-- 4. KIỂM TRA ĐÚNG ĐẮN (phải trả về 0 dòng là ĐẠT / VALID)
SELECT ol.ol_o_id, ol.ol_number, ol.ol_discount, ol.ol_mig_state
FROM order_line ol
JOIN item i ON i.i_id = ol.ol_i_id
WHERE ol.ol_mig_state <> 'MIGRATED'
   OR ol.ol_discount IS NULL
   OR ol.ol_discount <> (ol.ol_quantity * i.i_price *
      (CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END)) DIV 100;
```

---

## 2. Demo trên TiDB 8.5.7 (DBeaver + TiDB Dashboard)

### Bước 2.1: Dừng MySQL, bật TiDB & tạo dữ liệu mẫu
```powershell
docker compose -f docker/compose.mysql.yml stop
docker compose -f docker/compose.tidb.yml up -d
```
- Kết nối **DBeaver** tới `127.0.0.1:14000` (`root`, mật khẩu trống) và mở **TiDB Dashboard** tại `http://127.0.0.1:12379/dashboard`.
- Chạy lại **nguyên khối khởi tạo bảng `demo_ose`** ở Bước 1.1 trên DBeaver (TiDB tương thích cú pháp MySQL 100%).

### Bước 2.2: Demo E1 — TiDB Online DDL **KHÔNG chặn giao dịch mới** dù có giao dịch đọc dài
Mở **3 tab SQL** trên TiDB:
1. **Tab 1 (Giao dịch đọc dài):**
   ```sql
   USE demo_ose;
   BEGIN;
   SELECT * FROM order_line LIMIT 1;
   -- Giữ mở, KHÔNG COMMIT!
   ```
2. **Tab 2 (Chạy Online DDL trên TiDB):**
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';
   ```
   → **Quan sát:** Tab 2 đang chờ giao dịch Tab 1 kết thúc (để bảo đảm 0 lỗi `Information schema is changed`).
3. **Tab 3 (Khách hàng mới xem đơn & ghi đơn trong lúc Tab 2 đang chờ):**
   ```sql
   USE demo_ose;
   SELECT * FROM order_line WHERE ol_o_id = 1001;
   INSERT INTO order_line (ol_w_id, ol_d_id, ol_o_id, ol_number, ol_i_id, ol_quantity)
   VALUES (1, 1, 3002, 1, 1, 1);
   ```
   → **Điểm nhấn so với MySQL:** **Tab 3 chạy XONG NGAY LẬP TỨC (0 giây đóng băng!)** — không hề bị xếp hàng treo cứng như MySQL!
4. **Xem tiến độ Online DDL:** Chạy `COMMIT;` ở Tab 1 để Tab 2 hoàn tất, rồi chạy:
   ```sql
   ADMIN SHOW DDL JOBS 5;
   ```
   → Hiển thị lịch sử Online DDL của TiDB (`ADD COLUMN`, trạng thái `synced`, thời gian hoàn tất).
5. **Demo Bước E2 / E3 trên TiDB:** Chạy lại nguyên khối SQL Bước 1.3 trên DBeaver để minh họa Lazy, Batch và câu kiểm tra đúng đắn trả về `0` dòng sai.

---

## 3. Demo trên MongoDB 8.0.20 (MongoDB Compass + `>_ MONGOSH`)

### Bước 3.1: Dừng TiDB, bật MongoDB & kết nối Compass
```powershell
docker compose -f docker/compose.tidb.yml stop
docker compose -f docker/compose.mongo.yml up -d
```
- Mở **MongoDB Compass** → kết nối `mongodb://127.0.0.1:27018/?directConnection=true`.

### Bước 3.2: Demo E1 (Schemaless + `createIndex`) & E2/E3 (Lazy + Batch + Đối soát) trong `>_ MONGOSH`
```javascript
use demo_ose;
db.item.drop();
db.order_line.drop();

// 1. Nạp dữ liệu gốc (document cũ KHÔNG có trường ol_discount và ol_mig_state)
db.item.insertMany([
  { i_id: 1, i_price: 6000 },
  { i_id: 2, i_price: 3000 },
  { i_id: 3, i_price: 1500 }
]);
db.order_line.insertMany([
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 2, ol_i_id: 2, ol_quantity: 3 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 3, ol_quantity: 4 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1003, ol_number: 1, ol_i_id: 1, ol_quantity: 5 }
]);

// 2. E1 trên MongoDB: Không cần ALTER TABLE! Đơn mới ghi thẳng 2 trường mới ngay lập tức
db.order_line.insertOne({
  ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
  ol_discount: 1200, ol_mig_state: "MIGRATED"
});

// Tạo chỉ mục nền (E1)
db.order_line.createIndex({ ol_w_id: 1, ol_i_id: 1 }, { name: "idx_e1_ol_w_i" });
```
> **Bấm Refresh trên giao diện Compass → mở collection `demo_ose.order_line`:** Cho hội đồng thấy trực quan **document cũ (không có `ol_discount`)** và **document mới `3001` (có sẵn `ol_discount: 1200, ol_mig_state: "MIGRATED"`)** cùng tồn tại trong 1 collection!

```javascript
// Hàm tính ol_discount giống hệ thống benchmark
const prices = { 1: 6000, 2: 3000, 3: 1500 };
function calcDiscount(qty, itemId) {
  const p = prices[itemId];
  const r = p >= 5000 ? 10 : (p >= 2500 ? 5 : 0);
  return Math.floor((qty * p * r) / 100);
}

// 3. Chuyển LƯỜI (Lazy P3): Khách xem đơn 1001 -> chuyển có điều kiện (ol_mig_state != "MIGRATED")
db.order_line.find({ ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_mig_state: { $ne: "MIGRATED" } })
  .forEach(doc => {
    db.order_line.updateOne(
      { _id: doc._id, ol_mig_state: { $ne: "MIGRATED" } },
      { $set: { ol_discount: calcDiscount(doc.ol_quantity, doc.ol_i_id), ol_mig_state: "MIGRATED" } },
      { writeConcern: { w: "majority", j: true } }
    );
  });
// -> Bấm Refresh trên Compass: đơn 1001 đã tự thêm ol_discount & ol_mig_state="MIGRATED"!

// 4. Chuyển THEO LÔ NỀN (Batch P2): chuyển nốt các dòng còn thiếu bằng bulkWrite
const ops = [];
db.order_line.find({ ol_mig_state: { $ne: "MIGRATED" } }).forEach(doc => {
  ops.push({
    updateOne: {
      filter: { _id: doc._id, ol_mig_state: { $ne: "MIGRATED" } },
      update: { $set: { ol_discount: calcDiscount(doc.ol_quantity, doc.ol_i_id), ol_mig_state: "MIGRATED" } }
    }
  });
});
if (ops.length > 0) {
  db.order_line.bulkWrite(ops, { ordered: false, writeConcern: { w: "majority", j: true } });
}

// 5. KIỂM TRA ĐÚNG ĐẮN (trả về 0 tài liệu là ĐẠT / VALID)
db.order_line.countDocuments({ ol_mig_state: { $ne: "MIGRATED" } }); // 0
db.order_line.find({}, { _id: 0, ol_o_id: 1, ol_number: 1, ol_discount: 1, ol_mig_state: 1 }).toArray();
```

---

## 4. Dọn dẹp sau khi demo xong
```powershell
docker compose -f docker/compose.mongo.yml stop
```
*(Toàn bộ script trên chỉ thao tác trên database `demo_ose`, hoàn toàn không ảnh hưởng đến các volume hoặc dữ liệu benchmark hiện có.)*
