"""Config loading tests (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sakurascope.config.settings import SettingsError, load_settings

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_settings.yaml"


def test_load_sample_settings() -> None:
    settings = load_settings(config_path=FIXTURE)
    assert settings.app.name == "SakuraScopeTest"
    assert settings.app.environment == "test"
    assert settings.ai.enabled is False
    assert settings.http.max_retries == 0
    assert settings.config_path == FIXTURE.resolve()
    assert settings.paths.data_dir.is_absolute()
    assert settings.paths.log_dir.is_absolute()


def test_missing_settings_file_raises() -> None:
    missing = Path(__file__).resolve().parent / "does-not-exist.yaml"
    with pytest.raises(SettingsError, match="not found"):
        load_settings(config_path=missing)


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("app: [\n  broken", encoding="utf-8")
    with pytest.raises(SettingsError, match="Invalid YAML"):
        load_settings(config_path=bad)


def test_default_project_settings_exist() -> None:
    """Smoke-check the real default config shipped with the repo."""
    project_root = Path(__file__).resolve().parents[2]
    default = project_root / "config" / "settings.yaml"
    assert default.is_file()
    settings = load_settings(config_path=default)
    assert settings.app.name == "SakuraScope"
    assert settings.ai.enabled is False
