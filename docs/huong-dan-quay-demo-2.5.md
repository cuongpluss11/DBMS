# Hướng dẫn quay chi tiết Video Demo Mục 2.5 (`demo-2.5.mp4`): Tách Region trên cụm 3 TiKV

Tài liệu này hướng dẫn từng thao tác thực tế trên **Windows (Docker Desktop + MySQL Workbench + TiDB Dashboard + Snipping Tool + Clipchamp)** để quay mượt video **`demo-2.5.mp4`** (~35 giây, MP4 1080p, không cần thu tiếng) minh họa cơ chế chia slot tồn kho thành nhiều Region trên cụm **1 PD + 1 TiDB + 3 TiKV**.

> **Lưu ý phạm vi:** Demo chỉ minh họa **cơ chế tách và đặt Region**, **không đo hiệu năng**. Các mức tăng `1,22×` và `3,44×` là số đo chính thức trên AWS trình bày trong slide/báo cáo.

---

## 1. Chuẩn bị môi trường & bố cục màn hình (không quay)

### 1.1. Bật cụm TiDB trên Docker Desktop
1. Mở **Docker Desktop**, đảm bảo RAM cấp cho Docker **≥ 8 GiB** (mỗi nút TiKV dùng ~1,85 GiB khi rảnh). Đóng bớt trình duyệt/ứng dụng nặng.
2. Mở **PowerShell** tại thư mục gốc `e:\BTL-DBMS`, dừng MySQL/MongoDB (nếu đang chạy) và khởi động cụm TiDB:
   ```powershell
   docker compose -f docker/compose.mysql.yml stop
   docker compose -f docker/compose.mongo.yml stop
   docker compose -f docker/compose.tidb.yml up -d
   ```
3. Đợi 1–2 phút rồi kiểm tra cả 5 container đều ở trạng thái `Up`:
   ```powershell
   docker compose -f docker/compose.tidb.yml ps
   ```

### 1.2. Mở và sắp xếp 2 cửa sổ để quay gọn trong 1 khung 16:9
- **Tắt thông báo Windows:** Bật **Do Not Disturb** (góc dưới phải taskbar) để không dính pop-up Zalo/Messenger khi đang quay.
- **Cửa sổ 1 — Trình duyệt (TiDB Dashboard):**
  - Mở `http://127.0.0.1:12379/dashboard`, đăng nhập User `root`, mật khẩu để trống.
  - Mở sẵn **2 tab trình duyệt** trên Dashboard:
    - *Tab trình duyệt 1:* **Cluster Info → Instances** (kiểm tra thấy đủ **PD (1)**, **TiDB (1)**, **TiKV (3)** đều chấm xanh **`Up`** — dùng cho Cảnh 1).
    - *Tab trình duyệt 2:* **Cluster Info → Store Topology** (hiển thị sơ đồ 3 nút `tikv1`, `tikv2`, `tikv3` — dùng để đối chứng trực quan ở Cảnh 4 chỉ bằng 1 cú bấm chuột).
  - Phóng to trình duyệt lên **`110%–125%`** (`Ctrl + +`) cho chữ sắc nét.
- **Cửa sổ 2 — MySQL Workbench:**
  - Kết nối `127.0.0.1`, Port **`14000`**, User `root`, mật khẩu trống (nếu báo cảnh báo phiên bản `8.0.11-TiDB-v8.5.7`, chọn **Continue Anyway**).
  - Phóng to chữ SQL Editor & Result Grid: vào **Edit → Preferences → Fonts & Colors**, tăng cỡ chữ `SQL Editor` và `Resultset Grid` lên **`12–13 pt`**.
  - **Thu gọn panel không cần thiết:** Bấm 2 nút tắt thanh phải (*SQL Additions*) và thanh dưới (*Output*) khi cần để bảng **Result Grid** thật rộng, rõ đủ các cột `REGION_ID`, `START_KEY`, `END_KEY`, `LEADER_STORE_ID`.
- **Mẹo bố cục quay đẹp:** Đặt cả 2 cửa sổ **phóng to cùng kích thước** (chuyển qua lại nhanh bằng `Alt + Tab` hoặc bấm trên thanh Taskbar — hoặc chia đôi màn hình nếu màn hình rộng ≥ 1920×1080). Dùng `Alt + Tab` toàn màn hình sẽ giúp chữ trong Dashboard và bảng Result Grid lớn và dễ đọc nhất trên slide!

---

## 2. Chuẩn bị sẵn 6 Tab SQL trong MySQL Workbench (không gõ lúc quay)

Mở sẵn **6 tab SQL** trong MySQL Workbench và dán từng khối vào từng tab riêng để khi quay chỉ việc **chuyển tab → bấm nút tia sét vàng ⚡** (hoặc `Ctrl + Shift + Enter`):

