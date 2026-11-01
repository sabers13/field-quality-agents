from __future__ import annotations

from field_quality_agents.contracts import Clue, ClueKind
from field_quality_agents.tools import verify_quotes

TEXT = "The wiper motor stops\n intermittently when   the cabin is cold."


def clue(quote: str) -> Clue:
    return Clue(kind=ClueKind.SYMPTOM, quote=quote)


def test_quote_after_whitespace_normalisation() -> None:
    checks = verify_quotes(TEXT, [clue("wiper motor stops intermittently when")])
    assert [(check.quote, check.verified) for check in checks] == [
        ("wiper motor stops intermittently when", True)
    ]


def test_quote_must_match_case_exactly() -> None:
    checks = verify_quotes(TEXT, [clue("Wiper motor stops")])
    assert checks[0].verified is False


def test_quote_must_be_present() -> None:
    checks = verify_quotes(TEXT, [clue("wiper motor catches fire")])
    assert checks[0].verified is False


def test_no_quotes_returns_no_results() -> None:
    assert verify_quotes(TEXT, []) == []


def test_every_quote_gets_a_result_in_order() -> None:
    checks = verify_quotes(
        TEXT,
        [
            clue("wiper motor stops"),
            clue("cabin is cold"),
            clue("not in the text"),
        ],
    )
    assert [check.verified for check in checks] == [True, True, False]
    assert [check.quote for check in checks] == [
        "wiper motor stops",
        "cabin is cold",
        "not in the text",
    ]
