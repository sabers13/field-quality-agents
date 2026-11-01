import { useApp } from "../app/AppContext";
import { Icon } from "../components/Icon";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/States";
import {
  formatEstimate,
  formatHeadlineDelta,
  formatHeadlineValue,
  formatMetricValue,
  formatPercent,
  headlineTone,
  isEstimate,
  metricMeta,
  type MetricKind,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { ComparisonData, ComparisonSummary, MetricEstimate } from "../types";

function rowValue(value: MetricEstimate | number | null, kind: MetricKind): string {
  if (value === null) {
    return "—";
  }
  if (isEstimate(value)) {
    return formatEstimate(value, kind);
  }
  return formatMetricValue(value, kind);
}

function HeadlineCards({ summary }: { summary: ComparisonSummary }) {
  return (
    <div className="headline-grid">
      {summary.headline.map((item) => {
        const delta = item.after - item.before;
        const tone = headlineTone(item.id, delta);
        return (
          <article className="headline-card" key={item.id}>
            <span className="headline-label">{item.label}</span>
            <span className="headline-values">
              <span className="headline-before">{formatHeadlineValue(item.unit, item.before)}</span>
              <Icon name="chevron" size={14} />
              <span className="headline-after">{formatHeadlineValue(item.unit, item.after)}</span>
            </span>
            <span
              className={
                tone === "neutral" ? "headline-delta" : tone === "good" ? "headline-delta is-good" : "headline-delta is-bad"
              }
            >
              {formatHeadlineDelta(item.unit, delta)}
            </span>
          </article>
        );
      })}
    </div>
  );
}

function MetricsTable({ data }: { data: ComparisonData }) {
  return (
    <>
      <table className="metrics-table">
        <caption className="sr-only">Same replay set through both pipelines, with confidence intervals</caption>
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">Linear pipeline</th>
            <th scope="col">Agentic desk</th>
            <th scope="col">Note</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => {
            const meta = metricMeta(row.metric, row.label);
            return (
              <tr key={row.metric}>
                <th scope="row">{meta.label}</th>
                <td className="numeric">{rowValue(row.before, meta.kind)}</td>
                <td className="numeric">{rowValue(row.after, meta.kind)}</td>
                <td className="note-cell">{row.note ?? ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <dl className="metrics-list">
        {data.rows.map((row) => {
          const meta = metricMeta(row.metric, row.label);
          return (
            <div className="metrics-row" key={row.metric}>
              <dt>{meta.label}</dt>
              <dd>
                <span className="metrics-pipeline">Linear</span> {rowValue(row.before, meta.kind)}
              </dd>
              <dd>
                <span className="metrics-pipeline">Agentic</span> {rowValue(row.after, meta.kind)}
              </dd>
              {row.note ? <dd className="note-cell">{row.note}</dd> : null}
            </div>
          );
        })}
      </dl>
    </>
  );
}

export function ComparisonPage() {
  const { source, mode } = useApp();
  const state = useAsync(() => source.getComparison(), `comparison:${mode}`);

  if (state.data === null) {
    return state.status === "error" && state.error ? (
      <ErrorState error={state.error} onRetry={state.reload} />
    ) : (
      <LoadingState label="Loading comparison" />
    );
  }

  const data = state.data;
  const agentWins = data.summary.examples.filter((example) => !example.note.toLowerCase().includes("reverse"));
  const reverse = data.summary.examples.filter((example) => example.note.toLowerCase().includes("reverse"));

  return (
    <div className="page">
      <p className="lede">
        The same replay set through both pipelines. Every estimate carries its confidence interval
        where the method requires one; the arrows show direction, not significance.
      </p>

      <HeadlineCards summary={data.summary} />

      <Panel
        title="Metrics side by side"
        aside={<span className="muted">{data.after.cases} cases · {data.after.budget_hits} budget hits after</span>}
      >
        <p className="callout">
          Issue precision is read beside the base rate: a random week of the same series hits the
          same early-issue rule {formatPercent(data.after.issue_base_rate ?? 0)} of the time.
        </p>
        <MetricsTable data={data} />
      </Panel>

      <div className="split-grid">
        <Panel title="Where the agent found what the linear pipeline missed">
          {agentWins.length === 0 ? (
            <EmptyState title="No positive example in this run" />
          ) : (
            <ul className="example-list">
              {agentWins.map((example) => (
                <li key={example.case_id}>
                  <a href={`#/cases/${encodeURIComponent(example.case_id)}`} className="example-case">
                    <code>{example.case_id}</code> <Icon name="chevron" size={12} />
                  </a>
                  <dl className="before-after">
                    <div>
                      <dt>Before</dt>
                      <dd>{example.before}</dd>
                    </div>
                    <div>
                      <dt>After</dt>
                      <dd>{example.after}</dd>
                    </div>
                  </dl>
                  <p>{example.note}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Where the linear pipeline was right">
          {reverse.length === 0 ? (
            <EmptyState title="No reverse example in this run" />
          ) : (
            <ul className="example-list">
              {reverse.map((example) => (
                <li key={example.case_id}>
                  <a href={`#/cases/${encodeURIComponent(example.case_id)}`} className="example-case">
                    <code>{example.case_id}</code> <Icon name="chevron" size={12} />
                  </a>
                  <dl className="before-after">
                    <div>
                      <dt>Before</dt>
                      <dd>{example.before}</dd>
                    </div>
                    <div>
                      <dt>After</dt>
                      <dd>{example.after}</dd>
                    </div>
                  </dl>
                  <p>{example.note}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <p className="source-note">
        {mode === "static" ? "Source: bundled comparison.json." : "Source: GET /api/comparison."} Both
        columns cover the same {data.after.cases} cases.
      </p>
    </div>
  );
}
