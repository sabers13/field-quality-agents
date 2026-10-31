import type { TraceStep } from "../types";
import { formatDuration, formatTokens } from "../lib/format";
import { CopyButton } from "./CopyButton";
import { EmptyState } from "./States";

function compact(value: unknown): string {
  if (typeof value === "string") {
    return value.length > 60 ? `${value.slice(0, 57)}…` : value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.length}]`;
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
}

function outputSummary(output: Record<string, unknown> | null): string {
  if (!output) {
    return "";
  }
  return Object.entries(output)
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${compact(value)}`)
    .join(" · ");
}

function agentLabel(agent: string): string {
  if (agent === "human") {
    return "Human checkpoint";
  }
  return agent.charAt(0).toUpperCase() + agent.slice(1);
}

export function TraceTimeline({ steps }: { steps: readonly TraceStep[] }) {
  if (steps.length === 0) {
    return <EmptyState title="No agent steps yet">The trace appears when the desk starts work.</EmptyState>;
  }
  return (
    <ol className="trace">
      {steps.map((step) => {
        const raw = JSON.stringify(step, null, 2);
        const result = outputSummary(step.tool_output);
        return (
          <li className="trace-step" key={step.step} data-agent={step.agent}>
            <span className="trace-dot" aria-hidden="true" />
            <div className="trace-main">
              <div className="trace-top">
                <span className="trace-number">Step {step.step}</span>
                <span className="agent-badge" data-agent={step.agent}>
                  {agentLabel(step.agent)}
                </span>
                <span className="trace-metrics">
                  {step.duration_ms > 0 ? <span title="Duration">{formatDuration(step.duration_ms)}</span> : null}
                  {step.tokens > 0 ? (
                    <span title="Tokens">{formatTokens(step.tokens)} tokens</span>
                  ) : null}
                </span>
              </div>
              <p className="trace-action">{step.action}</p>
              {step.tool ? (
                <p className="tool-chip">
                  <code>
                    {step.tool}({step.tool_input ? compact(JSON.stringify(step.tool_input)) : ""})
                  </code>
                </p>
              ) : null}
              {result ? <p className="trace-result">Result: {result}</p> : null}
              {step.reason ? <p className="trace-reason">{step.reason}</p> : null}
              <details className="trace-raw">
                <summary>Raw step JSON</summary>
                <div className="raw-actions">
                  <CopyButton text={raw} label="Copy JSON" />
                </div>
                <pre>{raw}</pre>
              </details>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
