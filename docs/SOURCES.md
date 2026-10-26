# Source Configuration

SakuraScope only collects URLs you explicitly configure.

## File location

Default: `config/sources.example.yaml` (referenced by `config/settings.yaml` → `paths.sources_file`).

Copy the example to your own file (for example `config/sources.yaml`), point `sources_file` at it, and enable only public pages you are allowed to access.

## Fields

| Field | Meaning |
|-------|---------|
| `source_id` | Stable unique id |
| `source_name` | Human-readable label |
| `source_url` | Public `http`/`https` URL |
| `source_type` | Category (university site, RSS, PDF, …) |
| `collection_strategy` | `html`, `rss`, or `pdf` (PDF = local text extract, no OCR) |
| `enabled` | Must be `true` for default `collect` |
| `notes` | Free-form notes (use `[MOCK]` for fixtures) |

## Rules

- Respect robots.txt, site terms, rate limits, and copyright.
- Do not configure login-only, CAPTCHA, or paywalled pages.
- Do not enable mock/`example.invalid` sources expecting real data.
- A failed fetch is recorded as a **fetch failure**, never as “no admissions at this school.”

## CLI

```powershell
python -m sakurascope collect
python -m sakurascope collect --source some-source-id
python -m sakurascope collect --include-disabled
```
