import type { Kpi } from "../types";
import { formatInteger } from "../lib/format";
import { Icon } from "./Icon";
import { Sparkline } from "./Sparkline";

const PERCENT_IDS = new Set(["prepared_without_edits", "ntf_without_evidence"]);
const INTEGER_IDS = new Set(["cases_in", "open_issues"]);

export function formatKpiValue(kpi: Kpi): string {
  if (typeof kpi.value === "string") {
    return kpi.value;
  }
  if (INTEGER_IDS.has(kpi.id)) {
    return formatInteger(kpi.value);
  }
  if (PERCENT_IDS.has(kpi.id)) {
    return `${kpi.value.toFixed(1)}%`;
  }
  if (kpi.id === "cost_per_case") {
    return `$${kpi.value.toFixed(4)}`;
  }
  if (kpi.id === "time_to_decision") {
    return kpi.value.toFixed(1);
  }
  return kpi.value.toFixed(1);
}

function formatDelta(kpi: Kpi, delta: number): string {
  const absolute = Math.abs(delta);
  if (PERCENT_IDS.has(kpi.id)) {
    return `${absolute.toFixed(1)} pts`;
  }
  if (kpi.id === "cost_per_case") {
    return `$${absolute.toFixed(4)}`;
  }
  if (kpi.id === "time_to_decision") {
    return `${absolute.toFixed(1)} h`;
  }
  if (Number.isInteger(absolute)) {
    return formatInteger(absolute);
  }
  return absolute.toFixed(1);
}

export function KpiTile({ kpi }: { kpi: Kpi }) {
  const tone = kpi.tone ?? "neutral";
  const hasDelta = typeof kpi.delta === "number" && kpi.delta !== 0;
  const delta = kpi.delta ?? 0;
  const direction = delta > 0 ? "up" : "down";
  return (
    <article className="kpi" data-tone={tone}>
      <div className="kpi-label">{kpi.label}</div>
      <div className="kpi-value">
        {formatKpiValue(kpi)}
        {kpi.unit && !["%", "cases", "issues", "USD", "h"].includes(kpi.unit) ? (
          <span className="kpi-unit">{kpi.unit}</span>
        ) : null}
      </div>
      <div className="kpi-context">{kpi.context}</div>
      <div className="kpi-foot">
        {hasDelta ? (
          <span className="kpi-delta" data-tone={tone}>
            <Icon name={direction === "up" ? "arrow-up" : "arrow-down"} size={12} />
            <span className="sr-only">{direction === "up" ? "Up" : "Down"} </span>
            {formatDelta(kpi, delta)}
          </span>
        ) : (
          <span className="kpi-delta is-flat">No change</span>
        )}
        {kpi.series ? <Sparkline series={kpi.series} /> : null}
      </div>
    </article>
  );
}
