from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

import duckdb
from duckdb import DuckDBPyConnection

from app.config import Settings

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "sql" / "001_schema.sql"


class DuckDBManager:
    """Creates independently scoped DuckDB connections with bounded resource settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # DuckDB is an embedded, single-node engine. Serializing request-scoped
        # connections avoids overlapping Windows file handles while a FastAPI
        # yield dependency is completing its cleanup.
        self._connection_lock = Lock()

    def _prepare_directories(self) -> None:
        database_path = self._settings.data.database_path
        if str(database_path) != ":memory:":
            database_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings.duckdb.temp_directory.mkdir(parents=True, exist_ok=True)

    def connect(self) -> DuckDBPyConnection:
        self._prepare_directories()
        connection = duckdb.connect(str(self._settings.data.database_path))
        connection.execute("SET threads = ?", [self._settings.duckdb.threads])
        connection.execute("SET memory_limit = ?", [self._settings.duckdb.memory_limit])
        connection.execute(
            "SET preserve_insertion_order = ?",
            [self._settings.duckdb.preserve_insertion_order],
        )
        connection.execute(
            "SET temp_directory = ?",
            [str(self._settings.duckdb.temp_directory)],
        )
        # Canonical analytical timestamps are stored as UTC TIMESTAMP values.
        # Setting the session explicitly prevents host-local display/cast behavior.
        connection.execute("SET TimeZone = 'UTC'")
        return connection

    def initialize(self) -> None:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connection() as connection:
            connection.execute(schema_sql)

    @contextmanager
    def connection(self) -> Iterator[DuckDBPyConnection]:
        with self._connection_lock:
            connection = self.connect()
            try:
                yield connection
            finally:
                connection.close()
