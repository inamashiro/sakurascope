"""Content hashing helpers."""

from __future__ import annotations

import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse whitespace for stable content hashing."""
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def content_hash(text: str) -> str:
    """SHA-256 hex digest of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
