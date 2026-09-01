import { useEffect, useState } from "react";

import {
  createActivityMappingSet,
  createDatasetMapping,
  deleteArtifact,
  deleteDataset,
  fetchActivityMappingCoverage,
  fetchActivityMappingSets,
  fetchArtifacts,
  fetchDatasetPreview,
  fetchDatasetProfile,
  fetchDatasetQuality,
  fetchDatasets,
  normalizeDataset,
  setArtifactPinned,
} from "../api/datasets";
import { ActivityMappingPanel } from "../features/datasets/ActivityMappingPanel";
import { ArtifactPanel } from "../features/datasets/ArtifactPanel";
import { DataQualityPanel } from "../features/datasets/DataQualityPanel";
import { DatasetList } from "../features/datasets/DatasetList";
import { DatasetProfile } from "../features/datasets/DatasetProfile";
import { DatasetUploadPanel } from "../features/datasets/DatasetUploadPanel";
import { LocalImportPanel } from "../features/datasets/LocalImportPanel";
import { MappingPanel } from "../features/datasets/MappingPanel";
import type {
  ActivityMappingCoverage,
  ActivityMappingEntry,
  ActivityMappingSet,
  ArtifactListResponse,
  DataQualityReport,
  DatasetArtifact,
  DatasetPreviewResponse,
  DatasetProfileResponse,
  DatasetSummary,
  MappingCreateRequest,
  MappingDefinitionResponse,
  UnmappedActivityPolicy,
} from "../types/datasets";

interface DatasetsPageProps {
  onAnalyze: (dataset: DatasetSummary, page: "overview" | "process-map") => void;
}

