"""Logging setup tests."""

from __future__ import annotations

from pathlib import Path

from sakurascope.utils.logging import get_logger, setup_logging


def test_setup_logging_writes_file(tmp_path: Path) -> None:
    logger = setup_logging(level="INFO", log_dir=tmp_path)
    logger.info("hello-from-test")
    log_file = tmp_path / "sakurascope.log"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "hello-from-test" in content


def test_get_logger_namespaces() -> None:
    setup_logging(level="WARNING")
    child = get_logger("cli")
    assert child.name == "sakurascope.cli"
