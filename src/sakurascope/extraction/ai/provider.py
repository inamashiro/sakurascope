"""LLM provider protocol — keep model I/O separate from business logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LlmResponse:
    content: str
    model: str | None = None
    finish_reason: str | None = None


class LlmProvider(Protocol):
    """Minimal chat-completion interface for swappable providers."""

    name: str

    def complete(self, *, system: str, user: str) -> LlmResponse: ...
