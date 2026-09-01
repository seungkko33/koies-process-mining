from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.datasets import (
    ArtifactType,
    DatasetFileType,
    DatasetStatus,
    ImportMode,
    NormalizationStatus,
    PIIClassification,
    RetentionPolicy,
    UnmappedActivityPolicy,
)


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    original_filename: str
    staged_filename: str
    file_type: DatasetFileType
    file_size_bytes: int
    checksum: str | None
    created_at: datetime
    status: DatasetStatus
    row_count: int | None
    column_count: int | None
    schema_version: int
    mapping_version: int | None
    normalization_version: str | None
    normalization_status: NormalizationStatus
    normalized_filename: str | None
    normalized_file_size_bytes: int | None
    quarantine_filename: str | None
    quarantine_file_size_bytes: int | None
    source_type: str
    error_code: str | None
    source_path: str | None = None
    source_mtime_ns: int | None = None
    import_mode: ImportMode | None = None
    semantic_contract_version: int | None = None
    active_activity_mapping_version: int | None = None
    current_step: str | None = None
    operation_started_at: datetime | None = None


@dataclass(frozen=True)
class ColumnProfileRecord:
    dataset_id: str
    ordinal_position: int
    column_name: str
    inferred_type: str
    null_count: int
    approx_distinct: int
    min_value: str | None
    max_value: str | None
    sample_values: tuple[str, ...]


@dataclass(frozen=True)
class MappingRecord:
    mapping_id: str
    dataset_id: str
    version: int
    case_id_column: str
    activity_column: str
    timestamp_column: str
    event_id_column: str | None
    optional_mappings: dict[str, str]
    timestamp_format: str | None
    timezone: str | None
    display_timezone: str | None
    created_at: datetime


@dataclass(frozen=True)
class SemanticContractRecord:
    contract_id: str
    dataset_id: str
    version: int
    mapping_version: int
    case_null_policy: str
    case_empty_policy: str
    case_id_pseudonymized: bool
    case_id_classification: PIIClassification
    source_timezone: str
    display_timezone: str
    normalized_timezone: str
    ordering_fields: tuple[str, ...]
    attribute_policies: dict[str, RetentionPolicy]
    pii_classifications: dict[str, PIIClassification]
    business_activity_mapping_version: int | None
    created_at: datetime
    status: str


@dataclass(frozen=True)
class ActivityMappingEntryRecord:
    source_activity: str
    business_activity: str
    description: str | None
    enabled: bool


@dataclass(frozen=True)
class ActivityMappingSetRecord:
    mapping_set_id: str
    dataset_id: str
    version: int
    name: str
    unmapped_policy: UnmappedActivityPolicy
    created_at: datetime
    status: str
    entries: tuple[ActivityMappingEntryRecord, ...]


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    dataset_id: str
    semantic_contract_version: int | None
    mapping_version: int | None
    artifact_type: ArtifactType
    storage_area: str
    relative_path: str
    size_bytes: int
    created_at: datetime
    active: bool
    pinned: bool


@dataclass(frozen=True)
class QualityReportRecord:
    dataset_id: str
    mapping_version: int
    total_rows: int
    valid_events: int
    invalid_events: int
    unique_cases: int
    unique_activities: int
    null_case_id: int
    empty_case_id: int
    null_activity: int
    empty_activity: int
    null_timestamp: int
    invalid_timestamp: int
    duplicate_events: int
    duplicate_timestamp_rows: int
    single_event_cases: int
    ambiguous_ordering_cases: int
    events_per_case_min: int
    events_per_case_median: float
    events_per_case_p90: float
    events_per_case_max: int
    extremely_large_cases: int
    source_timezone_missing: bool
    timestamps_outside_dataset_range: int
    outcome: str
    measured_at: datetime


ALLOWED_STATUS_TRANSITIONS: dict[DatasetStatus, frozenset[DatasetStatus]] = {
    DatasetStatus.UPLOADING: frozenset({DatasetStatus.STAGED, DatasetStatus.FAILED}),
    DatasetStatus.STAGED: frozenset({DatasetStatus.PROFILING, DatasetStatus.FAILED}),
    DatasetStatus.PROFILING: frozenset({DatasetStatus.PROFILED, DatasetStatus.FAILED}),
    DatasetStatus.PROFILED: frozenset(
        {DatasetStatus.MAPPING_REQUIRED, DatasetStatus.SOURCE_CHANGED, DatasetStatus.FAILED}
    ),
    DatasetStatus.MAPPING_REQUIRED: frozenset(
        {DatasetStatus.VALIDATING, DatasetStatus.SOURCE_CHANGED, DatasetStatus.FAILED}
    ),
    DatasetStatus.VALIDATING: frozenset(
        {
            DatasetStatus.READY,
            DatasetStatus.MAPPING_REQUIRED,
            DatasetStatus.SOURCE_CHANGED,
            DatasetStatus.FAILED,
        }
    ),
    DatasetStatus.READY: frozenset(
        {
            DatasetStatus.MAPPING_REQUIRED,
            DatasetStatus.VALIDATING,
            DatasetStatus.SOURCE_CHANGED,
            DatasetStatus.FAILED,
        }
    ),
    DatasetStatus.SOURCE_CHANGED: frozenset({DatasetStatus.FAILED}),
    DatasetStatus.FAILED: frozenset(
        {DatasetStatus.PROFILING, DatasetStatus.MAPPING_REQUIRED, DatasetStatus.VALIDATING}
    ),
}


def require_status_transition(current: DatasetStatus, target: DatasetStatus) -> None:
    if current == target:
        return
    if target not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise ValueError(f"invalid dataset status transition: {current} -> {target}")
