import type { DFGData, DFGEdge, DFGNode, DFGQueryMeta, DFGResponse } from "../types/dfg";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(record: JsonRecord, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`DFG 응답의 ${key} 값이 올바르지 않습니다.`);
  return value;
}

function readNumber(record: JsonRecord, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`DFG 응답의 ${key} 값이 올바르지 않습니다.`);
  }
  return value;
}

function parseNode(value: unknown): DFGNode {
  if (!isRecord(value)) throw new Error("DFG node 형식이 올바르지 않습니다.");
  return {
    activity: readString(value, "activity"),
    event_count: readNumber(value, "event_count"),
    case_count: readNumber(value, "case_count"),
    case_share: readNumber(value, "case_share"),
  };
}

function parseEdge(value: unknown): DFGEdge {
  if (!isRecord(value)) throw new Error("DFG edge 형식이 올바르지 않습니다.");
  return {
    source: readString(value, "source"),
    target: readString(value, "target"),
    transition_count: readNumber(value, "transition_count"),
    case_count: readNumber(value, "case_count"),
    case_share: readNumber(value, "case_share"),
    median_transition_ms: readNumber(value, "median_transition_ms"),
    p90_transition_ms: readNumber(value, "p90_transition_ms"),
  };
}

function parseData(value: unknown): DFGData {
  if (!isRecord(value) || !Array.isArray(value.nodes) || !Array.isArray(value.edges)) {
    throw new Error("DFG data 형식이 올바르지 않습니다.");
  }
  const nodes = value.nodes.map(parseNode);
  const edges = value.edges.map(parseEdge);
  const data = {
    total_cases: readNumber(value, "total_cases"),
    total_events: readNumber(value, "total_events"),
    node_count: readNumber(value, "node_count"),
    edge_count: readNumber(value, "edge_count"),
    nodes,
    edges,
  };
  if (data.node_count !== nodes.length || data.edge_count !== edges.length) {
    throw new Error("DFG count와 node/edge 배열 길이가 일치하지 않습니다.");
  }
  return data;
}

function parseMeta(value: unknown): DFGQueryMeta {
  if (!isRecord(value)) throw new Error("DFG meta 형식이 올바르지 않습니다.");
  return {
    query_ms: readNumber(value, "query_ms"),
    rows: readNumber(value, "rows"),
    filter_signature: readString(value, "filter_signature"),
    mapping_version: readString(value, "mapping_version"),
    dataset_id: typeof value.dataset_id === "string" ? value.dataset_id : null,
    semantic_contract_version: typeof value.semantic_contract_version === "string" ? value.semantic_contract_version : null,
    activity_mapping_version: typeof value.activity_mapping_version === "string" ? value.activity_mapping_version : null,
    normalization_version: typeof value.normalization_version === "string" ? value.normalization_version : null,
    activity_level: value.activity_level === "business" ? "business" : "source",
    unique_source_activities: typeof value.unique_source_activities === "number" ? value.unique_source_activities : null,
    business_activities: typeof value.business_activities === "number" ? value.business_activities : null,
    event_mapping_coverage: typeof value.event_mapping_coverage === "number" ? value.event_mapping_coverage : null,
  };
}

export function parseDFGResponse(value: unknown): DFGResponse {
  if (!isRecord(value) || !Array.isArray(value.warnings)) {
    throw new Error("DFG API 응답 형식이 올바르지 않습니다.");
  }
  const warnings = value.warnings.map((warning) => {
    if (typeof warning !== "string") throw new Error("DFG warning 형식이 올바르지 않습니다.");
    return warning;
  });
  return { data: parseData(value.data), meta: parseMeta(value.meta), warnings };
}

export async function fetchDFG(
  signal?: AbortSignal,
  datasetId?: string | null,
  activityLevel: "source" | "business" = "source",
): Promise<DFGResponse> {
  const parameters = new URLSearchParams();
  if (datasetId) parameters.set("dataset_id", datasetId);
  if (activityLevel === "business") parameters.set("activity_level", activityLevel);
  const query = parameters.size ? `?${parameters.toString()}` : "";
  const response = await fetch(`/api/dfg${query}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Process Map 요청에 실패했습니다. (${response.status})`);
  }
  return parseDFGResponse(await response.json());
}
