"""Extraction evaluation metrics on MOCK fixtures (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from sakurascope.extraction.eval import EvalReport, evaluate_sample
from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.models.domain import PageSnapshotRecord

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_eval_metrics_are_computed_not_fabricated() -> None:
    expected_doc = yaml.safe_load((FIXTURES / "extract_expected.yaml").read_text(encoding="utf-8"))
    extractor = RuleBasedExtractor()
    report = EvalReport()
    for sample_id, spec in expected_doc.items():
        text = (FIXTURES / spec["fixture"]).read_text(encoding="utf-8")
        snap = PageSnapshotRecord(
            snapshot_id=sample_id,
            source_id=sample_id,
            original_url=f"https://fixtures.sakurascope.test/{sample_id}",
            fetched_at=datetime.now(UTC),
            title=text.splitlines()[0],
            extracted_text=text,
            parse_status="ok",
        )
        result = extractor.extract(snap)
        expect = dict(spec["expect"])
        if expect.get("application_deadline") is None:
            expect["application_deadline_null"] = True
        report.samples.append(
            evaluate_sample(
                sample_id,
                result,
                expect,
                source_text=f"{snap.title}\n{snap.extracted_text}",
            )
        )

    payload = report.as_dict()
    assert payload["sample_count"] == 3
    assert payload["failed_samples"] == 0
    assert payload["field_accuracy"] is not None
    assert payload["field_accuracy"] > 0.5
    assert payload["evidence_validity_rate"] == 1.0
    assert payload["false_fill_rate_on_unknown"] == 0.0
