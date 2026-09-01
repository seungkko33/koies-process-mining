import type { PropsWithChildren } from "react";

export type AppPage = "overview" | "process-map";

const navigation = [
  { id: "overview", label: "Overview", enabled: true },
  { id: "process-map", label: "Process Map", enabled: true },
  { id: "variants", label: "Variants", enabled: false },
  { id: "data-quality", label: "Data Quality", enabled: false },
] as const;

interface AppShellProps extends PropsWithChildren {
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
}

export function AppShell({ activePage, onNavigate, children }: AppShellProps) {
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
          <span>전체 합성 데이터</span>
          <span className="local-status">Local only</span>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
