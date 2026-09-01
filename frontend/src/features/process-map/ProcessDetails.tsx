import type { ProcessMapSelection } from "./processMapModel";

const integerFormatter = new Intl.NumberFormat("ko-KR");

function formatShare(value: number): string {
  return value.toLocaleString("ko-KR", { style: "percent", maximumFractionDigits: 1 });
}

function formatDuration(value: number): string {
  if (value < 1_000) return `${integerFormatter.format(value)} ms`;
  return `${(value / 1_000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}초`;
}

interface ProcessDetailsProps {
  selection: ProcessMapSelection | null;
}

export function ProcessDetails({ selection }: ProcessDetailsProps) {
  if (!selection) {
    return (
      <aside className="process-details" aria-live="polite">
        <h2>선택 상세</h2>
        <p>Activity 또는 transition을 선택하면 빈도와 소요시간을 확인할 수 있습니다.</p>
      </aside>
    );
  }

  if (selection.kind === "node") {
    return (
      <aside className="process-details" aria-live="polite">
        <span className="detail-type">Activity</span>
        <h2>{selection.data.activity}</h2>
        <dl>
          <div><dt>Events</dt><dd>{integerFormatter.format(selection.data.event_count)}</dd></div>
          <div><dt>Cases</dt><dd>{integerFormatter.format(selection.data.case_count)}</dd></div>
          <div><dt>Case share</dt><dd>{formatShare(selection.data.case_share)}</dd></div>
        </dl>
      </aside>
    );
  }

  return (
    <aside className="process-details" aria-live="polite">
      <span className="detail-type">Transition</span>
      <h2>{selection.data.source} → {selection.data.target}</h2>
      <dl>
        <div><dt>Transitions</dt><dd>{integerFormatter.format(selection.data.transition_count)}</dd></div>
        <div><dt>Cases</dt><dd>{integerFormatter.format(selection.data.case_count)}</dd></div>
        <div><dt>Case share</dt><dd>{formatShare(selection.data.case_share)}</dd></div>
        <div><dt>Median</dt><dd>{formatDuration(selection.data.median_transition_ms)}</dd></div>
        <div><dt>P90</dt><dd>{formatDuration(selection.data.p90_transition_ms)}</dd></div>
      </dl>
    </aside>
  );
}

