"""Extractor interface and shared result types."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from sakurascope.models.domain import PageSnapshotRecord, SourceConfig


class EvidenceDraft(BaseModel):
    field_name: str
    quoted_text: str
    source_url: str | None = None
    snapshot_id: str | None = None
    extraction_method: str = "rules"
    verification_status: str = "unverified"


class ExtractionResult(BaseModel):
    """
    Structured extraction output.

    Missing fields stay null. review_status is needs_review when evidence is weak
    or only topic keywords matched without admission language.
    """

    title: str | None = None
    institution_name_candidate: str | None = None
    graduate_school_candidate: str | None = None
    opportunity_type: str | None = None
    degree_level: str | None = None
    research_areas: list[str] = Field(default_factory=list)
    eligibility_text: str | None = None
    language_requirements: str | None = None
    application_open_date: str | None = None
    application_deadline: str | None = None
    tuition_or_fee_text: str | None = None
    funding_text: str | None = None
    official_source_url: str | None = None
    has_public_admission_language: bool = False
    research_topic_may_match: bool = False
    review_status: str = "insufficient_info"
    open_questions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceDraft] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def evidence_matches_source(self, source_text: str) -> bool:
        """Reject drafts whose quotes are not substrings of the source text."""
        if not source_text:
            return not self.evidence
        return all(e.quoted_text and e.quoted_text in source_text for e in self.evidence)


class Extractor(Protocol):
    name: str

    def extract(
        self,
        snapshot: PageSnapshotRecord,
        source: SourceConfig | None = None,
    ) -> ExtractionResult: ...
