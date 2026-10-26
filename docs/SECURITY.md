# Security & Responsible Use

SakuraScope is a **local-first research assistant**. It collects only URLs you configure and never claims to bypass access controls.

## Non-negotiables

- Do **not** configure login-only, CAPTCHA, paywalled, or private intranet pages.
- Do **not** ask the tool to defeat robots.txt, encryption, or DRM. Encrypted PDFs are reported as parse failures.
- Do **not** commit `.env`, API keys, cookies, or personal application materials.
- OCR cloud upload services are **out of default scope** (PDF text extraction is local via PyMuPDF only).

## Secrets

| Item | Guidance |
|------|----------|
| `.env` | Local only; start from `.env.example` |
| AI API key | Opt-in; required only when `ai.enabled: true` |
| SQLite DB | Local under `data/`; may contain scraped public text — treat as sensitive if you added personal notes |
| GitHub Actions | Do not put durable secrets into collect artifacts casually |

## Evidence honesty

- Topic keyword match ≠ open recruitment ≠ confirmed eligibility.
- Failed fetch / encrypted PDF / empty scan ≠ “school not recruiting.”
- Optional AI must not invent URLs, quotes, deadlines, or eligibility; invalid AI JSON falls back to rules.

## Network & robots

HTTP client respects robots.txt when enabled in settings, applies request intervals, and records blocked fetches. Rate-limit and copyright obligations remain the operator’s responsibility.

## Reporting issues

If you find a path that stores secrets in reports, logs credentials, or encourages bypassing access controls, treat it as a bug — open an issue and avoid sharing real keys in the report.
