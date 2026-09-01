import { describe, expect, it } from "vitest";

import { parseDFGResponse } from "./dfg";

const validResponse = {
  data: {
    total_cases: 3,
    total_events: 10,
    node_count: 2,
    edge_count: 1,
    nodes: [
      { activity: "A", event_count: 3, case_count: 3, case_share: 1 },
      { activity: "B", event_count: 3, case_count: 2, case_share: 2 / 3 },
    ],
    edges: [
      {
        source: "A",
        target: "B",
        transition_count: 2,
        case_count: 2,
        case_share: 2 / 3,
        median_transition_ms: 90_000,
        p90_transition_ms: 114_000,
      },
    ],
  },
  meta: { query_ms: 2, rows: 3, filter_signature: "all", mapping_version: "all" },
  warnings: [],
};

describe("parseDFGResponse", () => {
  it("parses the backend DFG contract", () => {
    expect(parseDFGResponse(validResponse)).toEqual(validResponse);
  });

  it("rejects inconsistent count metadata", () => {
    const invalidResponse = structuredClone(validResponse);
    invalidResponse.data.edge_count = 2;

    expect(() => parseDFGResponse(invalidResponse)).toThrow(
      "DFG count와 node/edge 배열 길이가 일치하지 않습니다.",
    );
  });

  it("rejects malformed error payloads instead of silently rendering them", () => {
    expect(() => parseDFGResponse({ detail: "query failed" })).toThrow(
      "DFG API 응답 형식이 올바르지 않습니다.",
    );
  });
});

