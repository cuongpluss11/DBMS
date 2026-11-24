# Hướng dẫn Demo UI & Terminal – Các phần còn lại của Phần 2 (Mục 2.2 – 2.5)

Tài liệu này bổ sung kịch bản demo trực quan (**Docker Desktop local trên Windows**) cho các phần còn lại của **Phần 2** trong báo cáo Nhóm 16 (bên cạnh [demo-ui-1.4.md](demo-ui-1.4.md) cho Mục 1.4 và [demo-ui-2.6.md](demo-ui-2.6.md) cho Mục 2.6):

| Mục báo cáo | Nội dung demo | Hình thức | Thời gian |
| --- | --- | --- | --- |
| **2.2 & 2.3.1** | Mất cập nhật (**P0 Lost Update**) vs Khóa dòng (**P1**) & bảng chờ khóa `data_lock_waits` | **UI (MySQL Workbench)** | ~2 phút |
| **2.3.2** | Fault injection — giết tiến trình giữa `COMMIT` + chống trùng bằng `request_id` (`UNIQUE`) | **Terminal (`pytest`)** + UI kiểm tra | ~1 phút |
| **2.4** | Chia tồn kho thành `N` slot (**P2**), cấp mã theo lô, và cơ chế `FOR UPDATE NOWAIT` (T4) | **UI (Workbench)** + **Terminal (`flashsale smoke`)** | ~2 phút |
| **2.5** | TiDB phân tán: tách Region (`SPLIT TABLE`), xem phân bố trên **3 TiKV** & **TiDB Dashboard** | **UI (Workbench + TiDB Dashboard)** | ~1,5 phút |

> **Lưu ý quan trọng khi dùng MySQL Workbench:** Mọi kịch bản cần 2–3 giao dịch chạy đồng thời **bắt buộc mở nhiều tab kết nối độc lập** từ màn hình **Home (🏠)** (tạo `MySQL_demo_btl (1)`, `(2)`, `(3)`), **không** dùng nhiều tab `SQL File` con bên trong cùng 1 tab kết nối.

---

## 1. Demo Mục 2.2 & 2.3.1 (UI MySQL Workbench) — Lost Update (P0) & Hàng chờ khóa dòng (P1)

**Bật MySQL local:**
```powershell
docker compose -f docker/compose.mysql.yml up -d
```
Mở **3 tab kết nối độc lập** tới MySQL `127.0.0.1:13306` (`root`, mật khẩu trống).

### Bước 1.1: Tạo dữ liệu mẫu `demo_lock` (chạy ở Kết nối 1)
```sql
CREATE DATABASE IF NOT EXISTS demo_lock;
USE demo_lock;

DROP TABLE IF EXISTS stock;
CREATE TABLE stock (
  s_w_id INT NOT NULL,
  s_i_id INT NOT NULL,
  s_quantity INT NOT NULL,
  PRIMARY KEY (s_w_id, s_i_id)
);

INSERT INTO stock (s_w_id, s_i_id, s_quantity) VALUES (1, 101, 5);
SELECT * FROM stock;
```

### Bước 1.2: Chứng minh **P0 (Đọc rồi ghi) gây Mất cập nhật / Oversell** trên 2 kết nối
*(Kịch bản: Kho còn 5 cái; Khách 1 và Khách 2 cùng mua 3 cái → tổng mua 6 cái > 5 cái!)*

1. **Kết nối (1):** Đọc tồn kho thấy `s_quantity = 5`, ứng dụng tính `5 - 3 = 2`:
   ```sql
   USE demo_lock;
   BEGIN;
   SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 101; -- Thấy 5
   ```
2. **Kết nối (2):** Cũng đọc tồn kho (MVCC đọc không chờ) → **cũng thấy `s_quantity = 5`**, ứng dụng cũng tính `5 - 3 = 2`:
   ```sql
   USE demo_lock;
   BEGIN;
   SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 101; -- Cũng thấy 5!
   ```
