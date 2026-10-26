"""AI extraction guards — no real network / no real API key."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sakurascope.config.settings import Settings
from sakurascope.extraction.ai.hybrid import HybridExtractor
from sakurascope.extraction.ai.provider import LlmResponse
from sakurascope.extraction.ai.redact import redact_for_model
from sakurascope.extraction.ai.validate import (
    InvalidAiJsonError,
    parse_ai_json,
    sanitize_ai_extraction,
)
from sakurascope.extraction.factory import build_extractor
from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.models.domain import PageSnapshotRecord

JA = (Path(__file__).resolve().parents[1] / "fixtures" / "extract_ja.txt").read_text(
    encoding="utf-8"
)


class FakeProvider:
    name = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def complete(self, *, system: str, user: str) -> LlmResponse:
        self.calls += 1
        return LlmResponse(content=self.content, model="fake-model")


def _snap(text: str = JA) -> PageSnapshotRecord:
    return PageSnapshotRecord(
        snapshot_id="ai1",
        source_id="mock",
        original_url="https://fixtures.sakurascope.test/ja",
        final_url="https://fixtures.sakurascope.test/ja",
        fetched_at=datetime.now(UTC),
        title=text.splitlines()[0],
        extracted_text=text,
        parse_status="ok",
        http_status=200,
    )


def test_factory_defaults_to_rules() -> None:
    settings = Settings()
    assert settings.ai.enabled is False
    extractor = build_extractor(settings)
    assert isinstance(extractor, RuleBasedExtractor)


def test_factory_enabled_without_key_falls_back_to_rules() -> None:
    settings = Settings()
    settings.ai.enabled = True
    settings.ai.provider = "openai_compatible"
    settings.ai.api_key = None
    extractor = build_extractor(settings)
    assert isinstance(extractor, RuleBasedExtractor)


def test_invalid_ai_json_keeps_rules_result() -> None:
    provider = FakeProvider("this is not json {{{")
    extractor = HybridExtractor(provider=provider)
    result = extractor.extract(_snap())
    assert provider.calls == 1
    assert result.metadata.get("ai_failed") is True
    assert any("AI extraction failed" in q for q in result.open_questions)
    # Rules should still find admission language in JA fixture.
    assert result.has_public_admission_language is True
    assert result.official_source_url is not None


def test_ai_fabricated_evidence_rejected() -> None:
    # Quote is not in the page; deadline must not be accepted from AI alone.
    payload = {
        "title": "Fake",
        "application_deadline": "2099-01-01",
        "has_public_admission_language": True,
        "research_topic_may_match": True,
        "research_areas": ["Public Health"],
        "review_status": "eligibility_confirmed",
        "open_questions": [],
        "evidence": [
            {
                "field_name": "application_deadline",
                "quoted_text": "THIS QUOTE DOES NOT EXIST IN SOURCE",
            }
        ],
    }
    import json

    provider = FakeProvider(json.dumps(payload))
    result = HybridExtractor(provider=provider).extract(_snap())
    # Fabricated AI deadline evidence rejected; rules may still set a real deadline.
    if result.application_deadline:
        assert result.application_deadline != "2099-01-01"
    assert result.review_status != "eligibility_confirmed"
    assert result.official_source_url == "https://fixtures.sakurascope.test/ja"


def test_parse_ai_json_raises_on_garbage() -> None:
    try:
        parse_ai_json("{not-json")
        raise AssertionError("expected InvalidAiJsonError")
    except InvalidAiJsonError:
        pass


def test_sanitize_drops_bad_quotes_and_url() -> None:
    from sakurascope.extraction.ai.schema import AiExtractionPayload

    payload = AiExtractionPayload(
        title="Hello",
        application_deadline="2026-05-15",
        evidence=[{"field_name": "title", "quoted_text": "not in text"}],
        review_status="eligibility_confirmed",
    )
    result = sanitize_ai_extraction(payload, source_text="completely different")
    assert result.title is None
    assert result.application_deadline is None
    assert result.evidence == []
    assert result.official_source_url is None
    assert result.review_status != "eligibility_confirmed"


def test_redact_email_and_phone() -> None:
    text = "Contact alice@example.com or +81-3-1234-5678 for details. 募集要項"
    out = redact_for_model(text)
    assert "alice@example.com" not in out
    assert "[REDACTED_EMAIL]" in out
    assert "募集要項" in out


def test_valid_ai_quote_merges() -> None:
    import json

    quote = "締切：2026年5月15日"
    assert quote in JA
    payload = {
        "application_deadline": "2026-05-15",
        "has_public_admission_language": True,
        "research_areas": ["Epidemiology"],
        "review_status": "public_admission_info_found",
        "evidence": [
            {"field_name": "application_deadline", "quoted_text": quote},
            {"field_name": "research_areas", "quoted_text": "疫学"},
        ],
    }
    result = HybridExtractor(provider=FakeProvider(json.dumps(payload))).extract(_snap())
    assert result.application_deadline == "2026-05-15"
    assert any(e.extraction_method == "ai" for e in result.evidence)
    assert result.metadata.get("ai_failed") is False
