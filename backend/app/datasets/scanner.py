from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from duckdb import DuckDBPyConnection
from pydantic import JsonValue

from app.datasets.domain import ColumnProfileRecord, MappingRecord
from app.schemas.datasets import DatasetFileType, TimestampPreview

PROFILE_SAMPLE_ROWS = 20
PROFILE_SAMPLE_VALUES = 3


@dataclass(frozen=True)
class ScanProfile:
    row_count: int
    columns: list[ColumnProfileRecord]


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def source_relation(file_type: DatasetFileType, parameter: str = "$source_path") -> str:
    if file_type in {DatasetFileType.CSV, DatasetFileType.CSV_GZ}:
        return (
            f"read_csv({parameter}, header = true, all_varchar = true, "
            "sample_size = 20480)"
        )
    return f"read_parquet({parameter})"


def inferred_source_relation(
    file_type: DatasetFileType,
    parameter: str = "$source_path",
) -> str:
    if file_type in {DatasetFileType.CSV, DatasetFileType.CSV_GZ}:
        return f"read_csv({parameter}, header = true, sample_size = 20480)"
    return f"read_parquet({parameter})"


class DatasetScanner:
    def __init__(self, connection: DuckDBPyConnection) -> None:
        self._connection = connection

    def detect_schema(
        self,
        path: Path,
        file_type: DatasetFileType,
    ) -> list[tuple[str, str]]:
        inferred_relation = inferred_source_relation(file_type)
        description_rows = self._connection.execute(
            f"DESCRIBE SELECT * FROM {inferred_relation}",
            {"source_path": str(path)},
        ).fetchall()
        if not description_rows:
            raise ValueError("The source file has no columns")
        schema = [(str(row[0]), str(row[1])) for row in description_rows]
        if len({name for name, _inferred_type in schema}) != len(schema):
            raise ValueError("The source file contains duplicate column names")
        return schema

    def profile(
        self,
        dataset_id: str,
        path: Path,
        file_type: DatasetFileType,
        schema: list[tuple[str, str]] | None = None,
    ) -> ScanProfile:
        active_schema = schema or self.detect_schema(path, file_type)
        column_names = [name for name, _inferred_type in active_schema]
        inferred_types = [inferred_type for _name, inferred_type in active_schema]

        relation = source_relation(file_type)
        aggregates = ["count(*) AS row_count"]
        for index, column_name in enumerate(column_names):
            identifier = quote_identifier(column_name)
            aggregates.extend(
                [
                    f"count(*) FILTER (WHERE {identifier} IS NULL) AS null_{index}",
                    f"approx_count_distinct({identifier}) AS distinct_{index}",
                    f"min(CAST({identifier} AS VARCHAR)) AS min_{index}",
                    f"max(CAST({identifier} AS VARCHAR)) AS max_{index}",
                ]
            )
        aggregate_row = self._connection.execute(
            f"SELECT {', '.join(aggregates)} FROM {relation}",
            {"source_path": str(path)},
        ).fetchone()
        if aggregate_row is None:
            raise RuntimeError("Profile query returned no row")

        sample_rows = self._connection.execute(
            f"SELECT {', '.join(quote_identifier(name) for name in column_names)} "
            f"FROM {relation} LIMIT {PROFILE_SAMPLE_ROWS}",
            {"source_path": str(path)},
        ).fetchall()
        samples: list[list[str]] = [[] for _ in column_names]
        for row in sample_rows:
            for index, value in enumerate(row):
                if value is None or len(samples[index]) >= PROFILE_SAMPLE_VALUES:
                    continue
                rendered = str(value)
                if rendered not in samples[index]:
                    samples[index].append(rendered)

        columns: list[ColumnProfileRecord] = []
        for index, (name, inferred_type) in enumerate(
            zip(column_names, inferred_types, strict=True)
        ):
            offset = 1 + index * 4
            columns.append(
                ColumnProfileRecord(
                    dataset_id=dataset_id,
                    ordinal_position=index + 1,
                    column_name=name,
                    inferred_type=inferred_type,
                    null_count=int(aggregate_row[offset]),
                    approx_distinct=int(aggregate_row[offset + 1]),
                    min_value=(
                        None
                        if aggregate_row[offset + 2] is None
                        else str(aggregate_row[offset + 2])
                    ),
                    max_value=(
                        None
                        if aggregate_row[offset + 3] is None
                        else str(aggregate_row[offset + 3])
                    ),
                    sample_values=tuple(samples[index]),
                )
            )
        return ScanProfile(row_count=int(aggregate_row[0]), columns=columns)

    def preview(
        self,
        path: Path,
        file_type: DatasetFileType,
        limit: int,
    ) -> tuple[list[str], list[dict[str, JsonValue]]]:
        relation = source_relation(file_type)
        cursor = self._connection.execute(
            f"SELECT * FROM {relation} LIMIT $preview_limit",
            {"source_path": str(path), "preview_limit": limit},
        )
        column_names = [str(description[0]) for description in cursor.description]
        rows = [
            {
                column_name: _json_value(value)
                for column_name, value in zip(column_names, row, strict=True)
            }
            for row in cursor.fetchall()
        ]
        return column_names, rows

    def timestamp_preview(
        self,
        path: Path,
        file_type: DatasetFileType,
        mapping: MappingRecord,
    ) -> list[TimestampPreview]:
        relation = source_relation(file_type)
        timestamp_identifier = quote_identifier(mapping.timestamp_column)
        parsed_expression = timestamp_parse_expression(
            timestamp_identifier,
            mapping.timestamp_format,
        )
        utc_expression = timestamp_utc_expression(
            timestamp_identifier,
            mapping.timestamp_format,
        )
        aware_expression = timestamp_is_aware_expression(timestamp_identifier)
        parameters: dict[str, object] = {
            "source_path": str(path),
            "source_timezone": mapping.timezone,
            "display_timezone": mapping.display_timezone or mapping.timezone,
        }
        if mapping.timestamp_format is not None:
            parameters["timestamp_format"] = mapping.timestamp_format
        rows = self._connection.execute(
            f"""
            SELECT
                CAST({timestamp_identifier} AS VARCHAR) AS source_value,
                CAST({parsed_expression} AS VARCHAR) AS parsed_value,
                CASE WHEN {utc_expression} IS NULL THEN NULL
                     ELSE CAST({utc_expression} AS VARCHAR) || 'Z' END AS utc_value,
                CASE WHEN {utc_expression} IS NULL THEN NULL
                     ELSE CAST(
                         timezone(
                             $display_timezone,
                             timezone('UTC', {utc_expression})
                         ) AS VARCHAR
                     ) || ' ' || $display_timezone END AS display_value,
                {aware_expression} AS timezone_aware
            FROM {relation}
            WHERE {timestamp_identifier} IS NOT NULL
            LIMIT 5
            """,
            parameters,
        ).fetchall()
        return [
            TimestampPreview(
                source_value=str(row[0]),
                parsed_value=None if row[1] is None else str(row[1]),
                utc_value=None if row[2] is None else str(row[2]),
                display_value=None if row[3] is None else str(row[3]),
                timezone_aware=bool(row[4]),
            )
            for row in rows
        ]

    def timestamp_requires_source_timezone(
        self,
        path: Path,
        file_type: DatasetFileType,
        timestamp_column: str,
    ) -> bool:
        relation = source_relation(file_type)
        identifier = quote_identifier(timestamp_column)
        row = self._connection.execute(
            f"""
            SELECT count(*) > 0
            FROM {relation}
            WHERE {identifier} IS NOT NULL
              AND trim(CAST({identifier} AS VARCHAR)) <> ''
              AND NOT ({timestamp_is_aware_expression(identifier)})
            """,
            {"source_path": str(path)},
        ).fetchone()
        return bool(row and row[0])

    def validate_timestamp_format(
        self,
        path: Path,
        file_type: DatasetFileType,
        timestamp_column: str,
        timestamp_format: str,
    ) -> None:
        relation = source_relation(file_type)
        identifier = quote_identifier(timestamp_column)
        self._connection.execute(
            f"""
            SELECT try_strptime(CAST({identifier} AS VARCHAR), $timestamp_format)
            FROM {relation}
            WHERE {identifier} IS NOT NULL
            LIMIT 1
            """,
            {"source_path": str(path), "timestamp_format": timestamp_format},
        ).fetchall()


