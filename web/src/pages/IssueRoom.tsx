import { useMemo } from "react";
import type { EChartsOption } from "echarts";

import { useApp } from "../app/AppContext";
import { Chart } from "../components/Chart";
import { CitationList } from "../components/Citations";
import { Icon } from "../components/Icon";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/States";
import { ToneBadge } from "../components/StatusBadge";
import { formatDate, formatDateTime, formatInteger, formatScore } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { IssueDetail, IssueSummary } from "../types";

const ISSUE_TONE = {
  open: "issue",
  monitoring: "needs_engineer",
  closed: "decided",
} as const;

const ISSUE_LABEL = {
  open: "Open",
  monitoring: "Monitoring",
  closed: "Closed",
} as const;

function IssueList({ issues, activeId }: { issues: IssueSummary[]; activeId: string | null }) {
  return (
    <aside className="issue-list" aria-label="Issues">
      <h2 className="panel-title">Issues</h2>
      {issues.length === 0 ? (
        <p className="muted">No issues opened in this window.</p>
      ) : (
        <ul>
          {issues.map((issue) => (
            <li key={issue.id}>
              <a
                className="issue-link"
                href={`#/issues/${encodeURIComponent(issue.id)}`}
                aria-current={issue.id === activeId ? "true" : undefined}
              >
                <span className="issue-link-top">
                  <code>{issue.id}</code>
                  <ToneBadge tone={ISSUE_TONE[issue.status]} label={ISSUE_LABEL[issue.status]} quiet />
                </span>
                <span className="issue-link-title">{issue.title}</span>
                <span className="issue-link-meta">
                  {issue.make} {issue.model} {issue.year} · {issue.group}
                </span>
                <span className="issue-link-meta">
                  {issue.observed} observed · {formatScore(issue.spike_ratio)}× threshold
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

function clusterOption(issue: IssueDetail, dark: boolean): EChartsOption {
  const labels = issue.weekly_counts.map((week) => week.week_start.slice(5));
  const counts = issue.weekly_counts.map((week) => week.count);
  const issueColour = dark ? "#ff8d8d" : "#a32020";
  return {
    grid: { left: 4, right: 12, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", confine: true },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLabel: { hideOverlap: true, margin: 12 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
    },
    series: [
      {
        name: "Reports",
        type: "line",
        data: counts,
        symbolSize: 5,
        lineStyle: { width: 2 },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: issueColour, type: "dashed", width: 1 },
          // The caption labels this line without crowding the plot on a phone.
          label: { show: false },
          data: [{ yAxis: issue.threshold }],
        },
      },
    ],
  };
}

function IssueTimeline({ issue }: { issue: IssueDetail }) {
  const events = [
    ...issue.linked_recall_ids.map((id) => ({ id, type: "Recall", date: null as string | null })),
    ...issue.linked_investigation_ids.map((id) => ({ id, type: "Investigation", date: null as string | null })),
  ];
  if (events.length === 0) {
    return <p className="muted">No recall or investigation is linked to this issue.</p>;
  }
  return (
    <ol className="issue-timeline">
      {events.map((event) => (
        <li key={`${event.type}-${event.id}`}>
          <span className="timeline-dot" aria-hidden="true" />
          <span className="timeline-type">{event.type}</span>
          <code>{event.id}</code>
          <span className="muted">Linked from the issue cluster</span>
        </li>
      ))}
    </ol>
  );
}

function IssueDetailView({ issue }: { issue: IssueDetail }) {
  const { resolvedTheme, mode } = useApp();
  const option = useMemo(() => clusterOption(issue, resolvedTheme === "dark"), [issue, resolvedTheme]);
  const latestCount = issue.weekly_counts.at(-1)?.count ?? 0;
  const firstWeek = issue.weekly_counts[0]?.week_start ?? issue.opened_at;
  const lastWeekStart = issue.weekly_counts.at(-1)?.week_start ?? issue.opened_at;

  return (
    <div className="issue-detail">
      <header className="issue-head">
        <div>
          <p className="eyebrow">{issue.id}</p>
          <h2>{issue.title}</h2>
          <p className="muted">
            {issue.make} {issue.model} {issue.year} · {issue.group} · opened {formatDate(issue.opened_at)}
          </p>
        </div>
        <ToneBadge tone={ISSUE_TONE[issue.status]} label={ISSUE_LABEL[issue.status]} />
      </header>

      <div className="stat-row">
        <div>
          <span className="stat-label">Observed this week</span>
          <span className="stat-value">{formatInteger(latestCount)}</span>
        </div>
        <div>
          <span className="stat-label">Threshold</span>
          <span className="stat-value">{formatScore(issue.threshold, 1)}</span>
        </div>
        <div>
          <span className="stat-label">Spike ratio</span>
          <span className="stat-value">{formatScore(issue.spike_ratio)}×</span>
        </div>
        <div>
          <span className="stat-label">Linked cases</span>
          <span className="stat-value">{formatInteger(issue.linked_case_count)}</span>
        </div>
      </div>

      <Panel title="Cluster over time">
        <Chart
          option={option}
          height={240}
          ariaLabel={`Weekly reports for ${issue.title}. The latest week observed ${latestCount} against a threshold of ${issue.threshold}.`}
          summary={
            <>
              Weekly reports, {formatDate(firstWeek)} to {formatDate(lastWeekStart)}. The dashed line is
              the Poisson 99.9% threshold ({formatScore(issue.threshold, 1)}); the latest week observed{" "}
              {latestCount}.
            </>
          }
        />
      </Panel>

      <div className="split-grid">
        <Panel title="Linked evidence">
          <h3 className="subheading">Cases</h3>
          {issue.linked_case_ids.length === 0 ? (
            <p className="muted">No case is linked yet.</p>
          ) : (
            <ul className="plain-list">
              {issue.linked_case_ids.map((id) => (
                <li key={id}>
                  <a href={`#/cases/${encodeURIComponent(id)}`}>
                    <code>{id}</code> <Icon name="chevron" size={12} />
                  </a>
                </li>
              ))}
            </ul>
          )}
          <h3 className="subheading">Recalls and investigations</h3>
          <IssueTimeline issue={issue} />
        </Panel>

        <Panel title="Decision memo">
          {issue.memo ? (
            <article className="memo">
              <p className="eyebrow">{issue.memo.id}</p>
              <h3>{issue.memo.title}</h3>
              <p>{issue.memo.body}</p>
              <p className="muted">Created {formatDateTime(issue.memo.created_at)}</p>
              <CitationList citations={issue.memo.citations} />
            </article>
          ) : (
            <EmptyState title="No memo yet">
              The report agent drafts a decision memo once the issue has a decision.
            </EmptyState>
          )}
        </Panel>
      </div>

      <Panel title="Investigation draft (8D)">
        <p className="muted">A structured problem-solving draft: the team, reported problem, proposed containment and possible causes. It still needs engineer review.</p>
        {issue.eight_d ? (
          <div className="eightd">
            <p className="muted">
              {issue.eight_d.id} · <ToneBadge tone="new" label={issue.eight_d.status} quiet /> · updated{" "}
              {formatDateTime(issue.eight_d.updated_at ?? issue.eight_d.created_at)}
            </p>
            <section>
              <h3 className="subheading">D1 · Team</h3>
              <ul className="tag-list">
                {issue.eight_d.d1_team.map((member) => (
                  <li key={member}>{member}</li>
                ))}
              </ul>
            </section>
            <section>
              <h3 className="subheading">D2 · Problem</h3>
              <p>{issue.eight_d.d2_problem}</p>
            </section>
            <section>
              <h3 className="subheading">D3 · Containment</h3>
              <p>{issue.eight_d.d3_containment}</p>
            </section>
            <section>
              <h3 className="subheading">D4 · Root cause hypotheses</h3>
              <ol className="plain-list">
                {issue.eight_d.d4_root_cause_hypotheses.map((hypothesis) => (
                  <li key={hypothesis}>{hypothesis}</li>
                ))}
              </ol>
            </section>
            <section>
              <h3 className="subheading">Citations</h3>
              <CitationList citations={issue.eight_d.citations} />
            </section>
          </div>
        ) : (
          <EmptyState title="No 8D draft yet">
            The issue agent drafts D1–D4 after a cluster is opened.
          </EmptyState>
        )}
      </Panel>

      <p className="source-note">
        {mode === "static"
          ? `Source: bundled issues.json (${issue.id}).`
          : `Source: GET /api/issues/${issue.id}.`}{" "}
        Linked ids open the case board; recall and investigation ids open their citation.
      </p>
    </div>
  );
}

export function IssueRoomPage({ issueId }: { issueId: string | undefined }) {
  const { source, mode } = useApp();
  const listState = useAsync(() => source.getIssues(), `issues:${mode}`);
  const detailState = useAsync(
    () => (issueId ? source.getIssue(issueId) : Promise.resolve(null)),
    `issue:${issueId ?? "none"}:${mode}`,
    Boolean(issueId),
  );

  if (listState.data === null) {
    return listState.status === "error" && listState.error ? (
      <ErrorState error={listState.error} onRetry={listState.reload} />
    ) : (
      <LoadingState label="Loading issues" layout="list" />
    );
  }

  return (
    <div className="page">
      <p className="lede">
        Do several reports point to the same problem? Open a cluster to inspect the report counts,
        linked evidence and a draft investigation summary.
      </p>
      <div className={issueId ? "issues-layout" : "issues-overview"} data-detail={issueId ? "true" : "false"}>
        <IssueList issues={listState.data} activeId={issueId ?? null} />
        {issueId ? <div className="issue-detail-pane">
          {issueId ? (
            <a className="back-link" href="#/issues">
              <Icon name="chevron" size={12} /> All issues
            </a>
          ) : null}
          {!issueId ? (
            <EmptyState title="Select an issue">
              The cluster chart, linked evidence and 8D draft open here. {listState.data.length} issue
              {listState.data.length === 1 ? "" : "s"} in this window.
            </EmptyState>
          ) : detailState.data === null ? (
            detailState.status === "error" && detailState.error ? (
              <ErrorState error={detailState.error} onRetry={detailState.reload} />
            ) : (
              <LoadingState label="Loading issue" />
            )
          ) : (
            <IssueDetailView issue={detailState.data} />
          )}
        </div> : null}
      </div>
    </div>
  );
}
