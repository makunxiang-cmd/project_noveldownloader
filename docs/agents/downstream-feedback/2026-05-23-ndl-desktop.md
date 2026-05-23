# ndl-storykit 0.2 — Improvement Requirements From `ndl-desktop`

- **Date:** 2026-05-23
- **Origin:** authored in the downstream consumer `makunxiang-cmd/ndl-desktop` (at commit `d2a5361`, branch `docs/upstream-feedback`) and shared into this repo (`makunxiang-cmd/project_noveldownloader`) for the 0.2 release.
- **Target:** this repo, `ndl-storykit` 0.2 (current development version `0.2.0.dev0`).
- **Audience:** agents tasked with shipping `ndl-storykit 0.2`. Each item is self-contained — pick one or a group (track) and ship.

> Where this document says "downstream" or "the downstream", it means `ndl-desktop`. Where it cites file paths like `src/ndl_desktop/services/...`, those paths refer to the downstream repo, not this one. Where it cites upstream paths like `src/ndl/...` or `src/ndl/fetchers/browser.py`, those are paths in **this** repo.

## Purpose

Everything below is something `ndl-desktop` (the macOS GUI built on top of `ndl-storykit`) had to **work around in the downstream** because upstream couldn't do it. Each item names the downstream workaround file with line counts so you can measure success: shipping items 1–5 below would let `ndl-desktop` delete roughly **1,000 lines** of adapter code and revert to thin YAML rules.

Every requirement here is grounded in real shipped code: the bundled `x23zw` (browser-rendered chapter bodies + paginated index) and `qishuxia` (whole-book TXT archive) sources, plus the local TXT-import and EPUB-export flows.

---

## How to use this document

Each item is tagged with:

- **Severity:** Critical (real bug) / High (forces downstream rewrites) / Medium (real friction, downstream still ships) / Low (nice to have)
- **Effort:** S (≤ a day) / M (a few days) / L (a week+)
- **Component:** the upstream file/module
- **Dependencies:** other items that must land first

### Tracks (parallel-safe groupings)

A single agent can claim one track and work in isolation. Within a track, items are listed in dependency order.

| Track | Items | Description | Total effort |
|---|---|---|---|
| **A — Browser session lifecycle** | A1, A2 | Fix the broken Playwright `aclose()` paths. | S |
| **B — Search schema + service** | B1, B2 → D1, D2, D3 | POST search, browser search, dedupe. | M |
| **C — Pagination schema + service** | B3 → C1, C2 | Extend `PaginationType`; make `DownloadService` consume `pagination`. | M |
| **D — Archive download mode** | B4 → C3 | A new `download.type: archive` for whole-book TXT/ZIP endpoints. | M |
| **E — Update service alignment** | E1 (depends on C, D) | `UpdateService` reuses the per-rule download pipeline. | M |
| **F — TXT import quality-of-life** | F1, F2 | Default `source_url`; recognise `书名:`/`标题:` prefixes. | S |
| **G — Styled EPUB output** | G1 | Either ship a styled writer or expose hooks. | M |
| **H — Packaging hygiene** | H1, H2 | Stop shipping the demo rule; document which schema fields are consumed. | S |
| **I — Selector enrichment** | I1 | Pick "second of multiple containers". Unblocks several rule simplifications. | S |

### Recommended landing order

1. **A** (frees the downstream of its runtime monkey-patch).
2. **C + D** in parallel (collapse the two largest adapters).
3. **B** (collapse the two search adapters).
4. **E** (collapse the two update adapters; depends on C and D).
5. **F + H + I** at any point — small and independent.
6. **G** last — the downstream styled writer is self-contained and not breaking anything.

After A–E land, downstream `ndl-desktop` can delete: `services/upstream_patches.py`, `services/x23zw_download.py`, `services/qishuxia_download.py`, `services/x23zw_search.py`, `services/qishuxia_search.py`, `services/x23zw_update.py`, `services/qishuxia_update.py`, `services/update_common.py`, and the per-rule branches in `services/container.py:download()` / `update_novel()` / `search()`.

---

## A — Browser session lifecycle bugs

### A1. `_PlaywrightBrowserSession.aclose()` crashes every browser shutdown

**Severity:** Critical (bug)
**Effort:** S
**Component:** `src/ndl/fetchers/browser.py:243-246`

#### Current behaviour

```python
# src/ndl/fetchers/browser.py:243
async def aclose(self) -> None:
    await self._context.close()
    await self._browser.close()
    await self._manager.stop()
```

`self._manager` is the `PlaywrightContextManager` object returned by `async_playwright()` (constructed at line 159: `manager = async_playwright()`). `PlaywrightContextManager` has `start()` and `__aexit__()` — **not** `stop()`. The bound `Playwright` instance (the one returned by `await manager.start()`) is what has a `stop` attribute.

#### Symptom

Every browser-source cleanup raises `AttributeError: 'PlaywrightContextManager' object has no attribute 'stop'`. In `ndl-desktop`, this happens after every x23zw or qishuxia download and after every Settings-page "检查浏览器运行时" click.

#### Evidence from `ndl-desktop`

Runtime monkey-patch in `src/ndl_desktop/services/upstream_patches.py:53-89` (`_patch_playwright_browser_session_aclose`). The patch replaces `aclose` with:

```python
async def patched_aclose(self: Any) -> None:
    await self._context.close()
    await self._browser.close()
    manager_stop = getattr(self._manager, "stop", None)
    if manager_stop is not None:
        await manager_stop()
        return
    await self._manager.__aexit__(None, None, None)
```

#### Proposed fix

Either:
- Store the started `Playwright` instance (return value of `await manager.start()`) on `_PlaywrightBrowserSession` and call its `stop()`, **or**
- Keep `manager` on the session and call `await self._manager.__aexit__(None, None, None)`.

The cleaner option is the first: rename `self._manager` to `self._playwright` and assign it from `await manager.start()` in `_playwright_session()` (line 164). Then `aclose` calls `await self._playwright.stop()`.

