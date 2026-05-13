"""Tests for the release distribution verifier script."""

from __future__ import annotations

import tarfile
import zipfile
from importlib import util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).parents[3] / "scripts" / "verify_distribution.py"
_SPEC = util.spec_from_file_location("verify_distribution", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
verify_distribution = util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verify_distribution)

REQUIRED_SDIST_SUFFIXES = verify_distribution.REQUIRED_SDIST_SUFFIXES
REQUIRED_WHEEL_MEMBERS = verify_distribution.REQUIRED_WHEEL_MEMBERS
main = verify_distribution.main


def test_verify_distribution_accepts_complete_artifacts(tmp_path: Path, capsys) -> None:
    wheel = tmp_path / "ndl_storykit-0.2.0.dev0-py3-none-any.whl"
    sdist = tmp_path / "ndl_storykit-0.2.0.dev0.tar.gz"
    _write_wheel(wheel, members=REQUIRED_WHEEL_MEMBERS)
    _write_sdist(sdist, suffixes=REQUIRED_SDIST_SUFFIXES)

    exit_code = main([str(wheel), str(sdist)])

    assert exit_code == 0
    assert "Distribution artifacts verified." in capsys.readouterr().out


def test_verify_distribution_reports_missing_wheel_member(tmp_path: Path, capsys) -> None:
    wheel = tmp_path / "ndl_storykit-0.2.0.dev0-py3-none-any.whl"
    sdist = tmp_path / "ndl_storykit-0.2.0.dev0.tar.gz"
    members = REQUIRED_WHEEL_MEMBERS - {"ndl/web/static/js/app.js"}
    _write_wheel(wheel, members=members)
    _write_sdist(sdist, suffixes=REQUIRED_SDIST_SUFFIXES)

    exit_code = main([str(wheel), str(sdist)])

    assert exit_code == 1
    assert "wheel missing required member: ndl/web/static/js/app.js" in capsys.readouterr().err


def _write_wheel(path: Path, *, members: set[str]) -> None:
    metadata = "\n".join(
        [
            "Metadata-Version: 2.4",
            "Name: ndl-storykit",
            "Version: 0.2.0.dev0",
            "Provides-Extra: browser",
            "Provides-Extra: dev",
            "Provides-Extra: docs",
            "Requires-Dist: playwright>=1.40; extra == 'browser'",
            "",
        ]
    )
    with zipfile.ZipFile(path, mode="w") as archive:
        for member in members:
            archive.writestr(member, "")
        archive.writestr("ndl_storykit-0.2.0.dev0.dist-info/METADATA", metadata)


def _write_sdist(path: Path, *, suffixes: set[str]) -> None:
    with tarfile.open(path, mode="w:gz") as archive:
        for suffix in suffixes:
            temp = path.parent / suffix.replace("/", "_")
            temp.write_text("", encoding="utf-8")
            archive.add(temp, arcname=f"ndl_storykit-0.2.0.dev0/{suffix}")
