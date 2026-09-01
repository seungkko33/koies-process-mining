from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

from app.config import load_settings
from app.database import DuckDBManager


def test_request_scoped_duckdb_connections_are_serialized(tmp_path: Path) -> None:
    base_settings = load_settings()
    settings = base_settings.model_copy(
        update={
            "data": base_settings.data.model_copy(
                update={"database_path": tmp_path / "serialized.duckdb"}
            ),
            "duckdb": base_settings.duckdb.model_copy(
                update={"temp_directory": tmp_path / "duckdb-temp"}
            ),
        }
    )
    manager = DuckDBManager(settings)
    manager.initialize()
    first_entered = Event()
    release_first = Event()
    second_entered = Event()

    def hold_first_connection() -> None:
        with manager.connection():
            first_entered.set()
            release_first.wait(timeout=5)

    def enter_second_connection() -> None:
        with manager.connection():
            second_entered.set()

    first = Thread(target=hold_first_connection)
    second = Thread(target=enter_second_connection)
    first.start()
    assert first_entered.wait(timeout=2)
    second.start()

    assert not second_entered.wait(timeout=0.1)
    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert second_entered.is_set()
