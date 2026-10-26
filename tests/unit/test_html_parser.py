"""HTML parser tests using local fixtures (no network)."""

from __future__ import annotations

from pathlib import Path

from sakurascope.parsers.html import parse_html

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_html.html"


def test_parse_html_extracts_title_and_main_text() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    parsed = parse_html(html)
    assert parsed.parse_status == "ok"
    assert parsed.title is not None
    assert "MOCK" in parsed.title
    assert "公衆衛生学研究室" in parsed.text
    assert "epidemiology" in parsed.text
    # Navigation / footer noise should be reduced.
    assert "大学ロゴとメニュー" not in parsed.text
    assert "Copyright Example University" not in parsed.text


def test_parse_html_empty_body() -> None:
    parsed = parse_html("<html><head><title>Only Title</title></head><body></body></html>")
    assert parsed.title == "Only Title"
    assert parsed.parse_status in {"partial", "failed"}
