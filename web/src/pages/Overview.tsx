import { useApp } from "../app/AppContext";
import { Icon } from "../components/Icon";
import { ErrorState, LoadingState } from "../components/States";
import { formatInteger, formatPercent } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { CaseDetail, ComparisonData } from "../types";

// Committed showcase example: results/runs/replay/comparison_examples.json.
const EXAMPLE_ID = "2156317";

function CasePreview({ detail }: { detail: CaseDetail }) {
  const quote = detail.proposal?.evidence.find((item) => item.verified && item.quote && detail.case.narrative.includes(item.quote));
  const test = detail.proposal?.targeted_test;
  return <article className="example-preview" aria-labelledby="example-title">
    <div className="example-preview-heading"><span>A real report</span><span>{detail.case.year} {detail.case.make} {detail.case.model}</span></div>
    <h2 id="example-title">A fault that comes and goes</h2>
    <blockquote className="report-quote">“{quote?.quote ?? detail.case.narrative}”</blockquote>
    {quote ? <p className="evidence-verified"><Icon name="check" size={14} /> Quote verified against the report</p> : null}
    <div className="test-preview">
      <span className="muted">The agent’s proposed next step</span>
      <h3>{test?.name ?? detail.proposal?.summary ?? "No test proposed"}</h3>
      <p>{test ? "Repeated wake and sleep cycles could help reproduce the intermittent fault." : "Read the case to inspect the available evidence."}</p>
    </div>
    <div className="example-preview-footer">
      <span>{detail.decision?.actor === "simulated_engineer" ? "Simulated engineer" : "Engineer"}{detail.decision ? ` · ${detail.decision.action === "approve" ? "Approved" : detail.decision.action}` : " · Awaiting review"}</span>
      <a href={`#/cases/${encodeURIComponent(detail.case.id)}`}>Read the full case <Icon name="chevron" size={14} /></a>
    </div>
  </article>;
}

function ResultSnapshot({ data }: { data: ComparisonData }) {
  const targeted = data.after.targeted_test_share;
  const grounding = data.after.quote_grounding_rate;
  return <section className="overview-evidence" aria-labelledby="snapshot-title">
    <div className="overview-section-heading"><div><h2 id="snapshot-title">Measured, with limits</h2><p>The same reports through a rule-based pipeline and an agent desk.</p></div><a href="#/compare">All results <Icon name="chevron" size={14} /></a></div>
    <dl className="evidence-strip">
      <div><dt>Reports in the comparison</dt><dd>{formatInteger(data.after.cases)}</dd><dd className="evidence-context">Public NHTSA complaint reports</dd></div>
      <div><dt>Targeted test proposals</dt><dd>{targeted ? formatPercent(targeted.value) : "—"}</dd><dd className="evidence-context">{targeted ? `Among ${formatInteger(targeted.n)} test proposals` : "No measurement available"}</dd></div>
      <div><dt>Quotes grounded in reports</dt><dd>{grounding ? formatPercent(grounding.value, 2) : "—"}</dd><dd className="evidence-context">{grounding ? `${formatInteger(grounding.n)} proposed quotes checked` : "No measurement available"}</dd></div>
    </dl>
    <div className="evaluation-note"><Icon name="issues" size={18} /><div><strong>What these results cannot prove</strong><p>Two answer fields were visible in the original run, so its component and safety scores are withheld. The later unseen test still exposed a classification failure. Decisions in the recorded comparison were made by a simulated engineer.</p><a href="#/compare">Read the evidence and limitations</a></div></div>
  </section>;
}