3. **Kết nối (1):** Ghi giá trị đã tính (`2`) rồi `COMMIT`:
   ```sql
   UPDATE stock SET s_quantity = 2 WHERE s_w_id = 1 AND s_i_id = 101;
   COMMIT;
   ```
4. **Kết nối (2):** Ghi đè giá trị đã tính (`2`) rồi `COMMIT`:
   ```sql
   UPDATE stock SET s_quantity = 2 WHERE s_w_id = 1 AND s_i_id = 101;
   COMMIT;
   SELECT * FROM stock;
   ```
→ **Chỉ cho hội đồng thấy:** Hai khách đã chốt mua tổng **6 sản phẩm**, nhưng kho chỉ giảm từ `5 → 2` (chỉ giảm 3) → **vi phạm Luật 2 (INV2: Lost Update / bán vượt)!**

### Bước 1.3: Chứng minh **P1 (Cập nhật có điều kiện) an toàn + Hàng chờ khóa dòng**
1. Đặt lại tồn kho về `5` ở **Kết nối (1)**:
   ```sql
   USE demo_lock;
   UPDATE stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;
   ```
2. **Kết nối (1):** Bắt đầu giao dịch trừ 3 cái (chưa `COMMIT`, đang giữ khóa X trên dòng `(1, 101)`):
   ```sql
   USE demo_lock;
   BEGIN;
   UPDATE stock SET s_quantity = s_quantity - 3
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;
   -- Updated Rows = 1 (tồn tạm = 2, chưa COMMIT)
   ```
3. **Kết nối (2):** Cố gắng trừ thêm 3 cái trên đúng món hot `(1, 101)`:
   ```sql
   USE demo_lock;
   BEGIN;
   UPDATE stock SET s_quantity = s_quantity - 3
   WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;
   ```
   → **Quan sát UI:** Kết nối (2) lập tức **quay vòng `Running...`** (bị xếp hàng chờ khóa dòng của Kết nối 1 — đây chính là nguyên nhân MySQL tốn 97% thời gian chờ khóa trong Mục 2.2!).
4. **Kết nối (3):** Chạy câu lệnh quan sát khóa trong báo cáo (Mục 1.5):
   ```sql
   SELECT
     r.trx_id AS waiting_trx,
     b.trx_id AS blocking_trx,
     w.REQUESTING_ENGINE_LOCK_ID,
     w.BLOCKING_ENGINE_LOCK_ID
   FROM performance_schema.data_lock_waits w
   JOIN information_schema.innodb_trx r ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID
   JOIN information_schema.innodb_trx b ON b.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID;
   ```
   → **Chụp/trình chiếu:** Thấy rõ cặp `waiting_trx` đang bị chặn bởi `blocking_trx`!
5. Quay lại **Kết nối (1)** bấm `COMMIT;` → lập tức **Kết nối (2)** chạy xong và trả về **`0 row(s) affected`** (vì tồn chỉ còn `2 < 3`) → **không bán vượt, không âm kho!** Chạy `ROLLBACK;` ở Kết nối (2) để kết thúc.

---

## 2. Demo Mục 2.3.2 (Terminal) — Kiểm chứng Fault Injection & Idempotency

Vì lỗi *chết tiến trình đúng cửa sổ "đã commit, chưa kịp trả phản hồi"* xảy ra ở mức mili-giây, ta demo bằng bộ test tích hợp đã viết sẵn trên **PowerShell (`e:\BTL-DBMS`)**:

```powershell
# Chạy bộ test fault injection (giả lập chết trước commit, chết sau commit mất phản hồi, và đối chứng âm)
python -m pytest tests/test_fault_injection.py -v
```

Nếu muốn demo nhanh quy tắc chống trùng **`UNIQUE (request_id)`** trực tiếp trên **UI MySQL Workbench**:
```sql
USE demo_lock;
DROP TABLE IF EXISTS orders_idem;
CREATE TABLE orders_idem (
  o_id INT AUTO_INCREMENT PRIMARY KEY,
  request_id VARCHAR(64) NOT NULL UNIQUE,
  qty INT NOT NULL
);

-- Lần gửi 1: thành công
INSERT INTO orders_idem (request_id, qty) VALUES ('req-flashsale-001', 2);

-- Lần gửi 2 (retry cùng request_id do mất mạng sau commit): bị DBMS chặn ngay bằng lỗi 1062 Duplicate entry!
INSERT INTO orders_idem (request_id, qty) VALUES ('req-flashsale-001', 2);
```

