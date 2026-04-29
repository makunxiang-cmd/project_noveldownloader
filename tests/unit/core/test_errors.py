"""Tests for user-visible error behavior."""

from __future__ import annotations

from ndl.core.errors import FetchError, RuleNotFoundError


def test_rule_not_found_error_includes_url_and_exit_code() -> None:
    error = RuleNotFoundError("https://example.test/book/1")

    assert error.exit_code == 1
    assert "https://example.test/book/1" in error.user_message()


def test_fetch_errors_use_unavailable_exit_code() -> None:
    assert FetchError("temporary unavailable").exit_code == 69
