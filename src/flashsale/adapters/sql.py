from collections.abc import Iterable, Iterator
import json
from contextlib import contextmanager, suppress
from typing import Any

import pymysql
from pymysql.cursors import DictCursor, SSDictCursor

from .base import DBError, Endpoint, Row
from flashsale.data.schema import SLOT_TABLE, TABLES, ddl


def classify(exc: pymysql.MySQLError, committing: bool = False) -> DBError:
    code = exc.args[0] if exc.args else None
    detail = str(exc).lower()
    if committing and ("result undetermined" in detail or "result is undetermined" in detail):
        return DBError("connection", True, True)
    if code in (1205, 3024, 1317, 9002, 9012):
        return DBError("timeout", True, committing and code in (9002, 9012))
    if code == 1213:
        return DBError("deadlock", True)
    if code == 1644 and "out_of_stock" in detail:  # SIGNAL của stored procedure new_order_sp
        return DBError("out_of_stock")
    if code == 3572:  # ER_LOCK_NOWAIT: không lấy được khóa ngay (FOR UPDATE NOWAIT)
        return DBError("lock_nowait", True)
    if code in (9007, 8002):
        return DBError("write_conflict", True)
    if code in (8022, 8028):
        return DBError("transaction_abort", True)
    if code in (2002, 2003, 2006, 2013, 2055):
        category = "timeout" if "timed out" in detail else "connection"
        return DBError(category, True, committing)
    if code == 1062:
        return DBError("duplicate_key", True)
    return DBError("database_error")


_DIST = "CASE p_d " + " ".join(f"WHEN {i} THEN s_dist_{i:02d}" for i in range(1, 11)) + " END"
NEW_ORDER_PROCEDURE = f"""
CREATE PROCEDURE new_order_sp(IN p_w INT, IN p_d INT, IN p_c INT, IN p_request VARCHAR(64), IN p_run CHAR(32),
                              IN p_items JSON, IN p_now DATETIME)
BEGIN
  DECLARE v_n INT DEFAULT JSON_LENGTH(p_items);
  DECLARE v_i INT DEFAULT 0;
  DECLARE v_item INT;
  DECLARE v_qty INT;
  DECLARE v_stock BIGINT;
  DECLARE v_price INT;
  DECLARE v_dist CHAR(24);
  DECLARE v_oid BIGINT;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  SELECT d_next_o_id INTO v_oid FROM district WHERE d_w_id = p_w AND d_id = p_d FOR UPDATE;
  UPDATE district SET d_next_o_id = d_next_o_id + 1 WHERE d_w_id = p_w AND d_id = p_d;
  WHILE v_i < v_n DO
    SET v_item = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '][0]')) AS SIGNED);
    SET v_qty = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '][1]')) AS SIGNED);
    SELECT s_quantity, {_DIST} INTO v_stock, v_dist FROM stock WHERE s_w_id = p_w AND s_i_id = v_item FOR UPDATE;
    IF v_stock < v_qty THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'out_of_stock';
    END IF;
    SELECT i_price INTO v_price FROM item WHERE i_id = v_item;
    UPDATE stock SET s_quantity = s_quantity - v_qty, s_ytd = s_ytd + v_qty, s_order_cnt = s_order_cnt + 1
      WHERE s_w_id = p_w AND s_i_id = v_item;
    INSERT INTO order_line (ol_w_id, ol_d_id, ol_o_id, ol_number, ol_i_id, ol_supply_w_id, ol_delivery_d, ol_quantity,
                            ol_amount, ol_dist_info, run_id)
      VALUES (p_w, p_d, v_oid, v_i + 1, v_item, p_w, NULL, v_qty, v_qty * v_price, v_dist, p_run);
    SET v_i = v_i + 1;
  END WHILE;
  INSERT INTO orders (o_w_id, o_d_id, o_id, o_c_id, o_entry_d, o_carrier_id, o_ol_cnt, o_all_local, request_id, run_id)
    VALUES (p_w, p_d, v_oid, p_c, p_now, NULL, v_n, 1, p_request, p_run);
  INSERT INTO new_order (no_w_id, no_d_id, no_o_id, run_id) VALUES (p_w, p_d, v_oid, p_run);
  COMMIT;
END
"""


def keys(key: Row) -> tuple[str, tuple]:
    if not key:
        return "", ()
    return " WHERE " + " AND ".join(f"{name}=%s" for name in key), tuple(key.values())


