# NDL 项目会话状态快照

> 用途：跨会话接力的状态记录。新会话开始时，接手的 agent 应先读取本文件，再读取当前活动 plan，再决定下一步动作。
>
> 最后更新：2026-04-30（P1 MVP 完成 + 一轮全面审计修复：CLI 走容器并接 rich 进度、章节并发、429 Retry-After、UA 单一来源、Novel.source_url 可空、删私有 HTTPStatus 访问、CHANGELOG 重新分类、spec §2.1/§8.1 与扁平实现对齐、新增 CONTEXT.md + ADR-0001。下一步进入 P2.1）

---

## 0. 项目一句话描述

**NDL (NOVELDOWNLOADER)**：基于 Python 的规则驱动中文小说下载器 + 格式转换工具，MIT 开源，托管在 <https://github.com/makunxiang-cmd/project_noveldownloader>。

---

## 1. 当前进度

### 已完成

| 阶段 | 范围 | 关键产出 |
|---|---|---|
| **P0 脚手架** | `pyproject.toml` / CLI 入口 / 质量工具链 / CI 矩阵 / 社区文件 / MkDocs 骨架 | 见 `docs/superpowers/plans/2026-04-20-ndl-p0-scaffold.md` |
| **P1.1 领域 + 规则基础** | `core/`（Novel/Chapter/ChapterStub/Protocol/异常树/进度事件） + `rules/`（Pydantic schema、selector DSL、loader、resolver） + `example_static` 内置规则 + 契约 fixtures | 见 P1 plan §P1.1 |
| **P1.2 HTML 解析器** | `parsers/html_index.py` + `parsers/html_chapter.py` + `HtmlParser` 类（实现 `Parser` Protocol）；契约测试改为端到端走解析器 | 见 P1 plan §P1.2 |
| **P1.3 HTTP 抓取器** | `fetchers/http.py`（`HttpFetcher`） + `_throttle.py`（每 host 限速） + `_robots.py`（robots.txt 检查 + 缓存）；新依赖 `httpx>=0.27` 与 dev 依赖 `respx>=0.21`；`asyncio.sleep` 在测试中 monkeypatch 提速 | 见 P1 plan §P1.3 |
| **P1.4 TXT/EPUB 转换器** | `converters/txt_writer.py` + `converters/epub_writer.py` + `converters/registry.py`；`parsers/txt_reader.py` 支持 NDL TXT 与常见章节标题；新依赖 `ebooklib>=0.20` | 见 P1 plan §P1.4 |
| **P1.5 Download/Convert 服务层** | `application/services/download.py` 编排 Fetcher/Parser；`application/services/convert.py` 编排 Reader/Writer；`application/container.py` 提供轻量工厂；服务层进度回调已覆盖 | 见 P1 plan §P1.5 |
| **P1.6 CLI 命令** | `ndl download` / `ndl convert` / `ndl rules validate`；download 首跑免责声明 gate；`typer.testing` + mocked HTTP 覆盖端到端下载到 EPUB | 见 P1 plan §P1.6 |

### 当前活动 Plan

已完成计划：**`docs/superpowers/plans/2026-04-29-ndl-p1-mvp.md`** —— P1 MVP 实施计划，6 个切片：

- P1.1 ✅ implemented
- P1.2 ✅ implemented
- P1.3 ✅ implemented
- P1.4 ✅ implemented
- P1.5 ✅ implemented
- P1.6 ✅ implemented

当前待执行计划：**`docs/superpowers/plans/2026-04-30-ndl-p2-library.md`** —— P2 书库持久化计划：

- **P2.1 ⏭ next** — SQLite/SQLAlchemy 存储基础
- P2.2 ⏳ pending — LibraryRepository
- P2.3 ⏳ pending — LibraryService
- P2.4 ⏳ pending — `ndl library` CLI 命令

### 质量门当前状态

```
ruff check / format     ✅
mypy --strict (36 文件) ✅
pytest                  ✅ 72 passed
coverage                ✅ 89.27%（fail_under=80）
```

### 本轮（2026-04-30）审计修复要点

**行为层（spec ↔ 代码对齐）**

- `DownloadService` 使用 `asyncio.create_task` + `as_completed` 并发抓取章节；并发上限由 fetcher 内的 `HostThrottle` 按 rule.rate_limit.max_concurrency 强制（不再每秒只发一个请求）
- `HttpFetcher` 在 HTTP 429 时识别 `Retry-After` header（delta-seconds 或 HTTP-date），上限 60s，否则回退到 backoff
- `HttpFetcher` 现在用 `_resolve_headers()` 计算单一 headers 集合，robots 检查与实际请求使用同一个 User-Agent
- CLI `download` / `convert` 通过 `ServiceContainer.download(url, progress=...)` / `container.convert_service(progress=...)` 走容器；fetcher 生命周期由容器在 try/finally 内 aclose
- 新增 `ndl.cli.renderers.cli_progress` 异步上下文管理器，把 `ProgressEvent` 渲染为 `rich.progress`；非交互（如 CI/CliRunner）静默回退到 None

