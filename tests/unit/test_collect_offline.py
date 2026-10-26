"""End-to-end collect against httpx MockTransport (no real network)."""

from __future__ import annotations

from pathlib import Path

import httpx
import yaml

from sakurascope.collectors.service import CollectOptions, run_collect
from sakurascope.config.settings import load_settings
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HTML = (FIXTURES / "sample_html.html").read_bytes()
FEED = (FIXTURES / "sample_feed.xml").read_bytes()


def _mock_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.rstrip("/").endswith("forbidden"):
        return httpx.Response(403, text="Forbidden")
    if path.endswith("feed.xml"):
        return httpx.Response(200, content=FEED, headers={"content-type": "application/rss+xml"})
    if "public-health" in path:
        return httpx.Response(
            200, content=HTML, headers={"content-type": "text/html; charset=utf-8"}
        )
    return httpx.Response(404, text="not found")


def test_collect_html_rss_and_failure(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.yaml"
    sources_path = tmp_path / "sources.yaml"
    sources_path.write_text(
        (FIXTURES / "sources_mock.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    settings_doc = {
        "app": {"name": "SakuraScopeTest", "environment": "test"},
        "paths": {
            "data_dir": str(tmp_path / "data"),
            "log_dir": str(tmp_path / "logs"),
            "sources_file": str(sources_path),
            "database_filename": "collect_test.db",
        },
        "logging": {"level": "WARNING"},
        "http": {
            "user_agent": "SakuraScope-Test/0.2",
            "timeout_seconds": 5,
            "max_retries": 0,
            "min_request_interval_seconds": 0.0,
            "respect_robots_txt": False,
        },
        "ai": {"enabled": False, "provider": "none"},
    }
    settings_path.write_text(yaml.safe_dump(settings_doc), encoding="utf-8")
    settings = load_settings(config_path=settings_path)

    transport = httpx.MockTransport(_mock_handler)
    client = httpx.Client(transport=transport, follow_redirects=True)

    summary = run_collect(settings, CollectOptions(), http_client=client)
    assert summary.sources_attempted == 3
    assert summary.sources_succeeded == 2
    assert summary.sources_failed == 1
    assert summary.pages_processed >= 3  # html + feed + entries + failure
    assert summary.opportunities_created >= 1
    assert summary.evidence_written >= 1
    assert not summary.ok

    db = create_database(summary.database_path)  # type: ignore[arg-type]
    with db.session() as session:
        repo = Repository(session)
        html_source = repo.get_source("mock-html-public-health")
        assert html_source is not None
        assert html_source.last_success_at is not None
        assert html_source.last_http_status == 200

        forbidden = repo.get_source("mock-html-forbidden")
        assert forbidden is not None
        assert forbidden.last_error is not None
        assert forbidden.last_success_at is None

        snaps = repo.list_snapshots_for_source("mock-html-public-health")
        assert snaps
        assert snaps[0].parse_status == "ok"
        assert snaps[0].title is not None
        assert "MOCK" in (snaps[0].title or "")
        # Fetch failure must not be narrated as "no admissions".
        fail_snaps = repo.list_snapshots_for_source("mock-html-forbidden")
        assert fail_snaps[0].parse_status == "failed"
        assert "no admission" not in (fail_snaps[0].error_message or "").lower()

        opps = repo.list_opportunities()
        assert opps
        assert all(o.review_status != "eligibility_confirmed" for o in opps)


def test_collect_duplicate_content_hash(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.yaml"
    sources_path = tmp_path / "sources.yaml"
    sources_doc = {
        "sources": [
            {
                "source_id": "mock-html-a",
                "source_name": "[MOCK] A",
                "source_url": "https://fixtures.sakurascope.test/public-health/",
                "source_type": "other",
                "collection_strategy": "html",
                "enabled": True,
            },
            {
                "source_id": "mock-html-b",
                "source_name": "[MOCK] B",
                "source_url": "https://fixtures.sakurascope.test/public-health/",
                "source_type": "other",
                "collection_strategy": "html",
                "enabled": True,
            },
        ]
    }
    sources_path.write_text(yaml.safe_dump(sources_doc), encoding="utf-8")
    settings_doc = {
        "app": {"name": "SakuraScopeTest", "environment": "test"},
        "paths": {
            "data_dir": str(tmp_path / "data"),
            "log_dir": str(tmp_path / "logs"),
            "sources_file": str(sources_path),
            "database_filename": "dup.db",
        },
        "logging": {"level": "WARNING"},
        "http": {
            "user_agent": "SakuraScope-Test/0.2",
            "max_retries": 0,
            "min_request_interval_seconds": 0.0,
            "respect_robots_txt": False,
        },
        "ai": {"enabled": False},
    }
    settings_path.write_text(yaml.safe_dump(settings_doc), encoding="utf-8")
    settings = load_settings(config_path=settings_path)
    client = httpx.Client(transport=httpx.MockTransport(_mock_handler), follow_redirects=True)
    summary = run_collect(settings, CollectOptions(), http_client=client)
    assert summary.duplicates_found >= 1