def timestamp_parse_expression(identifier: str, timestamp_format: str | None) -> str:
    if timestamp_format is None:
        return f"try_cast({identifier} AS TIMESTAMP)"
    return f"try_strptime(CAST({identifier} AS VARCHAR), $timestamp_format)"


def timestamp_is_aware_expression(identifier: str) -> str:
    return (
        "regexp_matches(trim(CAST("
        f"{identifier}"
        " AS VARCHAR)), '(Z|[+-][0-9]{2}:?[0-9]{2}|[A-Za-z_]+/[A-Za-z_]+)$', 'i')"
    )


def timestamp_utc_expression(identifier: str, timestamp_format: str | None) -> str:
    naive = timestamp_parse_expression(identifier, timestamp_format)
    if timestamp_format is None:
        aware = f"try_cast({identifier} AS TIMESTAMPTZ)"
    else:
        aware = (
            "try_cast(try_strptime(CAST("
            f"{identifier}"
            " AS VARCHAR), $timestamp_format) AS TIMESTAMPTZ)"
        )
    return (
        "CASE WHEN "
        f"{timestamp_is_aware_expression(identifier)} "
        f"THEN timezone('UTC', {aware}) "
        f"ELSE timezone('UTC', timezone($source_timezone, {naive})) END"
    )


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return f"<binary:{len(value)} bytes>"
    return str(value)
