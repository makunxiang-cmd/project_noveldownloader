"""Typer CLI entry point for NDL."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.cli.disclaimer import ensure_download_disclaimer
from ndl.cli.renderers import cli_progress
from ndl.core.errors import InvalidArgumentError, NDLError, UserError
from ndl.core.models import Novel
from ndl.rules import load_rule_file
from ndl.storage import NovelSummary

app = typer.Typer(
    name="ndl",
    help="NDL - NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)
rules_app = typer.Typer(help="Rule file utilities.", no_args_is_help=True)
library_app = typer.Typer(help="Local library commands.", no_args_is_help=True)


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
    save: Annotated[
        bool,
        typer.Option(
            "--save/--no-save",
            help="Save the downloaded novel into the local library.",
        ),
    ] = True,
) -> None:
    """Download a rule-matched novel and write it to TXT or EPUB."""
    try:
        ensure_download_disclaimer(accept=accept_disclaimer)
        written, novel_id = asyncio.run(
            _download(url, output_path, target_format=target_format, save=save)
        )
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Wrote {written}")
    if novel_id is not None:
        typer.echo(f"Saved to library: {novel_id}")


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", help="Host interface for the local Web UI."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", min=1, max=65535, help="Port for the local Web UI."),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable uvicorn auto-reload for development."),
    ] = False,
    accept_disclaimer: Annotated[
        bool,
        typer.Option(
            "--accept-disclaimer",
            help="Accept the lawful-use download disclaimer for this machine.",
        ),
    ] = False,
    allow_public_host: Annotated[
        bool,
        typer.Option(
            "--allow-public-host",
            help="Allow binding the Web UI to a non-localhost interface.",
        ),
    ] = False,
) -> None:
    """Serve the local Web UI."""
    try:
        ensure_download_disclaimer(accept=accept_disclaimer)
        _validate_serve_host(host, allow_public_host=allow_public_host)
        _run_web_server(host=host, port=port, reload=reload)
    except NDLError as exc:
        _raise_cli_error(exc)


@library_app.command("list")
def library_list() -> None:
    """List saved novels in the local library."""
    try:
        summaries = ServiceContainer().library_service().list()
    except NDLError as exc:
        _raise_cli_error(exc)
    if not summaries:
        typer.echo("No library entries.")
        return
    _console().print(_library_table(summaries))


@library_app.command("show")
def library_show(
    novel_id: Annotated[int, typer.Argument(min=1, help="Library novel id.")],
) -> None:
    """Show a saved novel header and chapter list."""
    try:
        novel = _load_library_novel(novel_id)
    except NDLError as exc:
        _raise_cli_error(exc)
    _print_library_novel(novel_id, novel)


@library_app.command("remove")
def library_remove(
    novel_id: Annotated[int, typer.Argument(min=1, help="Library novel id.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Remove without asking for confirmation."),
    ] = False,
) -> None:
    """Remove a saved novel from the local library."""
    try:
        container = ServiceContainer()
        library = container.library_service()
        novel = library.get(novel_id)
        if novel is None:
            raise UserError("Library entry not found.", detail=f"ID: {novel_id}")
    except NDLError as exc:
        _raise_cli_error(exc)
    if not yes and not typer.confirm(f"Remove '{novel.title}' from the library?"):
        typer.echo("Aborted.")
        raise typer.Exit(1)
    library.remove(novel_id)
    typer.echo(f"Removed library entry: {novel_id}")


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
app.add_typer(library_app, name="library")


async def _download(
    url: str,
    output_path: Path,
    *,
    target_format: str | None,
    save: bool,
) -> tuple[Path, int | None]:
    container = ServiceContainer()
    async with cli_progress() as progress:
        novel = await container.download(url, progress=progress)
        written = await container.convert_service(progress=progress).convert(
            novel, output_path, target_format=target_format
        )
    novel_id = container.library_service().save(novel) if save else None
    return written, novel_id


async def _convert(input_path: Path, output_path: Path, *, target_format: str | None) -> Path:
    container = ServiceContainer()
    async with cli_progress() as progress:
        return await container.convert_service(progress=progress).convert(
            input_path, output_path, target_format=target_format
        )


def _raise_cli_error(exc: NDLError) -> NoReturn:
    typer.echo(exc.user_message(), err=True)
    raise typer.Exit(exc.exit_code)


def _validate_serve_host(host: str, *, allow_public_host: bool) -> None:
    if allow_public_host or _is_local_bind(host):
        return
    raise InvalidArgumentError(
        "Refusing to expose the Web UI on a public interface.",
        detail=(
            f"Host: {host}\n"
            "Use the default 127.0.0.1 for local access, or pass --allow-public-host "
            "after confirming your network exposure is intentional."
        ),
    )


def _is_local_bind(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1", "[::1]"}


def _run_web_server(*, host: str, port: int, reload: bool) -> None:
    import uvicorn

    uvicorn.run(
        "ndl.web.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def _load_library_novel(novel_id: int) -> Novel:
    novel = ServiceContainer().library_service().get(novel_id)
    if novel is None:
        raise UserError("Library entry not found.", detail=f"ID: {novel_id}")
    return novel


def _console() -> Console:
    console = Console()
    return console if console.is_terminal else Console(width=140)


def _library_table(summaries: list[NovelSummary]) -> Table:
    table = Table()
    table.add_column("id", justify="right")
    table.add_column("title")
    table.add_column("author")
    table.add_column("status")
    table.add_column("chapter_count", justify="right")
    table.add_column("fetched_at")
    for summary in summaries:
        table.add_row(
            str(summary.id),
            summary.title,
            summary.author,
            summary.status,
            str(summary.chapter_count),
            _format_datetime(summary.fetched_at),
        )
    return table


def _print_library_novel(novel_id: int, novel: Novel) -> None:
    console = _console()
    console.print(f"[bold]{novel.title}[/bold]")
    console.print(f"id: {novel_id}")
    console.print(f"author: {novel.author}")
    console.print(f"status: {novel.status}")
    console.print(f"source_rule_id: {novel.source_rule_id}")
    if novel.source_url:
        console.print(f"source_url: {novel.source_url}")
    console.print(f"fetched_at: {_format_datetime(novel.fetched_at)}")
    if novel.summary:
        console.print(f"summary: {novel.summary}")

    table = Table(title="Chapters")
    table.add_column("index", justify="right")
    table.add_column("title")
    table.add_column("words", justify="right")
    for chapter in novel.chapters:
        table.add_row(str(chapter.index), chapter.title, str(chapter.word_count))
    console.print(table)


def _format_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
