"""URL safety tests (no network)."""

from __future__ import annotations

import pytest

from sakurascope.utils.urls import UnsafeUrlError, validate_public_http_url


def test_accepts_https_public_host() -> None:
    url = validate_public_http_url("https://example.com/path")
    assert url.startswith("https://")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://192.168.1.10/",
        "http://[::1]/",
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url(url)
