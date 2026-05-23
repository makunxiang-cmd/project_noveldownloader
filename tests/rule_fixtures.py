"""Helpers for loading test-only source rule fixtures."""

from __future__ import annotations

from pathlib import Path

from ndl.rules.loader import load_rule_file
from ndl.rules.schema import SourceRule

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_STATIC_RULE_PATH = REPO_ROOT / "tests" / "fixtures" / "rules" / "example_static.yaml"


def load_example_static_rule() -> SourceRule:
    """Load the test-only example_static source rule fixture."""
    return load_rule_file(EXAMPLE_STATIC_RULE_PATH)