**领域层（小重构）**

- `Novel.source_url: str | None`，删除 `HttpUrl` 校验；TXT 来源不再伪造 `https://local.ndl.invalid/...`，TXT-derived Novel 的 `source_url` 默认 None
- `Chapter.word_count` 改用 `model_validator(mode="before")` 注入，不再 `object.__setattr__` 绕 frozen
- `Novel` 删 `arbitrary_types_allowed`（无依赖任意类型）
- `Fetcher` Protocol 新增 `aclose()`，让容器/测试 fetcher 共享单一生命周期约定
- `NDLError.user_message()` 删除未使用的 `lang` 参数（i18n 在 P5 重新设计）
- `core.errors.HTTPError` 用 `try HTTPStatus(code)` 替换 `_value2member_map_` 私有访问

**包/构建**

- `pyproject.toml` 把 dev deps 全部归到 `[project.optional-dependencies].dev`（含 `types-pyyaml`），删除冗余的 `[dependency-groups]`
- `parsers/__init__.py` 把仅类型用途的 import 收进 `if TYPE_CHECKING`

**文档/约定**

- `CHANGELOG.md` 把误归在 "Changed" 的 P0 加项重新放回 "Added"；新增本轮变更条目
- `docs/superpowers/specs/2026-04-20-ndl-design.md` §2.1 标注扁平 src-layout（不再实现 `infrastructure/` 目录），§8.1 增加 "P1 实际生效" 与按 P 阶段引入的清单
- 新增 `CONTEXT.md`（领域词汇表）+ `docs/adr/0001-architecture-and-deps.md`（首条 ADR：扁平布局 + 阶段化引入依赖）+ `.scratch/.gitkeep`（issue tracker 根目录）

每个切片必须保持以下命令全绿：

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```

---

## 2. 下次会话启动协议

### 接手 agent 应做的事（严格顺序）

```
1. Read docs/superpowers/SESSION-STATE.md（本文件）
2. Read docs/superpowers/plans/2026-04-30-ndl-p2-library.md（活动 plan）
3. Read AGENTS.md + docs/agents/issue-tracker.md（约定）
4. 检查仓库状态：git log --oneline -10 + git status，确认本地工作区干净
5. 确认本文件 §1 的"已完成"列表与代码实际情况一致：
   - src/ndl/core/        ✅ P1.1
   - src/ndl/rules/       ✅ P1.1
   - src/ndl/parsers/     ✅ P1.2 + P1.4 TXT reader
   - src/ndl/fetchers/    ✅ P1.3
   - src/ndl/converters/  ✅ P1.4
   - src/ndl/application/ ✅ P1.5
   - src/ndl/cli/         ✅ P1.6
