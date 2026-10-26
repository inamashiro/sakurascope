"""Deterministic rule-based extractor (default; no API key required)."""

from __future__ import annotations

import re

from sakurascope.deduplication.urls import normalize_url
from sakurascope.extraction.base import EvidenceDraft, ExtractionResult
from sakurascope.extraction.dates import extract_dates
from sakurascope.extraction.keywords import (
    ADMISSION_KEYWORDS,
    DEGREE_KEYWORDS,
    GRADUATE_SCHOOL_PATTERNS,
    INSTITUTION_PATTERNS,
    RESEARCH_AREA_KEYWORDS,
)
from sakurascope.models.domain import PageSnapshotRecord, SourceConfig


class RuleBasedExtractor:
    """Extract only fields supported by literal text evidence."""

    name = "rules"

    def extract(
        self,
        snapshot: PageSnapshotRecord,
        source: SourceConfig | None = None,
    ) -> ExtractionResult:
        text = snapshot.extracted_text or ""
        title = snapshot.title
        url = snapshot.final_url or snapshot.original_url
        result = ExtractionResult(
            title=title,
            official_source_url=normalize_url(url) or url,
        )

        if title:
            result.evidence.append(
                EvidenceDraft(
                    field_name="title",
                    quoted_text=title,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )

        if not text and not title:
            result.review_status = "insufficient_info"
            result.open_questions.append("No extractable text in snapshot.")
            return result

        search_blob = f"{title or ''}\n{text}"

        # Research areas (topic may match — never equals admissions).
        areas: list[str] = []
        for label, keywords in RESEARCH_AREA_KEYWORDS.items():
            for kw in keywords:
                hit = _find_keyword(search_blob, kw)
                if hit:
                    areas.append(label)
                    result.evidence.append(
                        EvidenceDraft(
                            field_name="research_area",
                            quoted_text=hit,
                            source_url=url,
                            snapshot_id=snapshot.snapshot_id,
                        )
                    )
                    break
        result.research_areas = areas
        result.research_topic_may_match = bool(areas)

        # Admission language presence.
        admission_hits: list[str] = []
        for kw in ADMISSION_KEYWORDS:
            hit = _find_keyword(search_blob, kw)
            if hit:
                admission_hits.append(hit)
        result.has_public_admission_language = bool(admission_hits)
        if admission_hits:
            result.opportunity_type = "public_admission_notice_candidate"
            result.evidence.append(
                EvidenceDraft(
                    field_name="opportunity_type",
                    quoted_text=admission_hits[0],
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )
            # Keep a short eligibility snippet only when admission language exists.
            result.eligibility_text = _snippet_around(search_blob, admission_hits[0], radius=120)
            if result.eligibility_text:
                result.evidence.append(
                    EvidenceDraft(
                        field_name="eligibility_text",
                        quoted_text=result.eligibility_text,
                        source_url=url,
                        snapshot_id=snapshot.snapshot_id,
                    )
                )

        # Degree level candidates.
        for level, keywords in DEGREE_KEYWORDS.items():
            for kw in keywords:
                hit = _find_keyword(search_blob, kw)
                if hit:
                    result.degree_level = level
                    result.evidence.append(
                        EvidenceDraft(
                            field_name="degree_level",
                            quoted_text=hit,
                            source_url=url,
                            snapshot_id=snapshot.snapshot_id,
                        )
                    )
                    break
            if result.degree_level:
                break

        # Institution / graduate school candidates (first regex hit only).
        inst = _first_regex_hit(search_blob, INSTITUTION_PATTERNS)
        if inst:
            result.institution_name_candidate = inst
            result.evidence.append(
                EvidenceDraft(
                    field_name="institution_name_candidate",
                    quoted_text=inst,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )
        grad = _first_regex_hit(search_blob, GRADUATE_SCHOOL_PATTERNS)
        if grad:
            result.graduate_school_candidate = grad
            result.evidence.append(
                EvidenceDraft(
                    field_name="graduate_school_candidate",
                    quoted_text=grad,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )

        # Dates — only assign deadline when context suggests it.
        dates = extract_dates(search_blob)
        deadline_dates = [d for d in dates if d.likely_deadline and d.iso_date]
        if deadline_dates:
            # Prefer the last deadline-like date in document order.
            chosen = deadline_dates[-1]
            result.application_deadline = chosen.iso_date
            result.evidence.append(
                EvidenceDraft(
                    field_name="application_deadline",
                    quoted_text=chosen.quoted_text,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )
        elif dates:
            # Dates exist but no deadline context → do not auto-fill deadline.
            result.open_questions.append(
                "Dates found without clear deadline context; deadline left unset."
            )
            result.evidence.append(
                EvidenceDraft(
                    field_name="date_mention",
                    quoted_text=dates[0].quoted_text,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                    verification_status="needs_review",
                )
            )

        # Language requirements (explicit only).
        lang_hit = _find_any(
            search_blob,
            [
                "日本語能力試験",
                "JLPT",
                "TOEFL",
                "IELTS",
                "英语要求",
                "英語要件",
                "language requirement",
            ],
        )
        if lang_hit:
            result.language_requirements = _snippet_around(search_blob, lang_hit, radius=80)
            result.evidence.append(
                EvidenceDraft(
                    field_name="language_requirements",
                    quoted_text=result.language_requirements or lang_hit,
                    source_url=url,
                    snapshot_id=snapshot.snapshot_id,
                )
            )

        # Review status — never upgrade topic match into confirmed eligibility.
        result.review_status = _decide_review_status(result)
        result.open_questions.extend(_default_open_questions(result))
        result.metadata = {
            "extractor": self.name,
            "source_id": source.source_id if source else snapshot.source_id,
            "admission_keyword_hits": len(admission_hits),
            "date_mentions": len(dates),
        }

        # Hard guard: drop any evidence quote not present in source text/title.
        trusted = search_blob
        result.evidence = [e for e in result.evidence if e.quoted_text and e.quoted_text in trusted]
        return result


def _decide_review_status(result: ExtractionResult) -> str:
    if result.has_public_admission_language and result.application_deadline:
        return "public_admission_info_found"
    if result.has_public_admission_language:
        return "public_admission_info_found"
    if result.research_topic_may_match:
        return "research_topic_may_match"
    if result.title or result.institution_name_candidate:
        return "insufficient_info"
    return "insufficient_info"


def _default_open_questions(result: ExtractionResult) -> list[str]:
    questions: list[str] = []
    if result.research_topic_may_match and not result.has_public_admission_language:
        questions.append(
            "Research keywords matched, but no public admission language was found. "
            "Do not treat this as an open call."
        )
    if result.has_public_admission_language and not result.application_deadline:
        questions.append(
            "Public admission language found; application dates still need verification."
        )
    questions.append(
        "Eligibility is not confirmed until checked against the official page by a human."
    )
    return questions


def _find_keyword(text: str, keyword: str) -> str | None:
    if not keyword:
        return None
    # Case-insensitive for ASCII; exact for CJK.
    if re.fullmatch(r"[A-Za-z0-9 .'\-]+", keyword):
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        match = pattern.search(text)
        return match.group(0) if match else None
    return keyword if keyword in text else None


def _find_any(text: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        hit = _find_keyword(text, kw)
        if hit:
            return hit
    return None


def _first_regex_hit(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _snippet_around(text: str, needle: str, *, radius: int = 100) -> str | None:
    idx = text.find(needle)
    if idx < 0:
        # Case-insensitive fallback for ASCII needles.
        lower = text.lower()
        n = needle.lower()
        idx = lower.find(n)
        if idx < 0:
            return None
        needle_len = len(needle)
    else:
        needle_len = len(needle)
    left = max(0, idx - radius)
    right = min(len(text), idx + needle_len + radius)
    snippet = text[left:right].replace("\n", " ")
    return re.sub(r"\s+", " ", snippet).strip()
