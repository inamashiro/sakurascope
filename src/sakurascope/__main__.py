"""Allow `python -m sakurascope`."""

from __future__ import annotations

from sakurascope.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