### Tab 0 — Khởi tạo / Reset dữ liệu (chạy TRƯỚC khi quay)
Chạy lại tab này bất cứ khi nào muốn quay lại từ đầu:
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
```

### Tab 1 — Cảnh 2a: Xem 6 slot tồn kho của 1 mặt hàng
```sql
SELECT * FROM demo_scale.stock_slot ORDER BY ss_slot;
```
- **Kết quả kỳ vọng:** 6 dòng (`ss_slot` từ `0` đến `5`, mỗi slot `100`).

### Tab 2 — Cảnh 2b: Kiểm tra số Region TRƯỚC khi tách
> **Lưu ý kỹ thuật MySQL Workbench:** Lệnh `SHOW TABLE ... REGIONS;` là cú pháp riêng của TiDB nên Workbench thường gạch đỏ cảnh báo cú pháp. Dùng câu truy vấn `information_schema` dưới đây sẽ chạy **mượt 100% không gạch đỏ** và hiển thị gọn đúng các cột cần đối chiếu (`REGION_ID`, `LEADER_STORE_ID`, `START_KEY`, `END_KEY`):
```sql
SELECT DISTINCT
  r.TABLE_NAME,
  r.REGION_ID,
  p.STORE_ID AS LEADER_STORE_ID,
  r.START_KEY,
  r.END_KEY
FROM information_schema.TIKV_REGION_STATUS r
JOIN information_schema.TIKV_REGION_PEERS p
  ON r.REGION_ID = p.REGION_ID AND p.IS_LEADER = 1
WHERE r.DB_NAME = 'demo_scale'
  AND r.TABLE_NAME = 'stock_slot'
  AND r.IS_INDEX = 0
ORDER BY r.START_KEY;
```
*(Nếu chạy thử thấy `SHOW TABLE demo_scale.stock_slot REGIONS;` vẫn chạy được và bạn thích bảng gọn của nó thì có thể dùng thay thế; nếu không thì giữ nguyên câu `SELECT` trên).*
- **Kết quả kỳ vọng:** Đúng **1 dòng Region** duy nhất chứa toàn bộ 6 slot.

### Tab 3 — Cảnh 3a: Tách Region theo ranh giới slot (`SPLIT TABLE`)
```sql
SPLIT TABLE demo_scale.stock_slot BY (1, 101, 2), (1, 101, 4);
```
- **Lưu ý:** Nếu Workbench hiện gạch đỏ ở chữ `SPLIT`, cứ **bấm nút tia sét vàng ⚡** (Workbench vẫn gửi lệnh sang TiDB Server bình thường và trả về `TOTAL_SPLIT_REGION = 2, SCATTER_FINISH_RATIO = 1`).
- *(Phòng hờ: nếu Workbench từ chối chạy câu lệnh có gạch đỏ, chạy nhanh qua PowerShell: `python -c "import pymysql; c=pymysql.connect(host='127.0.0.1',port=14000,user='root'); cur=c.cursor(); cur.execute('SPLIT TABLE demo_scale.stock_slot BY (1,101,2),(1,101,4)'); print(cur.fetchall())"`).*

### Tab 4 — Cảnh 3b: Kiểm tra số Region SAU khi tách
Dán lại y hệt câu lệnh ở **Tab 2**:
```sql
SELECT DISTINCT
  r.TABLE_NAME,
  r.REGION_ID,
  p.STORE_ID AS LEADER_STORE_ID,
  r.START_KEY,
  r.END_KEY
FROM information_schema.TIKV_REGION_STATUS r
JOIN information_schema.TIKV_REGION_PEERS p
  ON r.REGION_ID = p.REGION_ID AND p.IS_LEADER = 1
WHERE r.DB_NAME = 'demo_scale'
  AND r.TABLE_NAME = 'stock_slot'
  AND r.IS_INDEX = 0
