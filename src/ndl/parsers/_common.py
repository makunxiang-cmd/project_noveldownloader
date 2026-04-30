"""Internal helpers shared by HTML parser modules."""

from __future__ import annotations

from typing import Any

from ndl.core.errors import ParseError
from ndl.rules.schema import Selector
from ndl.rules.selector import extract_selector


def extract_text(selector: Selector, root: Any, *, base_url: str | None = None) -> str:
    """Run a Selector and assert a single string value."""
    value = extract_selector(selector, root, base_url=base_url)
    if isinstance(value, list):
        raise ParseError(
            "Selector returned multiple values where one was expected.",
            detail=f"Selector: {selector.selector}",
        )
    return value
