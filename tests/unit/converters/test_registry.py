"""Unit tests for the writer registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from ndl.converters.registry import WriterRegistry, default_writer_registry
from ndl.converters.txt_writer import TxtWriter
from ndl.core.errors import ConvertError


def test_registry_resolves_by_suffix_case_insensitively() -> None:
    writer = TxtWriter()
    registry = WriterRegistry({"txt": writer})

    assert registry.get(Path("book.TXT")) is writer


def test_registry_resolves_by_explicit_format() -> None:
    writer = TxtWriter()
    registry = WriterRegistry({".txt": writer})

    assert registry.get(format="TXT") is writer


def test_registry_rejects_unknown_format() -> None:
    registry = WriterRegistry({"txt": TxtWriter()})

    with pytest.raises(ConvertError, match="Unsupported output format"):
        registry.get(Path("book.pdf"))


def test_default_registry_supports_txt_and_epub() -> None:
    registry = default_writer_registry()

    assert registry.formats() == ("epub", "txt")
