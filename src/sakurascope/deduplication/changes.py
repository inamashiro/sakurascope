"""Snapshot / field change detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChangeKind = Literal[
    "new_discovery",
    "content_updated",
    "application_date_maybe_changed",
    "page_unreachable",
    "collect_failed",
    "suspected_duplicate",
    "needs_human_review",
]


@dataclass(frozen=True)
class ChangeEventDraft:
    change_kind: ChangeKind
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    snapshot_id: str | None = None
    source_id: str | None = None
    details: dict | None = None


def detect_snapshot_changes(
    *,
    previous_hash: str | None,
    current_hash: str | None,
    previous_deadline: str | None,
    current_deadline: str | None,
    parse_ok: bool,
    http_status: int | None,
    is_first_sighting: bool,
) -> list[ChangeEventDraft]:
    """
    Compare previous vs current observation for the same normalized URL.

    Page unreachable is NOT the same as opportunity expiry.
    """
    events: list[ChangeEventDraft] = []

    if not parse_ok:
        if http_status is not None and http_status >= 400:
            events.append(
                ChangeEventDraft(
                    change_kind="page_unreachable",
                    message=(
                        f"Page returned HTTP {http_status}. "
                        "This is a fetch/access failure, not proof that admissions closed."
                    ),
                )
            )
        else:
            events.append(
                ChangeEventDraft(
                    change_kind="collect_failed",
                    message="Collection/parse failed. Do not infer admissions status from this.",
                )
            )
        return events

    if is_first_sighting:
        events.append(
            ChangeEventDraft(
                change_kind="new_discovery",
                message="First successful snapshot for this normalized URL.",
            )
        )
        return events

    if previous_hash and current_hash and previous_hash != current_hash:
        events.append(
            ChangeEventDraft(
                change_kind="content_updated",
                message="Normalized content hash changed since the previous successful snapshot.",
                details={"previous_hash": previous_hash, "current_hash": current_hash},
            )
        )

    if previous_deadline != current_deadline and (previous_deadline or current_deadline):
        events.append(
            ChangeEventDraft(
                change_kind="application_date_maybe_changed",
                message=(
                    "Extracted application deadline text differs from the previous observation. "
                    "Needs human verification against the official page."
                ),
                details={
                    "previous_deadline": previous_deadline,
                    "current_deadline": current_deadline,
                },
            )
        )

    return events
