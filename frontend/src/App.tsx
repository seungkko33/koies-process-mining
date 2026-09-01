import { lazy, Suspense, useState } from "react";

import { AppShell, type AppPage } from "./components/AppShell";
import { OverviewPage } from "./pages/OverviewPage";

const ProcessMapPage = lazy(() =>
  import("./pages/ProcessMapPage").then((module) => ({ default: module.ProcessMapPage })),
);

export default function App() {
  const [activePage, setActivePage] = useState<AppPage>("overview");

  return (
    <AppShell activePage={activePage} onNavigate={setActivePage}>
      {activePage === "overview" ? (
        <OverviewPage />
      ) : (
        <Suspense fallback={<section className="state-panel">Process Map을 준비하는 중입니다.</section>}>
          <ProcessMapPage />
        </Suspense>
      )}
    </AppShell>
  );
}
