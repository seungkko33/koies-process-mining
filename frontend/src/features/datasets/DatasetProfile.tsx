import type { DatasetPreviewResponse, DatasetProfileResponse } from "../../types/datasets";

interface DatasetProfileProps {
  profile: DatasetProfileResponse;
  preview: DatasetPreviewResponse;
}

function renderCell(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function DatasetProfile({ profile, preview }: DatasetProfileProps) {
  return (
    <>
      <section className="dataset-section" aria-labelledby="schema-heading">
        <div className="section-heading">
          <h2 id="schema-heading">Schema &amp; fast profile</h2>
          <span>{profile.columns.length} columns · approximate distinct</span>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr><th>Column</th><th>DuckDB type</th><th>Null</th><th>Approx. distinct</th><th>Min / Max</th><th>Samples</th></tr>
            </thead>
            <tbody>
              {profile.columns.map((column) => (
                <tr key={column.column_name}>
                  <td><strong>{column.column_name}</strong></td>
                  <td>{column.inferred_type}</td>
                  <td>{column.null_count.toLocaleString("ko-KR")}</td>
                  <td>{column.approx_distinct.toLocaleString("ko-KR")}</td>
                  <td className="compact-values">{column.min_value ?? "—"}<br />{column.max_value ?? "—"}</td>
                  <td className="compact-values">{column.sample_values.join(" · ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="dataset-section" aria-labelledby="preview-heading">
        <div className="section-heading">
          <h2 id="preview-heading">Data preview</h2>
          <span>최대 {preview.limit}행 중 {preview.returned_rows}행 표시</span>
        </div>
        <div className="table-scroll preview-table-scroll">
          <table className="data-table preview-table">
            <thead><tr>{preview.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>
              {preview.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {preview.columns.map((column) => <td key={column}>{renderCell(row[column])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
