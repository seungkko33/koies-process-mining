import type {
  ActivityMappingCoverage,
  ActivityMappingEntry,
  ActivityMappingSet,
  ArtifactListResponse,
  DataQualityReport,
  DatasetColumnProfile,
  DatasetFileType,
  DatasetPreviewResponse,
  DatasetProfileResponse,
  DatasetStatus,
  DatasetSummary,
  DatasetArtifact,
  MappingCreateRequest,
  MappingDefinitionResponse,
  NormalizationResponse,
  NormalizationStatus,
  TimestampPreview,
} from "../types/datasets";

type JsonRecord = Record<string, unknown>;

const datasetStatuses = new Set<DatasetStatus>([
  "UPLOADING",
  "STAGED",
  "PROFILING",
  "PROFILED",
  "MAPPING_REQUIRED",
  "VALIDATING",
  "READY",
  "SOURCE_CHANGED",
  "FAILED",
]);
const fileTypes = new Set<DatasetFileType>(["CSV", "CSV_GZ", "PARQUET"]);
const normalizationStatuses = new Set<NormalizationStatus>([
  "NOT_STARTED",
  "RUNNING",
  "READY",
  "FAILED",
]);

export class DatasetApiError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(record: JsonRecord, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`Dataset 응답의 ${key} 값이 올바르지 않습니다.`);
  return value;
}

function readNumber(record: JsonRecord, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Dataset 응답의 ${key} 값이 올바르지 않습니다.`);
  }
  return value;
}

function readNullableString(record: JsonRecord, key: string): string | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value !== "string") throw new Error(`Dataset 응답의 ${key} 값이 올바르지 않습니다.`);
  return value;
}

function readNullableNumber(record: JsonRecord, key: string): number | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Dataset 응답의 ${key} 값이 올바르지 않습니다.`);
  }
  return value;
}

function readBoolean(record: JsonRecord, key: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") throw new Error(`Dataset response field ${key} is invalid.`);
  return value;
}

function readBooleanOr(record: JsonRecord, key: string, fallback: boolean): boolean {
  return record[key] === undefined ? fallback : readBoolean(record, key);
}

function readNumberOr(record: JsonRecord, key: string, fallback = 0): number {
  return record[key] === undefined ? fallback : readNumber(record, key);
}

function readNullableNumberOrNull(record: JsonRecord, key: string): number | null {
  return record[key] === undefined ? null : readNullableNumber(record, key);
}

function readNullableStringOrNull(record: JsonRecord, key: string): string | null {
  return record[key] === undefined ? null : readNullableString(record, key);
}

function readStringArray(record: JsonRecord, key: string): string[] {
  const value = record[key];
  if (!Array.isArray(value) || !value.every((entry) => typeof entry === "string")) {
    throw new Error(`Dataset 응답의 ${key} 값이 올바르지 않습니다.`);
  }
  return value;
}

export function parseDatasetSummary(value: unknown): DatasetSummary {
  if (!isRecord(value)) throw new Error("Dataset 응답 형식이 올바르지 않습니다.");
  const status = readString(value, "status") as DatasetStatus;
  const fileType = readString(value, "file_type") as DatasetFileType;
  const normalizationStatus = readString(value, "normalization_status") as NormalizationStatus;
  if (!datasetStatuses.has(status) || !fileTypes.has(fileType) || !normalizationStatuses.has(normalizationStatus)) {
    throw new Error("Dataset 상태 또는 파일 형식이 올바르지 않습니다.");
  }
  return {
    dataset_id: readString(value, "dataset_id"),
    original_filename: readString(value, "original_filename"),
    file_type: fileType,
    file_size_bytes: readNumber(value, "file_size_bytes"),
    checksum: readNullableString(value, "checksum"),
    created_at: readString(value, "created_at"),
    status,
    row_count: readNullableNumber(value, "row_count"),
    column_count: readNullableNumber(value, "column_count"),
    schema_version: readNumber(value, "schema_version"),
    mapping_version: readNullableNumber(value, "mapping_version"),
    normalization_version: readNullableString(value, "normalization_version"),
    normalization_status: normalizationStatus,
    normalized_file_size_bytes: readNullableNumber(value, "normalized_file_size_bytes"),
    quarantine_file_size_bytes: readNullableNumber(value, "quarantine_file_size_bytes"),
    source_type: readString(value, "source_type"),
    error_code: readNullableString(value, "error_code"),
    semantic_contract_version: readNullableNumberOrNull(value, "semantic_contract_version"),
    active_activity_mapping_version: readNullableNumberOrNull(value, "active_activity_mapping_version"),
    import_mode: readNullableStringOrNull(value, "import_mode") as "COPY" | "REFERENCE" | null,
    current_step: readNullableStringOrNull(value, "current_step"),
    operation_started_at: readNullableStringOrNull(value, "operation_started_at"),
    data_ready: readBooleanOr(value, "data_ready", status === "READY"),
    semantic_ready: readBooleanOr(value, "semantic_ready", false),
    analysis_ready: readBooleanOr(value, "analysis_ready", status === "READY"),
  };
}

