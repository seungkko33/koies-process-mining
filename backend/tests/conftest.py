from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from app.database import SCHEMA_PATH
from duckdb import DuckDBPyConnection

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_event_log.json"
INSERT_EVENT_SQL = """
    INSERT INTO curated.event_log (
        event_id,
        case_id,
        activity,
        event_ts,
        source_sequence,
        ingest_sequence,
        mapping_version,
        case_rule_version,
        ingestion_batch_id,
        event_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CAST(? AS DATE))
"""


def load_golden_events() -> list[dict[str, object]]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        events = json.load(fixture_file)
    if not isinstance(events, list):
        raise TypeError("Golden fixture must contain a JSON list")
    return events


def insert_golden_events(connection: DuckDBPyConnection) -> None:
    rows = [
        (
            event["event_id"],
            event["case_id"],
            event["activity"],
            event["event_ts"],
            event["source_sequence"],
            event["ingest_sequence"],
            event["mapping_version"],
            event["case_rule_version"],
            event["ingestion_batch_id"],
            event["event_ts"],
        )
        for event in load_golden_events()
    ]
    connection.executemany(INSERT_EVENT_SQL, rows)


@pytest.fixture
def golden_connection() -> Iterator[DuckDBPyConnection]:
    connection = duckdb.connect(":memory:")
    connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    insert_golden_events(connection)
    try:
        yield connection
    finally:
        connection.close()

