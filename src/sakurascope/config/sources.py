"""Load user-configured source registry from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from sakurascope.config.settings import SettingsError
from sakurascope.models.domain import SourceConfig


def load_sources(path: Path, *, enabled_only: bool = False) -> list[SourceConfig]:
    if not path.is_file():
        raise SettingsError(f"Sources file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SettingsError(f"Cannot read sources file {path}: {exc}") from exc

    if raw is None:
        return []
    if not isinstance(raw, dict) or "sources" not in raw:
        raise SettingsError(f"Sources file must contain a top-level 'sources' list: {path}")

    items = raw["sources"]
    if items is None:
        return []
    if not isinstance(items, list):
        raise SettingsError(f"'sources' must be a list in {path}")

    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SettingsError(f"sources[{index}] must be a mapping in {path}")
        try:
            source = SourceConfig.model_validate(item)
        except ValidationError as exc:
            raise SettingsError(f"Invalid source at sources[{index}] in {path}:\n{exc}") from exc
        if source.source_id in seen_ids:
            raise SettingsError(f"Duplicate source_id {source.source_id!r} in {path}")
        seen_ids.add(source.source_id)
        if enabled_only and not source.enabled:
            continue
        sources.append(source)
    return sources


def dump_sources_summary(sources: list[SourceConfig]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": s.source_id,
            "enabled": s.enabled,
            "strategy": s.collection_strategy,
            "url": str(s.source_url),
        }
        for s in sources
    ]
