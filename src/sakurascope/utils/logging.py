"""Central logging setup for SakuraScope."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(
    *,
    level: str = "INFO",
    log_format: str = DEFAULT_FORMAT,
    log_dir: Path | None = None,
    logger_name: str = "sakurascope",
) -> logging.Logger:
    """Configure the package root logger once (idempotent for tests)."""
    global _CONFIGURED

    root = logging.getLogger(logger_name)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Always refresh handlers so tests and CLI overrides behave predictably.
    root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(log_format))
    root.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "sakurascope.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        root.addHandler(file_handler)

    root.propagate = False
    _CONFIGURED = True
    return root


def get_logger(name: str = "sakurascope") -> logging.Logger:
    """Return a child logger under the sakurascope namespace."""
    if name == "sakurascope" or name.startswith("sakurascope."):
        return logging.getLogger(name)
    return logging.getLogger(f"sakurascope.{name}")
