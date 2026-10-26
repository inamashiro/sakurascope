"""Build the active extractor from settings (rules default; AI opt-in)."""

from __future__ import annotations

import os

from sakurascope.config.settings import Settings
from sakurascope.extraction.ai.hybrid import HybridExtractor
from sakurascope.extraction.ai.openai_compatible import OpenAICompatibleProvider
from sakurascope.extraction.base import Extractor
from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.utils.logging import get_logger

logger = get_logger("extraction.factory")


def build_extractor(settings: Settings) -> Extractor:
    """
    Return a rules extractor unless AI is explicitly enabled AND an API key exists.

    Presence of a key alone does not enable AI.
    """
    if not settings.ai.enabled:
        return RuleBasedExtractor()

    api_key = settings.ai.api_key or os.environ.get("SAKURASCOPE_AI_API_KEY")
    if not api_key:
        logger.warning(
            "ai.enabled=true but no SAKURASCOPE_AI_API_KEY / ai.api_key; using rules only."
        )
        return RuleBasedExtractor()

    provider_name = (settings.ai.provider or "none").lower()
    if provider_name in {"none", "", "rules"}:
        logger.warning("ai.enabled=true but provider=%r; using rules only.", provider_name)
        return RuleBasedExtractor()

    if provider_name not in {"openai_compatible", "openai"}:
        logger.warning("Unsupported AI provider %r; using rules only.", provider_name)
        return RuleBasedExtractor()

    provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=settings.ai.base_url,
        model=settings.ai.model,
        timeout_seconds=settings.ai.timeout_seconds,
        temperature=settings.ai.temperature,
    )
    logger.info(
        "AI extraction enabled (provider=%s, model=%s).",
        provider.name,
        settings.ai.model,
    )
    return HybridExtractor(provider=provider, max_text_chars=settings.ai.max_text_chars)
