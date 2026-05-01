# NDL — NOVELDOWNLOADER 设计文档

| 字段 | 值 |
|---|---|
| 项目名 | NOVELDOWNLOADER |
| 缩写 | NDL |
| 仓库 | `github.com/makunxiang-cmd/project_noveldownloader` |
| Python 包名 | `ndl` |
| 文档日期 | 2026-04-20 |
| 文档状态 | 待审核（Draft）|
| License | MIT |
| 设计文档版本 | 1.0 |

> Implementation status, 2026-04-30: P0 and P1 download/convert MVP are implemented. P2 library persistence is the active next milestone. For current handoff state, read `docs/superpowers/SESSION-STATE.md`.

---

## 0. 执行摘要

NDL 是一个以 **Python 3.10+** 为基础的**中文小说下载与格式转换工具**，采用 **CLI + 本地 Web UI** 双交互模式，通过**规则驱动的插件化架构**支持任意站点适配。输出格式覆盖 **TXT 与 EPUB**，具备**本地书库管理**、**追更（增量更新）**、**多源搜索**等能力。

项目定位为 **MIT 开源项目**，优先考虑社区贡献友好度、法律与伦理合规、以及跨平台（Windows / macOS / Linux）一致性。

**非目标**（刻意排除）：
- 不提供对需要账号登录 / 付费章节 / DRM 保护内容的支持
- 不内置 Cloudflare 绕过 / 账号注册 / 签到等"灰色工具集"
- 不追求"全格式支持"（PDF / MOBI / AZW3 等交给社区后续 PR，以 EPUB 为 MVP 黄金格式）

---

## 1. 架构决策总账（ADR 精简版）

| # | 维度 | 决策 | 理由摘要 |
|---|------|------|---------|
| 1 | 交互方式 | CLI + 本地 Web UI | 兼顾终端用户与非技术用户；Web UI 跨设备访问 |
| 2 | 目标站点 | 纯规则驱动（YAML），不硬编码任何站点 | 开源可持续：社区零代码贡献新源 |
| 3 | 输出格式 | TXT + EPUB；`ndl convert` 独立子命令 | 中文电子书事实标准；PDF/MOBI 后续 PR |
| 4 | JavaScript 渲染 | HTTP 默认；Playwright 作为 `ndl[browser]` 可选 extras | 降低首装门槛，保留高级能力 |
| 5 | 状态管理 | SQLite + 追更功能，`platformdirs` 规范路径 | Web UI 前提；连载小说刚需 |
| 6a | Web 前端 | HTMX + Jinja2 + SSE | 纯 Python 栈，零 Node.js 构建 |
| 6b | 追更触发 | APScheduler 随 `ndl serve` 运行 + 手动 `ndl update` | 无守护进程负担 |
| 7a | 规则分发 | 三级加载：打包内置 + 远程仓库 + 用户自定义 | 即装可用 + 可升级 + 可私有 |
| 7b | 法律伦理 | 免责声明 + robots.txt 默认尊重 + 强制限速 | 开源爬虫项目社会契约 |
| 8a | Python 版本 | 3.10+ | `match` 语法在规则解析中使用 |
| 8b | 国际化 | 中英双语（babel） | 触达海外华人与国际用户 |
| 8c | 发布形态 | MVP 仅 PyPI；v1.0 加 Docker | 先跑起来再扩展 |
| 9 | 代码组织 | 分层 src-layout（方案 B） | 2025 年 Python 开源事实标准 |
| 10 | License | MIT | 爬虫工具最合理的许可形式 |

---

## 2. 架构总览

### 2.1 洋葱型分层

> 实现说明：实际代码采用扁平 src-layout，**不引入** `infrastructure/` 子目录层级 ——
> `fetchers/` / `parsers/` / `converters/` / `storage/` / `scheduler/` / `rules/`
> 直接位于 `src/ndl/` 之下。下图按"职责层"而非物理目录组织，扁平实现的取舍记录在
> `docs/adr/0001-architecture-and-deps.md`。

```
 ┌──────────────────────────────────────────────────┐
 │  cli/        web/                                │  交付层
 │  (Typer)     (FastAPI+HTMX+SSE)                  │
 ├──────────────────────────────────────────────────┤
 │  application/  services: Download | Convert      │  用例层
 │                          | Update | Library      │
 │                          | Search | Rules        │
 ├──────────────────────────────────────────────────┤
 │  fetchers/ {http, browser*}                      │  基础设施层（扁平）
 │  parsers/  {html_index, html_chapter, txt}       │
 │  converters/ {txt_writer, epub_writer}           │
 │  storage/  {SQLAlchemy 2.0 + Repository}         │
 │  scheduler/ {APScheduler AsyncIO}                │
 │  rules/    {YAML loader, schema, resolver}       │
 ├──────────────────────────────────────────────────┤
 │  core/   Novel, Chapter, SourceRule, errors      │  领域层
 │          Protocol: Fetcher, Parser, Writer       │
 └──────────────────────────────────────────────────┘
       * browser = 可选 extras，HTTP 为默认
```

