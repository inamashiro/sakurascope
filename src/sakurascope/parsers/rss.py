"""RSS / Atom feed parsing (no network)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any

import feedparser


@dataclass(frozen=True)
class ParsedFeedEntry:
    title: str | None
    link: str | None
    summary: str | None
    published_at: datetime | None
    entry_id: str | None


@dataclass(frozen=True)
class ParsedFeed:
    feed_title: str | None
    entries: list[ParsedFeedEntry] = field(default_factory=list)
    parse_status: str = "ok"
    error_message: str | None = None


def parse_rss(content: str | bytes) -> ParsedFeed:
    """Parse RSS/Atom bytes or text into structured entries."""
    try:
        parsed = feedparser.parse(content)
    except Exception as exc:  # noqa: BLE001
        return ParsedFeed(
            feed_title=None,
            entries=[],
            parse_status="failed",
            error_message=f"RSS parse error: {exc}",
        )

    # feedparser rarely raises; bozo means structural issues.
    bozo = bool(getattr(parsed, "bozo", False))
    feed_title = _clean(getattr(parsed.feed, "title", None))
    entries: list[ParsedFeedEntry] = []
    seen_keys: set[str] = set()

    for raw in getattr(parsed, "entries", []) or []:
        title = _clean(raw.get("title"))
        link = _clean(raw.get("link"))
        summary = _clean(raw.get("summary") or raw.get("description"))
        entry_id = _clean(raw.get("id") or raw.get("guid"))
        published_at = _entry_datetime(raw)

        dedupe_key = (entry_id or link or title or "").strip().lower()
        if not dedupe_key or dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        entries.append(
            ParsedFeedEntry(
                title=title,
                link=link,
                summary=summary,
                published_at=published_at,
                entry_id=entry_id,
            )
        )

    if not entries and bozo:
        err = getattr(parsed, "bozo_exception", None)
        return ParsedFeed(
            feed_title=feed_title,
            entries=[],
            parse_status="failed",
            error_message=f"Invalid feed: {err}" if err else "Invalid feed",
        )

    status = "ok" if entries else "partial"
    return ParsedFeed(feed_title=feed_title, entries=entries, parse_status=status)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _entry_datetime(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if isinstance(value, struct_time):
            try:
                return datetime(*value[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(str(raw))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except (TypeError, ValueError, IndexError, OverflowError):
            continue
    return None
