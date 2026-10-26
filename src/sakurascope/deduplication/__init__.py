"""URL normalization, candidate matching, and change detection."""

from sakurascope.deduplication.changes import ChangeKind, detect_snapshot_changes
from sakurascope.deduplication.matching import MatchDecision, match_opportunity_candidate
from sakurascope.deduplication.urls import normalize_url

__all__ = [
    "ChangeKind",
    "MatchDecision",
    "detect_snapshot_changes",
    "match_opportunity_candidate",
    "normalize_url",
]
