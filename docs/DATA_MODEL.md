# Data Model (Phase 3)

## Core tables

| Table | Purpose |
|-------|---------|
| `sources` | Configured public sources + last fetch status |
| `page_snapshots` | Raw fetch/parse observations |
| `opportunities` | Rule-extracted opportunity candidates |
| `evidence` | Field-level quotes tied to snapshots |
| `change_events` | New / update / unreachable / suspected duplicate / needs review |
| `run_logs` | Collect run summaries |
| `institutions` | Reserved schema (sparse use until enrichment) |

## Opportunity `review_status` (do not collapse)

- `insufficient_info`
- `research_topic_may_match` — keywords only; **not** admissions
- `public_admission_info_found` — public admission language present; still unverified
- `needs_review` — ambiguous duplicate or weak evidence
- `eligibility_confirmed` — **never set by rules**; humans only
- `needs_university_confirmation` — reserved for later workflows

## Evidence rules

- `quoted_text` must be a substring of the snapshot title/body
- Extractor inventing quotes is forbidden
- Missing fields stay `null`

## Change kinds

`new_discovery`, `content_updated`, `application_date_maybe_changed`, `page_unreachable`, `collect_failed`, `suspected_duplicate`, `needs_human_review`

`page_unreachable` ≠ opportunity expired.
