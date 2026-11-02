import { useEffect, useMemo, useState } from "react";

import { useApp } from "../app/AppContext";
import { CitationList } from "../components/Citations";
import { DecisionPanel } from "../components/DecisionPanel";
import { Icon } from "../components/Icon";
import { Narrative } from "../components/Narrative";
import { Sheet } from "../components/Overlay";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { StatusBadge, ToneBadge } from "../components/StatusBadge";
import { TraceTimeline } from "../components/TraceTimeline";
import {
  formatDate,
  formatDateTime,
  formatInteger,
  formatRelative,
  formatScore,
} from "../lib/format";
import { BOARD_COLUMNS, statusTone, type CaseStatus } from "../lib/status";
import { useAsync } from "../lib/useAsync";
import type { CaseDetail, CaseListItem, ProposalKind } from "../types";

const PROPOSAL_LABELS: Record<ProposalKind, string> = {
  standard_test: "Standard test",
  targeted_load_test: "Targeted load test",
  safety_priority: "Safety priority",
  evidence_pack: "Evidence pack",
  request_info: "Request info",
};

function readOnlyReason(mode: string): string | null {
  if (mode === "static") {
    return "Static export: this page is read-only; decisions come from the recorded run.";
  }
  if (mode === "replay") {
    return "Replay mode: decisions come from the recorded run and are read-only.";
  }
  return null;
}

function CaseCard({ item }: { item: CaseListItem }) {
  return (
    <a
      className="case-card"
      href={`#/cases/${encodeURIComponent(item.id)}`}
      data-tone={statusTone(item.status)}
      aria-label={`Open case ${item.id}: ${item.component}, ${item.make} ${item.model} ${item.year}, ${item.status.replaceAll("_", " ")}`}
    >
      <span className="case-card-top">
        <span className="case-id">{item.id}</span>
        <StatusBadge status={item.status} />
      </span>
      <span className="case-card-title">{item.component}</span>
      <span className="case-card-meta">
        {item.make} {item.model} {item.year}
        {item.group ? ` · ${item.group}` : ""}
      </span>
      <span className="case-card-foot">
        {item.safety_relevant ? (
          <span className="flag-safety">
            <Icon name="shield" size={12} /> Safety
          </span>
        ) : null}
        <span>{item.evidence_count} evidence</span>
        <span>{item.human_touches} human</span>
        <time dateTime={item.received_at} title={formatDate(item.received_at)}>
          {formatRelative(item.received_at)}
        </time>
      </span>
    </a>
  );
}

function CaseRegister({ items }: { items: CaseListItem[] }) {
  if (items.length === 0) return <EmptyState title="No matching reports">Try another search or clear the filters.</EmptyState>;
  return <div className="case-register">
    <div className="case-register-head" aria-hidden="true"><span>Report</span><span>Component & evidence</span><span>Review status</span><span /></div>
    <ul className="case-register-list" aria-label="Complaint reports">
      {items.map((item) => <li key={item.id}><a className="case-register-row" href={`#/cases/${encodeURIComponent(item.id)}`}
        aria-label={`Open case ${item.id}: ${item.make} ${item.model}, ${item.component}`}>
        <span><strong>{item.make} {item.model} {item.year}</strong><small>Report {item.id} · {formatDate(item.received_at)}</small></span>
        <span><span className="case-register-component">{item.component}</span><small>{item.evidence_count} evidence · {item.human_touches} human {item.human_touches === 1 ? "touch" : "touches"}</small></span>
        <span><StatusBadge status={item.status} />{item.safety_relevant ? <small className="flag-safety"><Icon name="shield" size={12} /> Safety flagged</small> : null}</span>
        <Icon name="chevron" size={16} />
      </a></li>)}
    </ul>
  </div>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="detail-section">
      <h3 className="subheading">{title}</h3>
      {children}
    </section>
  );
}

