"""URL normalization tests."""

from __future__ import annotations

from sakurascope.deduplication.urls import normalize_url


def test_strips_tracking_params_and_fragment() -> None:
    raw = "https://Example.com:443/path/?utm_source=x&id=1&fbclid=abc#section"
    assert normalize_url(raw) == "https://example.com/path?id=1"


def test_trailing_slash_normalized() -> None:
    assert normalize_url("https://example.com/a/") == "https://example.com/a"
    assert normalize_url("https://example.com/") == "https://example.com/"
