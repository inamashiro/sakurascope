# Filtering & Reports (Phase 4)

## Research areas

Configured in `config/research_areas.yaml`:

- `name` — canonical label
- `weight` — used only for **topic relevance** scoring
- `keywords` — EN / JA / ZH (users may add more)

`topic_relevance_score` = average weight of matched areas.

**It is not an admission probability and must never be presented as one.**

## Buckets

| Bucket | Meaning |
|--------|---------|
| `research_topic_related` | Keywords matched; not an open call by itself |
| `official_application_info_found` | Public admission language observed |
| `admission_info_pending_verification` | Admission text present; still unverified |
| `eligibility_unconfirmed` | Default until a human confirms |
| `insufficient_info` | Too little structured signal |

## Report formats

```powershell
python -m sakurascope report
python -m sakurascope report --format markdown --format csv
python -m sakurascope report --area "Public Health" --require-admission-info
```

Outputs land in `reports/` by default.

- Markdown: human-readable dossier per opportunity + evidence quotes
- CSV: Excel-friendly; formula-leading cells are neutralized
- JSON: full structured records + filter metadata

Report generation time is labeled separately from any extracted application dates.
