import { useMemo, useState } from "react";

import type {
  ActivityMappingCoverage,
  ActivityMappingEntry,
  ActivityMappingSet,
  UnmappedActivityPolicy,
} from "../../types/datasets";
import {
  filterActivityCoverageRows,
  type ActivityMappingFilter,
} from "./datasetModel";

interface ActivityMappingPanelProps {
  mappingSets: ActivityMappingSet[];
  coverage: ActivityMappingCoverage | null;
  busy: boolean;
  onSelectVersion: (version: number) => Promise<void>;
  onCreateVersion: (
    name: string,
    policy: UnmappedActivityPolicy,
    entries: ActivityMappingEntry[],
  ) => Promise<void>;
}

export function ActivityMappingPanel({
  mappingSets,
  coverage,
  busy,
  onSelectVersion,
  onCreateVersion,
}: ActivityMappingPanelProps) {
  const [filter, setFilter] = useState<ActivityMappingFilter>("all");
  const [search, setSearch] = useState("");
  const [policy, setPolicy] = useState<UnmappedActivityPolicy>("KEEP_SOURCE");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const rows = useMemo(
    () => filterActivityCoverageRows(coverage?.rows ?? [], filter, search),
    [coverage, filter, search],
  );

  function updateDraft(source: string, business: string) {
    setDraft((current) => ({ ...current, [source]: business }));
  }

  async function saveVersion() {
    const entries = Object.entries(draft)
      .filter(([, business]) => business.trim())
      .map(([source_activity, business_activity]) => ({
        source_activity,
        business_activity: business_activity.trim(),
        description: null,
        enabled: true,
      }));
    await onCreateVersion(`Business activities ${new Date().toLocaleString()}`, policy, entries);
  }

  return (
    <section className="dataset-section" aria-labelledby="activity-mapping-heading">
      <div className="section-heading">
        <div>
          <h2 id="activity-mapping-heading">Method → Business Activity</h2>
          <p>Exact mapping only. Saving creates an append-only version.</p>
        </div>
        <select
          aria-label="Activity mapping version"
          value={coverage?.activity_mapping_version ?? ""}
          onChange={(event) => onSelectVersion(Number(event.target.value))}
        >
          <option value="">New version</option>
          {mappingSets.map((item) => <option key={item.version} value={item.version}>v{item.version} · {item.name}</option>)}
        </select>
      </div>
      {coverage ? (
        <div className="coverage-strip">
          <span><strong>{coverage.unique_source_activities}</strong> source</span>
          <span><strong>{coverage.mapped_activities}</strong> mapped</span>
          <span><strong>{coverage.unmapped_activities}</strong> unmapped</span>
          <span><strong>{coverage.business_activities}</strong> business</span>
          <span><strong>{(coverage.event_mapping_coverage * 100).toFixed(1)}%</strong> event coverage</span>
        </div>
      ) : <p className="muted-message">Normalize first, then create an exact activity mapping version.</p>}
      <div className="mapping-toolbar">
        <input aria-label="Search source activity" placeholder="Search methods" value={search} onChange={(event) => setSearch(event.target.value)} />
        <select aria-label="Mapping status filter" value={filter} onChange={(event) => setFilter(event.target.value as ActivityMappingFilter)}><option value="all">All</option><option value="mapped">Mapped</option><option value="unmapped">Unmapped</option></select>
        <select aria-label="Unmapped policy" value={policy} onChange={(event) => setPolicy(event.target.value as UnmappedActivityPolicy)}><option value="KEEP_SOURCE">KEEP_SOURCE</option><option value="GROUP_AS_UNMAPPED">GROUP_AS_UNMAPPED</option><option value="EXCLUDE">EXCLUDE</option></select>
      </div>
      {coverage ? (
        <div className="table-scroll activity-mapping-table">
          <table className="data-table">
            <thead><tr><th>Source Activity</th><th>Business Activity</th><th>Events</th><th>Cases</th><th>Mapped?</th></tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row.source_activity}>
                <td>{row.source_activity}</td>
                <td><input value={draft[row.source_activity] ?? row.business_activity ?? ""} onChange={(event) => updateDraft(row.source_activity, event.target.value)} /></td>
                <td>{row.event_count.toLocaleString()}</td>
                <td>{row.case_count.toLocaleString()}</td>
                <td>{row.mapped ? "Mapped" : "Unmapped"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : null}
      <div className="form-actions"><button className="primary-button" type="button" disabled={busy} onClick={saveVersion}>{coverage ? "Create mapping version" : "Initialize mapping"}</button></div>
    </section>
  );
}
