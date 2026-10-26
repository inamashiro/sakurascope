"""Rule-based extraction tests with JA/EN/ZH MOCK fixtures (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.models.domain import PageSnapshotRecord

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = yaml.safe_load((FIXTURES / "extract_expected.yaml").read_text(encoding="utf-8"))


def _snapshot_from_file(name: str, *, lang: str) -> PageSnapshotRecord:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    first_line = text.splitlines()[0].strip()
    return PageSnapshotRecord(
        snapshot_id=f"snap-{lang}",
        source_id=f"mock-{lang}",
        original_url=f"https://fixtures.sakurascope.test/{lang}",
        final_url=f"https://fixtures.sakurascope.test/{lang}",
        fetched_at=datetime.now(UTC),
        http_status=200,
        title=first_line,
        extracted_text=text,
        parse_status="ok",
        content_hash="dummy",
    )


def test_multilingual_extraction_matches_oracle() -> None:
    extractor = RuleBasedExtractor()
    for lang, spec in EXPECTED.items():
        snap = _snapshot_from_file(spec["fixture"], lang=lang)
        result = extractor.extract(snap)
        expect = spec["expect"]

        assert result.research_topic_may_match is expect["research_topic_may_match"], lang
        assert result.has_public_admission_language is expect["has_public_admission_language"], lang
        for area in expect["research_areas_include"]:
            assert area in result.research_areas, f"{lang}: missing {area}"
        assert result.application_deadline == expect["application_deadline"], lang
        assert result.review_status == expect["review_status"], lang
        assert result.review_status != "eligibility_confirmed"
        # Every evidence quote must appear in the source text.
        blob = f"{snap.title}\n{snap.extracted_text}"
        for ev in result.evidence:
            assert ev.quoted_text in blob, f"{lang}: fabricated evidence {ev.field_name}"
        if expect.get("institution_name_contains"):
            assert result.institution_name_candidate is not None
            assert expect["institution_name_contains"] in result.institution_name_candidate


def test_date_without_deadline_context_not_auto_filled() -> None:
    text = "Lab seminar on 2026-03-01. No application information."
    snap = PageSnapshotRecord(
        snapshot_id="snap-date",
        source_id="mock",
        original_url="https://fixtures.sakurascope.test/date",
        fetched_at=datetime.now(UTC),
        title="Seminar",
        extracted_text=text,
        parse_status="ok",
    )
    result = RuleBasedExtractor().extract(snap)
    assert result.application_deadline is None
    assert result.has_public_admission_language is False
