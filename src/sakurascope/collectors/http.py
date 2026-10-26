"""HTTP fetching with timeouts, retries, rate limiting, and size caps."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.robotparser import RobotFileParser

import httpx

from sakurascope.models.domain import FetchResult
from sakurascope.utils.logging import get_logger
from sakurascope.utils.urls import UnsafeUrlError, robots_url_for, validate_public_http_url

logger = get_logger("collectors.http")


@dataclass
class HttpClientConfig:
    user_agent: str
    timeout_seconds: float = 30.0
    max_retries: int = 2
    min_request_interval_seconds: float = 1.0
    max_response_bytes: int = 5_000_000
    respect_robots_txt: bool = True


class HttpFetcher:
    """Thin sync httpx wrapper. Inject a custom client for offline tests."""

    def __init__(
        self,
        config: HttpClientConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._owns_client = client is None
        self._client = client or httpx.Client(
            headers={"User-Agent": config.user_agent},
            timeout=config.timeout_seconds,
            follow_redirects=True,
        )
        self._last_request_at = 0.0
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpFetcher:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def fetch(self, url: str) -> FetchResult:
        try:
            safe_url = validate_public_http_url(url)
        except UnsafeUrlError as exc:
            return FetchResult(
                original_url=url,
                final_url=url,
                status_code=0,
                error_message=str(exc),
            )

        if self.config.respect_robots_txt and not self._allowed_by_robots(safe_url):
            return FetchResult(
                original_url=safe_url,
                final_url=safe_url,
                status_code=0,
                error_message="Blocked by robots.txt",
                blocked_by_robots=True,
            )

        last_error: str | None = None
        attempts = self.config.max_retries + 1
        for attempt in range(attempts):
            self._throttle()
            try:
                response = self._client.get(safe_url)
                body = response.content
                if len(body) > self.config.max_response_bytes:
                    return FetchResult(
                        original_url=safe_url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type"),
                        error_message=(
                            f"Response exceeds max_response_bytes={self.config.max_response_bytes}"
                        ),
                    )
                return FetchResult(
                    original_url=safe_url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type"),
                    body=body,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
            except httpx.TimeoutException as exc:
                last_error = f"Timeout: {exc}"
            except httpx.TransportError as exc:
                last_error = f"Transport error: {exc}"
            except httpx.HTTPError as exc:
                last_error = f"HTTP error: {exc}"

            logger.warning(
                "Fetch attempt %s/%s failed for %s: %s",
                attempt + 1,
                attempts,
                safe_url,
                last_error,
            )
            if attempt + 1 < attempts:
                time.sleep(min(2**attempt, 5))

        return FetchResult(
            original_url=safe_url,
            final_url=safe_url,
            status_code=0,
            error_message=last_error or "Unknown fetch failure",
        )

    def _throttle(self) -> None:
        interval = self.config.min_request_interval_seconds
        if interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_request_at = time.monotonic()

    def _allowed_by_robots(self, url: str) -> bool:
        robots_url = robots_url_for(url)
        if robots_url not in self._robots_cache:
            parser = RobotFileParser()
            try:
                self._throttle()
                response = self._client.get(robots_url)
                if response.status_code >= 400:
                    # Unreachable robots.txt: allow with caution (user-configured URL).
                    logger.warning(
                        "robots.txt unavailable (%s) for %s; allowing fetch",
                        response.status_code,
                        robots_url,
                    )
                    self._robots_cache[robots_url] = None
                else:
                    parser.parse(response.text.splitlines())
                    self._robots_cache[robots_url] = parser
            except httpx.HTTPError as exc:
                logger.warning(
                    "robots.txt fetch failed for %s: %s; allowing fetch", robots_url, exc
                )
                self._robots_cache[robots_url] = None

        parser = self._robots_cache.get(robots_url)
        if parser is None:
            return True
        return bool(parser.can_fetch(self.config.user_agent, url))
