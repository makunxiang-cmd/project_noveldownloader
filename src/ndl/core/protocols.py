"""Structural interfaces consumed by application services."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ndl.core.models import Chapter, ChapterStub, Novel


class Fetcher(Protocol):
    """Fetches a text resource from a URL."""

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        """Return response text for `url` or raise a FetchError."""

    async def aclose(self) -> None:
        """Release any underlying connections held by the fetcher."""


class Parser(Protocol):
    """Parses fetched text into domain objects."""

    def parse_index(self, html: str, *, source_url: str) -> tuple[Novel, list[ChapterStub]]:
        """Parse an index page into novel metadata and chapter stubs."""

    def parse_chapter(self, html: str, *, index: int, source_url: str) -> Chapter:
        """Parse a chapter page into a normalized chapter."""


class Writer(Protocol):
    """Writes a novel into an output format."""

    def write(self, novel: Novel, output_path: Path) -> Path:
        """Write `novel` and return the output path."""


class Reader(Protocol):
    """Reads a file into the Novel intermediate representation."""

    def read(self, input_path: Path) -> Novel:
        """Read `input_path` into a Novel object."""
