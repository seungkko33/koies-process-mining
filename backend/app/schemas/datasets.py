from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class DatasetStatus(StrEnum):
    UPLOADING = "UPLOADING"
    STAGED = "STAGED"
    PROFILING = "PROFILING"
    PROFILED = "PROFILED"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    FAILED = "FAILED"


class DatasetFileType(StrEnum):
    CSV = "CSV"
    CSV_GZ = "CSV_GZ"
    PARQUET = "PARQUET"


class NormalizationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class ImportMode(StrEnum):
    COPY = "COPY"
    REFERENCE = "REFERENCE"


class PIIClassification(StrEnum):
    NONE = "NONE"
    POTENTIAL_PII = "POTENTIAL_PII"
    PII = "PII"
    SENSITIVE = "SENSITIVE"


class RetentionPolicy(StrEnum):
    KEEP = "KEEP"
    DROP = "DROP"
    PSEUDONYMIZE = "PSEUDONYMIZE"


class UnmappedActivityPolicy(StrEnum):
    KEEP_SOURCE = "KEEP_SOURCE"
    GROUP_AS_UNMAPPED = "GROUP_AS_UNMAPPED"
    EXCLUDE = "EXCLUDE"


class ActivityLevel(StrEnum):
    SOURCE = "source"
    BUSINESS = "business"


class DatasetSummary(BaseModel):
    dataset_id: str
    original_filename: str
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
    normalized_file_size_bytes: int | None
    quarantine_file_size_bytes: int | None
    source_type: str
    error_code: str | None
    semantic_contract_version: int | None = None
    active_activity_mapping_version: int | None = None
    import_mode: ImportMode | None = None
    current_step: str | None = None
    operation_started_at: datetime | None = None
    data_ready: bool = False
    semantic_ready: bool = False
    analysis_ready: bool = False


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary] = Field(default_factory=list)


class DatasetColumnProfile(BaseModel):
    ordinal_position: int
    column_name: str
    inferred_type: str
    nullable_observed: bool
    null_count: int
    approx_distinct: int
    min_value: str | None
    max_value: str | None
    sample_values: list[str] = Field(default_factory=list)


class DatasetProfileResponse(BaseModel):
    dataset: DatasetSummary
    columns: list[DatasetColumnProfile] = Field(default_factory=list)


class DatasetPreviewResponse(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, JsonValue]] = Field(default_factory=list)
    returned_rows: int
    limit: int


ALLOWED_OPTIONAL_MAPPINGS = frozenset(
    {
        "resource",
        "user",
        "department",
        "system",
        "method",
        "status",
        "duration",
        "source_sequence",
    }
)

ALLOWED_ATTRIBUTE_POLICY_TARGETS = ALLOWED_OPTIONAL_MAPPINGS | {"event_id"}


class MappingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id_column: str = Field(min_length=1)
    activity_column: str = Field(min_length=1)
    timestamp_column: str = Field(min_length=1)
    event_id_column: str | None = None
    optional_mappings: dict[str, str] = Field(default_factory=dict)
    timestamp_format: str | None = None
    timezone: str | None = None
    display_timezone: str | None = None
    case_null_policy: str = Field(default="REJECT", pattern=r"^REJECT$")
    case_empty_policy: str = Field(default="REJECT", pattern=r"^REJECT$")
    case_id_pseudonymized: bool = False
    case_id_classification: PIIClassification = PIIClassification.NONE
    attribute_policies: dict[str, RetentionPolicy] = Field(default_factory=dict)
    pii_classifications: dict[str, PIIClassification] = Field(default_factory=dict)
    ordering_fields: list[str] = Field(
        default_factory=lambda: [
            "event_ts",
            "source_sequence",
            "event_id",
            "source_row_number",
        ]
    )
    business_activity_mapping_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_mapping(self) -> MappingCreateRequest:
        required = {
            self.case_id_column,
            self.activity_column,
            self.timestamp_column,
        }
        if len(required) != 3:
            raise ValueError("case_id, activity, and timestamp columns must be different")
        unsupported = set(self.optional_mappings) - ALLOWED_OPTIONAL_MAPPINGS
        if unsupported:
            raise ValueError(f"unsupported optional mappings: {', '.join(sorted(unsupported))}")
        if any(not value.strip() for value in self.optional_mappings.values()):
            raise ValueError("optional mapping column names must not be empty")
        unsupported_policies = (
            set(self.attribute_policies) - ALLOWED_ATTRIBUTE_POLICY_TARGETS
        )
        unsupported_pii = (
            set(self.pii_classifications) - ALLOWED_ATTRIBUTE_POLICY_TARGETS
        )
        if unsupported_policies or unsupported_pii:
            raise ValueError("attribute policies must target event_id or optional mappings")
        numeric_pseudonyms = {
            name
            for name in ("duration", "source_sequence")
            if self.attribute_policies.get(name) == RetentionPolicy.PSEUDONYMIZE
        }
        if numeric_pseudonyms:
            raise ValueError(
                "numeric attributes cannot use PSEUDONYMIZE: "
                + ", ".join(sorted(numeric_pseudonyms))
            )
        expected_ordering = {
            "event_ts",
            "source_sequence",
            "event_id",
            "source_row_number",
        }
        if set(self.ordering_fields) != expected_ordering or len(self.ordering_fields) != 4:
            raise ValueError("ordering_fields must contain the four deterministic ordering keys")
        if self.ordering_fields[0] != "event_ts" or self.ordering_fields[-1] != "source_row_number":
            raise ValueError("ordering must start with event_ts and end with source_row_number")
        return self


