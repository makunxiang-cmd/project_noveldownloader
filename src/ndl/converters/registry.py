"""Writer registry keyed by output format or file suffix."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ndl.converters.epub_writer import EpubWriter
from ndl.converters.txt_writer import TxtWriter
from ndl.core.errors import ConvertError
from ndl.core.protocols import Writer


class WriterRegistry:
    """Resolve Writer implementations by explicit format or output suffix."""

    def __init__(self, writers: Mapping[str, Writer] | None = None) -> None:
        self._writers: dict[str, Writer] = {}
        if writers is not None:
            for name, writer in writers.items():
                self.register(name, writer)

    def register(self, format: str, writer: Writer) -> None:
        """Register `writer` for `format`."""
        self._writers[_normalize_format(format)] = writer

    def get(self, output_path: Path | str | None = None, *, format: str | None = None) -> Writer:
        """Return the matching Writer or raise ConvertError."""
        key = _normalize_format(format) if format is not None else _format_from_path(output_path)
        try:
            return self._writers[key]
        except KeyError as exc:
            raise ConvertError(
                "Unsupported output format.",
                detail=f"Format: {key}\nSupported: {', '.join(self.formats())}",
            ) from exc

    def formats(self) -> tuple[str, ...]:
        """Return registered format names in stable order."""
        return tuple(sorted(self._writers))


def default_writer_registry() -> WriterRegistry:
    """Create the default TXT/EPUB writer registry."""
    return WriterRegistry({"txt": TxtWriter(), "epub": EpubWriter()})


def _format_from_path(output_path: Path | str | None) -> str:
    if output_path is None:
        raise ConvertError("Output format is required.", detail="Pass `format` or an output path.")
    suffix = Path(output_path).suffix
    if not suffix:
        raise ConvertError(
            "Output path has no suffix.",
            detail=f"Path: {output_path}\nPass `format` explicitly.",
        )
    return _normalize_format(suffix)


def _normalize_format(format: str) -> str:
    key = format.strip().lower()
    if key.startswith("."):
        key = key[1:]
    if not key:
        raise ConvertError("Output format is empty.")
    return key
