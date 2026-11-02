import { useEffect, useMemo, useState } from "react";

import { AppContext, type AppMode } from "./app/AppContext";
import { Icon, type IconName } from "./components/Icon";
import { WorkspaceSettings } from "./components/WorkspaceSettings";
import { bundledManifest } from "./data/bundled";
import { LiveDataSource, type DashboardDataSource } from "./data/source";
import { StaticDataSource } from "./data/static";
import { NAV_ITEMS, PAGE_TITLES, parseRoute, routeHref, type PageId } from "./lib/router";
import {
  applyTheme,
  readThemePreference,
  resolveTheme,
  writeThemePreference,
  type ThemePreference,
} from "./lib/theme";
import { CaseBoardPage, CaseDetailView } from "./pages/CaseBoard";
import { OverviewPage } from "./pages/Overview";
import { CommandCentrePage } from "./pages/CommandCentre";
import { ComparisonPage } from "./pages/Comparison";
import { IssueRoomPage } from "./pages/IssueRoom";
import { ReplayPage } from "./pages/Replay";
import { WeeklyReportPage } from "./pages/WeeklyReport";
import type { StreamEvent } from "./types";

const PRIMARY_PAGES: PageId[] = ["overview", "cases", "issues", "compare"];
const TOOL_PAGES: PageId[] = ["command", "replay", "report"];
const PAGE_ICONS: Record<PageId, IconName> = {
  overview: "command", command: "command", cases: "cases", issues: "issues",
  compare: "compare", replay: "replay", report: "report",
};
function readMode(): AppMode {
  const value = new URLSearchParams(window.location.search).get("mode");
  if (value === "static" || value === "live" || value === "replay") return value;
  return window.location.protocol === "file:" ? "static" : "replay";
}
function useSystemDark(): boolean {
  const [dark, setDark] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => setDark(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);
  return dark;
}

function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    window.scrollTo({ top: 0 });
    const onHashChange = () => {
      setHash(window.location.hash);
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return parseRoute(hash);
}

