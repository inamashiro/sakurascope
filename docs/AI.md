# Optional AI Extraction (Phase 6)

## Default

**Rules only.** No API calls. No key required.

## Enabling (explicit)

1. Copy `.env.example` → `.env`
2. Set `SAKURASCOPE_AI_API_KEY=...` (never commit)
3. In `config/settings.yaml`:

```yaml
ai:
  enabled: true
  provider: openai_compatible
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
```

Having a key **without** `enabled: true` does nothing.

## Safety

- Page text is treated as untrusted data
- Emails/phones redacted before send
- AI JSON must match Pydantic schema
- Evidence quotes must be exact substrings of the source
- Invented URLs are rejected (`official_source_url` always from fetch)
- `eligibility_confirmed` is never accepted from the model
- Timeout / 429 / invalid JSON → keep rules result and mark notes

## Evaluation

```powershell
python scripts/eval_extraction.py
```

Reports field accuracy/coverage, evidence validity, false-fill rate, and failed samples on MOCK fixtures. Metrics are computed, not invented.

## Status honesty

Until you configure a key and enable AI, SakuraScope does **not** claim live AI extraction is active. The interface and tests use fake providers offline.
