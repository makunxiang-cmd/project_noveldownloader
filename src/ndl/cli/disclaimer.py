"""First-run disclaimer gate for network download commands."""

from __future__ import annotations

import os
from pathlib import Path

from ndl.application.paths import ndl_home
from ndl.core.errors import InvalidArgumentError

_ACCEPTED_FILE = "disclaimer.accepted"
_ENV_ACCEPT = "NDL_ACCEPT_DISCLAIMER"
_TRUTHY = {"1", "true", "yes", "y", "on"}


def ensure_download_disclaimer(*, accept: bool) -> None:
    """Require explicit acceptance before allowing network downloads."""
    marker = _disclaimer_marker()
    if marker.exists():
        return
    if accept or os.environ.get(_ENV_ACCEPT, "").strip().lower() in _TRUTHY:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("accepted\n", encoding="utf-8")
        return
    raise InvalidArgumentError(
        "Download disclaimer has not been accepted.",
        detail="Rerun with `--accept-disclaimer` after confirming you will only download lawful, allowed content and will respect site rules.",
    )


def _disclaimer_marker() -> Path:
    return ndl_home() / _ACCEPTED_FILE