function parseColumn(value: unknown): DatasetColumnProfile {
  if (!isRecord(value) || typeof value.nullable_observed !== "boolean") {
    throw new Error("Dataset column profile 형식이 올바르지 않습니다.");
  }
  return {
    ordinal_position: readNumber(value, "ordinal_position"),
    column_name: readString(value, "column_name"),
    inferred_type: readString(value, "inferred_type"),
    nullable_observed: value.nullable_observed,
    null_count: readNumber(value, "null_count"),
    approx_distinct: readNumber(value, "approx_distinct"),
    min_value: readNullableString(value, "min_value"),
    max_value: readNullableString(value, "max_value"),
    sample_values: readStringArray(value, "sample_values"),
  };
}

export function parseDatasetProfile(value: unknown): DatasetProfileResponse {
  if (!isRecord(value) || !Array.isArray(value.columns)) {
    throw new Error("Dataset profile 응답 형식이 올바르지 않습니다.");
  }
  return { dataset: parseDatasetSummary(value.dataset), columns: value.columns.map(parseColumn) };
}

export function parseDatasetPreview(value: unknown): DatasetPreviewResponse {
  if (!isRecord(value) || !Array.isArray(value.rows) || !value.rows.every(isRecord)) {
    throw new Error("Dataset preview 응답 형식이 올바르지 않습니다.");
  }
  return {
    columns: readStringArray(value, "columns"),
    rows: value.rows,
    returned_rows: readNumber(value, "returned_rows"),
    limit: readNumber(value, "limit"),
  };
}

function parseStringMap(value: unknown): Record<string, string> {
  if (!isRecord(value) || !Object.values(value).every((entry) => typeof entry === "string")) {
    throw new Error("Mapping optional field 형식이 올바르지 않습니다.");
  }
  return value as Record<string, string>;
}

function parseTimestampPreview(value: unknown): TimestampPreview {
  if (!isRecord(value)) throw new Error("Timestamp preview 형식이 올바르지 않습니다.");
  return {
    source_value: readString(value, "source_value"),
    parsed_value: readNullableString(value, "parsed_value"),
    utc_value: readNullableStringOrNull(value, "utc_value"),
    display_value: readNullableStringOrNull(value, "display_value"),
    timezone_aware: readBooleanOr(value, "timezone_aware", false),
  };
}

export function parseMapping(value: unknown): MappingDefinitionResponse {
  if (!isRecord(value) || !Array.isArray(value.timestamp_preview)) {
    throw new Error("Mapping 응답 형식이 올바르지 않습니다.");
  }
  return {
    mapping_id: readString(value, "mapping_id"),
    dataset_id: readString(value, "dataset_id"),
    version: readNumber(value, "version"),
    case_id_column: readString(value, "case_id_column"),
    activity_column: readString(value, "activity_column"),
    timestamp_column: readString(value, "timestamp_column"),
    event_id_column: readNullableString(value, "event_id_column"),
    optional_mappings: parseStringMap(value.optional_mappings),
    timestamp_format: readNullableString(value, "timestamp_format"),
    timezone: readNullableString(value, "timezone"),
    display_timezone: readNullableStringOrNull(value, "display_timezone"),
    created_at: readString(value, "created_at"),
    timestamp_preview: value.timestamp_preview.map(parseTimestampPreview),
    semantic_contract_id: readNullableStringOrNull(value, "semantic_contract_id"),
    semantic_contract_version: readNullableNumberOrNull(value, "semantic_contract_version"),
  };
}

