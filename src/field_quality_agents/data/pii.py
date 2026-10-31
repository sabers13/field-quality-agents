"""PII screen for complaint narratives.

A narrative is dropped when it contains a VIN, an e-mail address, a phone
number or a street address. The screen is deliberately broad: dropping a
hundred extra narratives is cheaper than committing one personal record.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = ["PATTERN_NAMES", "contains_pii", "pii_kind", "screen_counts"]

PATTERN_NAMES: tuple[str, ...] = ("vin", "email", "phone", "street_address")

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_PHONE = re.compile(
    r"(?:\+?1[-.\s]?)?"
    r"(?:\(\d{3}\)\s?|\d{3}[-.\s])"
    r"\d{3}[-.\s]\d{4}"
)

# VINs use 17 characters from A-H, J-N, P, R-Z and 0-9: no I, O or Q. Require
# at least one letter and one digit so long numeric ids (photo ids, campaign
# repeats) are not mistaken for a VIN.
_VIN = re.compile(
    r"\b(?=[A-HJ-NPR-Z0-9]*\d)(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])"
    r"[A-HJ-NPR-Z0-9]{17}\b",
    re.IGNORECASE,
)

_ADDRESS = re.compile(
    r"\b(?<![\d,])\d{2,6}\s+"
    r"(?:[NSEW]\.?\s+)?"
    r"(?:[A-Z][A-Za-z0-9.'-]*\s+){1,3}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|"
    r"Place|Pl|Way|Highway|Hwy|Parkway|Pkwy|Terrace|Ter|Circle|Cir|Trail|Trl)\.?"
    r"(?=[\s,.;:]|$)",
    re.IGNORECASE,
)

# A numeric quantity followed by a unit is not an address, even when the unit
# word is also a street suffix ("28,000 miles while driving down the drive").
_NOT_AN_ADDRESS = re.compile(
    r"\b(?:MILES?|MPH|KM|KILOMET(?:ER|RE)S?|FEET|FT|YARDS?|PSI|RPM|PERCENT|"
    r"DOLLARS?|DAYS?|WEEKS?|MONTHS?|YEARS?|HOURS?|MINUTES?|SECONDS?|AMPS?|"
    r"VOLTS?|WATTS?|DEGREES?|GALLONS?|LIT(?:ER|RE)S?|TONS?|POUNDS?)\b",
    re.IGNORECASE,
)

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("vin", _VIN),
    ("email", _EMAIL),
    ("phone", _PHONE),
    ("street_address", _ADDRESS),
)


def _has_address(text: str) -> bool:
    return any(
        not _NOT_AN_ADDRESS.search(match.group(0))
        for match in _ADDRESS.finditer(text)
    )


def _matches(text: str) -> dict[str, bool]:
    found = {"vin": False, "email": False, "phone": False, "street_address": False}
    for name, pattern in _PATTERNS:
        if name == "street_address":
            found[name] = _has_address(text)
        else:
            found[name] = pattern.search(text) is not None
    return found


def pii_kind(text: str) -> str | None:
    """Return the first matching pattern name, or ``None`` when clean."""
    found = _matches(text)
    for name in PATTERN_NAMES:
        if found[name]:
            return name
    return None


def contains_pii(text: str) -> bool:
    """True when any PII pattern matches."""
    return pii_kind(text) is not None


def screen_counts(narratives: Iterable[str]) -> dict[str, int]:
    """Count matches per pattern, the union, and the screened total."""
    counts = {name: 0 for name in PATTERN_NAMES}
    counts["any"] = 0
    counts["screened"] = 0
    for text in narratives:
        counts["screened"] += 1
        found = _matches(text)
        if any(found.values()):
            counts["any"] += 1
        for name in PATTERN_NAMES:
            if found[name]:
                counts[name] += 1
    return counts
