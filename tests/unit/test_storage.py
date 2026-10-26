"""SQLite insert / query tests (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sakurascope.models.domain import PageSnapshotRecord, SourceConfig
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository


def test_sqlite_source_and_snapshot_roundtrip(tmp_path: Path) -> None:
    db = create_database(tmp_path / "test.db")
    with db.session() as session:
        repo = Repository(session)
        source = SourceConfig(
            source_id="mock-1",
            source_name="[MOCK] Storage Test",
            source_url="https://fixtures.sakurascope.test/page",
            source_type="other",
            collection_strategy="html",
            enabled=True,
            notes="simulated",
        )
        repo.upsert_source_from_config(source)
        snap = PageSnapshotRecord(
            snapshot_id="snap1",
            source_id="mock-1",
            original_url="https://fixtures.sakurascope.test/page",
            final_url="https://fixtures.sakurascope.test/page",
            fetched_at=datetime.now(UTC),
            http_status=200,
            content_hash="abc123",
            content_type="text/html",
            title="Mock",
            extracted_text="hello mock",
            parse_status="ok",
        )
        repo.add_snapshot(snap)
        session.commit()

        loaded = repo.get_source("mock-1")
        assert loaded is not None
        assert loaded.source_name.startswith("[MOCK]")
        snaps = repo.list_snapshots_for_source("mock-1")
        assert len(snaps) == 1
        assert snaps[0].extracted_text == "hello mock"
        assert repo.content_hash_exists("abc123") is True
