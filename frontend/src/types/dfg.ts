export interface DFGNode {
  activity: string;
  event_count: number;
  case_count: number;
  case_share: number;
}

export interface DFGEdge {
  source: string;
  target: string;
  transition_count: number;
  case_count: number;
  case_share: number;
  median_transition_ms: number;
  p90_transition_ms: number;
}

export interface DFGData {
  total_cases: number;
  total_events: number;
  node_count: number;
  edge_count: number;
  nodes: DFGNode[];
  edges: DFGEdge[];
}

export interface DFGQueryMeta {
  query_ms: number;
  rows: number;
  filter_signature: string;
  mapping_version: string;
  dataset_id: string | null;
  semantic_contract_version: string | null;
  activity_mapping_version: string | null;
  normalization_version: string | null;
  activity_level: "source" | "business";
  unique_source_activities: number | null;
  business_activities: number | null;
  event_mapping_coverage: number | null;
}

export interface DFGResponse {
  data: DFGData;
  meta: DFGQueryMeta;
  warnings: string[];
}
