from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from duckdb import DuckDBPyConnection

from app.datasets.domain import (
    DatasetRecord,
    MappingRecord,
    QualityReportRecord,
    SemanticContractRecord,
)
from app.datasets.scanner import quote_identifier, source_relation, timestamp_utc_expression
from app.datasets.storage import DatasetStorage
from app.schemas.datasets import RetentionPolicy


@dataclass(frozen=True)
class NormalizationArtifacts:
    normalized_path: Path
    quarantine_path: Path
    quality: QualityReportRecord
    validation_seconds: float
    normalization_seconds: float
    quarantine_seconds: float


class DatasetNormalizer:
    def __init__(self, connection: DuckDBPyConnection, storage: DatasetStorage) -> None:
        self._connection = connection
        self._storage = storage

    def normalize(
        self,
        dataset: DatasetRecord,
        mapping: MappingRecord,
        contract: SemanticContractRecord,
        source_path: Path,
        pseudonymization_key: bytes | None,
        large_case_event_threshold: int,
    ) -> NormalizationArtifacts:
        normalized_path, quarantine_path, validation_path = (
            self._storage.normalization_paths(dataset.dataset_id, mapping.version)
        )
        normalized_temp = self._storage.atomic_temp_path(normalized_path)
        quarantine_temp = self._storage.atomic_temp_path(quarantine_path)
        for path in (normalized_temp, quarantine_temp, validation_path):
            self._storage.remove_file(path)

        try:
            validation_started_at = perf_counter()
            self._materialize_validation(dataset, mapping, contract, source_path, validation_path)
            quality = self._measure_quality(
                dataset.dataset_id,
                mapping.version,
                validation_path,
                large_case_event_threshold,
            )
            validation_seconds = perf_counter() - validation_started_at
            normalization_started_at = perf_counter()
            self._write_normalized(
                dataset,
                mapping,
                contract,
                validation_path,
                normalized_temp,
                pseudonymization_key,
            )
            normalization_seconds = perf_counter() - normalization_started_at
            quarantine_started_at = perf_counter()
            self._write_quarantine(dataset, mapping, validation_path, quarantine_temp)
            quarantine_seconds = perf_counter() - quarantine_started_at
            # The canonical artifact is replaced last. A failed run can never expose
            # a partial normalized Parquet as the active production artifact.
            self._storage.finalize_atomic(quarantine_temp, quarantine_path)
            self._storage.finalize_atomic(normalized_temp, normalized_path)
            return NormalizationArtifacts(
                normalized_path=normalized_path,
                quarantine_path=quarantine_path,
                quality=quality,
                validation_seconds=validation_seconds,
                normalization_seconds=normalization_seconds,
                quarantine_seconds=quarantine_seconds,
            )
        except Exception:
            self._storage.remove_file(normalized_temp)
            self._storage.remove_file(quarantine_temp)
            raise
        finally:
            self._storage.remove_file(validation_path)

    def _materialize_validation(
        self,
        dataset: DatasetRecord,
        mapping: MappingRecord,
        contract: SemanticContractRecord,
        source_path: Path,
        validation_path: Path,
    ) -> None:
        relation = source_relation(dataset.file_type)
        case_identifier = quote_identifier(mapping.case_id_column)
        activity_identifier = quote_identifier(mapping.activity_column)
        timestamp_identifier = quote_identifier(mapping.timestamp_column)
        event_expression = _mapped_text(mapping.event_id_column)
        optional = mapping.optional_mappings
        parsed_timestamp = timestamp_utc_expression(
            quote_identifier("timestamp_value"),
            mapping.timestamp_format,
        )
        parameters: dict[str, object] = {
            "source_path": str(source_path),
            "validation_path": str(validation_path),
            "source_timezone": contract.source_timezone,
        }
        if mapping.timestamp_format is not None:
            parameters["timestamp_format"] = mapping.timestamp_format

        self._connection.execute(
            f"""
            COPY (
                WITH mapped AS (
                    SELECT
                        row_number() OVER () AS source_row_number,
                        CAST({case_identifier} AS VARCHAR) AS case_value,
                        CAST({activity_identifier} AS VARCHAR) AS activity_value,
                        CAST({timestamp_identifier} AS VARCHAR) AS timestamp_value,
                        {event_expression} AS event_value,
                        {_mapped_text(optional.get('resource'))} AS resource_value,
                        {_mapped_text(optional.get('user'))} AS user_value,
                        {_mapped_text(optional.get('system'))} AS system_value,
                        {_mapped_text(optional.get('method'))} AS method_value,
                        {_mapped_text(optional.get('department'))} AS department_value,
                        {_mapped_text(optional.get('status'))} AS status_value,
                        {_mapped_text(optional.get('duration'))} AS duration_value,
                        {_mapped_text(optional.get('source_sequence'))} AS source_sequence_value
                    FROM {relation}
                ),
                parsed AS (
                    SELECT
                        *,
                        {parsed_timestamp} AS parsed_ts,
                        case_value IS NULL AS null_case_id,
                        case_value IS NOT NULL AND trim(case_value) = '' AS empty_case_id,
                        activity_value IS NULL AS null_activity,
                        activity_value IS NOT NULL AND trim(activity_value) = '' AS empty_activity,
                        timestamp_value IS NULL AS null_timestamp
                    FROM mapped
                ),
                keyed AS (
                    SELECT
                        *,
                        timestamp_value IS NOT NULL
                            AND trim(timestamp_value) <> ''
                            AND parsed_ts IS NULL AS invalid_timestamp,
                        CASE
                            WHEN event_value IS NOT NULL AND trim(event_value) <> ''
                                THEN 'event:' || trim(event_value)
                            ELSE concat_ws(
                                ':',
                                'composite',
                                coalesce(trim(case_value), '<null>'),
                                coalesce(trim(activity_value), '<null>'),
                                coalesce(CAST(parsed_ts AS VARCHAR), '<null>')
                            )
                        END AS duplicate_key,
                        count(*) OVER (
                            PARTITION BY case_value, parsed_ts
                        ) AS same_timestamp_count
                    FROM parsed
                )
                SELECT
                    *,
                    count(*) OVER (PARTITION BY duplicate_key) > 1 AS duplicate_event,
                    case_value IS NOT NULL
                        AND trim(case_value) <> ''
                        AND parsed_ts IS NOT NULL
                        AND same_timestamp_count > 1 AS duplicate_timestamp
                FROM keyed
            ) TO $validation_path (
                FORMAT PARQUET,
                COMPRESSION ZSTD,
                ROW_GROUP_SIZE 122880
            )
            """,
            parameters,
        )

    def _measure_quality(
        self,
        dataset_id: str,
        mapping_version: int,
        validation_path: Path,
        large_case_event_threshold: int,
    ) -> QualityReportRecord:
        valid_condition = _valid_condition()
        row = self._connection.execute(
            f"""
            WITH assessed AS (
                SELECT *, {valid_condition} AS is_valid
                FROM read_parquet($validation_path)
            ),
            valid_case_counts AS (
                SELECT trim(case_value) AS case_id, count(*) AS event_count
                FROM assessed
                WHERE is_valid
                GROUP BY trim(case_value)
            ),
            ambiguous_cases AS (
                SELECT DISTINCT trim(case_value) AS case_id
                FROM assessed
                WHERE is_valid
                  AND duplicate_timestamp
                  AND try_cast(source_sequence_value AS BIGINT) IS NULL
                  AND (event_value IS NULL OR trim(event_value) = '')
            )
            SELECT
                count(*) AS total_rows,
                count(*) FILTER (WHERE is_valid) AS valid_events,
                count(*) FILTER (WHERE NOT is_valid) AS invalid_events,
                count(DISTINCT trim(case_value)) FILTER (WHERE is_valid) AS unique_cases,
                count(DISTINCT trim(activity_value)) FILTER (WHERE is_valid) AS unique_activities,
                count(*) FILTER (WHERE null_case_id) AS null_case_id,
                count(*) FILTER (WHERE empty_case_id) AS empty_case_id,
                count(*) FILTER (WHERE null_activity) AS null_activity,
                count(*) FILTER (WHERE empty_activity) AS empty_activity,
                count(*) FILTER (WHERE null_timestamp) AS null_timestamp,
                count(*) FILTER (WHERE invalid_timestamp) AS invalid_timestamp,
                count(*) FILTER (WHERE duplicate_event) AS duplicate_events,
                count(*) FILTER (WHERE duplicate_timestamp) AS duplicate_timestamp_rows,
                (SELECT count(*) FROM valid_case_counts WHERE event_count = 1)
                    AS single_event_cases,
                (SELECT count(*) FROM ambiguous_cases) AS ambiguous_ordering_cases,
                coalesce((SELECT min(event_count) FROM valid_case_counts), 0)
                    AS events_per_case_min,
                coalesce((SELECT median(event_count) FROM valid_case_counts), 0)
                    AS events_per_case_median,
                coalesce((SELECT quantile_cont(event_count, 0.90) FROM valid_case_counts), 0)
                    AS events_per_case_p90,
                coalesce((SELECT max(event_count) FROM valid_case_counts), 0)
                    AS events_per_case_max,
                (SELECT count(*) FROM valid_case_counts WHERE event_count > $large_case_threshold)
                    AS extremely_large_cases
            FROM assessed
            """,
            {
                "validation_path": str(validation_path),
                "large_case_threshold": large_case_event_threshold,
            },
        ).fetchone()
        if row is None:
            raise RuntimeError("Data quality query returned no row")
        valid_events = int(row[1])
        invalid_events = int(row[2])
        if valid_events == 0:
            outcome = "FAILED_NO_VALID_EVENTS"
        elif invalid_events > 0:
            outcome = "PASSED_WITH_QUARANTINE"
        else:
            outcome = "PASSED"
        return QualityReportRecord(
            dataset_id=dataset_id,
            mapping_version=mapping_version,
            total_rows=int(row[0]),
            valid_events=valid_events,
            invalid_events=invalid_events,
            unique_cases=int(row[3]),
            unique_activities=int(row[4]),
            null_case_id=int(row[5]),
            empty_case_id=int(row[6]),
            null_activity=int(row[7]),
            empty_activity=int(row[8]),
            null_timestamp=int(row[9]),
            invalid_timestamp=int(row[10]),
            duplicate_events=int(row[11]),
            duplicate_timestamp_rows=int(row[12]),
            single_event_cases=int(row[13]),
            ambiguous_ordering_cases=int(row[14]),
            events_per_case_min=int(row[15]),
            events_per_case_median=float(row[16]),
            events_per_case_p90=float(row[17]),
            events_per_case_max=int(row[18]),
            extremely_large_cases=int(row[19]),
            source_timezone_missing=False,
            timestamps_outside_dataset_range=0,
            outcome=outcome,
            measured_at=datetime.now(UTC),
        )

    def _write_normalized(
        self,
        dataset: DatasetRecord,
        mapping: MappingRecord,
        contract: SemanticContractRecord,
        validation_path: Path,
        normalized_path: Path,
        pseudonymization_key: bytes | None,
    ) -> None:
        valid_condition = _valid_condition()
        mapping_version = f"mapping-v{mapping.version}"
        case_rule_version = f"case-column-v{mapping.version}"
        needs_hmac = contract.case_id_pseudonymized or any(
            policy == RetentionPolicy.PSEUDONYMIZE
            for policy in contract.attribute_policies.values()
        )
        if needs_hmac and pseudonymization_key is None:
            raise ValueError("Pseudonymization is enabled but no key is available")
        hmac_parameters: dict[str, object] = {}
        if needs_hmac and pseudonymization_key is not None:
            inner_pad, outer_pad = _hmac_sha256_pads(pseudonymization_key)
            hmac_parameters = {
                "hmac_inner_pad": inner_pad,
                "hmac_outer_pad": outer_pad,
            }
        case_expression = (
            _hmac_expression("trim(case_value)")
            if contract.case_id_pseudonymized
            else "trim(case_value)"
        )
        retained_event_id = _retained_expression("event_value", "event_id", contract)
        self._connection.execute(
            f"""
            COPY (
                SELECT
                    coalesce(
                        {retained_event_id},
                        sha256($dataset_id || ':' || CAST(source_row_number AS VARCHAR))
                    ) AS event_id,
                    {case_expression} AS case_id,
                    trim(activity_value) AS activity,
                    parsed_ts AS event_ts,
                    CAST(NULL AS VARCHAR) AS process_domain,
                    coalesce(
                        {_retained_expression('system_value', 'system', contract)},
                        'uploaded_file'
                    ) AS source_system,
                    CAST(NULL AS VARCHAR) AS source_class,
                    {_retained_expression('method_value', 'method', contract)}
                        AS source_method,
                    CAST(NULL AS VARCHAR) AS module,
                    CAST(NULL AS VARCHAR) AS lifecycle,
                    {_retained_expression('department_value', 'department', contract)}
                        AS org_code,
                    CAST(NULL AS VARCHAR) AS actor_hash,
                    {_retained_expression('status_value', 'status', contract)}
                        AS result_code,
                    CASE
                        WHEN {_policy_value('duration', contract)} = 'DROP' THEN NULL
                        ELSE try_cast(duration_value AS BIGINT)
                    END AS duration_ms,
                    CASE
                        WHEN {_policy_value('source_sequence', contract)} = 'DROP' THEN NULL
                        ELSE try_cast(source_sequence_value AS BIGINT)
                    END AS source_sequence,
                    source_row_number AS ingest_sequence,
                    $mapping_version AS mapping_version,
                    $case_rule_version AS case_rule_version,
                    $dataset_id AS ingestion_batch_id,
                    CAST(parsed_ts AS DATE) AS event_date,
                    $source_timezone AS source_timezone,
                    {retained_event_id} AS source_event_id,
                    {_retained_expression('resource_value', 'resource', contract)}
                        AS resource,
                    {_retained_expression('user_value', 'user', contract)} AS user
                FROM read_parquet($validation_path)
                WHERE {valid_condition}
            ) TO $normalized_path (
                FORMAT PARQUET,
                COMPRESSION ZSTD,
                ROW_GROUP_SIZE 122880
            )
            """,
            {
                "normalized_path": str(normalized_path),
                "validation_path": str(validation_path),
                "dataset_id": dataset.dataset_id,
                "mapping_version": mapping_version,
                "case_rule_version": case_rule_version,
                "source_timezone": contract.source_timezone,
                **hmac_parameters,
            },
        )

    def _write_quarantine(
        self,
        dataset: DatasetRecord,
        mapping: MappingRecord,
        validation_path: Path,
        quarantine_path: Path,
    ) -> None:
        valid_condition = _valid_condition()
        self._connection.execute(
            f"""
            COPY (
                SELECT
                    source_row_number,
                    concat_ws(
                        '|',
                        CASE WHEN null_case_id THEN 'NULL_CASE_ID' END,
                        CASE WHEN empty_case_id THEN 'EMPTY_CASE_ID' END,
                        CASE WHEN null_activity THEN 'NULL_ACTIVITY' END,
                        CASE WHEN empty_activity THEN 'EMPTY_ACTIVITY' END,
                        CASE WHEN null_timestamp THEN 'NULL_TIMESTAMP' END,
                        CASE WHEN invalid_timestamp THEN 'INVALID_TIMESTAMP' END,
                        CASE WHEN duplicate_event THEN 'DUPLICATE_EVENT' END
                    ) AS failure_code,
                    'Technical event-log validation failed' AS failure_reason,
                    $dataset_id AS dataset_id,
                    $mapping_version AS mapping_version
                FROM read_parquet($validation_path)
                WHERE NOT ({valid_condition})
            ) TO $quarantine_path (
                FORMAT PARQUET,
                COMPRESSION ZSTD
            )
            """,
            {
                "quarantine_path": str(quarantine_path),
                "validation_path": str(validation_path),
                "dataset_id": dataset.dataset_id,
                "mapping_version": mapping.version,
            },
        )


