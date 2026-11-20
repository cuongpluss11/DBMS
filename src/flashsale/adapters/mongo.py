from collections.abc import Iterable, Iterator
from contextlib import contextmanager, suppress
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .base import DBError, Endpoint, Row
from flashsale.data.schema import TABLES


def classify(exc: PyMongoError, committing: bool = False) -> DBError:
    code = getattr(exc, "code", None)
    if exc.has_error_label("UnknownTransactionCommitResult") or committing and isinstance(exc, ConnectionFailure):
        return DBError("timeout" if exc.timeout else "connection", True, True)
    if code == 112:
        return DBError("write_conflict", True)
    if code in (24, 50, 262) or exc.timeout:
        return DBError("timeout", True, committing)
    if isinstance(exc, DuplicateKeyError):
        return DBError("duplicate_key", True)
    if isinstance(exc, ConnectionFailure):
        return DBError("connection", True)
    if exc.has_error_label("TransientTransactionError"):
        return DBError("transaction_abort", True)
    return DBError("database_error")


class MongoAdapter:
    """Mode A. Một adapter và session cho mỗi client của runner."""

    def __init__(self, endpoint: Endpoint, timeout: float = 15.0):
        self.client = MongoClient(endpoint.host, endpoint.port, directConnection=True,
                                  replicaSet="flashsale", retryWrites=False,
                                  serverSelectionTimeoutMS=5000, socketTimeoutMS=int(timeout * 1000),
                                  maxPoolSize=1)
        self.db = self.client.get_database(endpoint.database, read_concern=ReadConcern("majority"))
        self.session = None

    def close(self) -> None:
        self.client.close()

    def ping(self, concurrency: int = 1) -> dict[str, Any]:
        hello = self.client.admin.command("hello")
        if hello.get("setName") != "flashsale" or not hello.get("isWritablePrimary"):
            raise RuntimeError("MongoDB replica set chưa có primary")
        info = {"version": self.client.server_info()["version"], "replica_set": "flashsale",
                "transaction_read_concern": "snapshot", "transaction_write_concern": "majority",
                "transaction_write_journal": True,
                "logical_session_timeout_minutes": hello.get("logicalSessionTimeoutMinutes")}
        try:
            cache = self.client.admin.command("serverStatus")["wiredTiger"]["cache"]
            info["wiredtiger_cache_bytes"] = cache["maximum bytes configured"]
        except Exception:
            info["wiredtiger_cache_bytes"] = None
        return info

    @contextmanager
    def atomic(self) -> Iterator[None]:
        committing = False
        with self.client.start_session() as session:
            self.session = session
            try:
                session.start_transaction(read_concern=ReadConcern("snapshot"),
                                          write_concern=WriteConcern("majority", j=True))
                yield
                committing = True
                session.commit_transaction()
            except BaseException as exc:
                if session.in_transaction:
                    with suppress(PyMongoError):
                        session.abort_transaction()
                if isinstance(exc, PyMongoError):
                    raise classify(exc, committing) from exc
                raise
            finally:
                self.session = None

    def create(self, idempotency: bool = True) -> None:
        if self.db.list_collection_names():
            raise RuntimeError("Database MongoDB đã có collection")
        for name, table in TABLES.items():
            collection = self.db.create_collection(name)
            if table.key:
                collection.create_index(list(table.key), unique=True, name="logical_pk")
            for field in table.unique:
                # Lượt idempotency_off: chỉ số thường (không UNIQUE) để vẫn có đường truy cập theo request_id.
                collection.create_index(field, unique=idempotency,
                                        name=("uq_" if idempotency else "ix_") + field,
                                        partialFilterExpression={field: {"$type": "string"}})
            for fields in table.indexes:
                collection.create_index(list(fields), name="ix_" + "_".join(fields))

    def drop(self) -> None:
        self.client.drop_database(self.db)

    def insert(self, table: str, row: Row) -> None:
        self.db[table].insert_one(dict(row), session=self.session)

    def insert_many(self, table: str, rows: list[Row]) -> None:
        self.db[table].insert_many([dict(row) for row in rows], session=self.session)

    def one(self, table: str, key: Row, *, lock: bool = False) -> Row | None:
        if "request_id" in key:
            key = {**key, "request_id": {"$eq": key["request_id"], "$type": "string"}}
        try:
            return self.db[table].find_one(key, {"_id": 0}, session=self.session)
        except PyMongoError as exc:
            if self.session is not None:
                raise
            raise classify(exc) from exc

    def change(self, table: str, key: Row, *, set_values: Row | None = None,
               increment: Row | None = None, changed_only: bool = False,
               between: dict[str, tuple[int, int]] | None = None) -> int:
        key = {**key, **{name: {"$gte": low, "$lte": high} for name, (low, high) in (between or {}).items()}}
        update = {}
        if set_values:
            update["$set"] = set_values
        if increment:
            update["$inc"] = increment
        if changed_only and set_values:
            key = {**key, "$or": [{name: {"$ne": value}} for name, value in set_values.items()]}
        return self.db[table].update_many(key, update, session=self.session).matched_count

    def delete_tagged(self, table: str, field: str) -> int:
        return self.db[table].delete_many({field: {"$type": "string"}}).deleted_count

    def rows(self, table: str, fields: Iterable[str], *, tagged: bool = False) -> Iterator[Row]:
        where = {"run_id": {"$type": "string"}} if tagged else {}
        projection = {field: 1 for field in fields}
        with self.db[table].find(where, {**projection, "_id": 0}) as cursor:
            yield from cursor

    def count(self, table: str) -> int:
        return self.db[table].count_documents({})

    def evidence(self, hot_item: int) -> dict[str, Any]:
        probes = {
            "district": {"d_w_id": 1, "d_id": 1},
            "stock": {"s_w_id": 1, "s_i_id": hot_item},
            "customer": {"c_w_id": 1, "c_d_id": 1, "c_id": 1},
        }
        plans = {}
        for table, where in probes.items():
            plans[table] = self.db[table].find(where).explain()
        for table in ("orders", "history"):
            # Eq on a string logically implies the partial index filter. Explicit
            # type condition also makes the implication visible to the planner.
            where = {"request_id": {"$eq": "probe", "$type": "string"}}
            plans[table] = self.db[table].find(where).explain()
        indexed = all("IXSCAN" in str(plan["queryPlanner"]["winningPlan"])
                      or "EXPRESS_IXSCAN" in str(plan["queryPlanner"]["winningPlan"])
                      for plan in plans.values())
        return {"indexed": indexed, "plans": plans}

    def doc_reconciliation(self, inventory: int, initial_orders: int) -> list[dict]:
        """Bản aggregation tương đương câu SQL kiểm luật 1 và 2 của đề. Kết quả rỗng là đạt."""
        grouped = [{"$match": {"ol_o_id": {"$gt": initial_orders}}},
                   {"$group": {"_id": {"w": "$ol_supply_w_id", "i": "$ol_i_id"}, "sold": {"$sum": "$ol_quantity"}}}]
        violations = grouped + [
            {"$lookup": {"from": "stock", "let": {"w": "$_id.w", "i": "$_id.i"}, "as": "stock",
                         "pipeline": [{"$match": {"$expr": {"$and": [{"$eq": ["$s_w_id", "$$w"]},
                                                                      {"$eq": ["$s_i_id", "$$i"]}]}}}]}},
            {"$match": {"$expr": {"$or": [
                {"$eq": [{"$size": "$stock"}, 0]},
                {"$lt": [{"$first": "$stock.s_quantity"}, 0]},
                {"$ne": [{"$subtract": [{"$subtract": [inventory, {"$first": "$stock.s_quantity"}]}, "$sold"]}, 0]}]}}},
            {"$limit": 10}]
        errors = [{"warehouse": row["_id"]["w"], "item": row["_id"]["i"], "sold": row["sold"],
                   "s_quantity": row["stock"][0]["s_quantity"] if row["stock"] else None}
                  for row in self.db.order_line.aggregate(violations)]
        # Dòng tồn đã đổi nhưng không có đơn tương ứng (bao gồm tồn âm không do đơn nào gây ra).
        groups = next(iter(self.db.order_line.aggregate(grouped + [{"$count": "n"}])), {"n": 0})["n"]
        changed = self.db.stock.count_documents({"s_quantity": {"$ne": inventory}})
        if changed != groups:
            errors.append({"stock_rows_changed": changed, "items_with_sales": groups})
        return errors

    def counters(self) -> dict[str, int | None]:
        return {"lock_wait_ms": None, "server_deadlocks": None}