### 2.2 依赖规则（代码评审强制执行）

- `core/` 不 import 本项目任何其它模块，仅依赖 stdlib + pydantic
- 基础设施模块（`fetchers/` / `parsers/` / `converters/` / `storage/` / `scheduler/` / `rules/`）相互独立，仅依赖 `core/`
- `application/` 通过 `core/` 定义的 `Protocol` 接口消费基础设施（依赖倒置）
- 交付层（`cli/` 与 `web/`）位于最外层，可 import 任何层，但不被任何层 import

### 2.3 横切关注点

| 关注点 | 实现位置 | 说明 |
|---|---|---|
| 结构化日志 | `src/ndl/logging.py` (structlog) | JSON 输出，issue 反馈友好 |
| 配置 | `src/ndl/config/` (pydantic-settings) | 合并顺序：默认值 → TOML → env → CLI 参数 |
| 国际化 | `src/ndl/i18n/locale/{zh_CN,en_US}/LC_MESSAGES/ndl.po` | babel + gettext |
| 路径 | `src/ndl/config/paths.py` (platformdirs) | 跨平台用户目录封装 |

### 2.4 技术选型一览

| 关注点 | 选择 | 理由 |
|---|---|---|
| 运行时 | Python 3.10+ | `match` 语法、更好的类型注解 |
| HTTP 客户端 | `httpx[http2]` | async 原生；HTTP/2 提升吞吐 |
| 浏览器（可选） | `playwright` | 比 selenium 快；官方维护 |
| HTML 解析 | `selectolax`（主）+ `lxml`（fallback）| 速度优先，lxml 作宽容 fallback |
| 数据建模 | `pydantic v2` | 规则 Schema + FastAPI 原生 |
| ORM | `SQLAlchemy 2.0` Mapped 风格 | 类型注解友好 |
| CLI 框架 | `typer` | 装饰器式；类型驱动 |
| Web 框架 | `fastapi` + `jinja2` + `htmx` + `sse-starlette` | 零 JS 构建链 |
| 任务调度 | `apscheduler` AsyncIOScheduler | 与 FastAPI loop 共享 |
| EPUB 生成 | `ebooklib` | 最成熟的纯 Python EPUB 库 |
| 包管理 | `uv`（推荐）+ `hatchling` 后端 | 2025 年 Python 工具链首选 |
| 测试 | `pytest` + `pytest-asyncio` + `respx` | 无 `unittest` |
| 代码质量 | `ruff`（lint+format）+ `mypy --strict` | 事实标准 |
| 文档 | `mkdocs-material` | 最佳开源文档体验 |
| 重试 | `tenacity` | 声明式重试策略 |
| 限速 | `aiolimiter` | async 原生令牌桶 |
| robots.txt | `protego` | Google 参考实现的 Python 版 |

---

## 3. 核心领域模型与规则引擎

### 3.1 数据模型（`src/ndl/core/models.py`）

```python
class Chapter(BaseModel):
    index: int                           # 在小说中的顺序，0-based
    title: str
    content: str                         # 纯文本正文，段落以 \n\n 分隔
    source_url: str | None = None
    word_count: int = 0
    published_at: datetime | None = None

class Novel(BaseModel):
    title: str
    author: str
    source_url: str                      # 目录页 URL
    source_rule_id: str                  # 所用规则 id（如 "biquge"）
    summary: str | None = None
    cover_url: str | None = None
    cover_data: bytes | None = None      # 可选嵌入封面二进制
    tags: list[str] = []
    status: Literal["ongoing", "completed", "unknown"] = "unknown"
    chapters: list[Chapter] = []
    fetched_at: datetime
    last_updated: datetime | None = None
```

**设计原则**：`Novel` 是整本书在内存中的**唯一中间表示**。下载、读 TXT、读 DB、写 EPUB，全部以 `Novel` 为枢纽。格式之间不直接互转。

### 3.2 规则 Schema（`src/ndl/rules/schema.py`）

YAML 文件通过 pydantic 校验为 `SourceRule`。包含 5 部分：

| 部分 | 关键字段 |
|---|---|
| **identity** | `id`, `name`, `version`, `author`, `enabled`, `priority` |
| **matching** | `url_patterns: [{pattern, type: regex\|glob}]` |
| **fetcher** | `type: http\|browser`; `headers`; `rate_limit.{min_interval_ms, max_concurrency}`; `retry.{attempts, backoff}`; `robots.{respect, ignore_justification}`; `encoding: utf-8\|gbk\|gb18030\|auto` |
| **index** | 目录页：`url_template`, `novel.{title, author, summary, cover, status}`, `chapter_list.{container, items, title, url}`, `pagination` |
| **chapter** | 章节页：`title`, `content.{selector, attr, clean.*}`, `pagination.{type, next, terminator}` |
| **search**（可选） | `url_template`, `results_container`, `items`, `fields.{title, author, url}` |

