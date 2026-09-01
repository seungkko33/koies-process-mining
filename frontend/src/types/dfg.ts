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
}

export interface DFGResponse {
  data: DFGData;
  meta: DFGQueryMeta;
  warnings: string[];
}

