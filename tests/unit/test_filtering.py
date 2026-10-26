"""Research-area filtering and bucket classification tests."""

from __future__ import annotations

from datetime import UTC, datetime

from sakurascope.filtering.areas import ResearchAreaConfig, ResearchAreaEntry, load_research_areas
from sakurascope.filtering.classify import (
    BUCKET_ELIGIBILITY_UNCONFIRMED,
    BUCKET_OFFICIAL_APPLICATION_FOUND,
    BUCKET_RESEARCH_TOPIC_RELATED,
    FilterCriteria,
    classify_opportunity,
    filter_opportunities,
)
from sakurascope.models.domain import OpportunityRecord


def _opp(**kwargs) -> OpportunityRecord:
    base = dict(
        opportunity_id="o1",
        title="MOCK Public Health notice",
        research_area="Public Health, Epidemiology",
        research_topic_may_match=True,
        has_public_admission_language=False,
        review_status="research_topic_may_match",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return OpportunityRecord(**base)


def test_load_default_and_repo_research_areas() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    cfg = load_research_areas(root / "config" / "research_areas.yaml")
    assert any(a.name == "Public Health" for a in cfg.areas)
    assert cfg.min_topic_score > 0


def test_topic_related_bucket_not_admission() -> None:
    cfg = ResearchAreaConfig(
        areas=[ResearchAreaEntry(name="Public Health", weight=1.0, keywords=["public health"])]
    )
    item = classify_opportunity(_opp(), cfg)
    assert BUCKET_RESEARCH_TOPIC_RELATED in item.buckets
    assert BUCKET_ELIGIBILITY_UNCONFIRMED in item.buckets
    assert BUCKET_OFFICIAL_APPLICATION_FOUND not in item.buckets
    assert item.topic_relevance_score > 0
    assert any("NOT" in e and "admission" in e.lower() for e in item.explanations)


def test_admission_pending_bucket() -> None:
    cfg = ResearchAreaConfig(areas=[ResearchAreaEntry(name="Epidemiology", weight=1.0)])
    item = classify_opportunity(
        _opp(
            has_public_admission_language=True,
            review_status="public_admission_info_found",
            application_deadline="2026-05-15",
            research_area="Epidemiology",
        ),
        cfg,
    )
    assert BUCKET_OFFICIAL_APPLICATION_FOUND in item.buckets
    assert "admission_info_pending_verification" in item.buckets


def test_filter_by_area_and_deadline() -> None:
    cfg = ResearchAreaConfig(
        areas=[
            ResearchAreaEntry(name="Public Health", weight=1.0),
            ResearchAreaEntry(name="Medical AI", weight=1.0),
        ]
    )
    items = [
        classify_opportunity(
            _opp(
                opportunity_id="a", research_area="Public Health", application_deadline="2026-05-01"
            ),
            cfg,
        ),
        classify_opportunity(
            _opp(
                opportunity_id="b",
                title="Medical AI lab",
                research_area="Medical AI",
                application_deadline="2025-01-01",
            ),
            cfg,
        ),
    ]
    filtered = filter_opportunities(
        items,
        FilterCriteria(research_areas=["Public Health"], deadline_from="2026-01-01"),
        cfg,
    )
    assert len(filtered) == 1
    assert filtered[0].opportunity.opportunity_id == "a"
