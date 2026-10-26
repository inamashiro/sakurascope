"""RSS/Atom feed collection → one snapshot per unique entry (+ feed summary)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sakurascope.collectors.http import HttpFetcher
from sakurascope.models.domain import PageSnapshotRecord, SourceConfig
from sakurascope.parsers.rss import parse_rss
from sakurascope.utils.hashing import content_hash

_MAX_STORED_CHARS = 50_000


def collect_rss_source(
    source: SourceConfig,
    fetcher: HttpFetcher,
) -> list[PageSnapshotRecord]:
    fetched_at = datetime.now(UTC)
    result = fetcher.fetch(str(source.source_url))

    if result.error_message and not result.body:
        return [
            PageSnapshotRecord(
                snapshot_id=_new_id(),
                source_id=source.source_id,
                original_url=result.original_url,
                final_url=result.final_url,
                fetched_at=fetched_at,
                http_status=result.status_code or None,
                content_type=result.content_type,
                parse_status="failed",
                error_message=result.error_message,
                metadata_json={"kind": "feed", "blocked_by_robots": result.blocked_by_robots},
            )
        ]

    if result.status_code >= 400:
        return [
            PageSnapshotRecord(
                snapshot_id=_new_id(),
                source_id=source.source_id,
                original_url=result.original_url,
                final_url=result.final_url,
                fetched_at=fetched_at,
                http_status=result.status_code,
                content_type=result.content_type,
                parse_status="failed",
                error_message=f"HTTP {result.status_code}",
                metadata_json={"kind": "feed"},
            )
        ]

    feed = parse_rss(result.body)
    snapshots: list[PageSnapshotRecord] = []

    # Feed-level snapshot (raw entry list summary).
    feed_text_parts = []
    if feed.feed_title:
        feed_text_parts.append(f"Feed: {feed.feed_title}")
    for entry in feed.entries:
        feed_text_parts.append(
            " | ".join(
                part
                for part in [
                    entry.title or "",
                    entry.link or "",
                    entry.published_at.isoformat() if entry.published_at else "",
                ]
                if part
            )
        )
    feed_text = "\n".join(feed_text_parts)
    snapshots.append(
        PageSnapshotRecord(
            snapshot_id=_new_id(),
            source_id=source.source_id,
            original_url=result.original_url,
            final_url=result.final_url,
            fetched_at=fetched_at,
            http_status=result.status_code,
            content_hash=content_hash(feed_text) if feed_text else None,
            content_type=result.content_type,
            title=feed.feed_title,
            extracted_text=feed_text or None,
            etag=result.etag,
            last_modified=result.last_modified,
            parse_status=feed.parse_status,  # type: ignore[arg-type]
            error_message=feed.error_message,
            metadata_json={
                "kind": "feed",
                "entry_count": len(feed.entries),
            },
        )
    )

    for entry in feed.entries:
        body_parts = [p for p in [entry.title, entry.summary, entry.link] if p]
        text = "\n".join(body_parts)
        stored = text if len(text) <= _MAX_STORED_CHARS else text[:_MAX_STORED_CHARS]
        snapshots.append(
            PageSnapshotRecord(
                snapshot_id=_new_id(),
                source_id=source.source_id,
                original_url=entry.link or result.original_url,
                final_url=entry.link or result.final_url,
                fetched_at=fetched_at,
                http_status=result.status_code,
                content_hash=content_hash(text) if text else None,
                content_type="application/rss+xml-entry",
                title=entry.title,
                extracted_text=stored or None,
                parse_status="ok" if text else "partial",
                error_message=None if text else "Empty RSS entry",
                metadata_json={
                    "kind": "feed_entry",
                    "entry_id": entry.entry_id,
                    "published_at": entry.published_at.isoformat() if entry.published_at else None,
                    "feed_url": result.final_url,
                },
            )
        )

    return snapshots


def _new_id() -> str:
    return uuid.uuid4().hex
