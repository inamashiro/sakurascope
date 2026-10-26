"""Dedup matching and change detection tests (no network)."""

from __future__ import annotations

from sakurascope.deduplication.changes import detect_snapshot_changes
from sakurascope.deduplication.matching import match_opportunity_candidate


def test_same_url_match() -> None:
    existing = [
        {
            "opportunity_id": "opp1",
            "official_source_url": "https://example.com/a?utm_source=x",
            "title": "Notice",
            "content_hash": "h1",
        }
    ]
    decision = match_opportunity_candidate(
        official_source_url="https://example.com/a",
        title="Notice",
        content_hash="h2",
        existing=existing,
    )
    assert decision.kind == "same_url"
    assert decision.existing_opportunity_id == "opp1"


def test_suspected_duplicate_on_similar_title_different_url() -> None:
    existing = [
        {
            "opportunity_id": "opp1",
            "official_source_url": "https://example.com/page-a",
            "title": "Graduate School of Medicine Public Health Admission Guidelines 2026",
            "content_hash": "h1",
        }
    ]
    decision = match_opportunity_candidate(
        official_source_url="https://other.example.com/page-b",
        title="Graduate School of Medicine Public Health Admission Guidelines 2026",
        content_hash="h2",
        existing=existing,
    )
    assert decision.kind == "suspected_duplicate"


def test_page_unreachable_is_not_admission_closed() -> None:
    events = detect_snapshot_changes(
        previous_hash="abc",
        current_hash=None,
        previous_deadline="2026-05-01",
        current_deadline=None,
        parse_ok=False,
        http_status=404,
        is_first_sighting=False,
    )
    assert any(e.change_kind == "page_unreachable" for e in events)
    assert all(
        "closed" not in e.message.lower() or "not proof" in e.message.lower() for e in events
    )


def test_content_and_deadline_change_events() -> None:
    events = detect_snapshot_changes(
        previous_hash="aaa",
        current_hash="bbb",
        previous_deadline="2026-05-01",
        current_deadline="2026-06-01",
        parse_ok=True,
        http_status=200,
        is_first_sighting=False,
    )
    kinds = {e.change_kind for e in events}
    assert "content_updated" in kinds
    assert "application_date_maybe_changed" in kinds
