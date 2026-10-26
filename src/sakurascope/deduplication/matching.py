"""Opportunity candidate matching (never claim identity from title alone)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from sakurascope.deduplication.urls import normalize_url
from sakurascope.utils.hashing import normalize_text

MatchKind = Literal["same_url", "same_content_hash", "suspected_duplicate", "new"]


@dataclass(frozen=True)
class MatchDecision:
    kind: MatchKind
    existing_opportunity_id: str | None = None
    reason: str = ""


def _title_tokens(title: str | None) -> set[str]:
    if not title:
        return set()
    text = normalize_text(title).lower()
    parts = re.split(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", text, flags=re.UNICODE)
    return {p for p in parts if len(p) >= 2}


def title_similarity(a: str | None, b: str | None) -> float:
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match_opportunity_candidate(
    *,
    official_source_url: str | None,
    title: str | None,
    content_hash: str | None,
    existing: list[dict],
) -> MatchDecision:
    """
    Decide how a new candidate relates to existing opportunities.

    `existing` items: opportunity_id, official_source_url, title, content_hash

    Rules:
    - Same normalized URL → same record (update)
    - Same content hash + similar title → same record
    - High title overlap but different URL → suspected_duplicate (needs review)
    - Otherwise → new
    """
    norm = normalize_url(official_source_url)
    for row in existing:
        if norm and normalize_url(row.get("official_source_url")) == norm:
            return MatchDecision(
                kind="same_url",
                existing_opportunity_id=row["opportunity_id"],
                reason="Normalized official_source_url matches",
            )

    if content_hash:
        for row in existing:
            if row.get("content_hash") == content_hash:
                sim = title_similarity(title, row.get("title"))
                if sim >= 0.4 or not title or not row.get("title"):
                    return MatchDecision(
                        kind="same_content_hash",
                        existing_opportunity_id=row["opportunity_id"],
                        reason="Identical content hash",
                    )

    if title:
        for row in existing:
            sim = title_similarity(title, row.get("title"))
            other_norm = normalize_url(row.get("official_source_url"))
            if sim >= 0.75 and norm and other_norm and norm != other_norm:
                return MatchDecision(
                    kind="suspected_duplicate",
                    existing_opportunity_id=row["opportunity_id"],
                    reason=f"Similar title (score={sim:.2f}) but different URL — needs human review",
                )

    return MatchDecision(kind="new", reason="No confident match")
