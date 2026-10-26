"""Structured extraction from page snapshots (rules-first; optional AI)."""

from sakurascope.extraction.base import ExtractionResult, Extractor
from sakurascope.extraction.factory import build_extractor
from sakurascope.extraction.rules import RuleBasedExtractor

__all__ = ["ExtractionResult", "Extractor", "RuleBasedExtractor", "build_extractor"]
