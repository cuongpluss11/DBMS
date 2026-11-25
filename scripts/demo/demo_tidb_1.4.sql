-- ============================================================================
-- KỊCH BẢN KIỂM CHỨNG CHỨC NĂNG CƠ BẢN TIDB v8.5.7 (MỤC 1.4 & PHỤ LỤC B.8)
-- Chuẩn hóa theo 3 câu hỏi: Thực hiện gì -> Quan sát được gì (trước/sau) -> Chứng minh cơ chế gì
-- Công cụ: MySQL Workbench (127.0.0.1:14000, user: root) & TiDB Dashboard (:12379)
-- Lưu ý: Toàn bộ cú pháp tương thích 100% trình kiểm tra MySQL 8.0.11 của Workbench.
-- ============================================================================

SET SQL_SAFE_UPDATES = 0;

-- ============================================================================
-- [Demo B1] Kết nối cụm phân tán, kiểm chứng phiên bản, DDL (AUTO_RANDOM) & CRUD
-- Cơ chế chứng minh: Giao diện SQL tương thích MySQL trên tầng lưu trữ phân tán TiKV,
-- sinh khóa chính phân tán bằng AUTO_RANDOM và thực thi đầy đủ INSERT / SELECT / DELETE.
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

CREATE TABLE orders (
  o_id BIGINT PRIMARY KEY /*T![auto_rand] AUTO_RANDOM */,
  o_i_id INT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(20) NOT NULL
);

-- 1. CREATE & READ: Chèn dữ liệu mẫu và quan sát khóa o_id sinh ngẫu nhiên 64-bit
INSERT INTO item VALUES (101, 'Tai nghe Flash-Sale', 500000);
INSERT INTO stock VALUES (1, 101, 5);
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'TEST_CRUD');

SELECT * FROM item;
SELECT * FROM stock;
SELECT * FROM orders; -- Quan sát đơn TEST_CRUD có o_id phân tán trước khi xóa

-- 2. DELETE & Kiểm tra trạng thái sau xóa: Xóa đơn kiểm thử, giữ tồn kho = 5 cho Demo B2
DELETE FROM orders WHERE status = 'TEST_CRUD';
SELECT COUNT(*) AS remaining_test_orders FROM orders;

-- ============================================================================
-- [Demo B2] Cập nhật tồn kho có điều kiện — Chống âm kho (tồn: 5 -> 2 -> 2)
-- Cơ chế chứng minh: Mệnh đề điều kiện s_quantity >= qty trong câu lệnh UPDATE
-- ngăn chặn phép trừ vượt quá số lượng tồn hiện có.
-- ============================================================================

-- 0. Trạng thái tồn kho trước khi cập nhật (s_quantity = 5)
SELECT s_w_id, s_i_id, s_quantity AS qty_before FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- 1. Lần (a): Mua 3 khi còn 5 -> 1 row(s) affected, tồn kho giảm còn 2
UPDATE stock
SET s_quantity = s_quantity - 3
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 3;

SELECT ROW_COUNT() AS rows_updated_buy_3, s_quantity AS qty_after_buy_3
FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- 2. Lần (b): Mua 4 khi chỉ còn 2 -> 0 row(s) affected, tồn kho giữ nguyên 2 (không âm)
UPDATE stock
SET s_quantity = s_quantity - 4
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 4;

SELECT ROW_COUNT() AS rows_updated_buy_4, s_quantity AS qty_final
FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- ============================================================================
-- [Demo B3] Giao dịch ACID — Quan sát rõ trạng thái sau COMMIT & sau ROLLBACK
-- Cơ chế chứng minh: Tính nguyên tử của giao dịch nhiều câu lệnh (cùng lưu hoặc cùng hủy).
-- ============================================================================

-- 1. Phiên (a) COMMIT: Trừ nốt 2 đơn vị tồn kho (2 -> 0) và lưu đơn 'COMMITTED'
BEGIN;
UPDATE stock
SET s_quantity = s_quantity - 2
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 2;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 2, 'COMMITTED');
COMMIT;

-- Kiểm tra trạng thái ngay sau COMMIT (stock = 0, orders có 1 đơn 'COMMITTED'):
SELECT s_w_id, s_i_id, s_quantity AS stock_after_commit FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
SELECT * FROM orders;

-- 2. Phiên (b) ROLLBACK: Chèn trước đơn 'SHOULD_ROLLBACK', trừ kho thất bại (tồn = 0) -> ROLLBACK
BEGIN;
INSERT INTO orders (o_i_id, qty, status) VALUES (101, 1, 'SHOULD_ROLLBACK');
UPDATE stock
SET s_quantity = s_quantity - 1
WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;
SELECT ROW_COUNT() AS updated_rows_when_empty; -- Trả về 0 (hết hàng)
ROLLBACK;

-- Kiểm tra trạng thái cuối sau ROLLBACK (stock = 0, orders CHỈ có 'COMMITTED', không có 'SHOULD_ROLLBACK'):
SELECT s_w_id, s_i_id, s_quantity AS stock_after_rollback FROM stock WHERE s_w_id = 1 AND s_i_id = 101;
SELECT * FROM orders;

