from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from duckdb import DuckDBPyConnection

from app.datasets.domain import (
    ActivityMappingEntryRecord,
    ActivityMappingSetRecord,
    ArtifactRecord,
    ColumnProfileRecord,
    DatasetRecord,
    MappingRecord,
    QualityReportRecord,
    SemanticContractRecord,
    require_status_transition,
)
from app.schemas.datasets import (
    ActivityMappingSetCreateRequest,
    ArtifactType,
    DatasetFileType,
    DatasetStatus,
    ImportMode,
    MappingCreateRequest,
    NormalizationStatus,
    PIIClassification,
    RetentionPolicy,
    UnmappedActivityPolicy,
)


class DatasetRepository:
    def __init__(self, connection: DuckDBPyConnection) -> None:
        self._connection = connection

    def create_dataset(self, record: DatasetRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO meta.dataset (
                dataset_id, original_filename, staged_filename, file_type,
                file_size_bytes, checksum, created_at, status, row_count,
                column_count, schema_version, mapping_version,
                normalization_version, normalization_status, normalized_filename,
                normalized_file_size_bytes, quarantine_filename,
                quarantine_file_size_bytes, source_type, error_code, source_path,
                source_mtime_ns, import_mode, semantic_contract_version,
                active_activity_mapping_version, current_step, operation_started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.dataset_id,
                record.original_filename,
                record.staged_filename,
                record.file_type.value,
                record.file_size_bytes,
                record.checksum,
                record.created_at,
                record.status.value,
                record.row_count,
                record.column_count,
                record.schema_version,
                record.mapping_version,
                record.normalization_version,
                record.normalization_status.value,
                record.normalized_filename,
                record.normalized_file_size_bytes,
                record.quarantine_filename,
                record.quarantine_file_size_bytes,
                record.source_type,
                record.error_code,
                record.source_path,
                record.source_mtime_ns,
                record.import_mode.value if record.import_mode else None,
                record.semantic_contract_version,
                record.active_activity_mapping_version,
                record.current_step,
                record.operation_started_at,
            ],
        )

    def get_dataset(self, dataset_id: str) -> DatasetRecord | None:
        row = self._connection.execute(
            """
            SELECT
                dataset_id, original_filename, staged_filename, file_type,
                file_size_bytes, checksum, created_at, status, row_count,
                column_count, schema_version, mapping_version,
                normalization_version, normalization_status, normalized_filename,
                normalized_file_size_bytes, quarantine_filename,
                quarantine_file_size_bytes, source_type, error_code, source_path,
                source_mtime_ns, import_mode, semantic_contract_version,
                active_activity_mapping_version, current_step, operation_started_at
            FROM meta.dataset
            WHERE dataset_id = ?
            """,
            [dataset_id],
        ).fetchone()
        return None if row is None else self._dataset_from_row(row)

    def list_datasets(self) -> list[DatasetRecord]:
        rows = self._connection.execute(
            """
            SELECT
                dataset_id, original_filename, staged_filename, file_type,
                file_size_bytes, checksum, created_at, status, row_count,
                column_count, schema_version, mapping_version,
                normalization_version, normalization_status, normalized_filename,
                normalized_file_size_bytes, quarantine_filename,
                quarantine_file_size_bytes, source_type, error_code, source_path,
                source_mtime_ns, import_mode, semantic_contract_version,
                active_activity_mapping_version, current_step, operation_started_at
            FROM meta.dataset
            ORDER BY created_at DESC, dataset_id ASC
            """
        ).fetchall()
        return [self._dataset_from_row(row) for row in rows]

    def update_staged_file(self, dataset_id: str, size: int, checksum: str) -> DatasetRecord:
        self.transition_status(dataset_id, DatasetStatus.STAGED)
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET file_size_bytes = ?, checksum = ?, error_code = NULL
            WHERE dataset_id = ?
            """,
            [size, checksum, dataset_id],
        )
        return self.require_dataset(dataset_id)

    def update_reference_source(
        self,
        dataset_id: str,
        *,
        size: int,
        checksum: str,
        source_path: str,
        source_mtime_ns: int,
    ) -> DatasetRecord:
        self.transition_status(dataset_id, DatasetStatus.STAGED)
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET file_size_bytes = ?, checksum = ?, source_path = ?,
                source_mtime_ns = ?, error_code = NULL
            WHERE dataset_id = ?
            """,
            [size, checksum, source_path, source_mtime_ns, dataset_id],
        )
        return self.require_dataset(dataset_id)

    def transition_status(
        self,
        dataset_id: str,
        target: DatasetStatus,
        *,
        error_code: str | None = None,
        normalization_status: NormalizationStatus | None = None,
    ) -> DatasetRecord:
        current = self.require_dataset(dataset_id)
        require_status_transition(current.status, target)
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET status = ?, error_code = ?,
                normalization_status = coalesce(?, normalization_status)
            WHERE dataset_id = ?
            """,
            [
                target.value,
                error_code,
                normalization_status.value if normalization_status else None,
                dataset_id,
            ],
        )
        return self.require_dataset(dataset_id)

    def set_operation(self, dataset_id: str, step: str | None) -> None:
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET current_step = ?, operation_started_at =
                CASE WHEN ? IS NULL THEN NULL ELSE current_timestamp END
            WHERE dataset_id = ?
            """,
            [step, step, dataset_id],
        )

    def save_profile(
        self,
        dataset_id: str,
        row_count: int,
        columns: list[ColumnProfileRecord],
    ) -> DatasetRecord:
        self._connection.execute(
            "DELETE FROM meta.dataset_column_profile WHERE dataset_id = ?",
            [dataset_id],
        )
        if columns:
            self._connection.executemany(
                """
                INSERT INTO meta.dataset_column_profile (
                    dataset_id, ordinal_position, column_name, inferred_type,
                    null_count, approx_distinct, min_value, max_value,
                    sample_values_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        column.dataset_id,
                        column.ordinal_position,
                        column.column_name,
                        column.inferred_type,
                        column.null_count,
                        column.approx_distinct,
                        column.min_value,
                        column.max_value,
                        json.dumps(column.sample_values, ensure_ascii=False),
                    )
                    for column in columns
                ],
            )
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET row_count = ?, column_count = ?
            WHERE dataset_id = ?
            """,
            [row_count, len(columns), dataset_id],
        )
        self.transition_status(dataset_id, DatasetStatus.PROFILED)
        return self.transition_status(dataset_id, DatasetStatus.MAPPING_REQUIRED)

    def get_profile(self, dataset_id: str) -> list[ColumnProfileRecord]:
        rows = self._connection.execute(
            """
            SELECT
                dataset_id, ordinal_position, column_name, inferred_type,
                null_count, approx_distinct, min_value, max_value,
                sample_values_json
            FROM meta.dataset_column_profile
            WHERE dataset_id = ?
            ORDER BY ordinal_position ASC
            """,
            [dataset_id],
        ).fetchall()
        records: list[ColumnProfileRecord] = []
        for row in rows:
            raw_samples: object = json.loads(str(row[8]))
            if not isinstance(raw_samples, list) or not all(
                isinstance(value, str) for value in raw_samples
            ):
                raise RuntimeError("Stored column profile samples are invalid")
            records.append(
                ColumnProfileRecord(
                    dataset_id=str(row[0]),
                    ordinal_position=int(row[1]),
                    column_name=str(row[2]),
                    inferred_type=str(row[3]),
                    null_count=int(row[4]),
                    approx_distinct=int(row[5]),
                    min_value=None if row[6] is None else str(row[6]),
                    max_value=None if row[7] is None else str(row[7]),
                    sample_values=tuple(cast(list[str], raw_samples)),
                )
            )
        return records

    def create_mapping(
        self,
        dataset_id: str,
        request: MappingCreateRequest,
    ) -> MappingRecord:
        version_row = self._connection.execute(
            """
            SELECT coalesce(max(version), 0) + 1
            FROM meta.mapping_definition
            WHERE dataset_id = ?
            """,
            [dataset_id],
        ).fetchone()
        if version_row is None:
            raise RuntimeError("Mapping version query returned no row")
        version = int(version_row[0])
        mapping = MappingRecord(
            mapping_id=str(uuid4()),
            dataset_id=dataset_id,
            version=version,
            case_id_column=request.case_id_column,
            activity_column=request.activity_column,
            timestamp_column=request.timestamp_column,
            event_id_column=request.event_id_column,
            optional_mappings=dict(request.optional_mappings),
            timestamp_format=request.timestamp_format,
            timezone=request.timezone,
            display_timezone=request.display_timezone or request.timezone,
            created_at=datetime.now(UTC),
        )
        self._connection.execute(
            """
            INSERT INTO meta.mapping_definition (
                mapping_id, dataset_id, version, case_id_column, activity_column,
                timestamp_column, event_id_column, optional_mappings_json,
                timestamp_format, timezone, created_at, display_timezone
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                mapping.mapping_id,
                mapping.dataset_id,
                mapping.version,
                mapping.case_id_column,
                mapping.activity_column,
                mapping.timestamp_column,
                mapping.event_id_column,
                json.dumps(mapping.optional_mappings, ensure_ascii=False, sort_keys=True),
                mapping.timestamp_format,
                mapping.timezone,
                mapping.created_at,
                mapping.display_timezone,
            ],
        )
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET mapping_version = ?, normalization_status = ?, error_code = NULL
            WHERE dataset_id = ?
            """,
            [version, NormalizationStatus.NOT_STARTED.value, dataset_id],
        )
        self.transition_status(dataset_id, DatasetStatus.MAPPING_REQUIRED)
        return mapping

    def get_latest_mapping(self, dataset_id: str) -> MappingRecord | None:
        mappings = self.list_mappings(dataset_id)
        return mappings[0] if mappings else None

    def list_mappings(self, dataset_id: str) -> list[MappingRecord]:
        rows = self._connection.execute(
            """
            SELECT
                mapping_id, dataset_id, version, case_id_column, activity_column,
                timestamp_column, event_id_column, optional_mappings_json,
                timestamp_format, timezone, created_at, display_timezone
            FROM meta.mapping_definition
            WHERE dataset_id = ?
            ORDER BY version DESC
            """,
            [dataset_id],
        ).fetchall()
        return [self._mapping_from_row(row) for row in rows]

    @staticmethod
    def _mapping_from_row(row: tuple[object, ...]) -> MappingRecord:
        raw_optional: object = json.loads(str(row[7]))
        if not isinstance(raw_optional, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in raw_optional.items()
        ):
            raise RuntimeError("Stored optional mappings are invalid")
        return MappingRecord(
            mapping_id=str(row[0]),
            dataset_id=str(row[1]),
            version=cast(int, row[2]),
            case_id_column=str(row[3]),
            activity_column=str(row[4]),
            timestamp_column=str(row[5]),
            event_id_column=None if row[6] is None else str(row[6]),
            optional_mappings=cast(dict[str, str], raw_optional),
            timestamp_format=None if row[8] is None else str(row[8]),
            timezone=None if row[9] is None else str(row[9]),
            created_at=cast(datetime, row[10]),
            display_timezone=None if row[11] is None else str(row[11]),
        )

    def create_semantic_contract(
        self,
        dataset_id: str,
        mapping: MappingRecord,
        request: MappingCreateRequest,
    ) -> SemanticContractRecord:
        version_row = self._connection.execute(
            "SELECT coalesce(max(version), 0) + 1 FROM meta.semantic_contract WHERE dataset_id = ?",
            [dataset_id],
        ).fetchone()
        if version_row is None:
            raise RuntimeError("Semantic Contract version query returned no row")
        version = int(version_row[0])
        attribute_policies: dict[str, RetentionPolicy] = {}
        pii_classifications: dict[str, PIIClassification] = {}
        policy_targets = set(request.optional_mappings)
        if request.event_id_column is not None:
            policy_targets.add("event_id")
        for logical_name in sorted(policy_targets):
            classification = request.pii_classifications.get(
                logical_name, PIIClassification.NONE
            )
            pii_classifications[logical_name] = classification
            default_policy = (
                RetentionPolicy.DROP
                if classification in {PIIClassification.PII, PIIClassification.SENSITIVE}
                else RetentionPolicy.KEEP
            )
            attribute_policies[logical_name] = request.attribute_policies.get(
                logical_name, default_policy
            )
        contract = SemanticContractRecord(
            contract_id=str(uuid4()),
            dataset_id=dataset_id,
            version=version,
            mapping_version=mapping.version,
            case_null_policy=request.case_null_policy,
            case_empty_policy=request.case_empty_policy,
            case_id_pseudonymized=request.case_id_pseudonymized,
            case_id_classification=request.case_id_classification,
            source_timezone=cast(str, request.timezone),
            display_timezone=request.display_timezone or cast(str, request.timezone),
            normalized_timezone="UTC",
            ordering_fields=tuple(request.ordering_fields),
            attribute_policies=attribute_policies,
            pii_classifications=pii_classifications,
            business_activity_mapping_version=request.business_activity_mapping_version,
            created_at=datetime.now(UTC),
            status="ACTIVE",
        )
        self._connection.execute(
            "UPDATE meta.semantic_contract SET status = 'SUPERSEDED' WHERE dataset_id = ?",
            [dataset_id],
        )
        self._connection.execute(
            """
            INSERT INTO meta.semantic_contract (
                contract_id, dataset_id, version, mapping_version,
                case_null_policy, case_empty_policy, case_id_pseudonymized,
                case_id_classification, source_timezone, display_timezone,
                normalized_timezone, ordering_fields_json, attribute_policy_json,
                pii_policy_json, business_activity_mapping_version, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                contract.contract_id,
                contract.dataset_id,
                contract.version,
                contract.mapping_version,
                contract.case_null_policy,
                contract.case_empty_policy,
                contract.case_id_pseudonymized,
                contract.case_id_classification.value,
                contract.source_timezone,
                contract.display_timezone,
                contract.normalized_timezone,
                json.dumps(contract.ordering_fields),
                json.dumps(
                    {key: value.value for key, value in contract.attribute_policies.items()},
                    sort_keys=True,
                ),
                json.dumps(
                    {key: value.value for key, value in contract.pii_classifications.items()},
                    sort_keys=True,
                ),
                contract.business_activity_mapping_version,
                contract.created_at,
                contract.status,
            ],
        )
        self._connection.execute(
            "UPDATE meta.dataset SET semantic_contract_version = ? WHERE dataset_id = ?",
            [contract.version, dataset_id],
        )
        return contract

    def list_semantic_contracts(self, dataset_id: str) -> list[SemanticContractRecord]:
        rows = self._connection.execute(
            """
            SELECT contract_id, dataset_id, version, mapping_version,
                   case_null_policy, case_empty_policy, case_id_pseudonymized,
                   case_id_classification, source_timezone, display_timezone,
                   normalized_timezone, ordering_fields_json, attribute_policy_json,
                   pii_policy_json, business_activity_mapping_version, created_at, status
            FROM meta.semantic_contract
            WHERE dataset_id = ?
            ORDER BY version DESC
            """,
            [dataset_id],
        ).fetchall()
        return [self._semantic_contract_from_row(row) for row in rows]

    def get_latest_semantic_contract(
        self, dataset_id: str
    ) -> SemanticContractRecord | None:
        contracts = self.list_semantic_contracts(dataset_id)
        return contracts[0] if contracts else None

    def create_activity_mapping_set(
        self,
        dataset_id: str,
        request: ActivityMappingSetCreateRequest,
    ) -> ActivityMappingSetRecord:
        row = self._connection.execute(
            """
            SELECT coalesce(max(version), 0) + 1
            FROM meta.activity_mapping_set
            WHERE dataset_id = ?
            """,
            [dataset_id],
        ).fetchone()
        if row is None:
            raise RuntimeError("Activity mapping version query returned no row")
        version = int(row[0])
        mapping_set_id = str(uuid4())
        created_at = datetime.now(UTC)
        self._connection.execute(
            "UPDATE meta.activity_mapping_set SET status = 'SUPERSEDED' WHERE dataset_id = ?",
            [dataset_id],
        )
        self._connection.execute(
            """
            INSERT INTO meta.activity_mapping_set (
                mapping_set_id, dataset_id, version, name, unmapped_policy,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            [
                mapping_set_id,
                dataset_id,
                version,
                request.name.strip(),
                request.unmapped_policy.value,
                created_at,
            ],
        )
        if request.entries:
            self._connection.executemany(
                """
                INSERT INTO meta.activity_mapping_entry (
                    mapping_set_id, source_activity, business_activity,
                    description, enabled
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        mapping_set_id,
                        entry.source_activity.strip(),
                        entry.business_activity.strip(),
                        entry.description,
                        entry.enabled,
                    )
                    for entry in request.entries
                ],
            )
        self._connection.execute(
            "UPDATE meta.dataset SET active_activity_mapping_version = ? WHERE dataset_id = ?",
            [version, dataset_id],
        )
        return cast(ActivityMappingSetRecord, self.get_activity_mapping_set(dataset_id, version))

    def get_activity_mapping_set(
        self, dataset_id: str, version: int
    ) -> ActivityMappingSetRecord | None:
        row = self._connection.execute(
            """
            SELECT mapping_set_id, dataset_id, version, name, unmapped_policy,
                   created_at, status
            FROM meta.activity_mapping_set
            WHERE dataset_id = ? AND version = ?
            """,
            [dataset_id, version],
        ).fetchone()
        if row is None:
            return None
        entry_rows = self._connection.execute(
            """
            SELECT source_activity, business_activity, description, enabled
            FROM meta.activity_mapping_entry
            WHERE mapping_set_id = ?
            ORDER BY source_activity
            """,
            [str(row[0])],
        ).fetchall()
        return ActivityMappingSetRecord(
            mapping_set_id=str(row[0]),
            dataset_id=str(row[1]),
            version=int(row[2]),
            name=str(row[3]),
            unmapped_policy=UnmappedActivityPolicy(str(row[4])),
            created_at=cast(datetime, row[5]),
            status=str(row[6]),
            entries=tuple(
                ActivityMappingEntryRecord(
                    source_activity=str(entry[0]),
                    business_activity=str(entry[1]),
                    description=None if entry[2] is None else str(entry[2]),
                    enabled=bool(entry[3]),
                )
                for entry in entry_rows
            ),
        )

    def list_activity_mapping_sets(self, dataset_id: str) -> list[ActivityMappingSetRecord]:
        versions = self._connection.execute(
            """
            SELECT version
            FROM meta.activity_mapping_set
            WHERE dataset_id = ?
            ORDER BY version DESC
            """,
            [dataset_id],
        ).fetchall()
        return [
            mapping_set
            for version in versions
            if (mapping_set := self.get_activity_mapping_set(dataset_id, int(version[0])))
            is not None
        ]

    def create_artifact(self, record: ArtifactRecord) -> None:
        if record.active:
            self._connection.execute(
                """
                UPDATE meta.dataset_artifact
                SET active = FALSE
                WHERE dataset_id = ? AND artifact_type = ?
                """,
                [record.dataset_id, record.artifact_type.value],
            )
        self._connection.execute(
            """
            INSERT INTO meta.dataset_artifact (
                artifact_id, dataset_id, semantic_contract_version, mapping_version,
                artifact_type, storage_area, relative_path, size_bytes, created_at,
                active, pinned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.artifact_id,
                record.dataset_id,
                record.semantic_contract_version,
                record.mapping_version,
                record.artifact_type.value,
                record.storage_area,
                record.relative_path,
                record.size_bytes,
                record.created_at,
                record.active,
                record.pinned,
            ],
        )

    def list_artifacts(self, dataset_id: str) -> list[ArtifactRecord]:
        rows = self._connection.execute(
            """
            SELECT artifact_id, dataset_id, semantic_contract_version,
                   mapping_version, artifact_type, storage_area, relative_path,
                   size_bytes, created_at, active, pinned
            FROM meta.dataset_artifact
            WHERE dataset_id = ?
            ORDER BY created_at DESC, artifact_id
            """,
            [dataset_id],
        ).fetchall()
        return [self._artifact_from_row(row) for row in rows]

    def get_artifact(self, dataset_id: str, artifact_id: str) -> ArtifactRecord | None:
        row = self._connection.execute(
            """
            SELECT artifact_id, dataset_id, semantic_contract_version,
                   mapping_version, artifact_type, storage_area, relative_path,
                   size_bytes, created_at, active, pinned
            FROM meta.dataset_artifact
            WHERE dataset_id = ? AND artifact_id = ?
            """,
            [dataset_id, artifact_id],
        ).fetchone()
        return None if row is None else self._artifact_from_row(row)

    def set_artifact_pinned(self, dataset_id: str, artifact_id: str, pinned: bool) -> None:
        self._connection.execute(
            "UPDATE meta.dataset_artifact SET pinned = ? WHERE dataset_id = ? AND artifact_id = ?",
            [pinned, dataset_id, artifact_id],
        )

    def delete_artifact(self, dataset_id: str, artifact_id: str) -> None:
        self._connection.execute(
            "DELETE FROM meta.dataset_artifact WHERE dataset_id = ? AND artifact_id = ?",
            [dataset_id, artifact_id],
        )

    def save_quality_report(self, report: QualityReportRecord) -> None:
        self._connection.execute(
            "DELETE FROM meta.dataset_quality_report WHERE dataset_id = ? AND mapping_version = ?",
            [report.dataset_id, report.mapping_version],
        )
        self._connection.execute(
            """
            INSERT INTO meta.dataset_quality_report (
                dataset_id, mapping_version, total_rows, valid_events,
                invalid_events, unique_cases, unique_activities, null_case_id,
                empty_case_id, null_activity, empty_activity, null_timestamp,
                invalid_timestamp, duplicate_events, duplicate_timestamp_rows,
                single_event_cases, ambiguous_ordering_cases, events_per_case_min,
                events_per_case_median, events_per_case_p90, events_per_case_max,
                extremely_large_cases, source_timezone_missing,
                timestamps_outside_dataset_range, outcome, measured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?)
            """,
            [
                report.dataset_id,
                report.mapping_version,
                report.total_rows,
                report.valid_events,
                report.invalid_events,
                report.unique_cases,
                report.unique_activities,
                report.null_case_id,
                report.empty_case_id,
                report.null_activity,
                report.empty_activity,
                report.null_timestamp,
                report.invalid_timestamp,
                report.duplicate_events,
                report.duplicate_timestamp_rows,
                report.single_event_cases,
                report.ambiguous_ordering_cases,
                report.events_per_case_min,
                report.events_per_case_median,
                report.events_per_case_p90,
                report.events_per_case_max,
                report.extremely_large_cases,
                report.source_timezone_missing,
                report.timestamps_outside_dataset_range,
                report.outcome,
                report.measured_at,
            ],
        )

    def get_quality_report(self, dataset_id: str) -> QualityReportRecord | None:
        row = self._connection.execute(
            """
            SELECT
                dataset_id, mapping_version, total_rows, valid_events,
                invalid_events, unique_cases, unique_activities, null_case_id,
                empty_case_id, null_activity, empty_activity, null_timestamp,
                invalid_timestamp, duplicate_events, duplicate_timestamp_rows,
                single_event_cases, ambiguous_ordering_cases, events_per_case_min,
                events_per_case_median, events_per_case_p90, events_per_case_max,
                extremely_large_cases, source_timezone_missing,
                timestamps_outside_dataset_range, outcome, measured_at
            FROM meta.dataset_quality_report
            WHERE dataset_id = ?
            ORDER BY mapping_version DESC
            LIMIT 1
            """,
            [dataset_id],
        ).fetchone()
        if row is None:
            return None
        return QualityReportRecord(
            dataset_id=str(row[0]),
            mapping_version=int(row[1]),
            total_rows=int(row[2]),
            valid_events=int(row[3]),
            invalid_events=int(row[4]),
            unique_cases=int(row[5]),
            unique_activities=int(row[6]),
            null_case_id=int(row[7]),
            empty_case_id=int(row[8]),
            null_activity=int(row[9]),
            empty_activity=int(row[10]),
            null_timestamp=int(row[11]),
            invalid_timestamp=int(row[12]),
            duplicate_events=int(row[13]),
            duplicate_timestamp_rows=int(row[14]),
            single_event_cases=int(row[15]),
            ambiguous_ordering_cases=int(row[16]),
            events_per_case_min=int(row[17]),
            events_per_case_median=float(row[18]),
            events_per_case_p90=float(row[19]),
            events_per_case_max=int(row[20]),
            extremely_large_cases=int(row[21]),
            source_timezone_missing=bool(row[22]),
            timestamps_outside_dataset_range=int(row[23]),
            outcome=str(row[24]),
            measured_at=cast(datetime, row[25]),
        )

    def finish_normalization(
        self,
        dataset_id: str,
        *,
        normalized_filename: str,
        normalized_size: int,
        quarantine_filename: str,
        quarantine_size: int,
        ready: bool,
    ) -> DatasetRecord:
        status = DatasetStatus.READY if ready else DatasetStatus.FAILED
        normalization_status = (
            NormalizationStatus.READY if ready else NormalizationStatus.FAILED
        )
        self._connection.execute(
            """
            UPDATE meta.dataset
            SET normalization_version = ?, normalization_status = ?,
                normalized_filename = ?, normalized_file_size_bytes = ?,
                quarantine_filename = ?, quarantine_file_size_bytes = ?,
                error_code = ?
            WHERE dataset_id = ?
            """,
            [
                "event-log-v1",
                normalization_status.value,
                normalized_filename,
                normalized_size,
                quarantine_filename,
                quarantine_size,
                None if ready else "NO_VALID_EVENTS",
                dataset_id,
            ],
        )
        return self.transition_status(
            dataset_id,
            status,
            error_code=None if ready else "NO_VALID_EVENTS",
            normalization_status=normalization_status,
        )

    def mark_failed(self, dataset_id: str, error_code: str) -> None:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            return
        self.transition_status(
            dataset_id,
            DatasetStatus.FAILED,
            error_code=error_code,
            normalization_status=(
                NormalizationStatus.FAILED
                if dataset.status == DatasetStatus.VALIDATING
                else None
            ),
        )

    def mark_source_changed(self, dataset_id: str) -> None:
        dataset = self.require_dataset(dataset_id)
        if dataset.status == DatasetStatus.SOURCE_CHANGED:
            return
        self.transition_status(
            dataset_id,
            DatasetStatus.SOURCE_CHANGED,
            error_code="SOURCE_CHANGED",
        )

    def delete_dataset(self, dataset_id: str) -> None:
        mapping_ids = self._connection.execute(
            "SELECT mapping_set_id FROM meta.activity_mapping_set WHERE dataset_id = ?",
            [dataset_id],
        ).fetchall()
        for mapping_id in mapping_ids:
            self._connection.execute(
                "DELETE FROM meta.activity_mapping_entry WHERE mapping_set_id = ?",
                [mapping_id[0]],
            )
        self._connection.execute(
            "DELETE FROM meta.activity_mapping_set WHERE dataset_id = ?", [dataset_id]
        )
        self._connection.execute(
            "DELETE FROM meta.dataset_artifact WHERE dataset_id = ?", [dataset_id]
        )
        self._connection.execute(
            "DELETE FROM meta.semantic_contract WHERE dataset_id = ?", [dataset_id]
        )
        self._connection.execute(
            "DELETE FROM meta.dataset_quality_report WHERE dataset_id = ?",
            [dataset_id],
        )
        self._connection.execute(
            "DELETE FROM meta.mapping_definition WHERE dataset_id = ?",
            [dataset_id],
        )
        self._connection.execute(
            "DELETE FROM meta.dataset_column_profile WHERE dataset_id = ?",
            [dataset_id],
        )
        self._connection.execute(
            "DELETE FROM meta.dataset WHERE dataset_id = ?",
            [dataset_id],
        )

    def require_dataset(self, dataset_id: str) -> DatasetRecord:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise KeyError(dataset_id)
        return dataset

    @staticmethod
    def _dataset_from_row(row: tuple[object, ...]) -> DatasetRecord:
        return DatasetRecord(
            dataset_id=str(row[0]),
            original_filename=str(row[1]),
            staged_filename=str(row[2]),
            file_type=DatasetFileType(str(row[3])),
            file_size_bytes=cast(int, row[4]),
            checksum=None if row[5] is None else str(row[5]),
            created_at=cast(datetime, row[6]),
            status=DatasetStatus(str(row[7])),
            row_count=None if row[8] is None else cast(int, row[8]),
            column_count=None if row[9] is None else cast(int, row[9]),
            schema_version=cast(int, row[10]),
            mapping_version=None if row[11] is None else cast(int, row[11]),
            normalization_version=None if row[12] is None else str(row[12]),
            normalization_status=NormalizationStatus(str(row[13])),
            normalized_filename=None if row[14] is None else str(row[14]),
            normalized_file_size_bytes=None if row[15] is None else cast(int, row[15]),
            quarantine_filename=None if row[16] is None else str(row[16]),
            quarantine_file_size_bytes=None if row[17] is None else cast(int, row[17]),
            source_type=str(row[18]),
            error_code=None if row[19] is None else str(row[19]),
            source_path=None if row[20] is None else str(row[20]),
            source_mtime_ns=None if row[21] is None else cast(int, row[21]),
            import_mode=None if row[22] is None else ImportMode(str(row[22])),
            semantic_contract_version=(
                None if row[23] is None else cast(int, row[23])
            ),
            active_activity_mapping_version=(
                None if row[24] is None else cast(int, row[24])
            ),
            current_step=None if row[25] is None else str(row[25]),
            operation_started_at=None if row[26] is None else cast(datetime, row[26]),
        )

    @staticmethod
    def _semantic_contract_from_row(row: tuple[object, ...]) -> SemanticContractRecord:
        raw_ordering = cast(list[str], json.loads(str(row[11])))
        raw_attributes = cast(dict[str, str], json.loads(str(row[12])))
        raw_pii = cast(dict[str, str], json.loads(str(row[13])))
        return SemanticContractRecord(
            contract_id=str(row[0]),
            dataset_id=str(row[1]),
            version=cast(int, row[2]),
            mapping_version=cast(int, row[3]),
            case_null_policy=str(row[4]),
            case_empty_policy=str(row[5]),
            case_id_pseudonymized=bool(row[6]),
            case_id_classification=PIIClassification(str(row[7])),
            source_timezone=str(row[8]),
            display_timezone=str(row[9]),
            normalized_timezone=str(row[10]),
            ordering_fields=tuple(raw_ordering),
            attribute_policies={
                key: RetentionPolicy(value) for key, value in raw_attributes.items()
            },
            pii_classifications={
                key: PIIClassification(value) for key, value in raw_pii.items()
            },
            business_activity_mapping_version=(
                None if row[14] is None else cast(int, row[14])
            ),
            created_at=cast(datetime, row[15]),
            status=str(row[16]),
        )

    @staticmethod
    def _artifact_from_row(row: tuple[object, ...]) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=str(row[0]),
            dataset_id=str(row[1]),
            semantic_contract_version=(
                None if row[2] is None else cast(int, row[2])
            ),
            mapping_version=None if row[3] is None else cast(int, row[3]),
            artifact_type=ArtifactType(str(row[4])),
            storage_area=str(row[5]),
            relative_path=str(row[6]),
            size_bytes=cast(int, row[7]),
            created_at=cast(datetime, row[8]),
            active=bool(row[9]),
            pinned=bool(row[10]),
        )
