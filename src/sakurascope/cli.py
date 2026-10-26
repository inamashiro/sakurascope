"""Command-line interface for SakuraScope."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from sakurascope import __version__
from sakurascope.collectors.service import CollectOptions, run_collect
from sakurascope.config.settings import SettingsError, find_project_root, load_settings
from sakurascope.filtering.classify import FilterCriteria
from sakurascope.monitoring.summary import since_from_hours, summarize_changes
from sakurascope.reporting.service import ReportOptions, generate_reports
from sakurascope.storage.db import create_database
from sakurascope.storage.repository import Repository
from sakurascope.utils.logging import get_logger, setup_logging

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sakurascope",
        description=(
            "SakuraScope — Japan Research & Graduate Opportunity Intelligence. "
            "Collects and organizes publicly available research/admission information. "
            "It does not decide where you should apply."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to settings YAML (default: config/settings.yaml).",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level from settings.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    help_parser = subparsers.add_parser(
        "help",
        help="Show available commands and current project status notes.",
    )
    help_parser.set_defaults(func=cmd_help)

    status_parser = subparsers.add_parser(
        "status",
        help="Show version, config path, and which features are implemented.",
    )
    status_parser.set_defaults(func=cmd_status)

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect enabled public HTML/RSS/PDF sources into the local SQLite database.",
    )
    collect_parser.add_argument(
        "--source",
        dest="source_id",
        default=None,
        help="Collect a single source_id (even if disabled).",
    )
    collect_parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Collect all configured sources, including disabled ones.",
    )
    collect_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip sources that succeeded recently (default window 24h).",
    )
    collect_parser.add_argument(
        "--incremental-hours",
        type=float,
        default=24.0,
        help="Freshness window in hours for --incremental (default: 24).",
    )
    collect_parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only collect sources that previously failed or were never successful.",
    )
    collect_parser.add_argument(
        "--run-retries",
        type=int,
        default=0,
        help="Extra in-run retry passes for sources that fail during this collect.",
    )
    collect_parser.set_defaults(func=cmd_collect)

    report_parser = subparsers.add_parser(
        "report",
        help="Generate Markdown/CSV/JSON reports from the local database.",
    )
    report_parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        choices=["markdown", "md", "csv", "json"],
        default=None,
        help="Report format (repeatable). Default: markdown,csv,json.",
    )
    report_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for report files (default: paths.reports_dir).",
    )
    report_parser.add_argument(
        "--area",
        dest="areas",
        action="append",
        default=None,
        help="Filter by research area name (repeatable).",
    )
    report_parser.add_argument(
        "--degree",
        dest="degrees",
        action="append",
        default=None,
        help="Filter by degree level (repeatable).",
    )
    report_parser.add_argument(
        "--review-status",
        dest="review_statuses",
        action="append",
        default=None,
        help="Filter by review_status (repeatable).",
    )
    report_parser.add_argument(
        "--require-admission-info",
        action="store_true",
        help="Only include opportunities with public admission language.",
    )
    report_parser.add_argument(
        "--require-topic-match",
        action="store_true",
        help="Only include opportunities meeting min topic relevance score.",
    )
    report_parser.add_argument(
        "--min-topic-score",
        type=float,
        default=None,
        help="Override minimum topic relevance score.",
    )
    report_parser.add_argument(
        "--deadline-from",
        default=None,
        help="Keep deadlines on/after this ISO date (YYYY-MM-DD).",
    )
    report_parser.add_argument(
        "--deadline-to",
        default=None,
        help="Keep deadlines on/before this ISO date (YYYY-MM-DD).",
    )
    report_parser.add_argument(
        "--query",
        default=None,
        help="Case-insensitive substring filter over title/area/text/url.",
    )
    report_parser.set_defaults(func=cmd_report)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Launch the local Streamlit query UI.",
    )
    dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Streamlit server port (default: 8501).",
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)

    changes_parser = subparsers.add_parser(
        "changes",
        help="Summarize page/opportunity change events (does not infer admissions closed).",
    )
    changes_parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Only include events from the last N hours (0 = all). Default: 24.",
    )
    changes_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max events to list (default: 100).",
    )
    changes_parser.set_defaults(func=cmd_changes)

    return parser


def cmd_help(args: argparse.Namespace) -> int:
    text = f"""SakuraScope {__version__}
