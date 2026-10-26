"""CLI smoke tests (no network)."""

from __future__ import annotations

from pathlib import Path

import yaml

from sakurascope.cli import EXIT_OK, main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_settings.yaml"


def test_help_command_exits_zero(capsys) -> None:
    code = main(["help"])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "SakuraScope" in captured.out
    assert "report" in captured.out


def test_status_with_fixture_config(capsys) -> None:
    code = main(["--config", str(FIXTURE), "status"])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "SakuraScope version" in captured.out
    assert "disabled (rule-based default)" in captured.out
    assert "[x] Config loading" in captured.out
    assert "[x] Research-area filtering & reports" in captured.out
    assert "[x] Streamlit dashboard" in captured.out
    assert "[x] Optional AI extraction interface" in captured.out
    assert "[x] Incremental collect" in captured.out
    assert "[x] GitHub Actions workflow" in captured.out


def test_collect_with_no_enabled_sources(tmp_path: Path, capsys) -> None:
    sources = tmp_path / "sources.yaml"
    sources.write_text("sources: []\n", encoding="utf-8")
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "t", "environment": "test"},
                "paths": {
                    "data_dir": str(tmp_path / "data"),
                    "log_dir": str(tmp_path / "logs"),
                    "sources_file": str(sources),
                    "reports_dir": str(tmp_path / "reports"),
                },
                "logging": {"level": "WARNING"},
                "http": {"min_request_interval_seconds": 0.0, "respect_robots_txt": False},
                "ai": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    code = main(["--config", str(settings), "collect"])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "No enabled sources" in captured.out or "sources attempted      : 0" in captured.out


def test_report_on_empty_database(tmp_path: Path, capsys) -> None:
    sources = tmp_path / "sources.yaml"
    sources.write_text("sources: []\n", encoding="utf-8")
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "t", "environment": "test"},
                "paths": {
                    "data_dir": str(tmp_path / "data"),
                    "log_dir": str(tmp_path / "logs"),
                    "sources_file": str(sources),
                    "reports_dir": str(tmp_path / "reports"),
                    "research_areas_file": str(
                        Path(__file__).resolve().parents[2] / "config" / "research_areas.yaml"
                    ),
                },
                "logging": {"level": "WARNING"},
                "http": {"min_request_interval_seconds": 0.0, "respect_robots_txt": False},
                "ai": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    code = main(["--config", str(settings), "report", "--format", "json"])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "opportunities     : 0" in captured.out
    assert "json" in captured.out.lower() or ".json" in captured.out


def test_no_subcommand_shows_help(capsys) -> None:
    code = main([])
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "Implemented now" in captured.out
