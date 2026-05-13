"""Tests for the NDL CLI entry point."""

from __future__ import annotations

import os
import textwrap
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
import respx
from typer.testing import CliRunner

from ndl import __version__
from ndl.application.container import ServiceContainer
from ndl.cli.main import _run_web_server, app
from ndl.core.models import Chapter, Novel
from ndl.fetchers import BrowserRuntimeDiagnostic

runner = CliRunner()
BASE_URL = "https://example-novels.test/book/123"
RULE_MANIFEST_URL = "https://rules.example.test/manifest.yaml"
REMOTE_RULE_URL = "https://rules.example.test/rules/remote_rule.yaml"
REPO_ROOT = Path(__file__).parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "contract" / "fixtures" / "example_static"
SEARCH_HTML = """
<html><body>
<div id="search-results">
  <div class="result-item">
    <span class="result-title">Journey to the West</span>
    <span class="result-author">Wu Cheng'en</span>
    <a class="result-link" href="/book/1">View</a>
  </div>
  <div class="result-item">
    <span class="result-title">Dream of the Red Chamber</span>
    <span class="result-author">Cao Xueqin</span>
    <a class="result-link" href="/book/2">View</a>
  </div>
</div>
</body></html>
"""
EMPTY_SEARCH_HTML = """
<html><body>
<div id="search-results"></div>
</body></html>
"""
REMOTE_RULE_YAML = """
id: remote_rule
name: Remote Rule
version: 1.0.0
author: Tests
priority: 25
url_patterns:
  - pattern: "https://remote.test/book/*"
    type: glob
index:
  novel:
    title: { selector: "h1" }
    author: { selector: ".author" }
  chapter_list:
    container: "#chapters"
    items: "a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


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


def test_doctor_browser_reports_available_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_check() -> BrowserRuntimeDiagnostic:
        return BrowserRuntimeDiagnostic(ok=True, message="Playwright Chromium is available.")

    monkeypatch.setattr("ndl.cli.main.check_browser_runtime", fake_check)

    result = runner.invoke(app, ["doctor", "browser"])

    assert result.exit_code == 0, result.output
    assert "Browser runtime: OK" in result.output
    assert "Playwright Chromium is available." in result.output


def test_doctor_browser_reports_missing_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_check() -> BrowserRuntimeDiagnostic:
        return BrowserRuntimeDiagnostic(
            ok=False,
            message="Playwright Chromium is not available.",
            detail="Run `playwright install chromium`.",
        )

    monkeypatch.setattr("ndl.cli.main.check_browser_runtime", fake_check)

    result = runner.invoke(app, ["doctor", "browser"])

    assert result.exit_code == 1
    assert "Browser runtime: FAILED" in result.output
    assert "Playwright Chromium is not available." in result.output
    assert "playwright install chromium" in result.output


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


def test_rules_list_command_lists_loaded_rules(tmp_path: Path) -> None:
    result = runner.invoke(app, ["rules", "list"], env={"NDL_HOME": str(tmp_path / "ndl-home")})

    assert result.exit_code == 0, result.output
    assert "example_static" in result.output


def test_rules_validate_command_accepts_builtin_rule() -> None:
    rule_path = REPO_ROOT / "src" / "ndl" / "builtin_rules" / "example_static.yaml"

    result = runner.invoke(app, ["rules", "validate", str(rule_path)])

    assert result.exit_code == 0, result.output
    assert "Rule valid: example_static" in result.output


@respx.mock
def test_rules_update_writes_valid_remote_rules_after_confirmation(tmp_path: Path) -> None:
    _mock_rule_manifest(REMOTE_RULE_YAML)

    result = runner.invoke(
        app,
        ["rules", "update", "--manifest-url", RULE_MANIFEST_URL],
        input="y\n",
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert "remote_rule" in result.output
    assert "added" in result.output
    assert "Updated 1 rule file" in result.output
    installed = tmp_path / "ndl-home" / "rules" / "remote_rule.yaml"
    assert installed.read_text(encoding="utf-8") == textwrap.dedent(REMOTE_RULE_YAML)


@respx.mock
def test_rules_update_aborts_without_confirmation(tmp_path: Path) -> None:
    _mock_rule_manifest(REMOTE_RULE_YAML)

    result = runner.invoke(
        app,
        ["rules", "update", "--manifest-url", RULE_MANIFEST_URL],
        input="n\n",
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 1, result.output
    assert "Aborted." in result.output
    assert not (tmp_path / "ndl-home" / "rules" / "remote_rule.yaml").exists()


@respx.mock
def test_rules_update_rejects_invalid_remote_rule_without_replacing(tmp_path: Path) -> None:
    ndl_home = tmp_path / "ndl-home"
    rules_dir = ndl_home / "rules"
    rules_dir.mkdir(parents=True)
    existing = "existing content"
    installed = rules_dir / "remote_rule.yaml"
    installed.write_text(existing, encoding="utf-8")
    _mock_rule_manifest("id: remote_rule\n")

    result = runner.invoke(
        app,
        ["rules", "update", "--manifest-url", RULE_MANIFEST_URL, "--yes"],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert result.exit_code == 1
    assert "Rule schema validation failed" in result.output
    assert installed.read_text(encoding="utf-8") == existing


def test_rules_update_requires_manifest_url(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["rules", "update", "--yes"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 2
    assert "Remote rule manifest URL is required." in result.output


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
    calls: list[tuple[str, int, bool, bool, int]] = []

    def _fake_run(
        *,
        host: str,
        port: int,
        reload: bool,
        scheduler: bool,
        update_interval_hours: int,
    ) -> None:
        calls.append((host, port, reload, scheduler, update_interval_hours))

    monkeypatch.setattr("ndl.cli.main._run_web_server", _fake_run)

    result = runner.invoke(
        app,
        ["serve", "--accept-disclaimer", "--port", "8123", "--reload"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert calls == [("127.0.0.1", 8123, True, True, 6)]


def test_serve_can_disable_scheduler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, bool, bool, int]] = []
    monkeypatch.setattr(
        "ndl.cli.main._run_web_server",
        lambda *, host, port, reload, scheduler, update_interval_hours: calls.append(
            (host, port, reload, scheduler, update_interval_hours)
        ),
    )

    result = runner.invoke(
        app,
        [
            "serve",
            "--accept-disclaimer",
            "--no-scheduler",
            "--update-interval-hours",
            "12",
        ],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert calls == [("127.0.0.1", 8000, False, False, 12)]


def test_serve_rejects_public_host_without_explicit_allow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int, bool, bool, int]] = []
    monkeypatch.setattr(
        "ndl.cli.main._run_web_server",
        lambda *, host, port, reload, scheduler, update_interval_hours: calls.append(
            (host, port, reload, scheduler, update_interval_hours)
        ),
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
    calls: list[tuple[str, int, bool, bool, int]] = []
    monkeypatch.setattr(
        "ndl.cli.main._run_web_server",
        lambda *, host, port, reload, scheduler, update_interval_hours: calls.append(
            (host, port, reload, scheduler, update_interval_hours)
        ),
    )

    result = runner.invoke(
        app,
        ["serve", "--accept-disclaimer", "--host", "0.0.0.0", "--allow-public-host"],
        env={"NDL_HOME": str(tmp_path / "ndl-home")},
    )

    assert result.exit_code == 0, result.output
    assert calls == [("0.0.0.0", 8000, False, True, 6)]


def test_run_web_server_uses_serve_factory_and_scheduler_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool, str, int, bool]] = []

    def _fake_uvicorn_run(
        app_target: str,
        *,
        factory: bool,
        host: str,
        port: int,
        reload: bool,
    ) -> None:
        calls.append((app_target, factory, host, port, reload))

    monkeypatch.setattr("uvicorn.run", _fake_uvicorn_run)
    monkeypatch.delenv("NDL_WEB_ENABLE_SCHEDULER", raising=False)
    monkeypatch.delenv("NDL_WEB_UPDATE_INTERVAL_HOURS", raising=False)

    _run_web_server(
        host="127.0.0.1",
        port=8123,
        reload=True,
        scheduler=False,
        update_interval_hours=12,
    )

    assert calls == [("ndl.web.app:create_serve_app", True, "127.0.0.1", 8123, True)]
    assert os.environ["NDL_WEB_ENABLE_SCHEDULER"] == "0"
    assert os.environ["NDL_WEB_UPDATE_INTERVAL_HOURS"] == "12"


@respx.mock
def test_search_command_renders_mocked_results() -> None:
    _mock_example_search("west", SEARCH_HTML)

    result = runner.invoke(app, ["search", "west"])

    assert result.exit_code == 0, result.output
    assert "Public Domain Static Site Example" in result.output
    assert "Journey to the West" in result.output
    assert "Wu Cheng'en" in result.output
    assert "https://example-novels.test/book/1" in result.output


@respx.mock
def test_search_command_supports_rule_filter_and_limit() -> None:
    _mock_example_search("west", SEARCH_HTML)

    result = runner.invoke(
        app,
        ["search", "west", "--rule", "example_static", "--limit", "1"],
    )

    assert result.exit_code == 0, result.output
    assert "Journey to the West" in result.output
    assert "Dream of the Red Chamber" not in result.output


@respx.mock
def test_search_command_prints_empty_state() -> None:
    _mock_example_search("nothing", EMPTY_SEARCH_HTML)

    result = runner.invoke(app, ["search", "nothing"])

    assert result.exit_code == 0, result.output
    assert "No search results." in result.output


def test_search_command_rejects_empty_keyword() -> None:
    result = runner.invoke(app, ["search", "   "])

    assert result.exit_code == 2
    assert "Search keyword cannot be empty." in result.output


def test_search_command_rejects_unsupported_rule_id() -> None:
    result = runner.invoke(app, ["search", "west", "--rule", "missing"])

    assert result.exit_code == 2
    assert "Unsupported search rule selection." in result.output
    assert "missing" in result.output
    assert "example_static" in result.output


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


@respx.mock
def test_update_all_appends_new_chapters_against_mocked_http(tmp_path: Path) -> None:
    ndl_home = tmp_path / "ndl-home"
    novel_id = _seed_updatable_library(ndl_home)
    _mock_example_update()

    result = runner.invoke(
        app,
        ["update", "--all", "--accept-disclaimer"],
        env={"NDL_HOME": str(ndl_home)},
    )

    assert result.exit_code == 0, result.output
    assert "Example Public Domain Novel" in result.output
    assert "updated" in result.output

    show_result = runner.invoke(
        app,
        ["library", "show", str(novel_id)],
        env={"NDL_HOME": str(ndl_home)},
    )
    assert show_result.exit_code == 0, show_result.output
    assert "Chapter 2: Noon" in show_result.output


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


def _mock_example_update() -> None:
    chapter_two = (
        (FIXTURE_DIR / "chapter.html")
        .read_text(encoding="utf-8")
        .replace(
            "Chapter 1: Dawn",
            "Chapter 2: Noon",
        )
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
    respx.get(f"{BASE_URL}/chapter/2").mock(return_value=httpx.Response(200, text=chapter_two))


def _mock_example_search(keyword: str, html: str) -> None:
    encoded_keyword = keyword.replace(" ", "+")
    respx.get("https://example-novels.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get(f"https://example-novels.test/search?q={encoded_keyword}").mock(
        return_value=httpx.Response(200, text=html)
    )


def _mock_rule_manifest(rule_yaml: str) -> None:
    digest = sha256(textwrap.dedent(rule_yaml).encode("utf-8")).hexdigest()
    manifest = f"""
version: 1
rules:
  - id: remote_rule
    url: /rules/remote_rule.yaml
    sha256: {digest}
"""
    respx.get(RULE_MANIFEST_URL).mock(
        return_value=httpx.Response(200, text=textwrap.dedent(manifest))
    )
    respx.get(REMOTE_RULE_URL).mock(
        return_value=httpx.Response(200, text=textwrap.dedent(rule_yaml))
    )


def _seed_library(ndl_home: Path) -> int:
    with ServiceContainer(rules=[], db_path=ndl_home / "library.db") as container:
        return container.library_service().save(
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


def _seed_updatable_library(ndl_home: Path) -> int:
    with ServiceContainer(db_path=ndl_home / "library.db") as container:
        return container.library_service().save(
            Novel(
                title="Example Public Domain Novel",
                author="Example Author",
                source_url=BASE_URL,
                source_rule_id="example_static",
                status="ongoing",
                chapters=[
                    Chapter(
                        index=0,
                        title="Chapter 1: Dawn",
                        content="Morning arrived over the quiet archive.",
                        source_url=f"{BASE_URL}/chapter/1",
                    )
                ],
                fetched_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            )
        )
