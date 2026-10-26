"""Validate and sanitize AI extraction against source text."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from sakurascope.extraction.ai.schema import AiExtractionPayload
from sakurascope.extraction.base import EvidenceDraft, ExtractionResult

_ALLOWED_REVIEW = {
    "insufficient_info",
    "research_topic_may_match",
    "public_admission_info_found",
    "needs_review",
}

# Fields that may be copied from AI only when evidence quote is present in source.
_EVIDENCED_FIELDS = {
    "title",
    "institution_name_candidate",
    "graduate_school_candidate",
    "opportunity_type",
    "degree_level",
    "eligibility_text",
    "language_requirements",
    "application_open_date",
    "application_deadline",
    "tuition_or_fee_text",
    "funding_text",
    "research_area",
}


class InvalidAiJsonError(ValueError):
    """Raised when the model returns non-JSON or schema-invalid content."""


def parse_ai_json(content: str) -> AiExtractionPayload:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidAiJsonError(f"Invalid JSON from AI: {exc}") from exc
    try:
        return AiExtractionPayload.model_validate(data)
    except ValidationError as exc:
        raise InvalidAiJsonError(f"AI JSON failed schema validation: {exc}") from exc


def sanitize_ai_extraction(
    payload: AiExtractionPayload,
    *,
    source_text: str,
    snapshot_id: str | None = None,
    source_url: str | None = None,
) -> ExtractionResult:
    """
    Convert AI payload into ExtractionResult.

    - Drop evidence quotes not found in source_text
    - Null out fields lacking matching evidence
    - Never accept AI-invented official_source_url (caller sets URL)
    - Never allow eligibility_confirmed
    """
    trusted = source_text or ""
    valid_evidence: list[EvidenceDraft] = []
    evidenced_fields: set[str] = set()

    for item in payload.evidence:
        quote = (item.quoted_text or "").strip()
        if not quote or quote not in trusted:
            continue
        field = item.field_name.strip()
        valid_evidence.append(
            EvidenceDraft(
                field_name=field,
                quoted_text=quote,
                source_url=source_url,
                snapshot_id=snapshot_id,
                extraction_method="ai",
                verification_status="unverified",
            )
        )
        evidenced_fields.add(field)
        if field == "research_areas":
            evidenced_fields.add("research_area")

    def take(field: str, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if field not in evidenced_fields and field in _EVIDENCED_FIELDS:
            return None
        # Value itself should appear in source for text fields when possible.
        if field in _EVIDENCED_FIELDS and value not in trusted and field not in evidenced_fields:
            return None
        return value

    areas = []
    if "research_area" in evidenced_fields or "research_areas" in evidenced_fields:
        areas = [a for a in payload.research_areas if a]

    review = payload.review_status if payload.review_status in _ALLOWED_REVIEW else "needs_review"
    if review == "eligibility_confirmed":
        review = "needs_review"

    dropped = len(payload.evidence) - len(valid_evidence)
    questions = list(payload.open_questions)
    if dropped:
        questions.append(
            f"{dropped} AI evidence quote(s) rejected because they were not found in source text."
        )
    questions.append("AI output is unverified; eligibility is not confirmed.")

    # Boolean flags: only keep True when supporting evidence exists or keyword-like evidence.
    has_admission = bool(payload.has_public_admission_language) and (
        "opportunity_type" in evidenced_fields
        or "eligibility_text" in evidenced_fields
        or any(e.field_name == "has_public_admission_language" for e in valid_evidence)
    )
    topic_match = bool(payload.research_topic_may_match) and bool(areas)

    if not has_admission and not topic_match and not valid_evidence:
        review = "insufficient_info"
    elif has_admission:
        review = "public_admission_info_found"
    elif topic_match and review == "insufficient_info":
        review = "research_topic_may_match"

    result = ExtractionResult(
        title=take("title", payload.title),
        institution_name_candidate=take(
            "institution_name_candidate", payload.institution_name_candidate
        ),
        graduate_school_candidate=take(
            "graduate_school_candidate", payload.graduate_school_candidate
        ),
        opportunity_type=take("opportunity_type", payload.opportunity_type),
        degree_level=take("degree_level", payload.degree_level),
        research_areas=areas,
        eligibility_text=take("eligibility_text", payload.eligibility_text),
        language_requirements=take("language_requirements", payload.language_requirements),
        application_open_date=take("application_open_date", payload.application_open_date),
        application_deadline=take("application_deadline", payload.application_deadline),
        tuition_or_fee_text=take("tuition_or_fee_text", payload.tuition_or_fee_text),
        funding_text=take("funding_text", payload.funding_text),
        official_source_url=None,  # never from AI
        has_public_admission_language=has_admission,
        research_topic_may_match=topic_match or bool(areas),
        review_status=review,
        open_questions=questions,
        evidence=valid_evidence,
        metadata={
            "extractor": "ai",
            "ai_evidence_accepted": len(valid_evidence),
            "ai_evidence_rejected": dropped,
        },
    )
    return result
