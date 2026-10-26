"""Classify and filter opportunities with explainable buckets (not admission odds)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sakurascope.filtering.areas import ResearchAreaConfig
from sakurascope.models.domain import EvidenceRecord, OpportunityRecord

# Transparent buckets shown to users. Never means "you will be admitted".
BUCKET_RESEARCH_TOPIC_RELATED = "research_topic_related"
BUCKET_ADMISSION_PENDING_VERIFY = "admission_info_pending_verification"
BUCKET_OFFICIAL_APPLICATION_FOUND = "official_application_info_found"
BUCKET_ELIGIBILITY_UNCONFIRMED = "eligibility_unconfirmed"
BUCKET_INSUFFICIENT_INFO = "insufficient_info"


@dataclass
class FilterCriteria:
    research_areas: list[str] | None = None
    degree_levels: list[str] | None = None
    review_statuses: list[str] | None = None
    require_public_admission_info: bool | None = None
    require_topic_match: bool = False
    min_topic_score: float | None = None
    deadline_from: str | None = None  # ISO date string inclusive
    deadline_to: str | None = None
    query: str | None = None


@dataclass
class FilteredOpportunity:
    opportunity: OpportunityRecord
    buckets: list[str]
    matched_areas: list[str]
    topic_relevance_score: float
    explanations: list[str] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)


def classify_opportunity(
    opportunity: OpportunityRecord,
    area_config: ResearchAreaConfig,
    *,
    evidence: list[EvidenceRecord] | None = None,
) -> FilteredOpportunity:
    matched = _matched_areas(opportunity, area_config)
    score = _topic_score(matched, area_config)
    buckets: list[str] = []
    explanations: list[str] = []

    # Eligibility is never auto-confirmed by this tool.
    if opportunity.review_status != "eligibility_confirmed":
        buckets.append(BUCKET_ELIGIBILITY_UNCONFIRMED)
        explanations.append("Eligibility remains unconfirmed until a human verifies official text.")

    if opportunity.has_public_admission_language or opportunity.review_status in {
        "public_admission_info_found",
    }:
        buckets.append(BUCKET_OFFICIAL_APPLICATION_FOUND)
        buckets.append(BUCKET_ADMISSION_PENDING_VERIFY)
        explanations.append(
            "Public admission language was observed; dates/eligibility still need verification."
        )
    elif opportunity.research_topic_may_match or matched:
        buckets.append(BUCKET_RESEARCH_TOPIC_RELATED)
        explanations.append("Research-area keywords matched. This is NOT evidence of an open call.")
    else:
        buckets.append(BUCKET_INSUFFICIENT_INFO)
        explanations.append("Not enough structured information to classify beyond observation.")

    if opportunity.application_deadline:
        explanations.append(
            f"Extracted deadline candidate: {opportunity.application_deadline} "
            "(source-page date if evidenced; not the report generation time)."
        )

    explanations.append(
        f"Topic relevance score={score:.2f} (weighted keyword overlap only; "
        "NOT an admission probability)."
    )

    return FilteredOpportunity(
        opportunity=opportunity,
        buckets=buckets,
        matched_areas=matched,
        topic_relevance_score=score,
        explanations=explanations,
        evidence=list(evidence or []),
    )


def filter_opportunities(
    items: list[FilteredOpportunity],
    criteria: FilterCriteria,
    area_config: ResearchAreaConfig,
) -> list[FilteredOpportunity]:
    min_score = (
        criteria.min_topic_score
        if criteria.min_topic_score is not None
        else area_config.min_topic_score
    )
    out: list[FilteredOpportunity] = []
    for item in items:
        opp = item.opportunity
        if criteria.research_areas:
            wanted = {a.lower() for a in criteria.research_areas}
            if not any(a.lower() in wanted for a in item.matched_areas):
                # Also allow substring match against stored research_area field.
                stored = (opp.research_area or "").lower()
                if not any(a in stored for a in wanted):
                    continue
        if criteria.degree_levels:
            levels = {d.lower() for d in criteria.degree_levels}
            if not opp.degree_level or opp.degree_level.lower() not in levels:
                continue
        if criteria.review_statuses:
            statuses = {s.lower() for s in criteria.review_statuses}
            if str(opp.review_status).lower() not in statuses:
                continue
        if criteria.require_public_admission_info is True and not (
            opp.has_public_admission_language or BUCKET_OFFICIAL_APPLICATION_FOUND in item.buckets
        ):
            continue
        if criteria.require_public_admission_info is False and (
            opp.has_public_admission_language or BUCKET_OFFICIAL_APPLICATION_FOUND in item.buckets
        ):
            continue
        if criteria.require_topic_match and item.topic_relevance_score < min_score:
            continue
        if criteria.deadline_from and (opp.application_deadline or "") < criteria.deadline_from:
            continue
        if criteria.deadline_to and (opp.application_deadline or "9999") > criteria.deadline_to:
            continue
        if criteria.query:
            q = criteria.query.lower()
            hay = " ".join(
                filter(
                    None,
                    [
                        opp.title,
                        opp.research_area,
                        opp.eligibility_text,
                        opp.official_source_url,
                        opp.open_questions,
                    ],
                )
            ).lower()
            if q not in hay:
                continue
        out.append(item)
    return out


def _matched_areas(opportunity: OpportunityRecord, config: ResearchAreaConfig) -> list[str]:
    stored = opportunity.research_area or ""
    parts = [p.strip() for p in stored.split(",") if p.strip()]
    known = {a.name for a in config.areas}
    matched = [p for p in parts if p in known]
    # Also scan title/eligibility for configured keywords when stored field is empty-ish.
    blob = " ".join(filter(None, [opportunity.title, opportunity.eligibility_text, stored])).lower()
    for area in config.areas:
        if area.name in matched:
            continue
        for kw in area.keywords:
            if kw.lower() in blob:
                matched.append(area.name)
                break
    return matched


def _topic_score(matched: list[str], config: ResearchAreaConfig) -> float:
    """Average weight of matched areas. Explicitly NOT an admission probability."""
    if not matched:
        return 0.0
    weights = config.weight_map()
    total = sum(weights.get(name, 1.0) for name in matched)
    return round(total / len(matched), 4)
