import { useState } from "react";

import type { DatasetSummary, ImportMode } from "../../types/datasets";
import { importLocalDataset } from "../../api/datasets";

interface LocalImportPanelProps {
  onImported: (dataset: DatasetSummary) => Promise<void>;
}

export function LocalImportPanel({ onImported }: LocalImportPanelProps) {
  const [path, setPath] = useState("");
  const [mode, setMode] = useState<ImportMode>("COPY");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await onImported(await importLocalDataset(path, mode));
      setPath("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Local import failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dataset-section local-import" aria-labelledby="local-import-heading">
      <div className="section-heading"><div><h2 id="local-import-heading">Large local file import</h2><p>Only absolute paths under configured allowed roots are accepted. No filesystem browser is exposed.</p></div></div>
      <div className="mapping-toolbar">
        <input aria-label="Allowed local file path" value={path} onChange={(event) => setPath(event.target.value)} placeholder="D:\\KOIES_DATA\\events.csv" />
        <select aria-label="Local import mode" value={mode} onChange={(event) => setMode(event.target.value as ImportMode)}><option value="COPY">COPY · reproducible</option><option value="REFERENCE">REFERENCE · low-copy</option></select>
        <button className="primary-button" type="button" disabled={busy || !path.trim()} onClick={submit}>Import</button>
      </div>
      {error ? <p className="inline-error" role="alert">{error}</p> : null}
    </section>
  );
}
