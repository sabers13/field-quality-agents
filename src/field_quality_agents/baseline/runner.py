"""Run the linear baseline on the committed replay set and write results.

``fqa baseline`` calls :func:`run_baseline`. The output is deterministic: JSON
keys are sorted, cases keep a stable order, and there is no timestamp. Running
the command twice over the same parquet files writes byte-identical files.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from field_quality_agents.baseline.keywords import KeywordRules, load_keywords
from field_quality_agents.baseline.pipeline import (
    BaselineDecision,
    baseline_runs,
    run_linear,
)
from field_quality_agents.baseline.tfidf import fit_tfidf_logreg
from field_quality_agents.contracts import (
    Case,
    MetricEstimate,
    Metrics,
    Proposal,
    ProposalKind,
)
from field_quality_agents.metrics import (
    group_coverage,
    macro_f1,
    safety_scores,
    targeted_test_share,
    targeted_test_with_quote_share,
    workload,
)

__all__ = ["BaselineReport", "load_cases", "run_baseline"]

#: PLAN §5's replay seed, reused for the bootstrap and the reference fit.
DEFAULT_SEED = 20261031


@dataclass(frozen=True)
class BaselineReport:
    """Where the results went and the numbers the CLI prints."""

    out_dir: Path
    cases: int
    macro_f1: MetricEstimate
    coverage: MetricEstimate
    safety_precision: MetricEstimate
    safety_recall: MetricEstimate
    priority: int
    standard_test: int
    no_trouble_found: int
    tfidf_macro_f1: MetricEstimate


def load_cases(path: str | Path) -> list[Case]:
    """Read one committed case parquet into contract ``Case`` objects."""

    connection = duckdb.connect(":memory:")
    connection.execute("SET threads = 1")
    try:
        rows = connection.execute(
            """
            SELECT id, received_at, make, model, year, component,
                   "group" AS group_name, narrative, safety_relevant, mileage
            FROM read_parquet(?)
            ORDER BY received_at, id
            """,
            [str(path)],
        ).fetchall()
    finally:
        connection.close()

    cases: list[Case] = []
    for (
        case_id,
        received_at,
        make,
        model,
        year,
        component,
        group_name,
        narrative,
        safety_relevant,
        mileage,
    ) in rows:
        cases.append(
            Case(
                id=str(case_id),
                received_at=received_at,
                make=str(make),
                model=str(model),
                year=int(year),
                component=str(component),
                narrative=str(narrative),
                group=str(group_name) if group_name is not None else None,
                safety_relevant=bool(safety_relevant),
                mileage=int(mileage) if mileage is not None else None,
            )
        )
    return cases


def _write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _decision_payload(decision: BaselineDecision) -> dict[str, object]:
    return {
        "case_id": decision.case_id,
        "group": decision.group,
        "safety_relevant": decision.safety_relevant,
        "route": decision.route,
        "closed_no_trouble_found": decision.closed_no_trouble_found,
        "keywords": list(decision.keywords),
    }


def _baseline_proposals(
    cases: Sequence[Case],
    decisions: Sequence[BaselineDecision],
) -> tuple[Proposal, ...]:
    """Represent the fixed route as a proposal per case for the shared metric."""

    by_id = {decision.case_id: decision for decision in decisions}
    proposals: list[Proposal] = []
    for case in cases:
        decision = by_id.get(case.id)
        if decision is None:
            continue
        kind = (
            ProposalKind.SAFETY_PRIORITY
            if decision.route == "priority"
            else ProposalKind.STANDARD_TEST
        )
        proposals.append(
            Proposal(
                case_id=case.id,
                kind=kind,
                summary=(
                    "Safety priority: route to an engineer before any test."
                    if kind is ProposalKind.SAFETY_PRIORITY
                    else "Standard test; the simulation always passes."
                ),
                created_at=datetime.combine(case.received_at, datetime.min.time(), tzinfo=UTC),
            )
        )
    return tuple(proposals)


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _metric_row(label: str, estimate_value: MetricEstimate | None, *, digits: int = 4) -> str:
    if estimate_value is None:
        return f"| {label} | n/a | n/a | 0 |"
    if estimate_value.ci_low is None or estimate_value.ci_high is None:
        interval = "n/a"
    else:
        interval = f"[{estimate_value.ci_low:.{digits}f}, {estimate_value.ci_high:.{digits}f}]"
    return (
        f"| {label} | {estimate_value.value:.{digits}f} | {interval} | "
        f"{estimate_value.n} |"
    )


def _top_confusions(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    limit: int = 5,
) -> list[tuple[str, str, int]]:
    counts = Counter(
        (truth, predicted)
        for truth, predicted in zip(y_true, y_pred, strict=True)
        if truth != predicted
    )
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    return [(truth, predicted, count) for (truth, predicted), count in ordered[:limit]]


def _summary(
    *,
    cases: Sequence[Case],
    rules: KeywordRules,
    metrics: Metrics,
    report: BaselineReport,
    y_true: Sequence[str],
    y_pred: Sequence[str],
    tfidf: dict[str, Any],
) -> str:
    groups = sorted({truth for truth in y_true})
    lines = [
        "# Linear baseline (\"before\")",
        "",
        "Generated by `make baseline` from the committed replay set. The run "
        "makes no model call and writes the same bytes every time.",
        "",
        "## Inputs",
        "",
        f"- Cases: {len(cases)} from `data/replay_2025.parquet`.",
        f"- Keyword rules: `{_display_path(rules.source)}` version `{rules.version}`, "
        "committed before any model result existed.",
        "- Truth: the NHTSA component group and the crash/fire/injury/death flag "
        "in the same parquet files.",
        f"- Groups in truth ({len(groups)}): "
        + ", ".join(f"`{group}`" for group in groups)
        + ".",
        "",
        "## Component group",
        "",
        "| metric | value | 95% CI | n |",
        "|---|---:|---:|---:|",
        _metric_row("macro-F1", metrics.group_macro_f1),
        _metric_row("coverage", metrics.group_coverage),
        "",
        "`unclear` counts as wrong. The bootstrap uses 2,000 resamples with "
        f"seed {DEFAULT_SEED}.",
        "",
        "Most common misclassifications (truth -> predicted):",
        "",
    ]
    confusions = _top_confusions(y_true, y_pred)
    if confusions:
        lines.extend(
            f"- `{truth}` -> `{predicted}`: {count}"
            for truth, predicted, count in confusions
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety flag",
            "",
            "| metric | value | 95% CI | n |",
            "|---|---:|---:|---:|",
            _metric_row("precision", metrics.safety_precision),
            _metric_row("recall", metrics.safety_recall),
            "",
            "Intervals are Wilson score intervals over the relevant denominator.",
            "",
            "## Routing",
            "",
            "| route | cases |",
            "|---|---:|",
            f"| priority | {report.priority} |",
            f"| standard test | {report.standard_test} |",
            f"| closed no trouble found | {report.no_trouble_found} |",
            "",
            "The standard test always passes in this simulation, so every "
            "standard-test case closes without a root cause. Safety cases go to "
            "priority and wait for an engineer.",
            "",
            "## TF-IDF + logistic regression reference",
            "",
            "A narrative-only text classifier trained on the 2020-2024 knowledge "
            "base and applied to the replay set.",
            "",
            "| metric | value |",
            "|---|---:|",
            f"| accuracy | {tfidf['accuracy']:.4f} |",
            f"| macro-F1 | {tfidf['macro_f1']['value']:.4f} |",
            f"| macro-F1 95% CI | [{tfidf['macro_f1']['ci_low']:.4f}, "
            f"{tfidf['macro_f1']['ci_high']:.4f}] |",
            f"| train cases | {tfidf['train_size']} |",
            f"| vocabulary | {tfidf['vocabulary_size']} |",
            "",
            "## Metrics not available in the linear pipeline",
            "",
            "- Quote grounding and citation validity: the baseline quotes no source.",
            "- Issue detection: the baseline has no fleet-level issue agent.",
            "- Recall linking: the baseline links no recalls.",
            "",
            "## Workload model",
            "",
            "The linear pipeline is modelled with one human touch per case (the "
            "person who registers the report and pushes it to the standard test), "
            "four fixed steps, zero model cost and zero latency. Those figures "
            "come from the synthetic trace in `baseline/pipeline.py`, not from an "
            "observed run; they exist so both pipelines feed the same workload "
            "function.",
            "",
        ]
    )
    return "\n".join(lines)


def run_baseline(
    *,
    data_dir: str | Path = "data",
    out_dir: str | Path = "results/baseline",
    keywords_path: str | Path | None = None,
    seed: int = DEFAULT_SEED,
) -> BaselineReport:
    """Run the linear pipeline and the reference, then write the result files."""

    data_path = Path(data_dir)
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rules = load_keywords(keywords_path)
    cases = load_cases(data_path / "replay_2025.parquet")
    training = load_cases(data_path / "kb_complaints.parquet")

    decisions = run_linear(cases, rules)
    y_true = [case.group or rules.unclear for case in cases]
    y_pred = [decision.group for decision in decisions]

    macro = macro_f1(y_true, y_pred, rng=random.Random(seed))
    coverage = group_coverage(y_pred, unclear=rules.unclear)
    safety_truth = [case.safety_relevant for case in cases]
    safety_pred = [decision.safety_relevant for decision in decisions]
    safety_precision, safety_recall = safety_scores(safety_truth, safety_pred)

    proposals = _baseline_proposals(cases, decisions)
    targeted = targeted_test_share(proposals)
    targeted_with_quote = targeted_test_with_quote_share(proposals)
    run_metrics = workload(baseline_runs(cases, decisions))

    metrics = Metrics(
        cases=len(cases),
        group_macro_f1=macro,
        group_coverage=coverage,
        safety_precision=safety_precision,
        safety_recall=safety_recall,
        targeted_test_share=targeted,
        targeted_test_with_quote_share=targeted_with_quote,
        human_touches_per_case=run_metrics["human_touches_per_case"],
        steps_per_case=run_metrics["steps_per_case"],
        cost_per_1000_cases_usd=run_metrics["cost_per_1000_cases_usd"],
        latency_p50_ms=run_metrics["latency_p50_ms"],
        latency_p95_ms=run_metrics["latency_p95_ms"],
        budget_hits=int(run_metrics["budget_hits"]),
    )

    reference = fit_tfidf_logreg(training, seed=seed)
    predicted = reference.predict(cases)
    tfidf_macro = macro_f1(y_true, predicted, rng=random.Random(seed))
    tfidf_accuracy = (
        sum(1 for truth, guess in zip(y_true, predicted, strict=True) if truth == guess)
        / len(cases)
        if cases
        else 0.0
    )
    tfidf = {
        "accuracy": round(tfidf_accuracy, 6),
        "macro_f1": tfidf_macro.model_dump(mode="json"),
        "train_size": reference.train_size,
        "test_size": len(cases),
        "vocabulary_size": reference.vocabulary_size,
        "labels": list(reference.labels),
        "predictions": [
            {"case_id": case.id, "true": truth, "predicted": guess}
            for case, truth, guess in zip(cases, y_true, predicted, strict=True)
        ],
    }

    priority = sum(1 for decision in decisions if decision.route == "priority")
    standard_test = len(decisions) - priority
    no_trouble_found = sum(1 for decision in decisions if decision.closed_no_trouble_found)

    report = BaselineReport(
        out_dir=output_path,
        cases=len(cases),
        macro_f1=macro,
        coverage=coverage,
        safety_precision=safety_precision,
        safety_recall=safety_recall,
        priority=priority,
        standard_test=standard_test,
        no_trouble_found=no_trouble_found,
        tfidf_macro_f1=tfidf_macro,
    )

    _write_json(
        output_path / "decisions.json",
        [_decision_payload(decision) for decision in sorted(decisions, key=lambda d: d.case_id)],
    )
    _write_json(output_path / "metrics.json", metrics.model_dump(mode="json"))
    _write_json(output_path / "tfidf.json", tfidf)
    (output_path / "SUMMARY.md").write_text(
        _summary(
            cases=cases,
            rules=rules,
            metrics=metrics,
            report=report,
            y_true=y_true,
            y_pred=y_pred,
            tfidf=tfidf,
        ),
        encoding="utf-8",
    )
    return report
