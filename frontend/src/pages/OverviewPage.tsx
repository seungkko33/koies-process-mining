import { useEffect, useState } from "react";

import { fetchOverview } from "../api/overview";
import { Metric } from "../components/Metric";
import type { OverviewResponse } from "../types/overview";

const integerFormatter = new Intl.NumberFormat("ko-KR");

function formatDuration(value: number | null): string {
  if (value === null) return "—";
  const minutes = value / 60_000;
  return `${minutes.toLocaleString("ko-KR", { maximumFractionDigits: 1 })}분`;
}

function formatRate(value: number): string {
  return value.toLocaleString("ko-KR", { style: "percent", maximumFractionDigits: 1 });
}

interface OverviewPageProps {
  datasetId?: string | null;
}

export function OverviewPage({ datasetId = null }: OverviewPageProps) {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchOverview(controller.signal, datasetId)
      .then(setOverview)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "알 수 없는 오류입니다.");
      });
    return () => controller.abort();
  }, [datasetId]);

  if (error) {
    return <section className="state-panel error">{error}</section>;
  }

  if (!overview) {
    return <section className="state-panel">Overview를 불러오는 중입니다.</section>;
  }

  if (overview.data.event_count === 0) {
    return <section className="state-panel">분석할 이벤트가 없습니다.</section>;
  }

  return (
    <section className="overview">
      <div className="page-heading">
        <div>
          <h1>Overview</h1>
          <p>DuckDB가 계산한 현재 이벤트 로그 요약입니다.</p>
        </div>
        <span>쿼리 {overview.meta.query_ms} ms</span>
      </div>
      <dl className="metrics" aria-label="프로세스 핵심 지표">
        <Metric label="Cases" value={integerFormatter.format(overview.data.case_count)} />
        <Metric label="Events" value={integerFormatter.format(overview.data.event_count)} />
        <Metric label="Activities" value={integerFormatter.format(overview.data.activity_count)} />
        <Metric
          label="Median Throughput"
          value={formatDuration(overview.data.median_throughput_ms)}
        />
        <Metric
          label="P90 Throughput"
          value={formatDuration(overview.data.p90_throughput_ms)}
        />
        <Metric label="Rework Rate" value={formatRate(overview.data.rework_rate)} />
      </dl>
    </section>
  );
}
