"""Load and validate application settings from YAML (+ optional env overrides)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(Exception):
    """Raised when configuration cannot be loaded or validated."""


class AppSection(BaseModel):
    name: str = "SakuraScope"
    environment: str = "development"


class PathsSection(BaseModel):
    data_dir: Path = Path("data/runtime")
    log_dir: Path = Path("logs")
    sources_file: Path = Path("config/sources.example.yaml")
    research_areas_file: Path = Path("config/research_areas.yaml")
    reports_dir: Path = Path("reports")
    database_filename: str = "sakurascope.db"


class LoggingSection(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class HttpSection(BaseModel):
    user_agent: str = (
        "SakuraScope/0.2 (+https://github.com/example/sakurascope; research-opportunity-radar)"
    )
    timeout_seconds: float = 30.0
    max_retries: int = Field(default=2, ge=0, le=10)
    min_request_interval_seconds: float = Field(default=1.0, ge=0.0)
    max_response_bytes: int = Field(default=5_000_000, ge=1024)
    respect_robots_txt: bool = True


class AiSection(BaseModel):
    """Optional AI extraction. Disabled by default; never commit API keys here."""

    enabled: bool = False
    provider: str = "none"  # none | openai_compatible
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_seconds: float = Field(default=60.0, gt=0)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_text_chars: int = Field(default=12000, ge=500)
    # Populated only from environment at load time — never from committed YAML secrets.
    api_key: str | None = None


class Settings(BaseModel):
    """Validated runtime settings used across the application."""

    app: AppSection = Field(default_factory=AppSection)
    paths: PathsSection = Field(default_factory=PathsSection)
    logging: LoggingSection = Field(default_factory=LoggingSection)
    http: HttpSection = Field(default_factory=HttpSection)
    ai: AiSection = Field(default_factory=AiSection)
    config_path: Path | None = None


class EnvOverrides(BaseSettings):
    """Optional environment variable overrides (never commit real secrets)."""

    model_config = SettingsConfigDict(
        env_prefix="SAKURASCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    config_path: Path | None = None
    data_dir: Path | None = None
    log_level: str | None = None
    ai_api_key: str | None = None


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward until pyproject.toml is found, else use cwd."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current


def default_config_path(project_root: Path | None = None) -> Path:
    root = project_root or find_project_root()
    return root / "config" / "settings.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SettingsError(f"Settings file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SettingsError(f"Cannot read settings file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SettingsError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SettingsError(f"Settings root must be a mapping/object in {path}")
    return data


def _resolve_path(value: Path, base: Path) -> Path:
    if value.is_absolute():
        return value
    return (base / value).resolve()


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from YAML and apply safe environment overrides."""
    env = EnvOverrides()
    project_root = find_project_root()

    path = config_path or env.config_path or default_config_path(project_root)
    if not path.is_absolute():
        path = (project_root / path).resolve()

    data = _load_yaml(path)
    try:
        settings = Settings.model_validate(data)
    except ValidationError as exc:
        raise SettingsError(f"Settings validation failed for {path}:\n{exc}") from exc

    settings.config_path = path

    # Resolve relative paths against the project root (not the caller's cwd alone).
    settings.paths.data_dir = _resolve_path(settings.paths.data_dir, project_root)
    settings.paths.log_dir = _resolve_path(settings.paths.log_dir, project_root)
    settings.paths.sources_file = _resolve_path(settings.paths.sources_file, project_root)
    settings.paths.research_areas_file = _resolve_path(
        settings.paths.research_areas_file, project_root
    )
    settings.paths.reports_dir = _resolve_path(settings.paths.reports_dir, project_root)

    if env.data_dir is not None:
        settings.paths.data_dir = _resolve_path(env.data_dir, project_root)
    if env.log_level is not None:
        settings.logging.level = env.log_level.upper()

    # Key may be present for future use; never auto-enable AI from key alone.
    if env.ai_api_key:
        settings.ai.api_key = env.ai_api_key

    return settings
