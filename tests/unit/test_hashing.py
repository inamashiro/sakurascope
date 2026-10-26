"""Content hash tests."""

from __future__ import annotations

from sakurascope.utils.hashing import content_hash, normalize_text


def test_content_hash_stable_under_whitespace() -> None:
    a = content_hash("hello   world\n")
    b = content_hash("hello world")
    assert a == b
    assert normalize_text("  a \n b  ") == "a b"


def test_content_hash_differs_for_different_text() -> None:
    assert content_hash("alpha") != content_hash("beta")
