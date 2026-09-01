import type { PropsWithChildren } from "react";

export type AppPage = "datasets" | "overview" | "process-map";

const navigation = [
  { id: "datasets", label: "Datasets", enabled: true },
  { id: "overview", label: "Overview", enabled: true },
  { id: "process-map", label: "Process Map", enabled: true },
  { id: "variants", label: "Variants", enabled: false },
] as const;

interface AppShellProps extends PropsWithChildren {
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
  datasetLabel: string;
}

export function AppShell({ activePage, onNavigate, datasetLabel, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 메뉴">
        <div className="brand">Process Mining</div>
        <nav>
          {navigation.map((item) => (
            <button
              type="button"
              className={item.id === activePage ? "nav-item active" : "nav-item"}
              disabled={!item.enabled}
              aria-current={item.id === activePage ? "page" : undefined}
              key={item.id}
              onClick={() => {
                if (item.enabled) onNavigate(item.id);
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="content-shell">
        <header className="topbar">
          <span>{datasetLabel}</span>
          <span className="local-status">Local only</span>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
