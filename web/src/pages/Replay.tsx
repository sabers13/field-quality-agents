import { useEffect, useMemo, useState } from "react";

import { useApp } from "../app/AppContext";
import { Icon } from "../components/Icon";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/States";
import { StatusBadge, ToneBadge } from "../components/StatusBadge";
import { formatDate, formatDateTime } from "../lib/format";
import { groupReplayByDay, replayEventText, summariseReplay } from "../lib/replay";
import { useAsync } from "../lib/useAsync";
import type { ReplayEvent } from "../types";

const SPEEDS = [0.5, 1, 2, 4] as const;
const BASE_INTERVAL_MS = 900;

function EventList({ events }: { events: ReplayEvent[] }) {
  const days = groupReplayByDay(events);
  return (
    <div className="replay-days">
      {days.map((day) => (
        <section className="replay-day" key={day.day}>
          <h3 className="subheading">{formatDate(day.day)}</h3>
          <ol className="replay-events">
            {day.events.map((event) => (
              <li className="replay-event" data-kind={event.kind} key={event.seq}>
                <span className="replay-seq">#{event.seq}</span>
                <ToneBadge
                  tone={
                    event.kind === "issue"
                      ? "issue"
                      : event.kind === "decision"
                        ? "decided"
                        : event.kind === "report"
                          ? "needs_engineer"
                          : "in_agent"
                  }
                  label={event.kind}
                  quiet
                />
                <span className="replay-text">{replayEventText(event)}</span>
                <time dateTime={event.at} title={formatDateTime(event.at)}>
                  {event.at.slice(11, 16)} UTC
                </time>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

export function ReplayPage() {
  const { source, mode } = useApp();
  const runsState = useAsync(() => source.getReplayRuns(), `replay-runs:${mode}`);
  const [runId, setRunId] = useState<string | null>(null);
  const [position, setPosition] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);

  const runs = runsState.data ?? [];
  const activeRun = runs.find((run) => run.run_id === runId) ?? runs[0] ?? null;
  const activeRunId = activeRun?.run_id ?? null;

  const eventsState = useAsync(
    () => {
      if (!activeRunId || !source.getReplayEvents) {
        return Promise.resolve([]);
      }
      return source.getReplayEvents(activeRunId);
    },
    `replay-events:${activeRunId ?? "none"}:${mode}`,
    activeRunId !== null,
  );
  const events = eventsState.data ?? [];

  useEffect(() => {
    setPosition(0);
    setPlaying(false);
  }, [activeRunId]);

  useEffect(() => {
    if (!playing) {
      return;
    }
    if (position >= events.length) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => {
      setPosition((value) => Math.min(value + 1, events.length));
    }, BASE_INTERVAL_MS / speed);
    return () => window.clearTimeout(timer);
  }, [playing, position, speed, events.length]);

  const summary = useMemo(() => summariseReplay(events, position), [events, position]);
  const current = position > 0 ? events[position - 1] : null;
  const next = position < events.length ? events[position] : null;
  const progress = events.length === 0 ? 0 : Math.round((position / events.length) * 100);

  if (runsState.data === null) {
    return runsState.status === "error" && runsState.error ? (
      <ErrorState error={runsState.error} onRetry={runsState.reload} />
    ) : (
      <LoadingState label="Loading replay runs" />
    );
  }

  return (
    <div className="page">
      <p className="lede">
        A recorded run, played day by day: cases arrive, agents act and humans decide. No model
        calls happen during replay.
      </p>

      {runs.length === 0 ? (
        <EmptyState title="No recorded run yet">
          Run <code>make run-replay</code> to write a replay set, then open this page.
        </EmptyState>
      ) : (
        <>
          <div className="replay-toolbar">
            <div className="replay-meta">
              {runs.length > 1 ? (
                <label className="field-inline" htmlFor="replay-run">
                  <span>Run</span>
                  <select
                    id="replay-run"
                    className="input"
                    value={activeRunId ?? ""}
                    onChange={(event) => setRunId(event.target.value)}
                  >
                    {runs.map((run) => (
                      <option value={run.run_id} key={run.run_id}>
                        {run.run_id}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div>
                  <p className="eyebrow">{activeRun?.run_id}</p>
                  <p className="muted">
                    {activeRun?.set_name} · {activeRun?.case_count} cases · started{" "}
                    {activeRun ? formatDateTime(activeRun.started_at) : ""} · {activeRun?.status}
                  </p>
                </div>
              )}
              <ToneBadge
                tone={activeRun?.status === "complete" ? "decided" : "needs_engineer"}
                label={activeRun?.status ?? "unknown"}
              />
            </div>

            <div className="replay-controls" role="group" aria-label="Replay controls">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  if (position >= events.length) {
                    setPosition(0);
                  }
                  setPlaying((value) => !value);
                }}
                aria-label={playing ? "Pause replay" : "Play replay"}
              >
                <Icon name={playing ? "pause" : "play"} size={14} />
                {playing ? "Pause" : position >= events.length ? "Play again" : "Play"}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setPlaying(false);
                  setPosition(0);
                }}
              >
                <Icon name="restart" size={14} /> Restart
              </button>
              <label className="field-inline" htmlFor="replay-speed">
                <span>Speed</span>
                <select
                  id="replay-speed"
                  className="input"
                  value={speed}
                  onChange={(event) => setSpeed(Number(event.target.value) as (typeof SPEEDS)[number])}
                >
                  {SPEEDS.map((value) => (
                    <option value={value} key={value}>
                      {value}×
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="replay-scrubber">
            <label htmlFor="replay-position">
              Position: {position} of {events.length} events
            </label>
            <input
              id="replay-position"
              type="range"
              min={0}
              max={events.length}
              value={position}
              onChange={(event) => {
                setPlaying(false);
                setPosition(Number(event.target.value));
              }}
            />
            <div className="progress-track" aria-hidden="true">
              <span style={{ width: `${progress}%` }} />
            </div>
            <p className="muted" role="status" aria-live="polite">
              {current
                ? `Now: ${replayEventText(current)}`
                : next
                  ? `Next: ${replayEventText(next)}`
                  : "At the end of the run."}
            </p>
          </div>

          <div className="replay-grid">
            <Panel title="Cases on the board">
              {summary.cases.length === 0 ? (
                <EmptyState title="No cases yet">Press play to bring the first case in.</EmptyState>
              ) : (
                <ul className="replay-case-list">
                  {summary.cases.map((item) => (
                    <li key={item.caseId}>
                      <a href={`#/cases/${encodeURIComponent(item.caseId)}`} className="replay-case">
                        <code>{item.caseId}</code>
                        {item.status ? <StatusBadge status={item.status} /> : <ToneBadge tone="new" label="Arrived" quiet />}
                        <span className="replay-case-summary">{item.lastSummary}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
              <p className="replay-counts">
                {summary.counts.case} cases · {summary.counts.trace} agent steps · {summary.counts.decision} decisions ·{" "}
                {summary.counts.issue} issues · {summary.counts.report} reports
              </p>
            </Panel>

            <Panel title="Events">
              {position === 0 ? (
                <EmptyState title="Ready to play">The recorded events appear here in order.</EmptyState>
              ) : (
                <EventList events={events.slice(0, position)} />
              )}
            </Panel>
          </div>

          {!source.getReplayEvents ? (
            <p className="inline-warning" role="note">
              This data source does not expose recorded events.
            </p>
          ) : null}
          <p className="source-note">
            {mode === "static" ? "Source: bundled replay.json." : "Source: GET /api/replay/runs."}
          </p>
        </>
      )}
    </div>
  );
}
