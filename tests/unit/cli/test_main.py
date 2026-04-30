"""Tests for the NDL CLI entry point."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
import respx
from typer.testing import CliRunner

from ndl import __version__
from ndl.cli.main import app

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

    result = runner.invoke(
        app,
        ["download", BASE_URL, "-o", str(output_path), "--accept-disclaimer"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert "Wrote" in result.output
    with ZipFile(output_path) as archive:
        assert "OEBPS/content.opf" in archive.namelist()
        assert "OEBPS/Text/chapter_0001.xhtml" in archive.namelist()
        assert "Example Public Domain Novel" in archive.read("OEBPS/content.opf").decode("utf-8")
