"""Deterministic HTML main-text extraction (no network)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

_NOISE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "form",
    "nav",
    "footer",
    "header",
    "aside",
}

_NOISE_CLASS_ID = re.compile(
    r"(nav|menu|footer|header|sidebar|breadcrumb|cookie|banner|social|share)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedHtml:
    title: str | None
    text: str
    parse_status: str
    error_message: str | None = None


def parse_html(html: str | bytes, *, encoding: str | None = None) -> ParsedHtml:
    """Extract page title and main body text; strip obvious chrome."""
    try:
        if isinstance(html, bytes):
            soup = BeautifulSoup(html, "html.parser", from_encoding=encoding)
        else:
            soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:  # noqa: BLE001 — parser must never crash collectors
        return ParsedHtml(
            title=None,
            text="",
            parse_status="failed",
            error_message=f"HTML parse error: {exc}",
        )

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        identity = " ".join(
            filter(
                None,
                [
                    " ".join(tag.get("class", []) or []),
                    tag.get("id") or "",
                    tag.get("role") or "",
                ],
            )
        )
        if identity and _NOISE_CLASS_ID.search(identity):
            tag.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    chunks: list[str] = []
    for node in root.descendants:
        if isinstance(node, NavigableString):
            parent = node.parent
            if parent and parent.name in {"script", "style"}:
                continue
            text = str(node).strip()
            if text:
                chunks.append(text)

    text = _normalize_blocks(chunks)
    if not text:
        return ParsedHtml(
            title=title,
            text="",
            parse_status="partial" if title else "failed",
            error_message="No main text extracted",
        )
    return ParsedHtml(title=title, text=text, parse_status="ok")


def _normalize_blocks(chunks: list[str]) -> str:
    # Deduplicate adjacent identical lines (common with repeated menus).
    cleaned: list[str] = []
    prev = None
    for chunk in chunks:
        compact = re.sub(r"\s+", " ", chunk).strip()
        if not compact or compact == prev:
            continue
        cleaned.append(compact)
        prev = compact
    return "\n".join(cleaned)
