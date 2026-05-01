"""NDL exception hierarchy."""

from __future__ import annotations

from http import HTTPStatus


class NDLError(Exception):
    """Base class for all user-visible NDL errors."""

    exit_code = 1

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def user_message(self) -> str:
        """Return a concise user-facing message."""
        if self.detail:
            return f"{self.message}\n\n{self.detail}"
        return self.message


class UserError(NDLError):
    """Invalid user input; not considered an application bug."""

    exit_code = 2


class InvalidURLError(UserError):
    """The provided URL is syntactically invalid or unsupported."""


class InvalidArgumentError(UserError):
    """A CLI/API argument failed validation."""


class ConfigError(NDLError):
    """Configuration is missing or invalid."""

    exit_code = 78


class RuleError(NDLError):
    """Base class for rule loading, validation, and resolution failures."""


class RuleNotFoundError(RuleError):
    """No enabled rule matches a URL."""

    def __init__(self, url: str) -> None:
        super().__init__(
            "No source rule matched the URL.",
            detail=f"URL: {url}\nTry `ndl rules list` or add a custom YAML rule.",
        )
        self.url = url


class RuleValidationError(RuleError):
    """A YAML rule failed schema validation."""


class RuleLoadError(RuleError):
    """A rule file could not be read or parsed."""


class FetchError(NDLError):
    """Base class for network and fetcher failures."""

    exit_code = 69


class HTTPError(FetchError):
    """A non-success HTTP status remained after retries."""

    def __init__(self, url: str, status_code: int) -> None:
        try:
            phrase = HTTPStatus(status_code).phrase
        except ValueError:
            phrase = "HTTP error"
        super().__init__(f"HTTP request failed with {status_code} {phrase}.", detail=f"URL: {url}")
        self.url = url
        self.status_code = status_code


class RobotsBlockedError(FetchError):
    """robots.txt forbids fetching the requested URL."""


class RateLimitedError(FetchError):
    """The upstream site explicitly rate-limited the request."""


class NetworkError(FetchError):
    """DNS, timeout, connection, or transport failure."""


class BrowserError(FetchError):
    """Browser-backed fetching failed."""


class ParseError(NDLError):
    """Base class for parser failures."""


class SelectorNotFoundError(ParseError):
    """A required selector did not match any node."""

    def __init__(self, selector: str) -> None:
        super().__init__(
            "Required selector did not match any node.", detail=f"Selector: {selector}"
        )
        self.selector = selector


class EmptyContentError(ParseError):
    """Parsed content was empty after cleaning."""


class StorageError(NDLError):
    """Persistence layer failure."""


class ConvertError(NDLError):
    """File conversion failure."""
