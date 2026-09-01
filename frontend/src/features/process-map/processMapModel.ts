import type { ElementDefinition } from "cytoscape";

import type { DFGData, DFGEdge, DFGNode } from "../../types/dfg";

export type ProcessMapSelection =
  | { kind: "node"; id: string; data: DFGNode }
  | { kind: "edge"; id: string; data: DFGEdge };

export interface ProcessMapModel {
  elements: ElementDefinition[];
  visibleNodes: DFGNode[];
  visibleEdges: DFGEdge[];
  maxTransitionCount: number;
}

export function nodeElementId(activity: string): string {
  return `activity:${activity}`;
}

export function edgeElementId(source: string, target: string): string {
  return `transition:${source}\u0000${target}`;
}

export function buildProcessMapModel(
  data: DFGData,
  minimumTransitionCount: number,
): ProcessMapModel {
  const visibleEdges = data.edges.filter(
    (edge) => edge.transition_count >= minimumTransitionCount,
  );
  const maxEventCount = Math.max(1, ...data.nodes.map((node) => node.event_count));
  const maxTransitionCount = Math.max(
    1,
    ...visibleEdges.map((edge) => edge.transition_count),
  );

  const nodeElements: ElementDefinition[] = data.nodes.map((node) => ({
    data: {
      id: nodeElementId(node.activity),
      label: node.activity,
      eventCount: node.event_count,
      caseCount: node.case_count,
      caseShare: node.case_share,
      size: 42 + Math.round(22 * Math.sqrt(node.event_count / maxEventCount)),
    },
  }));
  const edgeElements: ElementDefinition[] = visibleEdges.map((edge) => ({
    data: {
      id: edgeElementId(edge.source, edge.target),
      source: nodeElementId(edge.source),
      target: nodeElementId(edge.target),
      label: String(edge.transition_count),
      transitionCount: edge.transition_count,
      caseCount: edge.case_count,
      caseShare: edge.case_share,
      medianTransitionMs: edge.median_transition_ms,
      p90TransitionMs: edge.p90_transition_ms,
      width: 2 + Math.round(6 * Math.sqrt(edge.transition_count / maxTransitionCount)),
    },
  }));

  return {
    elements: [...nodeElements, ...edgeElements],
    visibleNodes: data.nodes,
    visibleEdges,
    maxTransitionCount,
  };
}

