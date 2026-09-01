import type { DatasetSummary } from "../../types/datasets";
import { datasetStatusLabel, formatBytes } from "./datasetModel";

interface DatasetListProps {
  datasets: DatasetSummary[];
  selectedId: string | null;
  onSelect: (datasetId: string) => void;
  onDelete: (dataset: DatasetSummary) => void;
}

export function DatasetList({ datasets, selectedId, onSelect, onDelete }: DatasetListProps) {
  return (
    <section className="dataset-list-section" aria-labelledby="dataset-list-heading">
      <div className="section-heading">
        <h2 id="dataset-list-heading">Datasets</h2>
        <span>{datasets.length} local files</span>
      </div>
      {datasets.length === 0 ? (
        <p className="muted-message">등록된 Dataset이 없습니다.</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table dataset-list-table">
            <thead>
              <tr><th>File</th><th>Format</th><th>Size</th><th>Rows</th><th>Status</th><th>Contract</th><th>Activity map</th><th>Created</th><th /></tr>
            </thead>
            <tbody>
              {datasets.map((dataset) => (
                <tr className={dataset.dataset_id === selectedId ? "selected-row" : undefined} key={dataset.dataset_id}>
                  <td>
                    <button className="table-link" type="button" onClick={() => onSelect(dataset.dataset_id)}>
                      {dataset.original_filename}
                    </button>
                  </td>
                  <td>{dataset.file_type}</td>
                  <td>{formatBytes(dataset.file_size_bytes)}</td>
                  <td>{dataset.row_count?.toLocaleString("ko-KR") ?? "—"}</td>
                  <td><span className={`status-text status-${dataset.status.toLowerCase()}`}>{datasetStatusLabel(dataset.status)}</span></td>
                  <td>{dataset.semantic_contract_version ? `v${dataset.semantic_contract_version}` : "—"}</td>
                  <td>{dataset.active_activity_mapping_version ? `v${dataset.active_activity_mapping_version}` : "—"}</td>
                  <td>{new Date(dataset.created_at).toLocaleString("ko-KR")}</td>
                  <td>
                    <button className="danger-link" type="button" onClick={() => onDelete(dataset)}>삭제</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
