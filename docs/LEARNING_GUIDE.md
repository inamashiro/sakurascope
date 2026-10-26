# Learning Guide

A short path through the codebase for contributors and curious users.

## Mental model

1. **Sources** (`config/*.yaml`) list public URLs you allow.
2. **Collect** fetches HTML / RSS / PDF → `page_snapshots` in SQLite.
3. **Extract** (rules-first, optional AI) produces opportunities + evidence spans.
4. **Filter / report / dashboard** help you review — they do not decide applications for you.

Review statuses are deliberate tiers. Never collapse “topic may match” into “eligible.”

## Suggested reading order

| Step | Where | Why |
|------|-------|-----|
| 1 | `README.md` | Install + CLI surface |
| 2 | `docs/ARCHITECTURE.md` | Phases and collect modes |
| 3 | `docs/DATA_MODEL.md` | Tables and evidence fields |
| 4 | `docs/SOURCES.md` | How to add real public sources |
| 5 | `src/sakurascope/collectors/service.py` | Orchestration |
| 6 | `src/sakurascope/extraction/rules.py` | How claims stay grounded |
| 7 | `docs/FILTERING.md` + `docs/DASHBOARD.md` | Review workflow |
| 8 | `docs/AI.md` | Opt-in AI contract |
| 9 | `docs/TESTING.md` + `docs/SECURITY.md` | Safe contribution |

## Local loop

```powershell
python -m sakurascope status
python -m sakurascope collect --source <id>   # after enabling a public source
python -m sakurascope report
python -m sakurascope dashboard
python -m pytest -q
```

## Common pitfalls

- Enabling MOCK `example.invalid` sources and expecting real pages.
- Treating relevance score as admission chance.
- Assuming Actions artifacts are a durable research database ([AUTOMATION.md](AUTOMATION.md)).
- Expecting OCR on scanned PDFs — report `is_likely_scan` / failed parse instead.
