"""Load configurable research-area keywords and weights."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from sakurascope.config.settings import SettingsError
from sakurascope.extraction.keywords import RESEARCH_AREA_KEYWORDS


class ResearchAreaEntry(BaseModel):
    name: str
    weight: float = Field(default=1.0, ge=0.0)
    keywords: list[str] = Field(default_factory=list)


class ResearchAreaConfig(BaseModel):
    areas: list[ResearchAreaEntry] = Field(default_factory=list)
    min_topic_score: float = Field(default=0.5, ge=0.0)

    def keyword_map(self) -> dict[str, list[str]]:
        return {area.name: list(area.keywords) for area in self.areas}

    def weight_map(self) -> dict[str, float]:
        return {area.name: area.weight for area in self.areas}


def default_research_areas() -> ResearchAreaConfig:
    """Built-in fallback mirroring extraction keyword labels."""
    areas = [
        ResearchAreaEntry(name=name, weight=1.0, keywords=list(keywords))
        for name, keywords in RESEARCH_AREA_KEYWORDS.items()
    ]
    return ResearchAreaConfig(areas=areas, min_topic_score=0.5)


def load_research_areas(path: Path | None) -> ResearchAreaConfig:
    if path is None or not path.is_file():
        return default_research_areas()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SettingsError(f"Cannot read research areas file {path}: {exc}") from exc
    if raw is None:
        return default_research_areas()
    try:
        return ResearchAreaConfig.model_validate(raw)
    except ValidationError as exc:
        raise SettingsError(f"Invalid research areas config {path}:\n{exc}") from exc