6. 跑一遍质量门（见上节）确认绿；如果某项失败，先修复再推进
7. P1 已完成；下一步进入 P2.1 Storage Foundation
8. 完成新切片后：更新 CHANGELOG.md、活动 plan 的 Status 行、本文件
```

### 工程风格约定（已在前 6 阶段固化，必须延续）

- **子模块平铺**：每个职责一个 `.py`，私有 helper 用 `_xxx.py`，`__init__.py` 仅做 import re-export + `__all__`
- **薄包装类**：纯函数承担逻辑（如 `parse_index(rule, html, ...)`），Protocol 实现作为绑定 rule 的薄类（如 `HtmlParser` / `HttpFetcher`）
- **类型严格**：mypy `--strict` 必须过；`python_version = "3.10"` —— 不要用 `Self` 等 3.11+ 语法
- **`from __future__ import annotations`** 每个模块顶部都加
- **零冗余注释**：模块单行 docstring + 公开函数单行 docstring；不要 WHAT 注释
- **错误层级对齐 `core/errors.py`**：`UserError` / `RuleError` / `FetchError` / `ParseError` / `StorageError` / `ConvertError`，新错误类必须落在某个分支下
- **测试结构镜像源码**：`tests/unit/<package>/test_<module>.py`；契约测试在 `tests/contract/`
- **不要新增依赖除非 plan 已写明**：P1.3 加入 `httpx` + `respx`，P1.4 加入 `ebooklib`，均是 plan/设计显式要求

---

## 3. 下一步（P2 书库持久化）的预备信息

接手 agent 应按 `docs/superpowers/plans/2026-04-30-ndl-p2-library.md` 实施 P2.1。P2 设计文档范围见 `docs/superpowers/specs/2026-04-20-ndl-design.md` §10：

- `storage/`：SQLite + SQLAlchemy 2.0 Mapped style + WAL（当前尚未引入依赖）
- `services(library)`：下载结果入库、书籍列表/详情/删除
- `cli(library)`：`ndl library {list,show,remove}` 最小可用
- 注意 P1 的 CLI download 当前只写输出文件，尚未自动入库；P2 应决定是否改变默认行为或新增显式选项

建议 P2 退出条件：

- 下载结果可持久化到本地 SQLite
- `ndl library list/show/remove` 有 `CliRunner` 覆盖
- 全量质量门保持通过

---

## 4. 关键设计决策备忘（持久）

完整 14 条 ADR 在 `docs/superpowers/specs/2026-04-20-ndl-design.md`。当前已落地的部分：

- ✅ 架构：Clean/Onion（core ← infrastructure ← application ← interfaces）
- ✅ HTTP 层：`httpx` 默认（已落地于 P1.3）
- ✅ 解析：`selectolax`（已落地于 P1.1 selector + P1.2 parsers）
- ✅ 规则：YAML + Pydantic v2 schema（已落地于 P1.1）
- ✅ EPUB：`ebooklib`（已落地于 P1.4）
- ✅ 服务层：Download/Convert services + lightweight container（已落地于 P1.5）
- ✅ CLI：Typer + rich（P1.6 已补齐 download/convert/rules validate）
- ✅ 包管理 / 构建：`uv` + `hatchling`
- ✅ 质量工具：`ruff` + `mypy --strict` + `pytest` + `pre-commit`

尚未落地（P1 之后）：

- ⏳ 存储：SQLite + SQLAlchemy 2.0 Mapped style + WAL（P2 阶段）
- ⏳ Web：FastAPI + HTMX + Jinja2 + SSE（P5+ 阶段）
- ⏳ 调度：APScheduler AsyncIO（P6 阶段）
- ⏳ Playwright extras（P2+，按需）
- ⏳ 日志：`structlog`（P2+）
- ⏳ i18n：`babel`（P5+）

**伦理硬约束（不可协商）：**

- 严格尊重 `robots.txt`（schema 强制 `respect=true` 时省略 `ignore_justification`，关闭时必须填写理由 —— 已落地）
- 限速：每域名默认 ≥ 500ms 间隔（schema 强制 `min_interval_ms >= 500`）、并发 ≤ 3（`max_concurrency <= 3`）—— 已落地
- 不内置：Cloudflare 绕过、商业平台、登录/验证码破解
- 永久不要把"绕过"作为 P1 之后的 backlog 项

---

## 5. 用户身份与偏好（持久）

- **GitHub**：`makunxiang-cmd`
- **目标仓库**：`project_noveldownloader`
- **协作语言**：中文为主
- **流程偏好**：先计划 → 问细节 → 再执行；输出前要自检可靠性
- **决策风格**：评估完选项后倾向"按你推荐的来"，信任 Claude 的判断但要看到 trade-off
- **开源定位**：MIT，无商业目的，合规优先

---

## 6. 关键文件清单

接手 agent 需要熟悉的文件：

```
.
├── AGENTS.md                                         ← agent 协作约定入口
├── CHANGELOG.md                                      ← 切片完成时追加
├── docs/
│   ├── agents/                                       ← agent 协作约定细则
│   │   ├── domain.md
│   │   ├── issue-tracker.md
│   │   └── triage-labels.md
│   └── superpowers/
│       ├── SESSION-STATE.md                          ← 本文件
│       ├── plans/
│       │   ├── 2026-04-20-ndl-p0-scaffold.md         ← P0 计划（已完成）
│       │   ├── 2026-04-29-ndl-p1-mvp.md              ← P1 计划（已完成）
│       │   └── 2026-04-30-ndl-p2-library.md          ← 当前活动 plan
│       └── specs/
│           └── 2026-04-20-ndl-design.md              ← 设计基础（v0.1 全套）
├── pyproject.toml                                    ← 依赖与质量工具配置
├── src/ndl/
│   ├── core/        ✅ P1.1
│   ├── rules/       ✅ P1.1
│   ├── parsers/     ✅ P1.2 + P1.4 TXT reader
│   ├── fetchers/    ✅ P1.3
│   ├── converters/  ✅ P1.4
│   ├── application/ ✅ P1.5
│   ├── cli/         ✅ P1.6
│   └── builtin_rules/example_static.yaml             ← 测试用规则
└── tests/
    ├── contract/                                     ← 端到端契约测试 + fixtures
    └── unit/                                         ← 镜像 src/ndl 结构
```
