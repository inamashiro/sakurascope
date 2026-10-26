"""Extraction pipeline persistence tests (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sakurascope.extraction.pipeline import process_snapshot
from sakurascope.models.domain import PageSnapshotRecord
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository

JA = (Path(__file__).resolve().parents[1] / "fixtures" / "extract_ja.txt").read_text(
    encoding="utf-8"
)


def test_pipeline_writes_opportunity_and_evidence(tmp_path: Path) -> None:
    db = create_database(tmp_path / "p3.db")
    snap = PageSnapshotRecord(
        snapshot_id="s1",
        source_id="mock-ja",
        original_url="https://fixtures.sakurascope.test/ja?utm_source=test",
        final_url="https://fixtures.sakurascope.test/ja",
        fetched_at=datetime.now(UTC),
        http_status=200,
        title="MOCK JA",
        extracted_text=JA,
        parse_status="ok",
        content_hash="hash-ja-1",
    )
    with db.session() as session:
        repo = Repository(session)
        repo.add_snapshot(snap)
        stats = process_snapshot(repo, snap)
        session.commit()
        assert stats.opportunities_created == 1
        assert stats.evidence_written >= 1
        opps = repo.list_opportunities()
        assert len(opps) == 1
        opp = opps[0]
        assert opp.application_deadline == "2026-05-15"
        assert opp.has_public_admission_language is True
        assert opp.review_status != "eligibility_confirmed"
        evidence = repo.list_evidence_for_entity("opportunity", opp.opportunity_id)
        assert evidence
        for ev in evidence:
            assert ev.quoted_text in JA or ev.quoted_text in "MOCK JA"

        # Second pass same URL → update, not duplicate create.
        snap2 = snap.model_copy(
            update={
                "snapshot_id": "s2",
                "content_hash": "hash-ja-2",
                "extracted_text": JA + "\n更新メモ",
            }
        )
        repo.add_snapshot(snap2)
        stats2 = process_snapshot(repo, snap2)
        session.commit()
        assert stats2.opportunities_updated == 1
        assert len(repo.list_opportunities()) == 1


def test_failed_snapshot_records_unreachable_change(tmp_path: Path) -> None:
    db = create_database(tmp_path / "fail.db")
    snap = PageSnapshotRecord(
        snapshot_id="fail1",
        source_id="mock",
        original_url="https://fixtures.sakurascope.test/missing",
        fetched_at=datetime.now(UTC),
        http_status=404,
        parse_status="failed",
        error_message="HTTP 404",
    )
    with db.session() as session:
        repo = Repository(session)
        repo.add_snapshot(snap)
        stats = process_snapshot(repo, snap)
        session.commit()
        assert stats.opportunities_created == 0
        events = repo.list_change_events()
        assert any(e.change_kind == "page_unreachable" for e in events)
        assert all("no admission" not in e.message.lower() for e in events)
