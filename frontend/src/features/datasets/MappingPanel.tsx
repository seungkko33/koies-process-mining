import { useState } from "react";

import type {
  DatasetColumnProfile,
  MappingCreateRequest,
  MappingDefinitionResponse,
  PIIClassification,
  RetentionPolicy,
} from "../../types/datasets";
import { validateMappingSelection } from "./datasetModel";

interface MappingPanelProps {
  columns: DatasetColumnProfile[];
  mapping: MappingDefinitionResponse | null;
  busy: boolean;
  onSave: (mapping: MappingCreateRequest) => Promise<void>;
  onNormalize: () => Promise<void>;
}

const emptyMapping: MappingCreateRequest = {
  case_id_column: "",
  activity_column: "",
  timestamp_column: "",
  event_id_column: null,
  optional_mappings: {},
  timestamp_format: null,
  timezone: "Asia/Seoul",
  display_timezone: "Asia/Seoul",
  case_null_policy: "REJECT",
  case_empty_policy: "REJECT",
  case_id_pseudonymized: false,
  case_id_classification: "NONE",
  attribute_policies: {},
  pii_classifications: {},
  ordering_fields: ["event_ts", "source_sequence", "event_id", "source_row_number"],
  business_activity_mapping_version: null,
};

export function MappingPanel({ columns, mapping, busy, onSave, onNormalize }: MappingPanelProps) {
  const [form, setForm] = useState<MappingCreateRequest>(emptyMapping);
  const [errors, setErrors] = useState<string[]>([]);
  const options = columns.map((column) => column.column_name);
  const mappedAttributes = [
    ...(form.event_id_column ? ["event_id"] : []),
    ...Object.keys(form.optional_mappings),
  ];

  function setRequired(
    field: "case_id_column" | "activity_column" | "timestamp_column",
    value: string,
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function setOptional(field: string, value: string) {
    setForm((current) => {
      const optional = { ...current.optional_mappings };
      if (value) optional[field] = value;
      else {
        delete optional[field];
        const attributePolicies = { ...current.attribute_policies };
        const piiClassifications = { ...current.pii_classifications };
        delete attributePolicies[field];
        delete piiClassifications[field];
        return {
          ...current,
          optional_mappings: optional,
          attribute_policies: attributePolicies,
          pii_classifications: piiClassifications,
        };
      }
      return { ...current, optional_mappings: optional };
    });
  }

  function setClassification(field: string, value: PIIClassification) {
    setForm((current) => {
      const attributePolicies = { ...current.attribute_policies };
      if (!(field in attributePolicies)) {
        attributePolicies[field] = value === "PII" || value === "SENSITIVE" ? "DROP" : "KEEP";
      }
      return {
        ...current,
        attribute_policies: attributePolicies,
        pii_classifications: { ...current.pii_classifications, [field]: value },
      };
    });
  }

  function setRetention(field: string, value: RetentionPolicy) {
    setForm((current) => ({
      ...current,
      attribute_policies: { ...current.attribute_policies, [field]: value },
    }));
  }

  async function save() {
    const nextErrors = validateMappingSelection(form, columns);
    setErrors(nextErrors);
    if (nextErrors.length === 0) await onSave(form);
  }

  return (
    <section className="dataset-section mapping-section" aria-labelledby="mapping-heading">
      <div className="section-heading">
        <div>
          <h2 id="mapping-heading">Semantic Contract</h2>
          <p>Define event meaning, timezone, ordering, and minimum retention.</p>
        </div>
        {mapping ? <span>Contract v{mapping.semantic_contract_version}</span> : null}
      </div>
      <div className="mapping-grid">
        <ColumnSelect label="Case ID *" value={form.case_id_column} options={options} onChange={(value) => setRequired("case_id_column", value)} />
        <ColumnSelect label="Activity *" value={form.activity_column} options={options} onChange={(value) => setRequired("activity_column", value)} />
        <ColumnSelect label="Timestamp *" value={form.timestamp_column} options={options} onChange={(value) => setRequired("timestamp_column", value)} />
        <ColumnSelect label="Event ID" value={form.event_id_column ?? ""} options={options} onChange={(value) => setForm((current) => {
          if (value) return { ...current, event_id_column: value };
          const attributePolicies = { ...current.attribute_policies };
          const piiClassifications = { ...current.pii_classifications };
          delete attributePolicies.event_id;
          delete piiClassifications.event_id;
          return { ...current, event_id_column: null, attribute_policies: attributePolicies, pii_classifications: piiClassifications };
        })} />
        <ColumnSelect label="Source sequence" value={form.optional_mappings.source_sequence ?? ""} options={options} onChange={(value) => setOptional("source_sequence", value)} />
        <ColumnSelect label="Method" value={form.optional_mappings.method ?? ""} options={options} onChange={(value) => setOptional("method", value)} />
        <ColumnSelect label="Resource" value={form.optional_mappings.resource ?? ""} options={options} onChange={(value) => setOptional("resource", value)} />
        <ColumnSelect label="User" value={form.optional_mappings.user ?? ""} options={options} onChange={(value) => setOptional("user", value)} />
        <ColumnSelect label="Department" value={form.optional_mappings.department ?? ""} options={options} onChange={(value) => setOptional("department", value)} />
        <ColumnSelect label="System" value={form.optional_mappings.system ?? ""} options={options} onChange={(value) => setOptional("system", value)} />
        <ColumnSelect label="Status" value={form.optional_mappings.status ?? ""} options={options} onChange={(value) => setOptional("status", value)} />
        <ColumnSelect label="Duration" value={form.optional_mappings.duration ?? ""} options={options} onChange={(value) => setOptional("duration", value)} />
        <label>Timestamp format<input type="text" placeholder="e.g. %Y-%m-%d %H:%M:%S" value={form.timestamp_format ?? ""} onChange={(event) => setForm((current) => ({ ...current, timestamp_format: event.target.value || null }))} /></label>
        <label>Source timezone<input type="text" placeholder="Asia/Seoul" value={form.timezone ?? ""} onChange={(event) => setForm((current) => ({ ...current, timezone: event.target.value || null }))} /></label>
        <label>Display timezone<input type="text" placeholder="Asia/Seoul" value={form.display_timezone ?? ""} onChange={(event) => setForm((current) => ({ ...current, display_timezone: event.target.value || null }))} /></label>
        <label>Case ID classification<select value={form.case_id_classification} onChange={(event) => setForm((current) => ({ ...current, case_id_classification: event.target.value as MappingCreateRequest["case_id_classification"] }))}><option value="NONE">NONE</option><option value="POTENTIAL_PII">POTENTIAL_PII</option><option value="PII">PII</option><option value="SENSITIVE">SENSITIVE</option></select></label>
        <label className="checkbox-field"><input type="checkbox" checked={form.case_id_pseudonymized} onChange={(event) => setForm((current) => ({ ...current, case_id_pseudonymized: event.target.checked }))} />Keyed HMAC case ID</label>
      </div>
      {mappedAttributes.length > 0 ? (
        <div className="attribute-policy-grid" aria-label="Attribute classification and retention">
          <strong>Attribute</strong><strong>PII classification</strong><strong>Retention</strong>
          {mappedAttributes.map((field) => (
            <div className="attribute-policy-row" key={field}>
              <span>{field}</span>
              <select
                aria-label={`${field} PII classification`}
                value={form.pii_classifications[field] ?? "NONE"}
                onChange={(event) => setClassification(field, event.target.value as PIIClassification)}
              >
                <option value="NONE">NONE</option><option value="POTENTIAL_PII">POTENTIAL_PII</option><option value="PII">PII</option><option value="SENSITIVE">SENSITIVE</option>
              </select>
              <select
                aria-label={`${field} retention policy`}
                value={form.attribute_policies[field] ?? "KEEP"}
                onChange={(event) => setRetention(field, event.target.value as RetentionPolicy)}
              >
                <option value="KEEP">KEEP</option><option value="DROP">DROP</option>
                {field !== "duration" && field !== "source_sequence" ? <option value="PSEUDONYMIZE">PSEUDONYMIZE</option> : null}
              </select>
            </div>
          ))}
        </div>
      ) : null}
      <p className="contract-note">Order: event_ts → source_sequence → event_id → source_row_number. The last key is deterministic fallback, not business chronology.</p>
      {errors.length > 0 ? <ul className="inline-error">{errors.map((error) => <li key={error}>{error}</li>)}</ul> : null}
      <div className="form-actions">
        <button className="secondary-button" type="button" disabled={busy} onClick={save}>Save contract version</button>
        <button className="primary-button" type="button" disabled={busy || !mapping} onClick={onNormalize}>Validate and normalize</button>
      </div>
      {mapping ? (
        <div className="timestamp-preview">
          <strong>Timestamp preview</strong>
          <div className="timestamp-preview-header"><span>Raw</span><span>Parsed</span><span>UTC</span><span>Display</span></div>
          {mapping.timestamp_preview.map((item, index) => (
            <div className="timestamp-preview-row" key={`${item.source_value}-${index}`}>
              <span>{item.source_value}</span>
              <span>{item.parsed_value ?? "parse failed"}</span>
              <span>{item.utc_value ?? "—"}</span>
              <span>{item.display_value ?? "—"}</span>
            </div>
          ))}
          <p>Source {mapping.timezone} · display {mapping.display_timezone} · canonical UTC</p>
        </div>
      ) : null}
    </section>
  );
}

interface ColumnSelectProps {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}

function ColumnSelect({ label, value, options, onChange }: ColumnSelectProps) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select column</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
