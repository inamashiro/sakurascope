# SakuraScope

**Japan Research & Graduate Opportunity Intelligence**

自动搜集、整理、去重、追踪并报告日本大学 / 研究室 / 招生公告等**公开**信息的本地工具。

## 当前进度（阶段 0–9）

已完成：采集（HTML / RSS / **PDF 文本抽取，无 OCR**）、抽取、筛选报告、Streamlit、可选 AI、变化摘要、GitHub Actions、测试/安全/学习文档、发布前检查，以及公开发布文档（`CONTRIBUTING` / `CHANGELOG` / `docs/PUBLISHING.md`）。

证据分层始终成立：**主题相关 ≠ 公开招生 ≠ 已确认资格**。本工具不代替你做申请决策，也不绕过访问控制。首次推远程前请看 [docs/PUBLISHING.md](docs/PUBLISHING.md)。

## 安装与命令

```powershell
cd D:\NIGHTHARBOR
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

python -m sakurascope status
python -m sakurascope collect
python -m sakurascope collect --incremental
python -m sakurascope collect --retry-failed --run-retries 1
python -m sakurascope changes --hours 48
python -m sakurascope report
python -m sakurascope dashboard
python -m pytest
python scripts/preflight.py
```

配置真实公开源：复制 `config/sources.example.yaml`，将 `collection_strategy` 设为 `html` / `rss` / `pdf`，仅启用你有权访问的页面。自动化说明见 [docs/AUTOMATION.md](docs/AUTOMATION.md)。

## 文档

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 架构与阶段 |
| [DATA_MODEL](docs/DATA_MODEL.md) | 存储与证据字段 |
| [SOURCES](docs/SOURCES.md) | 源配置 |
| [TESTING](docs/TESTING.md) | 测试约定 |
| [SECURITY](docs/SECURITY.md) | 安全与负责任使用 |
| [LEARNING_GUIDE](docs/LEARNING_GUIDE.md) | 阅读路径 |
| [KNOWN_LIMITATIONS](docs/KNOWN_LIMITATIONS.md) | 已知限制 |
| [PUBLISHING](docs/PUBLISHING.md) | 首次公开推送检查清单 |
| [CONTRIBUTING](CONTRIBUTING.md) / [CHANGELOG](CHANGELOG.md) | 贡献与版本记录 |
| [AI](docs/AI.md) / [DASHBOARD](docs/DASHBOARD.md) / [FILTERING](docs/FILTERING.md) | 可选 AI、面板、筛选 |

## 实际测试状态（阶段 9 / 包版本 0.8.0）

| 检查 | 结果 |
|------|------|
| `pytest` | **64 passed** |
| `ruff check` / `ruff format --check` | **All checks passed** |
| `scripts/preflight.py` | **PREFLIGHT OK** |
| PDF | 文本 PDF 可抽取；加密 / 扫描件明确失败（无 OCR）；依赖 `pymupdf>=1.24,<2` |
| Git | 本地已 `git init`（`main`）；**尚未**做首次 commit / remote（见 PUBLISHING） |
| GitHub Actions | `ci.yml` + `collect.yml`（DB 默认不持久） |
