export interface OverviewData {
  case_count: number;
  event_count: number;
  activity_count: number;
  median_throughput_ms: number | null;
  p90_throughput_ms: number | null;
  rework_rate: number;
}

export interface QueryMeta {
  query_ms: number;
  rows: number;
  filter_signature: string;
  mapping_version: string;
}

export interface OverviewResponse {
  data: OverviewData;
  meta: QueryMeta;
  warnings: string[];
}

