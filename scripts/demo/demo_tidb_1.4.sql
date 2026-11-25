-- ============================================================================
-- KỊCH BẢN KIỂM CHỨNG & DEMO CHỨC NĂNG CƠ BẢN TIDB v8.5.7 (MỤC 1.4 & PHỤ LỤC B.8)
-- Công cụ: MySQL Workbench (127.0.0.1:14000, user: root) & TiDB Dashboard (:12379)
-- ============================================================================

SET SQL_SAFE_UPDATES = 0;

-- ============================================================================
-- [B.8 - Kịch bản 1] Kết nối cụm, kiểm chứng phiên bản, DDL (AUTO_RANDOM) & CRUD
-- Bằng chứng: Hình B.4 (TiDB Dashboard) & Hình B.5 (SELECT VERSION())
-- ============================================================================

SELECT VERSION() AS tidb_version;

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

-- Khóa chính dùng AUTO_RANDOM phân tán tải ghi trên nhiều Region TiKV
CREATE TABLE orders (
  o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */,
  o_i_id INT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(20) NOT NULL
);

-- CRUD cơ bản: INSERT, SELECT (quan sát o_id ngẫu nhiên 64-bit) & DELETE đơn nháp
INSERT INTO item VALUES (101, 'Tai nghe Flash-Sale', 500000);
INSERT INTO stock VALUES (1, 101, 5);
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'TEST_DELETE');

SELECT * FROM item;
SELECT * FROM stock;
SELECT * FROM orders;

DELETE FROM orders WHERE status = 'TEST_DELETE';
SELECT * FROM orders;

-- ============================================================================
-- [B.8 - Kịch bản 2] Trừ tồn kho có điều kiện (chống âm kho)
-- ============================================================================

-- Lần (a): Mua 3 khi kho còn 5 -> 1 row(s) affected, tồn kho giảm còn 2
UPDATE stock
SET s_quantity = s_quantity - 3
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;

-- Lần (b): Mua 4 khi kho còn 2 -> 0 row(s) affected, tồn kho giữ nguyên 2 (không âm)
UPDATE stock
SET s_quantity = s_quantity - 4
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- ============================================================================
-- [B.8 - Kịch bản 3] Giao dịch ACID phân tán — COMMIT & ROLLBACK (Hình B.6)
-- ============================================================================

-- Phiên (a) COMMIT: Mua nốt 2 đơn vị còn lại (tồn 2 -> 0) và lưu đơn 'COMMITTED'
BEGIN;
UPDATE stock
SET s_quantity = s_quantity - 2
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 2;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 2, 'COMMITTED');
COMMIT;

-- Phiên (b) ROLLBACK: Chèn đơn 'SHOULD_ROLLBACK' rồi trừ tồn khi đã về 0 -> hủy toàn bộ
BEGIN;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'SHOULD_ROLLBACK');
UPDATE stock
SET s_quantity = s_quantity - 1
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;
SELECT ROW_COUNT() AS updated_rows; -- Kỳ vọng = 0 (thiếu hàng)
ROLLBACK;

-- Kiểm chứng sau ROLLBACK: tồn = 0 và orders CHỈ có đơn 'COMMITTED' (Hình B.6)
SELECT * FROM stock;
SELECT * FROM orders;

-- ============================================================================
-- [B.8 - Kịch bản 4] Giám sát cấu hình cụm, kế hoạch thực thi & Region (Hình B.7)
-- ============================================================================

-- 1. Kiểm chứng 5 nút trong cụm (1 pd, 1 tidb, 3 tikv) cùng nhánh v8.5.7
SELECT TYPE, INSTANCE, STATUS_ADDRESS, VERSION
FROM information_schema.CLUSTER_INFO
ORDER BY TYPE, INSTANCE;

-- 2. Kiểm chứng cấu hình nhân bản PD (max-replicas = 1 cho lượt đo chính)
SELECT TYPE, INSTANCE, `KEY`, VALUE
FROM information_schema.CLUSTER_CONFIG
WHERE `KEY` = 'replication.max-replicas';

-- 3. Kiểm chứng chế độ giao dịch bi quan (pessimistic) và tối ưu 2PC (async commit, 1PC)
SHOW VARIABLES WHERE Variable_name IN (
  'tidb_txn_mode', 'tidb_enable_async_commit', 'tidb_enable_1pc', 'transaction_isolation'
);

-- 4. Kiểm chứng kế hoạch thực thi đi đúng khóa chính (Point_Get trên PRIMARY)
EXPLAIN SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- 5. Quan sát REGION_ID và LEADER_STORE_ID của bảng stock trên TiKV (Hình B.7)
SELECT DISTINCT
  r.TABLE_NAME,
  r.REGION_ID,
  r.START_KEY,
  r.END_KEY,
  p.PEER_ID AS LEADER_ID,
  p.STORE_ID AS LEADER_STORE_ID
FROM information_schema.TIKV_REGION_STATUS r
JOIN information_schema.TIKV_REGION_PEERS p
  ON r.REGION_ID = p.REGION_ID AND p.IS_LEADER = 1
WHERE r.DB_NAME = 'demo_flashsale' AND r.TABLE_NAME = 'stock';

-- ============================================================================
-- [B.8 - Kịch bản 5] Online DDL không chặn giao dịch đang hoạt động (Hình B.8)
-- Hướng dẫn chạy 2 phiên độc lập trên MySQL Workbench:
--   Bước 1 (Kết nối 1): Chạy khối khởi tạo demo_ose và giữ mở BEGIN; SELECT ...
--   Bước 2 (Kết nối 2): Chạy ALTER TABLE order_line ADD COLUMN ...
--   Bước 3 (Kết nối 1): Chạy COMMIT; rồi kiểm tra DDL_JOBS trên Kết nối 2 (STATE = synced).
-- ============================================================================

-- [Kết nối 1] Khởi tạo bảng order_line lược đồ cũ
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

-- [Kết nối 2] Thực thi Online DDL thêm cột và kiểm tra trạng thái synced (Hình B.8)
ALTER TABLE demo_ose.order_line
  ADD COLUMN ol_discount BIGINT NULL,
  ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';

SELECT JOB_ID, DB_NAME, TABLE_NAME, JOB_TYPE, STATE
FROM information_schema.DDL_JOBS
WHERE DB_NAME = 'demo_ose'
ORDER BY JOB_ID DESC
LIMIT 3;

-- ============================================================================
-- [B.8 - Kịch bản 6] Kiểm soát tranh chấp khóa bi quan trên cùng dòng stock (Hình B.9)
-- Hướng dẫn chạy đồng thời trên 2 tab kết nối độc lập của MySQL Workbench:
-- ============================================================================

-- [Kết nối 1] Đặt lại tồn kho = 5 và mở giao dịch giữ khóa bi quan (chưa COMMIT):
UPDATE demo_flashsale.stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;
-- BEGIN;
-- UPDATE demo_flashsale.stock SET s_quantity = s_quantity - 1
-- WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;

-- [Kết nối 2] Chạy đồng thời câu lệnh dưới đây -> quan sát trạng thái chờ khóa (Running...):
-- BEGIN;
-- UPDATE demo_flashsale.stock SET s_quantity = s_quantity - 1
-- WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;

-- [Sau khi cả 2 kết nối chạy COMMIT;] Đối soát tồn kho giảm đúng 2 đơn vị (5 -> 3):
-- SELECT * FROM demo_flashsale.stock WHERE s_w_id = 1 AND s_i_id = 101;
