"""Shared helpers for HTTP and browser fetchers."""

from __future__ import annotations

from ndl.rules.schema import RetryRule, SourceRule


def resolve_headers(rule: SourceRule) -> dict[str, str]:
    """Return request headers with a guaranteed User-Agent matching robots checks."""
    headers = dict(rule.fetcher.headers)
    if not any(key.lower() == "user-agent" for key in headers):
        headers["User-Agent"] = f"ndl/{rule.id}"
    return headers


def backoff_delay(retry: RetryRule, attempt: int) -> float:
    """Return the next retry delay in seconds for `attempt` (0-based)."""
    if retry.backoff == "fixed":
        return 1.0
    return 2.0**attempt
