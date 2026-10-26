"""Report generation tests (Markdown/CSV/JSON), no network."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from sakurascope.config.settings import load_settings
from sakurascope.filtering.areas import ResearchAreaConfig, ResearchAreaEntry
from sakurascope.filtering.classify import classify_opportunity
from sakurascope.models.domain import EvidenceRecord, OpportunityRecord
from sakurascope.reporting.csv_report import render_csv
from sakurascope.reporting.csv_safe import csv_safe_cell
from sakurascope.reporting.json_report import render_json_payload
from sakurascope.reporting.markdown import render_markdown
from sakurascope.reporting.service import ReportOptions, generate_reports
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository


def test_csv_formula_injection_neutralized() -> None:
    assert csv_safe_cell("=CMD()") == "'=CMD()"
    assert csv_safe_cell("+1+1") == "'+1+1"
    assert csv_safe_cell("normal") == "normal"


def test_markdown_csv_json_render_content() -> None:
    cfg = ResearchAreaConfig(
        areas=[ResearchAreaEntry(name="Public Health", weight=1.0, keywords=["public health"])]
    )
    opp = OpportunityRecord(
        opportunity_id="opp-mock",
        title="[MOCK] Public Health Admission Notice",
        research_area="Public Health",
        has_public_admission_language=True,
        research_topic_may_match=True,
        review_status="public_admission_info_found",
        application_deadline="2026-05-15",
        official_source_url="https://fixtures.sakurascope.test/mock",
        first_seen_at=datetime(2026, 1, 2, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 3, tzinfo=UTC),
        open_questions="Eligibility not confirmed",
        eligibility_text="募集要項（MOCK）",
    )
    evidence = [
        EvidenceRecord(
            evidence_id="e1",
            entity_type="opportunity",
            entity_id="opp-mock",
            field_name="application_deadline",
            quoted_text="締切：2026年5月15日",
            source_url=opp.official_source_url,
        )
    ]
    item = classify_opportunity(opp, cfg, evidence=evidence)

    md = render_markdown([item], generated_at=datetime(2026, 10, 25, tzinfo=UTC))
    assert "Generated at (report time)" in md
    assert "2026-05-15" in md
    assert "NOT admission probability" in md
    assert "締切：2026年5月15日" in md
    assert "eligibility_confirmed" not in md or "never" in md.lower()

    csv_text = render_csv([item])
    assert "opportunity_id" in csv_text
    assert "opp-mock" in csv_text
    assert "topic_relevance_score" in csv_text

    payload = render_json_payload([item], generated_at=datetime(2026, 10, 25, tzinfo=UTC))
    assert payload["count"] == 1
    assert payload["opportunities"][0]["application_deadline"] == "2026-05-15"
    assert "NOT admission probability" in payload["opportunities"][0]["topic_relevance_note"]
    assert payload["opportunities"][0]["evidence"][0]["quoted_text"] == "締切：2026年5月15日"


def test_generate_reports_writes_files(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "t.db"
    db = create_database(db_path)
    with db.session() as session:
        repo = Repository(session)
        opp = OpportunityRecord(
            opportunity_id="r1",
            title="[MOCK] Epidemiology page",
            research_area="Epidemiology",
            research_topic_may_match=True,
            has_public_admission_language=False,
            review_status="research_topic_may_match",
            official_source_url="https://fixtures.sakurascope.test/epi",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        repo.upsert_opportunity(opp)
        session.commit()

    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "t", "environment": "test"},
                "paths": {
                    "data_dir": str(tmp_path / "data"),
                    "log_dir": str(tmp_path / "logs"),
                    "sources_file": str(tmp_path / "sources.yaml"),
                    "research_areas_file": str(
                        Path(__file__).resolve().parents[2] / "config" / "research_areas.yaml"
                    ),
                    "reports_dir": str(tmp_path / "reports"),
                    "database_filename": "t.db",
                },
                "logging": {"level": "WARNING"},
                "http": {"respect_robots_txt": False, "min_request_interval_seconds": 0},
                "ai": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "sources.yaml").write_text("sources: []\n", encoding="utf-8")
    settings = load_settings(config_path=settings_path)
    result = generate_reports(
        settings,
        ReportOptions(formats=["markdown", "csv", "json"], output_dir=tmp_path / "out"),
    )
    assert result.opportunity_count == 1
    assert "markdown" in result.files and result.files["markdown"].is_file()
    assert "csv" in result.files and result.files["csv"].is_file()
    assert "json" in result.files and result.files["json"].is_file()
    data = json.loads(result.files["json"].read_text(encoding="utf-8"))
    assert data["count"] == 1
