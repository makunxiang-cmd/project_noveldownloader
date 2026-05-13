"""Verify NDL wheel and source distribution release artifacts."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from email.message import Message
from email.parser import Parser
from pathlib import Path

REQUIRED_WHEEL_MEMBERS = {
    "ndl/builtin_rules/example_static.yaml",
    "ndl/web/static/css/app.css",
    "ndl/web/static/js/app.js",
    "ndl/web/templates/base.html",
    "ndl/web/templates/download_job.html",
    "ndl/web/templates/error.html",
    "ndl/web/templates/index.html",
    "ndl/web/templates/library_detail.html",
    "ndl/web/templates/search_results.html",
    "ndl/web/templates/update_results.html",
}
REQUIRED_SDIST_SUFFIXES = {
    "pyproject.toml",
    "src/ndl/builtin_rules/example_static.yaml",
    "src/ndl/web/static/css/app.css",
    "src/ndl/web/static/js/app.js",
    "src/ndl/web/templates/base.html",
    "src/ndl/web/templates/download_job.html",
    "src/ndl/web/templates/error.html",
    "src/ndl/web/templates/index.html",
    "src/ndl/web/templates/library_detail.html",
    "src/ndl/web/templates/search_results.html",
    "src/ndl/web/templates/update_results.html",
}
REQUIRED_EXTRAS = {"browser", "dev", "docs"}


def main(argv: list[str] | None = None) -> int:
    """Run distribution verification and return a process exit code."""
    args = _parse_args(argv)
    failures: list[str] = []
    failures.extend(_verify_wheel(args.wheel))
    failures.extend(_verify_sdist(args.sdist))
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print("Distribution artifacts verified.")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="Path to the built .whl artifact.")
    parser.add_argument("sdist", type=Path, help="Path to the built .tar.gz artifact.")
    return parser.parse_args(argv)


def _verify_wheel(path: Path) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        return [f"wheel not found: {path}"]
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        failures.extend(
            f"wheel missing required member: {name}"
            for name in sorted(REQUIRED_WHEEL_MEMBERS - names)
        )
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            failures.append(
                f"wheel should contain exactly one METADATA file, found {len(metadata_names)}"
            )
        else:
            metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
            failures.extend(_verify_metadata(metadata))
    return failures


def _verify_metadata(metadata: Message) -> list[str]:
    failures: list[str] = []
    version = metadata["Version"]
    if version != "0.1.0.dev0":
        failures.append(f"unexpected package version: {version}")
    extras = set(metadata.get_all("Provides-Extra", []))
    missing_extras = REQUIRED_EXTRAS - extras
    failures.extend(f"wheel metadata missing extra: {extra}" for extra in sorted(missing_extras))
    requires_dist = metadata.get_all("Requires-Dist", [])
    if not any(
        value.startswith("playwright>=1.40") and "extra == 'browser'" in value
        for value in requires_dist
    ):
        failures.append("wheel metadata missing browser extra Playwright dependency")
    return failures


def _verify_sdist(path: Path) -> list[str]:
    if not path.is_file():
        return [f"sdist not found: {path}"]
    with tarfile.open(path, mode="r:gz") as archive:
        names = set(archive.getnames())
    failures: list[str] = []
    for suffix in sorted(REQUIRED_SDIST_SUFFIXES):
        if not any(name.endswith(f"/{suffix}") for name in names):
            failures.append(f"sdist missing required member ending with: {suffix}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
