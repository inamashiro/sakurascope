# Testing Guide

SakuraScope tests are offline-first: unit tests use fixtures and `httpx.MockTransport`. They must not hit the live internet or invent admissions facts.

## Quick run

```powershell
cd D:\NIGHTHARBOR
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
```

Full release checklist:

```powershell
python scripts/preflight.py
```

## Layout

| Path | Purpose |
|------|---------|
| `tests/unit/` | Fast, isolated tests (config, parsers, extractors, collect, filter, AI validation) |
| `tests/fixtures/` | MOCK HTML/RSS/YAML only — never treat as real recruitment |
| `scripts/eval_extraction.py` | Rule extraction eval against fixture corpus |

## Conventions

- Prefer `MockTransport` over real HTTP.
- PDF tests generate bytes with PyMuPDF in-process (no fixture files required).
- Example sources in `config/sources.example.yaml` stay `enabled: false`.
- Do not assert “eligibility confirmed” unless a test explicitly constructs that status after human-style verification fields.
- Network-using manual smoke tests are optional and out of CI.

## What CI runs

`.github/workflows/ci.yml` installs the package with `[dev]` extras and runs `pytest` + `ruff`. Collect workflow DB is ephemeral — see [AUTOMATION.md](AUTOMATION.md).

## Adding a test

1. Keep it deterministic and offline.
2. Mark MOCK content clearly in fixtures / source notes.
3. For collectors, assert `parse_status`, evidence fields, and that failures are recorded as failures (not “no admission”).
