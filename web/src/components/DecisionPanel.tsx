import { useId, useState } from "react";

import type { DecisionClient } from "../data/source";
import { formatDateTime } from "../lib/format";
import type { CaseDetail, DecisionAction, Proposal } from "../types";
import { Icon } from "./Icon";
import { Modal } from "./Overlay";
import { ToneBadge } from "./StatusBadge";

const ACTION_LABELS: Record<DecisionAction, string> = {
  approve: "Approve",
  override: "Override",
  ask: "Ask",
  request_info: "Request info",
};

function actorLabel(actor: "simulated_engineer" | "live_engineer"): string {
  return actor === "simulated_engineer" ? "Simulated engineer" : "Engineer";
}

interface DecisionPanelProps {
  detail: CaseDetail;
  decisionClient: DecisionClient | null;
  readOnlyReason: string | null;
  onDecided: () => void;
}

export function DecisionPanel({ detail, decisionClient, readOnlyReason, onDecided }: DecisionPanelProps) {
  const [open, setOpen] = useState<DecisionAction | null>(null);
  const [rationale, setRationale] = useState("");
  const [editedSummary, setEditedSummary] = useState(detail.proposal?.summary ?? "");
  const [editedTest, setEditedTest] = useState(detail.proposal?.targeted_test?.name ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const rationaleId = useId();
  const summaryId = useId();
  const testId = useId();

  const proposal = detail.proposal;
  const decision = detail.decision;
  const canAct =
    decisionClient !== null &&
    readOnlyReason === null &&
    proposal !== null &&
    detail.case.status === "needs_engineer";

  const openDialog = (action: DecisionAction) => {
    setRationale("");
    setEditedSummary(proposal?.summary ?? "");
    setEditedTest(proposal?.targeted_test?.name ?? "");
    setError(null);
    setDone(null);
    setOpen(action);
  };

  const closeDialog = () => {
    if (!pending) {
      setOpen(null);
    }
  };

  const submit = async (action: DecisionAction) => {
    if (!decisionClient) {
      return;
    }
    setPending(true);
    setError(null);
    let editedProposal: Proposal | null = null;
    if (action === "override" && proposal) {
      editedProposal = {
        ...proposal,
        summary: editedSummary.trim() || proposal.summary,
        targeted_test:
          proposal.targeted_test && editedTest.trim()
            ? { ...proposal.targeted_test, name: editedTest.trim() }
            : proposal.targeted_test,
      };
    }
    try {
      await decisionClient.submitDecision(detail.case.id, {
        action,
        rationale: rationale.trim(),
        edited_proposal: editedProposal,
      });
      setDone(`Decision recorded: ${ACTION_LABELS[action].toLowerCase()}.`);
      setOpen(null);
      onDecided();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="decision-panel" aria-labelledby="decision-heading">
      <div className="decision-head">
        <h3 id="decision-heading" className="subheading">
          Human decision
        </h3>
        {decision ? <ToneBadge tone={decision.action === "approve" ? "decided" : "needs_engineer"} label={ACTION_LABELS[decision.action]} /> : null}
      </div>

      {decision ? (
        <div className="decision-record">
          <p>
            <strong>{ACTION_LABELS[decision.action]}</strong> by {actorLabel(decision.actor)} on{" "}
            {formatDateTime(decision.decided_at)}
          </p>
          {decision.rationale ? <p>{decision.rationale}</p> : null}
          {decision.edited_proposal ? (
            <p className="decision-edit">
              Edited proposal: {decision.edited_proposal.summary}
              {decision.edited_proposal.targeted_test
                ? ` · ${decision.edited_proposal.targeted_test.name}`
                : ""}
            </p>
          ) : null}
        </div>
      ) : null}

      {done ? (
        <p className="form-success" role="status">
          <Icon name="check" size={14} /> {done}
        </p>
      ) : null}

      {canAct && !decision ? (
        <>
          <p className="decision-hint">
            {proposal.kind === "safety_priority"
              ? "Safety case: a person decides before the desk continues."
              : "The agent drafts; the engineer decides. Approve, override or ask for more."}
          </p>
          <div className="decision-actions">
            <button type="button" className="btn btn-primary" onClick={() => openDialog("approve")}>
              Approve
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => openDialog("override")}>
              Override
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => openDialog("ask")}>
              Ask
            </button>
          </div>
        </>
      ) : null}

      {readOnlyReason ? (
        <p className="read-only-note" role="note">
          {readOnlyReason}
        </p>
      ) : null}

      {!decision && !readOnlyReason && !canAct ? (
        <p className="read-only-note" role="note">
          {proposal
            ? "This case is not waiting for a decision."
            : "No proposal is ready yet; the desk is still working."}
        </p>
      ) : null}

      {open ? (
        <Modal
          title={`${ACTION_LABELS[open]} proposal`}
          subtitle={detail.case.id}
          onClose={closeDialog}
          footer={
            <>
              <button type="button" className="btn btn-secondary" onClick={closeDialog} disabled={pending}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void submit(open)}
                disabled={pending || (open !== "approve" && rationale.trim().length === 0)}
              >
                {pending ? "Recording…" : `${ACTION_LABELS[open]} decision`}
              </button>
            </>
          }
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submit(open);
            }}
          >
            {open === "override" && proposal ? (
              <>
                <label className="field" htmlFor={summaryId}>
                  Proposal summary
                </label>
                <textarea
                  id={summaryId}
                  className="input"
                  rows={2}
                  value={editedSummary}
                  onChange={(event) => setEditedSummary(event.target.value)}
                />
                {proposal.targeted_test ? (
                  <>
                    <label className="field" htmlFor={testId}>
                      Test name
                    </label>
                    <input
                      id={testId}
                      className="input"
                      value={editedTest}
                      onChange={(event) => setEditedTest(event.target.value)}
                    />
                  </>
                ) : null}
              </>
            ) : null}

            <label className="field" htmlFor={rationaleId}>
              Reason {open === "approve" ? "(optional)" : "(required)"}
            </label>
            <textarea
              id={rationaleId}
              className="input"
              rows={3}
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
              required={open !== "approve"}
            />
            <p className="field-note">
              {open === "approve"
                ? "The rationale is written into the trace."
                : open === "override"
                  ? "The edited proposal is recorded with the decision."
                  : "The case stays with the engineer while the question is open."}
            </p>
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            <button type="submit" hidden aria-hidden="true" tabIndex={-1}>
              Submit
            </button>
          </form>
        </Modal>
      ) : null}
    </section>
  );
}
