"""Typer CLI entry point for NDL."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="ndl",
    help="NDL - NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _callback() -> None:
    """NDL - rule-driven Chinese novel downloader and format converter."""
