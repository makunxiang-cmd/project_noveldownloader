"""Filesystem path helpers shared across CLI and application layers."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_HOME = "NDL_HOME"
_LIBRARY_DB = "library.db"


def ndl_home() -> Path:
    """Return the NDL state directory (`$NDL_HOME` or `~/.ndl`)."""
    configured = os.environ.get(_ENV_HOME)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".ndl"


def library_db_path() -> Path:
    """Return the absolute path to the local library SQLite database."""
    return ndl_home() / _LIBRARY_DB
