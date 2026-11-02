import { formatDate, formatMetricValue, formatMoney } from "../lib/format";
import { finalLiveRows } from "../lib/finalLive";
import { Panel } from "./States";
import type { FinalLiveData } from "../types";

/**
 * Q14: the sealed 150-case set, run live after Q9 and never used before.
 *
 * Every number comes from `results/final-live/metrics.json` and the Q9 run's
 * `metrics.json`, read by the export. A withheld value renders as an em dash.
 */
export function FinalLivePanel({ data }: { data: FinalLiveData }) {
  const rows = finalLiveRows(data);
  const groupRow = rows.find((row) => row.metric === "group_macro_f1");
  const perCase = data.final.cases > 0 ? data.spend_usd / data.final.cases : 0;
  return (
    <Panel
      title="Final live test"
      aside={<span className="badge">{data.final.cases} unseen cases</span>}
    >
      <p className="lede">
        The desk ran again on {data.final.cases} reports it had never seen
        ({formatDate(data.window_start)} to {formatDate(data.window_end)}), and the
        original recorded comparison is beside it. Spend {formatMoney(data.spend_usd)} (
        {formatMoney(perCase, { perCase: true })} per case), {data.budget_hits} budget{" "}
        {data.budget_hits === 1 ? "hit" : "hits"}.
      </p>
      {groupRow && groupRow.final !== null && groupRow.final < 0.1 ? (
        <div className="evaluation-note"><div><strong>Component classification failed in the unseen test</strong>
          <p>The agent returned component descriptions rather than the required group codes. The classification score was {formatMetricValue(groupRow.final, groupRow.kind)}. The remaining measurements do not depend on that field.</p>
        </div></div>
      ) : null}
      <details className="technical-disclosure"><summary>Compare the complete recorded measurements</summary>
      <table className="mini-table">
        <caption className="sr-only">
          Q9 replay set against the final live test set, agentic desk
        </caption>
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">Q9 · {data.q9.cases} cases</th>
            <th scope="col">Final live · {data.final.cases} cases</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.metric}>
              <th scope="row">{row.label}</th>
              <td>{row.q9 === null ? "—" : formatMetricValue(row.q9, row.kind)}</td>
              <td>{row.final === null ? "—" : formatMetricValue(row.final, row.kind)}</td>
            </tr>
          ))}
        </tbody>
      </table></details>
      <p className="source-note">
        Source: results/final-live/metrics.json and the Q9 run ({data.q9_run_id}).
        The linear pipeline ran on the same cases; its numbers are in the
        comparison page.
      </p>
    </Panel>
  );
}
