"""Change summary tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sakurascope.models.domain import ChangeEventRecord
from sakurascope.monitoring.summary import summarize_changes


def test_summarize_changes_counts_and_reminder() -> None:
    now = datetime.now(UTC)
    events = [
        ChangeEventRecord(
            change_id="1",
            change_kind="page_unreachable",
            message="HTTP 404. not proof that admissions closed.",
            detected_at=now,
        ),
        ChangeEventRecord(
            change_id="2",
            change_kind="new_discovery",
            message="First successful snapshot",
            detected_at=now - timedelta(hours=1),
        ),
        ChangeEventRecord(
            change_id="3",
            change_kind="content_updated",
            message="hash changed",
            detected_at=now - timedelta(days=3),
        ),
    ]
    summary = summarize_changes(events, since=now - timedelta(hours=2), limit=10)
    assert summary.total == 2
    assert summary.by_kind["page_unreachable"] == 1
    assert summary.by_kind["new_discovery"] == 1
    text = summary.render_text()
    assert "page_unreachable" in text
    assert "admissions closed" in text.lower() or "≠" in text or "not" in text.lower()
