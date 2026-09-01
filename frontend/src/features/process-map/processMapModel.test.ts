import { describe, expect, it } from "vitest";

import type { DFGData } from "../../types/dfg";
import { buildProcessMapModel, edgeElementId, nodeElementId } from "./processMapModel";

const dfg: DFGData = {
  total_cases: 3,
  total_events: 10,
  node_count: 3,
  edge_count: 2,
  nodes: [
    { activity: "A", event_count: 3, case_count: 3, case_share: 1 },
    { activity: "B", event_count: 3, case_count: 2, case_share: 2 / 3 },
    { activity: "C", event_count: 1, case_count: 1, case_share: 1 / 3 },
  ],
  edges: [
    {
      source: "A",
      target: "B",
      transition_count: 3,
      case_count: 3,
      case_share: 1,
      median_transition_ms: 100,
      p90_transition_ms: 120,
    },
    {
      source: "B",
      target: "C",
      transition_count: 1,
      case_count: 1,
      case_share: 1 / 3,
      median_transition_ms: 200,
      p90_transition_ms: 200,
    },
  ],
};

describe("buildProcessMapModel", () => {
  it("maps API activities and transitions to stable Cytoscape elements", () => {
    const model = buildProcessMapModel(dfg, 1);
    const ids = model.elements.map((element) => element.data.id);

    expect(ids).toContain(nodeElementId("A"));
    expect(ids).toContain(edgeElementId("A", "B"));
    expect(model.visibleNodes).toHaveLength(3);
    expect(model.visibleEdges).toHaveLength(2);
  });

  it("filters only rendered transitions without recalculating business metrics", () => {
    const model = buildProcessMapModel(dfg, 2);

    expect(model.visibleNodes).toHaveLength(3);
    expect(model.visibleEdges.map((edge) => `${edge.source}->${edge.target}`)).toEqual(["A->B"]);
    expect(model.elements).toHaveLength(4);
  });

  it("returns an empty topology for an empty API result", () => {
    const model = buildProcessMapModel(
      { ...dfg, total_cases: 0, total_events: 0, node_count: 0, edge_count: 0, nodes: [], edges: [] },
      1,
    );

    expect(model.elements).toEqual([]);
    expect(model.visibleEdges).toEqual([]);
  });
});

