"""Dashboard data-layer tests (no Streamlit runtime / no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from sakurascope.dashboard.data import load_dashboard_data
from sakurascope.filtering.classify import FilterCriteria
from sakurascope.models.domain import OpportunityRecord
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository


def test_load_dashboard_data_empty_and_with_opportunity(tmp_path: Path) -> None:
    sources = tmp_path / "sources.yaml"
    sources.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "source_id": "mock-dash",
                        "source_name": "[MOCK] Dashboard Source",
                        "source_url": "https://fixtures.sakurascope.test/dash",
                        "source_type": "other",
                        "collection_strategy": "html",
                        "enabled": False,
                        "notes": "MOCK only",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "t", "environment": "test"},
                "paths": {
                    "data_dir": str(tmp_path / "data"),
                    "log_dir": str(tmp_path / "logs"),
                    "sources_file": str(sources),
                    "reports_dir": str(tmp_path / "reports"),
                    "research_areas_file": str(
                        Path(__file__).resolve().parents[2] / "config" / "research_areas.yaml"
                    ),
                    "database_filename": "dash.db",
                },
                "logging": {"level": "WARNING"},
                "http": {"respect_robots_txt": False, "min_request_interval_seconds": 0},
                "ai": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    data = load_dashboard_data(settings)
    assert data.overview.opportunities == 0
    assert data.overview.sources_configured == 1
    assert data.sources_config[0].source_name.startswith("[MOCK]")

    db = create_database(tmp_path / "data" / "dash.db")
    with db.session() as session:
        repo = Repository(session)
        repo.upsert_opportunity(
            OpportunityRecord(
                opportunity_id="dash1",
                title="[MOCK] Public Health opportunity",
                research_area="Public Health",
                graduate_school_candidate="例示大学大学院",
                research_topic_may_match=True,
                has_public_admission_language=True,
                review_status="public_admission_info_found",
                official_source_url="https://fixtures.sakurascope.test/dash",
                first_seen_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
            )
        )
        session.commit()

    data2 = load_dashboard_data(settings)
    assert data2.overview.opportunities == 1
    assert data2.overview.with_admission_language == 1
    assert data2.institutions
    assert any("例示" in i.label or i.opportunity_count >= 1 for i in data2.institutions)

    filtered = load_dashboard_data(
        settings,
        criteria=FilterCriteria(research_areas=["Medical AI"]),
    )
    assert filtered.opportunities == []
