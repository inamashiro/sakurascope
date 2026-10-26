"""OpenAI-compatible Chat Completions client (httpx; optional)."""

from __future__ import annotations

import contextlib
import json
from typing import Any

import httpx

from sakurascope.extraction.ai.provider import LlmResponse
from sakurascope.utils.logging import get_logger

logger = get_logger("extraction.ai.openai")


class AiProviderError(Exception):
    """Raised for transport, timeout, rate-limit, or API errors."""


class OpenAICompatibleProvider:
    """Calls POST {base_url}/chat/completions with a bearer token."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 60.0,
        temperature: float = 0.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise AiProviderError("API key is required for OpenAI-compatible provider")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete(self, *, system: str, user: str) -> LlmResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = self._client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AiProviderError(f"AI request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise AiProviderError(f"AI transport error: {exc}") from exc

        if response.status_code == 429:
            raise AiProviderError("AI rate limited (HTTP 429)")
        if response.status_code >= 400:
            raise AiProviderError(
                f"AI API error HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise AiProviderError(f"AI response was not JSON: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AiProviderError(f"Unexpected AI response shape: {data!r}") from exc

        if not isinstance(content, str) or not content.strip():
            raise AiProviderError("AI returned empty content")

        finish = None
        with contextlib.suppress(KeyError, IndexError, TypeError):
            finish = data["choices"][0].get("finish_reason")

        logger.info("AI completion ok (model=%s, finish=%s)", self.model, finish)
        return LlmResponse(
            content=content, model=data.get("model", self.model), finish_reason=finish
        )
