"""Tests for the NDL CLI entry point."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
import respx
from typer.testing import CliRunner

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.cli.main import app
from ndl.core.models import Chapter, Novel

runner = CliRunner()
BASE_URL = "https://example-novels.test/book/123"
REPO_ROOT = Path(__file__).parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "contract" / "fixtures" / "example_static"


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


def test_module_entrypoint_exposes_cli_app() -> None:
    """`python -m ndl` imports the same Typer app object."""
    from ndl import __main__

    assert __main__.app is app


def test_convert_command_writes_epub_from_txt(tmp_path) -> None:
    input_path = tmp_path / "book.txt"
    output_path = tmp_path / "book.epub"
    input_path.write_text(
        "# 测试小说\n作者:某作者\n来源:https://example.test/book/1\n\n## 第一章\n\n正文。",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["convert", str(input_path), "-o", str(output_path)])

    assert result.exit_code == 0, result.output
    assert "Wrote" in result.output
    with ZipFile(output_path) as archive:
        assert "OEBPS/content.opf" in archive.namelist()
        assert "OEBPS/Text/chapter_0001.xhtml" in archive.namelist()


def test_rules_validate_command_accepts_builtin_rule() -> None:
    rule_path = REPO_ROOT / "src" / "ndl" / "builtin_rules" / "example_static.yaml"

    result = runner.invoke(app, ["rules", "validate", str(rule_path)])

    assert result.exit_code == 0, result.output
    assert "Rule valid: example_static" in result.output


def test_download_requires_disclaimer_acceptance(tmp_path) -> None:
    output_path = tmp_path / "book.epub"

    result = runner.invoke(
        app,
        ["download", BASE_URL, "-o", str(output_path)],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 2
    assert "--accept-disclaimer" in result.output
    assert not output_path.exists()


def test_serve_requires_disclaimer_acceptance(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["serve"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 2
    assert "--accept-disclaimer" in result.output


def test_serve_runs_uvicorn_after_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int, bool]] = []

    def _fake_run(*, host: str, port: int, reload: bool) -> None:
        calls.append((host, port, reload))

    monkeypatch.setattr("ndl.cli.main._run_web_server", _fake_run)

    result = runner.invoke(
        app,
        ["serve", "--accept-disclaimer", "--port", "8123", "--reload"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert calls == [("127.0.0.1", 8123, True)]


def test_serve_rejects_public_host_without_explicit_allow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int, bool]] = []
    monkeypatch.setattr(
        "ndl.cli.main._run_web_server",
        lambda *, host, port, reload: calls.append((host, port, reload)),
    )

    result = runner.invoke(
        app,
        ["serve", "--accept-disclaimer", "--host", "0.0.0.0"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 2
    assert "public interface" in result.output
    assert calls == []


def test_serve_allows_public_host_with_explicit_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int, bool]] = []
    monkeypatch.setattr(
        "ndl.cli.main._run_web_server",
        lambda *, host, port, reload: calls.append((host, port, reload)),
    )

    result = runner.invoke(
        app,
        ["serve", "--accept-disclaimer", "--host", "0.0.0.0", "--allow-public-host"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert calls == [("0.0.0.0", 8000, False)]


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real sleeping in CLI download tests."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("ndl.fetchers._throttle.asyncio.sleep", _instant)
    monkeypatch.setattr("ndl.fetchers.http.asyncio.sleep", _instant)


@respx.mock
def test_download_command_writes_epub_against_mocked_http(tmp_path) -> None:
    output_path = tmp_path / "downloaded.epub"
    ndl_home = tmp_path / "ndl-home"
    _mock_example_download()

    result = runner.invoke(
        app,
        ["download", BASE_URL, "-o", str(output_path), "--accept-disclaimer"],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert result.exit_code == 0, result.output
    assert "Wrote" in result.output
    assert "Saved to library: 1" in result.output
    with ZipFile(output_path) as archive:
        assert "OEBPS/content.opf" in archive.namelist()
        assert "OEBPS/Text/chapter_0001.xhtml" in archive.namelist()
        assert "Example Public Domain Novel" in archive.read("OEBPS/content.opf").decode("utf-8")

    list_result = runner.invoke(app, ["library", "list"], env={"NDL_HOME": str(ndl_home)})
    assert list_result.exit_code == 0, list_result.output
    assert "Example Public Domain Novel" in list_result.output
    assert "Example Author" in list_result.output


@respx.mock
def test_download_no_save_skips_library(tmp_path) -> None:
    output_path = tmp_path / "downloaded.epub"
    ndl_home = tmp_path / "ndl-home"
    _mock_example_download()

    result = runner.invoke(
        app,
        ["download", BASE_URL, "-o", str(output_path), "--accept-disclaimer", "--no-save"],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert result.exit_code == 0, result.output
    assert "Wrote" in result.output
    assert "Saved to library" not in result.output

    list_result = runner.invoke(app, ["library", "list"], env={"NDL_HOME": str(ndl_home)})
    assert list_result.exit_code == 0, list_result.output
    assert "No library entries." in list_result.output


def test_library_show_and_remove_commands(tmp_path) -> None:
    ndl_home = tmp_path / "ndl-home"
    novel_id = _seed_library(ndl_home)

    show_result = runner.invoke(
        app,
        ["library", "show", str(novel_id)],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert show_result.exit_code == 0, show_result.output
    assert "Seed Novel" in show_result.output
    assert "First Chapter" in show_result.output
    assert "secret body" not in show_result.output

    remove_result = runner.invoke(
        app,
        ["library", "remove", str(novel_id), "--yes"],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert remove_result.exit_code == 0, remove_result.output
    assert f"Removed library entry: {novel_id}" in remove_result.output

    list_result = runner.invoke(app, ["library", "list"], env={"NDL_HOME": str(ndl_home)})
    assert list_result.exit_code == 0, list_result.output
    assert "No library entries." in list_result.output


def _mock_example_download() -> None:
    chapter_one = (FIXTURE_DIR / "chapter.html").read_text(encoding="utf-8")
    chapter_two = chapter_one.replace("Chapter 1: Dawn", "Chapter 2: Noon").replace(
        "Morning arrived over the quiet archive.",
        "Noon light filled the reading room.",
    )
    respx.get("https://example-novels.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            text=(FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
        )
    )
    respx.get(f"{BASE_URL}/chapter/1").mock(return_value=httpx.Response(200, text=chapter_one))
    respx.get(f"{BASE_URL}/chapter/2").mock(return_value=httpx.Response(200, text=chapter_two))


def _seed_library(ndl_home: Path) -> int:
    service = ServiceContainer(rules=[], db_path=ndl_home / "library.db").library_service()
    return service.save(
        Novel(
            title="Seed Novel",
            author="Seed Author",
            source_url="https://example.com/seed",
            source_rule_id="example_static",
            chapters=[
                Chapter(index=0, title="First Chapter", content="secret body"),
                Chapter(index=1, title="Second Chapter", content="more secret body"),
            ],
            fetched_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
    )