#### Acceptance criteria

1. `ndl/fetchers/browser.py` no longer references `self._manager.stop()`.
2. Running a browser-source download (e.g., x23zw) followed by `fetcher.aclose()` does not raise `AttributeError`.
3. Repeated `check_browser_runtime()` calls succeed without leaking processes (verified by counting `chromium-headless-shell` processes before and after).
4. Add a regression test in `tests/fetchers/test_browser.py` that exercises the close path with a mocked `async_playwright()` and asserts no exception.

#### Migration / compat

None — pure bug fix. Downstream `ndl-desktop` will delete `_patch_playwright_browser_session_aclose` from `upstream_patches.py` once 0.2 is pinned.

---

### A2. `_safe_stop_manager()` silently swallows the same bug

**Severity:** High (silent leak, not crash)
**Effort:** S
**Component:** `src/ndl/fetchers/browser.py:288-290`

#### Current behaviour

```python
# src/ndl/fetchers/browser.py:288
async def _safe_stop_manager(manager: Any) -> None:
    with contextlib.suppress(Exception):
        await manager.stop()
```

Used at line 180 (in the error path of `_playwright_session()`) and line 276 (`BrowserFetcher.aclose()` cleanup). The `contextlib.suppress(Exception)` means the AttributeError from A1 is silently dropped — the manager never actually shuts down, leaking the headless Chromium child process.

#### Symptom

Every browser-source failure path leaks a Chromium process. Visible when the Settings-page diagnostic runs in a loop on a misconfigured environment — process count grows.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/upstream_patches.py:91-118` (`_patch_playwright_safe_stop_manager`) replaces `_safe_stop_manager` with a version that falls through to `__aexit__` when `stop` is absent.

#### Proposed fix

After A1, `manager` is consistently either the `Playwright` instance (which has `stop()`) or the `PlaywrightContextManager` (which has `__aexit__`). Settle on one type throughout `_playwright_session()` and `BrowserFetcher.aclose()` and use the correct method. If you keep `_safe_stop_manager` as a helper at all, make it call the right method based on the actual type rather than swallowing exceptions.

A clean version:

```python
async def _safe_stop(playwright: Any) -> None:
    if playwright is None:
        return
    with contextlib.suppress(Exception):
        await playwright.stop()
```

…where `playwright` is the started `Playwright` instance, not the context manager.

#### Acceptance criteria

1. No `contextlib.suppress(Exception)` around `manager.stop()` or `__aexit__()` in normal paths (one suppress in error-handling cleanup is acceptable).
2. Running browser-source download in a loop (10×) leaves zero leaked `chromium-headless-shell` processes.
3. Failure path test: a `_playwright_session()` failure correctly cleans up the started Playwright runtime.

#### Migration / compat

None — pure bug fix.

---

## B — Rule schema additions

### B1. `SearchRule`: support POST + body

**Severity:** High
**Effort:** S (schema only) + M (paired service work in D1)
**Component:** `src/ndl/rules/schema.py:213-219`

#### Current behaviour

```python
# src/ndl/rules/schema.py:213
class SearchRule(StrictModel):
    """Optional search endpoint parsing rule."""

    url_template: str
    results_container: str
    items: str
    fields: SearchFields
```

The implicit assumption is GET. There's no `method`, no `body`, no `headers` distinct from the parent `FetcherRule`.

#### Problem

x23zw rejects GET; its search endpoint at `https://x23zw.com/search.html` requires `POST` with `data={"s": keyword}`. No YAML expression for this — the whole search has to live in a desktop adapter.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/x23zw_search.py` (entire file, ~90 lines):

```python
# x23zw_search.py:28-37
async def search_x23zw(rule: SourceRule, keyword: str) -> list[SearchResult]:
    headers = resolve_headers(rule)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        response = await client.post(_SEARCH_URL, data={"s": keyword})
    ...
```

The container dispatches to this adapter at `src/ndl_desktop/services/container.py:DesktopServiceContainer.search()` (the `if rule.id == "x23zw"` branch).

#### Proposed fix — schema

```python
SearchMethod = Literal["GET", "POST"]

class SearchRule(StrictModel):
    method: SearchMethod = "GET"
    url_template: str
    # When method == "POST": form-encoded body. The {keyword} placeholder is
    # substituted with the (URL-encoded for GET, plain for POST) user query.
    body: dict[str, str] | None = None
    results_container: str
    items: str
    fields: SearchFields

    @model_validator(mode="after")
    def _body_only_for_post(self) -> SearchRule:
        if self.method == "GET" and self.body is not None:
            raise ValueError("body is only valid when method='POST'")
        return self
```

The downstream-equivalent YAML for x23zw becomes:

```yaml
search:
  method: POST
  url_template: "https://x23zw.com/search.html"
  body:
    s: "{keyword}"
  results_container: ".txt-list"
  items: "li"
  fields:
    title: { selector: "a[href^='/shu/']", attr: text }
    author: { selector: "a[href^='/author/']", attr: text }
    url: { selector: "a[href^='/shu/']", attr: href, resolve: relative }
```

#### Acceptance criteria

1. Schema accepts `method: POST` with `body:` and validates the model_validator above.
2. `tests/rules/test_schema.py` covers: GET (existing), POST with body, POST without body (error), GET with body (error).

#### Dependencies

Paired with **D1** (service consumes the new fields).

---

### B2. `SearchRule`: support browser-fetcher search

**Severity:** High
**Effort:** S (schema) + M (paired service work in D2)
**Component:** `src/ndl/rules/schema.py:213-219`

#### Problem

