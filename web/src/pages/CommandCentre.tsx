import { useApp } from "../app/AppContext";
import { KpiTile } from "../components/KpiTile";
import { Panel, EmptyState, ErrorState, LoadingState } from "../components/States";
import { ToneBadge } from "../components/StatusBadge";
import {
  describeStreamEvent,
  formatDateTime,
  formatHeadlineDelta,
  formatHeadlineValue,
  formatRelative,
  headlineTone,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { ComparisonSummary, StreamEvent } from "../types";

function windowLabel(window: string): string {
  const match = /^(\d+)d$/.exec(window);
  return match ? `Last ${match[1]} days` : window;
}

function streamLabel(status: "idle" | "open" | "error", mode: string): string {
  if (mode === "static") {
    return "Bundled JSON";
  }
  if (mode === "replay") {
    return "Replay API";
  }
  if (status === "open") {
    return "Live stream connected";
  }
  if (status === "error") {
    return "Live stream reconnecting";
  }
  return "Live stream connecting";
}

function FeedItem({ event }: { event: StreamEvent }) {
  return (
    <li className="feed-item">
      <span className="feed-kind" data-kind={event.kind}>
        {event.kind.replaceAll("_", " ")}
      </span>
      <span className="feed-text">{describeStreamEvent(event)}</span>
      <time dateTime={event.at} title={formatDateTime(event.at)}>
        {formatRelative(event.at)}
      </time>
    </li>
  );
}

function MiniComparison({ summary }: { summary: ComparisonSummary }) {
  if (summary.headline.length === 0) {
    return <EmptyState title="No comparison yet">The before/after summary appears after a replay run.</EmptyState>;
  }
  return (
    <table className="mini-table">
      <caption className="sr-only">Before and after headline metrics</caption>
      <thead>
        <tr>
          <th scope="col">Metric</th>
          <th scope="col">Before</th>
          <th scope="col">After</th>
          <th scope="col">Change</th>
        </tr>
      </thead>
      <tbody>
        {summary.headline.map((item) => {
          const delta = item.after - item.before;
          const tone = headlineTone(item.id, delta);
          return (
            <tr key={item.id}>
              <th scope="row">{item.label}</th>
              <td>{formatHeadlineValue(item.unit, item.before)}</td>
              <td>{formatHeadlineValue(item.unit, item.after)}</td>
              <td className={tone === "neutral" ? "" : tone === "good" ? "delta-good" : "delta-bad"}>
                {formatHeadlineDelta(item.unit, delta)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function CommandCentrePage() {
  const { source, mode, streamEvents, streamStatus } = useApp();
  const state = useAsync(() => source.getCommandCentre(), `command:${mode}`);

  if (state.data === null) {
    return state.status === "error" && state.error ? (
      <ErrorState error={state.error} onRetry={state.reload} />
    ) : (
      <LoadingState label="Loading dashboard" layout="metrics" />
    );
  }

  const data = state.data;
  const events = [
    ...streamEvents.filter((event) => event.kind !== "connection"),
    ...data.live_feed,
  ]
    .filter((event, index, all) => (event.id ? all.findIndex((item) => item.id === event.id) === index : true))
    .slice(0, 50);
  const primaryKpis = new Set(["cases_in", "human_touches", "open_issues", "cost_per_case"]);

  return (
    <div className="page">
      <p className="lede">
        The recorded desk at a glance: reports received, engineer workload and model spend.
        Decisions in this run came from a simulated engineer.{" "}
        <span className="window-label">{windowLabel(data.window)}</span>
      </p>

      {state.status === "error" && state.error ? (
        <p className="inline-warning" role="alert">
          Refresh failed: {state.error.message}. Showing the last loaded numbers.
        </p>
      ) : null}

      <div className="kpi-grid">
        {data.kpis.filter((kpi) => primaryKpis.has(kpi.id)).map((kpi) => (
          <KpiTile kpi={kpi} key={kpi.id} />
        ))}
      </div>

      <p className="dashboard-result-link">Looking for the evaluation? <a href="#/compare">Read the results and limitations</a>.</p>

      <div className="split-grid dashboard-main">
        <Panel
          title="Agent actions"
          className="feed-panel"
          aside={<ToneBadge tone={streamStatus === "error" ? "issue" : "decided"} label={streamLabel(streamStatus, mode)} />}
        >
          {events.length === 0 ? (
            <EmptyState title="No actions yet">Agent steps stream here as the desk works through cases.</EmptyState>
          ) : (
            <ol className="feed" aria-label="Recent agent actions">
              {events.slice(0, 4).map((event, index) => (
                <FeedItem event={event} key={event.id ?? `${event.at}-${index}`} />
              ))}
            </ol>
          )}
          <p className="source-note">
            {mode === "static"
              ? "Source: bundled command_centre.json."
              : "Source: GET /api/kpis and the /api/events stream."}
          </p>
        </Panel>

        <Panel title="Before vs after" aside={<a href="#/compare">Open the full comparison</a>}>
          <MiniComparison summary={data.comparison} />
          <p className="source-note">
            {mode === "static"
              ? "Source: bundled comparison.json, same replay set."
              : "Source: GET /api/comparison, same replay set."}
          </p>
        </Panel>
      </div>
      <details className="technical-disclosure"><summary>More operational measurements</summary>
        <div className="kpi-grid dashboard-secondary-kpis">{data.kpis.filter((kpi) => !primaryKpis.has(kpi.id)).map((kpi) => <KpiTile kpi={kpi} key={kpi.id} />)}</div>
      </details>
      {events.length > 4 ? <details className="technical-disclosure"><summary>Full recorded activity</summary>
        <ol className="feed" aria-label="Full recorded agent actions">{events.map((event, index) => <FeedItem event={event} key={event.id ?? index} />)}</ol>
      </details> : null}
    </div>
  );
}