### 3.3 选择器 DSL

每个"字段提取"均为 `Selector` 对象：

```yaml
title:
  selector: "#info > h1"    # CSS 选择器；"self" 指当前节点
  attr: text                # text | html | href | src | <任意属性名>
  regex: "作[\\s　]*者[：:]\\s*(.+)"   # 可选：后处理正则
  regex_group: 1
  strip: true
  default: "未知"           # 未匹配时的 fallback
  multiple: false           # true 返回列表
  map:                      # 可选：字符串映射
    连载中: ongoing
    完本: completed
```

内容清洗独立命名空间（仅正文用）：

```yaml
chapter:
  content:
    selector: "#content"
    attr: html
    clean:
      remove_selectors: [".ad", "script", "style", ".copyright"]
      strip_patterns: ["笔趣阁首发.*", "天才一秒记住.*"]
      normalize_whitespace: true
      min_paragraph_length: 2
```

**分离结构与清洗的意义**：结构选择器（标题在哪）罕有失效；清洗模式（广告关键字）经常更新。分离后用户仅修 `strip_patterns` 而不碰整份规则。

### 3.4 规则三级加载优先级

```
src/ndl/builtin_rules/*.yaml          (打包内置，示例/样板)
     ↓
~/.ndl/rules/*.yaml                   (`ndl rules update` 拉取的远程规则)
     ↓
~/.ndl/rules/custom/*.yaml            (用户手写；不受远程更新覆盖)
```

同 `id` 高优先级覆盖低优先级。用户无需 fork 官方仓库即可"打补丁"。

### 3.5 规则引擎执行流（下载场景）

```
RuleResolver.resolve(url)            → SourceRule
         ↓
FetcherFactory.for(rule.fetcher)     → Fetcher 实例（http 或 browser）
         ↓
Fetcher.get(index_url)               → HTML（含节流/重试/robots 检查）
         ↓
IndexParser.parse(html, rule.index)  → Novel 元数据 + 章节 stubs
         ↓ （翻页循环直至尾页）
         ↓
for stub in stubs:                   → 按 rate_limit.max_concurrency 并发
    Fetcher.get(stub.url)
    ChapterParser.parse(html, rule.chapter)  → 清洗 + 拼接正文
    （若正文分页，内循环 fetch）
    yield Chapter(...)
         ↓
Novel(chapters=[...])                → 组装完整对象返回
```

---

## 4. 应用服务与端到端数据流

### 4.1 服务清单

| 服务类 | 核心方法 | 消费者 |
|---|---|---|
| `DownloadService` | `download(url, progress_cb) -> Novel` | CLI `ndl download`, Web `POST /downloads` |
| `SearchService` | `search(keyword, rule_ids=None) -> list[SearchResult]` | CLI `ndl search`, Web `GET /search` |
| `ConvertService` | `convert(input, target_format, output_path, opts) -> Path` | CLI `ndl convert`, Web 导出按钮 |
| `UpdateService` | `update_novel(id)`, `update_all()` | CLI `ndl update`, APScheduler, Web 按钮 |
| `LibraryService` | `list`, `get`, `remove`, `export_all` | CLI `ndl library`, Web 首页 |
| `RulesService` | `load`, `update_remote`, `validate(yaml_path)` | CLI `ndl rules *`, Web 规则管理页 |

所有服务经 `src/ndl/application/container.py` 的 `AppContainer` 组装（手写轻量 DI）。FastAPI 和 Typer 共享同一容器。

### 4.2 进度事件（SSE + CLI 共用模型）

```python
class ProgressEvent(BaseModel):
    kind: Literal["stage", "chapter", "done", "error"]
    stage: str | None = None
      # "resolving_rule" | "fetching_index" | "fetching_chapters"
      # | "saving" | "converting"
    total: int | None = None
    done: int | None = None
    current_title: str | None = None
    message: str | None = None
    timestamp: datetime

ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]
```

服务方法接受 `progress_cb`；CLI 传入"渲染 `rich.progress`"的回调，Web 传入"推送到 SSE 通道"的回调。**服务本身不知事件最终去哪里**——这是核心解耦。

### 4.3 三大数据流

#### 4.3.1 下载流

```
User → CLI/Web → DownloadService.download(url, cb)
 → RuleResolver.resolve(url) → SourceRule
 → cb(stage="fetching_index")
 → Fetcher.get(url) [RateLimiter + RobotsChecker + Retry]
 → IndexParser.parse(html) → Novel + [ChapterStub]
 → cb(stage="fetching_chapters", total=N)
 → asyncio.gather(fetch_and_parse_chapter(s, rule) for s in stubs)
     [每完成一章 cb(kind="chapter", done=i)]
 → cb(stage="saving")
 → LibraryRepo.save_novel(novel)  [单次 SQL 事务原子写入]
 → cb(kind="done")
 → return Novel
```

