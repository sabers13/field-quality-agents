"""PII patterns and the screening counts."""

from __future__ import annotations

import pytest

from field_quality_agents.data.pii import PATTERN_NAMES, contains_pii, pii_kind, screen_counts


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("The VIN is 1HGCM82633A004352 and it matters.", "vin"),
        ("Write to synthetic.person@example.com about it.", "email"),
        ("Call (555) 123-4567 during the day.", "phone"),
        ("The vehicle was at 220 North Stephanie Street, Henderson.", "street_address"),
        ("Dealer at 4735 Atlanta Hwy, Athens, GA.", "street_address"),
    ],
)
def test_pii_patterns_match(text: str, kind: str) -> None:
    assert pii_kind(text) == kind
    assert contains_pii(text)


@pytest.mark.parametrize(
    "text",
    [
        "The 2021 Honda Accord had 45,000 miles when the fault appeared.",
        "It happened at 28,000 miles while driving down the freeway.",
        "The report number is 20-005325 and the campaign is 20V246000.",
        "No personal details are present in this synthetic narrative.",
    ],
)
def test_clean_narratives_stay(text: str) -> None:
    assert pii_kind(text) is None
    assert not contains_pii(text)


def test_screen_counts_counts_patterns_and_the_union() -> None:
    narratives = [
        "Clean narrative with no personal details.",
        "Mail me at synthetic@example.com or call 555-123-4567.",
        "The VIN is 1HGCM82633A004352.",
        "No details here either.",
    ]
    counts = screen_counts(narratives)
    assert counts["screened"] == 4
    assert counts["any"] == 2
    assert counts["email"] == 1
    assert counts["phone"] == 1
    assert counts["vin"] == 1
    assert counts["street_address"] == 0
    assert set(PATTERN_NAMES) <= set(counts)
