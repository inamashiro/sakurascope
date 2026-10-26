"""URL validation and light SSRF guards for outbound fetches."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

# Hostnames that must never be fetched by the collector.
_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}

_IP_LITERAL_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


class UnsafeUrlError(ValueError):
    """Raised when a URL is not allowed for fetching."""


def validate_public_http_url(url: str) -> str:
    """
    Allow only http(s) URLs that do not obviously target local/private networks.

    This is a best-effort guard, not a complete SSRF firewall. DNS rebinding
    and all edge cases are out of scope for Phase 2.
    """
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("URL is empty")

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL is missing a hostname")

    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        raise UnsafeUrlError(f"Blocked hostname: {host}")

    # Bracketed IPv6 or bare IPv4 literals.
    candidate = host
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]

    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        ip = None

    if ip is not None:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(f"Blocked IP address: {ip}")
    elif _IP_LITERAL_RE.match(host):
        # Malformed IP-like host that did not parse — reject defensively.
        raise UnsafeUrlError(f"Blocked IP-like hostname: {host}")

    return url.strip()


def robots_url_for(page_url: str) -> str:
    """Return the robots.txt URL for the same origin as page_url."""
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
