"""End-to-end smoke that the post-install CLI smoke script reports OK."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "smoke_cli.py"


def _resolve_ndl_entry_point() -> str | None:
    candidate = Path(sys.executable).with_name("ndl")
    if candidate.exists():
        return str(candidate)
    return which("ndl")


def test_smoke_cli_reports_ok_against_dev_environment() -> None:
    ndl = _resolve_ndl_entry_point()
    if ndl is None:
        pytest.skip("`ndl` entry point not installed in this environment")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--ndl", ndl],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Smoke OK." in completed.stdout
    assert "Smoke FAILED:" not in completed.stdout
