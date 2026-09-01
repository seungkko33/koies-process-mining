import type { DataQualityReport, DatasetSummary } from "../../types/datasets";
import { qualityMetricViews } from "./datasetModel";

interface DataQualityPanelProps {
  dataset: DatasetSummary;
  quality: DataQualityReport;
  onAnalyze: (page: "overview" | "process-map") => void;
}

export function DataQualityPanel({ dataset, quality, onAnalyze }: DataQualityPanelProps) {
  return (
    <section className="dataset-section quality-section" aria-labelledby="quality-heading">
      <div className="section-heading">
        <div><h2 id="quality-heading">Data Quality</h2><p>Technical validation 기준이며 business rule 판단은 포함하지 않습니다.</p></div>
        <span className={quality.invalid_events ? "quality-outcome warning" : "quality-outcome"}>{quality.outcome}</span>
      </div>
      <dl className="quality-grid">
        {qualityMetricViews(quality).map((metric) => (
          <div className={`quality-metric ${metric.severity}`} key={metric.key}>
            <dt>{metric.label}</dt><dd>{metric.value.toLocaleString("ko-KR")}</dd>
          </div>
        ))}
      </dl>
      <div className="quality-breakdown">
        <span>Technical quality <strong>{quality.technical_quality}</strong></span>
        <span>Semantic quality <strong>{quality.semantic_quality}</strong></span>
        <span>Events/case min · median · p90 · max <strong>{quality.events_per_case_min} · {quality.events_per_case_median.toFixed(1)} · {quality.events_per_case_p90.toFixed(1)} · {quality.events_per_case_max}</strong></span>
      </div>
      {quality.invalid_events > 0 ? <p className="quality-note">Invalid rows는 원본에서 삭제하지 않고 failure code만 포함한 quarantine Parquet으로 분리했습니다.</p> : null}
      {dataset.status === "READY" ? (
        <div className="form-actions">
          <button className="secondary-button" type="button" onClick={() => onAnalyze("overview")}>Overview 분석</button>
          <button className="primary-button" type="button" onClick={() => onAnalyze("process-map")}>Process Map 열기</button>
        </div>
      ) : null}
    </section>
  );
}
