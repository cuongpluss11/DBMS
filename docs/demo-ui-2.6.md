# Phụ lục D (Mục D.5.3) — Minh chứng kiểm chứng trực quan cơ chế đổi lược đồ

> **Ghi chú sử dụng:** Nội dung dưới đây được biên tập gọn theo văn phong báo cáo để chèn trực tiếp nối tiếp sau **Mục D.5.2** của **Phụ lục D**. Khi thực thi trên Docker Compose cục bộ, chỉ bật một hệ quản trị tại một thời điểm (`docker compose -f docker/compose.<mysql|tidb|mongo>.yml up -d`) và kết nối bằng **MySQL Workbench** (`127.0.0.1:13306` cho MySQL; `127.0.0.1:14000` cho TiDB) hoặc **MongoDB Compass / `mongosh`** (`mongodb://127.0.0.1:27018/?directConnection=true`).

---

### D.5.3. Kịch bản kiểm chứng trực quan cơ chế đổi lược đồ

Bên cạnh 159 lượt đo tự động dưới tải ở Mục D.2–D.4 (tái lập qua bộ script `scripts/run-2.4-*.sh` và `scripts/plot-2.4.py` tại `https://github.com/cuongpluss11/DBMS`), nhóm xây dựng bộ kịch bản thu gọn trên cơ sở dữ liệu độc lập `demo_ose` (Docker Compose cục bộ) nhằm kiểm chứng trực tiếp ở mức câu lệnh bốn cơ chế cốt lõi của quá trình đổi lược đồ như tổng hợp tại **Bảng D.6**.

**Bảng D.6:** *Tổng hợp bốn kịch bản kiểm chứng trực quan cơ chế đổi lược đồ trên MySQL, TiDB và MongoDB.*

| Mã | Hệ DBMS & Thao tác thực hiện | Kết quả quan sát thực tế | Cơ chế được chứng minh |
| :---: | --- | --- | --- |
| **D1** | **MySQL 8.4.8:** Mở 1 phiên đọc chưa `COMMIT`, phát `ALTER TABLE ... ALGORITHM=INSTANT` ở phiên 2, chạy `SELECT` ở phiên 3; sau đó lặp lại với `lock_wait_timeout = 3`. | Khi mặc định: `metadata_locks` ghi nhận `EXCLUSIVE (PENDING)` chặn dây chuyền cả `SELECT` mới. Khi đặt `timeout = 3`: `ALTER` tự hủy sau `3 s` (`Error 1205`), phiên `SELECT` đọc bình thường. | Bẫy hàng đợi *Metadata Lock* trên MySQL và cơ chế giải phóng hàng đợi bằng `lock_wait_timeout` ngắn. |
| **D2** | **TiDB v8.5.7:** Mở 1 phiên đọc chưa `COMMIT`, phát `ALTER TABLE ... ADD COLUMN` ở phiên 2, đồng thời chạy `SELECT` và `INSERT` ở phiên 3. | Phiên 2 tự đợi phiên 1 kết thúc, nhưng phiên 3 vẫn đọc và chèn dòng mới thành công tức thì; sau khi phiên 1 `COMMIT`, `ADMIN SHOW DDL JOBS` báo `synced`. | Cơ chế *Online DDL* đa phiên bản phối hợp với giao dịch đang mở mà không chặn giao dịch mới. |
| **D3** | **MySQL / TiDB:** Chèn đơn mới (`MIGRATED`), chạy `UPDATE` có điều kiện cho 1 đơn cũ (*Lazy*, lặp 2 lần), quét dải khóa chính (*Batch*) và chạy SQL đối soát. | Đơn mới và đơn cũ cùng tồn tại hợp lệ; chạy lặp lần 2 trả về `0 rows affected`; sau bước *Batch*, toàn bộ dòng đạt `MIGRATED` và `invalid_rows = 0`. | Tính tương thích hai phiên bản, tính lũy đẳng (*idempotent*) của điều kiện `UNMIGRATED` và bảo toàn công thức chiết khấu. |
| **D4** | **MongoDB 8.0.20:** Chèn tài liệu mới có sẵn `ol_discount` vào collection cũ, tạo chỉ mục phụ, chạy `bulkWrite` có điều kiện và kiểm đếm. | Tài liệu cũ (thiếu trường) và tài liệu mới cùng tồn tại không cần `ALTER`; sau `bulkWrite`, `unmigrated = 0` và mọi tài liệu khớp giá trị chiết khấu. | Tính linh hoạt của lược đồ BSON (*Flexible Schema*) và khả năng cập nhật bổ sung trường có điều kiện. |

#### Chuẩn bị dữ liệu mẫu dùng chung cho MySQL và TiDB (`demo_ose`)

