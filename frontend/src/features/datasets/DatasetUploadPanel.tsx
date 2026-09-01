import { useRef, useState } from "react";

import { uploadDataset } from "../../api/datasets";
import type { DatasetSummary } from "../../types/datasets";
import { formatBytes } from "./datasetModel";

interface DatasetUploadPanelProps {
  onUploaded: (dataset: DatasetSummary) => void;
}

type UploadPhase = "idle" | "selected" | "uploading" | "profiling" | "failed";

export function DatasetUploadPanel({ onUploaded }: DatasetUploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  function chooseFile(nextFile: File | null) {
    setFile(nextFile);
    setPhase(nextFile ? "selected" : "idle");
    setProgress(0);
    setError(null);
  }

  async function submit() {
    if (!file) return;
    setPhase("uploading");
    setError(null);
    try {
      const dataset = await uploadDataset(file, (value) => {
        setProgress(value);
        if (value === 100) setPhase("profiling");
      });
      chooseFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded(dataset);
    } catch (requestError) {
      setPhase("failed");
      setError(requestError instanceof Error ? requestError.message : "업로드에 실패했습니다.");
    }
  }

  return (
    <section className="dataset-upload" aria-labelledby="dataset-upload-heading">
      <div>
        <h2 id="dataset-upload-heading">Local file import</h2>
        <p>CSV, CSV.GZ 또는 Parquet 파일을 로컬 staging에 저장하고 DuckDB가 직접 검사합니다.</p>
      </div>
      <div
        className="drop-zone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          chooseFile(event.dataTransfer.files.item(0));
        }}
      >
        <input
          ref={inputRef}
          id="dataset-file"
          type="file"
          accept=".csv,.csv.gz,.parquet"
          onChange={(event) => chooseFile(event.target.files?.item(0) ?? null)}
        />
        <label htmlFor="dataset-file">파일 선택 또는 여기로 드래그</label>
        <span>Excel/XLSX는 대용량 ingestion 대상에서 제외됩니다.</span>
      </div>
      {file ? (
        <div className="selected-file">
          <span><strong>{file.name}</strong> · {formatBytes(file.size)}</span>
          <button type="button" disabled={phase === "uploading" || phase === "profiling"} onClick={submit}>
            Upload &amp; profile
          </button>
        </div>
      ) : null}
      {phase === "uploading" || phase === "profiling" ? (
        <div className="upload-progress" role="status">
          <progress max="100" value={progress} />
          <span>{phase === "uploading" ? `업로드 ${progress}%` : "Schema profiling 중…"}</span>
        </div>
      ) : null}
      {error ? <p className="inline-error" role="alert">{error}</p> : null}
    </section>
  );
}