-- ============================================================================
-- [Demo B4] Giám sát cấu hình cụm, kế hoạch thực thi (EXPLAIN) & phân bố Region
-- Lưu ý học thuật về phạm vi bằng chứng:
--   (1) Biến tidb_enable_1pc = ON và tidb_enable_async_commit = ON chỉ xác nhận hai tối ưu
--       đang được bật ở mức cấu hình, KHÔNG chứng minh một giao dịch cụ thể đã dùng 1PC/Async Commit.
--   (2) Bảng demo nhỏ (1 dòng) hiện nằm gọn trong 1 Region do 1 TiKV giữ vai trò Leader;
--       khi dữ liệu lớn hoặc tách Region, các Region được phân phối trên nhiều nút TiKV.
-- ============================================================================

-- 1. Trạng thái 5 thành phần trong cụm (1 pd, 1 tidb, 3 tikv)
SELECT TYPE, INSTANCE, STATUS_ADDRESS, VERSION
FROM information_schema.CLUSTER_INFO
ORDER BY TYPE, INSTANCE;

-- 2. Cấu hình nhân bản trên PD (max-replicas = 1 ở cấu hình cơ sở)
SELECT TYPE, INSTANCE, `KEY`, VALUE
FROM information_schema.CLUSTER_CONFIG
WHERE `KEY` = 'replication.max-replicas';

-- 3. Biến cấu hình chế độ giao dịch & tối ưu bước chốt
SHOW VARIABLES WHERE Variable_name IN (
  'tidb_txn_mode', 'tidb_enable_async_commit', 'tidb_enable_1pc', 'transaction_isolation'
);

-- 4. Kế hoạch thực thi truy vấn tồn kho (xác nhận sử dụng Point_Get qua khóa chính PRIMARY)
EXPLAIN SELECT * FROM stock WHERE s_w_id = 1 AND s_i_id = 101;

-- 5. Thông tin định danh Region và nút TiKV giữ Leader của bảng stock
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
-- [Demo B5] Kiểm chứng Online DDL và quan sát sự phối hợp với giao dịch đang mở
-- Cơ chế chứng minh: TiDB sử dụng Metadata Lock (MDL) để phối hợp phiên bản lược đồ
-- với giao dịch cũ đang mở trên cùng bảng trước khi hoàn tất trạng thái synced.
-- Quy trình 5 bước thực hiện trên 2 kết nối độc lập của MySQL Workbench:
-- ============================================================================

-- [Bước 1 - Chạy trên Kết nối T1]: Tạo bảng order_line và mở giao dịch đọc (chưa COMMIT)
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

-- Mở giao dịch T1 giữ phiên bản lược đồ cũ (chưa chạy COMMIT):
-- BEGIN;
-- SELECT * FROM demo_ose.order_line LIMIT 1;

-- [Bước 2 & 3 - Chạy trên Kết nối T2]: Thực thi Online DDL thêm 2 cột mới
-- Quan sát: Khi T1 chưa COMMIT, lệnh ALTER trên T2 ở trạng thái chờ phối hợp MDL (Running...).
ALTER TABLE demo_ose.order_line
  ADD COLUMN ol_discount BIGINT NULL,
  ADD COLUMN ol_mig_state VARCHAR(16) NOT NULL DEFAULT 'UNMIGRATED';

-- [Bước 4 - Chạy trên Kết nối T1]: Chốt giao dịch cũ để T2 hoàn tất DDL
-- COMMIT;

-- [Bước 5 - Chạy trên Kết nối T2]: Kiểm tra trạng thái DDL Job (synced) VÀ cấu trúc bảng mới
SELECT JOB_ID, DB_NAME, TABLE_NAME, JOB_TYPE, STATE
FROM information_schema.DDL_JOBS
WHERE DB_NAME = 'demo_ose'
ORDER BY JOB_ID DESC
LIMIT 3;

SELECT * FROM demo_ose.order_line;

-- ============================================================================
-- [Demo B6] Kiểm soát tranh chấp ghi trên một dòng bằng Pessimistic Lock (tồn: 5 -> 3)
-- Cơ chế chứng minh: Ở chế độ pessimistic, T1 giữ khóa ghi khi UPDATE khiến T2 phải chờ;
-- sau khi T1 COMMIT, T2 tiếp tục thực thi trên giá trị mới và bảo toàn tổng lượng trừ.
-- ============================================================================

-- [Bước 1 - Kết nối T1]: Khởi tạo lại s_quantity = 5, bắt đầu giao dịch trừ 1 (chưa COMMIT)
UPDATE demo_flashsale.stock SET s_quantity = 5 WHERE s_w_id = 1 AND s_i_id = 101;
-- BEGIN;
-- UPDATE demo_flashsale.stock SET s_quantity = s_quantity - 1
-- WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;

-- [Bước 2 - Kết nối T2]: Chạy đồng thời cùng câu lệnh -> quan sát T2 chờ khóa (Running...)
-- BEGIN;
-- UPDATE demo_flashsale.stock SET s_quantity = s_quantity - 1
-- WHERE s_w_id = 1 AND s_i_id = 101 AND s_quantity >= 1;

-- [Bước 3 - Giải phóng & Xuất trạng thái dữ liệu cuối cùng]:
-- Chạy COMMIT; trên T1 -> T2 hoàn tất (1 row affected) -> chạy COMMIT; trên T2, rồi kiểm tra:
-- SELECT s_w_id, s_i_id, s_quantity AS final_stock_after_2_txns
-- FROM demo_flashsale.stock WHERE s_w_id = 1 AND s_i_id = 101; -- Kỳ vọng = 3 (5 - 1 - 1)
