"""HTML page collection → PageSnapshotRecord."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sakurascope.collectors.http import HttpFetcher
from sakurascope.models.domain import PageSnapshotRecord, SourceConfig
from sakurascope.parsers.html import parse_html
from sakurascope.utils.hashing import content_hash

# Keep stored snapshots readable but bounded.
_MAX_STORED_CHARS = 200_000


def collect_html_source(
    source: SourceConfig,
    fetcher: HttpFetcher,
) -> list[PageSnapshotRecord]:
    """Fetch one HTML source and return a single snapshot list."""
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
                metadata_json={"blocked_by_robots": result.blocked_by_robots},
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
                etag=result.etag,
                last_modified=result.last_modified,
                parse_status="failed",
                error_message=f"HTTP {result.status_code}",
            )
        ]

    parsed = parse_html(result.body)
    text = parsed.text
    stored = text if len(text) <= _MAX_STORED_CHARS else text[:_MAX_STORED_CHARS]
    digest = content_hash(text) if text else None

    return [
        PageSnapshotRecord(
            snapshot_id=_new_id(),
            source_id=source.source_id,
            original_url=result.original_url,
            final_url=result.final_url,
            fetched_at=fetched_at,
            http_status=result.status_code,
            content_hash=digest,
            content_type=result.content_type,
            title=parsed.title,
            extracted_text=stored or None,
            etag=result.etag,
            last_modified=result.last_modified,
            parse_status=parsed.parse_status,  # type: ignore[arg-type]
            error_message=parsed.error_message,
            metadata_json={
                "truncated": len(text) > _MAX_STORED_CHARS,
                "text_length": len(text),
            },
        )
    ]


def _new_id() -> str:
    return uuid.uuid4().hex
