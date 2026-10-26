# Changelog

All notable changes to SakuraScope are documented here.

Format inspired by [Keep a Changelog](https://keepachangelog.com/). Versioning follows SemVer for the public CLI/package surface.

## [0.8.0] — 2026-10-25

### Added

- PDF collection strategy with local PyMuPDF text extraction (no OCR, no password bypass).
- Docs: `TESTING.md`, `SECURITY.md`, `LEARNING_GUIDE.md`.
- `scripts/preflight.py` release checklist (import, ruff, pytest, eval, CLI smoke, required files).
- Offline PDF unit + collect tests.

### Changed

- CLI `help` / `status` mark HTML / RSS / PDF collectors ready.
- Dependency pin: `pymupdf>=1.24,<2` (avoid PyMuPDF 2.x heavy extras).

### Notes

- Encrypted and image-only PDFs fail with explicit errors.
- GitHub Actions collect DB remains ephemeral unless artifacts are downloaded.

## [0.7.0] — 2026-10-25

### Added

- Incremental collect, retry-failed, in-run retries.
- `changes` CLI summary.
- GitHub Actions: `ci.yml`, `collect.yml`.

## [0.1.0] – [0.6.0] — 2026-10

Scaffold through optional AI extraction, Streamlit dashboard, filtering, and reports (Phases 0–6). See `docs/ARCHITECTURE.md`.