export function parseQuality(value: unknown): DataQualityReport {
  if (!isRecord(value)) throw new Error("Data Quality 응답 형식이 올바르지 않습니다.");
  return {
    dataset_id: readString(value, "dataset_id"),
    mapping_version: readNumber(value, "mapping_version"),
    total_rows: readNumber(value, "total_rows"),
    valid_events: readNumber(value, "valid_events"),
    invalid_events: readNumber(value, "invalid_events"),
    unique_cases: readNumber(value, "unique_cases"),
    unique_activities: readNumber(value, "unique_activities"),
    null_case_id: readNumber(value, "null_case_id"),
    empty_case_id: readNumber(value, "empty_case_id"),
    null_activity: readNumber(value, "null_activity"),
    empty_activity: readNumber(value, "empty_activity"),
    null_timestamp: readNumber(value, "null_timestamp"),
    invalid_timestamp: readNumber(value, "invalid_timestamp"),
    duplicate_events: readNumber(value, "duplicate_events"),
    duplicate_timestamp_rows: readNumber(value, "duplicate_timestamp_rows"),
    single_event_cases: readNumber(value, "single_event_cases"),
    ambiguous_ordering_cases: readNumberOr(value, "ambiguous_ordering_cases"),
    events_per_case_min: readNumberOr(value, "events_per_case_min"),
    events_per_case_median: readNumberOr(value, "events_per_case_median"),
    events_per_case_p90: readNumberOr(value, "events_per_case_p90"),
    events_per_case_max: readNumberOr(value, "events_per_case_max"),
    extremely_large_cases: readNumberOr(value, "extremely_large_cases"),
    source_timezone_missing: readBooleanOr(value, "source_timezone_missing", false),
    timestamps_outside_dataset_range: readNumberOr(value, "timestamps_outside_dataset_range"),
    technical_quality: value.technical_quality === undefined ? readString(value, "outcome") : readString(value, "technical_quality"),
    semantic_quality: value.semantic_quality === undefined ? "UNKNOWN" : readString(value, "semantic_quality"),
    outcome: readString(value, "outcome"),
    measured_at: readString(value, "measured_at"),
  };
}

function parseNormalization(value: unknown): NormalizationResponse {
  if (!isRecord(value)) throw new Error("Normalization 응답 형식이 올바르지 않습니다.");
  return { dataset: parseDatasetSummary(value.dataset), quality: parseQuality(value.quality) };
}

export function parseApiErrorPayload(value: unknown): DatasetApiError {
  if (isRecord(value) && isRecord(value.detail)) {
    const code = typeof value.detail.code === "string" ? value.detail.code : "API_ERROR";
    const message = typeof value.detail.message === "string" ? value.detail.message : "Dataset 요청에 실패했습니다.";
    return new DatasetApiError(code, message);
  }
  if (isRecord(value) && typeof value.detail === "string") {
    return new DatasetApiError("API_ERROR", value.detail);
  }
  return new DatasetApiError("API_ERROR", "Dataset 요청에 실패했습니다.");
}

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  const payload: unknown = await response.json();
  if (!response.ok) throw parseApiErrorPayload(payload);
  return payload;
}

export async function fetchDatasets(signal?: AbortSignal): Promise<DatasetSummary[]> {
  const payload = await requestJson("/api/datasets", { signal });
  if (!isRecord(payload) || !Array.isArray(payload.datasets)) {
    throw new Error("Dataset 목록 응답 형식이 올바르지 않습니다.");
  }
  return payload.datasets.map(parseDatasetSummary);
}

export async function fetchDatasetProfile(datasetId: string, signal?: AbortSignal) {
  return parseDatasetProfile(await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/profile`, { signal }));
}

export async function fetchDatasetPreview(datasetId: string, signal?: AbortSignal) {
  return parseDatasetPreview(await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/preview?limit=20`, { signal }));
}

export async function createDatasetMapping(datasetId: string, mapping: MappingCreateRequest) {
  return parseMapping(await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/mappings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mapping),
  }));
}

export async function normalizeDataset(datasetId: string) {
  return parseNormalization(await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/normalize`, { method: "POST" }));
}

export async function fetchDatasetQuality(datasetId: string, signal?: AbortSignal) {
  return parseQuality(await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/quality`, { signal }));
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}`, { method: "DELETE" });
}

function parseActivityEntry(value: unknown): ActivityMappingEntry {
  if (!isRecord(value) || typeof value.enabled !== "boolean") {
    throw new Error("Activity mapping entry response is invalid.");
  }
  return {
    source_activity: readString(value, "source_activity"),
    business_activity: readString(value, "business_activity"),
    description: readNullableString(value, "description"),
    enabled: value.enabled,
  };
}

function parseActivityMappingSet(value: unknown): ActivityMappingSet {
  if (!isRecord(value) || !Array.isArray(value.entries)) {
    throw new Error("Activity mapping response is invalid.");
  }
  return {
    mapping_set_id: readString(value, "mapping_set_id"),
    dataset_id: readString(value, "dataset_id"),
    version: readNumber(value, "version"),
    name: readString(value, "name"),
    unmapped_policy: readString(value, "unmapped_policy") as ActivityMappingSet["unmapped_policy"],
    created_at: readString(value, "created_at"),
    status: readString(value, "status"),
    entries: value.entries.map(parseActivityEntry),
  };
}

export async function fetchActivityMappingSets(datasetId: string, signal?: AbortSignal) {
  const payload = await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/activity-mappings`,
    { signal },
  );
  if (!isRecord(payload) || !Array.isArray(payload.mapping_sets)) {
    throw new Error("Activity mapping list response is invalid.");
  }
  return payload.mapping_sets.map(parseActivityMappingSet);
}

