import { describe, expect, it } from "vitest";

import {
  parseApiErrorPayload,
  parseDatasetProfile,
  parseDatasetSummary,
  parseQuality,
} from "../../api/datasets";
import type {
  DataQualityReport,
  DatasetColumnProfile,
  MappingCreateRequest,
} from "../../types/datasets";
import {
  datasetStatusLabel,
  formatBytes,
  qualityMetricViews,
  validateMappingSelection,
} from "./datasetModel";

const dataset = {
  dataset_id: "47f3919d-8ead-43ac-8cdf-909880548d21",
  original_filename: "events.csv",
  file_type: "CSV",
  file_size_bytes: 1024,
  checksum: "abc",
  created_at: "2026-09-01T10:00:00",
  status: "MAPPING_REQUIRED",
  row_count: 10,
  column_count: 3,
  schema_version: 1,
  mapping_version: null,
  normalization_version: null,
  normalization_status: "NOT_STARTED",
  normalized_file_size_bytes: null,
  quarantine_file_size_bytes: null,
  source_type: "UPLOADED_FILE",
  error_code: null,
};

const columns: DatasetColumnProfile[] = [
  { ordinal_position: 1, column_name: "case_id", inferred_type: "VARCHAR", nullable_observed: false, null_count: 0, approx_distinct: 3, min_value: "C1", max_value: "C3", sample_values: ["C1"] },
  { ordinal_position: 2, column_name: "activity", inferred_type: "VARCHAR", nullable_observed: false, null_count: 0, approx_distinct: 4, min_value: "A", max_value: "D", sample_values: ["A"] },
  { ordinal_position: 3, column_name: "event_ts", inferred_type: "TIMESTAMP", nullable_observed: false, null_count: 0, approx_distinct: 10, min_value: null, max_value: null, sample_values: ["2026-01-01"] },
];

const quality: DataQualityReport = {
  dataset_id: dataset.dataset_id,
  mapping_version: 1,
  total_rows: 10,
  valid_events: 8,
  invalid_events: 2,
  unique_cases: 3,
  unique_activities: 4,
  null_case_id: 1,
  empty_case_id: 0,
  null_activity: 0,
  empty_activity: 0,
  null_timestamp: 0,
  invalid_timestamp: 1,
  duplicate_events: 0,
  duplicate_timestamp_rows: 0,
  single_event_cases: 1,
  ambiguous_ordering_cases: 0,
  events_per_case_min: 1,
  events_per_case_median: 3,
  events_per_case_p90: 4,
  events_per_case_max: 4,
  extremely_large_cases: 0,
  source_timezone_missing: false,
  timestamps_outside_dataset_range: 0,
  technical_quality: "PASSED_WITH_QUARANTINE",
  semantic_quality: "PASSED",
  outcome: "PASSED_WITH_QUARANTINE",
  measured_at: "2026-09-01T10:01:00",
};

describe("Dataset API contracts", () => {
  it("parses Dataset status used by upload UI", () => {
    expect(parseDatasetSummary(dataset).status).toBe("MAPPING_REQUIRED");
    expect(datasetStatusLabel("PROFILING")).toBe("Profiling");
  });

  it("rejects unknown Dataset states", () => {
    expect(() => parseDatasetSummary({ ...dataset, status: "MAGIC" })).toThrow(
      "Dataset 상태 또는 파일 형식이 올바르지 않습니다.",
    );
  });

  it("parses schema profile rows", () => {
    const parsed = parseDatasetProfile({ dataset, columns });
    expect(parsed.columns.map((column) => column.column_name)).toEqual([
      "case_id",
      "activity",
      "event_ts",
    ]);
  });

  it("parses Data Quality DTO and preserves failure counts", () => {
    expect(parseQuality(quality).invalid_timestamp).toBe(1);
    expect(qualityMetricViews(quality).find((metric) => metric.key === "invalid_events")).toMatchObject({
      value: 2,
      severity: "warning",
    });
  });

  it("extracts structured API errors", () => {
    const error = parseApiErrorPayload({ detail: { code: "INVALID_CSV", message: "Bad file" } });
    expect(error.code).toBe("INVALID_CSV");
    expect(error.message).toBe("Bad file");
  });
});

describe("Event Log mapping validation", () => {
  const mapping: MappingCreateRequest = {
    case_id_column: "case_id",
    activity_column: "activity",
    timestamp_column: "event_ts",
    event_id_column: null,
    optional_mappings: {},
    timestamp_format: null,
    timezone: "Asia/Seoul",
    display_timezone: "Asia/Seoul",
    case_null_policy: "REJECT",
    case_empty_policy: "REJECT",
    case_id_pseudonymized: false,
    case_id_classification: "NONE",
    attribute_policies: {},
    pii_classifications: {},
    ordering_fields: ["event_ts", "source_sequence", "event_id", "source_row_number"],
    business_activity_mapping_version: null,
  };

  it("accepts three explicit, distinct source columns", () => {
    expect(validateMappingSelection(mapping, columns)).toEqual([]);
  });

  it("rejects missing, duplicate, and unknown selections", () => {
    expect(validateMappingSelection({ ...mapping, activity_column: "case_id" }, columns)).toContain(
      "필수 Event Log 컬럼은 서로 달라야 합니다.",
    );
    expect(validateMappingSelection({ ...mapping, case_id_column: "unknown" }, columns)).toContain(
      "현재 schema에 없는 컬럼이 선택됐습니다.",
    );
  });

  it("formats large upload sizes without row materialization", () => {
    expect(formatBytes(2 * 1024 * 1024)).toBe("2 MB");
  });
});
