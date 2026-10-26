"""Orchestrate a collect run: sources → fetch/parse → extract → SQLite."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from sakurascope.collectors.html import collect_html_source
from sakurascope.collectors.http import HttpClientConfig, HttpFetcher
from sakurascope.collectors.pdf import collect_pdf_source
from sakurascope.collectors.rss import collect_rss_source
from sakurascope.config.settings import Settings
from sakurascope.config.sources import load_sources
from sakurascope.extraction.factory import build_extractor
from sakurascope.extraction.pipeline import process_snapshot
from sakurascope.models.domain import RunLogRecord, SourceConfig, SourceRecord
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository
from sakurascope.utils.logging import get_logger

logger = get_logger("collectors.service")


@dataclass
class CollectOptions:
    source_id: str | None = None
    include_disabled: bool = False
    skip_extraction: bool = False
    # Phase 7: incremental / recovery
    incremental: bool = False
    incremental_max_age_hours: float = 24.0
    retry_failed_only: bool = False
    run_retries: int = 0  # extra passes over sources that failed in this run


@dataclass
class CollectSummary:
    run_id: str
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    sources_skipped: int = 0
    pages_processed: int = 0
    new_records: int = 0
    updated_records: int = 0
    duplicates_found: int = 0
    opportunities_created: int = 0
    opportunities_updated: int = 0
    evidence_written: int = 0
    change_events: int = 0
    retry_passes: int = 0
    errors: list[str] = field(default_factory=list)
    skipped_source_ids: list[str] = field(default_factory=list)
    failed_source_ids: list[str] = field(default_factory=list)
    database_path: Path | None = None
    mode: str = "full"

    @property
    def ok(self) -> bool:
        return self.sources_failed == 0


def run_collect(
    settings: Settings,
    options: CollectOptions | None = None,
    *,
    http_client: httpx.Client | None = None,
) -> CollectSummary:
    options = options or CollectOptions()
    started = datetime.now(UTC)
    run_id = uuid.uuid4().hex
    mode = _mode_label(options)

    db_path = settings.paths.data_dir / settings.paths.database_filename
    database = create_database(db_path)
    summary = CollectSummary(run_id=run_id, database_path=db_path, mode=mode)

    all_sources = load_sources(settings.paths.sources_file, enabled_only=False)

    http_cfg = HttpClientConfig(
        user_agent=settings.http.user_agent,
        timeout_seconds=settings.http.timeout_seconds,
        max_retries=settings.http.max_retries,
        min_request_interval_seconds=settings.http.min_request_interval_seconds,
        max_response_bytes=settings.http.max_response_bytes,
        respect_robots_txt=settings.http.respect_robots_txt,
    )

    with database.session() as session, HttpFetcher(http_cfg, client=http_client) as fetcher:
        repo = Repository(session)
        # Ensure existing DB rows are visible for incremental / retry filters.
        selected, skipped = _select_sources(all_sources, options, repo)
        for source in [*selected, *skipped]:
            repo.upsert_source_from_config(source)
        session.commit()

        summary.sources_skipped = len(skipped)
        summary.skipped_source_ids = [s.source_id for s in skipped]
        for sid in summary.skipped_source_ids:
            logger.info("Skipping source %s (incremental/retry filter)", sid)

        if not selected:
            logger.info("No sources selected for collection.")
            repo.add_run_log(
                RunLogRecord(
                    run_id=run_id,
                    started_at=started,
                    completed_at=datetime.now(UTC),
                    error_summary=(f"No sources selected (mode={mode}; skipped={len(skipped)})."),
                )
            )
            session.commit()
            return summary

        run = RunLogRecord(run_id=run_id, started_at=started)
        repo.add_run_log(run)
        session.commit()

        extractor = None if options.skip_extraction else build_extractor(settings)

        pending = list(selected)
        pass_index = 0
        max_passes = 1 + max(0, options.run_retries)
        final_failed: set[str] = set()
        final_succeeded: set[str] = set()

        while pending and pass_index < max_passes:
            if pass_index > 0:
                summary.retry_passes += 1
                logger.info(
                    "Retry pass %s/%s for %s failed source(s)",
                    pass_index,
                    options.run_retries,
                    len(pending),
                )
            failed_this_pass: list[SourceConfig] = []
            for source in pending:
                ok = _collect_source(
                    source,
                    fetcher=fetcher,
                    repo=repo,
                    extractor=extractor,
                    summary=summary,
                    session=session,
                    count_attempt=(pass_index == 0),
                )
                if ok:
                    final_succeeded.add(source.source_id)
                    final_failed.discard(source.source_id)
                else:
                    failed_this_pass.append(source)
                    final_failed.add(source.source_id)
                    final_succeeded.discard(source.source_id)
            pending = failed_this_pass
            pass_index += 1

        # Recount unique source outcomes after retries (attempts may include retries).
        summary.sources_succeeded = len(final_succeeded)
        summary.sources_failed = len(final_failed)
        summary.failed_source_ids = sorted(final_failed)
        # Keep errors only for sources that remain failed.
        if final_failed:
            summary.errors = [err for err in summary.errors if err.split(":", 1)[0] in final_failed]
        else:
            summary.errors = []

        run.completed_at = datetime.now(UTC)
        run.sources_attempted = summary.sources_attempted
        run.sources_succeeded = summary.sources_succeeded
        run.sources_failed = summary.sources_failed
        run.pages_processed = summary.pages_processed
        run.new_records = summary.new_records
        run.updated_records = summary.updated_records
        run.duplicates_found = summary.duplicates_found
        run.error_summary = "; ".join(summary.errors) if summary.errors else None
        repo.update_run_log(run)
        session.commit()

    return summary


def _mode_label(options: CollectOptions) -> str:
    if options.retry_failed_only:
        return "retry_failed"
    if options.incremental:
        return "incremental"
    if options.source_id:
        return "single_source"
    return "full"


def _collect_source(
    source: SourceConfig,
    *,
    fetcher: HttpFetcher,
    repo: Repository,
    extractor,
    summary: CollectSummary,
    session,
    count_attempt: bool = True,
) -> bool:
    if count_attempt:
        summary.sources_attempted += 1
    logger.info(
        "Collecting source %s (%s) via %s",
        source.source_id,
        source.source_url,
        source.collection_strategy,
    )
    try:
        snapshots = _collect_one(source, fetcher)
    except Exception as exc:  # noqa: BLE001 — record and continue
        msg = f"{source.source_id}: unexpected error: {exc}"
        logger.exception(msg)
        summary.errors.append(msg)
        repo.mark_source_attempt(source.source_id, http_status=None, error=str(exc), success=False)
        session.commit()
        return False

    source_ok = False
    last_status: int | None = None
    last_error: str | None = None

    for snap in snapshots:
        summary.pages_processed += 1
        last_status = snap.http_status
        if snap.parse_status == "ok":
            source_ok = True
        else:
            last_error = snap.error_message or last_error

        if snap.content_hash and repo.content_hash_exists(snap.content_hash):
            snap.is_duplicate_content = True
            summary.duplicates_found += 1
        else:
            summary.new_records += 1

        repo.add_snapshot(snap)

        if extractor is not None:
            stats = process_snapshot(repo, snap, source, extractor=extractor)
            summary.opportunities_created += stats.opportunities_created
            summary.opportunities_updated += stats.opportunities_updated
            summary.updated_records += stats.opportunities_updated
            summary.evidence_written += stats.evidence_written
            summary.change_events += stats.change_events
            summary.duplicates_found += stats.suspected_duplicates

    if source_ok:
        # Drop prior error lines for this source if a later retry succeeds.
        summary.errors = [
            err for err in summary.errors if not err.startswith(f"{source.source_id}:")
        ]
        repo.mark_source_attempt(
            source.source_id,
            http_status=last_status,
            error=None,
            success=True,
        )
        session.commit()
        return True

    err = last_error or "Collection failed"
    # Replace prior error line for this source.
    summary.errors = [e for e in summary.errors if not e.startswith(f"{source.source_id}:")]
    summary.errors.append(f"{source.source_id}: {err}")
    repo.mark_source_attempt(
        source.source_id,
        http_status=last_status,
        error=err,
        success=False,
    )
    session.commit()
    return False


def _select_sources(
    sources: list[SourceConfig],
    options: CollectOptions,
    repo: Repository,
) -> tuple[list[SourceConfig], list[SourceConfig]]:
    if options.source_id:
        matched = [s for s in sources if s.source_id == options.source_id]
        if not matched:
            raise ValueError(f"Unknown source_id: {options.source_id}")
        return matched, []

    base = list(sources) if options.include_disabled else [s for s in sources if s.enabled]
    db_rows = {row.source_id: row for row in repo.list_sources()}
    selected: list[SourceConfig] = []
    skipped: list[SourceConfig] = []
    now = datetime.now(UTC)

    for source in base:
        record = db_rows.get(source.source_id)
        if options.retry_failed_only:
            if _needs_failure_retry(record):
                selected.append(source)
            else:
                skipped.append(source)
            continue

        if options.incremental and _recently_succeeded(
            record, now=now, max_age_hours=options.incremental_max_age_hours
        ):
            skipped.append(source)
            continue

        selected.append(source)

    return selected, skipped


def _needs_failure_retry(record: SourceRecord | None) -> bool:
    if record is None:
        return True
    if record.last_error:
        return True
    if record.last_attempt_at and not record.last_success_at:
        return True
    return bool(
        record.last_attempt_at
        and record.last_success_at
        and record.last_attempt_at > record.last_success_at
    )


def _recently_succeeded(
    record: SourceRecord | None,
    *,
    now: datetime,
    max_age_hours: float,
) -> bool:
    if record is None or record.last_success_at is None:
        return False
    if record.last_error:
        return False
    success = record.last_success_at
    if success.tzinfo is None:
        success = success.replace(tzinfo=UTC)
    return (now - success) <= timedelta(hours=max_age_hours)


def _collect_one(source: SourceConfig, fetcher: HttpFetcher):
    if source.collection_strategy == "html":
        return collect_html_source(source, fetcher)
    if source.collection_strategy == "rss":
        return collect_rss_source(source, fetcher)
    if source.collection_strategy == "pdf":
        return collect_pdf_source(source, fetcher)
    raise ValueError(f"Unsupported collection_strategy: {source.collection_strategy}")
