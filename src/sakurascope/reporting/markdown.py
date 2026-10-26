"""Markdown report writer."""

from __future__ import annotations

from datetime import UTC, datetime

from sakurascope import __version__
from sakurascope.filtering.classify import FilteredOpportunity


def render_markdown(
    items: list[FilteredOpportunity],
    *,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    lines: list[str] = [
        "# SakuraScope Opportunity Report",
        "",
        f"- Generated at (report time): `{generated_at.isoformat()}`",
        f"- SakuraScope version: `{__version__}`",
        f"- Opportunities in report: **{len(items)}**",
        "",
        "> This report never confirms admission eligibility. "
        "Topic relevance ≠ open recruitment ≠ verified qualifications.",
        "",
    ]

    if not items:
        lines.append("_No opportunities matched the current filters._")
        lines.append("")
        return "\n".join(lines)

    for index, item in enumerate(items, start=1):
        opp = item.opportunity
        lines.extend(
            [
                f"## {index}. {opp.title or '(untitled)'}",
                "",
                f"- University / institution candidate: {opp.graduate_school_candidate or opp.institution_id or '_unknown_'}",
                f"- Graduate school / lab candidate: {opp.graduate_school_candidate or '_unknown_'}",
                f"- Opportunity title: {opp.title or '_unknown_'}",
                f"- Research areas: {opp.research_area or ', '.join(item.matched_areas) or '_unknown_'}",
                f"- Opportunity type: {opp.opportunity_type or '_unknown_'}",
                f"- Degree level: {opp.degree_level or '_unknown_'}",
                f"- Deadline (if evidenced): {opp.application_deadline or '_none extracted_'}",
                f"- Application open date (if evidenced): {opp.application_open_date or '_none extracted_'}",
                f"- Public admission language observed: {'yes' if opp.has_public_admission_language else 'no'}",
                f"- Review status: `{opp.review_status}`",
                f"- Buckets: {', '.join(f'`{b}`' for b in item.buckets)}",
                f"- Topic relevance score: `{item.topic_relevance_score}` "
                "(NOT admission probability)",
                f"- Official source URL: {opp.official_source_url or '_unknown_'}",
                f"- First seen at: {opp.first_seen_at.isoformat() if opp.first_seen_at else '_unknown_'}",
                f"- Last seen / checked at: {opp.last_seen_at.isoformat() if opp.last_seen_at else '_unknown_'}",
                "",
                "### Key eligibility / admission snippets",
                "",
                f"{opp.eligibility_text or '_No admission snippet extracted._'}",
                "",
                "### Evidence quotes",
                "",
            ]
        )
        if item.evidence:
            for ev in item.evidence:
                lines.append(f"- **{ev.field_name}**: {ev.quoted_text}")
        else:
            lines.append("_No evidence rows stored for this opportunity._")
        lines.extend(["", "### Needs human confirmation", ""])
        if opp.open_questions:
            for q in opp.open_questions.split(" | "):
                lines.append(f"- {q}")
        for exp in item.explanations:
            lines.append(f"- {exp}")
        lines.append("")

    return "\n".join(lines)