ORDER BY r.START_KEY;
```
- **Kết quả kỳ vọng:** Xuất hiện **3 dòng Region** ứng với 3 khoảng khóa (`slot 0–1`, `slot 2–3`, `slot 4–5`).

### Tab 5 — Cảnh 4: Đối chiếu `STORE_ID` với địa chỉ 3 nút TiKV
```sql
SELECT STORE_ID, ADDRESS, STORE_STATE_NAME
FROM information_schema.TIKV_STORE_STATUS
ORDER BY STORE_ID;
```
- **Kết quả kỳ vọng:** 3 dòng ứng với `tikv1:20160`, `tikv2:20160`, `tikv3:20160` và mã `STORE_ID` tương ứng (ví dụ `1`, `4`, `5`).

---

## 3. Chạy thử 1 lần (Dry-run) trước khi bấm quay thật

1. Chạy lần lượt **Tab 0 → Tab 1 → Tab 2 → Tab 3 → Tab 4 → Tab 5**.
2. Kiểm tra 3 điểm:
   - Tab 2 có đúng **1 Region** không?
   - Tab 3 chạy xong báo thành công và Tab 4 có đúng **3 Region** không?
   - Cột `LEADER_STORE_ID` ở Tab 4 đang nằm trên **3 nút khác nhau** hay bị dồn vào cùng 1 nút?
3. **Nếu 3 Leader bị dồn vào cùng 1 nút TiKV (xử lý bằng PD API):**
   - Xem 3 giá trị `REGION_ID` và `LEADER_STORE_ID` hiện tại ở Tab 4, và 3 giá trị `STORE_ID` ở Tab 5.
   - Chạy lệnh PowerShell sau để chuyển 2 Region sang 2 nút TiKV còn lại (thay đúng số của máy bạn):
     ```powershell
     Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:12379/pd/api/v1/operators' -ContentType 'application/json' -Body '{"name":"transfer-peer","region_id":<REGION_ID_2>,"from_store_id":<STORE_CU>,"to_store_id":<STORE_MOI_2>}'
     Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:12379/pd/api/v1/operators' -ContentType 'application/json' -Body '{"name":"transfer-peer","region_id":<REGION_ID_3>,"from_store_id":<STORE_CU>,"to_store_id":<STORE_MOI_3>}'
     ```
   - Chạy lại **Tab 4** ngay lập tức để kiểm tra 3 `LEADER_STORE_ID` đã tách sang 3 nút khác nhau.
   - **Mẹo quay nếu cần dùng `transfer-peer`:** Cứ quay liền mạch từ Cảnh 1 → Cảnh 3, đến lúc chạy Tab 4 mà thấy Leader trùng nhau thì tạm dừng thao tác (không tắt quay), chuyển sang PowerShell chạy `transfer-peer`, quay lại bấm chạy lại Tab 4 rồi chạy Tab 5; sau đó vào **Clipchamp cắt bỏ đoạn chạy PowerShell chờ đợi** và ghi phụ đề `Đặt leader bằng PD API` (hoặc giữ nguyên cảnh gõ lệnh nếu muốn minh họa trực tiếp). Nếu vẫn không rải được, giữ nguyên kết quả thật và **không nói rằng tải đã được rải đều**.
4. **Reset sạch trước khi bấm quay thật:** Chạy lại **Tab 0**, xóa kết quả cũ (đóng các khung Result Grid đang mở ở Tab 1–5 nếu muốn nhìn thật mới), rồi chuyển về màn hình **TiDB Dashboard → Instances**.

---

## 4. Thao tác quay từng giây bằng Snipping Tool (`Win + Shift + R`)

1. Nhấn tổ hợp **`Win + Shift + R`** để mở trình quay màn hình của Snipping Tool.
2. Kéo khung chọn vùng quay **16:9** bao trọn cửa sổ làm việc (bỏ thanh Taskbar Windows phía dưới cho chuyên nghiệp).
3. Kiểm tra biểu tượng micro đang **tắt** (không cần thu tiếng), bấm **Start** (đếm ngược 3-2-1).

| Cảnh | Thời lượng mục tiêu | Thao tác tay trên màn hình | Dừng mắt (nhịp chậm) | Phụ đề sẽ gắn ở Clipchamp | Lời thuyết trình khi chiếu slide |
| --- | :---: | --- | --- | --- | --- |
| **Cảnh 1** | `0:00 – 0:08` | Đang ở **TiDB Dashboard → Instances**. Rê con trỏ chuột chậm lần lượt qua dòng **PD (1)**, **TiDB (1)** và 3 dòng **TiKV (3)** đang `Up`. | Dừng 2 giây cuối | `Cụm TiDB: 1 PD, 1 TiDB, 3 TiKV` | *"Cụm minh họa gồm 1 PD, 1 TiDB và 3 TiKV."* |
| **Cảnh 2** | `0:08 – 0:18` | Chuyển sang **MySQL Workbench**.<br>• Bấm **Tab 1** → nhấn ⚡ (hiện 6 dòng slot `0..5`).<br>• Bấm **Tab 2** → nhấn ⚡ (hiện đúng **1 dòng Region**). Rê chuột nhẹ qua dòng `REGION_ID`. | Dừng 2–3 giây ở mỗi bảng kết quả | `1 mặt hàng, 6 slot, 1 Region` | *"Một mặt hàng được chia thành 6 slot, ban đầu nằm chung một Region."* |
| **Cảnh 3** | `0:18 – 0:28` | • Bấm **Tab 3** → nhấn ⚡ chạy `SPLIT TABLE ... BY (1,101,2), (1,101,4)`.<br>• Bấm **Tab 4** → nhấn ⚡ (hiện **3 dòng Region**). Rê chuột dọc qua 3 dòng `REGION_ID` và cột `LEADER_STORE_ID`. | Dừng 3 giây ở bảng 3 Region | `SPLIT TABLE: tách theo slot` *(thêm `Đặt leader bằng PD API` nếu có chạy bước 4.1)* | *"Tách bảng theo slot thành nhiều Region."* |
| **Cảnh 4** | `0:28 – 0:38` | • Ở Workbench, bấm **Tab 5** → nhấn ⚡ chạy `TIKV_STORE_STATUS` (hiện 3 `STORE_ID` ứng với `tikv1`, `tikv2`, `tikv3`).<br>• Chuyển nhanh sang **Trình duyệt → Tab 2 (`Cluster Info → Store Topology`)**, rê chuột qua 3 nút TiKV để đối chứng trực quan vị trí các Store tương ứng với `LEADER_STORE_ID` vừa tách ở Workbench. | Dừng 2 giây ở Tab 5 + 3 giây ở Store Topology rồi bấm **Stop** | `Đối chứng Store Topology — Hiệu năng: xem số đo trên AWS` | *"Đối chiếu mã Store với 3 nút TiKV trên Dashboard. Đây là minh họa cơ chế đặt dữ liệu; hiệu năng được đo riêng trên AWS."* |

4. Bấm **Stop** (nút đỏ trên thanh trên cùng) → lưu file thô vào máy (ví dụ `demo-2.5-raw.mp4`).
5. **Chụp ngay 2 ảnh minh chứng** trước khi đóng Workbench:
   - Ảnh 1: Màn hình kết quả **Tab 4** (3 dòng Region sau khi tách).
   - Ảnh 2: Màn hình kết quả **Tab 5** (bảng ánh xạ `STORE_ID` ↔ `tikv1/2/3`).

---

## 5. Hậu kỳ nhanh trong Microsoft Clipchamp (~5 phút)

1. Mở **Microsoft Clipchamp** → **Create a new video** → kéo `demo-2.5-raw.mp4` vào thanh Timeline.
2. **Cắt đoạn thừa cho gọn ~35 giây:**
   - Đưa vạch thời gian tới đầu/cuối các đoạn chờ hoặc lúc di chuột thừa → bấm phím **`S`** để tách đoạn → chọn đoạn thừa bấm **`Delete`**.
   - Nếu đoạn chuyển tab hơi lâu, chọn đoạn đó → mục **Speed** bên phải kéo lên `1.5×–2×`.
   - Nếu có âm thanh nền lọt vào, bấm biểu tượng loa trên clip để **Mute**.
3. **Thêm 2 lớp chữ (Text → Plain text hoặc Lower third):**
   - **Dòng cố định suốt video (góc trên phải hoặc dưới phải, cỡ nhỏ vừa đọc, nền mờ):**
     `Demo quy mô nhỏ trên Docker, không phải số đo chính thức`
   - **Phụ đề từng cảnh (căn dưới giữa, nền hộp đen mờ chữ trắng):**
     - `0:00 – 0:08`: `Cụm TiDB: 1 PD, 1 TiDB, 3 TiKV`
     - `0:08 – 0:18`: `1 mặt hàng, 6 slot, 1 Region`
     - `0:18 – 0:28`: `SPLIT TABLE: tách theo slot` *(hoặc `SPLIT TABLE + đặt leader bằng PD API` nếu có dùng `transfer-peer`)*
     - `0:28 – 0:38`: `Đối chứng Store Topology — Hiệu năng: xem số đo trên AWS`
4. **Xuất video:** Bấm **Export → 1080p HD** → lưu đúng tên **`demo-2.5.mp4`**. Xem lại 1 lượt kiểm tra chữ có rõ và tổng thời lượng có quanh `~35 giây` không.

---

## 6. Dọn dẹp & Checklist bàn giao

### 6.1. Dọn dẹp sau khi đã lưu video và 2 ảnh chụp
Trong MySQL Workbench:
```sql
DROP DATABASE IF EXISTS demo_scale;
```
Trong PowerShell (`e:\BTL-DBMS`):
```powershell
docker compose -f docker/compose.tidb.yml stop
```

### 6.2. Checklist gửi lại nhóm (trong ngày 27/11)
- [ ] File video **`demo-2.5.mp4`** (MP4 1080p, ~35 giây, có đủ phụ đề 4 cảnh + dòng chú thích cố định ở góc).
- [ ] **2 ảnh chụp màn hình** kết quả **Tab 4** (3 Region sau `SPLIT TABLE`) và **Tab 5** (`TIKV_STORE_STATUS`).
- [ ] **Ghi chú ngắn** gửi kèm nếu kết quả thực tế khác dự kiến hoặc có dùng lệnh `transfer-peer` của PD API.
