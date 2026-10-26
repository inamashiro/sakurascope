"""JSON report writer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sakurascope import __version__
from sakurascope.filtering.classify import FilteredOpportunity


def render_json_payload(
    items: list[FilteredOpportunity],
    *,
    generated_at: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(UTC)
    return {
        "sakurascope_version": __version__,
        "generated_at": generated_at.isoformat(),
        "disclaimer": (
            "Topic relevance is not admission probability. "
            "Fetched/checked timestamps are not announcement publication dates "
            "unless separately evidenced."
        ),
        "meta": meta or {},
        "count": len(items),
        "opportunities": [_item_to_dict(item) for item in items],
    }


def _item_to_dict(item: FilteredOpportunity) -> dict[str, Any]:
    opp = item.opportunity
    return {
        "opportunity_id": opp.opportunity_id,
        "title": opp.title,
        "institution_id": opp.institution_id,
        "graduate_school_candidate": opp.graduate_school_candidate,
        "opportunity_type": opp.opportunity_type,
        "degree_level": opp.degree_level,
        "research_area": opp.research_area,
        "matched_areas": item.matched_areas,
        "topic_relevance_score": item.topic_relevance_score,
        "topic_relevance_note": "Weighted keyword overlap only; NOT admission probability",
        "eligibility_text": opp.eligibility_text,
        "language_requirements": opp.language_requirements,
        "application_open_date": opp.application_open_date,
        "application_deadline": opp.application_deadline,
        "dates_note": (
            "application_* fields are extracted from source text when evidenced; "
            "they are not the report generation timestamp."
        ),
        "has_public_admission_language": opp.has_public_admission_language,
        "research_topic_may_match": opp.research_topic_may_match,
        "review_status": opp.review_status,
        "buckets": item.buckets,
        "official_source_url": opp.official_source_url,
        "normalized_url": opp.normalized_url,
        "first_seen_at": opp.first_seen_at.isoformat() if opp.first_seen_at else None,
        "last_seen_at": opp.last_seen_at.isoformat() if opp.last_seen_at else None,
        "last_verified_at": opp.last_verified_at.isoformat() if opp.last_verified_at else None,
        "open_questions": opp.open_questions,
        "explanations": item.explanations,
        "evidence": [
            {
                "evidence_id": ev.evidence_id,
                "field_name": ev.field_name,
                "quoted_text": ev.quoted_text,
                "source_url": ev.source_url,
                "snapshot_id": ev.snapshot_id,
                "extraction_method": ev.extraction_method,
                "verification_status": ev.verification_status,
                "evidence_date": ev.evidence_date.isoformat() if ev.evidence_date else None,
            }
            for ev in item.evidence
        ],
    }
