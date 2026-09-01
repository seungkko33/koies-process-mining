import { useEffect, useMemo, useState } from "react";

import { fetchDFG } from "../api/dfg";
import { ProcessDetails } from "../features/process-map/ProcessDetails";
import { ProcessGraph } from "../features/process-map/ProcessGraph";
import { ProcessMapTable } from "../features/process-map/ProcessMapTable";
import {
  buildProcessMapModel,
  type ProcessMapSelection,
} from "../features/process-map/processMapModel";
import type { DFGResponse } from "../types/dfg";

const integerFormatter = new Intl.NumberFormat("ko-KR");

export function ProcessMapPage() {
  const [response, setResponse] = useState<DFGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);
  const [minimumTransitionCount, setMinimumTransitionCount] = useState(1);
  const [selection, setSelection] = useState<ProcessMapSelection | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchDFG(controller.signal)
      .then(setResponse)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "알 수 없는 오류입니다.");
      });
    return () => controller.abort();
  }, [requestVersion]);

  const maximumTransitionCount = useMemo(
    () => Math.max(1, ...(response?.data.edges.map((edge) => edge.transition_count) ?? [])),
    [response],
  );
  const model = useMemo(
    () =>
      response
        ? buildProcessMapModel(response.data, minimumTransitionCount)
        : null,
    [minimumTransitionCount, response],
  );

  if (error) {
    return (
      <section className="state-panel error">
        <p>{error}</p>
        <button
          type="button"
          onClick={() => {
            setError(null);
            setResponse(null);
            setRequestVersion((version) => version + 1);
          }}
        >
          다시 시도
        </button>
      </section>
    );
  }

  if (!response || !model) {
    return <section className="state-panel">Process Map을 불러오는 중입니다.</section>;
  }

  if (response.data.total_events === 0 || response.data.node_count === 0) {
    return <section className="state-panel">분석할 이벤트가 없습니다.</section>;
  }

  return (
    <section className="process-map-page">
      <div className="page-heading">
        <div>
          <h1>Process Map</h1>
          <p>Activity와 직접 연결된 다음 단계를 frequency 기준으로 탐색합니다.</p>
        </div>
        <span>쿼리 {response.meta.query_ms} ms</span>
      </div>

      <div className="process-summary" aria-label="Process Map 요약">
        <span><strong>{integerFormatter.format(response.data.total_cases)}</strong> cases</span>
        <span><strong>{integerFormatter.format(response.data.total_events)}</strong> events</span>
        <span><strong>{model.visibleNodes.length}</strong> activities</span>
        <span><strong>{model.visibleEdges.length}</strong> transitions</span>
      </div>

      <div className="process-controls">
        <label htmlFor="minimum-transition-count">
          Minimum transition frequency
          <strong>{integerFormatter.format(minimumTransitionCount)}</strong>
        </label>
        <input
          id="minimum-transition-count"
          type="range"
          min="1"
          max={maximumTransitionCount}
          value={minimumTransitionCount}
          onChange={(event) => {
            setMinimumTransitionCount(Number(event.target.value));
            setSelection(null);
          }}
        />
      </div>

      {response.warnings.length > 0 ? (
        <div className="analysis-warning" role="status">{response.warnings.join(" ")}</div>
      ) : null}

      <div className="process-workspace">
        <div>
          <ProcessGraph model={model} onSelectionChange={setSelection} />
          {model.visibleEdges.length === 0 ? (
            <p className="graph-empty-note">현재 threshold를 통과한 transition이 없습니다.</p>
          ) : null}
          <div className="graph-legend" aria-label="Process Map 범례">
            <span><i className="legend-node" /> Node 크기: event frequency</span>
            <span><i className="legend-edge" /> Edge 굵기: transition frequency</span>
          </div>
        </div>
        <ProcessDetails selection={selection} />
      </div>

      <ProcessMapTable edges={model.visibleEdges} />
    </section>
  );
}
