"""CRUD helpers for SakuraScope entities."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from sakurascope.deduplication.urls import normalize_url
from sakurascope.models.domain import (
    ChangeEventRecord,
    EvidenceRecord,
    OpportunityRecord,
    PageSnapshotRecord,
    RunLogRecord,
    SourceConfig,
    SourceRecord,
)
from sakurascope.storage.schema import (
    ChangeEventRow,
    EvidenceRow,
    OpportunityRow,
    PageSnapshotRow,
    RunLogRow,
    SourceRow,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_source_from_config(self, config: SourceConfig) -> SourceRecord:
        row = self.session.get(SourceRow, config.source_id)
        if row is None:
            row = SourceRow(
                source_id=config.source_id,
                source_name=config.source_name,
                source_url=str(config.source_url),
                source_type=config.source_type,
                collection_strategy=config.collection_strategy,
                enabled=config.enabled,
                notes=config.notes,
            )
            self.session.add(row)
        else:
            row.source_name = config.source_name
            row.source_url = str(config.source_url)
            row.source_type = config.source_type
            row.collection_strategy = config.collection_strategy
            row.enabled = config.enabled
            row.notes = config.notes
        self.session.flush()
        return self._source_to_model(row)

    def mark_source_attempt(
        self,
        source_id: str,
        *,
        http_status: int | None,
        error: str | None,
        success: bool,
    ) -> None:
        row = self.session.get(SourceRow, source_id)
        if row is None:
            return
        now = _utcnow()
        row.last_attempt_at = now
        row.last_http_status = http_status
        row.last_error = error
        if success:
            row.last_success_at = now
        self.session.flush()

    def content_hash_exists(
        self, content_hash: str, *, exclude_snapshot_id: str | None = None
    ) -> bool:
        stmt = select(PageSnapshotRow.snapshot_id).where(
            PageSnapshotRow.content_hash == content_hash,
            PageSnapshotRow.parse_status == "ok",
        )
        if exclude_snapshot_id:
            stmt = stmt.where(PageSnapshotRow.snapshot_id != exclude_snapshot_id)
        return self.session.scalar(stmt) is not None

    def add_snapshot(self, snapshot: PageSnapshotRecord) -> PageSnapshotRecord:
        row = PageSnapshotRow(
            snapshot_id=snapshot.snapshot_id,
            source_id=snapshot.source_id,
            original_url=snapshot.original_url,
            final_url=snapshot.final_url,
            fetched_at=snapshot.fetched_at,
            http_status=snapshot.http_status,
            content_hash=snapshot.content_hash,
            content_type=snapshot.content_type,
            title=snapshot.title,
            extracted_text=snapshot.extracted_text,
            etag=snapshot.etag,
            last_modified=snapshot.last_modified,
            parse_status=snapshot.parse_status,
            error_message=snapshot.error_message,
            is_duplicate_content=snapshot.is_duplicate_content,
            metadata_json=json.dumps(snapshot.metadata_json, ensure_ascii=False)
            if snapshot.metadata_json
            else None,
        )
        self.session.add(row)
        self.session.flush()
        return snapshot

    def get_latest_successful_snapshot_by_normalized_url(
        self,
        normalized: str,
        *,
        exclude_snapshot_id: str | None = None,
    ) -> PageSnapshotRecord | None:
        rows = self.session.scalars(
            select(PageSnapshotRow)
            .where(PageSnapshotRow.parse_status.in_(("ok", "partial")))
            .order_by(PageSnapshotRow.fetched_at.desc())
        ).all()
        for row in rows:
            if exclude_snapshot_id and row.snapshot_id == exclude_snapshot_id:
                continue
            candidate = normalize_url(row.final_url or row.original_url)
            if candidate == normalized:
                return self._snapshot_to_model(row)
        return None

    def add_run_log(self, run: RunLogRecord) -> RunLogRecord:
        row = RunLogRow(
            run_id=run.run_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            sources_attempted=run.sources_attempted,
            sources_succeeded=run.sources_succeeded,
            sources_failed=run.sources_failed,
            pages_processed=run.pages_processed,
            new_records=run.new_records,
            updated_records=run.updated_records,
            duplicates_found=run.duplicates_found,
            error_summary=run.error_summary,
        )
        self.session.add(row)
        self.session.flush()
        return run

    def update_run_log(self, run: RunLogRecord) -> None:
        row = self.session.get(RunLogRow, run.run_id)
        if row is None:
            self.add_run_log(run)
            return
        row.completed_at = run.completed_at
        row.sources_attempted = run.sources_attempted
        row.sources_succeeded = run.sources_succeeded
        row.sources_failed = run.sources_failed
        row.pages_processed = run.pages_processed
        row.new_records = run.new_records
        row.updated_records = run.updated_records
        row.duplicates_found = run.duplicates_found
        row.error_summary = run.error_summary
        self.session.flush()

    def count_snapshots(self) -> int:
        return len(self.session.scalars(select(PageSnapshotRow.snapshot_id)).all())

    def get_source(self, source_id: str) -> SourceRecord | None:
        row = self.session.get(SourceRow, source_id)
        return self._source_to_model(row) if row else None

    def list_snapshots_for_source(self, source_id: str) -> list[PageSnapshotRecord]:
        rows = self.session.scalars(
            select(PageSnapshotRow)
            .where(PageSnapshotRow.source_id == source_id)
            .order_by(PageSnapshotRow.fetched_at.desc())
        ).all()
        return [self._snapshot_to_model(row) for row in rows]

    def list_opportunity_match_rows(self) -> list[dict]:
        rows = self.session.scalars(select(OpportunityRow)).all()
        return [
            {
                "opportunity_id": row.opportunity_id,
                "official_source_url": row.official_source_url,
                "title": row.title,
                "content_hash": row.content_hash,
            }
            for row in rows
        ]

    def get_opportunity(self, opportunity_id: str) -> OpportunityRecord | None:
        row = self.session.get(OpportunityRow, opportunity_id)
        return self._opportunity_to_model(row) if row else None

    def upsert_opportunity(self, opportunity: OpportunityRecord) -> OpportunityRecord:
        row = self.session.get(OpportunityRow, opportunity.opportunity_id)
        values = dict(
            title=opportunity.title,
            institution_id=opportunity.institution_id,
            lab_id=opportunity.lab_id,
            opportunity_type=opportunity.opportunity_type,
            degree_level=opportunity.degree_level,
            research_area=opportunity.research_area,
            eligibility_text=opportunity.eligibility_text,
            language_requirements=opportunity.language_requirements,
            application_open_date=opportunity.application_open_date,
            application_deadline=opportunity.application_deadline,
            tuition_or_fee_text=opportunity.tuition_or_fee_text,
            funding_text=opportunity.funding_text,
            status=opportunity.status,
            first_seen_at=opportunity.first_seen_at,
            last_seen_at=opportunity.last_seen_at,
            last_verified_at=opportunity.last_verified_at,
            official_source_url=opportunity.official_source_url,
            normalized_url=opportunity.normalized_url,
            content_hash=opportunity.content_hash,
            review_status=str(opportunity.review_status),
            open_questions=opportunity.open_questions,
            graduate_school_candidate=opportunity.graduate_school_candidate,
            has_public_admission_language=opportunity.has_public_admission_language,
            research_topic_may_match=opportunity.research_topic_may_match,
        )
        if row is None:
            row = OpportunityRow(opportunity_id=opportunity.opportunity_id, **values)
            self.session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        self.session.flush()
        return opportunity

    def replace_evidence_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: str,
        snapshot_id: str,
        records: list[EvidenceRecord],
    ) -> int:
        self.session.execute(
            delete(EvidenceRow).where(
                EvidenceRow.entity_type == entity_type,
                EvidenceRow.entity_id == entity_id,
                EvidenceRow.snapshot_id == snapshot_id,
            )
        )
        for record in records:
            self.session.add(
                EvidenceRow(
                    evidence_id=record.evidence_id,
                    entity_type=record.entity_type,
                    entity_id=record.entity_id,
                    field_name=record.field_name,
                    source_url=record.source_url,
                    snapshot_id=record.snapshot_id,
                    quoted_text=record.quoted_text,
                    evidence_date=record.evidence_date,
                    extraction_method=record.extraction_method,
                    verification_status=record.verification_status,
                )
            )
        self.session.flush()
        return len(records)

    def list_evidence_for_entity(self, entity_type: str, entity_id: str) -> list[EvidenceRecord]:
        rows = self.session.scalars(
            select(EvidenceRow).where(
                EvidenceRow.entity_type == entity_type,
                EvidenceRow.entity_id == entity_id,
            )
        ).all()
        return [
            EvidenceRecord(
                evidence_id=row.evidence_id,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                field_name=row.field_name,
                source_url=row.source_url,
                snapshot_id=row.snapshot_id,
                quoted_text=row.quoted_text,
                evidence_date=row.evidence_date,
                extraction_method=row.extraction_method,
                verification_status=row.verification_status,
            )
            for row in rows
        ]

    def add_change_event(self, event: ChangeEventRecord) -> ChangeEventRecord:
        self.session.add(
            ChangeEventRow(
                change_id=event.change_id,
                change_kind=event.change_kind,
                message=event.message,
                detected_at=event.detected_at,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                snapshot_id=event.snapshot_id,
                source_id=event.source_id,
                details_json=json.dumps(event.details_json, ensure_ascii=False)
                if event.details_json
                else None,
            )
        )
        self.session.flush()
        return event

    def list_change_events(self, *, limit: int = 100) -> list[ChangeEventRecord]:
        rows = self.session.scalars(
            select(ChangeEventRow).order_by(ChangeEventRow.detected_at.desc()).limit(limit)
        ).all()
        return [
            ChangeEventRecord(
                change_id=row.change_id,
                change_kind=row.change_kind,
                message=row.message,
                detected_at=row.detected_at,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                snapshot_id=row.snapshot_id,
                source_id=row.source_id,
                details_json=json.loads(row.details_json) if row.details_json else {},
            )
            for row in rows
        ]

    def list_opportunities(self) -> list[OpportunityRecord]:
        rows = self.session.scalars(select(OpportunityRow)).all()
        return [self._opportunity_to_model(row) for row in rows]

    def list_sources(self) -> list[SourceRecord]:
        rows = self.session.scalars(select(SourceRow).order_by(SourceRow.source_id)).all()
        return [self._source_to_model(row) for row in rows]

    def list_run_logs(self, *, limit: int = 50) -> list[RunLogRecord]:
        rows = self.session.scalars(
            select(RunLogRow).order_by(RunLogRow.started_at.desc()).limit(limit)
        ).all()
        return [
            RunLogRecord(
                run_id=row.run_id,
                started_at=row.started_at,
                completed_at=row.completed_at,
                sources_attempted=row.sources_attempted,
                sources_succeeded=row.sources_succeeded,
                sources_failed=row.sources_failed,
                pages_processed=row.pages_processed,
                new_records=row.new_records,
                updated_records=row.updated_records,
                duplicates_found=row.duplicates_found,
                error_summary=row.error_summary,
            )
            for row in rows
        ]

    def count_opportunities(self) -> int:
        return len(self.session.scalars(select(OpportunityRow.opportunity_id)).all())

    def count_evidence(self) -> int:
        return len(self.session.scalars(select(EvidenceRow.evidence_id)).all())

    @staticmethod
    def _source_to_model(row: SourceRow) -> SourceRecord:
        return SourceRecord(
            source_id=row.source_id,
            source_name=row.source_name,
            source_url=row.source_url,
            source_type=row.source_type,
            collection_strategy=row.collection_strategy,
            enabled=row.enabled,
            notes=row.notes,
            last_attempt_at=row.last_attempt_at,
            last_success_at=row.last_success_at,
            last_http_status=row.last_http_status,
            last_error=row.last_error,
        )

    @staticmethod
    def _snapshot_to_model(row: PageSnapshotRow) -> PageSnapshotRecord:
        meta: dict = {}
        if row.metadata_json:
            meta = json.loads(row.metadata_json)
        return PageSnapshotRecord(
            snapshot_id=row.snapshot_id,
            source_id=row.source_id,
            original_url=row.original_url,
            final_url=row.final_url,
            fetched_at=row.fetched_at,
            http_status=row.http_status,
            content_hash=row.content_hash,
            content_type=row.content_type,
            title=row.title,
            extracted_text=row.extracted_text,
            etag=row.etag,
            last_modified=row.last_modified,
            parse_status=row.parse_status,  # type: ignore[arg-type]
            error_message=row.error_message,
            is_duplicate_content=row.is_duplicate_content,
            metadata_json=meta,
        )

    @staticmethod
    def _opportunity_to_model(row: OpportunityRow) -> OpportunityRecord:
        return OpportunityRecord(
            opportunity_id=row.opportunity_id,
            title=row.title,
            institution_id=row.institution_id,
            lab_id=row.lab_id,
            opportunity_type=row.opportunity_type,
            degree_level=row.degree_level,
            research_area=row.research_area,
            eligibility_text=row.eligibility_text,
            language_requirements=row.language_requirements,
            application_open_date=row.application_open_date,
            application_deadline=row.application_deadline,
            tuition_or_fee_text=row.tuition_or_fee_text,
            funding_text=row.funding_text,
            status=row.status,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            last_verified_at=row.last_verified_at,
            official_source_url=row.official_source_url,
            normalized_url=row.normalized_url,
            content_hash=row.content_hash,
            review_status=row.review_status,
            open_questions=row.open_questions,
            graduate_school_candidate=row.graduate_school_candidate,
            has_public_admission_language=row.has_public_admission_language,
            research_topic_may_match=row.research_topic_may_match,
        )
