"""Core domain layer for NDL.

This package intentionally depends only on the Python standard library and
Pydantic. Outer layers depend on these objects, not the other way around.
"""

from ndl.core.errors import (
    BrowserError,
    ConfigError,
    ConvertError,
    EmptyContentError,
    FetchError,
    HTTPError,
    InvalidArgumentError,
    InvalidURLError,
    NDLError,
    NetworkError,
    ParseError,
    RateLimitedError,
    RobotsBlockedError,
    RuleError,
    RuleLoadError,
    RuleNotFoundError,
    RuleValidationError,
    SelectorNotFoundError,
    StorageError,
    UserError,
)
from ndl.core.models import Chapter, ChapterStub, Novel, NovelStatus
from ndl.core.progress import ProgressCallback, ProgressEvent, ProgressKind, ProgressStage
from ndl.core.protocols import Fetcher, Parser, Reader, Writer

__all__ = [
    "BrowserError",
    "Chapter",
    "ChapterStub",
    "ConfigError",
    "ConvertError",
    "EmptyContentError",
    "FetchError",
    "Fetcher",
    "HTTPError",
    "InvalidArgumentError",
    "InvalidURLError",
    "NDLError",
    "NetworkError",
    "Novel",
    "NovelStatus",
    "ParseError",
    "Parser",
    "ProgressCallback",
    "ProgressEvent",
    "ProgressKind",
    "ProgressStage",
    "RateLimitedError",
    "Reader",
    "RobotsBlockedError",
    "RuleError",
    "RuleLoadError",
    "RuleNotFoundError",
    "RuleValidationError",
    "SelectorNotFoundError",
    "StorageError",
    "UserError",
    "Writer",
]
