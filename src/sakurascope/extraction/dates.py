"""Deterministic date extraction from page/RSS text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

# Order matters: more specific patterns first.
_DATE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ymd_jp",
        re.compile(r"(?P<y>20\d{2})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日"),
    ),
    (
        "ymd_cn",
        re.compile(r"(?P<y>20\d{2})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日"),
    ),
    (
        "ymd_iso",
        re.compile(r"(?P<y>20\d{2})-(?P<m>\d{1,2})-(?P<d>\d{1,2})"),
    ),
    (
        "ymd_slash",
        re.compile(r"(?P<y>20\d{2})/(?P<m>\d{1,2})/(?P<d>\d{1,2})"),
    ),
    (
        "mdy_en",
        re.compile(
            r"(?P<m>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Dec(?:ember)?)\s+(?P<d>\d{1,2}),?\s+(?P<y>20\d{2})",
            re.IGNORECASE,
        ),
    ),
]

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_DEADLINE_CONTEXT = re.compile(
    r"(締切|締め切り|期限|deadline|due\s*date|截止|报名截止|出願期間|募集期間|"
    r"application\s+period|application\s+deadline)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedDate:
    iso_date: str | None
    quoted_text: str
    likely_deadline: bool
    pattern_name: str


def extract_dates(text: str) -> list[ExtractedDate]:
    """Return dates found in text with local evidence quotes. Never invent dates."""
    if not text:
        return []
    found: list[ExtractedDate] = []
    seen: set[tuple[str | None, str]] = set()

    for pattern_name, pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            iso = _to_iso(match, pattern_name)
            quote = _quote_window(text, match.start(), match.end())
            key = (iso, quote)
            if key in seen:
                continue
            seen.add(key)
            likely = bool(_DEADLINE_CONTEXT.search(quote))
            found.append(
                ExtractedDate(
                    iso_date=iso,
                    quoted_text=quote,
                    likely_deadline=likely,
                    pattern_name=pattern_name,
                )
            )
    return found


def _to_iso(match: re.Match[str], pattern_name: str) -> str | None:
    groups = match.groupdict()
    try:
        year = int(groups["y"])
        month = _MONTHS[groups["m"].lower()] if pattern_name == "mdy_en" else int(groups["m"])
        day = int(groups["d"])
        return date(year, month, day).isoformat()
    except (KeyError, ValueError):
        return None


def _quote_window(text: str, start: int, end: int, radius: int = 40) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    snippet = text[left:right].replace("\n", " ")
    return re.sub(r"\s+", " ", snippet).strip()
