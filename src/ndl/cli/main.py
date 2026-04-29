"""Typer CLI entry point for NDL."""

from __future__ import annotations

from typing import Annotated

import typer

from ndl import __version__

app = typer.Typer(
    name="ndl",
    help="NDL - NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    """Print version and exit when the version flag is supplied."""
    if value:
        typer.echo(f"NDL {__version__}")
        raise typer.Exit()


@app.callback()
def _callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """NDL - rule-driven Chinese novel downloader and format converter."""
