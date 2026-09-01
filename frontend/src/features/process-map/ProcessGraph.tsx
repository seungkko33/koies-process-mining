import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

import type { ProcessMapModel, ProcessMapSelection } from "./processMapModel";
import { edgeElementId, nodeElementId } from "./processMapModel";

interface ProcessGraphProps {
  model: ProcessMapModel;
  onSelectionChange: (selection: ProcessMapSelection | null) => void;
}

const graphStyle: cytoscape.StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      width: "data(size)",
      height: "data(size)",
      "background-color": "#2f6fdf",
      "border-color": "#ffffff",
      "border-width": 2,
      color: "#172033",
      "font-size": 12,
      "font-weight": 600,
      "text-valign": "bottom",
      "text-margin-y": 8,
      "text-wrap": "ellipsis",
      "text-max-width": "120px",
      "min-zoomed-font-size": 8,
    },
  },
  {
    selector: "edge",
    style: {
      width: "data(width)",
      label: "data(label)",
      "curve-style": "bezier",
      "line-color": "#9aa8bd",
      "target-arrow-color": "#9aa8bd",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
      color: "#56647b",
      "font-size": 10,
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.9,
      "text-background-padding": "3px",
      "min-zoomed-font-size": 8,
    },
  },
  {
    selector: ":selected",
    style: {
      "background-color": "#173f8a",
      "line-color": "#173f8a",
      "target-arrow-color": "#173f8a",
      "border-color": "#f0a04b",
      "border-width": 4,
    },
  },
];

export function ProcessGraph({ model, onSelectionChange }: ProcessGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<cytoscape.Core | null>(null);
  const selectionHandlerRef = useRef(onSelectionChange);

  useEffect(() => {
    selectionHandlerRef.current = onSelectionChange;
  }, [onSelectionChange]);

  useEffect(() => {
    if (!containerRef.current) return;

    const graph = cytoscape({
      container: containerRef.current,
      elements: model.elements,
      style: graphStyle,
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 36,
        spacingFactor: 1.35,
      },
      autoungrabify: true,
      boxSelectionEnabled: false,
      minZoom: 0.35,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
    });
    graphRef.current = graph;

    graph.on("tap", "node", (event) => {
      const id = event.target.id();
      const node = model.visibleNodes.find(
        (candidate) => nodeElementId(candidate.activity) === id,
      );
      if (node) selectionHandlerRef.current({ kind: "node", id, data: node });
    });
    graph.on("tap", "edge", (event) => {
      const id = event.target.id();
      const edge = model.visibleEdges.find(
        (candidate) => edgeElementId(candidate.source, candidate.target) === id,
      );
      if (edge) selectionHandlerRef.current({ kind: "edge", id, data: edge });
    });
    graph.on("tap", (event) => {
      if (event.target === graph) selectionHandlerRef.current(null);
    });

    return () => {
      graphRef.current = null;
      graph.destroy();
    };
  }, [model]);

  return (
    <div className="graph-surface">
      <div className="graph-toolbar" aria-label="Process Map 보기 도구">
        <button type="button" onClick={() => graphRef.current?.fit(undefined, 36)}>
          Fit
        </button>
        <button type="button" onClick={() => graphRef.current?.reset()}>
          Reset view
        </button>
      </div>
      <div className="process-graph" ref={containerRef} aria-label="프로세스 맵 그래프" />
    </div>
  );
}