Khởi tạo bảng `item` (3 mức giá đại diện cho 3 bậc chiết khấu `10%`, `5%`, `0%`) và bảng `order_line` ở lược đồ gốc (3 dòng đơn cũ chưa có `ol_discount` và `ol_mig_state`):

```sql
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

#### 1. Kịch bản D1 — Hiện tượng kẹt Metadata Lock và giải pháp `lock_wait_timeout = 3` (MySQL 8.4.8)

Thực hiện trên **4 kết nối độc lập** trong MySQL Workbench:
1. **Kết nối 1 (phiên đọc giữ mở):** Chạy `USE demo_ose; BEGIN; SELECT * FROM order_line LIMIT 1;` và giữ nguyên chưa `COMMIT`.
2. **Kết nối 2 (phát DDL mặc định):**
   ```sql
   USE demo_ose;
   ALTER TABLE order_line
     ADD COLUMN ol_discount BIGINT NULL,
     ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED',
     ALGORITHM=INSTANT;
   ```
3. **Kết nối 3 (giao dịch mới đến sau):** Chạy `USE demo_ose; SELECT * FROM order_line WHERE ol_o_id = 1001;` → bị treo chờ cùng Kết nối 2 dù chỉ là truy vấn đọc.
4. **Kết nối 4 (kiểm tra hàng đợi khóa siêu dữ liệu):**
   ```sql
   SELECT OBJECT_NAME, LOCK_TYPE, LOCK_STATUS, OWNER_THREAD_ID
   FROM performance_schema.metadata_locks
   WHERE OBJECT_SCHEMA = 'demo_ose' AND OBJECT_NAME = 'order_line';
   ```
   Kết quả trả về xác nhận chuỗi chặn: Kết nối 1 giữ `SHARED_READ (GRANTED)` → Kết nối 2 chờ `EXCLUSIVE (PENDING)` → Kết nối 3 bị chặn phía sau ở `SHARED_READ (PENDING)`.
5. **Kiểm chứng giải pháp bảo vệ:** Hủy lệnh ở Kết nối 2, giữ nguyên Kết nối 1 đang mở, chạy lại ở Kết nối 2 kèm `SET SESSION lock_wait_timeout = 3;` phía trước câu `ALTER TABLE`. Sau đúng `3 s`, Kết nối 2 tự dừng với lỗi `Error 1205 (Lock wait timeout exceeded)` và giải phóng hàng đợi để Kết nối 3 trả kết quả `SELECT` tức thì. Cuối cùng, chạy `COMMIT;` ở Kết nối 1 rồi chạy lại `ALTER TABLE` ở Kết nối 2 để hoàn tất thêm cột trong `~0,01 s`.

#### 2. Kịch bản D2 — Online DDL không chặn giao dịch mới (TiDB v8.5.7)

Sau khi nạp cùng bộ dữ liệu mẫu `demo_ose` trên TiDB, mở **3 kết nối độc lập**:
1. **Kết nối 1:** Chạy `USE demo_ose; BEGIN; SELECT * FROM order_line LIMIT 1;` *(chưa `COMMIT`)*.
2. **Kết nối 2:** Chạy lệnh `ALTER TABLE order_line ADD COLUMN ol_discount BIGINT NULL, ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';` *(đứng đợi Kết nối 1 kết thúc phiên đọc cũ)*.
3. **Kết nối 3 (đọc/ghi đồng thời khi Kết nối 2 đang đợi):**
   ```sql
   USE demo_ose;
   SELECT * FROM order_line WHERE ol_o_id = 1001;
   INSERT INTO order_line VALUES (1, 1, 3001, 1, 1, 1);
   ```
   Khác với MySQL, cả hai lệnh đọc và ghi ở Kết nối 3 đều hoàn thành ngay lập tức (`0 s` đóng băng). Khi chạy `COMMIT;` ở Kết nối 1, lệnh DDL ở Kết nối 2 hoàn tất; kiểm tra `ADMIN SHOW DDL JOBS 5;` ghi nhận trạng thái `synced` và `DESC order_line;` hiển thị đầy đủ hai cột mới. *(Xóa dòng thử `DELETE FROM order_line WHERE ol_o_id = 3001;` trước khi sang D3).*

#### 3. Kịch bản D3 — Chuyển đổi *Lazy*, *Batch*, tính lũy đẳng và đối soát trên SQL (MySQL / TiDB)

Thực hiện tuần tự trên bảng `order_line` đã mở rộng cột:

```sql
USE demo_ose;

-- (1) Đơn hàng mới (ol_o_id > 3000) ghi sẵn chiết khấu và trạng thái MIGRATED
INSERT INTO order_line VALUES (1, 1, 3002, 1, 1, 2, 1200, 'MIGRATED');

-- (2) Chuyển lười (Lazy): khách xem đơn cũ 1001 -> chỉ cập nhật có điều kiện đơn 1001
UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id
SET ol.ol_discount = (ol.ol_quantity * i.i_price *
      CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100,
    ol.ol_mig_state = 'MIGRATED'
WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id = 1001
  AND ol.ol_mig_state = 'UNMIGRATED';
-- Lần 1: 1 row affected; chạy lại đúng lệnh trên lần 2: 0 rows affected (chứng minh tính lũy đẳng)

-- (3) Chuyển theo lô nền (Batch): quét dải khóa chính chuyển nốt đơn 1002, 1003 còn UNMIGRATED
UPDATE order_line ol JOIN item i ON i.i_id = ol.ol_i_id
SET ol.ol_discount = (ol.ol_quantity * i.i_price *
      CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100,
    ol.ol_mig_state = 'MIGRATED'
WHERE ol.ol_w_id = 1 AND ol.ol_d_id = 1 AND ol.ol_o_id BETWEEN 1001 AND 3000
  AND ol.ol_mig_state = 'UNMIGRATED';

-- (4) Kiểm tra dữ liệu cuối cùng và đối soát công thức (invalid_rows = 0 là hợp lệ)
SELECT * FROM order_line ORDER BY ol_o_id;
SELECT COUNT(*) AS invalid_rows FROM order_line ol JOIN item i ON i.i_id = ol.ol_i_id
WHERE ol.ol_mig_state <> 'MIGRATED' OR ol.ol_discount IS NULL
   OR ol.ol_discount <> (ol.ol_quantity * i.i_price *
      CASE WHEN i.i_price >= 5000 THEN 10 WHEN i.i_price >= 2500 THEN 5 ELSE 0 END) DIV 100;
```

Kết quả cuối cùng ghi nhận cả 4 dòng (`1001`, `1002`, `1003`, `3002`) đều mang trạng thái `'MIGRATED'` với `ol_discount` lần lượt bằng `1200, 450, 0, 1200` và `invalid_rows = 0`.

#### 4. Kịch bản D4 — Lược đồ linh hoạt và cập nhật bổ sung trường trên MongoDB 8.0.20

Thực hiện trong cửa sổ `mongosh` trên MongoDB Compass:

```javascript
db = db.getSiblingDB("demo_ose");
db.item.drop(); db.order_line.drop();
db.item.insertMany([{ i_id: 1, i_price: 6000 }, { i_id: 2, i_price: 3000 }]);
db.order_line.insertMany([
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
]);

// (1) Đơn mới ghi thẳng 2 trường mới mà không cần lệnh DDL thay đổi cấu trúc
db.order_line.insertOne({
  ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
  ol_discount: 1200, ol_mig_state: "MIGRATED"
});
db.order_line.createIndex({ ol_w_id: 1, ol_i_id: 1 }, { name: "idx_ol_w_i" });

// (2) Cập nhật có điều kiện các tài liệu cũ chưa có trạng thái MIGRATED qua bulkWrite
const prices = { 1: 6000, 2: 3000 };
const calc = (q, id) => Math.floor(q * prices[id] * (prices[id] >= 5000 ? 10 : 5) / 100);
const ops = db.order_line.find({ ol_mig_state: { $ne: "MIGRATED" } }).toArray().map(d => ({
  updateOne: {
    filter: { _id: d._id, ol_mig_state: { $ne: "MIGRATED" } },
    update: { $set: { ol_discount: calc(d.ol_quantity, d.ol_i_id), ol_mig_state: "MIGRATED" } }
  }
}));
db.order_line.bulkWrite(ops, { ordered: false, writeConcern: { w: "majority", j: true } });

// (3) Kiểm tra trạng thái dữ liệu cuối cùng (unmigrated = 0)
printjson({
  unmigrated: db.order_line.countDocuments({ ol_mig_state: { $ne: "MIGRATED" } }),
  docs: db.order_line.find({}, { _id: 0, ol_o_id: 1, ol_discount: 1, ol_mig_state: 1 }).toArray()
});
```

Kết quả quan sát trên Compass cho thấy ở bước (1), tài liệu cũ chưa có trường `ol_discount` và tài liệu mới `3001` cùng tồn tại hợp lệ trong một collection *(minh họa tính linh hoạt của lược đồ BSON; tác động tranh chấp đồng thời dưới tải được đo riêng ở Mục D.2–D.4)*. Sau bước (2)–(3), kết quả in ra `unmigrated: 0` và cả ba tài liệu (`1001`, `1002`, `3001`) đều mang trạng thái `"MIGRATED"` với `ol_discount` tương ứng `1200, 450, 1200`.