class SQLAdapter:
    def __init__(self, endpoint: Endpoint, *, admin: bool = False, timeout: float = 15.0,
                 txn_mode: str = "default"):
        self.endpoint = endpoint
        self.tidb = endpoint.engine == "tidb"
        self.in_transaction = False
        self.connection = pymysql.connect(
            host=endpoint.host, port=endpoint.port, user="root", charset="utf8mb4",
            database=None if admin else endpoint.database, autocommit=True, cursorclass=DictCursor,
            connect_timeout=5, read_timeout=timeout, write_timeout=timeout,
        )
        if txn_mode != "default":
            if not self.tidb:
                raise ValueError("txn_mode chỉ áp dụng cho TiDB")
            self.query(f"SET SESSION tidb_txn_mode = '{txn_mode}'")

    def close(self) -> None:
        with suppress(pymysql.MySQLError):
            self.connection.close()

    def query(self, statement: str, values: tuple = ()) -> list[Row]:
        with self.connection.cursor() as cursor:
            cursor.execute(statement, values)
            return list(cursor.fetchall())

    def ping(self, concurrency: int = 1) -> dict[str, Any]:
        rows = self.query("SELECT VERSION() AS version, @@transaction_isolation AS isolation, "
                          "@@max_connections AS max_connections, @@foreign_key_checks AS foreign_key_checks")
        info = rows[0]
        limit = info["max_connections"]
        if limit and concurrency + 2 > limit:
            raise RuntimeError(f"max_connections={limit}; cần ít nhất {concurrency + 2}")
        if self.tidb:
            info["build"] = self.query("SELECT TIDB_VERSION() AS build")[0]["build"]
            info["transaction_mode"] = self.query("SELECT @@tidb_txn_mode AS mode")[0]["mode"]
            try:
                rows = self.query("SHOW CONFIG WHERE type='tikv' AND name IN "
                                  "('storage.block-cache.capacity','raftstore.sync-log')")
                info["tikv_durability_config"] = sorted({(r["Instance"], r["Name"], r["Value"]) for r in rows})
            except Exception:
                info["tikv_durability_config"] = None
        else:
            values = self.query("SELECT @@innodb_buffer_pool_size AS buffer_pool_bytes, "
                                "@@innodb_flush_log_at_trx_commit AS flush_at_commit, "
                                "@@sync_binlog AS sync_binlog, @@log_bin AS log_bin, "
                                "@@innodb_lock_wait_timeout AS lock_wait_timeout, "
                                "@@default_storage_engine AS storage_engine")
            info.update(values[0])
        return info

    @contextmanager
    def atomic(self) -> Iterator[None]:
        committing = False
        try:
            if not self.connection.open:
                self.connection.ping(reconnect=True)
            self.connection.begin()
            self.in_transaction = True
            yield
            committing = True
            self.connection.commit()
        except BaseException as exc:
            with suppress(pymysql.MySQLError):
                self.connection.rollback()
            if isinstance(exc, pymysql.MySQLError):
                raise classify(exc, committing) from exc
            raise
        finally:
            self.in_transaction = False

    def create(self, idempotency: bool = True) -> None:
        self.query(f"CREATE DATABASE {self.endpoint.database} CHARACTER SET utf8mb4")
        self.connection.select_db(self.endpoint.database)
        for name in TABLES:
            self.query(ddl(name, self.tidb, idempotency=idempotency))

    def drop(self) -> None:
        self.query(f"DROP DATABASE IF EXISTS {self.endpoint.database}")

    def install_procedures(self) -> None:
        """T4 (MySQL): tạo stored procedure đặt hàng trong database của lượt chạy (DDL, ngoài thời gian đo)."""
        if self.tidb:
            raise RuntimeError("TiDB không hỗ trợ stored procedure")
        self.query("DROP PROCEDURE IF EXISTS new_order_sp")
        self.query(NEW_ORDER_PROCEDURE)

    def call_new_order(self, w: int, d: int, c: int, request_id: str, run_id: str,
                       items: list[tuple[int, int]], now) -> None:
        """Một lần CALL: thủ tục tự BEGIN/COMMIT (kết nối đang autocommit), nên toàn bộ giao dịch là một vòng mạng."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("CALL new_order_sp(%s, %s, %s, %s, %s, CAST(%s AS JSON), %s)",
                               (w, d, c, request_id, run_id, json.dumps([list(item) for item in items]), now))
                while cursor.nextset():
                    pass
        except pymysql.MySQLError as exc:
            raise classify(exc, committing=True) from exc

    def create_slots(self) -> None:
        self.drop_slots()
        self.query(ddl(SLOT_TABLE, self.tidb))

    def drop_slots(self) -> None:
        self.query(f"DROP TABLE IF EXISTS {SLOT_TABLE}")

    def insert(self, table: str, row: Row) -> None:
        self.insert_many(table, [row])

    def insert_many(self, table: str, rows: list[Row]) -> None:
        fields = ",".join(rows[0])
        params = ",".join(["%s"] * len(rows[0]))
        with self.connection.cursor() as cursor:
            cursor.executemany(f"INSERT INTO {table} ({fields}) VALUES ({params})",
                               [tuple(row.values()) for row in rows])

    def one(self, table: str, key: Row, *, lock: bool = False, nowait: bool = False) -> Row | None:
        where, values = keys(key)
        suffix = (" FOR UPDATE NOWAIT" if nowait else " FOR UPDATE") if lock or nowait else ""
        try:
            if not self.in_transaction and not self.connection.open:
                self.connection.ping(reconnect=True)
            result = self.query(f"SELECT * FROM {table}{where}{suffix}", values)
        except pymysql.MySQLError as exc:
            if self.in_transaction:
                raise
            raise classify(exc) from exc
        return result[0] if result else None

    def change(self, table: str, key: Row, *, set_values: Row | None = None,
               increment: Row | None = None, changed_only: bool = False,
               between: dict[str, tuple[int, int]] | None = None,
               at_least: Row | None = None) -> int:
        """UPDATE; `at_least` thêm điều kiện `cột >= giá trị` vào cùng câu lệnh (P1: kiểm tra và trừ kho
        nguyên tử). Trả về số dòng bị ảnh hưởng."""
        assignments = [f"{name}=%s" for name in (set_values or {})]
        assignments.extend(f"{name}={name}+%s" for name in (increment or {}))
        where, values = keys(key)
        params = (*((set_values or {}).values()), *((increment or {}).values()), *values)
        for name, (low, high) in (between or {}).items():
            where += (" AND " if where else " WHERE ") + f"{name} BETWEEN %s AND %s"
            params += (low, high)
        for name, minimum in (at_least or {}).items():
            where += (" AND " if where else " WHERE ") + f"{name} >= %s"
            params += (minimum,)
        if changed_only and set_values:
            conditions = " OR ".join(f"NOT ({name} <=> %s)" for name in set_values)
            where += (" AND " if where else " WHERE ") + f"({conditions})"
            params += tuple(set_values.values())
        with self.connection.cursor() as cursor:
            return cursor.execute(f"UPDATE {table} SET {','.join(assignments)}{where}", params)

    def delete_tagged(self, table: str, field: str) -> int:
        removed = 0
        with self.connection.cursor() as cursor:
            while True:
                count = cursor.execute(f"DELETE FROM {table} WHERE {field} IS NOT NULL LIMIT 5000")
                removed += count
                if count < 5000:
                    return removed

    def rows(self, table: str, fields: Iterable[str], *, tagged: bool = False) -> Iterator[Row]:
        where = " WHERE run_id IS NOT NULL" if tagged else ""
        with self.connection.cursor(SSDictCursor) as cursor:
            cursor.execute(f"SELECT {','.join(fields)} FROM {table}{where}")
            yield from cursor

    def count(self, table: str) -> int:
        return self.query(f"SELECT COUNT(*) AS count FROM {table}")[0]["count"]

    def evidence(self, hot_item: int) -> dict[str, Any]:
        probes = {
            "district": ("SELECT * FROM district WHERE d_w_id=1 AND d_id=1 FOR UPDATE", ()),
            "stock": ("SELECT * FROM stock WHERE s_w_id=1 AND s_i_id=%s FOR UPDATE", (hot_item,)),
            "customer": ("SELECT * FROM customer WHERE c_w_id=1 AND c_d_id=1 AND c_id=1", ()),
            # Câu P1 (mục 2.2): cập nhật có điều kiện theo khóa chính; EXPLAIN không thực thi câu lệnh.
            "stock_update": ("UPDATE stock SET s_quantity = s_quantity - 1 WHERE s_w_id=1 AND s_i_id=%s "
                             "AND s_quantity >= 1", (hot_item,)),
            "orders": ("SELECT * FROM orders WHERE request_id=%s", ("probe",)),
            "history": ("SELECT * FROM history WHERE request_id=%s", ("probe",)),
        }
        plans = {table: self.query("EXPLAIN " + statement, params)
                 for table, (statement, params) in probes.items()}
        if self.tidb:
            indexed = all(any("Point_Get" in row["id"] or "Index" in row["id"] for row in plan)
                          for plan in plans.values())
        else:
            # An absent unique equality is resolved during MySQL optimization.
            # Record a second, non-constant probe of the same index when that happens.
            for table in ("orders", "history"):
                if any(row.get("Extra") == "no matching row in const table" for row in plans[table]):
                    plans[table + "_range"] = self.query(
                        f"EXPLAIN SELECT * FROM {table} WHERE request_id >= %s AND request_id < %s",
                        ("probe", "probz"),
                    )
            indexed = all(
                any(row.get("key") in (("uq_request_id", "ix_request_id") if table in ("orders", "history")
                                       else ("PRIMARY",))
                    for row in plans.get(table + "_range", plans[table]))
                for table in probes
            )
        result = {"indexed": indexed, "plans": plans}
        if self.tidb:
            result["regions"] = {table: self.query(f"SHOW TABLE {table} REGIONS")
                                 for table in ("stock", "history")}
            result["history_ddl"] = self.query("SHOW CREATE TABLE history")
        return result

    def doc_reconciliation(self, inventory: int, initial_orders: int, slots: bool = False) -> list[dict]:
        """Câu SQL kiểm luật 1 và 2 của đề (mục 2.1), mở rộng cho mọi kho. Kết quả rỗng là đạt.
        Chỉ đếm dòng đơn tạo trong lượt chạy bằng ol_o_id > initial_orders: đúng vì d_next_o_id nạp
        ban đầu là initial_orders + 1 và reset khôi phục lại giá trị đó."""
        statement = (
            "SELECT s.s_w_id, s.s_i_id, s.s_quantity, COALESCE(o.sold, 0) AS sold FROM stock s "
            "LEFT JOIN (SELECT ol_supply_w_id AS w, ol_i_id AS i, SUM(ol_quantity) AS sold FROM order_line "
            "WHERE ol_o_id > %s GROUP BY ol_supply_w_id, ol_i_id) o ON o.w = s.s_w_id AND o.i = s.s_i_id "
            "WHERE s.s_quantity < 0 OR %s - s.s_quantity <> COALESCE(o.sold, 0) LIMIT 10")
        if slots:
            # Mục 2.2 (nhóm C): luật 2 tính trên tổng tồn của các dòng con; luật 1 kiểm từng dòng con.
            statement = (
                "SELECT s.s_w_id, s.s_i_id, s.total AS s_quantity, COALESCE(o.sold, 0) AS sold FROM "
                "(SELECT st.s_w_id, st.s_i_id, st.s_quantity AS own, st.s_quantity + COALESCE(sl.q, 0) AS total, "
                "sl.m AS min_slot FROM stock st LEFT JOIN (SELECT ss_w_id, ss_i_id, SUM(ss_quantity) AS q, "
                "MIN(ss_quantity) AS m FROM stock_slot GROUP BY ss_w_id, ss_i_id) sl "
                "ON sl.ss_w_id = st.s_w_id AND sl.ss_i_id = st.s_i_id) s "
                "LEFT JOIN (SELECT ol_supply_w_id AS w, ol_i_id AS i, SUM(ol_quantity) AS sold FROM order_line "
                "WHERE ol_o_id > %s GROUP BY ol_supply_w_id, ol_i_id) o ON o.w = s.s_w_id AND o.i = s.s_i_id "
                "WHERE s.own < 0 OR s.min_slot < 0 OR %s - s.total <> COALESCE(o.sold, 0) LIMIT 10")
        return self.query(statement, (initial_orders, inventory))

    def counters(self) -> dict[str, int | None]:
        if self.tidb:
            return {"lock_wait_ms": None, "server_deadlocks": None}
        rows = self.query("SHOW GLOBAL STATUS WHERE Variable_name = 'Innodb_row_lock_time'")
        lock_wait = int(rows[0]["Value"]) if rows else None
        # MySQL không có status variable Innodb_deadlocks (chỉ MariaDB/Percona);
        # bộ đếm nằm ở INNODB_METRICS.lock_deadlocks. Chưa bật thì trả None, không phải 0.
        metric = self.query("SELECT `COUNT` AS cnt, STATUS AS status FROM information_schema.INNODB_METRICS "
                            "WHERE NAME = 'lock_deadlocks'")
        deadlocks = int(metric[0]["cnt"]) if metric and metric[0]["status"] == "enabled" else None
        return {"lock_wait_ms": lock_wait, "server_deadlocks": deadlocks}