---

## 3. Demo Mục 2.4 (UI + Terminal) — Chia tồn kho `N` slot (P2) & `FOR UPDATE NOWAIT` (T4)

### Bước 3.1: Demo UI ý tưởng Chia tồn kho `N` slot (P2) & `FOR UPDATE NOWAIT` (T4)
1. **Minh họa `FOR UPDATE NOWAIT` (T4 trên MySQL Workbench):**
   - **Kết nối (1):** `USE demo_lock; BEGIN; SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101 FOR UPDATE;` *(giữ khóa)*
   - **Kết nối (2):**
     ```sql
     USE demo_lock;
     SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101 FOR UPDATE NOWAIT;
     ```
     → Thay vì quay vòng chờ khóa như Bước 1.3, Kết nối (2) **báo lỗi ngay tức thì** (`Error 3572: Statement aborted because lock(s) could not be acquired immediately and NOWAIT is set`) để ứng dụng thử lại sau backoff!
   - Nhớ chạy `ROLLBACK;` ở Kết nối (1) sau khi xong.

2. **Minh họa bảng `stock_slot` (P2 chia 1 món hot thành `N` dòng con):**
   ```sql
   USE demo_lock;
   DROP TABLE IF EXISTS stock_slot;
   CREATE TABLE stock_slot (
     ss_w_id INT NOT NULL,
     ss_i_id INT NOT NULL,
     ss_slot INT NOT NULL,
     ss_quantity INT NOT NULL,
     PRIMARY KEY (ss_w_id, ss_i_id, ss_slot)
   );

   -- Món hot còn 900 cái -> chia thành N=3 slot, mỗi slot 300 cái (3 giao dịch có thể trừ song song 3 dòng khác nhau!)
   INSERT INTO stock_slot VALUES (1, 101, 0, 300), (1, 101, 1, 300), (1, 101, 2, 300);
   SELECT *, (SELECT SUM(ss_quantity) FROM stock_slot WHERE ss_w_id=1 AND ss_i_id=101) AS total_stock
   FROM stock_slot;
   ```

### Bước 3.2: Demo Terminal chạy benchmark thật thu gọn (`flashsale smoke`, ~15 giây)
Nếu giảng viên muốn xem công cụ benchmark thật tự sinh tải, chạy P2 chia slot và tự động kiểm tra 3 luật tồn kho (`VALID`):
```powershell
# Chạy nhanh smoke test trên MySQL (tự nạp dataset nhỏ, chạy tải, tự đối soát 3 luật rồi dọn sạch)
flashsale smoke mysql --variant p2 --slots 9 --order-id-batch 50
```
→ Trong JSON đầu ra, chỉ trực tiếp 3 trường:
- `"tps"` và `"p99_ms"` (hiệu năng thực đo)
- `"validation": { "status": "VALID", "rules": { "nonnegative": true, "reconciliation": true, "idempotency": true } }`

---

## 4. Demo Mục 2.5 (UI Workbench + TiDB Dashboard) — Phân vùng Region & 3 nút TiKV

Dừng MySQL và bật TiDB local:
```powershell
docker compose -f docker/compose.mysql.yml stop
docker compose -f docker/compose.tidb.yml up -d
```

1. **Mở TiDB Dashboard trên trình duyệt:** `http://127.0.0.1:12379/dashboard` (`root`, mật khẩu trống)
   - Vào **Cluster Info → Instances**: chỉ rõ cụm phân tán gồm **1 PD + 1 TiDB Server + 3 TiKV** (`tikv1`, `tikv2`, `tikv3`).
