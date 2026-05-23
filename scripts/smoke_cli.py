"""Post-install CLI smoke for an installed NDL build.

Run this against any environment where `ndl` resolves on PATH:

* dev tree:       `uv run python scripts/smoke_cli.py`
* clean venv:     `pip install dist/ndl-*.whl && python scripts/smoke_cli.py`
* with browser:   `pip install 'dist/ndl-*.whl[browser]' && playwright install chromium && \
                   python scripts/smoke_cli.py --browser`

The script never touches the network. It exercises:

1. `ndl --version` exits 0 and prints `NDL <version>`.
2. `ndl rules list` exits 0 in an isolated fresh NDL_HOME and reports no rules.
3. `ndl rules validate <fixture yaml>` exits 0 with `Rule valid: smoke_static`.
4. `ndl doctor browser` is run for diagnostic only by default. Pass `--browser`
   to assert the runtime is fully wired up.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

_VERSION_PATTERN = re.compile(r"^NDL\s+\S+\s*$", re.MULTILINE)
_SMOKE_RULE_YAML = """
id: smoke_static
name: Smoke Static Rule
version: 1.0.0
author: NDL team
url_patterns:
  - pattern: "https://smoke.test/book/*"
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

    with tempfile.TemporaryDirectory(prefix="ndl-smoke-") as tmp:
        smoke_dir = Path(tmp)
        rule_path = smoke_dir / "smoke_static.yaml"
        rule_path.write_text(_SMOKE_RULE_YAML.strip() + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["NDL_HOME"] = str(smoke_dir / "ndl-home")
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
                expect_stdout_contains=["No rules loaded."],
            ),
            SmokeStep(
                name="ndl rules validate <fixture>",
                command=[args.ndl, "rules", "validate", str(rule_path)],
                ok_when_returncode=0,
                expect_stdout_contains=["Rule valid: smoke_static"],
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
            ok, report = _run_step(step, env=env)
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


def _run_step(step: SmokeStep, *, env: dict[str, str]) -> tuple[bool, str]:
    completed = subprocess.run(
        list(step.command),
        capture_output=True,
        text=True,
        check=False,
        env=env,
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


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


if __name__ == "__main__":
    sys.exit(main())