Japan Research & Graduate Opportunity Intelligence

Implemented now (Phase 0–9):
  help       Show this help
  status     Show config and feature readiness
  collect    Fetch HTML/RSS/PDF (full / incremental / retry-failed)
  report     Export Markdown / CSV / JSON with transparent filters
  changes    Summarize change events since a time window
  dashboard  Launch local Streamlit UI (Chinese-first)
  (AI)       Optional; disabled unless ai.enabled + API key

Examples:
  python -m sakurascope collect
  python -m sakurascope collect --incremental
  python -m sakurascope collect --retry-failed --run-retries 1
  python -m sakurascope changes --hours 48
  python -m sakurascope report
  python -m sakurascope dashboard

Important:
  - This tool never invents admissions facts.
  - Topic relevance score ≠ admission probability.
  - Topic match ≠ open recruitment ≠ confirmed eligibility.
  - Example sources in config/ are MOCK data only (disabled by default).
"""
    print(text)
    return EXIT_OK


def _ai_status_line(settings) -> str:
    if not settings.ai.enabled:
        return "disabled (rule-based default)"
    if not settings.ai.api_key:
        return "enabled in config but NO API key — rules fallback"
    return f"enabled ({settings.ai.provider} / {settings.ai.model})"


def cmd_status(args: argparse.Namespace) -> int:
    logger = get_logger("cli")
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        logger.error("Failed to load settings: %s", exc)
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    db_path = settings.paths.data_dir / settings.paths.database_filename
    lines = [
        f"SakuraScope version : {__version__}",
        f"Config file         : {settings.config_path}",
        f"Environment         : {settings.app.environment}",
        f"Data directory      : {settings.paths.data_dir}",
        f"Database file       : {db_path}",
        f"Reports directory   : {settings.paths.reports_dir}",
        f"Research areas file : {settings.paths.research_areas_file}",
        f"Log directory       : {settings.paths.log_dir}",
        f"Sources file        : {settings.paths.sources_file}",
        f"Log level           : {settings.logging.level}",
        f"AI extraction       : {_ai_status_line(settings)}",
        "",
        "Feature readiness:",
        "  [x] Config loading",
        "  [x] Logging",
        "  [x] CLI help / status / collect / report / dashboard",
        "  [x] Collectors (HTML / RSS / PDF text, no OCR)",
        "  [x] SQLite storage",
        "  [x] Rule-based extraction & evidence",
        "  [x] URL normalize + candidate match + change events",
        "  [x] Research-area filtering & reports (MD/CSV/JSON)",
        "  [x] Streamlit dashboard",
        "  [x] Optional AI extraction interface (opt-in; default off)",
        "  [x] Incremental collect / retry-failed / change summary",
        "  [x] GitHub Actions workflow (ephemeral DB unless artifacts)",
        "  [x] Docs (TESTING / SECURITY / LEARNING_GUIDE) + preflight script",
        "  [x] Publication docs (CONTRIBUTING / CHANGELOG / PUBLISHING)",
    ]
    print("\n".join(lines))
    logger.info("Status command completed successfully.")
    return EXIT_OK


def cmd_collect(args: argparse.Namespace) -> int:
    logger = get_logger("cli")
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    if args.incremental and args.retry_failed:
        print("Collect error: use only one of --incremental or --retry-failed.", file=sys.stderr)
        return EXIT_USAGE

    options = CollectOptions(
        source_id=args.source_id,
        include_disabled=bool(args.include_disabled),
        incremental=bool(args.incremental),
        incremental_max_age_hours=float(args.incremental_hours),
        retry_failed_only=bool(args.retry_failed),
        run_retries=max(0, int(args.run_retries)),
    )
    try:
        summary = run_collect(settings, options)
    except ValueError as exc:
        print(f"Collect error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except NotImplementedError as exc:
        print(f"Collect error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(
        "\n".join(
            [
                f"Collect finished (run_id={summary.run_id})",
                f"  mode                   : {summary.mode}",
                f"  database               : {summary.database_path}",
                f"  sources attempted      : {summary.sources_attempted}",
                f"  sources succeeded      : {summary.sources_succeeded}",
                f"  sources failed         : {summary.sources_failed}",
                f"  sources skipped        : {summary.sources_skipped}",
                f"  retry passes           : {summary.retry_passes}",
                f"  pages processed        : {summary.pages_processed}",
                f"  new snapshots          : {summary.new_records}",
                f"  opportunities created  : {summary.opportunities_created}",
                f"  opportunities updated  : {summary.opportunities_updated}",
                f"  evidence written       : {summary.evidence_written}",
                f"  change events          : {summary.change_events}",
                f"  duplicates / suspects  : {summary.duplicates_found}",
            ]
        )
    )
    if summary.errors:
        print("  errors:")
        for err in summary.errors:
            print(f"    - {err}")

    if summary.sources_attempted == 0 and summary.sources_skipped == 0:
        print(
            "\nNo enabled sources. Edit your sources YAML and set enabled: true "
            "for public URLs you are allowed to access, or pass --source / --include-disabled."
        )
        return EXIT_OK

    if summary.sources_attempted == 0 and summary.sources_skipped > 0:
        print(
            "\nAll candidate sources were skipped by incremental/retry filters. "
            "Use a full collect or widen --incremental-hours."
        )
        return EXIT_OK

    if summary.ok:
        logger.info("Collect completed with no source failures.")
        return EXIT_OK

    logger.warning("Collect completed with failures.")
    return EXIT_PARTIAL


def cmd_changes(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    db_path = settings.paths.data_dir / settings.paths.database_filename
    database = create_database(db_path)
    with database.session() as session:
        repo = Repository(session)
        events = repo.list_change_events(limit=max(args.limit * 5, 200))
    summary = summarize_changes(
        events,
        since=since_from_hours(args.hours),
        limit=args.limit,
    )
    print(summary.render_text())
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    logger = get_logger("cli")
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    formats = args.formats or ["markdown", "csv", "json"]
    criteria = FilterCriteria(
        research_areas=args.areas,
        degree_levels=args.degrees,
        review_statuses=args.review_statuses,
        require_public_admission_info=True if args.require_admission_info else None,
        require_topic_match=bool(args.require_topic_match),
        min_topic_score=args.min_topic_score,
        deadline_from=args.deadline_from,
        deadline_to=args.deadline_to,
        query=args.query,
    )
    options = ReportOptions(
        formats=formats,
        output_dir=args.output_dir,
        criteria=criteria,
    )
    try:
        result = generate_reports(settings, options)
    except ValueError as exc:
        print(f"Report error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(
        "\n".join(
            [
                f"Report generated at : {result.generated_at.isoformat() if result.generated_at else ''}",
                f"  opportunities     : {result.opportunity_count}",
                f"  output directory  : {result.output_dir}",
                *[f"  {name:<18}: {path}" for name, path in result.files.items()],
                "",
                "Reminder: topic relevance score is NOT an admission probability.",
            ]
        )
    )
    logger.info("Report command completed (%s opportunities).", result.opportunity_count)
    return EXIT_OK


def cmd_dashboard(args: argparse.Namespace) -> int:
    logger = get_logger("cli")
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    app_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    if not app_path.is_file():
        print(f"Dashboard app not found: {app_path}", file=sys.stderr)
        return EXIT_USAGE

    env = os.environ.copy()
    if args.config is not None:
        env["SAKURASCOPE_CONFIG_PATH"] = str(Path(args.config).resolve())
    elif settings.config_path is not None:
        env["SAKURASCOPE_CONFIG_PATH"] = str(settings.config_path)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
        "--browser.gatherUsageStats",
        "false",
    ]
    print(f"Launching Streamlit UI on port {args.port}…")
    print(f"  app: {app_path}")
    print(f"  cwd: {find_project_root()}")
    logger.info("Starting dashboard: %s", " ".join(cmd))
    try:
        completed = subprocess.run(cmd, cwd=str(find_project_root()), env=env, check=False)
    except FileNotFoundError:
        print(
            "Streamlit is not available. Install project deps: pip install -e .",
            file=sys.stderr,
        )
        return EXIT_USAGE
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return cmd_help(args)

    log_level_override = args.log_level
    try:
        settings = load_settings(config_path=args.config)
    except SettingsError as exc:
        if args.command == "help":
            setup_logging(level=log_level_override or "INFO")
            return cmd_help(args)
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    setup_logging(
        level=log_level_override or settings.logging.level,
        log_format=settings.logging.format,
        log_dir=settings.paths.log_dir,
    )

    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return EXIT_USAGE
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
