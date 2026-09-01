from __future__ import annotations

from collections.abc import Iterator

from duckdb import DuckDBPyConnection
from fastapi import Request

from app.database import DuckDBManager


def get_connection(request: Request) -> Iterator[DuckDBPyConnection]:
    manager: DuckDBManager = request.app.state.database
    with manager.connection() as connection:
        yield connection