**部分失败语义**（明确约束）：

- **SQL 事务性**：`save_novel` 本身是单次 SQL 事务，要么整本入库，要么回滚——防止数据库半吞咽。
- **章节级容错**：单个章节抓取失败**不触发回滚**，而是记入 `download_jobs.progress.failed_chapters` JSON 字段；主流程继续。`Novel` 的**出版状态** (`ongoing/completed/unknown`) 与下载完成度是正交维度——下载完成度由 `download_jobs.status` 单独追踪，取值 `succeeded / incomplete / failed`。
- **全量失败**：若目录页抓取失败或成功章节为 0，`save_novel` 不被调用，`download_jobs.status = failed`，无 Novel 持久化。
- **补下**：`ndl retry-failed <novel_id>` 读取 `failed_chapters` 列表，仅对这些章节重跑 `Fetcher + ChapterParser`，成功后 `append_chapters` 合并入库；`failed_chapters` 更新。

#### 4.3.2 追更流

```
Trigger (CLI / Scheduler / Web) → UpdateService.update_all()
 → for novel in library.list_novels(status != "completed"):
      RuleResolver.resolve(novel.source_url)
      Fetcher.get(novel.source_url) → 最新目录 HTML
      IndexParser.parse() → [ChapterStub]（全量最新）
      new_stubs = [s for s in latest if s.index not in stored_indices]
      若 new_stubs 为空 → skip
      fetch_chapters(new_stubs) → [Chapter]
      LibraryRepo.append_chapters(novel.id, new)
      yield UpdateResult(novel_id, new_count)
```

APScheduler 触发在 `ndl serve` 启动时注册（默认 6 小时一次，可配置）。CLI 手动触发调用**完全相同**的 `UpdateService.update_all()`。

#### 4.3.3 转换流

```
Input (Path 或 NovelID) → ConvertService.convert(...)
 → 若 NovelID → LibraryRepo.get_novel(id) → Novel
 → 若 Path：
    - .txt  → TxtReader.read(path)   [正则识别章节标题] → Novel
    - .epub → EpubReader.read(path)  → Novel
    - .json → JsonReader.read(path)  → Novel (NDL 备份格式)
 → Novel (统一 IR)
 → Writer = WriterRegistry.get(target_format)
 → Writer.write(novel, output_path, opts)
 → return output_path
```

TXT 反向解析支持 15+ 种中文章节标题变体：`第X章` / `第X回` / `第X节` / `楔子` / `序章` / `序幕` / `引子` / `终章` / `尾声` / `后记` / `番外` / `外传` / `卷X` / `Chapter X` 等。识别规则存 `~/.ndl/config.toml`，可扩展。

### 4.4 存储模型（`src/ndl/infrastructure/storage/models.py`）

SQLAlchemy 2.0 `Mapped` 风格。

| 表 | 主要字段 | 用途 |
|---|---|---|
| `novels` | id, title, author, source_url, source_rule_id, cover_blob, summary, tags (JSON), status, fetched_at, last_updated | 主表 |
| `chapters` | id, novel_id (FK), index, title, content (TEXT), source_url, word_count, published_at, fetched_at | 每章一行 |
| `download_jobs` | id, novel_id, status (`running\|succeeded\|incomplete\|failed`), started_at, finished_at, error, progress (JSON 含 failed_chapters 列表) | 任务历史 + 失败续传 |
| `settings` | key, value (JSON) | 通用 KV |

**SQLite PRAGMA**：`journal_mode=WAL`（支持并发读 + 单写）、`foreign_keys=ON`。

**Repository 模式**：ORM 隐藏在 `LibraryRepository` 后；服务层仅见领域对象 `Novel`/`Chapter`。

---

## 5. 错误处理

### 5.1 错误层次（`src/ndl/core/errors.py`）

```
NDLError (base)
├── UserError                    # 退出码 2，不上报为 bug
│   ├── InvalidURLError
│   └── InvalidArgumentError
├── ConfigError                  # 退出码 78 (EX_CONFIG)
├── RuleError
│   ├── RuleNotFoundError        # URL 无匹配规则
│   ├── RuleValidationError      # YAML schema 错
│   └── RuleLoadError
├── FetchError                   # 退出码 69 (EX_UNAVAILABLE)
│   ├── HTTPError                # 非 2xx 重试耗尽
│   ├── RobotsBlockedError       # robots.txt 禁止
│   ├── RateLimitedError         # 429
│   ├── NetworkError             # DNS/timeout
│   └── BrowserError
├── ParseError
│   ├── SelectorNotFoundError
│   └── EmptyContentError
├── StorageError
└── ConvertError
```

所有异常必含 `.user_message(lang)` 与 `.exit_code`。

### 5.2 重试策略