export function App() {
  const bundled = bundledManifest();
  const [mode, setMode] = useState<AppMode>(() => bundled ? "static" : readMode());
  const [theme, setThemeState] = useState<ThemePreference>(() => readThemePreference(window.localStorage));
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [streamStatus, setStreamStatus] = useState<"idle" | "open" | "error">("idle");
  const systemDark = useSystemDark();
  const resolvedTheme = resolveTheme(theme, systemDark);
  const route = useHashRoute();
  const source = useMemo<DashboardDataSource>(() => mode === "static"
    ? new StaticDataSource()
    : new LiveDataSource({ baseUrl: import.meta.env.VITE_FQA_API ?? "/api" }), [mode]);
  const decisionClient = mode === "live" && source instanceof LiveDataSource ? source : null;

  useEffect(() => {
    applyTheme(theme, document.documentElement);
    const meta = document.querySelector('meta[name="theme-color"]');
    meta?.setAttribute("content", resolvedTheme === "dark" ? "#030712" : "#f9fafb");
  }, [theme, resolvedTheme]);
  useEffect(() => {
    document.title = route.page === "overview" ? "Field quality agents — evidence for engineer review" : `${PAGE_TITLES[route.page]} — Field quality agents`;
  }, [route.page]);
  useEffect(() => {
    setStreamEvents([]);
    setStreamStatus("idle");
    const subscribe = source.subscribe?.bind(source);
    if (mode !== "live" || !subscribe) return;
    return subscribe((event: StreamEvent) => {
      if (event.kind === "connection") {
        setStreamStatus(event.data["status"] === "open" ? "open" : "error");
      } else setStreamEvents((previous) => [event, ...previous].slice(0, 50));
    });
  }, [source, mode]);

  const setTheme = (next: ThemePreference) => {
    setThemeState(next);
    writeThemePreference(window.localStorage, next);
  };
  const changeMode = (next: AppMode) => {
    setMode(next);
    const url = new URL(window.location.href);
    url.searchParams.set("mode", next);
    window.history.replaceState(null, "", url);
  };
  const navLink = (page: PageId, tool = false) => {
    const item = NAV_ITEMS.find((item) => item.page === page)!;
    return <a key={page} href={routeHref({ page })} className={tool ? "tool-link" : "project-nav-link"}
      aria-current={route.page === page ? "page" : undefined}
      aria-label={item.label} title={tool ? item.label : undefined}>
      {tool ? <Icon name={PAGE_ICONS[page]} size={20} /> : null}<span>{item.short}</span>
    </a>;
  };
  const statusText = mode === "static" ? "Saved results" : mode === "replay" ? "Recorded run"
    : streamStatus === "open" ? "Live connected" : streamStatus === "error" ? "Connection interrupted" : "Connecting…";
  const page = (() => {
    switch (route.page) {
      case "overview": return <OverviewPage />;
      case "command": return <CommandCentrePage />;
      case "cases": return <CaseBoardPage />;
      case "issues": return <IssueRoomPage issueId={route.issueId} />;
      case "compare": return <ComparisonPage />;
      case "replay": return <ReplayPage />;
      case "report": return <WeeklyReportPage />;
    }
  })();
  return <AppContext.Provider value={{ mode, setMode: changeMode, theme, resolvedTheme, setTheme, source,
    decisionClient, streamEvents, streamStatus }}>
    <a className="skip-link" href="#main-content" onClick={(event) => {
      event.preventDefault();
      const main = document.getElementById("main-content");
      main?.focus();
      main?.scrollIntoView({ block: "start" });
    }}>Skip to content</a>
    <div className="project-app">
      <header className="portfolio-header">
        <div className="portfolio-header-inner">
          <a className="portfolio-brand" href="https://sabersojudi.com/">Saber Sojudi</a>
          <nav className="project-nav" aria-label="Primary">
            {PRIMARY_PAGES.map((id) => navLink(id))}
            <span className="mobile-tool-links">{TOOL_PAGES.map((id) => navLink(id))}</span>
          </nav>
          <div className="portfolio-header-end">
            <a className="project-badge" href="#/">Field quality agents</a>
            <a className="portfolio-back" href="https://sabersojudi.com/" aria-label="Back to the portfolio">
              <Icon name="arrow-up" size={16} /><span>Back</span>
            </a>
          </div>
        </div>
      </header>
      <div className="project-workspace">
        <aside className="tool-rail" aria-label="Project tools">
          <nav aria-label="Inspect the run">{TOOL_PAGES.map((id) => navLink(id, true))}</nav>
          <a className="tool-link rail-home" href="https://sabersojudi.com/" title="Back to portfolio" aria-label="Back to portfolio">
            <Icon name="external" size={18} /><span>Portfolio</span>
          </a>
        </aside>
        <div className="workspace-sheet">
          <div className="workspace-toolbar">
            <div className="recorded-status"><span className="status-dot" aria-hidden="true" />{statusText}
              {mode !== "live" ? <span className="toolbar-context"> · Read-only evidence</span> : null}</div>
            <WorkspaceSettings bundled={Boolean(bundled)} />
          </div>
          <main id="main-content" className="workspace-content" tabIndex={-1}>
            {route.page !== "overview" ? <div className="workspace-page-heading">
              <a className="back-overview" href="#/">Project overview <Icon name="chevron" size={12} /></a>
              <h1>{PAGE_TITLES[route.page]}</h1>
            </div> : null}
            <div className="route-content" key={route.page}>{page}</div>
          </main>
          <footer className="project-footer"><span>Field quality agents · Public complaint evidence</span>
            <a href="#/compare">Results & limitations</a><a href="./THIRD_PARTY_NOTICES.txt">Credits</a><a href="https://sabersojudi.com/">Back to portfolio</a></footer>
        </div>
      </div>
    </div>
    {route.page === "cases" && route.caseId ? <CaseDetailView caseId={route.caseId}
      onClose={() => { window.location.hash = "#/cases"; }} /> : null}
  </AppContext.Provider>;
}