def _mapped_text(column_name: str | None) -> str:
    if column_name is None:
        return "CAST(NULL AS VARCHAR)"
    return f"CAST({quote_identifier(column_name)} AS VARCHAR)"


def _policy_value(logical_name: str, contract: SemanticContractRecord) -> str:
    return f"'{contract.attribute_policies.get(logical_name, RetentionPolicy.DROP).value}'"


def _retained_expression(
    validation_column: str,
    logical_name: str,
    contract: SemanticContractRecord,
) -> str:
    policy = contract.attribute_policies.get(logical_name, RetentionPolicy.DROP)
    value = f"nullif(trim({validation_column}), '')"
    if policy == RetentionPolicy.DROP:
        return "CAST(NULL AS VARCHAR)"
    if policy == RetentionPolicy.PSEUDONYMIZE:
        return f"CASE WHEN {value} IS NULL THEN NULL ELSE {_hmac_expression(value)} END"
    return value


def _hmac_expression(value_expression: str) -> str:
    return (
        "sha256($hmac_outer_pad::BLOB || unhex(sha256("
        f"$hmac_inner_pad::BLOB || encode({value_expression})"
        ")))"
    )


def _hmac_sha256_pads(key: bytes) -> tuple[bytes, bytes]:
    normalized = hashlib.sha256(key).digest() if len(key) > 64 else key
    block = normalized + bytes(64 - len(normalized))
    inner_pad = bytes(value ^ 0x36 for value in block)
    outer_pad = bytes(value ^ 0x5C for value in block)
    return inner_pad, outer_pad


def _valid_condition() -> str:
    return """
        NOT null_case_id
        AND NOT empty_case_id
        AND NOT null_activity
        AND NOT empty_activity
        AND NOT null_timestamp
        AND NOT invalid_timestamp
        AND NOT duplicate_event
    """