| 错误类型 | 策略 |
|---|---|
| 网络临时错误（connect timeout / DNS / 5xx） | 指数退避，默认 3 次（规则 `fetcher.retry` 可覆盖） |
| HTTP 429 | 尊重 `Retry-After` header，上限 60 秒；后续继续指数退避 |
| 选择器未找到 | 不重试——规则问题 |
| robots.txt 禁止 | 不重试——立即失败，给建议 |
| 章节级失败 | 记入 `download_jobs.progress.failed_chapters`；`ndl retry-failed` 单独补 |

### 5.3 用户可见错误模板

CLI 仿 `rustc` 风格：

```
✗ 下载失败：没有匹配到任何规则 (RuleNotFoundError)

  URL:  https://example.com/book/123

  可能原因：
  - 该站点还没有对应的规则文件
  - 你的规则库可能过期，试试 `ndl rules update`

  快速排查：
  $ ndl rules list                  # 查看已加载规则
  $ ndl rules validate <your.yaml>  # 编写自定义规则

  如果这是常用站点，欢迎在 GitHub 提交规则 PR：
  https://github.com/makunxiang-cmd/project_noveldownloader
```

Web UI 使用 `web/templates/partials/error_card.html`，结构字段与 CLI 一致。

---

## 6. 测试策略

### 6.1 四层测试金字塔

```
 ┌─────────────────┐
 │  E2E (CLI+Web)  │   ~5%   真实子进程 / HTTP client
 ├─────────────────┤
 │    Contract     │   ~10%  规则契约测试（每条规则 vs fixture）
 ├─────────────────┤
 │   Integration   │   ~25%  SQLite + respx mock
 ├─────────────────┤
 │      Unit       │   ~60%  纯内存，微秒级
 └─────────────────┘
```

| 层 | 工具 | 覆盖对象 |
|---|---|---|
| Unit | `pytest` + `pytest-asyncio` | 规则 Schema 校验、Selector DSL、TXT 反向解析器、EPUB 结构、服务类（注入 mock） |
| Integration | `pytest` + `respx` + 内存 SQLite | Fetcher 对假服务器、LibraryRepository 对真 DB、下载服务端到端（fixture→Novel→DB） |
| Contract | `pytest` 参数化 | 每条**内置规则**对应 `tests/contract/fixtures/<rule_id>/{index.html, chapter.html, expected.json}`；单测试模板循环全部规则 |
| E2E | `typer.testing.CliRunner`, `fastapi.testclient.TestClient` | CLI 子进程、Web HTTP 路由 |

### 6.2 红线：测试不得访问真实站点

**任何自动化测试不得访问真实小说网站**。所有网络交互用 `respx` mock 或本地 HTML fixture。

### 6.3 规则契约测试

对每条内置规则（及用户提交 PR 的规则），CI 要求：

- `tests/contract/fixtures/<rule_id>/index.html`（目录页截图）
- `tests/contract/fixtures/<rule_id>/chapter.html`（章节页截图）
- `tests/contract/fixtures/<rule_id>/expected.json`（应解析出的 Novel 结构）

`test_rule_contract.py` 参数化运行所有规则，规则失效则 CI 变红。

### 6.4 CI 质量门禁（`.github/workflows/ci.yml`）

| 检查 | 工具 | 阻断合并 |
|---|---|:---:|
| Lint | `ruff check` | ✓ |
| Format | `ruff format --check` | ✓ |
| Type | `mypy --strict src/ndl` | ✓ |
| Test | `pytest` 在 Python 3.10/3.11/3.12 × ubuntu/windows/macos | ✓ |
| Coverage | `coverage report --fail-under=80`（`core/`、`rules/`、`converters/` 要求 90%+） | ✓ |
| Rule lint | 自定义脚本：`rate_limit.min_interval_ms >= 500`；`ignore_robots: true` 必须伴随 `ignore_justification` 字段 | ✓ |

---

## 7. 项目目录骨架