When `fetcher.type: browser`, search has to navigate to a page, fill a form, click submit, wait for results, and parse them. The current `SearchRule` has no fields for any of this.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/qishuxia_search.py` (entire file, ~131 lines). Real flow:

```python
# qishuxia_search.py:50-70 (paraphrased)
await page.goto(_HOME_URL, wait_until="domcontentloaded", timeout=30000)
await page.fill("input[name='searchkey']", keyword)
await page.locator(".btn-tosearch").click(timeout=30000)
await page.wait_for_url("**/modules/article/search.php**", ...)
html = await page.content()
```

#### Proposed fix — schema

Extend `SearchRule` with an optional `browser:` block. When present (and the parent rule's `fetcher.type` is `browser`), the search service uses the browser flow instead of the HTTP flow.

```python
class BrowserSearchRule(StrictModel):
    navigate_url: str          # e.g. "https://www.qishuxia.com/"
    input_selector: str        # e.g. "input[name='searchkey']"
    submit_selector: str       # e.g. ".btn-tosearch"
    # Either wait for a URL match or for a result selector to appear.
    wait_for_url: str | None = None       # glob pattern, like Playwright wait_for_url
    wait_for_selector: str | None = None  # CSS selector

    @model_validator(mode="after")
    def _one_wait_required(self) -> BrowserSearchRule:
        if not (self.wait_for_url or self.wait_for_selector):
            raise ValueError("Either wait_for_url or wait_for_selector must be set")
        return self


class SearchRule(StrictModel):
    # ... existing fields ...
    browser: BrowserSearchRule | None = None
```

#### Acceptance criteria

1. A YAML rule with `fetcher.type: browser` AND `search.browser: { ... }` validates.
2. Schema rejects `search.browser` when `fetcher.type` is NOT `browser` (cross-rule validator).
3. Test fixture covers the full qishuxia-style rule.

#### Dependencies

Paired with **D2** (service consumes the new fields).

---

### B3. `PaginationType`: extend beyond `none | next`

**Severity:** High (silently inert today — see C1/C2)
**Effort:** S
**Component:** `src/ndl/rules/schema.py:16` and `src/ndl/rules/schema.py:174-186`

#### Current behaviour

```python
# src/ndl/rules/schema.py:16
PaginationType = Literal["none", "next"]

# src/ndl/rules/schema.py:174
class PaginationRule(StrictModel):
    type: PaginationType = "none"
    next: Selector | None = None
    terminator: str | None = None
    # validator: type=="next" requires `next:` selector
```

The schema permits `type: "next"` and validates a selector is provided. **But the `DownloadService` (`src/ndl/application/services/download.py`) never reads `rule.index.pagination` or `rule.chapter.pagination`.** A rule that sets `type: "next"` gets the same behaviour as `type: "none"` — silent no-op.

#### Problem

`type: "next"` is half-built: schema yes, service no. And `next-link` alone doesn't cover real sites like x23zw which expose the index either as an explicit "查看更多章节" link (`<a class="btn-mulu" href="index_1.html">`) **or** as a template-discoverable pattern (`/shu/{id}/index_{n}.html`).

#### Proposed fix — schema

Extend the literal and the pagination model:

```python
PaginationType = Literal["none", "next", "index-template"]

class PaginationRule(StrictModel):
    type: PaginationType = "none"

    # type == "next": follow the link matched by `next:` until it disappears
    # or matches `terminator:`.
    next: Selector | None = None

    # type == "index-template": iterate a URL template until the page yields no
    # new items (or until `max_pages` is hit as a safety net).
    template: str | None = None   # e.g. "{source_url}index_{page}.html"
    start: int = 2                # first page number to try (page 1 is source_url)
    max_pages: int = 50

    # Optional terminator selector: stop when the page contains a matching element.
    terminator: str | None = None

    @model_validator(mode="after")
    def _required_fields(self) -> PaginationRule:
        if self.type == "next" and self.next is None:
            raise ValueError("pagination.next is required when type='next'")
        if self.type == "index-template" and self.template is None:
            raise ValueError("pagination.template is required when type='index-template'")
        if self.type != "index-template" and self.template is not None:
            raise ValueError("pagination.template only valid when type='index-template'")
        return self
```

#### Acceptance criteria

1. Schema validates all four combinations (`none`, `next` with selector, `index-template` with template, errors otherwise).
2. Test fixtures: x23zw-style `type: next` against the `<a class="btn-mulu">` selector; `type: index-template` with `{source_url}index_{page}.html`.

#### Dependencies

Paired with **C1** (service consumes the new fields).

---

### B4. New `download.archive` block for whole-book TXT/ZIP endpoints

**Severity:** Medium (qishuxia-specific today, but a recognised pattern)
**Effort:** M
**Component:** `src/ndl/rules/schema.py` — new `ArchiveDownloadRule`, added to `SourceRule`

#### Problem

Some sites expose a whole-book TXT (or ZIP) endpoint. The directory page lists chapter titles + per-chapter URLs, but the cheap path is one HTTP fetch for the entire archive plus a local splitter against the chapter-title list. The current schema has no way to express this — the only download model is "fetch each chapter page individually."

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/qishuxia_download.py` (entire file, ~260 lines). Real flow:

```python
# qishuxia_download.py:38-50
book_id = _book_id(url)                       # "/book/69600/" -> "69600"
book_url = f"https://www.qishuxia.com/book/{book_id}/"
# fetch detail page (via browser; site is JS-rendered),
# also expects a TXT download triggered by clicking 'a[href*="txtarticle.php"]'
html, txt_bytes = await _fetch_detail_and_txt(book_url)
novel, _ = parser.parse_index(html, source_url=book_url)
stubs = _parse_index_stubs(html, source_url=book_url)
text = _decode_full_text(txt_bytes)            # gb18030/utf-8-sig fallback
chapters = _parse_full_text_chapters(text, stubs)
```

#### Proposed fix — schema

