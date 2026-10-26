"""Evaluate extraction results against labeled fixtures (real metrics, no fakes)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sakurascope.extraction.base import ExtractionResult

# Fields compared for accuracy / coverage when expected value is not null.
SCALAR_FIELDS = [
    "application_deadline",
    "degree_level",
    "review_status",
]


@dataclass
class EvalSampleResult:
    sample_id: str
    field_hits: int = 0
    field_expected: int = 0
    field_predicted_for_expected: int = 0
    evidence_valid: int = 0
    evidence_total: int = 0
    false_fills: int = 0
    unknown_expected_nulls: int = 0
    failed: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    samples: list[EvalSampleResult] = field(default_factory=list)

    @property
    def field_accuracy(self) -> float:
        expected = sum(s.field_expected for s in self.samples)
        hits = sum(s.field_hits for s in self.samples)
        return hits / expected if expected else 0.0

    @property
    def field_coverage(self) -> float:
        """Share of expected non-null fields that the extractor filled (match or not)."""
        expected = sum(s.field_expected for s in self.samples)
        predicted = sum(s.field_predicted_for_expected for s in self.samples)
        return predicted / expected if expected else 0.0

    @property
    def evidence_validity_rate(self) -> float:
        total = sum(s.evidence_total for s in self.samples)
        valid = sum(s.evidence_valid for s in self.samples)
        return valid / total if total else 1.0

    @property
    def false_fill_rate(self) -> float:
        unknown = sum(s.unknown_expected_nulls for s in self.samples)
        false_fills = sum(s.false_fills for s in self.samples)
        return false_fills / unknown if unknown else 0.0

    @property
    def failed_samples(self) -> int:
        return sum(1 for s in self.samples if s.failed)

    def as_dict(self) -> dict[str, Any]:
        expected = sum(s.field_expected for s in self.samples)
        hits = sum(s.field_hits for s in self.samples)
        predicted = sum(s.field_predicted_for_expected for s in self.samples)
        return {
            "sample_count": len(self.samples),
            "failed_samples": self.failed_samples,
            "field_accuracy": round(hits / expected, 4) if expected else None,
            "field_coverage": round(predicted / expected, 4) if expected else None,
            "evidence_validity_rate": round(self.evidence_validity_rate, 4),
            "false_fill_rate_on_unknown": round(self.false_fill_rate, 4),
            "samples": [
                {
                    "sample_id": s.sample_id,
                    "failed": s.failed,
                    "field_hits": s.field_hits,
                    "field_expected": s.field_expected,
                    "evidence_valid": s.evidence_valid,
                    "evidence_total": s.evidence_total,
                    "false_fills": s.false_fills,
                    "notes": s.notes,
                }
                for s in self.samples
            ],
        }


def evaluate_sample(
    sample_id: str,
    result: ExtractionResult,
    expected: dict[str, Any],
    *,
    source_text: str,
    failed: bool = False,
) -> EvalSampleResult:
    """
    Compare one ExtractionResult to an expected dict.

    expected may include:
      application_deadline, review_status, degree_level,
      research_areas_include (list),
      has_public_admission_language (bool),
      application_deadline_null (bool) — if true, filling a deadline counts as false_fill
    """
    out = EvalSampleResult(sample_id=sample_id, failed=failed)
    if failed:
        out.notes.append("Extractor raised or returned hard failure")
        return out

    for field_name in SCALAR_FIELDS:
        if field_name not in expected or expected[field_name] is None:
            continue
        out.field_expected += 1
        actual = getattr(result, field_name, None)
        if actual is not None and actual != "":
            out.field_predicted_for_expected += 1
        if actual == expected[field_name]:
            out.field_hits += 1

    if "research_areas_include" in expected:
        wanted = list(expected["research_areas_include"])
        out.field_expected += len(wanted)
        for area in wanted:
            if area in result.research_areas:
                out.field_hits += 1
                out.field_predicted_for_expected += 1

    if "has_public_admission_language" in expected:
        out.field_expected += 1
        out.field_predicted_for_expected += 1
        if result.has_public_admission_language is bool(expected["has_public_admission_language"]):
            out.field_hits += 1

    # Unknown/null expectations: measuring wrongful fills.
    if expected.get("application_deadline_null") or (
        "application_deadline" in expected and expected.get("application_deadline") is None
    ):
        out.unknown_expected_nulls += 1
        if result.application_deadline:
            out.false_fills += 1
            out.notes.append("application_deadline filled but expected null/unknown")

    if (
        expected.get("must_not_claim_eligibility_confirmed", True)
        and result.review_status == "eligibility_confirmed"
    ):
        out.unknown_expected_nulls += 1
        out.false_fills += 1
        out.notes.append("eligibility_confirmed incorrectly set")

    for ev in result.evidence:
        out.evidence_total += 1
        if ev.quoted_text and ev.quoted_text in source_text:
            out.evidence_valid += 1

    return out
