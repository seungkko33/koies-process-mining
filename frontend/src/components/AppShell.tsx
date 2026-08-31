import type { PropsWithChildren } from "react";

const navigation = ["Overview", "Process Map", "Variants", "Data Quality"];

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 메뉴">
        <div className="brand">Process Mining</div>
        <nav>
          {navigation.map((item, index) => (
            <button className={index === 0 ? "nav-item active" : "nav-item"} key={item}>
              {item}
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

