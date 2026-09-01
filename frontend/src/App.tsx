import { lazy, Suspense, useState } from "react";

import { AppShell, type AppPage } from "./components/AppShell";
import { OverviewPage } from "./pages/OverviewPage";
import type { DatasetSummary } from "./types/datasets";

const DatasetsPage = lazy(() =>
  import("./pages/DatasetsPage").then((module) => ({ default: module.DatasetsPage })),
);
const ProcessMapPage = lazy(() =>
  import("./pages/ProcessMapPage").then((module) => ({ default: module.ProcessMapPage })),
);

export default function App() {
  const [activePage, setActivePage] = useState<AppPage>("overview");
  const [activeDataset, setActiveDataset] = useState<DatasetSummary | null>(null);

  function pageContent() {
    if (activePage === "datasets") {
      return (
        <DatasetsPage
          onAnalyze={(dataset, page) => {
            setActiveDataset(dataset);
            setActivePage(page);
          }}
        />
      );
    }
    if (activePage === "overview") {
      return <OverviewPage datasetId={activeDataset?.dataset_id} />;
    }
    return <ProcessMapPage datasetId={activeDataset?.dataset_id} />;
  }

  return (
    <AppShell
      activePage={activePage}
      onNavigate={setActivePage}
      datasetLabel={activeDataset ? `Dataset: ${activeDataset.original_filename}` : "기본 합성 데이터"}
    >
      <Suspense fallback={<section className="state-panel">화면을 준비하는 중입니다.</section>}>
        {pageContent()}
      </Suspense>
    </AppShell>
  );
}