function Workflow() {
  return <section className="overview-method" aria-labelledby="method-title">
    <div><h2 id="method-title">Agents prepare. Engineers decide.</h2><p>A standard test can miss a fault that only appears under specific conditions. The desk reads the complaint, checks its clues against the source, and drafts a test recommendation for review.</p><p>It proposes work. It does not close a case, scrap a part, perform a physical test or accept a charge.</p><a href="#/replay">Follow the recorded workflow <Icon name="chevron" size={14} /></a></div>
    <figure className="workflow-figure">
      <svg viewBox="0 0 560 220" role="img" aria-labelledby="workflow-title workflow-desc">
        <title id="workflow-title">From report to engineer review</title>
        <desc id="workflow-desc">A complaint report enters the agent desk. It gathers verified evidence and drafts a test recommendation. An engineer approves, overrides or asks for information.</desc>
        <g className="workflow-line" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M100 75H275V145H410" /><path d="m402 139 8 6-8 6" /><path d="m267 69 8 6-8 6" /></g>
        <g id="report-node"><title>Complaint report</title><rect className="workflow-node" x="12" y="22" width="180" height="78" rx="16"/><text x="30" y="53" className="workflow-node-title">Complaint report</text><text x="30" y="78" className="workflow-node-note">What happened?</text></g>
        <g id="evidence-node"><title>Verified evidence</title><rect className="workflow-node" x="242" y="22" width="300" height="78" rx="16"/><text x="262" y="53" className="workflow-node-title">Verified evidence</text><text x="262" y="78" className="workflow-node-note">Source quotes → test proposal</text></g>
        <g id="review-node"><title>Engineer decision</title><rect className="workflow-review" x="180" y="133" width="362" height="74" rx="16"/><text x="200" y="164" className="workflow-node-title">Engineer decision</text><text x="200" y="188" className="workflow-node-note">Approve · Override · Ask for more</text></g>
      </svg>
      <figcaption>Every recommendation keeps its supporting evidence and action history.</figcaption>
    </figure>
  </section>;
}

export function OverviewPage() {
  const { source, mode } = useApp();
  const comparison = useAsync(() => source.getComparison(), `overview-results:${mode}`);
  const example = useAsync(() => source.getCase(EXAMPLE_ID), `overview-example:${mode}`);
  return <div className="overview-page">
    <section className="overview-hero" aria-labelledby="overview-title">
      <div className="overview-intro">
        <h1 id="overview-title">Field quality agents</h1>
        <p className="overview-lead">A returned part can pass a standard test and still leave the real problem unexplained.</p>
        <p>I built an agent desk that reads complaint reports, gathers evidence and proposes what to test next. Engineers keep the decision, with a trail they can inspect.</p>
        <div className="overview-actions"><a className="btn btn-primary" href={`#/cases/${EXAMPLE_ID}`}>Explore a real case <Icon name="chevron" size={16} /></a><a href="#/compare">Read the results</a></div>
        <p className="overview-context">Public NHTSA reports stand in for returned-part reports. This is a recorded demonstration, with a simulated engineer.</p>
      </div>
      {example.data ? <CasePreview detail={example.data} /> : example.error ? <ErrorState title="The example could not load" error={example.error} onRetry={example.reload} /> : <LoadingState label="Loading a recorded case" />}
    </section>
    <Workflow />
    {comparison.data ? <ResultSnapshot data={comparison.data} /> : comparison.error ? <ErrorState title="Results could not load" error={comparison.error} onRetry={comparison.reload} /> : <LoadingState label="Loading measured results" />}
    <section className="explore-project" aria-labelledby="explore-title">
      <div className="overview-section-heading"><h2 id="explore-title">Inspect the work</h2><span>Real reports, traceable decisions</span></div>
      <div className="explore-project-grid">
        <a href="#/cases"><Icon name="cases" size={20} /><div><h3>Follow a case</h3><p>Read the report, the proposed test and the evidence behind it.</p></div><Icon name="chevron" size={18} /></a>
        <a href="#/issues"><Icon name="issues" size={20} /><div><h3>Find recurring problems</h3><p>Look across reports for clusters and linked investigations.</p></div><Icon name="chevron" size={18} /></a>
        <a href="#/dashboard"><Icon name="command" size={20} /><div><h3>Open the dashboard</h3><p>Inspect the workload, model spend and recorded activity.</p></div><Icon name="chevron" size={18} /></a>
        <a href="#/report"><Icon name="report" size={20} /><div><h3>Read a weekly report</h3><p>See how the desk turns its evidence into a reviewable summary.</p></div><Icon name="chevron" size={18} /></a>
      </div>
    </section>
    <details className="implementation-details"><summary>What I built & how to inspect it</summary><div><p>The project includes a rule-based comparison pipeline, a supervisor and specialist agents, source lookup tools, quote verification, human review checkpoints, this dashboard and an offline evidence export.</p><p>Python, typed data contracts, React and TypeScript connect the recorded results to each view. The replay uses saved model responses; exploring it makes no new model calls.</p><a href="#/replay">Inspect the saved action history</a></div></details>
  </div>;
}
