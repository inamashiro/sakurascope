"""PDF collector offline tests via httpx MockTransport."""

from __future__ import annotations

from pathlib import Path

import httpx
import pymupdf
import yaml

from sakurascope.collectors.service import CollectOptions, run_collect
from sakurascope.config.settings import load_settings
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository


def _pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "MOCK PDF admission guideline epidemiology")
    data = doc.tobytes()
    doc.close()
    return data


def test_collect_pdf_source(tmp_path: Path) -> None:
    pdf = _pdf_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=pdf,
            headers={"content-type": "application/pdf"},
        )

    sources = tmp_path / "sources.yaml"
    sources.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "source_id": "mock-pdf",
                        "source_name": "[MOCK] Admission PDF",
                        "source_url": "https://fixtures.sakurascope.test/admission.pdf",
                        "source_type": "public_pdf",
                        "collection_strategy": "pdf",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
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
                    "database_filename": "pdf.db",
                },
                "logging": {"level": "WARNING"},
                "http": {
                    "respect_robots_txt": False,
                    "min_request_interval_seconds": 0,
                    "max_retries": 0,
                },
                "ai": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    settings = load_settings(settings_path)
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    summary = run_collect(settings, CollectOptions(), http_client=client)
    assert summary.sources_succeeded == 1

    db = create_database(summary.database_path)  # type: ignore[arg-type]
    with db.session() as session:
        repo = Repository(session)
        snaps = repo.list_snapshots_for_source("mock-pdf")
        assert snaps
        assert snaps[0].parse_status == "ok"
        assert snaps[0].metadata_json.get("kind") == "pdf"
        assert snaps[0].metadata_json.get("ocr_used") is False
        assert "epidemiology" in (snaps[0].extracted_text or "").lower()