```python
ArchiveFormat = Literal["txt"]   # zip can be added later when a real site demands it
ArchiveTriggerType = Literal["url-template", "selector"]


class ArchiveDownloadRule(StrictModel):
    format: ArchiveFormat = "txt"

    # How to get the archive bytes:
    # - "url-template": archive_url is a template substituting `{source_url_path_id}`
    #   or `{source_url}` etc.
    # - "selector": after rendering the index page, click/anchor the element
    #   matched by this CSS selector and capture the resulting download.
    trigger: ArchiveTriggerType
    url_template: str | None = None
    selector: str | None = None

    # For "txt": encodings to try in order before falling back to a lossy decode.
    encodings: list[str] = Field(default_factory=lambda: ["utf-8-sig", "gb18030", "gbk"])

    # Regex lines to drop from the decoded text (site-injected ads / watermarks).
    strip_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _trigger_field(self) -> ArchiveDownloadRule:
        if self.trigger == "url-template" and not self.url_template:
            raise ValueError("url_template required for trigger='url-template'")
        if self.trigger == "selector" and not self.selector:
            raise ValueError("selector required for trigger='selector'")
        return self


class SourceRule(StrictModel):
    # ... existing fields ...
    # Optional. When present, DownloadService uses the archive path instead
    # of per-chapter fetches. The chapter_list selectors are still required
    # (we need them to split the archive into chapters).
    download_archive: ArchiveDownloadRule | None = None
```

YAML for qishuxia becomes:

```yaml
download_archive:
  format: txt
  trigger: selector
  selector: "a[href*='txtarticle.php']"
  encodings: ["utf-8-sig", "gb18030", "gbk"]
  strip_patterns:
    - "^一秒记住【.*?】，为您提供精彩小说阅读。?$"
    - "^最新网址：?.*$"
```

#### Acceptance criteria

1. Schema validates both trigger modes; rejects mismatched fields.
2. Test fixture covers a qishuxia-style rule.

#### Dependencies

Paired with **C3** (service consumes the new fields).

---

### B5. Container disambiguation: pick "second of multiple matches"

**Severity:** Medium
**Effort:** S
**Component:** `src/ndl/rules/schema.py` (`ChapterListRule.container`)

#### Problem

x23zw book pages contain two `<ul class="section-list">` elements: the first is the latest-12-chapters strip, the second is the full list (~100 chapters). Today the rule disambiguates via the attribute-value hack `container: 'ul[class="fix section-list"]'` — relies on exact class-string ordering, brittle when the site reorders class tokens.

#### Proposed fix

Either:

**Option A** — accept `:nth-of-type(N)` in the CSS selector. This is the cheapest fix if the CSS engine in use is `cssselect` (it supports nth-of-type out of the box).

**Option B** — extend `ChapterListRule` with an explicit picker:

```python
ContainerPick = Literal["first", "last", "largest"]

class ChapterListRule(StrictModel):
    container: str = Field(min_length=1)
    pick: ContainerPick = "first"   # which match to pick when selector matches multiple
    items: str = Field(min_length=1)
    title: Selector
    url: Selector
```

`pick: largest` would resolve x23zw cleanly: "the `<ul class="section-list">` with the most `<li>` children."

#### Acceptance criteria

1. Schema accepts `pick:` and applies it during index parsing.
2. Test fixture: x23zw `book4020.html` fixture (already in this repo at `tests/fixtures/x23zw/book4020.html`) parses correctly with `container: "ul.section-list"`, `pick: "largest"`.

---

## C — Download service consumes the new schema

### C1. `DownloadService` honours `index.pagination`

**Severity:** High
**Effort:** M
**Component:** `src/ndl/application/services/download.py:28-50`

#### Current behaviour

```python
# src/ndl/application/services/download.py:28
index_html = await self._fetcher.get(url)
novel, stubs = self._parser.parse_index(index_html, source_url=url)
```

One fetch. Whatever `rule.index.pagination` says, ignored.

#### Problem

Sites with paginated indexes (x23zw, …) silently lose chapters past the first page.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/x23zw_download.py:60-128` (`_fetch_all_index_pages`, `_next_index_url`). The core loop:

```python
# x23zw_download.py:106-128 (paraphrased)
next_url = _next_index_url(first_html, url)
page_count = 1
while next_url and next_url not in visited and page_count < _MAX_INDEX_PAGES:
    visited.add(next_url)
    page_count += 1
    html = await _fetch_with_retries(fetcher, next_url, ...)
    page_stubs = _parse_index_stubs(rule, html, source_url=next_url, start_index=len(stubs))
    added = _extend_unique_stubs(stubs, seen_chapters, page_stubs)
    next_url = _next_index_url(html, next_url) if added else None
```

#### Proposed fix

In `DownloadService.download()` and any helper, after the first `parse_index`, consult `rule.index.pagination`:

- `type == "none"`: today's behaviour.
- `type == "next"`: follow `pagination.next` selector chain. Stop when (a) selector matches nothing, (b) URL matches `terminator`, (c) the same URL is seen twice (cycle guard), (d) safety cap (e.g. 200 pages).
- `type == "index-template"`: iterate `n = pagination.start, start+1, ...` substituting into `pagination.template`. Stop when fetched page yields zero new stubs (de-dupe by URL), or `max_pages` reached, or `terminator` selector present.

The "dedupe by chapter URL" logic should be in the service — the loop must combine pages without double-counting overlapping chapters across page boundaries.

```python
# Sketch
all_stubs: list[ChapterStub] = []
seen_urls: set[str] = set()
_extend_unique(all_stubs, seen_urls, first_stubs)

if rule.index.pagination.type != "none":
    for next_url in _iterate_pagination(rule.index.pagination, first_html, url):
        page_html = await self._fetcher.get(next_url)
        _, page_stubs = self._parser.parse_index(page_html, source_url=next_url)
        added = _extend_unique(all_stubs, seen_urls, page_stubs)
        if not added:
            break