```
project_noveldownloader/
├── .github/
│   ├── workflows/              # ci.yml, release.yml, rules-sync.yml
│   ├── ISSUE_TEMPLATE/         # bug_report / rule_request / feature_request
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── mkdocs.yml
│   ├── superpowers/specs/      # 本设计文档存此
│   ├── user-guide/             # installation, cli, web-ui, configuration
│   ├── rule-authoring/         # writing-your-first-rule, selector-dsl-reference
│   └── developer/              # architecture, contributing, rule-contract-tests
├── src/ndl/
│   ├── __init__.py             # __version__
│   ├── __main__.py             # python -m ndl 入口
│   ├── core/                   # models, progress, protocols, errors
│   ├── rules/                  # schema, loader, resolver, selector, remote, validator
│   ├── fetchers/               # base, http, browser*, rate_limiter, robots, factory
│   ├── parsers/                # html_index, html_chapter, txt_reader
│   ├── converters/             # base, txt_writer, epub_writer, registry
│   ├── storage/
│   │   ├── database.py, models.py, repository.py
│   │   └── migrations/         # alembic
│   ├── scheduler/              # update_job.py (APScheduler)
│   ├── application/
│   │   ├── container.py        # 手写 DI
│   │   └── services/           # download, search, convert, update, library, rules
│   ├── config/                 # schema (pydantic-settings), paths (platformdirs), defaults.toml
│   ├── cli/
│   │   ├── main.py
│   │   ├── commands/           # download, search, convert, update, library, rules, serve
│   │   ├── renderers.py        # rich.progress → ProgressCallback
│   │   └── disclaimer.py       # 首次运行免责声明
│   ├── web/
│   │   ├── app.py              # FastAPI + lifespan
│   │   ├── routes/             # pages, downloads, library, rules, sse
│   │   ├── templates/          # Jinja2 + partials/
│   │   └── static/             # css, js/htmx.min.js, favicon
│   ├── i18n/locale/            # zh_CN, en_US .po 文件
│   ├── logging.py              # structlog 配置
│   └── builtin_rules/          # example_static.yaml, example_browser.yaml
├── tests/
│   ├── conftest.py
│   ├── unit/                   # 镜像 src/ndl/ 结构
│   ├── integration/            # storage, fetchers, flows
│   ├── contract/               # fixtures/<rule_id>/ + test_rule_contract.py
│   ├── e2e/                    # cli/, web/
│   └── fixtures/               # 共享 HTML 样本
├── .pre-commit-config.yaml
├── .gitignore
├── .editorconfig
├── pyproject.toml              # PEP 621 + optional-dependencies[browser,dev,docs]
├── uv.lock
├── README.md                   # 英文主版
├── README.zh-CN.md             # 中文版
├── LICENSE                     # MIT
├── CHANGELOG.md                # keep-a-changelog
├── CONTRIBUTING.md             # 贡献指南
├── CODE_OF_CONDUCT.md          # Contributor Covenant
├── DISCLAIMER.md               # 法律免责 + 伦理守则
└── SECURITY.md                 # 漏洞报告渠道
```

---

## 8. 依赖清单

> **状态说明（2026-04-30）**：§8.1 是 **v1.0 目标**清单，包含搜索 / 远程规则 / 追更 / Web /
> i18n 等多阶段工作所需的库。**P1 实际生效的依赖远少于此**，按 P 阶段逐步引入：
>
> - **P1 已落地（runtime）**：`typer`, `rich`, `pydantic`, `pyyaml`, `selectolax`, `httpx`, `ebooklib`
> - **P1 已落地（dev）**：`mypy`, `pre-commit`, `pytest`, `pytest-asyncio`, `pytest-cov`, `respx`, `ruff`, `types-pyyaml`
> - **P1 已落地（docs）**：`mkdocs`, `mkdocs-material`
> - **P2 计划引入**：`SQLAlchemy>=2`（书库持久化）；`platformdirs`（跨平台路径）酌情同步
> - **P3+ 计划引入**：`fastapi`, `uvicorn`, `jinja2`, `sse-starlette`（Web UI）
> - **P4 计划引入**：`apscheduler`（追更调度）
> - **P5 计划引入**：`structlog`, `babel`（结构化日志 + i18n）
> - **P6 计划引入**：`playwright`（可选 extras）
>
> 以下清单按"加入时机"在 §9 路线图行内重申。新增任何依赖必须在对应 P 阶段 plan 中显式批准。

### 8.1 `pyproject.toml` 核心部分

