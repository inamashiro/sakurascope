# Known Limitations

Last updated with **Phase 9 (publication readiness on top of 0.8.0)**.

## Implemented

- Collect HTML / RSS / PDF (text layer only) → extract → filter → report → dashboard → optional AI
- Incremental collect, retry-failed, in-run retries, change summary
- GitHub Actions CI + scheduled collect with artifact upload
- TESTING / SECURITY / LEARNING_GUIDE docs and `scripts/preflight.py`
- CONTRIBUTING / CHANGELOG / PUBLISHING docs; local `git init` expected before first push

## PDF constraints

- No OCR: image-only / scanned PDFs fail with an explicit `is_likely_scan` style message
- No password bypass: encrypted PDFs fail as encrypted
- No third-party OCR upload in the default path

## Not in scope (by design)

- Durable cloud database (local-first SQLite)
- Automatic merge of Actions artifacts into a long-term archive
- Deciding where you should apply or inventing eligibility

## Automation constraints

- GitHub Actions filesystem is ephemeral
- Uploaded artifacts expire (configured retention)
- Fetch failure ≠ opportunity closed
- Default example sources remain MOCK/disabled
