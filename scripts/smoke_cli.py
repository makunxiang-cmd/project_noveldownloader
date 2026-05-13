"""Post-install CLI smoke for an installed NDL build.

Run this against any environment where `ndl` resolves on PATH:

* dev tree:       `uv run python scripts/smoke_cli.py`
* clean venv:     `pip install dist/ndl-*.whl && python scripts/smoke_cli.py`
* with browser:   `pip install 'dist/ndl-*.whl[browser]' && playwright install chromium && \
                   python scripts/smoke_cli.py --browser`

The script never touches the network. It exercises:

1. `ndl --version` exits 0 and prints `NDL <version>`.
2. `ndl rules list` exits 0 and prints at least the bundled `example_static` rule.
3. `ndl rules validate <bundled yaml>` exits 0 with `Rule valid: example_static`.
4. `ndl doctor browser` is run for diagnostic only by default. Pass `--browser`
   to assert the runtime is fully wired up.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

_VERSION_PATTERN = re.compile(r"^NDL\s+\S+\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SmokeStep:
    name: str
    command: Sequence[str]
    ok_when_returncode: int
    expect_stdout_contains: Sequence[str] = ()
    expect_stdout_matches: re.Pattern[str] | None = None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke an installed NDL build.")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Assert `ndl doctor browser` succeeds (requires the `browser` extra + Chromium).",
    )
    parser.add_argument(
        "--ndl",
        default="ndl",
        help="Path to the `ndl` entry point (defaults to PATH lookup).",
    )
    args = parser.parse_args(argv)

    rule_path = _locate_bundled_rule()
    steps = [
        SmokeStep(
            name="ndl --version",
            command=[args.ndl, "--version"],
            ok_when_returncode=0,
            expect_stdout_matches=_VERSION_PATTERN,
        ),
        SmokeStep(
            name="ndl rules list",
            command=[args.ndl, "rules", "list"],
            ok_when_returncode=0,
            expect_stdout_contains=["example_static"],
        ),
        SmokeStep(
            name="ndl rules validate <bundled>",
            command=[args.ndl, "rules", "validate", str(rule_path)],
            ok_when_returncode=0,
            expect_stdout_contains=["Rule valid: example_static"],
        ),
    ]
    if args.browser:
        steps.append(
            SmokeStep(
                name="ndl doctor browser",
                command=[args.ndl, "doctor", "browser"],
                ok_when_returncode=0,
                expect_stdout_contains=["Browser runtime: OK"],
            )
        )
    else:
        steps.append(
            SmokeStep(
                name="ndl doctor browser (diagnostic)",
                command=[args.ndl, "doctor", "browser"],
                ok_when_returncode=-1,
            )
        )

    failures: list[str] = []
    for step in steps:
        ok, report = _run_step(step)
        prefix = "OK" if ok else "FAIL"
        print(f"[{prefix}] {step.name}")
        print(_indent(report))
        if not ok:
            failures.append(step.name)

    if failures:
        print(f"\nSmoke FAILED: {', '.join(failures)}")
        return 1
    print("\nSmoke OK.")
    return 0


def _run_step(step: SmokeStep) -> tuple[bool, str]:
    completed = subprocess.run(
        list(step.command),
        capture_output=True,
        text=True,
        check=False,
    )
    parts = [f"exit_code: {completed.returncode}"]
    if completed.stdout.strip():
        parts.append(f"stdout:\n{completed.stdout.strip()}")
    if completed.stderr.strip():
        parts.append(f"stderr:\n{completed.stderr.strip()}")
    report = "\n".join(parts)
    if step.ok_when_returncode == -1:
        return True, report
    if completed.returncode != step.ok_when_returncode:
        return False, report
    output = (completed.stdout or "") + (completed.stderr or "")
    for needle in step.expect_stdout_contains:
        if needle not in output:
            return False, report + f"\nmissing expected substring: {needle!r}"
    if step.expect_stdout_matches is not None and not step.expect_stdout_matches.search(output):
        return False, report + f"\nstdout did not match {step.expect_stdout_matches.pattern!r}"
    return True, report


def _locate_bundled_rule() -> Path:
    package = files("ndl.builtin_rules")
    candidate = package.joinpath("example_static.yaml")
    with as_file(candidate) as path:
        if not path.exists():
            raise SystemExit(f"Bundled rule not found: {path}")
        return path


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


if __name__ == "__main__":
    sys.exit(main())
