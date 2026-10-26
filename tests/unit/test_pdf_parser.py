"""PDF parser tests (local fixtures, no network, no OCR)."""

from __future__ import annotations

import pymupdf

from sakurascope.parsers.pdf import parse_pdf


def _text_pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _encrypted_pdf_bytes(text: str = "secret mock") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="sakura-secret",
        owner_pw="sakura-owner",
    )
    doc.close()
    return data


def test_parse_text_pdf_ok() -> None:
    raw = _text_pdf_bytes("MOCK 募集要項 epidemiology public health")
    parsed = parse_pdf(raw)
    assert parsed.parse_status == "ok"
    assert "募集要項" in parsed.text or "epidemiology" in parsed.text
    assert parsed.page_count >= 1
    assert parsed.is_encrypted is False


def test_parse_encrypted_pdf_reports_limitation() -> None:
    raw = _encrypted_pdf_bytes()
    parsed = parse_pdf(raw)
    assert parsed.parse_status == "failed"
    assert parsed.is_encrypted is True
    assert "encrypt" in (parsed.error_message or "").lower()
    assert parsed.text == ""


def test_parse_empty_payload() -> None:
    parsed = parse_pdf(b"")
    assert parsed.parse_status == "failed"


def test_parse_non_pdf_bytes() -> None:
    parsed = parse_pdf(b"not a pdf at all")
    assert parsed.parse_status == "failed"
