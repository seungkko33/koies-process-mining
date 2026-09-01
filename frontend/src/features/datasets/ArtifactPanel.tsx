import type { ArtifactListResponse, DatasetArtifact } from "../../types/datasets";
import { formatBytes } from "./datasetModel";

interface ArtifactPanelProps {
  value: ArtifactListResponse;
  busy: boolean;
  onPin: (artifact: DatasetArtifact, pinned: boolean) => Promise<void>;
  onDelete: (artifact: DatasetArtifact) => Promise<void>;
}

export function ArtifactPanel({ value, busy, onPin, onDelete }: ArtifactPanelProps) {
  const usage = value.disk_usage;
  return (
    <section className="dataset-section" aria-labelledby="artifact-heading">
      <div className="section-heading">
        <div><h2 id="artifact-heading">Artifacts and disk usage</h2><p>Cleanup is explicit; source, active, and pinned artifacts are protected.</p></div>
        <span>{formatBytes(usage.total)} managed</span>
      </div>
      <div className="coverage-strip">
        <span>Raw <strong>{formatBytes(usage.raw_source)}</strong></span>
        <span>Normalized <strong>{formatBytes(usage.normalized)}</strong></span>
        <span>Quarantine <strong>{formatBytes(usage.quarantine)}</strong></span>
        <span>Previous <strong>{formatBytes(usage.previous_versions)}</strong></span>
        <span>Temporary <strong>{formatBytes(usage.temporary)}</strong></span>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Type</th><th>Contract</th><th>Size</th><th>Status</th><th>Path</th><th>Actions</th></tr></thead>
          <tbody>{value.artifacts.map((artifact) => (
            <tr key={artifact.artifact_id}>
              <td>{artifact.artifact_type}</td>
              <td>{artifact.semantic_contract_version ? `v${artifact.semantic_contract_version}` : "—"}</td>
              <td>{formatBytes(artifact.size_bytes)}</td>
              <td>{artifact.active ? "Active" : "Inactive"}{artifact.pinned ? " · Pinned" : ""}</td>
              <td>{artifact.path}</td>
              <td className="artifact-actions">
                <button className="table-link" type="button" disabled={busy || artifact.artifact_type === "SOURCE"} onClick={() => onPin(artifact, !artifact.pinned)}>{artifact.pinned ? "Unpin" : "Pin"}</button>
                <button className="danger-link" type="button" disabled={busy || artifact.active || artifact.pinned || artifact.artifact_type === "SOURCE"} onClick={() => onDelete(artifact)}>Delete</button>
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}