export function DatasetsPage({ onAnalyze }: DatasetsPageProps) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<DatasetProfileResponse | null>(null);
  const [preview, setPreview] = useState<DatasetPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<MappingDefinitionResponse | null>(null);
  const [quality, setQuality] = useState<DataQualityReport | null>(null);
  const [activityMappingSets, setActivityMappingSets] = useState<ActivityMappingSet[]>([]);
  const [coverage, setCoverage] = useState<ActivityMappingCoverage | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactListResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchDatasets(controller.signal).then(setDatasets).catch((requestError: unknown) => {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setError(requestError instanceof Error ? requestError.message : "Dataset 목록을 불러오지 못했습니다.");
    });
    return () => controller.abort();
  }, []);

  async function selectDataset(datasetId: string) {
    setSelectedId(datasetId);
    setMapping(null);
    setQuality(null);
    setActivityMappingSets([]);
    setCoverage(null);
    setArtifacts(null);
    setError(null);
    setBusy(true);
    try {
      const selectedDataset = datasets.find((dataset) => dataset.dataset_id === datasetId);
      const ready = selectedDataset?.status === "READY";
      const [nextProfile, nextPreview, nextQuality, nextSets, nextArtifacts] = await Promise.all([
        fetchDatasetProfile(datasetId),
        fetchDatasetPreview(datasetId),
        ready ? fetchDatasetQuality(datasetId) : Promise.resolve(null),
        ready ? fetchActivityMappingSets(datasetId) : Promise.resolve([]),
        ready ? fetchArtifacts(datasetId) : Promise.resolve(null),
      ]);
      setProfile(nextProfile);
      setPreview(nextPreview);
      setQuality(nextQuality);
      setActivityMappingSets(nextSets);
      setArtifacts(nextArtifacts);
      const activeVersion = selectedDataset?.active_activity_mapping_version
        ?? nextSets[0]?.version;
      if (activeVersion) {
        setCoverage(await fetchActivityMappingCoverage(datasetId, activeVersion));
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Dataset을 불러오지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUploaded(dataset: DatasetSummary) {
    setDatasets((current) => [dataset, ...current.filter((item) => item.dataset_id !== dataset.dataset_id)]);
    await selectDataset(dataset.dataset_id);
  }

  async function handleMapping(request: MappingCreateRequest) {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      setMapping(await createDatasetMapping(selectedId, request));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "매핑 저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleNormalize() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await normalizeDataset(selectedId);
      setQuality(result.quality);
      setProfile((current) => current ? { ...current, dataset: result.dataset } : current);
      setDatasets((current) => current.map((item) => item.dataset_id === selectedId ? result.dataset : item));
      const [nextSets, nextArtifacts] = await Promise.all([
        fetchActivityMappingSets(selectedId),
        fetchArtifacts(selectedId),
      ]);
      setActivityMappingSets(nextSets);
      setArtifacts(nextArtifacts);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "정규화에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectActivityVersion(version: number) {
    if (!selectedId) return;
    setCoverage(await fetchActivityMappingCoverage(selectedId, version));
  }

  async function handleCreateActivityVersion(
    name: string,
    policy: UnmappedActivityPolicy,
    entries: ActivityMappingEntry[],
  ) {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createActivityMappingSet(selectedId, {
        name,
        unmapped_policy: policy,
        entries,
      });
      const [nextSets, nextCoverage] = await Promise.all([
        fetchActivityMappingSets(selectedId),
        fetchActivityMappingCoverage(selectedId, created.version),
      ]);
      setActivityMappingSets(nextSets);
      setCoverage(nextCoverage);
      setDatasets((current) => current.map((item) => item.dataset_id === selectedId
        ? { ...item, active_activity_mapping_version: created.version }
        : item));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Activity mapping failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshArtifacts() {
    if (selectedId) setArtifacts(await fetchArtifacts(selectedId));
  }

  async function handlePinArtifact(artifact: DatasetArtifact, pinned: boolean) {
    if (!selectedId) return;
    await setArtifactPinned(selectedId, artifact.artifact_id, pinned);
    await refreshArtifacts();
  }

  async function handleDeleteArtifact(artifact: DatasetArtifact) {
    if (!selectedId) return;
    await deleteArtifact(selectedId, artifact.artifact_id);
    await refreshArtifacts();
  }

  async function handleDelete(dataset: DatasetSummary) {
    if (!window.confirm(`${dataset.original_filename} Dataset과 로컬 산출물을 삭제할까요?`)) return;
    setBusy(true);
    try {
      await deleteDataset(dataset.dataset_id);
      setDatasets((current) => current.filter((item) => item.dataset_id !== dataset.dataset_id));
      if (selectedId === dataset.dataset_id) {
        setSelectedId(null);
        setProfile(null);
        setPreview(null);
        setMapping(null);
        setQuality(null);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Dataset 삭제에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="datasets-page">
      <div className="page-heading">
        <div><h1>Datasets</h1><p>파일은 이 PC 안에서만 staging, profiling, normalization됩니다.</p></div>
        <span>20M+ rows · DuckDB direct scan</span>
      </div>
      <div className="disk-warning">원본 + normalized Parquet + DuckDB temporary spill이 동시에 필요할 수 있습니다. 여유 디스크 공간을 먼저 확인하세요.</div>
      <DatasetUploadPanel onUploaded={handleUploaded} />
      <LocalImportPanel onImported={handleUploaded} />
      <DatasetList datasets={datasets} selectedId={selectedId} onSelect={selectDataset} onDelete={handleDelete} />
      {busy ? <p className="workspace-status" role="status">Local Dataset 작업을 처리하는 중입니다…</p> : null}
      {error ? <p className="inline-error" role="alert">{error}</p> : null}
      {profile && preview ? (
        <div className="dataset-workflow">
          <DatasetProfile profile={profile} preview={preview} />
          <MappingPanel key={profile.dataset.dataset_id} columns={profile.columns} mapping={mapping} busy={busy} onSave={handleMapping} onNormalize={handleNormalize} />
          {quality ? <DataQualityPanel dataset={profile.dataset} quality={quality} onAnalyze={(page) => onAnalyze(profile.dataset, page)} /> : null}
          {quality ? <ActivityMappingPanel mappingSets={activityMappingSets} coverage={coverage} busy={busy} onSelectVersion={handleSelectActivityVersion} onCreateVersion={handleCreateActivityVersion} /> : null}
          {artifacts ? <ArtifactPanel value={artifacts} busy={busy} onPin={handlePinArtifact} onDelete={handleDeleteArtifact} /> : null}
        </div>
      ) : selectedId ? null : <p className="workspace-empty">Dataset을 업로드하거나 목록에서 선택하면 schema와 mapping workflow가 표시됩니다.</p>}
    </section>
  );
}
