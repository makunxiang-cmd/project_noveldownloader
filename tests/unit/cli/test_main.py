"""Tests for the NDL CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from ndl import __version__
from ndl.cli.main import app

runner = CliRunner()


def test_version_flag_outputs_version_string() -> None:
    """`ndl --version` prints the package version and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.stdout
    assert __version__ in result.stdout


def test_version_short_flag_outputs_version_string() -> None:
    """`ndl -V` is the short form of --version."""
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0, result.stdout
    assert __version__ in result.stdout
