"""Pydantic schema for model JSON responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiEvidenceItem(BaseModel):
    field_name: str
    quoted_text: str


class AiExtractionPayload(BaseModel):
    """Strict model output. official_source_url is intentionally absent."""

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
    has_public_admission_language: bool = False
    research_topic_may_match: bool = False
    review_status: str = "needs_review"
    open_questions: list[str] = Field(default_factory=list)
    evidence: list[AiEvidenceItem] = Field(default_factory=list)
