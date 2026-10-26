# Automation, Incremental Collect & GitHub Actions (Phase 7)

## Local collect modes

```powershell
# Full collect of enabled sources
python -m sakurascope collect

# Skip sources that succeeded within the last 24 hours
python -m sakurascope collect --incremental
python -m sakurascope collect --incremental --incremental-hours 12

# Only sources that failed previously / never succeeded
python -m sakurascope collect --retry-failed

# Extra in-run retries after failures
python -m sakurascope collect --run-retries 1

# Change event summary
python -m sakurascope changes --hours 48
```

Exit codes: `0` ok / nothing to do, `1` partial failures, `2` usage, `3` config.

## Change kinds

| Kind | Meaning |
|------|---------|
| `new_discovery` | 新发现 |
| `content_updated` | 正文更新 |
| `application_date_maybe_changed` | 申请日期可能变化（需人工核验） |
| `page_unreachable` | 原页面无法访问（≠ 招生结束） |
| `collect_failed` | 采集失败（≠ 招生结束） |
| `suspected_duplicate` | 疑似重复 |
| `needs_human_review` | 需要人工复核 |

## GitHub Actions

Workflows:

- `.github/workflows/ci.yml` — tests + ruff on PR/push
- `.github/workflows/collect.yml` — schedule + `workflow_dispatch`

### Persistence limits (read carefully)

- Actions runners **do not** keep your SQLite DB between runs.
- This project uploads `reports/` and optional DB snapshots as **artifacts** with short retention.
- Artifacts are **not** a durable research archive. Download them if you need history.
- Never commit live databases or API keys.
- Default `sources.example.yaml` entries are MOCK/disabled — enable real public sources in your own config before expecting collect output.

### Secrets

- Optional: `SAKURASCOPE_AI_API_KEY` (only if you also enable AI in settings)
- Do not print secrets in logs