```

`_iterate_pagination` is the new private helper that yields URLs lazily based on pagination type.

#### Acceptance criteria

1. Existing tests still pass (rules with `type: "none"` are unaffected).
2. New test: a rule with `type: "next"` against two fixture pages where the second only contributes new stubs — service combines them correctly.
3. New test: a rule with `type: "index-template"` against three fixture pages, terminating on the empty third page.
4. New test: cycle guard — if pagination keeps yielding the same URL, the loop exits cleanly.
5. The x23zw HTML fixture in `tests/fixtures/x23zw/book4020.html` (downstream) becomes a usable upstream fixture for this test.

#### Dependencies

**B3** (schema for `index-template`).

---

### C2. `DownloadService` honours `chapter.pagination`

**Severity:** High
**Effort:** M
**Component:** `src/ndl/application/services/download.py:90-102`

#### Current behaviour

```python
# src/ndl/application/services/download.py:97
async def _fetch_chapter(self, stub: ChapterStub) -> Chapter:
    chapter_html = await self._fetcher.get(stub.url)
    return self._parser.parse_chapter(chapter_html, index=stub.index, source_url=stub.url)
```

One fetch per chapter. `rule.chapter.pagination` ignored.

#### Problem

Sites that split long chapters across multiple pages (`{id}.html`, `{id}_2.html`, …) silently lose the tail of each chapter.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/x23zw_download.py:201-247` (`_fetch_full_chapter`, `_next_chapter_page_url`, `_chapter_stem`):

```python
# x23zw_download.py:213-228 (paraphrased)
first = parser.parse_chapter(html, index=stub.index, source_url=stub.url)
parts = [_clean_chapter_part(first.content, first.title)]
visited = {stub.url}
next_url = _next_chapter_page_url(html, stub.url)
while next_url and next_url not in visited and page_count < _MAX_CHAPTER_PAGES:
    visited.add(next_url)
    page = parser.parse_chapter(html_next, index=stub.index, source_url=next_url)
    parts.append(_clean_chapter_part(page.content, first.title))
    next_url = _next_chapter_page_url(html_next, stub.url)
return Chapter(..., content="\n\n".join(parts))
```

The critical detail in `_next_chapter_page_url`: only follow the "下一" link if the next page's URL stem matches the first page's stem — otherwise the "下一" link goes to the *next chapter*, not the next *page* of the current chapter. The downstream uses `_chapter_stem` to compare.

#### Proposed fix

When `rule.chapter.pagination.type == "next"`:

1. Fetch page 1, parse; remember the URL stem (last path segment up to `.html`, minus a trailing `_<digit>+` suffix).
2. Apply `pagination.next` selector to the parsed HTML — if it matches and the resolved URL's stem **matches** the page-1 stem, follow it. Otherwise stop.
3. Cap at e.g. 50 pages.
4. Concatenate page bodies (the parser already has the per-page content via `parse_chapter`).
5. Build a single `Chapter` with `index=stub.index`, `title=page1.title`, `content="\n\n".join(parts)`, `source_url=stub.url`.

The stem-matching rule is the non-obvious bit; document it in the schema or implement it as the default fallback so rule authors don't have to redo it.

#### Acceptance criteria

1. Test: a chapter split across `chapter_001.html` and `chapter_001_2.html`, with a "下一" link at the end of page 2 pointing to `chapter_002.html` — service collects pages 1 and 2 into one chapter, does NOT follow into chapter 2.
2. Test: a chapter with only one page works unchanged (pagination is a no-op).
3. Existing tests still pass.

#### Dependencies

**B3** (`type: "next"` already exists in schema; this is service consumption).

---

### C3. `DownloadService` supports `SourceRule.download_archive`

**Severity:** Medium
**Effort:** M
**Component:** `src/ndl/application/services/download.py` — new code path when `rule.download_archive` is set

#### Proposed flow

When `rule.download_archive is not None`:

1. Fetch index (no pagination — archive downloads imply a single index page; if pagination is also set, error out at schema validation time).
2. Parse `novel` and `stubs` from the index HTML.
3. Fetch the archive bytes:
   - `trigger == "url-template"`: format the template (substitute `{source_url}`, `{source_url_path_id}`, etc.) and HTTP-GET it.
   - `trigger == "selector"`: if `fetcher.type == "browser"`, locate the selector on the rendered page and capture the resulting download via Playwright's `expect_download`. If `fetcher.type` is HTTP, error — selector-trigger requires browser.
4. Decode bytes per `encodings` list (try each, fall through to last with `errors="replace"`).
5. Apply `strip_patterns` to filter noise lines.
6. Split the decoded text into chapters by matching against the index `stubs`' titles — a simple line-by-line scan tracking the current stub index, looking for the next stub's normalized title.
7. Return `Novel` with the split chapters.

The splitter is the non-trivial piece; the downstream `_parse_full_text_chapters` in `qishuxia_download.py:163-191` is a working reference (with the bounded lookahead for out-of-order matches).

#### Acceptance criteria

1. A rule with `download_archive.trigger == "url-template"` fetches one URL and splits the result correctly.
2. A rule with `download_archive.trigger == "selector"` requires `fetcher.type == "browser"`; schema rejects otherwise.
3. Test fixture: a small TXT archive with N chapters from the upstream's test corpus.

#### Dependencies

**B4** (schema).

---

## D — Search service consumes the new schema

### D1. `SearchService` supports POST search

**Severity:** High
**Effort:** S
**Component:** `src/ndl/application/services/search.py`

When `rule.search.method == "POST"`, send a POST with `body` form-encoded. Substitute `{keyword}` in body values with the user's query (URL-encoded? No — POST bodies are form-encoded, not URL-encoded; just pass the raw string and let `httpx` encode it).

#### Acceptance criteria

1. Test: a rule with `method: POST` against a fixture POST endpoint returns parsed results.
2. Test: a rule with `method: GET` (existing behavior) unaffected.

#### Dependencies

**B1**.

---

### D2. `SearchService` supports browser search

**Severity:** High
**Effort:** M
**Component:** `src/ndl/application/services/search.py`

When `rule.fetcher.type == "browser"` AND `rule.search.browser is not None`, take the browser path:

1. Open a browser session.
2. Navigate to `rule.search.browser.navigate_url`.
3. Fill `input_selector` with the keyword.
4. Click `submit_selector`.
5. Wait for `wait_for_url` (Playwright `page.wait_for_url`) OR `wait_for_selector` (Playwright `page.wait_for_selector`).
6. Capture `page.content()`.
7. Parse with the existing `results_container` / `items` / `fields` selectors against the captured HTML.
8. Close the browser session.

Reuse the existing `BrowserFetcher`'s session-creation helper rather than re-implementing Playwright bootstrapping inside the search service.

#### Acceptance criteria

1. Test (with mocked Playwright): a browser-search rule completes the fill+submit+wait+parse path.
2. The Settings-page "检查浏览器运行时" path remains unaffected.

#### Dependencies

**B2**, and indirectly **A1/A2** (browser cleanup must be correct or the test pollutes process state).

---

### D3. `SearchService.search()` deduplicates by `(source_rule_id, url)` before returning

**Severity:** Low
**Effort:** S
**Component:** `src/ndl/application/services/search.py:SearchService.search()`

#### Current behaviour

Each rule's results are concatenated in `SearchOutcome.results`. Duplicates within a single rule or across rules (rare but possible — e.g., one rule has a redirect URL, another resolves it) are not removed.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/container.py:_dedupe_search_results` reimplements this:

```python
def _dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
    deduped: list[SearchResult] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        key = (getattr(result, "source_rule_id", ""), getattr(result, "url", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped
```

#### Proposed fix

Move the dedupe into `SearchService.search()` so every consumer gets clean results. Keep it idempotent — if a downstream still calls a dedupe of its own, it should be a no-op.

#### Acceptance criteria

1. Test: a rule that returns the same `(rule_id, url)` twice → service returns it once.
2. Downstream `_dedupe_search_results` becomes a no-op after upgrade.

---

## E — Update service alignment

### E1. `UpdateService` routes through the per-rule download pipeline

**Severity:** High
**Effort:** M
**Component:** `src/ndl/application/services/update.py:_update_novel_with_pool`

#### Current behaviour

```python
# src/ndl/application/services/update.py:142
index_html = await fetcher.get(novel.source_url)
latest, stubs = parser.parse_index(index_html, source_url=novel.source_url)
stored_indices = {chapter.index for chapter in novel.chapters}
new_stubs = [stub for stub in stubs if stub.index not in stored_indices]
```

One fetch. No pagination. No archive support. Uses `stub.index` as the dedupe key — broken when re-running an index re-indexes the same chapters (which happens if the site inserts a chapter mid-list).

#### Problem

Once C1, C2, C3 land, downloads support pagination and archives — but updates don't. The asymmetry means custom adapters need TWO downstream paths (download_x23zw, update_x23zw) instead of one.

#### Evidence from `ndl-desktop`

The desktop ships an entire parallel adapter set just for updates:
- `src/ndl_desktop/services/x23zw_update.py` (~52 lines)
- `src/ndl_desktop/services/qishuxia_update.py` (~46 lines)
- `src/ndl_desktop/services/update_common.py` (~62 lines)
- The dispatch in `services/container.py:DesktopServiceContainer.update_novel()`.

Plus a custom `UpdateOutcome` dataclass because the downstream's `skipped` semantics differ from upstream's.

#### Proposed fix

Refactor `UpdateService._update_novel_with_pool` to:

1. Call `DownloadService.fetch_index_only(url, rule)` (a new method) which returns `(Novel, list[ChapterStub])` after applying pagination per C1. This step is cheap (no per-chapter fetches yet).
2. Compute `new_stubs` by **URL** diff against `novel.chapters`:
   ```python
   stored_urls = {_normalize(c.source_url) for c in novel.chapters if c.source_url}
   new_stubs = [s for s in latest_stubs if _normalize(s.url) not in stored_urls]
   ```
   This is more robust than the current index-based diff against re-indexing.
3. If there are new stubs, call `DownloadService.fetch_chapters(rule, new_stubs)` which applies C2 chapter pagination per stub.
4. If the rule has `download_archive` (C3), this changes — for archive sources, you have to fetch the whole archive again, then take only the tail chapters after the URL diff. The downstream `qishuxia_update.py` already implements this; mirror it.
5. Re-index new chapters: `index = max(stored index, default=-1) + 1 + i`. Sort by index. Append via `LibraryService.append_chapters`.
6. Status sync: if `latest.status != novel.status`, call `append_chapters` with the new status even if `new_stubs` is empty (already done by current code — preserve).

In other words: `UpdateService` should be a *thin wrapper* over `DownloadService`, not a parallel reimplementation.

#### Acceptance criteria

1. After landing C1+C2+E1, a rule with `index.pagination.type: "next"` (or `index-template`) correctly updates a saved novel — fetches paginated index, computes URL-based diff, fetches only new chapters, appends them.
2. After landing C3+E1, a rule with `download_archive` correctly updates a saved novel — re-fetches archive, diffs against stored chapter URLs, appends only the tail.
3. The downstream test corpus from `ndl-desktop` (the same fixture pairs used in `tests/unit/test_x23zw_update.py` / `tests/unit/test_qishuxia_update.py`) becomes redundant when consumed by upstream tests.
4. Downstream `services/x23zw_update.py`, `qishuxia_update.py`, `update_common.py` can be deleted after this lands.

#### Dependencies

**C1, C2, C3** (must land first). Also benefits from **A1/A2**.

---

## F — TXT import quality of life

### F1. `TxtReader` defaults `source_url` to `file://{absolute_path}`

**Severity:** Medium
**Effort:** S
**Component:** `src/ndl/parsers/txt_reader.py:_parse_metadata`

#### Current behaviour

```python
# src/ndl/parsers/txt_reader.py:127
def _parse_metadata(lines: list[str], source_path: Path) -> _TxtMetadata:
    title = source_path.stem
    author = "unknown"
    source_url: str | None = None         # only set if `来源:` line present
    ...
```

