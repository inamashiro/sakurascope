"""Transparent opportunity filtering and topic relevance scoring."""

from sakurascope.filtering.areas import ResearchAreaConfig, load_research_areas
from sakurascope.filtering.classify import (
    FilterCriteria,
    FilteredOpportunity,
    classify_opportunity,
    filter_opportunities,
)

__all__ = [
    "FilterCriteria",
    "FilteredOpportunity",
    "ResearchAreaConfig",
    "classify_opportunity",
    "filter_opportunities",
    "load_research_areas",
]
