export type DatasetStatus =
  | "UPLOADING"
  | "STAGED"
  | "PROFILING"
  | "PROFILED"
  | "MAPPING_REQUIRED"
  | "VALIDATING"
  | "READY"
  | "SOURCE_CHANGED"
  | "FAILED";

export type DatasetFileType = "CSV" | "CSV_GZ" | "PARQUET";
export type NormalizationStatus = "NOT_STARTED" | "RUNNING" | "READY" | "FAILED";
export type ImportMode = "COPY" | "REFERENCE";
export type PIIClassification = "NONE" | "POTENTIAL_PII" | "PII" | "SENSITIVE";
export type RetentionPolicy = "KEEP" | "DROP" | "PSEUDONYMIZE";
export type UnmappedActivityPolicy = "KEEP_SOURCE" | "GROUP_AS_UNMAPPED" | "EXCLUDE";

export interface DatasetSummary {
  dataset_id: string;
  original_filename: string;
  file_type: DatasetFileType;
  file_size_bytes: number;
  checksum: string | null;
  created_at: string;
  status: DatasetStatus;
  row_count: number | null;
  column_count: number | null;
  schema_version: number;
  mapping_version: number | null;
  normalization_version: string | null;
  normalization_status: NormalizationStatus;
  normalized_file_size_bytes: number | null;
  quarantine_file_size_bytes: number | null;
  source_type: string;
  error_code: string | null;
  semantic_contract_version: number | null;
  active_activity_mapping_version: number | null;
  import_mode: ImportMode | null;
  current_step: string | null;
  operation_started_at: string | null;
  data_ready: boolean;
  semantic_ready: boolean;
  analysis_ready: boolean;
}

export interface DatasetColumnProfile {
  ordinal_position: number;
  column_name: string;
  inferred_type: string;
  nullable_observed: boolean;
  null_count: number;
  approx_distinct: number;
  min_value: string | null;
  max_value: string | null;
  sample_values: string[];
}

export interface DatasetProfileResponse {
  dataset: DatasetSummary;
  columns: DatasetColumnProfile[];
}

export interface DatasetPreviewResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  returned_rows: number;
  limit: number;
}

export interface MappingCreateRequest {
  case_id_column: string;
  activity_column: string;
  timestamp_column: string;
  event_id_column: string | null;
  optional_mappings: Record<string, string>;
  timestamp_format: string | null;
  timezone: string | null;
  display_timezone: string | null;
  case_null_policy: "REJECT";
  case_empty_policy: "REJECT";
  case_id_pseudonymized: boolean;
  case_id_classification: PIIClassification;
  attribute_policies: Record<string, RetentionPolicy>;
  pii_classifications: Record<string, PIIClassification>;
  ordering_fields: string[];
  business_activity_mapping_version: number | null;
}

export interface TimestampPreview {
  source_value: string;
  parsed_value: string | null;
  utc_value: string | null;
  display_value: string | null;
  timezone_aware: boolean;
}

export interface MappingDefinitionResponse
  extends Pick<
    MappingCreateRequest,
    | "case_id_column"
    | "activity_column"
    | "timestamp_column"
    | "event_id_column"
    | "optional_mappings"
    | "timestamp_format"
    | "timezone"
    | "display_timezone"
  > {
  mapping_id: string;
  dataset_id: string;
  version: number;
  created_at: string;
  timestamp_preview: TimestampPreview[];
  semantic_contract_id: string | null;
  semantic_contract_version: number | null;
}

export interface DataQualityReport {
  dataset_id: string;
  mapping_version: number;
  total_rows: number;
  valid_events: number;
  invalid_events: number;
  unique_cases: number;
  unique_activities: number;
  null_case_id: number;
  empty_case_id: number;
  null_activity: number;
  empty_activity: number;
  null_timestamp: number;
  invalid_timestamp: number;
  duplicate_events: number;
  duplicate_timestamp_rows: number;
  single_event_cases: number;
  ambiguous_ordering_cases: number;
  events_per_case_min: number;
  events_per_case_median: number;
  events_per_case_p90: number;
  events_per_case_max: number;
  extremely_large_cases: number;
  source_timezone_missing: boolean;
  timestamps_outside_dataset_range: number;
  technical_quality: string;
  semantic_quality: string;
  outcome: string;
  measured_at: string;
}

export interface NormalizationResponse {
  dataset: DatasetSummary;
  quality: DataQualityReport;
}

export interface ActivityMappingEntry {
  source_activity: string;
  business_activity: string;
  description: string | null;
  enabled: boolean;
}

export interface ActivityMappingSet {
  mapping_set_id: string;
  dataset_id: string;
  version: number;
  name: string;
  unmapped_policy: UnmappedActivityPolicy;
  created_at: string;
  status: string;
  entries: ActivityMappingEntry[];
}

export interface ActivityCoverageRow {
  source_activity: string;
  business_activity: string | null;
  event_count: number;
  case_count: number;
  mapped: boolean;
}

export interface ActivityMappingCoverage {
  dataset_id: string;
  activity_mapping_version: number;
  unique_source_activities: number;
  mapped_activities: number;
  unmapped_activities: number;
  business_activities: number;
  mapped_event_count: number;
  unmapped_event_count: number;
  activity_mapping_coverage: number;
  event_mapping_coverage: number;
  rows: ActivityCoverageRow[];
}

export type ArtifactType = "SOURCE" | "NORMALIZED" | "QUARANTINE" | "TEMPORARY";

export interface DatasetArtifact {
  artifact_id: string;
  dataset_id: string;
  semantic_contract_version: number | null;
  mapping_version: number | null;
  artifact_type: ArtifactType;
  path: string;
  size_bytes: number;
  created_at: string;
  active: boolean;
  pinned: boolean;
}

export interface ArtifactDiskUsage {
  raw_source: number;
  normalized: number;
  quarantine: number;
  previous_versions: number;
  temporary: number;
  total: number;
}

export interface ArtifactListResponse {
  artifacts: DatasetArtifact[];
  disk_usage: ArtifactDiskUsage;
}
