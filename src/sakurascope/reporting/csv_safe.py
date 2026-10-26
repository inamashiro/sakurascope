"""CSV helpers that neutralize spreadsheet formula injection."""

from __future__ import annotations

from typing import Any


def csv_safe_cell(value: Any) -> str:
    """
    Convert a value to a CSV cell string.

    Prefix dangerous leading characters so Excel/LibreOffice do not execute formulas.
    """
    if value is None:
        return ""
    text = ("true" if value else "false") if isinstance(value, bool) else str(value)
    if text and text[0] in {"=", "+", "-", "@", "\t", "\r"}:
        return "'" + text
    return text
