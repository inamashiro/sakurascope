"""Local PDF text extraction (no OCR upload service)."""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf


@dataclass(frozen=True)
class ParsedPdf:
    text: str
    page_count: int
    parse_status: str
    error_message: str | None = None
    is_encrypted: bool = False
    is_likely_scan: bool = False


def parse_pdf(data: bytes) -> ParsedPdf:
    """
    Extract readable text from a PDF byte payload.

    Limitations are reported explicitly:
    - encrypted / password-protected
    - empty text (often scanned images; OCR intentionally out of scope)
    - corrupt or unreadable files
    """
    if not data:
        return ParsedPdf(
            text="",
            page_count=0,
            parse_status="failed",
            error_message="Empty PDF payload",
        )

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        return ParsedPdf(
            text="",
            page_count=0,
            parse_status="failed",
            error_message=f"PDF open failed: {exc}",
        )

    try:
        if doc.is_encrypted:
            # Try empty password; if still locked, report limitation.
            try:
                unlocked = doc.authenticate("")
            except Exception:  # noqa: BLE001
                unlocked = 0
            if not unlocked:
                return ParsedPdf(
                    text="",
                    page_count=doc.page_count,
                    parse_status="failed",
                    error_message=(
                        "PDF is encrypted/password-protected. "
                        "SakuraScope will not bypass encryption."
                    ),
                    is_encrypted=True,
                )

        chunks: list[str] = []
        for page in doc:
            chunks.append(page.get_text("text") or "")
        text = "\n".join(part.strip() for part in chunks if part and part.strip()).strip()
        page_count = doc.page_count
    finally:
        doc.close()

    if not text:
        return ParsedPdf(
            text="",
            page_count=page_count,
            parse_status="failed",
            error_message=(
                "No extractable text in PDF. It may be a scanned/image-only document. "
                "OCR upload services are intentionally out of default scope."
            ),
            is_likely_scan=True,
        )

    return ParsedPdf(text=text, page_count=page_count, parse_status="ok")
