# NDL Domain Glossary

This file is the canonical vocabulary for the NDL codebase. When you author code, tests, issues,
or commit messages, use the terms defined here. If a concept you need is not in this list, that is
a signal to either reconsider naming or extend this glossary intentionally.

## Core entities

| Term | Definition |
|---|---|
| **Novel** | The single in-memory representation of a complete book (`ndl.core.models.Novel`). All flows — download, TXT/EPUB read, library read, format conversion — converge on `Novel` as the intermediate representation (IR). Formats never convert directly to one another. |
| **Chapter** | A fully fetched chapter in normalized plain-text form (`ndl.core.models.Chapter`). `index` is zero-based and unique within a Novel; chapters in a Novel are stored sorted by index. |
| **ChapterStub** | An index-page entry containing only `index`, `title`, and `url`. Produced by index parsing before chapter bodies are fetched. |

## Pipeline roles (Protocols)

| Term | Definition |
|---|---|
| **Fetcher** | Async role that turns a URL into response text (`ndl.core.protocols.Fetcher`). The default implementation is `HttpFetcher`, which honors per-host rate limits, retries, robots.txt, and rule-driven encoding. Browser-backed fetchers are P6+. |
| **Parser** | Role that turns fetched HTML into domain objects (`ndl.core.protocols.Parser`). `HtmlParser` binds a `SourceRule` to this Protocol. |
| **Writer** | Role that serializes a `Novel` into an output format (`ndl.core.protocols.Writer`). Implementations: `TxtWriter`, `EpubWriter`. |
| **Reader** | Role that hydrates a file back into a `Novel` (`ndl.core.protocols.Reader`). Implementations: `TxtReader`. EPUB / JSON readers are roadmap items. |

## Rule engine

| Term | Definition |
|---|---|
| **Rule** (a.k.a. **SourceRule**) | A YAML site adapter validated by Pydantic (`ndl.rules.schema.SourceRule`). Encodes URL patterns, fetcher policy, and the selectors needed to parse index and chapter pages. |
| **Selector** | A declarative field-extraction rule (`ndl.rules.schema.Selector`). Specifies a CSS path, an attribute or text mode, optional regex post-processing, and value mapping. |
| **Selector DSL** | The execution helpers in `ndl.rules.selector` that interpret `Selector` and `CleanRule` against `selectolax` HTML trees. |
| **Contract test** | A test that runs a bundled rule against fixed HTML fixtures and an expected JSON snapshot, ensuring the rule still produces the same `Novel` after refactors. Lives under `tests/contract/`. |

## Transport-neutral signals

| Term | Definition |
|---|---|
| **ProgressEvent** | A model emitted by services to communicate stage transitions and per-chapter progress (`ndl.core.progress.ProgressEvent`). Both CLI (`rich.progress`) and Web (SSE) consume the same events. |
| **ProgressCallback** | `Callable[[ProgressEvent], Awaitable[None]]`. Services accept this as an optional dependency; `None` means silent. |

## Architectural shape

| Term | Definition |
|---|---|
| **Onion / clean layering** | Source code is organized into four layers: `core/` (domain), infrastructure (`fetchers/` / `parsers/` / `converters/` / `rules/` / `storage/`), `application/` (services + container), and the delivery surface (`cli/`, future `web/`). Inner layers do not import outer layers. |
| **Flat src-layout** | Implementation detail: there is no `infrastructure/` directory; the infrastructure modules live directly under `src/ndl/`. See ADR-0001. |
| **ServiceContainer** | The single entry point that resolves rules and wires fetchers, parsers, readers, writers, and the convert service (`ndl.application.container.ServiceContainer`). CLI and Web both compose through it. |

## Compliance vocabulary

| Term | Definition |
|---|---|
| **Disclaimer gate** | First-run lawful-use acceptance check enforced by `ndl.cli.disclaimer.ensure_download_disclaimer`. The marker lives at `~/.ndl/disclaimer.accepted` (overridable via `NDL_HOME`). |
| **Robots policy** | Each rule declares `robots.respect`. `false` requires a non-empty `ignore_justification`. The `RobotsChecker` caches `robots.txt` per origin and matches against the same `User-Agent` used for real requests. |
| **Rate limit** | Each rule declares `rate_limit.min_interval_ms` (≥500) and `max_concurrency` (≤3). `HostThrottle` enforces both per-host. |