class TimestampPreview(BaseModel):
    source_value: str
    parsed_value: str | None
    utc_value: str | None = None
    display_value: str | None = None
    timezone_aware: bool = False


class MappingDefinitionResponse(BaseModel):
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
    display_timezone: str | None = None
    created_at: datetime
    timestamp_preview: list[TimestampPreview] = Field(default_factory=list)
    semantic_contract_id: str | None = None
    semantic_contract_version: int | None = None


class SemanticContractResponse(BaseModel):
    contract_id: str
    dataset_id: str
    version: int
    mapping_version: int
    case_id_column: str
    activity_column: str
    timestamp_column: str
    case_null_policy: str
    case_empty_policy: str
    case_id_pseudonymized: bool
    case_id_classification: PIIClassification
    source_timezone: str
    display_timezone: str
    normalized_timezone: str
    ordering_fields: list[str]
    attribute_policies: dict[str, RetentionPolicy]
    pii_classifications: dict[str, PIIClassification]
    business_activity_mapping_version: int | None
    created_at: datetime
    status: str
    timestamp_preview: list[TimestampPreview] = Field(default_factory=list)


class SemanticContractListResponse(BaseModel):
    contracts: list[SemanticContractResponse] = Field(default_factory=list)


class DataQualityReport(BaseModel):
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
    ambiguous_ordering_cases: int = 0
    events_per_case_min: int = 0
    events_per_case_median: float = 0
    events_per_case_p90: float = 0
    events_per_case_max: int = 0
    extremely_large_cases: int = 0
    source_timezone_missing: bool = False
    timestamps_outside_dataset_range: int = 0
    technical_quality: str = "UNKNOWN"
    semantic_quality: str = "UNKNOWN"
    outcome: str
    measured_at: datetime


class NormalizationResponse(BaseModel):
    dataset: DatasetSummary
    quality: DataQualityReport


class DeleteDatasetResponse(BaseModel):
    dataset_id: str
    deleted: bool


class LocalImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    mode: ImportMode | None = None


class ActivityMappingEntryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_activity: str = Field(min_length=1)
    business_activity: str = Field(min_length=1)
    description: str | None = None
    enabled: bool = True


class ActivityMappingSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    unmapped_policy: UnmappedActivityPolicy = UnmappedActivityPolicy.KEEP_SOURCE
    entries: list[ActivityMappingEntryRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_sources(self) -> ActivityMappingSetCreateRequest:
        sources = [entry.source_activity.strip() for entry in self.entries]
        if len(sources) != len(set(sources)):
            raise ValueError("source_activity entries must be unique")
        return self


class ActivityMappingEntryResponse(BaseModel):
    source_activity: str
    business_activity: str
    description: str | None
    enabled: bool


class ActivityMappingSetResponse(BaseModel):
    mapping_set_id: str
    dataset_id: str
    version: int
    name: str
    unmapped_policy: UnmappedActivityPolicy
    created_at: datetime
    status: str
    entries: list[ActivityMappingEntryResponse] = Field(default_factory=list)


class ActivityMappingSetListResponse(BaseModel):
    mapping_sets: list[ActivityMappingSetResponse] = Field(default_factory=list)


class ActivityCoverageRow(BaseModel):
    source_activity: str
    business_activity: str | None
    event_count: int
    case_count: int
    mapped: bool


class ActivityMappingCoverage(BaseModel):
    dataset_id: str
    activity_mapping_version: int
    unique_source_activities: int
    mapped_activities: int
    unmapped_activities: int
    business_activities: int
    mapped_event_count: int
    unmapped_event_count: int
    activity_mapping_coverage: float
    event_mapping_coverage: float
    rows: list[ActivityCoverageRow] = Field(default_factory=list)


class ArtifactType(StrEnum):
    SOURCE = "SOURCE"
    NORMALIZED = "NORMALIZED"
    QUARANTINE = "QUARANTINE"
    TEMPORARY = "TEMPORARY"


class ArtifactResponse(BaseModel):
    artifact_id: str
    dataset_id: str
    semantic_contract_version: int | None
    mapping_version: int | None
    artifact_type: ArtifactType
    path: str
    size_bytes: int
    created_at: datetime
    active: bool
    pinned: bool


class ArtifactDiskUsage(BaseModel):
    raw_source: int = 0
    normalized: int = 0
    quarantine: int = 0
    previous_versions: int = 0
    temporary: int = 0
    total: int = 0


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    disk_usage: ArtifactDiskUsage


class ArtifactPinRequest(BaseModel):
    pinned: bool


class ArtifactDeleteResponse(BaseModel):
    artifact_id: str
    deleted: bool
