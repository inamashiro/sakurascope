"""Load opportunities from SQLite and write Markdown/CSV/JSON reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sakurascope.config.settings import Settings
from sakurascope.filtering.areas import load_research_areas
from sakurascope.filtering.classify import (
    FilterCriteria,
    FilteredOpportunity,
    classify_opportunity,
    filter_opportunities,
)
from sakurascope.reporting.csv_report import render_csv
from sakurascope.reporting.json_report import render_json_payload
from sakurascope.reporting.markdown import render_markdown
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository
from sakurascope.utils.logging import get_logger

logger = get_logger("reporting.service")


@dataclass
class ReportOptions:
    formats: list[str] = field(default_factory=lambda: ["markdown", "csv", "json"])
    output_dir: Path | None = None
    criteria: FilterCriteria = field(default_factory=FilterCriteria)
    basename: str = "sakurascope_report"


@dataclass
class ReportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    opportunity_count: int = 0
    generated_at: datetime | None = None


def generate_reports(settings: Settings, options: ReportOptions | None = None) -> ReportResult:
    options = options or ReportOptions()
    generated_at = datetime.now(UTC)
    output_dir = options.output_dir or settings.paths.reports_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    area_config = load_research_areas(settings.paths.research_areas_file)
    db_path = settings.paths.data_dir / settings.paths.database_filename
    database = create_database(db_path)

    with database.session() as session:
        repo = Repository(session)
        raw = repo.list_opportunities()
        classified: list[FilteredOpportunity] = []
        for opp in raw:
            evidence = repo.list_evidence_for_entity("opportunity", opp.opportunity_id)
            classified.append(classify_opportunity(opp, area_config, evidence=evidence))
        filtered = filter_opportunities(classified, options.criteria, area_config)

    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    base = f"{options.basename}_{stamp}"
    result = ReportResult(
        output_dir=output_dir,
        opportunity_count=len(filtered),
        generated_at=generated_at,
    )

    formats = {fmt.lower() for fmt in options.formats}
    if "markdown" in formats or "md" in formats:
        path = output_dir / f"{base}.md"
        path.write_text(render_markdown(filtered, generated_at=generated_at), encoding="utf-8")
        result.files["markdown"] = path
        logger.info("Wrote Markdown report: %s", path)

    if "csv" in formats:
        path = output_dir / f"{base}.csv"
        path.write_text(render_csv(filtered), encoding="utf-8-sig")
        result.files["csv"] = path
        logger.info("Wrote CSV report: %s", path)

    if "json" in formats:
        path = output_dir / f"{base}.json"
        payload = render_json_payload(
            filtered,
            generated_at=generated_at,
            meta={
                "database": str(db_path),
                "filters": {
                    "research_areas": options.criteria.research_areas,
                    "degree_levels": options.criteria.degree_levels,
                    "review_statuses": options.criteria.review_statuses,
                    "require_public_admission_info": options.criteria.require_public_admission_info,
                    "require_topic_match": options.criteria.require_topic_match,
                    "min_topic_score": options.criteria.min_topic_score,
                    "deadline_from": options.criteria.deadline_from,
                    "deadline_to": options.criteria.deadline_to,
                    "query": options.criteria.query,
                },
                "research_areas_file": str(settings.paths.research_areas_file)
                if settings.paths.research_areas_file
                else None,
            },
        )
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        result.files["json"] = path
        logger.info("Wrote JSON report: %s", path)

    if not result.files:
        raise ValueError("No report formats selected. Use markdown/csv/json.")

    return result
