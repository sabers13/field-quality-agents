import { BOARD_COLUMNS } from "./lib/status";

const KPIS = [
  { label: "Cases in", value: "—", context: "Awaiting the Q1 replay set" },
  { label: "Prepared without human edits", value: "—", context: "Simulated engineer" },
  { label: "Human touches / case", value: "—", context: "Both pipelines" },
  { label: "Open issues", value: "—", context: "Issue agent lands in Q8" },
  { label: "Cost / case", value: "—", context: "Recorded calls only" },
  { label: "NTF without evidence", value: "—", context: "Before vs after" },
];

const NAV = [
  "Command centre",
  "Case board",
  "Issue room",
  "Before vs after",
  "Replay",
  "Weekly report",
];

export function App() {
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">Field quality agents</div>
        <nav aria-label="Primary">
          {NAV.map((item, index) => (
            <a
              className="nav-item"
              href={index === 0 ? "#" : `#${item.toLowerCase().replaceAll(" ", "-")}`}
              aria-current={index === 0 ? "page" : undefined}
              key={item}
            >
              <span className="nav-label">{item}</span>
            </a>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <h1 className="page-title">Command centre</h1>
          <span className="mode">
            <span className="mode-dot" aria-hidden="true" />
            Q0 scaffold
          </span>
        </header>

        <section className="content" aria-labelledby="overview-heading">
          <h2 id="overview-heading" hidden>
            Overview
          </h2>
          <p className="lede">
            The same returns process, run by a linear rule pipeline and by an agentic desk, on
            the same cases. Agents gather evidence and draft; engineers decide.
          </p>

          <div className="kpi-grid">
            {KPIS.map((kpi) => (
              <article className="kpi" key={kpi.label}>
                <div className="kpi-label">{kpi.label}</div>
                <div className="kpi-value">{kpi.value}</div>
                <div className="kpi-context">{kpi.context}</div>
              </article>
            ))}
          </div>

          <div className="scaffold-note">
            Q0 scaffold: design tokens, status mapping and chart themes are in place. Pages, charts
            and live data land in Q6/Q7; the board columns are{" "}
            {BOARD_COLUMNS.map((column) => column.label).join(" · ")}.
          </div>
        </section>
      </main>

      <nav className="bottom-nav" aria-label="Primary, mobile">
        <a href="#" aria-current="page">
          Command
        </a>
        <a href="#case-board">Cases</a>
        <a href="#issue-room">Issues</a>
        <a href="#before-vs-after">Compare</a>
        <a href="#weekly-report">Report</a>
      </nav>
    </div>
  );
}
