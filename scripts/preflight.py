#!/usr/bin/env python3
"""Release / Phase-8 preflight checks for SakuraScope.

Runs offline-safe verification:
  1) import package
  2) ruff
  3) pytest
  4) extraction eval
  5) CLI help/status smoke
  6) required docs presence

Usage:
  python scripts/preflight.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    ".gitignore",
    ".env.example",
    "docs/ARCHITECTURE.md",
    "docs/DATA_MODEL.md",
    "docs/SOURCES.md",
    "docs/TESTING.md",
    "docs/SECURITY.md",
    "docs/LEARNING_GUIDE.md",
    "docs/KNOWN_LIMITATIONS.md",
    "docs/AUTOMATION.md",
    "docs/AI.md",
    "docs/DASHBOARD.md",
    "docs/FILTERING.md",
    "docs/PUBLISHING.md",
    ".github/workflows/ci.yml",
    ".github/workflows/collect.yml",
]


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(completed.returncode)


def main() -> int:
    py = sys.executable
    failures: list[str] = []

    missing = [p for p in REQUIRED_DOCS if not (ROOT / p).is_file()]
    if missing:
        print("Missing required files:")
        for path in missing:
            print(f"  - {path}")
        failures.append("docs")
    else:
        print(f"Required docs/workflows present ({len(REQUIRED_DOCS)}).")

    if run([py, "-c", "import sakurascope; print(sakurascope.__version__)"]) != 0:
        failures.append("import")

    if run([py, "-m", "ruff", "check", "src", "tests", "scripts"]) != 0:
        failures.append("ruff")
    if run([py, "-m", "ruff", "format", "--check", "src", "tests", "scripts"]) != 0:
        failures.append("ruff-format")

    if run([py, "-m", "pytest", "-q"]) != 0:
        failures.append("pytest")

    if run([py, "scripts/eval_extraction.py"]) != 0:
        failures.append("eval")

    if run([py, "-m", "sakurascope", "help"]) != 0:
        failures.append("cli-help")
    if run([py, "-m", "sakurascope", "status"]) != 0:
        failures.append("cli-status")

    if failures:
        print("PREFLIGHT FAILED:", ", ".join(failures))
        return 1

    print("PREFLIGHT OK — SakuraScope looks ready for public release checklist.")
    print("Reminder: do not commit .env, *.db, or live API keys.")
    print("Next: see docs/PUBLISHING.md (commit / remote only when you choose).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
