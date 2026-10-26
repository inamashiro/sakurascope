"""RSS parser tests using local fixtures (no network)."""

from __future__ import annotations

from pathlib import Path

from sakurascope.parsers.rss import parse_rss

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_feed.xml"


def test_parse_rss_entries_and_dedupe() -> None:
    feed = parse_rss(FIXTURE.read_bytes())
    assert feed.parse_status == "ok"
    assert feed.feed_title is not None
    assert "MOCK" in feed.feed_title
    assert len(feed.entries) == 2
    assert feed.entries[0].title is not None
    assert feed.entries[0].link is not None
    assert feed.entries[0].published_at is not None
    assert feed.entries[0].published_at.year == 2025


def test_parse_rss_invalid_content() -> None:
    feed = parse_rss(b"this is not a feed at all <<<")
    assert feed.parse_status in {"failed", "partial"}
    assert feed.entries == [] or feed.parse_status != "ok"
