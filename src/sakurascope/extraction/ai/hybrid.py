"""Hybrid extractor: rules first, optional AI enrichment with hard guards."""

from __future__ import annotations

from sakurascope.deduplication.urls import normalize_url
from sakurascope.extraction.ai.openai_compatible import AiProviderError
from sakurascope.extraction.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from sakurascope.extraction.ai.provider import LlmProvider
from sakurascope.extraction.ai.validate import (
    InvalidAiJsonError,
    parse_ai_json,
    sanitize_ai_extraction,
)
from sakurascope.extraction.base import EvidenceDraft, ExtractionResult
from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.models.domain import PageSnapshotRecord, SourceConfig
from sakurascope.utils.logging import get_logger

logger = get_logger("extraction.ai.hybrid")


class HybridExtractor:
    """
    Always runs rule-based extraction.

    If an LlmProvider is supplied, attempts AI enrichment. On timeout / rate limit /
    invalid JSON / empty usable evidence, keeps the rules result and records the failure.
    """

    name = "hybrid"

    def __init__(
        self,
        provider: LlmProvider | None = None,
        *,
        max_text_chars: int = 12000,
        rules: RuleBasedExtractor | None = None,
    ) -> None:
        self.provider = provider
        self.max_text_chars = max_text_chars
        self.rules = rules or RuleBasedExtractor()

    def extract(
        self,
        snapshot: PageSnapshotRecord,
        source: SourceConfig | None = None,
    ) -> ExtractionResult:
        base = self.rules.extract(snapshot, source)
        url = normalize_url(snapshot.final_url or snapshot.original_url) or (
            snapshot.final_url or snapshot.original_url
        )
        base.official_source_url = url

        if self.provider is None:
            base.metadata = {**base.metadata, "ai_attempted": False}
            return base

        trusted = f"{snapshot.title or ''}\n{snapshot.extracted_text or ''}"
        try:
            response = self.provider.complete(
                system=SYSTEM_PROMPT,
                user=build_user_prompt(snapshot, max_chars=self.max_text_chars),
            )
            payload = parse_ai_json(response.content)
            ai_result = sanitize_ai_extraction(
                payload,
                source_text=trusted,
                snapshot_id=snapshot.snapshot_id,
                source_url=url,
            )
        except (AiProviderError, InvalidAiJsonError) as exc:
            logger.warning("AI extraction failed; keeping rules result: %s", exc)
            base.open_questions = [
                *base.open_questions,
                f"AI extraction failed ({exc}); rules-only result retained.",
            ]
            base.review_status = (
                "needs_review" if base.review_status == "insufficient_info" else base.review_status
            )
            base.metadata = {
                **base.metadata,
                "ai_attempted": True,
                "ai_failed": True,
                "ai_error": str(exc),
            }
            return base

        merged = _merge_results(base, ai_result, source_url=url)
        merged.metadata = {
            **merged.metadata,
            "ai_attempted": True,
            "ai_failed": False,
            "ai_model": getattr(response, "model", None),
            "ai_provider": getattr(self.provider, "name", "unknown"),
        }
        return merged


def _merge_results(
    rules: ExtractionResult,
    ai: ExtractionResult,
    *,
    source_url: str | None,
) -> ExtractionResult:
    """Prefer evidenced AI fields; never take official_source_url from AI."""

    def prefer(ai_val, rules_val):
        return ai_val if ai_val not in (None, "", []) else rules_val

    evidence: list[EvidenceDraft] = list(rules.evidence)
    seen = {(e.field_name, e.quoted_text) for e in evidence}
    for item in ai.evidence:
        key = (item.field_name, item.quoted_text)
        if key not in seen:
            evidence.append(item)
            seen.add(key)

    review = rules.review_status
    if ai.review_status == "public_admission_info_found":
        review = "public_admission_info_found"
    elif ai.review_status == "needs_review" and review == "insufficient_info":
        review = "needs_review"
    elif (
        ai.research_topic_may_match
        and review == "insufficient_info"
        and ai.review_status == "research_topic_may_match"
    ):
        review = "research_topic_may_match"

    areas = list(dict.fromkeys([*rules.research_areas, *ai.research_areas]))
    questions = list(dict.fromkeys([*rules.open_questions, *ai.open_questions]))

    return ExtractionResult(
        title=prefer(ai.title, rules.title),
        institution_name_candidate=prefer(
            ai.institution_name_candidate, rules.institution_name_candidate
        ),
        graduate_school_candidate=prefer(
            ai.graduate_school_candidate, rules.graduate_school_candidate
        ),
        opportunity_type=prefer(ai.opportunity_type, rules.opportunity_type),
        degree_level=prefer(ai.degree_level, rules.degree_level),
        research_areas=areas,
        eligibility_text=prefer(ai.eligibility_text, rules.eligibility_text),
        language_requirements=prefer(ai.language_requirements, rules.language_requirements),
        application_open_date=prefer(ai.application_open_date, rules.application_open_date),
        application_deadline=prefer(ai.application_deadline, rules.application_deadline),
        tuition_or_fee_text=prefer(ai.tuition_or_fee_text, rules.tuition_or_fee_text),
        funding_text=prefer(ai.funding_text, rules.funding_text),
        official_source_url=source_url or rules.official_source_url,
        has_public_admission_language=rules.has_public_admission_language
        or ai.has_public_admission_language,
        research_topic_may_match=rules.research_topic_may_match or ai.research_topic_may_match,
        review_status=review,
        open_questions=questions,
        evidence=evidence,
        metadata={"extractor": "hybrid"},
    )
