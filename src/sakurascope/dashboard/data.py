"""Dashboard data loading (Streamlit-free; unit-testable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sakurascope.config.settings import Settings, load_settings
from sakurascope.config.sources import load_sources
from sakurascope.filtering.areas import ResearchAreaConfig, load_research_areas
from sakurascope.filtering.classify import (
    FilterCriteria,
    FilteredOpportunity,
    classify_opportunity,
    filter_opportunities,
)
from sakurascope.models.domain import (
    ChangeEventRecord,
    OpportunityRecord,
    RunLogRecord,
    SourceConfig,
    SourceRecord,
)
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository


@dataclass
class OverviewStats:
    sources_configured: int = 0
    sources_in_db: int = 0
    sources_enabled: int = 0
    snapshots: int = 0
    opportunities: int = 0
    evidence: int = 0
    change_events: int = 0
    runs: int = 0
    with_admission_language: int = 0
    topic_match_only: int = 0
    database_path: str = ""


@dataclass
class InstitutionView:
    """Derived institution/lab view from opportunity candidates (not invented names)."""

    label: str
    opportunity_count: int = 0
    research_areas: list[str] = field(default_factory=list)
    sample_urls: list[str] = field(default_factory=list)


@dataclass
class DashboardData:
    settings: Settings
    area_config: ResearchAreaConfig
    overview: OverviewStats
    opportunities: list[FilteredOpportunity]
    sources_db: list[SourceRecord]
    sources_config: list[SourceConfig]
    change_events: list[ChangeEventRecord]
    run_logs: list[RunLogRecord]
    institutions: list[InstitutionView]


def load_dashboard_data(
    config_path: Path | None = None,
    *,
    criteria: FilterCriteria | None = None,
) -> DashboardData:
    settings = load_settings(config_path=config_path)
    area_config = load_research_areas(settings.paths.research_areas_file)
    db_path = settings.paths.data_dir / settings.paths.database_filename
    database = create_database(db_path)

    try:
        sources_config = load_sources(settings.paths.sources_file, enabled_only=False)
    except Exception:  # noqa: BLE001 — dashboard should still open
        sources_config = []

    with database.session() as session:
        repo = Repository(session)
        raw_opps = repo.list_opportunities()
        classified = [
            classify_opportunity(
                opp,
                area_config,
                evidence=repo.list_evidence_for_entity("opportunity", opp.opportunity_id),
            )
            for opp in raw_opps
        ]
        filtered = filter_opportunities(classified, criteria or FilterCriteria(), area_config)
        sources_db = repo.list_sources()
        changes = repo.list_change_events(limit=200)
        runs = repo.list_run_logs(limit=50)
        overview = OverviewStats(
            sources_configured=len(sources_config),
            sources_in_db=len(sources_db),
            sources_enabled=sum(1 for s in sources_config if s.enabled),
            snapshots=repo.count_snapshots(),
            opportunities=len(raw_opps),
            evidence=repo.count_evidence(),
            change_events=len(changes),
            runs=len(runs),
            with_admission_language=sum(1 for o in raw_opps if o.has_public_admission_language),
            topic_match_only=sum(
                1
                for o in raw_opps
                if o.research_topic_may_match and not o.has_public_admission_language
            ),
            database_path=str(db_path),
        )
        institutions = _derive_institutions([c.opportunity for c in classified])

    return DashboardData(
        settings=settings,
        area_config=area_config,
        overview=overview,
        opportunities=filtered,
        sources_db=sources_db,
        sources_config=sources_config,
        change_events=changes,
        run_logs=runs,
        institutions=institutions,
    )


def _derive_institutions(opportunities: list[OpportunityRecord]) -> list[InstitutionView]:
    buckets: dict[str, InstitutionView] = {}
    for opp in opportunities:
        label = (
            opp.graduate_school_candidate
            or opp.institution_id
            or _host_label(opp.official_source_url)
            or "（未知机构 / Unknown）"
        )
        view = buckets.get(label)
        if view is None:
            view = InstitutionView(label=label)
            buckets[label] = view
        view.opportunity_count += 1
        if opp.research_area:
            for part in opp.research_area.split(","):
                name = part.strip()
                if name and name not in view.research_areas:
                    view.research_areas.append(name)
        if (
            opp.official_source_url
            and opp.official_source_url not in view.sample_urls
            and len(view.sample_urls) < 5
        ):
            view.sample_urls.append(opp.official_source_url)
    return sorted(buckets.values(), key=lambda v: (-v.opportunity_count, v.label))


def _host_label(url: str | None) -> str | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse

        host = urlparse(url).hostname
        return host
    except Exception:  # noqa: BLE001
        return None
