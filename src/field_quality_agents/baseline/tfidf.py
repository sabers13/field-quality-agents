"""TF-IDF + logistic regression reference for the component group.

This is the second reference PLAN §7 asks for. It reads only the narrative, so
it is a genuine text classifier rather than a copy of the NHTSA component
taxonomy the keyword rules already use. It trains on the 2020-2024 knowledge
base and predicts the 2025 replay set; the split is by time, not random.

The fit is deterministic: a fixed seed, one job, and a fixed vocabulary cap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from field_quality_agents.contracts import Case

__all__ = ["TfidfReference", "fit_tfidf_logreg", "run_tfidf_logreg"]

#: PLAN §5's replay seed.
DEFAULT_SEED = 20261031

_MAX_FEATURES = 50_000
_MIN_DOCUMENT_FREQUENCY = 2


@dataclass(frozen=True)
class TfidfReference:
    """A fitted reference model plus the sizes the report quotes."""

    vectorizer: TfidfVectorizer
    classifier: LogisticRegression
    vocabulary_size: int
    train_size: int
    labels: tuple[str, ...]

    def predict(self, cases: Sequence[Case]) -> list[str]:
        if not cases:
            return []
        matrix = self.vectorizer.transform([case.narrative for case in cases])
        return [str(label) for label in self.classifier.predict(matrix)]


def fit_tfidf_logreg(
    train: Sequence[Case],
    *,
    seed: int = DEFAULT_SEED,
) -> TfidfReference:
    """Fit the reference on labelled training cases."""

    if not train:
        raise ValueError("train must not be empty")
    labels = tuple(sorted({case.group or "unclear" for case in train}))
    if len(labels) < 2:
        raise ValueError("train must contain at least two component groups")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=_MIN_DOCUMENT_FREQUENCY,
        max_features=_MAX_FEATURES,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform([case.narrative for case in train])
    targets = [case.group or "unclear" for case in train]

    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=1_000,
        C=2.0,
        random_state=seed,
    )
    classifier.fit(matrix, targets)

    return TfidfReference(
        vectorizer=vectorizer,
        classifier=classifier,
        vocabulary_size=len(vectorizer.vocabulary_),
        train_size=len(train),
        labels=labels,
    )


def run_tfidf_logreg(train: Sequence[Case], test: Sequence[Case]) -> list[str]:
    """Fit on ``train`` and return one predicted group label per test case."""

    return fit_tfidf_logreg(train).predict(test)
