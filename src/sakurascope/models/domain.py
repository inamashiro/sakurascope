"""Pydantic models for SakuraScope domain entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

SourceType = Literal[
    "university_site",
    "graduate_school_site",
    "lab_or_supervisor_page",
    "official_admission_notice",
    "official_rss",
    "public_pdf",
    "other",
]

CollectionStrategy = Literal["html", "rss", "pdf"]

ParseStatus = Literal["ok", "partial", "failed", "skipped"]

ReviewStatus = Literal[
    "insufficient_info",
    "research_topic_may_match",
    "public_admission_info_found",
    "eligibility_confirmed",
    "needs_review",
    "needs_university_confirmation",
]


class SourceConfig(BaseModel):
    """A user-configured public source from YAML (not yet a DB row)."""

    source_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_url: HttpUrl
    source_type: SourceType = "other"
    collection_strategy: CollectionStrategy = "html"
    enabled: bool = False
    notes: str | None = None


class SourceRecord(BaseModel):
    """Persisted source status (mirrors storage)."""

    source_id: str
    source_name: str
    source_url: str
    source_type: str
    collection_strategy: str
    enabled: bool = True
    notes: str | None = None
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_http_status: int | None = None
    last_error: str | None = None


class PageSnapshotRecord(BaseModel):
    """One fetch/parse attempt for a source URL (or RSS item URL)."""

    snapshot_id: str
    source_id: str
    original_url: str
    final_url: str | None = None
    fetched_at: datetime
    http_status: int | None = None
    content_hash: str | None = None
    content_type: str | None = None
    title: str | None = None
    extracted_text: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    parse_status: ParseStatus = "failed"
    error_message: str | None = None
    is_duplicate_content: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class InstitutionRecord(BaseModel):
    institution_id: str
    official_name: str | None = None
    japanese_name: str | None = None
    english_name: str | None = None
    official_url: str | None = None
    country: str | None = "Japan"
    notes: str | None = None


class OpportunityRecord(BaseModel):
    opportunity_id: str
    title: str | None = None
    institution_id: str | None = None
    lab_id: str | None = None
    opportunity_type: str | None = None
    degree_level: str | None = None
    research_area: str | None = None
    eligibility_text: str | None = None
    language_requirements: str | None = None
    application_open_date: str | None = None
    application_deadline: str | None = None
    tuition_or_fee_text: str | None = None
    funding_text: str | None = None
    status: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_verified_at: datetime | None = None
    official_source_url: str | None = None
    normalized_url: str | None = None
    content_hash: str | None = None
    review_status: ReviewStatus | str = "insufficient_info"
    open_questions: str | None = None
    graduate_school_candidate: str | None = None
    has_public_admission_language: bool = False
    research_topic_may_match: bool = False


class EvidenceRecord(BaseModel):
    evidence_id: str
    entity_type: str
    entity_id: str
    field_name: str
    source_url: str | None = None
    snapshot_id: str | None = None
    quoted_text: str
    evidence_date: datetime | None = None
    extraction_method: str = "rules"
    verification_status: str = "unverified"


class ChangeEventRecord(BaseModel):
    change_id: str
    change_kind: str
    message: str
    detected_at: datetime
    entity_type: str | None = None
    entity_id: str | None = None
    snapshot_id: str | None = None
    source_id: str | None = None
    details_json: dict[str, Any] = Field(default_factory=dict)


class RunLogRecord(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    pages_processed: int = 0
    new_records: int = 0
    updated_records: int = 0
    duplicates_found: int = 0
    error_summary: str | None = None


class FetchResult(BaseModel):
    """Raw HTTP outcome before parsing (shared by collectors)."""

    original_url: str
    final_url: str
    status_code: int
    content_type: str | None = None
    body: bytes = b""
    etag: str | None = None
    last_modified: str | None = None
    error_message: str | None = None
    blocked_by_robots: bool = False
