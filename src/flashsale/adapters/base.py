from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Protocol


Row = dict[str, Any]


@dataclass(frozen=True)
class Endpoint:
    engine: str
    port: int
    database: str

    def __post_init__(self) -> None:
        prefix, _, token = self.database.partition("_")
        if prefix != "flashsale" or len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
            raise ValueError("Tên database phải thuộc phạm vi dự án và có UUID hex")


class DBError(Exception):
    def __init__(self, category: str, retryable: bool = False, ambiguous: bool = False):
        super().__init__(category)
        self.category = category
        self.retryable = retryable
        self.ambiguous = ambiguous


class Adapter(Protocol):
    def close(self) -> None: ...
    def ping(self, concurrency: int = 1) -> dict[str, Any]: ...
    def atomic(self) -> AbstractContextManager[None]: ...
    def create(self) -> None: ...
    def drop(self) -> None: ...
    def insert(self, table: str, row: Row) -> None: ...
    def insert_many(self, table: str, rows: list[Row]) -> None: ...
    def one(self, table: str, key: Row, *, lock: bool = False) -> Row | None: ...
    def change(self, table: str, key: Row, *, set_values: Row | None = None,
               increment: Row | None = None, changed_only: bool = False,
               between: dict[str, tuple[int, int]] | None = None) -> int: ...
    def delete_tagged(self, table: str, field: str) -> int: ...
    def rows(self, table: str, fields: Iterable[str], *, tagged: bool = False) -> Iterator[Row]: ...
    def count(self, table: str) -> int: ...
    def evidence(self, hot_item: int) -> dict[str, Any]: ...
    def counters(self) -> dict[str, int | None]: ...


def open_adapter(endpoint: Endpoint, *, admin: bool = False) -> Adapter:
    if endpoint.engine == "mongo":
        from .mongo import MongoAdapter
        return MongoAdapter(endpoint)
    from .sql import SQLAdapter
    return SQLAdapter(endpoint, admin=admin)
