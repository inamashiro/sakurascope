"""Aggregate change events into an explainable summary."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sakurascope.models.domain import ChangeEventRecord

CHANGE_KIND_LABELS = {
    "new_discovery": "新发现",
    "content_updated": "正文更新",
    "application_date_maybe_changed": "申请日期可能变化",
    "page_unreachable": "原页面无法访问",
    "collect_failed": "采集失败",
    "suspected_duplicate": "疑似重复",
    "needs_human_review": "需要人工复核",
}


@dataclass
class ChangeSummary:
    since: datetime | None
    total: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    events: list[ChangeEventRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def render_text(self) -> str:
        lines = [
            "SakuraScope change summary",
            f"  since : {self.since.isoformat() if self.since else '(all)'}",
            f"  total : {self.total}",
            "",
            "By kind:",
        ]
        if not self.by_kind:
            lines.append("  (no events)")
        else:
            for kind, count in sorted(self.by_kind.items(), key=lambda kv: (-kv[1], kv[0])):
                label = CHANGE_KIND_LABELS.get(kind, kind)
                lines.append(f"  - {kind} ({label}): {count}")
        lines.append("")
        lines.append("Reminders:")
        lines.append("  - page_unreachable / collect_failed ≠ admissions closed")
        lines.append("  - application_date_maybe_changed needs human verification")
        for note in self.notes:
            lines.append(f"  - {note}")
        if self.events:
            lines.append("")
            lines.append("Recent events:")
            for event in self.events[:30]:
                when = event.detected_at.isoformat() if event.detected_at else ""
                lines.append(f"  [{when}] {event.change_kind}: {event.message}")
        return "\n".join(lines)


def summarize_changes(
    events: list[ChangeEventRecord],
    *,
    since: datetime | None = None,
    limit: int = 100,
) -> ChangeSummary:
    filtered = events
    if since is not None:
        filtered = [e for e in events if e.detected_at and e.detected_at >= since]
    filtered = sorted(
        filtered,
        key=lambda e: e.detected_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )[:limit]
    counts = Counter(e.change_kind for e in filtered)
    notes: list[str] = []
    if counts.get("page_unreachable") or counts.get("collect_failed"):
        notes.append("Fetch failures were recorded separately from opportunity expiry.")
    return ChangeSummary(
        since=since,
        total=len(filtered),
        by_kind=dict(counts),
        events=filtered,
        notes=notes,
    )


def since_from_hours(hours: float | None) -> datetime | None:
    if hours is None or hours <= 0:
        return None
    return datetime.now(UTC) - timedelta(hours=hours)