```toml
[project]
name = "ndl"
version = "0.1.0"
requires-python = ">=3.10"
description = "NOVELDOWNLOADER: 规则驱动的中文小说下载与格式转换工具"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "makunxiang-cmd" }]

dependencies = [
  # 领域 + 校验
  "pydantic>=2.5",
  "pydantic-settings>=2.1",
  # HTTP 栈
  "httpx[http2]>=0.27",
  "tenacity>=8.2",
  "aiolimiter>=1.1",
  "protego>=0.3",
  # HTML 解析
  "selectolax>=0.3.17",
  "lxml>=5.0",
  # 规则/配置
  "PyYAML>=6.0",
  # 存储
  "SQLAlchemy>=2.0",
  "aiosqlite>=0.19",
  "alembic>=1.13",
  # CLI/Web
  "typer>=0.12",
  "rich>=13.7",
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "jinja2>=3.1",
  "sse-starlette>=2.0",
  "apscheduler>=3.10",
  # 转换
  "ebooklib>=0.18",
  # 横切
  "structlog>=24.1",
  "platformdirs>=4.2",
  "babel>=2.14",
]

[project.optional-dependencies]
browser = ["playwright>=1.40"]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pytest-cov>=4.1",
  "respx>=0.20",
  "freezegun>=1.4",
  "ruff>=0.3",
  "mypy>=1.8",
  "types-PyYAML",
  "types-protego",
  "pre-commit>=3.6",
]
docs = [
  "mkdocs>=1.5",
  "mkdocs-material>=9.5",
  "mkdocstrings[python]>=0.24",
]

[project.scripts]
ndl = "ndl.cli.main:app"

[project.urls]
Homepage = "https://github.com/makunxiang-cmd/project_noveldownloader"
Repository = "https://github.com/makunxiang-cmd/project_noveldownloader"
Issues = "https://github.com/makunxiang-cmd/project_noveldownloader/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 8.2 前端静态资源

`htmx.min.js`（约 14 KB）直接提交到 `src/ndl/web/static/js/`，不走 npm。固定版本写入 README 便于审计。

---

## 9. 分期路线图

| Phase | 范围 | 预估 | 交付判据 |
|---|---|---|---|
| **P0 脚手架** | 目录结构 + `pyproject.toml` + CI + LICENSE + 空 CLI | 1-2 天 | `ndl --version` 工作；CI 全绿 |
| **P1 MVP：下载 + 转换** | `core` / `rules` / `fetchers(http)` / `parsers` / `converters` / `services(download+convert)` / `cli(download+convert)` + 合规 fixture 内置规则 + 契约测试 | 已完成 | `ndl download <url> -o book.epub` 端到端工作 |
| **P2 书库持久化** | `storage` / `services(library)` / `cli(library)` | 1 周 | 下载自动入库；`ndl library {list,show,remove}` |
| **P3 Web UI** | `web` / Jinja2 + HTMX + SSE / `ndl serve` | 1-2 周 | `localhost:8000` 可用 |
| **P4 追更** | `scheduler` / `services(update)` / CLI+Web 触发入口 | 1 周 | APScheduler 定时 + 手动双通道 |
| **P5 搜索 + 远程规则** | `services(search)` / `rules/remote` / CLI 新命令 | 1 周 | `ndl search "关键词"` / `ndl rules update` |
| **P6 浏览器 Fetcher + 发布** | `fetchers/browser` / 英文 locale / 文档站完善 / PyPI v0.1 | 1-2 周 | `pip install ndl[browser]` |
| **P7 v1.0** | Docker 镜像 / 更多内置规则 / UX 打磨 / 批量导出 | 持续 | Docker Hub + v1.0 tag |

**总计 MVP→PyPI 发布约 6-10 周**（兼职节奏，每日 1-2 小时）。

### 9.1 MVP (v0.1) vs v1.0 能力对照

| 功能 | MVP (v0.1) | v1.0 |
|---|:---:|:---:|
| CLI `download` / `convert` | ✓ | ✓ |
| 书库 SQLite 持久化 | ✓ | ✓ |
| Web UI (基础) | ✓ | ✓ |
| HTTP Fetcher | ✓ | ✓ |
| 内置规则示例 | 2 条 | 5+ 条 |
| Browser Fetcher | ✗ | ✓ (extras) |
| 追更（手动+定时） | ✗ | ✓ |
| 搜索（多源聚合） | ✗ | ✓ |
| 远程规则更新 | ✗ | ✓ |
| i18n 中英双语 | 中 | 中+英 |
| Docker 镜像 | ✗ | ✓ |
| PyPI 发布 | ✓ | ✓ |

---

## 10. 关键风险与缓解

| # | 风险 | 缓解策略 |
|---|---|---|
| 1 | **规则腐蚀**：小说站改版致规则失效 | 契约测试 + `.github/workflows/rules-sync.yml` 每周健康检查；社区 PR 主导更新 |
| 2 | **法律风险**：用户下载商业正版内容 | `DISCLAIMER.md` + 首运行强制确认 + **不内置**起点/番茄/晋江等正版站规则 + 无登录/账号功能 + DMCA 响应流程 |
| 3 | **反爬升级**：Cloudflare 5s 盾、JS 挑战 | Browser fetcher 基础设施就绪，但**不内置** `cloudscraper` 等主动绕过库 |
| 4 | **Playwright 安装痛**：Windows 防病毒 / 企业网络 | 可选 extras；错误提示含手动安装步骤；MVP 不依赖 |
| 5 | **SQLite 并发写**：`serve` + `update` 撞车 | `PRAGMA journal_mode=WAL`；仓储层写操作单 writer lock |
| 6 | **编码混乱**：GBK / GB18030 / UTF-8 混用 | 规则可声明 `encoding`；auto 用启发式检测 |
| 7 | **存储膨胀**：长篇网文 ≈ 50 MB | 章节存 TEXT；`ndl library compact`；"导出后仅保留元数据"模式 |
| 8 | **规则仓库供应链**：远程规则被注入 | 规则纯声明式无代码执行；`rules update` 显示 diff 需确认；v1.0 考虑签名 |
| 9 | **Windows 路径/编码**：OS 最复杂 | CI 矩阵强制 `windows-latest`；`platformdirs` 统一路径；所有 I/O 显式 `encoding="utf-8"` |

---

## 11. 法律与伦理

### 11.1 免责声明（`DISCLAIMER.md` 摘要）

- 本软件仅用于**个人学习、教育研究、本地备份公有领域或合法授权内容**
- 用户**自行承担**使用本软件的法律责任
- 本软件不破解任何 DRM、不绕过付费墙、不内置商业小说站规则
- 收到 DMCA / 版权通知将在 7 天内响应（`SECURITY.md` 列出联系渠道）

### 11.2 伦理守则（硬编码约束）

1. 默认尊重 `robots.txt`；规则若声明 `ignore_robots: true` **必须**附带 `ignore_justification` 字段且经社区 PR 审查
2. 单规则默认 `rate_limit.min_interval_ms >= 500`，`max_concurrency <= 3`
3. User-Agent 必须包含 NDL 标识与 GitHub 项目链接，便于源站识别联系
4. 不实现以下功能：登录态维持、CAPTCHA 自动识别、代理池、Cloudflare JS 挑战绕过

### 11.3 首次运行确认

首次 `ndl download` 或 `ndl serve` 展示免责声明并要求用户确认。P1 当前实现为 `ndl download --accept-disclaimer` 写入 `~/.ndl/disclaimer.accepted`；P2 引入 settings/config 时可迁移到结构化配置。CI 禁止功能变更绕过该步骤。

---

## 12. 开放问题与待决策项

本 spec 到此可进入实现阶段。后续实现过程中可能浮现的待定项：

1. **内置规则选择**：P1 MVP 附带哪 2 条示例规则？建议选**公有领域文学站**（如古籍、译言古登堡、汉典）而非盗版聚合站，作为"合规示例"
2. **规则远程仓库初始域名**：`ndl rules update` 默认指向 `github.com/makunxiang-cmd/ndl-rules`（需独立创建该仓库）
3. ~~**本地目录名 vs 仓库名不一致**~~ **已决**（2026-04-20）：本地目录 `NDL/` 将重命名为 `project_noveldownloader/` 与 GitHub 仓库对齐。重命名作为 P0 实施计划的**第一步**执行（详见实现计划）。
4. **封面图存储**：SQLite BLOB 字段 vs 文件系统 `~/.ndl/covers/<hash>.jpg`？倾向文件系统（BLOB 膨胀数据库）
5. **Web UI 访问认证**：本地 `127.0.0.1` 默认无认证；若用户 `--host 0.0.0.0` 暴露，是否强制启用 token？v1.0 考虑

---

## 13. 词汇表

| 术语 | 含义 |
|---|---|
| IR | Intermediate Representation，指 `Novel` 对象作为所有格式互转的中间表示 |
| Stub | "章节存根"，仅含标题和 URL，未下载正文的章节占位 |
| Fetcher | HTTP 或浏览器客户端的抽象，负责拿到页面 HTML |
| Parser | 将 HTML 按规则解析为领域对象 |
| Writer | 将 `Novel` 对象写入目标格式（TXT/EPUB）的输出器 |
| Reader | 反向：从文件读回 `Novel` 对象（用于 `ndl convert` 独立命令） |
| Rule | YAML 文件定义的站点适配器 |
| Contract test | 规则契约测试：固定的 HTML fixture + 期望 JSON，保证规则不因代码重构或规则编辑而静默失效 |

---

## 附录 A：示例规则文件（概念性）

```yaml
# src/ndl/builtin_rules/example_static.yaml
id: example_static
name: 公有领域静态站点示例
version: 1.0.0
author: NDL team
enabled: true
priority: 50