function ProposalView({ detail }: { detail: CaseDetail }) {
  const proposal = detail.proposal;
  if (!proposal) {
    return (
      <Section title="Proposal">
        <EmptyState title="No proposal yet">The desk is still gathering evidence for this case.</EmptyState>
      </Section>
    );
  }
  return (
    <Section title="Proposal">
      <div className="proposal">
        <div className="proposal-head">
          <ToneBadge tone="in_agent" label={PROPOSAL_LABELS[proposal.kind]} />
          <span className="muted">Drafted {formatDateTime(proposal.created_at)}</span>
        </div>
        <h4>{proposal.summary}</h4>
        <p>{proposal.rationale}</p>
        {proposal.targeted_test ? (
          <div className="test-card">
            <p className="test-name">
              <Icon name="spark" size={14} /> {proposal.targeted_test.name}
            </p>
            {proposal.targeted_test.conditions.length > 0 ? (
              <ul className="tag-list">
                {proposal.targeted_test.conditions.map((condition) => (
                  <li key={condition}>{condition}</li>
                ))}
              </ul>
            ) : null}
            {proposal.targeted_test.reason ? <p>{proposal.targeted_test.reason}</p> : null}
          </div>
        ) : null}
        {proposal.requested_info.length > 0 ? (
          <div>
            <h4>Information requested</h4>
            <ul className="plain-list">
              {proposal.requested_info.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <h4>Evidence</h4>
        <CitationList citations={proposal.evidence} />
      </div>
    </Section>
  );
}

function SimilarCases({ detail }: { detail: CaseDetail }) {
  return (
    <Section title="Similar cases">
      {detail.similar_cases.length === 0 ? (
        <p className="muted">No similar case was found in the knowledge base.</p>
      ) : (
        <ul className="similar-list">
          {detail.similar_cases.map((similar) => (
            <li key={similar.id}>
              <a href={`#/cases/${encodeURIComponent(similar.id)}`} className="similar-link">
                <span className="similar-head">
                  <code>{similar.id}</code>
                  <span className="score">{formatScore(similar.score, 4)}</span>
                </span>
                <span className="similar-meta">
                  {similar.make} {similar.model} {similar.year} · {similar.group}
                </span>
                <span className="similar-excerpt">{similar.excerpt}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function LinkedSources({ detail }: { detail: CaseDetail }) {
  const hasAny = detail.recalls.length > 0 || detail.investigations.length > 0;
  return (
    <Section title="Linked recalls and investigations">
      {!hasAny ? <p className="muted">No recall or investigation matched this case.</p> : null}
      {detail.recalls.length > 0 ? (
        <ul className="link-list">
          {detail.recalls.map((recall) => (
            <li key={recall.id}>
              <span className="link-row">
                <code>{recall.id}</code>
                <ToneBadge tone={recall.match ? "issue" : "new"} label={recall.match ? "Match" : "No match"} />
                <time dateTime={recall.open_date}>{formatDate(recall.open_date)}</time>
              </span>
              <span>{recall.summary}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {detail.investigations.length > 0 ? (
        <ul className="link-list">
          {detail.investigations.map((investigation) => (
            <li key={investigation.id}>
              <span className="link-row">
                <code>{investigation.id}</code>
                <ToneBadge
                  tone={investigation.match ? "needs_engineer" : "new"}
                  label={investigation.match ? "Match" : "No match"}
                />
                <time dateTime={investigation.open_date}>{formatDate(investigation.open_date)}</time>
              </span>
              <span>{investigation.summary}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </Section>
  );
}

export function CaseDetailView({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const { source, mode, decisionClient, streamEvents } = useApp();
  const state = useAsync(() => source.getCase(caseId), `case:${caseId}:${mode}`);

  const detail = state.data;
  const liveTrace = useMemo(() => {
    if (!detail) {
      return [];
    }
    const extra = streamEvents
      .filter((event) => event.kind === "trace" && event.data.case_id === caseId)
      .map((event) => event.data.step)
      .filter((step): step is NonNullable<typeof step> => Boolean(step))
      .map((step) => step as unknown as CaseDetail["trace"][number]);
    return [...detail.trace, ...extra];
  }, [detail, streamEvents, caseId]);

  return (
    <Sheet
      title={caseId}
      subtitle={detail ? `${detail.case.make} ${detail.case.model} ${detail.case.year} · ${detail.case.component}` : "Case detail"}
      onClose={onClose}
      size="wide"
    >
      {!detail ? (
        state.status === "error" && state.error ? (
          <ErrorState error={state.error} onRetry={state.reload} />
        ) : (
          <LoadingState label="Loading case" layout="case" />
        )
      ) : (
        <div className="case-detail">
          {state.status === "error" && state.error ? (
            <p className="inline-warning" role="alert">
              Refresh failed: {state.error.message}
            </p>
          ) : null}

          <div className="detail-topline">
            <StatusBadge status={detail.case.status} />
            {detail.case.safety_relevant ? (
              <ToneBadge tone="issue" label="Safety" />
            ) : (
              <ToneBadge tone="new" label="Not safety-flagged" quiet />
            )}
            <span className="muted">
              Received {formatDate(detail.case.received_at)} · {formatInteger(detail.case.mileage ?? 0)} mi ·{" "}
              {detail.case.source.toUpperCase()} {detail.case.source_id ?? ""}
            </span>
          </div>

          <Narrative detail={detail} />

          <ProposalView detail={detail} />

          <DecisionPanel
            detail={{ ...detail, trace: liveTrace }}
            decisionClient={decisionClient}
            readOnlyReason={readOnlyReason(mode)}
            onDecided={state.reload}
          />

          <details className="case-disclosure"><summary>Agent trace · inspect the action history</summary>
            <Section title="Agent trace"><TraceTimeline steps={liveTrace} /></Section>
          </details>

          {detail.extraction ? (
            <details className="case-disclosure"><summary>Extracted symptoms & conditions</summary><Section title="Extraction">
              <dl className="meta-grid">
                <div>
                  <dt>Group</dt>
                  <dd>{detail.extraction.group}</dd>
                </div>
                <div>
                  <dt>Safety</dt>
                  <dd>{detail.extraction.safety_relevant ? "Flagged" : "Not flagged"}</dd>
                </div>
                <div>
                  <dt>Symptoms</dt>
                  <dd>{detail.extraction.symptoms.join("; ") || "—"}</dd>
                </div>
                <div>
                  <dt>Conditions</dt>
                  <dd>{detail.extraction.conditions.join("; ") || "—"}</dd>
                </div>
              </dl>
              <p>{detail.extraction.summary}</p>
            </Section></details>
          ) : null}
          <details className="case-disclosure"><summary>Related reports & linked sources</summary>
            <SimilarCases detail={detail} /><LinkedSources detail={detail} />
          </details>
        </div>
      )}
    </Sheet>
  );
}

export function CaseBoardPage() {
  const { source, mode } = useApp();
  const [view, setView] = useState<"list" | "board">("list");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [safetyOnly, setSafetyOnly] = useState(false);
  const [group, setGroup] = useState("");
  const [mobileColumn, setMobileColumn] = useState<CaseStatus | "all">("all");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(search.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  const query = {
    limit: view === "list" ? 25 : 200,
    offset,
    ...(mobileColumn !== "all" ? { status: mobileColumn } : {}),
    ...(debounced ? { q: debounced } : {}),
    ...(safetyOnly ? { safety: true } : {}),
    ...(group ? { group } : {}),
  };
  const key = `cases:${mode}:${debounced}:${safetyOnly}:${group}:${view}:${offset}:${mobileColumn}`;
  const state = useAsync(() => source.getCases(query), key);

  const items = state.data?.items ?? [];
  const groups = [...new Set(items.map((item) => item.group).filter((value): value is string => Boolean(value)))].sort();
  const visibleColumns = mobileColumn === "all" ? BOARD_COLUMNS : BOARD_COLUMNS.filter((column) => column.id === mobileColumn);

  return (
    <div className="page">
      <p className="lede">
        Read complaint reports, proposed tests and recorded decisions. Open a report to inspect its evidence.
      </p>

      <div className="board-controls">
        <label className="field-inline" htmlFor="case-search">
          <span>Search</span>
          <input
            id="case-search"
            className="input"
            type="search"
            value={search}
            placeholder="Case, make or component…"
            name="case-search" autoComplete="off"
            onChange={(event) => { setSearch(event.target.value); setOffset(0); }}
          />
        </label>
        <details className="case-extra-filters"><summary>Filters</summary><div className="case-extra-filters-panel">
        <label className="field-inline" htmlFor="case-group">
          <span>Group</span>
          <select id="case-group" className="input" value={group} onChange={(event) => { setGroup(event.target.value); setOffset(0); }}>
            <option value="">All groups</option>
            {groups.map((value) => (
              <option value={value} key={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={safetyOnly} onChange={(event) => { setSafetyOnly(event.target.checked); setOffset(0); }} />
          Safety only
        </label>
        </div></details>
      </div>

      <div className="case-results-heading">
        <p role="status">{state.data ? `${formatInteger(state.data.total)} reports match · showing ${items.length === 0 ? 0 : offset + 1}–${offset + items.length}` : "Finding reports…"}</p>
        <div className="view-switch" role="group" aria-label="Case view">
          <button type="button" aria-pressed={view === "list"} onClick={() => { setView("list"); setOffset(0); }}>List</button>
          <button type="button" aria-pressed={view === "board"} onClick={() => { setView("board"); setOffset(0); }}>Board</button>
        </div>
      </div>
      <div className="board-filter" role="group" aria-label="Filter board by status">
        <button
          type="button"
          className="chip"
          aria-pressed={mobileColumn === "all"}
          onClick={() => { setMobileColumn("all"); setOffset(0); }}
        >
          All
        </button>
        {BOARD_COLUMNS.map((column) => (
          <button
            type="button"
            className="chip"
            key={column.id}
            aria-pressed={mobileColumn === column.id}
            onClick={() => { setMobileColumn(column.id); setOffset(0); }}
          >
            {column.header}
          </button>
        ))}
      </div>

      {state.data === null && state.status === "error" && state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} />
      ) : state.data === null ? (
        <LoadingState label="Loading cases" layout="list" />
      ) : view === "list" ? <CaseRegister items={items} /> : (
        <div className="board" aria-label="Case board">
          {visibleColumns.map((column) => {
            const columnItems = items.filter((item) => column.statuses.includes(item.status));
            return (
              <section className="board-column" data-tone={column.tone} key={column.id}>
                <header className="board-column-head">
                  <h2>
                    <span className="status-dot" data-tone={column.tone} aria-hidden="true" />
                    {column.header}
                  </h2>
                  <span className="count">{columnItems.length}</span>
                </header>
                <div className="board-column-body">
                  {columnItems.length === 0 ? (
                    <p className="column-empty">No cases</p>
                  ) : (
                    columnItems.map((item) => <CaseCard item={item} key={item.id} />)
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {state.data && state.data.total > state.data.limit ? <nav className="case-pagination" aria-label="Report pages">
        <button type="button" className="btn btn-secondary" disabled={offset === 0 || state.status === "refreshing"}
          onClick={() => setOffset(Math.max(0, offset - state.data!.limit))}>Previous</button>
        <span>{formatInteger(offset + 1)}–{formatInteger(offset + items.length)} of {formatInteger(state.data.total)}</span>
        <button type="button" className="btn btn-secondary" disabled={offset + items.length >= state.data.total || state.status === "refreshing"}
          onClick={() => setOffset(offset + state.data!.limit)}>Next reports</button>
      </nav> : null}
      <p className="source-note">
        {mode === "static" ? "Source: bundled cases.json." : "Source: GET /api/cases."}
        {state.data ? ` ${state.data.total} cases match.` : ""}
      </p>
    </div>
  );
}
