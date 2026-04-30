"""Convert service that composes readers and writers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ndl.application.services._progress import emit_progress
from ndl.converters import WriterRegistry, default_writer_registry
from ndl.core.errors import ConvertError
from ndl.core.models import Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Reader
from ndl.parsers import TxtReader

ConvertInput = Novel | Path | str


class ConvertService:
    """Convert a Novel or supported input file into a target output file."""

    def __init__(
        self,
        *,
        readers: Mapping[str, Reader] | None = None,
        writer_registry: WriterRegistry | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self._readers = _normalize_readers(readers or {"txt": TxtReader()})
        self._writers = writer_registry or default_writer_registry()
        self._progress = progress

    async def convert(
        self,
        source: ConvertInput,
        output_path: Path,
        *,
        target_format: str | None = None,
    ) -> Path:
        """Convert `source` to `output_path` and return the written path."""
        await emit_progress(
            self._progress,
            kind="stage",
            stage="converting",
            total=2,
            done=0,
            message="Preparing conversion.",
        )
        novel = self._load_novel(source)
        await emit_progress(
            self._progress,
            kind="stage",
            stage="converting",
            total=2,
            done=1,
            current_title=novel.title,
            message="Selecting writer.",
        )
        writer = self._writers.get(output_path, format=target_format)

        await emit_progress(
            self._progress,
            kind="stage",
            stage="saving",
            total=2,
            done=1,
            current_title=novel.title,
            message=f"Writing output: {output_path}",
        )
        written = writer.write(novel, output_path)
        await emit_progress(
            self._progress,
            kind="done",
            stage="saving",
            total=2,
            done=2,
            current_title=novel.title,
            message="Conversion complete.",
        )
        return written

    def _load_novel(self, source: ConvertInput) -> Novel:
        if isinstance(source, Novel):
            return source
        path = Path(source)
        reader = self._reader_for(path)
        return reader.read(path)

    def _reader_for(self, input_path: Path) -> Reader:
        suffix = _suffix_format(input_path)
        try:
            return self._readers[suffix]
        except KeyError as exc:
            raise ConvertError(
                "Unsupported input format.",
                detail=f"Format: {suffix}\nSupported: {', '.join(sorted(self._readers))}",
            ) from exc


def _normalize_readers(readers: Mapping[str, Reader]) -> dict[str, Reader]:
    return {_normalize_format(name): reader for name, reader in readers.items()}


def _suffix_format(path: Path) -> str:
    if not path.suffix:
        raise ConvertError(
            "Input path has no suffix.",
            detail=f"Path: {path}",
        )
    return _normalize_format(path.suffix)


def _normalize_format(format: str) -> str:
    key = format.strip().lower()
    if key.startswith("."):
        key = key[1:]
    if not key:
        raise ConvertError("Input format is empty.")
    return key
