# SakuraScope Architecture

**Status:** Phase 0–8 product baseline complete; Phase 9 covers GitHub publication readiness (docs + local git).

## Collect modes

- `full` — all enabled sources  
- `incremental` — skip recently successful sources  
- `retry_failed` — only previously failed / never successful  
- `run_retries` — extra in-run passes for failures  

## Strategies

| `collection_strategy` | Behavior |
|-----------------------|----------|
| `html` | Fetch page, BeautifulSoup text |
| `rss` | Parse feed + optional entry pages |
| `pdf` | Fetch PDF, local PyMuPDF text extract (**no OCR**, no password bypass) |

## Automation

- Local CLI: `collect` / `changes` / `report` / `dashboard`  
- GitHub Actions: `ci.yml` (test), `collect.yml` (schedule + manual)  
- Actions DB is ephemeral unless artifacts are downloaded — see `docs/AUTOMATION.md`
- Release check: `python scripts/preflight.py`

## Roadmap

| Phase | Focus | Done? |
|-------|--------|-------|
| 0–6 | Core product + optional AI | Yes |
| 7 | Incremental, recovery, Actions | Yes |
| 8 | PDF, docs, preflight / release check | Yes |
| 9 | GitHub publication readiness (CONTRIBUTING / CHANGELOG / git) | Yes |
