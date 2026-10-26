#!/usr/bin/env python3
"""Evaluate rule-based extraction on labeled MOCK fixtures.

Computes real metrics — does not invent scores.

Usage:
  python scripts/eval_extraction.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sakurascope.extraction.base import ExtractionResult  # noqa: E402
from sakurascope.extraction.eval import EvalReport, evaluate_sample  # noqa: E402
from sakurascope.extraction.rules import RuleBasedExtractor  # noqa: E402
from sakurascope.models.domain import PageSnapshotRecord  # noqa: E402


def main() -> int:
    fixtures = ROOT / "tests" / "fixtures"
    expected_doc = yaml.safe_load((fixtures / "extract_expected.yaml").read_text(encoding="utf-8"))
    extractor = RuleBasedExtractor()
    report = EvalReport()

    for sample_id, spec in expected_doc.items():
        text = (fixtures / spec["fixture"]).read_text(encoding="utf-8")
        snap = PageSnapshotRecord(
            snapshot_id=f"eval-{sample_id}",
            source_id=f"mock-{sample_id}",
            original_url=f"https://fixtures.sakurascope.test/{sample_id}",
            final_url=f"https://fixtures.sakurascope.test/{sample_id}",
            fetched_at=datetime.now(UTC),
            http_status=200,
            title=text.splitlines()[0].strip(),
            extracted_text=text,
            parse_status="ok",
        )
        source_text = f"{snap.title}\n{snap.extracted_text}"
        expect = dict(spec["expect"])
        if expect.get("application_deadline") is None:
            expect["application_deadline_null"] = True

        try:
            result = extractor.extract(snap)
            sample = evaluate_sample(
                sample_id, result, expect, source_text=source_text, failed=False
            )
        except Exception as exc:  # noqa: BLE001
            sample = evaluate_sample(
                sample_id,
                ExtractionResult(),
                expect,
                source_text=source_text,
                failed=True,
            )
            sample.notes.append(str(exc))
        report.samples.append(sample)

    payload = report.as_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["failed_samples"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