A TXT file without an explicit `来源:` line yields `Novel(source_url=None)`. The library upsert key is `(source_rule_id, source_url)` — `None` means every re-import inserts a duplicate row instead of upserting.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/txt_import.py:_read_with_default_source` (~30 lines) back-fills:

```python
return novel.model_copy(update={
    "source_url": f"file://{path.resolve()}",
    ...
})
```

#### Proposed fix

In `_parse_metadata`, default `source_url` to `f"file://{source_path.resolve()}"` when no `来源:` line is found. The `file://` scheme is honest about origin and lets the library upsert deterministically.

#### Acceptance criteria

1. `TxtReader().read("foo.txt")` returns a `Novel` whose `source_url == f"file://{Path('foo.txt').resolve()}"`.
2. Explicit `来源: https://example.com/...` lines still take precedence over the default.
3. `LibraryService.save()` of two reads of the same TXT file results in one library row.
4. Downstream `_read_with_default_source` becomes a no-op (or just an override-applier) after upgrade.

---

### F2. `TxtReader` recognises common Chinese title-line prefixes

**Severity:** Low
**Effort:** S
**Component:** `src/ndl/parsers/txt_reader.py:_parse_metadata`

#### Current behaviour

`_parse_metadata` recognises `# Title` (markdown H1), then on subsequent untitled lines treats the first non-metadata line as the title (`title_set = True` flips). It does NOT recognise:
- `书名：神雕侠侣`
- `标题：神雕侠侣`
- `Title: My Novel`

These end up stored verbatim as the title, e.g. `"书名：神雕侠侣"` instead of `"神雕侠侣"`.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/txt_import.py:_TITLE_PREFIX_RE` strips:

```python
_TITLE_PREFIX_RE = re.compile(r"^\s*(?:书名|标题|Title)\s*[:：]\s*", flags=re.IGNORECASE)
```

…then applies it post-read to the parsed title.

#### Proposed fix

Add a `_TITLE_LABELS` tuple alongside the existing `_AUTHOR_LABELS` / `_SOURCE_LABELS` / `_RULE_LABELS`:

```python
_TITLE_LABELS = ("书名:", "书名：", "标题:", "标题：", "Title:", "Title：", "title:")
```

Treat title-labeled lines symmetrically with author/source/rule lines. Keep the existing `# Markdown H1` path.

#### Acceptance criteria

1. A TXT starting with `书名：神雕侠侣\n作者：金庸\n...` parses to `Novel(title="神雕侠侣", author="金庸")`.
2. Existing fixtures (markdown-H1 path, no-prefix path) unchanged.
3. Downstream `_TITLE_PREFIX_RE` becomes redundant.

---

## G — Styled EPUB output

### G1. Either ship a styled EPUB writer or expose hooks

**Severity:** Medium
**Effort:** M
**Component:** `src/ndl/converters/` (EPUB writer)

#### Current behaviour

`ConvertService.convert(novel, output_path, target_format="epub")` produces a minimal, unstyled EPUB: one `<h1>` per chapter, plain `<p>` paragraphs, no cover, no title page, no stylesheet.

#### Problem

The output is acceptable for KOReader but visually flat on Apple Books. Any reader app shipping `ndl-storykit` has to either accept the flat output or replace the writer.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/styled_epub_writer.py` (~280 lines) — independent ebooklib writer with:
- Songti/Source-Han serif stack
- Justified body, 2em first-line indent
- Centred chapter titles with page break + ornament divider
- Title page with synopsis
- Cover image best-effort-downloaded from `novel.cover_url`

#### Proposed fix — choose one

**Option A** (preferred): ship a styled writer in upstream. Use ebooklib as the dependency. The downstream styled writer is a working reference — copy the layout, stylesheet, cover-download logic, and the gotcha noted in `styled_epub_writer.py` ("`EpubHtml.content` must be inner-body HTML only; wrapping with `<html>` yourself crashes lxml in `_get_nav`").

**Option B**: expose hooks on the existing writer so downstreams can inject a stylesheet, a title-page template (HTML string or callable), and a cover-fetcher callback without replacing the writer entirely.

Option A is preferred because (a) every downstream wants nice output, and (b) personal-use apps shouldn't have to ship 280 lines of EPUB plumbing.

#### Acceptance criteria

1. The EPUB produced by `ConvertService.convert(..., target_format="epub")` opens cleanly in Apple Books, KOReader, and `calibre`.
2. Output includes: cover (when `novel.cover_url` or `novel.cover_data` is set), title page with `novel.title`/`novel.author`/`novel.summary`, and chapter pages with consistent styling.
3. The downstream `services/styled_epub_writer.py` can be deleted (Option A) or simplified to a config dict (Option B).

---

## H — Packaging hygiene

### H1. Don't ship `example_static` in the production package

**Severity:** Medium
**Effort:** S
**Component:** `src/ndl/builtin_rules/` (the directory `loader.py:65` reads via `resources.files("ndl.builtin_rules")`)

#### Current behaviour

`load_builtin_rules()` returns a rule whose `id == "example_static"`. The desktop has to filter it out or users would see "example_static" alongside real rules in the Settings page rule list.

#### Evidence from `ndl-desktop`

`src/ndl_desktop/services/container.py:_UPSTREAM_EXAMPLE_RULE_IDS`:

```python
_UPSTREAM_EXAMPLE_RULE_IDS = {"example_static"}
# ... used in _merged_rules():
for rule in load_builtin_rules():
    if rule.id in _UPSTREAM_EXAMPLE_RULE_IDS:
        continue
    merged[rule.id] = rule
