"""Incremental / retry-failed collect selection tests (offline MockTransport)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import yaml

from sakurascope.collectors.service import CollectOptions, run_collect
from sakurascope.config.settings import load_settings
from sakurascope.models.domain import SourceRecord

HTML = b"<html><head><title>MOCK</title></head><body><main>epidemiology public health</main></body></html>"


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("fail"):
        return httpx.Response(500, text="error")
    return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})


def _write_settings(tmp_path: Path, sources: list[dict]) -> Path:
    sources_path = tmp_path / "sources.yaml"
    sources_path.write_text(yaml.safe_dump({"sources": sources}), encoding="utf-8")
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "t", "environment": "test"},
                "paths": {
                    "data_dir": str(tmp_path / "data"),
                    "log_dir": str(tmp_path / "logs"),
                    "sources_file": str(sources_path),
                    "reports_dir": str(tmp_path / "reports"),
                    "research_areas_file": str(
                        Path(__file__).resolve().parents[2] / "config" / "research_areas.yaml"
                    ),
                    "database_filename": "inc.db",
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
    return settings_path


def test_incremental_skips_recent_success(tmp_path: Path) -> None:
    settings_path = _write_settings(
        tmp_path,
        [
            {
                "source_id": "ok-src",
                "source_name": "[MOCK] OK",
                "source_url": "https://fixtures.sakurascope.test/ok",
                "source_type": "other",
                "collection_strategy": "html",
                "enabled": True,
            }
        ],
    )
    settings = load_settings(settings_path)
    client = httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=True)

    first = run_collect(settings, CollectOptions(), http_client=client)
    assert first.sources_succeeded == 1

    second = run_collect(
        settings,
        CollectOptions(incremental=True, incremental_max_age_hours=24),
        http_client=client,
    )
    assert second.mode == "incremental"
    assert second.sources_attempted == 0
    assert second.sources_skipped == 1


def test_retry_failed_only_targets_failures(tmp_path: Path) -> None:
    settings_path = _write_settings(
        tmp_path,
        [
            {
                "source_id": "bad-src",
                "source_name": "[MOCK] BAD",
                "source_url": "https://fixtures.sakurascope.test/fail",
                "source_type": "other",
                "collection_strategy": "html",
                "enabled": True,
            },
            {
                "source_id": "good-src",
                "source_name": "[MOCK] GOOD",
                "source_url": "https://fixtures.sakurascope.test/ok",
                "source_type": "other",
                "collection_strategy": "html",
                "enabled": True,
            },
        ],
    )
    settings = load_settings(settings_path)
    client = httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=True)

    full = run_collect(settings, CollectOptions(), http_client=client)
    assert full.sources_failed == 1
    assert full.sources_succeeded == 1

    retry = run_collect(
        settings,
        CollectOptions(retry_failed_only=True),
        http_client=client,
    )
    assert retry.mode == "retry_failed"
    assert retry.sources_attempted == 1
    assert retry.failed_source_ids == ["bad-src"] or retry.sources_failed == 1


def test_needs_failure_helpers() -> None:
    from sakurascope.collectors.service import _needs_failure_retry, _recently_succeeded

    assert _needs_failure_retry(None) is True
    failed = SourceRecord(
        source_id="x",
        source_name="x",
        source_url="https://example.com",
        source_type="other",
        collection_strategy="html",
        last_error="boom",
        last_attempt_at=datetime.now(UTC),
    )
    assert _needs_failure_retry(failed) is True
    ok = SourceRecord(
        source_id="y",
        source_name="y",
        source_url="https://example.com",
        source_type="other",
        collection_strategy="html",
        last_success_at=datetime.now(UTC),
        last_error=None,
    )
    assert _recently_succeeded(ok, now=datetime.now(UTC), max_age_hours=24) is True
    old = SourceRecord(
        source_id="z",
        source_name="z",
        source_url="https://example.com",
        source_type="other",
        collection_strategy="html",
        last_success_at=datetime.now(UTC) - timedelta(hours=48),
    )
    assert _recently_succeeded(old, now=datetime.now(UTC), max_age_hours=24) is False
