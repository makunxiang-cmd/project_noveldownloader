# ADR-0001: Flat src-layout and stage-gated dependency growth

- Status: Accepted
- Date: 2026-04-30
- Context: P0/P1 implementation review

## Context

The original design spec (`docs/superpowers/specs/2026-04-20-ndl-design.md`) §2.1 and §8.1
described two things that, taken literally, would have shaped the repo differently:

1. An `infrastructure/` directory holding `fetchers/`, `parsers/`, `converters/`,
   `storage/`, `scheduler/`, and `rules/`.
2. A pyproject dependency list of ~25 packages spanning every roadmap phase
   (Web, scheduling, structured logging, i18n, ORM, retry libraries, rate-limit
   libraries, etc.).

During P0/P1 implementation we deliberately diverged from both. This ADR records the choice
so future reviewers do not treat the divergence as drift.

## Decision

### 1. Use a flat `src/ndl/` layout, not `src/ndl/infrastructure/`

`fetchers/`, `parsers/`, `converters/`, `rules/`, and (soon) `storage/` sit directly under
`src/ndl/`. There is no `infrastructure/` namespace package. The conceptual onion layering
in spec §2.1 is enforced by review and by `core/` having no internal imports — not by
directory nesting.

### 2. Introduce dependencies stage by stage

The runtime dependency set in `pyproject.toml` is intentionally minimal at each P-phase
boundary. New libraries are added only when the P-plan calling for them lands.

P1 runtime: `typer`, `rich`, `pydantic`, `pyyaml`, `selectolax`, `httpx`, `ebooklib`.

Future phases (per the plans and spec §8.1):

- P2: `SQLAlchemy>=2`
- P3: `fastapi`, `uvicorn`, `jinja2`, `sse-starlette`
- P4: `apscheduler`
- P5: `structlog`, `babel`
- P6 (extras): `playwright`

Libraries that the spec implied as "nice to have" but were absorbed by stdlib or already
covered (e.g. `tenacity` → custom retry in `HttpFetcher`; `aiolimiter` → `HostThrottle`;
`protego` → `urllib.robotparser` via `RobotsChecker`; `pydantic-settings` → not yet needed)
remain unintroduced unless a future plan justifies them.

## Consequences

**Positive**

- Smaller import graph, faster CI installs, fewer supply-chain entries to audit.
- New contributors can read the entire infrastructure layer without traversing a
  redundant package level.
- ADR makes the gap between spec §8.1 and current `pyproject.toml` legible rather than
  appearing as drift.

**Negative / risks**

- The conceptual "infrastructure" boundary is not surfaced by file layout, so reviewers
  must rely on import discipline (this is enforced by `core/` having no internal imports
  and by future PR review of `application/` not importing across infrastructure modules).
- The minimal-deps policy means we sometimes write small helpers (retry loop, throttle,
  robots check) that a library could provide. We accept that cost in exchange for
  predictable behavior and a smaller surface; if a hand-rolled helper grows past ~100
  lines or develops corner-case bugs, replacing it with the spec-listed library is a
  reasonable refactor and does not require a new ADR.

## Status of related spec sections

- Spec §2.1: now annotated with a note pointing to this ADR; the diagram retains the
  conceptual layering but no longer implies a physical `infrastructure/` directory.
- Spec §8.1: now annotated with a "P1 actually-installed" subset. The full list remains
  the v1.0 target.
