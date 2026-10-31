import { useEffect, useMemo, useState } from "react";

import { AppContext, MODE_DESCRIPTIONS, MODE_LABELS, type AppMode } from "./app/AppContext";
import { Icon, type IconName } from "./components/Icon";
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
import { CommandCentrePage } from "./pages/CommandCentre";
import { ComparisonPage } from "./pages/Comparison";
import { IssueRoomPage } from "./pages/IssueRoom";
import { ReplayPage } from "./pages/Replay";
import { WeeklyReportPage } from "./pages/WeeklyReport";
import type { StreamEvent } from "./types";

const PAGE_ICONS: Record<PageId, IconName> = {
  command: "command",
  cases: "cases",
  issues: "issues",
  compare: "compare",
  replay: "replay",
  report: "report",
};

const PHONE_NAV: PageId[] = ["command", "cases", "issues", "compare", "report"];

function readMode(): AppMode {
  const value = new URLSearchParams(window.location.search).get("mode");
  return value === "live" || value === "replay" ? value : "static";
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
  const [mode, setMode] = useState<AppMode>(readMode);
  const [theme, setThemeState] = useState<ThemePreference>(() => readThemePreference(window.localStorage));
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [streamStatus, setStreamStatus] = useState<"idle" | "open" | "error">("idle");
  const [menuOpen, setMenuOpen] = useState(false);
  const systemDark = useSystemDark();
  const resolvedTheme = resolveTheme(theme, systemDark);
  const route = useHashRoute();

  const source = useMemo<DashboardDataSource>(
    () =>
      mode === "static"
        ? new StaticDataSource()
        : new LiveDataSource({ baseUrl: import.meta.env.VITE_FQA_API ?? "/api" }),
    [mode],
  );

  const decisionClient = mode === "live" && source instanceof LiveDataSource ? source : null;

  useEffect(() => {
    applyTheme(theme, document.documentElement);
  }, [theme]);

  useEffect(() => {
    setStreamEvents([]);
    setStreamStatus("idle");
    const subscribe = source.subscribe?.bind(source);
    if (mode !== "live" || !subscribe) {
      return;
    }
    return subscribe((event: StreamEvent) => {
      if (event.kind === "connection") {
        setStreamStatus(event.data["status"] === "open" ? "open" : "error");
        return;
      }
      setStreamEvents((previous) => [event, ...previous].slice(0, 50));
    });
  }, [source, mode]);

  const setTheme = (next: ThemePreference) => {
    setThemeState(next);
    writeThemePreference(window.localStorage, next);
  };

  const nav = (
    <nav aria-label="Primary">
      {NAV_ITEMS.map((item) => (
        <a
          className="nav-item"
          href={routeHref({ page: item.page })}
          aria-current={route.page === item.page ? "page" : undefined}
          aria-label={item.label}
          key={item.page}
        >
          <Icon name={PAGE_ICONS[item.page]} size={18} />
          <span className="nav-label">{item.label}</span>
        </a>
      ))}
    </nav>
  );

  const modeControl = (
    <label className="select-control">
      <span className="select-label">Data mode</span>
      <select
        value={mode}
        onChange={(event) => setMode(event.target.value as AppMode)}
        aria-label="Data mode"
      >
        {(["static", "replay", "live"] as const).map((value) => (
          <option value={value} key={value}>
            {MODE_LABELS[value]}
          </option>
        ))}
      </select>
    </label>
  );

  const themeControl = (
    <label className="select-control">
      <span className="select-label">Theme</span>
      <select
        value={theme}
        onChange={(event) => setTheme(event.target.value as ThemePreference)}
        aria-label="Theme"
      >
        <option value="auto">Auto</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );

  const statusText =
    mode === "static" ? "Bundled data" : mode === "replay" ? "Replay API" : streamStatus === "open" ? "Live connected" : streamStatus === "error" ? "Live offline" : "Live connecting";

  const page = (() => {
    switch (route.page) {
      case "command":
        return <CommandCentrePage />;
      case "cases":
        return <CaseBoardPage />;
      case "issues":
        return <IssueRoomPage issueId={route.issueId} />;
      case "compare":
        return <ComparisonPage />;
      case "replay":
        return <ReplayPage />;
      case "report":
        return <WeeklyReportPage />;
    }
  })();

  return (
    <AppContext.Provider
      value={{
        mode,
        setMode,
        theme,
        resolvedTheme,
        setTheme,
        source,
        decisionClient,
        streamEvents,
        streamStatus,
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="shell">
        <aside className="rail">
          <a className="brand" href="#/">
            Field quality agents
          </a>
          {nav}
          <p className="rail-note">{MODE_DESCRIPTIONS[mode]}</p>
        </aside>

        <div className="main">
          <header className="topbar">
            <div className="topbar-title">
              <h1 className="page-title">{PAGE_TITLES[route.page]}</h1>
              {route.page === "cases" && route.caseId ? (
                <span className="crumb">/ {route.caseId}</span>
              ) : null}
            </div>
            <div className="topbar-controls">
              {modeControl}
              {themeControl}
              <span className="live-status" data-status={mode === "live" ? streamStatus : "static"}>
                <span className="live-dot" aria-hidden="true" />
                {statusText}
              </span>
            </div>
            <div className="phone-menu">
              <button
                type="button"
                className="icon-button"
                aria-label="Page menu"
                aria-expanded={menuOpen}
                aria-controls="phone-menu-panel"
                onClick={() => setMenuOpen((value) => !value)}
              >
                <Icon name="menu" size={18} />
              </button>
              {menuOpen ? (
                <div className="menu-panel" id="phone-menu-panel">
                  {modeControl}
                  {themeControl}
                  <span className="live-status" data-status={mode === "live" ? streamStatus : "static"}>
                    <span className="live-dot" aria-hidden="true" />
                    {statusText}
                  </span>
                  <a href={routeHref({ page: "replay" })} onClick={() => setMenuOpen(false)}>
                    Replay
                  </a>
                  <a href={routeHref({ page: "report" })} onClick={() => setMenuOpen(false)}>
                    Weekly report
                  </a>
                </div>
              ) : null}
            </div>
          </header>

          {mode === "static" ? (
            <p className="fixture-banner" role="note">
              Bundled fixture data for the Q6 dashboard. Q10 wires the recorded run and replaces
              these numbers.
            </p>
          ) : null}

          <main id="main-content" className="content" tabIndex={-1}>
            {page}
          </main>
        </div>
      </div>

      <nav className="bottom-nav" aria-label="Primary, mobile">
        {PHONE_NAV.map((pageId) => (
          <a
            href={routeHref({ page: pageId })}
            key={pageId}
            aria-current={route.page === pageId ? "page" : undefined}
            aria-label={NAV_ITEMS.find((item) => item.page === pageId)?.label}
          >
            <Icon name={PAGE_ICONS[pageId]} size={20} />
            <span>{NAV_ITEMS.find((item) => item.page === pageId)?.short}</span>
          </a>
        ))}
      </nav>

      {route.page === "cases" && route.caseId ? (
        <CaseDetailView
          caseId={route.caseId}
          onClose={() => {
            window.location.hash = "#/cases";
          }}
        />
      ) : null}
    </AppContext.Provider>
  );
}