```

Plus a smoke test (`tests/unit/test_smoke.py:test_upstream_example_rule_is_not_loaded`) that keeps the filter honest.

#### Proposed fix

Move `example_static.yaml` out of the production `ndl/builtin_rules/` package and into `tests/fixtures/` (or a separate `ndl-storykit-examples` package). Document that `load_builtin_rules()` is the production builtin-rules entry point and returns nothing in the default install.

If you want to keep an example for documentation purposes, ship it as a string constant or in a docs-only location — not in the importable rules package.

#### Acceptance criteria

1. `load_builtin_rules()` on a fresh install returns `[]` (or at least zero rules with `id == "example_static"`).
2. Tests that previously relied on `example_static` (search/download smoke tests in upstream) migrate to load the rule from the new location.
3. Downstream `_UPSTREAM_EXAMPLE_RULE_IDS` and the corresponding test become redundant.

---

### H2. Document which schema fields are actually consumed by services

**Severity:** Low
**Effort:** S (docs only)
**Component:** `docs/rule-authoring/` (or wherever `ndl-storykit` documents its YAML schema)

#### Problem

Today, `index.pagination.type` accepts `"next"` but the service ignores it. `download_archive` doesn't exist yet. Discovering which fields are inert vs. consumed requires reading the service source.

#### Proposed fix

Add a "Consumed by" column to the rule-authoring docs for every schema field, listing the upstream version that introduced consumption. Example:

| Field | Schema since | Consumed since |
|---|---|---|
| `index.pagination.type: "next"` | 0.1 | 0.2 (this release) |
| `index.pagination.type: "index-template"` | 0.2 | 0.2 |
| `chapter.pagination.type: "next"` | 0.1 | 0.2 |
| `download_archive` | 0.2 | 0.2 |
| `search.method: "POST"` | 0.2 | 0.2 |
| `search.browser` | 0.2 | 0.2 |

Optional: have the rule loader log a warning if a YAML rule sets a field whose `Consumed since` is greater than the installed version.

#### Acceptance criteria

1. The doc table is present and accurate as of 0.2.
2. A rule that sets a not-yet-consumed field gets at least a deprecation-style warning at load time, not a silent no-op.

---

## I — Selector enrichment

### I1. `pick:` modifier on `ChapterListRule.container`

Covered above as **B5**. Listed here as its own track item because it's independent of all other tracks and a one-day fix.

---

## Test plan: verifying the downstream collapses

When all of tracks A through E land, the downstream `ndl-desktop` should be able to:

1. Delete `src/ndl_desktop/services/upstream_patches.py` (and the `import` in `services/__init__.py`).
2. Delete `src/ndl_desktop/services/x23zw_download.py`, `x23zw_update.py`, `qishuxia_download.py`, `qishuxia_update.py`, `update_common.py`.
3. Simplify `src/ndl_desktop/services/container.py` — `download()` reduces to `return await self._upstream.download(url, progress=progress)`, `update_novel()` reduces to a thin wrapper over `self._upstream.update_service().update_novel(novel_id)` with the desktop's `UpdateOutcome` adapter, `search()` reduces to `return await self._upstream.search_service().search(keyword)`.
4. Rewrite `src/ndl_desktop/builtin_rules/x23zw.yaml` to use:
   - `index.pagination.type: index-template` with `template: "{source_url}index_{page}.html"`, OR
   - `index.pagination.type: next` with `next.selector: "a.btn-mulu"`
   - `chapter.pagination.type: next` with `next.selector: "div.word_read .read_btn a:contains('下一')"`
   - `chapter_list.pick: largest`
5. Rewrite `src/ndl_desktop/builtin_rules/qishuxia.yaml` to use:
   - `search.browser` block for the home-page form search
   - `download_archive` block with `trigger: selector`, `selector: "a[href*='txtarticle.php']"`
6. All `tests/unit/test_*_download.py`, `test_*_update.py`, `test_*_search.py` for x23zw and qishuxia can be deleted (they're testing the now-unnecessary adapters); the contract tests in `tests/contract/test_x23zw_rule.py` should continue to pass because they test the YAML rule against saved HTML fixtures.

If the downstream cannot complete this collapse, an item in tracks A–E was either not landed or landed differently than spec'd — file an issue back to upstream noting which downstream file you couldn't delete and why.

---

## Appendix: downstream files inventoried

Workaround files in `ndl-desktop` that exist solely because of upstream gaps:

| Downstream file | Lines | Upstream gap |
|---|---:|---|
| `src/ndl_desktop/services/upstream_patches.py` | 104 | A1, A2 |
| `src/ndl_desktop/services/x23zw_search.py` | 91 | B1, D1 |
| `src/ndl_desktop/services/x23zw_download.py` | 422 | B3, B5, C1, C2 |
| `src/ndl_desktop/services/qishuxia_search.py` | 131 | B2, D2 |
| `src/ndl_desktop/services/qishuxia_download.py` | 260 | B4, C3 |
| `src/ndl_desktop/services/x23zw_update.py` | 52 | E1 |
| `src/ndl_desktop/services/qishuxia_update.py` | 46 | E1 |
| `src/ndl_desktop/services/update_common.py` | 62 | E1 |
| `src/ndl_desktop/services/txt_import.py` | 88 | F1, F2 (partially) |
| `src/ndl_desktop/services/styled_epub_writer.py` | 273 | G1 |
| Filter in `services/container.py:_UPSTREAM_EXAMPLE_RULE_IDS` | 3 | H1 |
| Dedupe in `services/container.py:_dedupe_search_results` | 11 | D3 |
| **Total addressable** | **~1,540** | |

That's the maximum collapse if every item in this document lands. A realistic 0.2 ship targeting tracks A–E captures ~1,200 of those lines.

---

## How to file follow-ups

If implementing any item surfaces a finer issue, file a GitHub issue on `ndl-storykit` referencing this document section (e.g., "Tracking 2026-05-23 doc, item C2"). When in doubt about a design choice (e.g., "should `pick: largest` break ties by document order or alphabetically?"), prefer matching what `ndl-desktop`'s current adapter does so the downstream collapse stays mechanical.
