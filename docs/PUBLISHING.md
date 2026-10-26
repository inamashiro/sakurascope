# Publishing checklist (Phase 9)

SakuraScope is local-first OSS. Use this before the first public push.

## Before first push

1. Confirm `python scripts/preflight.py` prints `PREFLIGHT OK`.
2. Replace placeholder URLs in `pyproject.toml` → `[project.urls]` with your real repo.
3. Copy `config/sources.example.yaml` locally as needed; keep MOCK sources disabled in the public tree.
4. Ensure no `.env`, `*.db`, or personal notes are staged (`git status`).
5. Create the remote (GitHub / Cursor Origin / other), then push the branch you choose.

## Suggested first commands

```powershell
# If not already initialized:
git init
git add -A
git status   # review carefully

# Commit only when you explicitly want a snapshot (ask the agent or run yourself):
# git commit -m "Initial public release of SakuraScope 0.8.0"

git remote add origin <YOUR_REPO_URL>
git push -u origin HEAD
```

## After the repo exists

- Enable GitHub Actions; `ci.yml` should run on push/PR.
- Treat `collect.yml` artifacts as short-lived — not a durable research DB ([AUTOMATION.md](AUTOMATION.md)).
- Tag releases optionally: `git tag v0.8.0` after the commit you want to pin.

## What not to publish

- Live API keys, cookies, or applicant PII
- Scraped databases that mix personal annotations with public text without review
- Enabled sources pointing at private or login-only pages
