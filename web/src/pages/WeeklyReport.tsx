import { useApp } from "../app/AppContext";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/States";
import {
  formatDate,
  formatDateTime,
  formatEstimate,
  formatInteger,
  formatMetricValue,
  isEstimate,
  metricMeta,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { Metrics } from "../types";

const SKIP = new Set(["cases"]);

function MetricsGrid({ metrics }: { metrics: Metrics }) {
  const rows = Object.entries(metrics).filter(([key, value]) => !SKIP.has(key) && value !== null);
  const display = (value: unknown, kind: ReturnType<typeof metricMeta>["kind"]): string => {
    if (value === null) {
      return "—";
    }
    if (isEstimate(value)) {
      return formatEstimate(value, kind);
    }
    if (typeof value === "number") {
      return formatMetricValue(value, kind);
    }
    return String(value);
  };

  return (
    <>
      <table className="metrics-table weekly-metrics">
        <caption className="sr-only">Weekly metrics with confidence intervals</caption>
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">Value</th>
            <th scope="col">n</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([key, value]) => {
            const meta = metricMeta(key);
            return (
              <tr key={key}>
                <th scope="row">{meta.label}</th>
                <td className="numeric">{display(value, meta.kind)}</td>
                <td className="numeric">{isEstimate(value) ? formatInteger(value.n) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <dl className="metrics-list">
        {rows.map(([key, value]) => {
          const meta = metricMeta(key);
          return (
            <div className="metrics-row" key={key}>
              <dt>{meta.label}</dt>
              <dd>{display(value, meta.kind)}</dd>
              {isEstimate(value) ? (
                <dd>
                  <span className="metrics-pipeline">n</span> {formatInteger(value.n)}
                </dd>
              ) : null}
            </div>
          );
        })}
      </dl>
    </>
  );
}

export function WeeklyReportPage() {
  const { source, mode } = useApp();
  const state = useAsync(() => source.getWeeklyReport(), `weekly:${mode}`);

  if (state.data === null) {
    return state.status === "error" && state.error ? (
      <ErrorState error={state.error} onRetry={state.reload} />
    ) : (
      <LoadingState label="Loading weekly report" />
    );
  }

  const report = state.data;

  return (
    <div className="page">
      <p className="lede">
        The report agent's output for one week: arrivals, decisions, engineer load and the metrics
        for the same cases.
      </p>

      <header className="report-head">
        <div>
          <p className="eyebrow">Week {formatDate(report.week_start)} – {formatDate(report.week_end)}</p>
          <h2>{formatInteger(report.cases_received)} cases received, {formatInteger(report.cases_decided)} decided</h2>
          <p className="muted">Generated {formatDateTime(report.generated_at)}</p>
        </div>
      </header>

      <Panel title="Report narrative">
        {report.narrative ? (
          <p className="report-narrative">{report.narrative}</p>
        ) : (
          <EmptyState title="No narrative">
            The report agent writes the week's story from the committed run files.
          </EmptyState>
        )}
      </Panel>

      <div className="stat-grid">
        <article className="stat-card">
          <span className="stat-label">Cases received</span>
          <span className="stat-value">{formatInteger(report.cases_received)}</span>
        </article>
        <article className="stat-card">
          <span className="stat-label">Decided</span>
          <span className="stat-value">{formatInteger(report.cases_decided)}</span>
        </article>
        <article className="stat-card" data-tone="needs_engineer">
          <span className="stat-label">Needs engineer</span>
          <span className="stat-value">{formatInteger(report.cases_needing_engineer)}</span>
        </article>
        <article className="stat-card" data-tone="issue">
          <span className="stat-label">Open issues</span>
          <span className="stat-value">{formatInteger(report.open_issues)}</span>
        </article>
        <article className="stat-card">
          <span className="stat-label">Targeted test proposals</span>
          <span className="stat-value">{formatInteger(report.proposals_targeted_test)}</span>
        </article>
      </div>

      <details className="technical-disclosure"><summary>Detailed measurements for this week</summary>
        <Panel title="Metrics for the week"><MetricsGrid metrics={report.metrics} /></Panel>
      </details>

      <p className="source-note">
        {mode === "static" ? "Source: bundled weekly_report.json." : "Source: GET /api/reports/weekly."}
      </p>
    </div>
  );
}
