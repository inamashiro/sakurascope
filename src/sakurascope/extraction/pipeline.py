"""Apply extraction + dedupe + change events to a stored snapshot."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sakurascope.deduplication.changes import ChangeEventDraft, detect_snapshot_changes
from sakurascope.deduplication.matching import match_opportunity_candidate
from sakurascope.deduplication.urls import normalize_url
from sakurascope.extraction.base import ExtractionResult, Extractor
from sakurascope.extraction.rules import RuleBasedExtractor
from sakurascope.models.domain import (
    ChangeEventRecord,
    EvidenceRecord,
    OpportunityRecord,
    PageSnapshotRecord,
    SourceConfig,
)
from sakurascope.storage.repository import Repository
from sakurascope.utils.hashing import content_hash


@dataclass
class ProcessStats:
    opportunities_created: int = 0
    opportunities_updated: int = 0
    evidence_written: int = 0
    change_events: int = 0
    suspected_duplicates: int = 0
    notes: list[str] = field(default_factory=list)


def process_snapshot(
    repo: Repository,
    snapshot: PageSnapshotRecord,
    source: SourceConfig | None = None,
    *,
    extractor: Extractor | None = None,
) -> ProcessStats:
    """Extract structured fields from a snapshot and upsert opportunity/evidence."""
    extractor = extractor or RuleBasedExtractor()
    stats = ProcessStats()
    now = datetime.now(UTC)
    norm_url = normalize_url(snapshot.final_url or snapshot.original_url)

    previous = (
        repo.get_latest_successful_snapshot_by_normalized_url(
            norm_url, exclude_snapshot_id=snapshot.snapshot_id
        )
        if norm_url
        else None
    )

    parse_ok = snapshot.parse_status in {"ok", "partial"} and bool(
        snapshot.extracted_text or snapshot.title
    )

    if not parse_ok:
        drafts = detect_snapshot_changes(
            previous_hash=previous.content_hash if previous else None,
            current_hash=snapshot.content_hash,
            previous_deadline=None,
            current_deadline=None,
            parse_ok=False,
            http_status=snapshot.http_status,
            is_first_sighting=previous is None,
        )
        for draft in drafts:
            _store_change(repo, draft, snapshot, entity_id=None)
            stats.change_events += 1
        return stats

    extraction = extractor.extract(snapshot, source)
    # Evidence must come from the actual snapshot text.
    trusted = f"{snapshot.title or ''}\n{snapshot.extracted_text or ''}"
    if not extraction.evidence_matches_source(trusted):
        extraction.evidence = [
            e for e in extraction.evidence if e.quoted_text and e.quoted_text in trusted
        ]
        extraction.open_questions.append(
            "Some evidence quotes were dropped because they were not found in source text."
        )
        extraction.review_status = "needs_review"

    existing_rows = repo.list_opportunity_match_rows()
    fingerprint = _fingerprint(extraction, snapshot)
    decision = match_opportunity_candidate(
        official_source_url=extraction.official_source_url,
        title=extraction.title,
        content_hash=fingerprint,
        existing=existing_rows,
    )

    previous_deadline = None
    if decision.existing_opportunity_id:
        existing_opp = repo.get_opportunity(decision.existing_opportunity_id)
        previous_deadline = existing_opp.application_deadline if existing_opp else None

    if decision.kind in {"same_url", "same_content_hash"} and decision.existing_opportunity_id:
        opp = _merge_opportunity(
            repo.get_opportunity(decision.existing_opportunity_id),
            extraction,
            snapshot,
            fingerprint,
            now,
        )
        repo.upsert_opportunity(opp)
        stats.opportunities_updated += 1
        opportunity_id = opp.opportunity_id
    elif decision.kind == "suspected_duplicate":
        opp = _new_opportunity(extraction, snapshot, fingerprint, now)
        opp.review_status = "needs_review"
        questions = [opp.open_questions] if opp.open_questions else []
        questions.append(decision.reason)
        if decision.existing_opportunity_id:
            questions.append(
                f"Suspected duplicate of opportunity_id={decision.existing_opportunity_id}"
            )
        opp.open_questions = " | ".join(q for q in questions if q)
        repo.upsert_opportunity(opp)
        stats.opportunities_created += 1
        stats.suspected_duplicates += 1
        opportunity_id = opp.opportunity_id
        _store_change(
            repo,
            ChangeEventDraft(
                change_kind="suspected_duplicate",
                message=decision.reason,
                entity_type="opportunity",
                entity_id=opportunity_id,
                details={"matched_opportunity_id": decision.existing_opportunity_id},
            ),
            snapshot,
            entity_id=opportunity_id,
        )
        stats.change_events += 1
    else:
        opp = _new_opportunity(extraction, snapshot, fingerprint, now)
        repo.upsert_opportunity(opp)
        stats.opportunities_created += 1
        opportunity_id = opp.opportunity_id

    # Replace evidence for this opportunity from this snapshot's extraction.
    written = repo.replace_evidence_for_entity(
        entity_type="opportunity",
        entity_id=opportunity_id,
        snapshot_id=snapshot.snapshot_id,
        records=[
            EvidenceRecord(
                evidence_id=uuid.uuid4().hex,
                entity_type="opportunity",
                entity_id=opportunity_id,
                field_name=e.field_name,
                source_url=e.source_url,
                snapshot_id=snapshot.snapshot_id,
                quoted_text=e.quoted_text,
                evidence_date=now,
                extraction_method=e.extraction_method,
                verification_status=e.verification_status,
            )
            for e in extraction.evidence
        ],
    )
    stats.evidence_written += written

    change_drafts = detect_snapshot_changes(
        previous_hash=previous.content_hash if previous else None,
        current_hash=snapshot.content_hash,
        previous_deadline=previous_deadline,
        current_deadline=extraction.application_deadline,
        parse_ok=True,
        http_status=snapshot.http_status,
        is_first_sighting=previous is None and decision.kind == "new",
    )
    if extraction.review_status in {"needs_review", "research_topic_may_match"}:
        change_drafts.append(
            ChangeEventDraft(
                change_kind="needs_human_review",
                message=f"review_status={extraction.review_status}",
                entity_type="opportunity",
                entity_id=opportunity_id,
            )
        )
    for draft in change_drafts:
        _store_change(repo, draft, snapshot, entity_id=opportunity_id)
        stats.change_events += 1

    return stats


def _fingerprint(extraction: ExtractionResult, snapshot: PageSnapshotRecord) -> str:
    parts = [
        extraction.title or "",
        extraction.official_source_url or "",
        extraction.application_deadline or "",
        ",".join(extraction.research_areas),
        snapshot.content_hash or "",
    ]
    return content_hash("|".join(parts))


def _new_opportunity(
    extraction: ExtractionResult,
    snapshot: PageSnapshotRecord,
    fingerprint: str,
    now: datetime,
) -> OpportunityRecord:
    return OpportunityRecord(
        opportunity_id=uuid.uuid4().hex,
        title=extraction.title,
        opportunity_type=extraction.opportunity_type,
        degree_level=extraction.degree_level,
        research_area=", ".join(extraction.research_areas) or None,
        eligibility_text=extraction.eligibility_text,
        language_requirements=extraction.language_requirements,
        application_open_date=extraction.application_open_date,
        application_deadline=extraction.application_deadline,
        first_seen_at=now,
        last_seen_at=now,
        official_source_url=extraction.official_source_url or snapshot.original_url,
        normalized_url=normalize_url(extraction.official_source_url or snapshot.original_url),
        content_hash=fingerprint,
        review_status=extraction.review_status,
        open_questions=" | ".join(extraction.open_questions) or None,
        graduate_school_candidate=extraction.graduate_school_candidate,
        has_public_admission_language=extraction.has_public_admission_language,
        research_topic_may_match=extraction.research_topic_may_match,
        status="observed",
    )


def _merge_opportunity(
    existing: OpportunityRecord | None,
    extraction: ExtractionResult,
    snapshot: PageSnapshotRecord,
    fingerprint: str,
    now: datetime,
) -> OpportunityRecord:
    if existing is None:
        return _new_opportunity(extraction, snapshot, fingerprint, now)

    # Update sighting timestamps; only fill fields when new evidence provides values.
    existing.last_seen_at = now
    existing.content_hash = fingerprint
    if extraction.title:
        existing.title = extraction.title
    if extraction.opportunity_type:
        existing.opportunity_type = extraction.opportunity_type
    if extraction.degree_level:
        existing.degree_level = extraction.degree_level
    if extraction.research_areas:
        existing.research_area = ", ".join(extraction.research_areas)
    if extraction.eligibility_text:
        existing.eligibility_text = extraction.eligibility_text
    if extraction.language_requirements:
        existing.language_requirements = extraction.language_requirements
    if extraction.application_deadline:
        existing.application_deadline = extraction.application_deadline
    if extraction.official_source_url:
        existing.official_source_url = extraction.official_source_url
        existing.normalized_url = normalize_url(extraction.official_source_url)
    existing.has_public_admission_language = (
        existing.has_public_admission_language or extraction.has_public_admission_language
    )
    existing.research_topic_may_match = (
        existing.research_topic_may_match or extraction.research_topic_may_match
    )
    # Never auto-upgrade to eligibility_confirmed.
    if extraction.review_status == "public_admission_info_found":
        existing.review_status = "public_admission_info_found"
    elif (
        extraction.review_status == "research_topic_may_match"
        and existing.review_status == "insufficient_info"
    ):
        existing.review_status = "research_topic_may_match"
    if extraction.open_questions:
        existing.open_questions = " | ".join(extraction.open_questions)
    if extraction.graduate_school_candidate:
        existing.graduate_school_candidate = extraction.graduate_school_candidate
    return existing


def _store_change(
    repo: Repository,
    draft: ChangeEventDraft,
    snapshot: PageSnapshotRecord,
    *,
    entity_id: str | None,
) -> None:
    repo.add_change_event(
        ChangeEventRecord(
            change_id=uuid.uuid4().hex,
            change_kind=draft.change_kind,
            message=draft.message,
            detected_at=datetime.now(UTC),
            entity_type=draft.entity_type or ("opportunity" if entity_id else "snapshot"),
            entity_id=draft.entity_id or entity_id,
            snapshot_id=snapshot.snapshot_id,
            source_id=snapshot.source_id,
            details_json=draft.details or {},
        )
    )