export async function createActivityMappingSet(
  datasetId: string,
  payload: {
    name: string;
    unmapped_policy: ActivityMappingSet["unmapped_policy"];
    entries: ActivityMappingEntry[];
  },
) {
  return parseActivityMappingSet(await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/activity-mappings`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  ));
}

function parseCoverageRow(value: unknown) {
  if (!isRecord(value) || typeof value.mapped !== "boolean") {
    throw new Error("Activity coverage row is invalid.");
  }
  return {
    source_activity: readString(value, "source_activity"),
    business_activity: readNullableString(value, "business_activity"),
    event_count: readNumber(value, "event_count"),
    case_count: readNumber(value, "case_count"),
    mapped: value.mapped,
  };
}

export async function fetchActivityMappingCoverage(
  datasetId: string,
  version: number,
  signal?: AbortSignal,
): Promise<ActivityMappingCoverage> {
  const payload = await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/activity-mappings/${version}/coverage`,
    { signal },
  );
  if (!isRecord(payload) || !Array.isArray(payload.rows)) {
    throw new Error("Activity coverage response is invalid.");
  }
  return {
    dataset_id: readString(payload, "dataset_id"),
    activity_mapping_version: readNumber(payload, "activity_mapping_version"),
    unique_source_activities: readNumber(payload, "unique_source_activities"),
    mapped_activities: readNumber(payload, "mapped_activities"),
    unmapped_activities: readNumber(payload, "unmapped_activities"),
    business_activities: readNumber(payload, "business_activities"),
    mapped_event_count: readNumber(payload, "mapped_event_count"),
    unmapped_event_count: readNumber(payload, "unmapped_event_count"),
    activity_mapping_coverage: readNumber(payload, "activity_mapping_coverage"),
    event_mapping_coverage: readNumber(payload, "event_mapping_coverage"),
    rows: payload.rows.map(parseCoverageRow),
  };
}

export function parseArtifact(value: unknown): DatasetArtifact {
  if (!isRecord(value)) throw new Error("Artifact response is invalid.");
  return {
    artifact_id: readString(value, "artifact_id"),
    dataset_id: readString(value, "dataset_id"),
    semantic_contract_version: readNullableNumber(value, "semantic_contract_version"),
    mapping_version: readNullableNumber(value, "mapping_version"),
    artifact_type: readString(value, "artifact_type") as DatasetArtifact["artifact_type"],
    path: readString(value, "path"),
    size_bytes: readNumber(value, "size_bytes"),
    created_at: readString(value, "created_at"),
    active: readBoolean(value, "active"),
    pinned: readBoolean(value, "pinned"),
  };
}

export async function fetchArtifacts(datasetId: string, signal?: AbortSignal): Promise<ArtifactListResponse> {
  const payload = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/artifacts`, { signal });
  if (!isRecord(payload) || !Array.isArray(payload.artifacts) || !isRecord(payload.disk_usage)) {
    throw new Error("Artifact list response is invalid.");
  }
  return {
    artifacts: payload.artifacts.map(parseArtifact),
    disk_usage: {
      raw_source: readNumber(payload.disk_usage, "raw_source"),
      normalized: readNumber(payload.disk_usage, "normalized"),
      quarantine: readNumber(payload.disk_usage, "quarantine"),
      previous_versions: readNumber(payload.disk_usage, "previous_versions"),
      temporary: readNumber(payload.disk_usage, "temporary"),
      total: readNumber(payload.disk_usage, "total"),
    },
  };
}

export async function setArtifactPinned(datasetId: string, artifactId: string, pinned: boolean) {
  return parseArtifact(await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/artifacts/${encodeURIComponent(artifactId)}/pin`,
    { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pinned }) },
  ));
}

export async function deleteArtifact(datasetId: string, artifactId: string): Promise<void> {
  await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/artifacts/${encodeURIComponent(artifactId)}`,
    { method: "DELETE" },
  );
}

export async function importLocalDataset(path: string, mode: "COPY" | "REFERENCE") {
  return parseDatasetSummary(await requestJson("/api/datasets/import-local", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, mode }),
  }));
}

export function uploadDataset(
  file: File,
  onProgress: (progress: number) => void,
): Promise<DatasetSummary> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/datasets/upload");
    request.responseType = "json";
    request.setRequestHeader("Accept", "application/json");
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        try {
          resolve(parseDatasetSummary(request.response));
        } catch (error) {
          reject(error);
        }
        return;
      }
      reject(parseApiErrorPayload(request.response));
    });
    request.addEventListener("error", () => reject(new DatasetApiError("NETWORK_ERROR", "로컬 서버에 연결할 수 없습니다.")));
    const form = new FormData();
    form.append("file", file, file.name);
    request.send(form);
  });
}
