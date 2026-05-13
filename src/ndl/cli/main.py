"""Typer CLI entry point for NDL."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.application.paths import rules_dir
from ndl.application.services import (
    RuleUpdatePlan,
    RuleUpdateService,
    SearchFailure,
    SearchOutcome,
    UpdateResult,
)
from ndl.cli.disclaimer import ensure_download_disclaimer
from ndl.cli.renderers import cli_progress
from ndl.core.errors import InvalidArgumentError, NDLError, UserError
from ndl.core.models import Novel, SearchResult
from ndl.fetchers import BrowserRuntimeDiagnostic, check_browser_runtime
from ndl.rules import SourceRule, load_rule_file
from ndl.storage import NovelSummary

_ENV_RULES_MANIFEST_URL = "NDL_RULES_MANIFEST_URL"

app = typer.Typer(
    name="ndl",
    help="NDL - NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)
rules_app = typer.Typer(help="Rule file utilities.", no_args_is_help=True)
library_app = typer.Typer(help="Local library commands.", no_args_is_help=True)
doctor_app = typer.Typer(help="Environment diagnostics.", no_args_is_help=True)


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
    scheduler: Annotated[
        bool,
        typer.Option(
            "--scheduler/--no-scheduler",
            help="Run recurring library updates while the Web UI is active.",
        ),
    ] = True,
    update_interval_hours: Annotated[
        int,
        typer.Option(
            "--update-interval-hours",
            min=1,
            help="Hours between recurring Web update checks.",
        ),
    ] = 6,
) -> None:
    """Serve the local Web UI."""
    try:
        ensure_download_disclaimer(accept=accept_disclaimer)
        _validate_serve_host(host, allow_public_host=allow_public_host)
        _run_web_server(
            host=host,
            port=port,
            reload=reload,
            scheduler=scheduler,
            update_interval_hours=update_interval_hours,
        )
    except NDLError as exc:
        _raise_cli_error(exc)


@app.command("update")
def update_command(
    all_entries: Annotated[
        bool,
        typer.Option("--all", help="Update all saved non-completed novels."),
    ] = False,
    accept_disclaimer: Annotated[
        bool,
        typer.Option(
            "--accept-disclaimer",
            help="Accept the lawful-use download disclaimer for this machine.",
        ),
    ] = False,
) -> None:
    """Check saved novels for newly published chapters."""
    try:
        if not all_entries:
            raise InvalidArgumentError(
                "Choose an update scope.",
                detail="Use `ndl update --all` to update every eligible library entry.",
            )
        ensure_download_disclaimer(accept=accept_disclaimer)
        results = asyncio.run(_update_all())
    except NDLError as exc:
        _raise_cli_error(exc)
    if not results:
        typer.echo("No updatable library entries.")
        return
    _console().print(_update_table(results))
    if any(result.status == "failed" for result in results):
        raise typer.Exit(1)


@app.command("search")
def search_command(
    keyword: Annotated[str, typer.Argument(help="Keyword to search for.")],
    rule_ids: Annotated[
        list[str] | None,
        typer.Option(
            "--rule",
            help="Restrict search to a rule id. Repeat for multiple rules.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Maximum number of rows to print."),
    ] = None,
) -> None:
    """Search rule-defined source indexes for a keyword."""
    try:
        outcome = asyncio.run(_search(keyword, rule_ids=rule_ids, limit=limit))
    except NDLError as exc:
        _raise_cli_error(exc)
    console = _console()
    if outcome.results:
        console.print(_search_table(outcome.results))
    else:
        typer.echo("No search results.")
    if outcome.failures:
        console.print(_search_failure_table(outcome.failures))


@library_app.command("list")
def library_list() -> None:
    """List saved novels in the local library."""
    try:
        with ServiceContainer() as container:
            summaries = container.library_service().list()
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
        with ServiceContainer() as container:
            library = container.library_service()
            novel = library.get(novel_id)
            if novel is None:
                raise UserError("Library entry not found.", detail=f"ID: {novel_id}")
            if not yes and not typer.confirm(f"Remove '{novel.title}' from the library?"):
                typer.echo("Aborted.")
                raise typer.Exit(1)
            library.remove(novel_id)
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Removed library entry: {novel_id}")


@rules_app.command("list")
def rules_list() -> None:
    """List all loaded rules with their id, name, version, and capabilities."""
    try:
        with ServiceContainer() as container:
            rules = container.list_rules()
    except NDLError as exc:
        _raise_cli_error(exc)
    if not rules:
        typer.echo("No rules loaded.")
        return
    _console().print(_rules_table(rules))


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


@rules_app.command("update")
def rules_update(
    manifest_url: Annotated[
        str | None,
        typer.Option(
            "--manifest-url",
            help="Remote YAML/JSON manifest URL. May also be set with NDL_RULES_MANIFEST_URL.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Write validated rule updates without prompting."),
    ] = False,
) -> None:
    """Fetch, validate, and install remote source rules."""
    try:
        resolved_manifest_url = _resolve_rules_manifest_url(manifest_url)
        plan = asyncio.run(_plan_rule_update(resolved_manifest_url))
        _console().print(_rule_update_table(plan))
        if plan.changed_count == 0:
            typer.echo("No rule updates to apply.")
            return
        if not yes and not typer.confirm(
            f"Write {plan.changed_count} rule update(s) to {plan.rules_dir}?"
        ):
            typer.echo("Aborted.")
            raise typer.Exit(1)
        asyncio.run(_apply_rule_update(plan))
    except NDLError as exc:
        _raise_cli_error(exc)
    typer.echo(f"Updated {plan.changed_count} rule file(s) in {plan.rules_dir}.")


@doctor_app.command("browser")
def doctor_browser() -> None:
    """Check optional browser-fetcher dependencies and Chromium runtime."""
    diagnostic = asyncio.run(check_browser_runtime())
    _print_browser_diagnostic(diagnostic)
    if not diagnostic.ok:
        raise typer.Exit(1)


app.add_typer(rules_app, name="rules")
app.add_typer(library_app, name="library")
app.add_typer(doctor_app, name="doctor")


async def _download(
    url: str,
    output_path: Path,
    *,
    target_format: str | None,
    save: bool,
) -> tuple[Path, int | None]:
    with ServiceContainer() as container:
        async with cli_progress() as progress:
            novel = await container.download(url, progress=progress)
            written = await container.convert_service(progress=progress).convert(
                novel, output_path, target_format=target_format
            )
        novel_id = container.library_service().save(novel) if save else None
        return written, novel_id


async def _convert(input_path: Path, output_path: Path, *, target_format: str | None) -> Path:
    with ServiceContainer() as container:
        async with cli_progress() as progress:
            return await container.convert_service(progress=progress).convert(
                input_path, output_path, target_format=target_format
            )


async def _update_all() -> list[UpdateResult]:
    with ServiceContainer() as container:
        async with cli_progress() as progress:
            return await container.update_service(progress=progress).update_all()


async def _search(
    keyword: str,
    *,
    rule_ids: list[str] | None,
    limit: int | None,
) -> SearchOutcome:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise InvalidArgumentError("Search keyword cannot be empty.")

    selected_rule_ids = _normalize_search_rule_ids(rule_ids)
    with ServiceContainer() as container:
        searchable_rules = [
            rule for rule in container.list_rules() if rule.enabled and rule.search is not None
        ]
        _validate_search_rule_ids(selected_rule_ids, searchable_rules)
        outcome = await container.search_service().search(
            normalized_keyword,
            rule_ids=selected_rule_ids or None,
        )
    if limit is not None:
        return SearchOutcome(results=outcome.results[:limit], failures=outcome.failures)
    return outcome


async def _plan_rule_update(manifest_url: str) -> RuleUpdatePlan:
    service = RuleUpdateService(rules_dir=rules_dir())
    try:
        return await service.plan_update(manifest_url)
    finally:
        await service.aclose()


async def _apply_rule_update(plan: RuleUpdatePlan) -> None:
    service = RuleUpdateService(rules_dir=rules_dir())
    try:
        service.apply_update(plan)
    finally:
        await service.aclose()


def _raise_cli_error(exc: NDLError) -> NoReturn:
    typer.echo(exc.user_message(), err=True)
    raise typer.Exit(exc.exit_code)


def _print_browser_diagnostic(diagnostic: BrowserRuntimeDiagnostic) -> None:
    status = "OK" if diagnostic.ok else "FAILED"
    typer.echo(f"Browser runtime: {status}")
    typer.echo(diagnostic.message)
    if diagnostic.detail:
        typer.echo(diagnostic.detail)


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


def _run_web_server(
    *,
    host: str,
    port: int,
    reload: bool,
    scheduler: bool,
    update_interval_hours: int,
) -> None:
    import uvicorn

    os.environ["NDL_WEB_ENABLE_SCHEDULER"] = "1" if scheduler else "0"
    os.environ["NDL_WEB_UPDATE_INTERVAL_HOURS"] = str(update_interval_hours)
    uvicorn.run(
        "ndl.web.app:create_serve_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def _load_library_novel(novel_id: int) -> Novel:
    with ServiceContainer() as container:
        novel = container.library_service().get(novel_id)
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


def _update_table(results: list[UpdateResult]) -> Table:
    table = Table()
    table.add_column("id", justify="right")
    table.add_column("title")
    table.add_column("status")
    table.add_column("new", justify="right")
    table.add_column("total", justify="right")
    table.add_column("message")
    for result in results:
        table.add_row(
            str(result.novel_id),
            result.title,
            result.status,
            str(result.new_chapter_count),
            str(result.total_chapter_count),
            result.message or "",
        )
    return table


def _search_table(results: list[SearchResult]) -> Table:
    table = Table()
    table.add_column("source")
    table.add_column("title")
    table.add_column("author")
    table.add_column("url")
    for result in results:
        table.add_row(
            result.source_name,
            result.title,
            result.author or "",
            result.url,
        )
    return table


def _search_failure_table(failures: list[SearchFailure]) -> Table:
    table = Table(title="Search failures")
    table.add_column("rule")
    table.add_column("source")
    table.add_column("message")
    for failure in failures:
        table.add_row(failure.rule_id, failure.source_name, failure.message)
    return table


def _normalize_search_rule_ids(rule_ids: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for rule_id in rule_ids or []:
        stripped = rule_id.strip()
        if not stripped:
            raise InvalidArgumentError("Search rule id cannot be empty.")
        normalized.append(stripped)
    return normalized


def _validate_search_rule_ids(rule_ids: list[str], searchable_rules: list[SourceRule]) -> None:
    available_ids = {rule.id for rule in searchable_rules}
    unsupported = sorted(set(rule_ids) - available_ids)
    if not unsupported:
        return
    available = ", ".join(sorted(available_ids)) if available_ids else "none"
    raise InvalidArgumentError(
        "Unsupported search rule selection.",
        detail=(
            f"Unsupported rule id(s): {', '.join(unsupported)}\n"
            f"Available searchable rules: {available}"
        ),
    )


def _resolve_rules_manifest_url(value: str | None) -> str:
    resolved = (value or os.environ.get(_ENV_RULES_MANIFEST_URL) or "").strip()
    if not resolved:
        raise InvalidArgumentError(
            "Remote rule manifest URL is required.",
            detail=(
                "Pass --manifest-url or set NDL_RULES_MANIFEST_URL. "
                "NDL does not ship a default remote rule feed yet."
            ),
        )
    return resolved


def _rules_table(rules: list[SourceRule]) -> Table:
    table = Table()
    table.add_column("id")
    table.add_column("name")
    table.add_column("version")
    table.add_column("enabled")
    table.add_column("search")
    table.add_column("fetcher")
    table.add_column("patterns", justify="right")
    for rule in rules:
        table.add_row(
            rule.id,
            rule.name,
            rule.version,
            "yes" if rule.enabled else "no",
            "yes" if rule.search is not None else "no",
            rule.fetcher.type,
            str(len(rule.url_patterns)),
        )
    return table


def _rule_update_table(plan: RuleUpdatePlan) -> Table:
    table = Table()
    table.add_column("status")
    table.add_column("id")
    table.add_column("name")
    table.add_column("version")
    table.add_column("target")
    for item in plan.items:
        table.add_row(
            item.status,
            item.rule.id,
            item.rule.name,
            item.rule.version,
            str(item.target_path),
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
