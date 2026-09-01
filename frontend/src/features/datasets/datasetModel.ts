import type {
  ActivityCoverageRow,
  DataQualityReport,
  DatasetColumnProfile,
  DatasetStatus,
  MappingCreateRequest,
} from "../../types/datasets";

export type ActivityMappingFilter = "all" | "mapped" | "unmapped";

export function filterActivityCoverageRows(
  rows: ActivityCoverageRow[],
  filter: ActivityMappingFilter,
  search: string,
): ActivityCoverageRow[] {
  const query = search.trim().toLocaleLowerCase();
  return rows.filter((row) => {
    if (filter === "mapped" && !row.mapped) return false;
    if (filter === "unmapped" && row.mapped) return false;
    return !query || row.source_activity.toLocaleLowerCase().includes(query)
      || row.business_activity?.toLocaleLowerCase().includes(query);
  });
}

export interface QualityMetricView {
  key: keyof DataQualityReport;
  label: string;
  value: number;
  severity: "neutral" | "good" | "warning";
}

const statusLabels: Record<DatasetStatus, string> = {
  UPLOADING: "업로드 중",
  STAGED: "Staged",
  PROFILING: "Profiling",
  PROFILED: "Profiled",
  MAPPING_REQUIRED: "매핑 필요",
  VALIDATING: "검증 중",
  READY: "분석 가능",
  SOURCE_CHANGED: "Source changed",
  FAILED: "실패",
};

export function datasetStatusLabel(status: DatasetStatus): string {
  return statusLabels[status];
}

export function validateMappingSelection(
  mapping: MappingCreateRequest,
  columns: DatasetColumnProfile[],
): string[] {
  const errors: string[] = [];
  if (!mapping.case_id_column) errors.push("Case ID 컬럼을 선택하세요.");
  if (!mapping.activity_column) errors.push("Activity 컬럼을 선택하세요.");
  if (!mapping.timestamp_column) errors.push("Timestamp 컬럼을 선택하세요.");
  if (!mapping.timezone) errors.push("Naive timestamps require a source timezone.");
  const required = [mapping.case_id_column, mapping.activity_column, mapping.timestamp_column];
  if (required.every(Boolean) && new Set(required).size !== 3) {
    errors.push("필수 Event Log 컬럼은 서로 달라야 합니다.");
  }
  const available = new Set(columns.map((column) => column.column_name));
  const selected = [
    ...required,
    mapping.event_id_column,
    ...Object.values(mapping.optional_mappings),
  ].filter((column): column is string => Boolean(column));
  if (selected.some((column) => !available.has(column))) {
    errors.push("현재 schema에 없는 컬럼이 선택됐습니다.");
  }
  return errors;
}

export function qualityMetricViews(report: DataQualityReport): QualityMetricView[] {
  return [
    { key: "total_rows", label: "Total rows", value: report.total_rows, severity: "neutral" },
    { key: "valid_events", label: "Valid events", value: report.valid_events, severity: "good" },
    { key: "invalid_events", label: "Invalid events", value: report.invalid_events, severity: report.invalid_events ? "warning" : "good" },
    { key: "unique_cases", label: "Unique cases", value: report.unique_cases, severity: "neutral" },
    { key: "unique_activities", label: "Unique activities", value: report.unique_activities, severity: "neutral" },
    { key: "null_case_id", label: "Null case ID", value: report.null_case_id, severity: report.null_case_id ? "warning" : "good" },
    { key: "empty_case_id", label: "Empty case ID", value: report.empty_case_id, severity: report.empty_case_id ? "warning" : "good" },
    { key: "null_activity", label: "Null activity", value: report.null_activity, severity: report.null_activity ? "warning" : "good" },
    { key: "empty_activity", label: "Empty activity", value: report.empty_activity, severity: report.empty_activity ? "warning" : "good" },
    { key: "null_timestamp", label: "Null timestamp", value: report.null_timestamp, severity: report.null_timestamp ? "warning" : "good" },
    { key: "invalid_timestamp", label: "Invalid timestamp", value: report.invalid_timestamp, severity: report.invalid_timestamp ? "warning" : "good" },
    { key: "single_event_cases", label: "Single-event cases", value: report.single_event_cases, severity: "neutral" },
    { key: "duplicate_timestamp_rows", label: "Same timestamp events", value: report.duplicate_timestamp_rows, severity: report.duplicate_timestamp_rows ? "warning" : "good" },
    { key: "ambiguous_ordering_cases", label: "Ambiguous ordering cases", value: report.ambiguous_ordering_cases, severity: report.ambiguous_ordering_cases ? "warning" : "good" },
    { key: "extremely_large_cases", label: "Extremely large cases", value: report.extremely_large_cases, severity: report.extremely_large_cases ? "warning" : "good" },
    { key: "duplicate_events", label: "Duplicate events", value: report.duplicate_events, severity: report.duplicate_events ? "warning" : "good" },
  ];
}

export function formatBytes(value: number): string {
  if (value < 1_024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = value / 1_024;
  let unitIndex = 0;
  while (amount >= 1_024 && unitIndex < units.length - 1) {
    amount /= 1_024;
    unitIndex += 1;
  }
  return `${amount.toLocaleString("ko-KR", { maximumFractionDigits: 1 })} ${units[unitIndex]}`;
}
