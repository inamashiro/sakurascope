# Contributing to SakuraScope

Thanks for helping improve a local-first research tool. Contributions should keep evidence honest and access controls intact.

## Ground rules

- Topic match ≠ open recruitment ≠ confirmed eligibility.
- Do not invent facts, URLs, quotes, deadlines, or eligibility.
- Do not add bypasses for login walls, CAPTCHA, paywalls, robots.txt, or PDF encryption.
- OCR cloud upload is out of default scope; PDF support is local text extraction only.
- Prefer offline tests (`httpx.MockTransport`, fixtures). Do not hit live university sites in CI.

## Dev setup

```powershell
cd D:\NIGHTHARBOR   # or your clone path
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests scripts
python scripts/preflight.py
```

## Workflow

1. Open an issue (or describe the change) before large features.
2. Keep MOCK sources disabled and clearly labeled.
3. Add/adjust tests for collectors, parsers, and extraction status tiers.
4. Update docs when behavior or limitations change (`docs/KNOWN_LIMITATIONS.md` especially).
5. Run `python scripts/preflight.py` before opening a PR.

## Pull requests

- One focused change per PR when possible.
- Explain *why* in the description; link evidence of test runs.
- Do not commit `.env`, `*.db`, API keys, or personal application materials.

## Code style

- Python ≥ 3.11, `src/` layout, Ruff for lint/format.
- Prefer clear failure messages over silent empty results (especially for PDF / HTTP failures).
