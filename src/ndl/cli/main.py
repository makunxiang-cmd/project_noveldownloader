"""Typer CLI entry point for NDL."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.cli.disclaimer import ensure_download_disclaimer
from ndl.cli.renderers import cli_progress
from ndl.core.errors import NDLError
from ndl.rules import load_rule_file

app = typer.Typer(
    name="ndl",
    help="NDL - NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)
rules_app = typer.Typer(help="Rule file utilities.", no_args_is_help=True)


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


@app.command()
def convert(
    input_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Input file to convert.",
        ),
    ],
    output_path: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path."),
    ],
    target_format: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Explicit output format."),
    ] = None,
) -> None:
    """Convert a local novel file to another supported format."""
    try:
        written = asyncio.run(_convert(input_path, output_path, target_format=target_format))
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Wrote {written}")


@app.command()
def download(
    url: Annotated[str, typer.Argument(help="Novel index URL to download.")],
    output_path: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path."),
    ],
    target_format: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Explicit output format."),
    ] = None,
    accept_disclaimer: Annotated[
        bool,
        typer.Option(
            "--accept-disclaimer",
            help="Accept the lawful-use download disclaimer for this machine.",
        ),
    ] = False,
) -> None:
    """Download a rule-matched novel and write it to TXT or EPUB."""
    try:
        ensure_download_disclaimer(accept=accept_disclaimer)
        written = asyncio.run(_download(url, output_path, target_format=target_format))
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Wrote {written}")


@rules_app.command("validate")
def rules_validate(
    rule_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="YAML rule file to validate.",
        ),
    ],
) -> None:
    """Validate a YAML source rule file."""
    try:
        rule = load_rule_file(rule_path)
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Rule valid: {rule.id}")


app.add_typer(rules_app, name="rules")


async def _download(url: str, output_path: Path, *, target_format: str | None) -> Path:
    container = ServiceContainer()
    async with cli_progress() as progress:
        novel = await container.download(url, progress=progress)
        return await container.convert_service(progress=progress).convert(
            novel, output_path, target_format=target_format
        )


async def _convert(input_path: Path, output_path: Path, *, target_format: str | None) -> Path:
    container = ServiceContainer()
    async with cli_progress() as progress:
        return await container.convert_service(progress=progress).convert(
            input_path, output_path, target_format=target_format
        )


def _raise_cli_error(exc: NDLError) -> NoReturn:
    typer.echo(exc.user_message(), err=True)
    raise typer.Exit(exc.exit_code)
