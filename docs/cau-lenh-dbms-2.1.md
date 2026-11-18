# Câu lệnh SQL và MongoDB để trình bày mục 2.1

CLI dùng adapter Python để gửi truy vấn. Các ví dụ dưới đây viết tường minh luồng của một `New-Order` có một món và một `Payment`. Có thể dán vào trình soạn truy vấn SQL hoặc chạy trong `mongosh`. Ví dụ dùng giá trị cố định và rollback để quan sát từng bước. Luồng benchmark đầy đủ có xử lý retry và commit ở [mã giao dịch](../src/flashsale/transactions/core.py).

## 1. Tạo database demo nhỏ

Chạy trên VM của hệ được giao. Đổi `mysql` thành `mongo` hoặc `tidb`. Lấy tên ở trường `database` của kết quả `load` để chọn trong giao diện.

```bash
source .venv/bin/activate
DBMS=mysql
flashsale start "$DBMS"
flashsale load "$DBMS" --config configs/smoke.toml
```

Dùng database mới này cho phần trình bày. Cổng loopback mặc định là `13306` cho MySQL, `14000` cho TiDB và `27018` cho MongoDB. Người dùng SQL của môi trường demo là `root`. Với MongoDB, dùng URI `mongodb://127.0.0.1:27018/?replicaSet=flashsale&directConnection=true`. Đọc `.env` của VM nếu đã đổi cổng. Chạy tất cả câu trong một transaction trên cùng một kết nối. Kết thúc phần demo bằng `flashsale stop "$DBMS"` để giữ volume.

## 2. MySQL và TiDB trong trình soạn SQL

