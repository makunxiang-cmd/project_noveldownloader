"""FastAPI application factory for the local Web UI."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.application.paths import ndl_home
from ndl.application.services import UpdateResult
from ndl.core.errors import NDLError, UserError
from ndl.core.models import Novel
from ndl.core.progress import ProgressEvent
from ndl.scheduler import UpdateScheduler
from ndl.web.jobs import DownloadJob, JobRegistry

_WEB_DIR = Path(__file__).parent
_STATIC_DIR = _WEB_DIR / "static"
_TEMPLATES_DIR = _WEB_DIR / "templates"
_SUPPORTED_DOWNLOAD_FORMATS = {"epub", "txt"}


def create_app(
    *,
    container: ServiceContainer | None = None,
    output_dir: Path | None = None,
    enable_scheduler: bool = False,
    scheduler_interval_hours: int = 6,
) -> FastAPI:
    """Create the local Web UI app."""
    service_container = container or ServiceContainer()
    download_output_dir = output_dir or (ndl_home() / "downloads")
    job_registry = JobRegistry()
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    update_scheduler = (
        UpdateScheduler(
            update_all=service_container.update_service().update_all,
            interval_hours=scheduler_interval_hours,
        )
        if enable_scheduler
        else None
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if update_scheduler is not None:
            update_scheduler.start()
        try:
            yield
        finally:
            if update_scheduler is not None:
                update_scheduler.shutdown()

    app = FastAPI(
        title="NDL",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.container = service_container
    app.state.job_registry = job_registry
    app.state.update_scheduler = update_scheduler
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Response:
        summaries = service_container.library_service().list()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_version": __version__,
                "summaries": summaries,
                "download_formats": sorted(_SUPPORTED_DOWNLOAD_FORMATS),
            },
        )

    @app.post("/updates", response_class=HTMLResponse)
    async def update_library(request: Request) -> Response:
        try:
            results = await service_container.update_service().update_all()
        except NDLError as exc:
            return _error_response(
                templates,
                request,
                UserError("Update failed.", detail=exc.user_message()),
                status_code=500,
            )
        return templates.TemplateResponse(
            request,
            "update_results.html",
            {
                "app_version": __version__,
                "results": results,
                "summary": _update_summary(results),
            },
        )

    @app.get("/library/{novel_id}", response_class=HTMLResponse)
    async def library_detail(request: Request, novel_id: int) -> Response:
        library = service_container.library_service()
        novel = library.get(novel_id)
        if novel is None:
            error = UserError("Library entry not found.", detail=f"ID: {novel_id}")
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "app_version": __version__,
                    "error_title": "Library entry not found",
                    "error_message": error.user_message(),
                },
                status_code=404,
            )
        return templates.TemplateResponse(
            request,
            "library_detail.html",
            {
                "app_version": __version__,
                "novel": novel,
                "novel_id": novel_id,
            },
        )

    @app.post("/downloads", response_class=HTMLResponse, status_code=202)
    async def create_download(request: Request, background_tasks: BackgroundTasks) -> Response:
        form = _parse_urlencoded(await request.body())
        url = form.get("url", "").strip()
        target_format = form.get("format", "epub").strip().lower()
        save = form.get("save") == "on"
        if not url:
            return _error_response(
                templates,
                request,
                UserError("Download URL is required."),
                status_code=400,
            )
        if target_format not in _SUPPORTED_DOWNLOAD_FORMATS:
            return _error_response(
                templates,
                request,
                UserError("Unsupported output format.", detail=f"Format: {target_format}"),
                status_code=400,
            )

        job = job_registry.create(url=url, target_format=target_format, save=save)
        background_tasks.add_task(
            _run_download_job,
            job=job,
            container=service_container,
            registry=job_registry,
            output_dir=download_output_dir,
        )
        return templates.TemplateResponse(
            request,
            "download_job.html",
            {
                "app_version": __version__,
                "job": job,
            },
            status_code=202,
        )

    @app.get("/downloads/{job_id}/events")
    async def download_events(job_id: str) -> Response:
        job = job_registry.get(job_id)
        if job is None:
            return Response("Download job not found.", status_code=404)
        return EventSourceResponse(job_registry.stream(job_id))

    return app


def create_serve_app() -> FastAPI:
    """Create the app used by `ndl serve`."""
    return create_app(
        enable_scheduler=_env_flag("NDL_WEB_ENABLE_SCHEDULER", default=False),
        scheduler_interval_hours=_env_int("NDL_WEB_UPDATE_INTERVAL_HOURS", default=6),
    )


async def _run_download_job(
    *,
    job: DownloadJob,
    container: ServiceContainer,
    registry: JobRegistry,
    output_dir: Path,
) -> None:
    registry.mark_running(job.id)

    async def progress(event: ProgressEvent) -> None:
        await registry.record(job.id, event)

    try:
        novel = await container.download(job.url, progress=progress)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = _download_output_path(output_dir, job, novel)
        written = await container.convert_service(progress=progress).convert(
            novel,
            output_path,
            target_format=job.target_format,
        )
        novel_id = container.library_service().save(novel) if job.save else None
    except NDLError as exc:
        registry.mark_failed(job.id, exc.user_message())
        return
    registry.mark_succeeded(job.id, output_path=written, novel_id=novel_id)


def _download_output_path(output_dir: Path, job: DownloadJob, novel: Novel) -> Path:
    slug = _slugify(novel.title) or "novel"
    return output_dir / f"{job.id[:8]}-{slug}.{job.target_format}"


def _slugify(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in value.strip()]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug[:80]


def _parse_urlencoded(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _update_summary(results: list[UpdateResult]) -> str:
    if not results:
        return "No updatable library entries."
    updated = sum(result.new_chapter_count for result in results)
    failed = sum(1 for result in results if result.status == "failed")
    return f"{updated} new chapter(s), {failed} failed."


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        return default


def _error_response(
    templates: Jinja2Templates,
    request: Request,
    error: UserError,
    *,
    status_code: int,
) -> Response:
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "app_version": __version__,
            "error_title": error.message,
            "error_message": error.user_message(),
        },
        status_code=status_code,
    )