url_patterns:
  - pattern: '^https?://example-novels\.test/book/\d+/?$'
    type: regex

fetcher:
  type: http
  headers:
    User-Agent: "NDL/0.1 (+https://github.com/makunxiang-cmd/project_noveldownloader)"
  rate_limit:
    min_interval_ms: 800
    max_concurrency: 2
  retry:
    attempts: 3
    backoff: exponential
  robots:
    respect: true
  encoding: auto

index:
  url_template: "{source_url}"
  novel:
    title:   { selector: "h1.book-title", attr: text }
    author:  { selector: ".book-meta .author", attr: text }
    summary: { selector: ".book-intro", attr: text }
    cover:   { selector: ".book-cover img", attr: src }
    status:
      selector: ".book-meta .status"
      attr: text
      map:
        连载中: ongoing
        已完结: completed
  chapter_list:
    container: "#chapter-list"
    items: "li > a"
    title: { selector: "self", attr: text }
    url:   { selector: "self", attr: href, resolve: relative }
  pagination:
    type: none

chapter:
  title: { selector: "h1.chapter-title", attr: text }
  content:
    selector: "#chapter-content"
    attr: html
    clean:
      remove_selectors: [".ad", "script", "style"]
      strip_patterns:
        - "本章未完.*"
      normalize_whitespace: true
      min_paragraph_length: 2
  pagination:
    type: none
```

---

**设计文档结束**。实现阶段将通过 `superpowers:writing-plans` 技能生成详细的、可执行的步骤化计划。
