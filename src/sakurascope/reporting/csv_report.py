"""CSV report writer (Excel-friendly, formula-safe)."""

from __future__ import annotations

import csv
from io import StringIO

from sakurascope.filtering.classify import FilteredOpportunity
from sakurascope.reporting.csv_safe import csv_safe_cell

CSV_COLUMNS = [
    "opportunity_id",
    "title",
    "research_area",
    "matched_areas",
    "topic_relevance_score",
    "degree_level",
    "opportunity_type",
    "application_deadline",
    "application_open_date",
    "has_public_admission_language",
    "research_topic_may_match",
    "review_status",
    "buckets",
    "official_source_url",
    "first_seen_at",
    "last_seen_at",
    "eligibility_text",
    "open_questions",
    "graduate_school_candidate",
]


def render_csv(items: list[FilteredOpportunity]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for item in items:
        opp = item.opportunity
        row = {
            "opportunity_id": opp.opportunity_id,
            "title": opp.title,
            "research_area": opp.research_area,
            "matched_areas": "; ".join(item.matched_areas),
            "topic_relevance_score": item.topic_relevance_score,
            "degree_level": opp.degree_level,
            "opportunity_type": opp.opportunity_type,
            "application_deadline": opp.application_deadline,
            "application_open_date": opp.application_open_date,
            "has_public_admission_language": opp.has_public_admission_language,
            "research_topic_may_match": opp.research_topic_may_match,
            "review_status": opp.review_status,
            "buckets": "; ".join(item.buckets),
            "official_source_url": opp.official_source_url,
            "first_seen_at": opp.first_seen_at.isoformat() if opp.first_seen_at else "",
            "last_seen_at": opp.last_seen_at.isoformat() if opp.last_seen_at else "",
            "eligibility_text": opp.eligibility_text,
            "open_questions": opp.open_questions,
            "graduate_school_candidate": opp.graduate_school_candidate,
        }
        writer.writerow({key: csv_safe_cell(value) for key, value in row.items()})
    return buffer.getvalue()
