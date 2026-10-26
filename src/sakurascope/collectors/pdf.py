"""Public PDF collection → PageSnapshotRecord."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sakurascope.collectors.http import HttpFetcher
from sakurascope.models.domain import PageSnapshotRecord, SourceConfig
from sakurascope.parsers.pdf import parse_pdf
from sakurascope.utils.hashing import content_hash

_MAX_STORED_CHARS = 200_000


def collect_pdf_source(
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
                metadata_json={
                    "kind": "pdf",
                    "blocked_by_robots": result.blocked_by_robots,
                },
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
                metadata_json={"kind": "pdf"},
            )
        ]

    content_type = (result.content_type or "").lower()
    looks_like_pdf = result.body.startswith(b"%PDF")
    # Soft path: if Content-Type is wrong but magic is %PDF, still attempt parse.
    if content_type and "pdf" not in content_type and not looks_like_pdf:
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
                error_message=(
                    f"Response does not look like a PDF (content-type={result.content_type!r})."
                ),
                metadata_json={"kind": "pdf"},
            )
        ]

    parsed = parse_pdf(result.body)
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
            content_type=result.content_type or "application/pdf",
            title=None,
            extracted_text=stored or None,
            etag=result.etag,
            last_modified=result.last_modified,
            parse_status=parsed.parse_status,  # type: ignore[arg-type]
            error_message=parsed.error_message,
            metadata_json={
                "kind": "pdf",
                "page_count": parsed.page_count,
                "is_encrypted": parsed.is_encrypted,
                "is_likely_scan": parsed.is_likely_scan,
                "truncated": len(text) > _MAX_STORED_CHARS,
                "text_length": len(text),
                "ocr_used": False,
            },
        )
    ]


def _new_id() -> str:
    return uuid.uuid4().hex