Thay `flashsale_UUID` bằng tên database từ `load`. Chạy các câu đọc để hiện bảng, DDL và chỉ mục. Trong `EXPLAIN`, đối chiếu cột `key` trên MySQL hoặc tên operator trên TiDB. [MySQL SELECT và FOR UPDATE](https://dev.mysql.com/doc/refman/8.4/en/select.html), [TiDB SQL FAQs](https://docs.pingcap.com/tidb/stable/sql-faq/)

```sql
USE flashsale_UUID;
SHOW TABLES;
SHOW CREATE TABLE stock;
SHOW CREATE TABLE orders;
SHOW INDEX FROM orders;

EXPLAIN SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 1 FOR UPDATE;
SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 1;
```

Trên TiDB, chạy thêm các câu sau để thấy thiết lập `history` và Region thực tế.

```sql
SHOW CREATE TABLE history;
SHOW TABLE stock REGIONS;
SHOW TABLE history REGIONS;
```

### New-Order một món

Mở transaction, tra khóa chống trùng, lấy mã đơn và đọc tồn kho. Dataset smoke mới có `d_next_o_id = 11` và `s_quantity = 20` cho các khóa này. Tiếp tục với khối thứ hai khi tra `request_id` trả về rỗng và hai giá trị này đúng. Nếu kết quả khác, chạy `ROLLBACK;` và dùng một dataset demo mới.

```sql
START TRANSACTION;

SELECT * FROM orders WHERE request_id = 'demo-new-order';
SELECT d_next_o_id FROM district WHERE d_w_id = 1 AND d_id = 1 FOR UPDATE;
SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 1 FOR UPDATE;
SELECT i_price FROM item WHERE i_id = 1;
```

Trên cùng kết nối, cấp mã đơn, trừ một đơn vị tồn và ghi đơn. Các câu `SELECT` trước và sau rollback giúp quan sát thay đổi có bị hủy hay không. Nếu trình soạn SQL dừng khi gặp lỗi, chạy `ROLLBACK;` trên kết nối đó. [MySQL START TRANSACTION và ROLLBACK](https://dev.mysql.com/doc/refman/8.4/en/commit.html)

```sql
UPDATE district SET d_next_o_id = d_next_o_id + 1
WHERE d_w_id = 1 AND d_id = 1;

UPDATE stock
SET s_quantity = s_quantity - 1, s_ytd = s_ytd + 1, s_order_cnt = s_order_cnt + 1
WHERE s_w_id = 1 AND s_i_id = 1;

INSERT INTO orders
    (o_w_id, o_d_id, o_id, o_c_id, o_entry_d, o_carrier_id,
     o_ol_cnt, o_all_local, request_id, run_id)
VALUES (1, 1, 11, 1, UTC_TIMESTAMP(), NULL, 1, 1,
        'demo-new-order', '00000000000000000000000000000001');

INSERT INTO new_order (no_w_id, no_d_id, no_o_id, run_id)
VALUES (1, 1, 11, '00000000000000000000000000000001');

INSERT INTO order_line
    (ol_w_id, ol_d_id, ol_o_id, ol_number, ol_i_id, ol_supply_w_id,
     ol_delivery_d, ol_quantity, ol_amount, ol_dist_info, run_id)
SELECT 1, 1, 11, 1, i.i_id, s.s_w_id, NULL, 1, i.i_price, s.s_dist_01,
       '00000000000000000000000000000001'
FROM item AS i JOIN stock AS s ON s.s_i_id = i.i_id
WHERE i.i_id = 1 AND s.s_w_id = 1;

SELECT o_id, request_id FROM orders WHERE request_id = 'demo-new-order';
SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 1;
ROLLBACK;

SELECT o_id, request_id FROM orders WHERE request_id = 'demo-new-order';
SELECT s_quantity FROM stock WHERE s_w_id = 1 AND s_i_id = 1;
```

### Payment

Dữ liệu tiền dùng cent nguyên. Ví dụ trừ `100` vào số dư khách, tăng tổng đã thanh toán và số lượt thanh toán, rồi ghi `history`. Profile chính giữ nguyên YTD của warehouse và district.

```sql
START TRANSACTION;
SELECT * FROM history WHERE request_id = 'demo-payment';

UPDATE customer
SET c_balance = c_balance - 100, c_ytd_payment = c_ytd_payment + 100,
    c_payment_cnt = c_payment_cnt + 1
WHERE c_w_id = 1 AND c_d_id = 1 AND c_id = 1;

INSERT INTO history
    (h_c_w_id, h_c_d_id, h_c_id, h_w_id, h_d_id, h_date, h_amount, h_data, request_id)
VALUES (1, 1, 1, 1, 1, UTC_TIMESTAMP(), 100, 'FLASHSALE', 'demo-payment');

SELECT c_balance, c_ytd_payment, c_payment_cnt
FROM customer WHERE c_w_id = 1 AND c_d_id = 1 AND c_id = 1;
SELECT h_amount, request_id FROM history WHERE request_id = 'demo-payment';
ROLLBACK;
```

## 3. MongoDB trong mongosh

Thay `flashsale_UUID` bằng tên database của MongoDB. Chạy khối này trước để thấy replica set, collection, chỉ mục và kế hoạch truy vấn. [MongoDB 8.0 collection explain](https://www.mongodb.com/docs/v8.0/reference/method/db.collection.explain/)

```javascript
const demo = db.getSiblingDB("flashsale_UUID");
printjson(demo.runCommand({hello: 1}));
printjson(demo.getCollectionNames());
printjson(demo.orders.getIndexes());
printjson(demo.stock.find({s_w_id: 1, s_i_id: 1}).explain("queryPlanner"));
```

### New-Order một món

Các thao tác đều dùng database gắn với cùng session. Khối `finally` hủy transaction để chạy lại demo được. [Session trong mongosh](https://www.mongodb.com/docs/v8.0/reference/method/session/)

```javascript
{
  const session = db.getMongo().startSession();
  const tx = session.getDatabase(demo.getName());
  try {
    session.startTransaction({
      readConcern: {level: "snapshot"},
      writeConcern: {w: "majority"}
    });
    const districtKey = {d_w_id: 1, d_id: 1};
    const stockKey = {s_w_id: 1, s_i_id: 1};
    const requestId = "demo-new-order";
    const runId = "00000000000000000000000000000001";
    if (tx.orders.findOne({request_id: {$eq: requestId, $type: "string"}})) {
      throw new Error("request_id đã có");
    }
    const orderId = tx.district.findOne(districtKey).d_next_o_id;
    tx.district.updateMany(districtKey, {$inc: {d_next_o_id: 1}});
    const stock = tx.stock.findOne(stockKey);
    if (!stock || stock.s_quantity < 1) throw new Error("out_of_stock");
    const item = tx.item.findOne({i_id: 1});
    tx.stock.updateMany(stockKey, {$inc: {s_quantity: -1, s_ytd: 1, s_order_cnt: 1}});

    tx.orders.insertOne({
      o_w_id: 1, o_d_id: 1, o_id: orderId, o_c_id: 1, o_entry_d: new Date(),
      o_carrier_id: null, o_ol_cnt: 1, o_all_local: 1, request_id: requestId, run_id: runId
    });
    tx.new_order.insertOne({no_w_id: 1, no_d_id: 1, no_o_id: orderId, run_id: runId});
    tx.order_line.insertMany([{
      ol_w_id: 1, ol_d_id: 1, ol_o_id: orderId, ol_number: 1, ol_i_id: 1, ol_supply_w_id: 1,
      ol_delivery_d: null, ol_quantity: 1, ol_amount: item.i_price, ol_dist_info: stock.s_dist_01,
      run_id: runId
    }]);
    printjson(tx.orders.findOne({request_id: requestId}));
    printjson(tx.stock.findOne(stockKey, {s_quantity: 1, _id: 0}));
  } finally {
    try { session.abortTransaction(); } finally { session.endSession(); }
  }
  printjson(demo.orders.findOne({request_id: "demo-new-order"}));
  printjson(demo.stock.findOne({s_w_id: 1, s_i_id: 1}, {s_quantity: 1, _id: 0}));
}
```

### Payment

```javascript
{
  const session = db.getMongo().startSession();
  const tx = session.getDatabase(demo.getName());
  try {
    session.startTransaction({
      readConcern: {level: "snapshot"},
      writeConcern: {w: "majority"}
    });
    const key = {c_w_id: 1, c_d_id: 1, c_id: 1};
    const requestId = "demo-payment";
    if (tx.history.findOne({request_id: {$eq: requestId, $type: "string"}})) {
      throw new Error("request_id đã có");
    }
    const result = tx.customer.updateMany(
      key, {$inc: {c_balance: -100, c_ytd_payment: 100, c_payment_cnt: 1}}
    );
    if (result.matchedCount !== 1) throw new Error("Cần đúng một customer");
    tx.history.insertOne({
      h_c_w_id: 1, h_c_d_id: 1, h_c_id: 1, h_w_id: 1, h_d_id: 1,
      h_date: new Date(), h_amount: 100, h_data: "FLASHSALE", request_id: requestId
    });
    printjson(tx.history.findOne({request_id: requestId}));
  } finally {
    try { session.abortTransaction(); } finally { session.endSession(); }
  }
}
```

## 4. Đối chiếu với bằng chứng benchmark

Khi trình bày, mở thêm `results/<run_id>/manifest.json` và xem `access_paths.plans` để đối chiếu những phép `EXPLAIN` đã thu trong lượt chạy. Các khối trên là ví dụ tương tác có giá trị thay thế cụ thể. Nhật ký từng lệnh kèm tham số của một lượt benchmark hiện chưa có trong đầu ra. [Định nghĩa manifest và kết quả](experiment-2.1.md)