2. **Mở MySQL Workbench kết nối `TiDB_Local` (`127.0.0.1:14000`)** và chạy kịch bản tách Region chủ động (`SPLIT TABLE`) giống Mục 2.5:
   ```sql
   CREATE DATABASE IF NOT EXISTS demo_scale;
   USE demo_scale;

   DROP TABLE IF EXISTS stock_slot;
   CREATE TABLE stock_slot (
     ss_w_id INT NOT NULL,
     ss_i_id INT NOT NULL,
     ss_slot INT NOT NULL,
     ss_quantity INT NOT NULL,
     PRIMARY KEY (ss_w_id, ss_i_id, ss_slot)
   );

   INSERT INTO stock_slot VALUES
     (1, 101, 0, 100), (1, 101, 1, 100), (1, 101, 2, 100),
     (1, 101, 3, 100), (1, 101, 4, 100), (1, 101, 5, 100);

   -- Trước khi SPLIT: toàn bộ món hot nằm gọn trong 1 Region duy nhất (1 TiKV gánh hết!)
   SHOW TABLE stock_slot REGIONS;

   -- Tách chủ động thành các Region riêng theo từng slot (cơ chế dùng ở Nhóm C của Mục 2.5)
   SPLIT TABLE stock_slot BY (1, 101, 2), (1, 101, 4);

   -- Sau khi SPLIT: thấy bảng đã tách thành nhiều Region có REGION_ID và LEADER khác nhau
   SHOW TABLE stock_slot REGIONS;
   ```
   → **Điểm nhấn cực mạnh cho câu kết Mục 2.5:** Cho hội đồng thấy trực tiếp trước `SPLIT` chỉ có **1 Region** (một nút TiKV bận 100%, hai nút còn lại ngồi chơi), sau `SPLIT` trên các slot đã tách thành **3 Region** để PD rải leader ra **3 TiKV** — minh họa trực quan cho kết luận *"Thêm máy chỉ có ích sau khi đã phá điểm nóng"*!

---

## 5. Kịch bản tổng hợp 5 phút cho buổi bảo vệ (khuyên dùng)

| Thời lượng | Bước demo | Công cụ | Thông điệp chốt với hội đồng |
| --- | --- | --- | --- |
| **0:00 – 1:15** | Mục 2.2 / 2.3.1: **P0 Lost Update** (2 tab) → **P1 Khóa dòng** + `data_lock_waits` | MySQL Workbench | Giải thích vì sao P0 bị oversell và vì sao MySQL nghẽn vì hàng chờ khóa dòng. |
| **1:15 – 2:45** | Mục 2.6.1: **Kẹt Metadata Lock** (4 tab) + `metadata_locks` → hóa giải bằng `lock_wait_timeout = 3` | MySQL Workbench | Điểm nhấn ấn tượng nhất: 1 câu `SELECT` chưa chốt treo cả bảng 57s → giảm còn 2s. |
| **2:45 – 3:45** | Mục 1.4 & 2.5: **3 TiKV Dashboard** + `SPLIT TABLE` / `SHOW TABLE REGIONS` + **TiDB Online DDL không treo** | TiDB Dashboard + Workbench | Minh họa kiến trúc phân tán NewSQL và lý do TiDB không bị kẹt MDL như MySQL. |
| **3:45 – 4:30** | Mục 1.4 & 2.6: **MongoDB Compass** (`modifiedCount: 0` chống âm kho + Transaction `ABORT` + schemaless) | MongoDB Compass | Minh họa NoSQL linh hoạt lược đồ nhưng cần Replica Set + xử lý retry khi tranh chấp. |
| **4:30 – 5:00** | *(Tùy chọn nếu GV hỏi)* Chạy `flashsale smoke mysql --variant p2 --slots 9` | PowerShell | Chứng minh toàn bộ hệ thống benchmark tự động chạy & tự đối soát 3 luật **`VALID`**. |

### Dọn dẹp sau khi bảo vệ xong
```powershell
docker compose -f docker/compose.mysql.yml stop
docker compose -f docker/compose.tidb.yml stop
docker compose -f docker/compose.mongo.yml stop
```
