# NDL 项目会话状态快照

> 用途：跨会话接力的状态记录。新会话开始时，接手的 agent 应先读取本文件，再读取活动的 release-prep plan，然后参考已完成的 P7/P6/P5 plan。
>
> 最后更新：2026-05-13（P7 全部 4 个 slice 完成、9 项预发布加固完成、PyPI 改名 `noveldownloader`、main 启用轻度分支保护、MkDocs Pages workflow 已就绪等 Pages source 切换。活动计划 `docs/superpowers/plans/2026-05-13-ndl-release-prep.md`）

---

## 0. 项目一句话描述

**NDL (NOVELDOWNLOADER)**：基于 Python 的规则驱动中文小说下载器 + 格式转换工具，MIT 开源，托管在 <https://github.com/makunxiang-cmd/project_noveldownloader>。

## 0.1 下个 agent 快速接手摘要

- **当前状态**：P0-P7 全部实现 + 9 项预发布 P0/P1/P2 加固已实现 + Phase A (Pre-release setup) 3/6 已实现。**仓库已到达 release candidate state**，等待 maintainer 完成 A1+A2+Pages-Source 三件不可代理的 web UI 操作后即可进入 Phase B（release execution）。
- **活动计划**：`docs/superpowers/plans/2026-05-13-ndl-release-prep.md` 列出了 A→E 五阶段的完整路线。新 session 进来先读这个 + 本文件。
- **PyPI 命名**：`ndl` 名字 2016 年被无关项目 `msull/needle` 注册，故 v0.1 发行名 = **`noveldownloader`**。Python import (`from ndl...`) 与 CLI 入口 (`ndl`) 保持不变。已 `uv build` 生成 `noveldownloader-0.1.0.dev0` 工件并跑过 verifier + clean-venv smoke 全绿。
- **`main` 分支保护已开启**（轻度）：要求 PR，但 `required_approving_review_count = 0`；force-push / 删 main 禁用；CI status check 暂未列为 required（因 paths-ignore 会导致 doc-only PR 卡住）。**Agent 工作流：必须 `git checkout -b <topic>` → push → `gh pr create` → `gh pr merge --squash`**，不能再 `git push origin main`。`gh` CLI 已在本地装好并认证为 `makunxiang-cmd`。
- **Phase A 进度**：
  - A0 改名 `noveldownloader` ✅（commit `0b412af`）
  - A1 PyPI 账号 + 2FA ⏳ **等 maintainer 手动**
  - A2 PyPI API token ⏳ **等 maintainer 手动**（依赖 A1）
  - A3 main 分支保护 ✅ 已开
  - A4 MkDocs Pages workflow ✅ workflow 已合（`aea9978`），**Pages source 待 maintainer 在 web UI 切换为 "GitHub Actions"**
  - A5 tag GPG 签名 ⏳ 可选；若不签 tag B13 用 `git tag -a` 即可
  - A6 Issue/PR 模板 ✅ 早已存在
- **Phase B (release execution) 仍 100% 由 maintainer 执行**。Agent 不得 bump 版本、改 CHANGELOG 日期 heading、做 release commit、打 tag、push tag、建 GitHub Release、上 PyPI。
- **最后完整验证（PyPI 改名后）**：`.venv/bin/ruff check .`、`.venv/bin/ruff format --check .`、`.venv/bin/mypy src/ndl`、`.venv/bin/pytest --cov=ndl --cov-report=term` 全绿；pytest **185 passed**，coverage **88.96%**。`uv run mkdocs build --strict --config-file docs/mkdocs.yml` 也零 warning 通过。
- **加固后契约改动**：`SearchService.search()` 返回 `SearchOutcome(results, failures)` 而非 `list[SearchResult]`；调用方需通过 `outcome.results` / `outcome.failures` 访问。CLI 与 Web 均已适配。
- **CI 状态**：main 上的最新 push（`aea9978`）CI 主 workflow 全绿（15/15 cells + lint）；Docs workflow build ✅、deploy ❌（Pages source 未启用，预期失败）。
- **本地 Web 验证**：`ndl serve` 在 `127.0.0.1:8765` 做过 HTTP smoke check，首页 200，空 keyword 搜索 400。Playwright runtime 仍需使用者 `pip install 'noveldownloader[browser]'` + `playwright install chromium`。

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
| **P2.1 存储基础** | `src/ndl/storage/`：engine 工厂（WAL + foreign_keys=ON PRAGMA）、`session_scope` 上下文管理器、SQLAlchemy 2.0 Mapped 模型 4 张表（`NovelRow` / `ChapterRow` / `DownloadJobRow` / `SettingRow`）；新依赖 `sqlalchemy>=2.0`；8 个新 unit test 覆盖 schema、PRAGMA、唯一约束、级联删除、settings KV、status check | 见 P2 plan §P2.1 |
| **P2.2 LibraryRepository** | `src/ndl/storage/repository.py`：`LibraryRepository` 提供 save/list/get/remove；upsert 锚点 `(source_rule_id, source_url)`，章节替换走 `clear() + flush` 再 insert 避免 UNIQUE 冲突；list 走 `func.count` 单查询返回 `NovelSummary` 摘要；9 个新 unit test 覆盖 round-trip / upsert / 无 source_url 总插入 / list 计数 / 缺失返回 None / remove 级联 | 见 P2 plan §P2.2 |
| **P2.3 LibraryService + 容器接线** | `src/ndl/application/services/library.py`：薄包装 `LibraryRepository`；`application/paths.py` 暴露 `ndl_home()` + `library_db_path()`，`cli/disclaimer.py` 改用共享 helper；`ServiceContainer` 加 `db_path` 参数 + 懒加载 `library_service()`（rules validate 等命令不会创建 `~/.ndl/`）；10 个新 unit test 覆盖 service 方法、paths 的 NDL_HOME override、container 单例 | 见 P2 plan §P2.3 |
| **P2.4 Library CLI + download 入库** | `ndl library list/show/remove`；list/show 使用 Rich 表格，show 不展开正文；remove 支持 `--yes`；`ndl download` 成功写文件后默认 `library_service().save(novel)`，`--no-save` 保留文件-only 行为；CLI 测试通过 `NDL_HOME` 隔离 `library.db` | 见 P2 plan §P2.4 |
| **P3.1 Web App Skeleton** | `src/ndl/web/`：FastAPI app factory、Jinja2 templates、static CSS；首页渲染本地书库 UI shell 并从 `LibraryService.list()` 读取摘要；新增 P3 runtime deps；TestClient 覆盖空库和种子库首页 | 见 P3 plan §P3.1 |
| **P3.2 Read-only Library Views** | `GET /` 摘要行链接到详情；`GET /library/{id}` 显示小说元数据 + 章节标题/字数且不展示正文；缺失 ID 返回 404 error template；TestClient 覆盖列表链接、详情和缺失 ID | 见 P3 plan §P3.2 |
| **P3.3 Download Form + Progress Channel** | 首页下载表单；`POST /downloads` URL-encoded 表单解析（不加 `python-multipart`）；FastAPI background task 复用下载/转换服务；输出默认写到 `NDL_HOME/downloads`；`JobRegistry` 记录进度并通过 SSE 输出；native EventSource 渲染进度 | 见 P3 plan §P3.3 |
| **P3.4 `ndl serve` CLI** | `ndl serve` 启动本地 FastAPI Web UI；支持 `--host` / `--port` / `--reload` / `--accept-disclaimer` / `--allow-public-host`；默认 localhost，公共 bind 需显式确认；CliRunner 测试不启动真实 server | 见 P3 plan §P3.4 |
| **P3.5 Web Polish + Docs** | `docs/user-guide/README.md` 重写覆盖 library/serve/--no-save 与 `<NDL_HOME>/{library.db,disclaimer.accepted,downloads/}` 状态布局；`docs/index.md`、`README.zh-CN.md` 同步 P2/P3 状态；Web UI 加首页空态提示和下载任务结果块（输出路径 + 书库链接） | 见 P3 plan §P3.5 |
| **P4.1 Manual Update** | `UpdateService` 按书库条目重新抓目录、比较已存章节 index、只抓缺失章节并追加入库；`ndl update --all` 复用免责声明 gate 和 CLI progress；无新增依赖 | 见 P4 plan §P4.1 |
| **P4.2 Scheduled Runs** | `UpdateScheduler` 使用 APScheduler interval job 调用同一个 `UpdateService.update_all()`；`ndl serve` 默认启用定时追更并可通过 `--no-scheduler` / `--update-interval-hours` 调整；TestClient 默认不启动调度 | 见 P4 plan §P4.2 |
| **P4.3 Web Update Trigger + Status** | Web 首页 `Update all` 入口；`/updates` 结果页展示 id/title/status/new/total/message；TestClient + mocked HTTP 覆盖 append-only 更新与空库状态 | 见 P4 plan §P4.3 |
| **P5.1 Search Domain + Service** | `SearchResult` 领域模型（`core/models.py`）；`parse_search` HTML 解析器（`parsers/html_search.py`）；`SearchService.search(keyword, rule_ids=None)`（`application/services/search.py`）；`ServiceContainer.search_service()` 接线；`example_static` 规则增加 `search` 块；12 个新测试覆盖字段提取、URL 编码、规则过滤、空结果、容器缺失 | 见 P5 plan §P5.1 |
| **P5.2 `ndl search` CLI** | `ndl search <keyword>`；Rich 表格输出 source/title/author/url；支持 repeatable `--rule` 与 `--limit`；空关键词、空 rule id、未知/不可搜索 rule id 走 `InvalidArgumentError`；CliRunner + mocked HTTP 覆盖结果、过滤、空态、错误 | 见 P5 plan §P5.2 |
| **P5.3 Remote Rule Update** | `<NDL_HOME>/rules` 用户规则目录；默认规则加载支持用户规则覆盖 builtin；`RuleUpdateService` 拉取 manifest + YAML、校验可选 SHA-256、全量规则校验后生成写入计划；`ndl rules update --manifest-url` 展示摘要并确认后写盘；非法 bundle 不替换现有规则 | 见 P5 plan §P5.3 |
| **P5.4 Web Search Surface** | Web 首页搜索表单；`GET /search` 复用 `SearchService.search()`；结果页展示 source/title/author/url；每条结果提供 Download 表单，复用现有 `/downloads` 后台下载 + SSE 状态流；TestClient + mocked HTTP 覆盖结果、rule filter、limit、空态和错误输入 | 见 P5 plan §P5.4 |
| **P6.1 Browser Fetcher Foundation** | `pyproject.toml` 新增 `browser` optional extra（`playwright>=1.40`）；`src/ndl/fetchers/browser.py` 新增 `BrowserFetcher`，按 `fetcher.type: browser` 通过 `ServiceContainer` 路由；可选依赖缺失给出明确 `BrowserError`；浏览器路径保留 robots.txt、per-host throttle、retry 和 HTTP status 错误语义；单元测试使用 fake session/respx，不下载浏览器、不访问真实站点 | 见 P6 plan §P6.1 |
| **P6.2 Browser Rule Controls** | `src/ndl/rules/schema.py` 新增 `BrowserRule` / `BrowserViewportRule`，规则可在 `fetcher.browser` 声明 navigation timeout、wait_until、wait_for_selector、extra_wait_ms、viewport、javascript_enabled；`BrowserFetcher` 将配置传入 Playwright context/page 调用；规则 schema 测试和 fake Playwright session 测试覆盖校验与消费路径 | 见 P6 plan §P6.2 |
| **P6.3 Browser Diagnostics** | 新增 `BrowserRuntimeDiagnostic` 与 `check_browser_runtime()`；CLI 新增 `ndl doctor browser` 检查 Playwright 包与 Chromium runtime；BrowserError 启动失败详情包含 `ndl[browser]` / `uv sync --extra browser` 与 `playwright install chromium` 指引；Web 下载 job 失败通过现有 SSE status event 暴露同一诊断详情 | 见 P6 plan §P6.3 |
| **P6.4 Release Hardening** | 新增 `docs/developer/release.md`，记录 v0.1 version decision、preflight gates、browser smoke check、artifact build/inspection、发布步骤和合规边界；用 `/private/tmp/ndl-dist` 临时构建 wheel/sdist 并验证 wheel 含 builtin rule、Web templates/static assets、`browser` extra metadata | 见 P6 plan §P6.4 |
| **P7.1 Distribution Verification Script** | 新增 `scripts/verify_distribution.py`，用 stdlib 校验 wheel/sdist 必需资源（builtin rule、Web templates/static assets）与 wheel metadata（version、extras、browser Playwright dependency）；release checklist 改用该 verifier；单元测试覆盖完整 artifact 成功与缺失 member 失败 | 见 P7 plan §P7.1 |

### 已完成 Plan

已完成计划：**`docs/superpowers/plans/2026-04-29-ndl-p1-mvp.md`** —— P1 MVP 实施计划，6 个切片：

- P1.1 ✅ implemented
- P1.2 ✅ implemented
- P1.3 ✅ implemented
- P1.4 ✅ implemented
- P1.5 ✅ implemented
- P1.6 ✅ implemented

已完成计划：**`docs/superpowers/plans/2026-04-30-ndl-p2-library.md`** —— P2 书库持久化计划：

- P2.1 ✅ implemented — SQLite/SQLAlchemy 存储基础
- P2.2 ✅ implemented — LibraryRepository（save/list/get/remove + Novel↔Row 双向映射）
- P2.3 ✅ implemented — LibraryService + ServiceContainer.library_service()
- P2.4 ✅ implemented — `ndl library list/show/remove` CLI + download 默认入库 + `--no-save` 退出口

已完成计划：**`docs/superpowers/plans/2026-05-01-ndl-p3-web-ui.md`** —— P3 Web UI 计划：

- P3.1 ✅ implemented — Web App Skeleton（依赖 + `src/ndl/web/` app factory/templates/static + `GET /` 测试）
- P3.2 ✅ implemented — Read-only Library Views
- P3.3 ✅ implemented — Download Form + Progress Channel
- P3.4 ✅ implemented — `ndl serve` CLI
- P3.5 ✅ implemented — Web Polish + Docs

已完成计划：**`docs/superpowers/plans/2026-05-01-ndl-p4-update-scheduling.md`** —— P4 Update Scheduling 计划：

- P4.1 ✅ implemented — Manual Update Service + CLI（`ndl update --all`）
- P4.2 ✅ implemented — Scheduled Runs Under `ndl serve`（APScheduler）
- P4.3 ✅ implemented — Web Update Trigger + Status

已完成计划：**`docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md`** —— P5 Search and Remote Rules 计划：

- P5.1 ✅ implemented — Search Domain + Service
- P5.2 ✅ implemented — `ndl search`
- P5.3 ✅ implemented — Remote Rule Update
- P5.4 ✅ implemented — Web Search Surface

已完成计划：**`docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`** —— P6 Browser Fetcher and Release Hardening 计划：

- P6.1 ✅ implemented — Optional Browser Fetcher Foundation
- P6.2 ✅ implemented — Browser Rule Capabilities
- P6.3 ✅ implemented — CLI/Web Documentation and Diagnostics
- P6.4 ✅ implemented — Release Hardening

活动计划：**`docs/superpowers/plans/2026-05-13-ndl-release-prep.md`** —— Release Preparation Plan (Phases A–E)，覆盖从 release candidate 到 v0.1.0 published 与日常运营：

- Phase A 一次性 setup：A0 改名 ✅、A1+A2 PyPI ⏳ maintainer、A3 main 分支保护 ✅、A4 Pages workflow ✅（待 web UI 切 source）、A5 GPG 可选、A6 模板 ✅
- Phase B 发布执行：100% maintainer-only，按 `docs/developer/release.md` 11 步执行
- Phase C–E：发布后文档收尾、用户安装流程、长期维护

已完成（前置 milestone）：**`docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`** —— P7 Release Candidate Verification 计划，4 项全部实现：

- P7.1 ✅ implemented — Distribution Verification Script
- P7.2 ✅ implemented — Release Notes Draft（`docs/release-notes/v0.1.md`，已挂入 MkDocs nav）
- P7.3 ✅ implemented — Install Smoke Strategy（`scripts/smoke_cli.py` + release.md 文档化 + 单测验证）
- P7.4 ✅ implemented — Release Execution Gate（`docs/developer/release.md` 增 Execution Gate 表 + Maintainer Runbook 11 步；agents 必须在 gate 处停手）

已完成（附属）：**`docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md`** —— 预发布 P0/P1/P2 加固，9 项均已实现：

- P0.1 ✅ implemented — LibraryRepository 追加式 upsert（保留旧章节 + 首抓 fetched_at）
- P0.2 ✅ implemented — SearchService 多源容错（SearchOutcome.results/failures）
- P0.3 ✅ implemented — JobRegistry 上限与驱逐（默认 max_jobs=100，仅驱逐终态 job）
- P0.4 ✅ implemented — UpdateService fetcher pool（update_all 期间按 rule.id 复用 fetcher）
- P1.1 ✅ implemented — fetchers/_common.py（resolve_headers / backoff_delay；消除 BrowserFetcher 跨模块私有 import）
- P1.2 ✅ implemented — BrowserFetcher 启动错误清理（_safe_aclose / _safe_stop_manager，避免 Playwright 子进程残留）
- P2.1 ✅ implemented — SSE 用 asyncio.Event 替代 100ms 轮询（DownloadJob.notify；record/mark_* 全部 set）
- P2.2 ✅ implemented — `ndl rules list` CLI（id/name/version/enabled/search/fetcher/patterns 表）
- P2.3 ✅ implemented — RuleUpdateService 并发 fetch + https-only 白名单（NDL_RULES_ALLOW_INSECURE 可降级）

剩余 non-goal：`/updates` 异步化、`Novel.cover_url` 校验器、RuleUpdateService 删除语义、`cli/renderers.py` 覆盖率、`_fetch_chapter` 重复代码。理由详见 plan 文档。

### 质量门当前状态

```
ruff check / format     ✅ 100 files
mypy --strict           ✅ 53 source files
pytest                  ✅ 185 passed, 0 warnings
coverage                ✅ 88.96%（fail_under=80）
```

### 开发环境（macOS / 本地）

- Python: 3.14.4（CI matrix 现覆盖 3.10–3.14）
- 包管理: `uv 0.11.13`（aarch64-apple-darwin），`.venv` 是 macOS arm64
- 全部 runtime/dev 依赖与 `uv.lock` 锁定一致
- 标准开发命令均通过 `uv run`：

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```

### 本轮（2026-05-13）执行要点

**P6.1 Optional Browser Fetcher Foundation 实施**

- 新增 `docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`，把 P6 拆为 browser fetcher 基础、浏览器规则控制、诊断/文档、release hardening
- `pyproject.toml` 新增 optional extra：`browser = ["playwright>=1.40"]`；`uv.lock` 已同步 optional dependency metadata（含 `playwright` / `pyee`）
- `src/ndl/fetchers/browser.py` 新增 `BrowserFetcher`，实现现有 `Fetcher` protocol；默认通过 Playwright Chromium headless 渲染，返回 `page.content()`
- 可选依赖缺失时抛 `BrowserError`，提示安装 `pip install ndl[browser]` 与 `playwright install chromium`
- 浏览器路径保留项目既有边界：通过 `RobotsChecker` 先查 robots.txt，通过 `HostThrottle` 做 per-host 限速，通过 rule retry 处理 5xx / 浏览器错误；4xx 仍直接 `HTTPError`
- `src/ndl/application/container.py`：默认 fetcher factory 根据 `rule.fetcher.type` 路由，`browser` → `BrowserFetcher`，否则保持 `HttpFetcher`
- `src/ndl/fetchers/__init__.py` 导出 `BrowserFetcher`
- `tests/unit/fetchers/test_browser.py`：fake browser session + respx 覆盖 rendered HTML、session 生命周期、5xx retry、robots block、HTTP 404、缺失 Playwright 诊断
- `tests/unit/application/test_container.py`：覆盖默认 HTTP/browser fetcher 路由
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/CHANGELOG/AGENTS/本文件同步 P6.1 状态
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`（162 passed，coverage 88.74%）、`pre-commit run --all-files` 全部通过

**P6.2 Browser Rule Controls 实施**

- `src/ndl/rules/schema.py`：新增 `BrowserWaitUntil`、`BrowserViewportRule`、`BrowserRule`；`FetcherRule` 增加 `browser` 子配置，默认值兼容现有 HTTP 规则
- `fetcher.browser` 支持 `navigation_timeout_ms`、`wait_until`（commit/domcontentloaded/load/networkidle）、`wait_for_selector`、`extra_wait_ms`、`viewport.width/height`、`javascript_enabled`
- `src/ndl/fetchers/browser.py`：默认 timeout 改为读取 `rule.fetcher.browser.navigation_timeout_ms`；Playwright context 使用 viewport 和 JS 开关；page navigation 使用 wait_until，必要时等待 selector 和额外延迟
- `src/ndl/rules/__init__.py` 导出 `BrowserRule` / `BrowserViewportRule`
- `tests/unit/rules/test_schema.py` 覆盖浏览器配置合法值与非法 wait_until/timeout/viewport
- `tests/unit/fetchers/test_browser.py` 增加 fake Playwright session 测试，验证 wait_until / wait_for_selector / wait_for_timeout 被消费
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/docs/rule-authoring/CHANGELOG/AGENTS/P6 plan/本文件同步 P6.2 状态
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`（166 passed，coverage 89.10%）、`pre-commit run --all-files`、`uv lock --check` 全部通过

**P6.3 Browser Diagnostics 实施**

- `src/ndl/fetchers/browser.py`：新增 `BrowserRuntimeDiagnostic` dataclass 与 `check_browser_runtime()`；检查 Playwright import 与 Chromium headless launch，不访问真实站点
- `src/ndl/cli/main.py`：新增 `doctor` Typer 子命令组与 `ndl doctor browser`；成功输出 `Browser runtime: OK`，失败输出 `Browser runtime: FAILED` 并以 exit code 1 退出
- Browser fetcher 缺失依赖/启动失败错误详情补充 `pip install ndl[browser]` / `uv sync --extra browser` 与 `playwright install chromium` 指引
- Web 下载后台 job 继续复用 `NDLError.user_message()`；浏览器 runtime 失败会通过现有 SSE status event 暴露同一诊断消息
- `tests/unit/fetchers/test_browser.py` 覆盖 missing Playwright diagnostic
- `tests/unit/cli/test_main.py` 覆盖 `ndl doctor browser` 成功/失败输出与 exit code
- `tests/unit/web/test_app.py` 覆盖浏览器 runtime 失败时 Web job 记录错误并通过 SSE status event 返回安装提示
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/docs/rule-authoring/CHANGELOG/AGENTS/P6 plan/本文件同步 P6.3 状态
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`（170 passed，coverage 88.91%）、`pre-commit run --all-files`、`uv lock --check` 全部通过

**P6.4 Release Hardening 实施**

- 新增 `docs/developer/release.md`：记录当前版本仍为 `0.1.0.dev0`，v0.1 发布前由 maintainer 专门 bump 到 `0.1.0`
- release checklist 覆盖 `uv lock --check`、ruff、format、mypy、pytest coverage、pre-commit、optional browser smoke (`ndl doctor browser`)
- release checklist 覆盖 `uv build --wheel --sdist --out-dir dist`、wheel/sdist inspection、PyPI 发布步骤和合规边界
- `docs/index.md` 与 `docs/developer/README.md` 链接 release checklist
- 本地临时构建验证：`uv build --wheel --sdist --out-dir /private/tmp/ndl-dist` 成功生成 `ndl-0.1.0.dev0.tar.gz` 和 `ndl-0.1.0.dev0-py3-none-any.whl`
- wheel 内容验证包含 `ndl/builtin_rules/example_static.yaml`、`ndl/web/templates/*.html`、`ndl/web/static/css/app.css`、`ndl/web/static/js/app.js`
- wheel metadata 验证：`Version: 0.1.0.dev0`、`Provides-Extra: browser/dev/docs`、`Requires-Dist: playwright>=1.40; extra == 'browser'`
- 文档：CHANGELOG/AGENTS/P6 plan/本文件同步 P6.4 状态

**P7.1 Distribution Verification Script 实施**

- 新增 `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`，把 P7 拆为 distribution verifier、release notes draft、install smoke strategy、release execution gate
- 新增 `scripts/verify_distribution.py`，只用 Python stdlib (`zipfile` / `tarfile` / `email.parser`) 校验 wheel/sdist
- verifier 检查 wheel 必含 `ndl/builtin_rules/example_static.yaml`、`ndl/web/templates/*.html`、`ndl/web/static/css/app.css`、`ndl/web/static/js/app.js`
- verifier 检查 wheel metadata：当前版本 `0.1.0.dev0`、`Provides-Extra: browser/dev/docs`、`Requires-Dist: playwright>=1.40; extra == 'browser'`
- verifier 检查 sdist 必含 `pyproject.toml`、builtin rule、Web templates/static assets
- `docs/developer/release.md` 的 artifact inspection 增加 `uv run python scripts/verify_distribution.py dist/ndl-*.whl dist/ndl-*.tar.gz`
- `tests/unit/scripts/test_verify_distribution.py` 覆盖完整 fake artifact 成功与缺失 `ndl/web/static/js/app.js` 失败
- 本地临时构建验证：`uv build --wheel --sdist --out-dir /private/tmp/ndl-p7-dist` 成功，`scripts/verify_distribution.py` 对生成的 wheel/sdist 返回 `Distribution artifacts verified.`
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`（172 passed，coverage 88.91%）、`pre-commit run --all-files`、`uv lock --check` 全部通过

**文档交接整理**

- README、中文 README、docs index、user/developer/rule-authoring guide、release checklist、ADR、design spec、P3/P5/P6 plans、CONTEXT、SECURITY、CONTRIBUTING、CHANGELOG 与本文件同步到 P0-P6 完成、P7.1 已完成、P7.2 下一步
- 清理旧 handoff 文案：不再让新 agent 以 P5 或 P6 为活动 milestone；明确活动计划为 P7 release-candidate verification
- 明确发布边界：当前仍未发布到 PyPI，版本仍为 `0.1.0.dev0`，不 bump/tag/release/upload，除非 maintainer 明确批准
- 设计文档补齐实现偏差：当前 Web UI 是 Jinja2 + SSE + native JavaScript，不使用 HTMX；用户规则加载是 builtin + `<NDL_HOME>/rules/*.yaml`，不递归加载 `custom/`
- 验证：`.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`.venv/bin/mypy src/ndl`、`.venv/bin/pytest --cov=ndl --cov-report=term --cov-report=xml`、`git diff --check` 通过；`uv run pre-commit run --all-files` / `uv lock --check` 未能重跑，原因是沙箱不能访问 `/Users/makunxiang/.cache/uv` 且提权请求被系统拒绝

### 本轮（2026-05-11）执行要点

**P5.4 Web Search Surface 实施**

- `src/ndl/web/app.py`：新增 `GET /search`；解析 keyword/rule_id/limit；复用 `service_container.search_service().search()`；错误输入走现有 `error.html` / `UserError` 风格
- `src/ndl/web/templates/index.html`：首页新增搜索表单，包含 keyword、source(rule_id)、limit
- `src/ndl/web/templates/search_results.html`：新增搜索结果页；展示 source/title/author/url；每条结果提供 POST `/downloads` 的 Download 表单，复用现有 Web 下载后台任务与 SSE 结果流
- `src/ndl/web/static/css/app.css`：新增 search panel/results/inline download 样式，沿用现有紧凑本地工具界面
- `tests/unit/web/test_app.py`：新增 5 个 Web 搜索测试（mocked search results、rule filter + limit、empty state、missing keyword、unsupported rule）；不接真实网络
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/CHANGELOG/AGENTS/P5 plan/本文件同步到 P5.4 完成、P5 全部完成
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`、`pre-commit run --all-files` 全部通过

**P5.3 Remote Rule Update 实施**

- `src/ndl/application/paths.py`：新增 `rules_dir()`，用户规则目录固定为 `<NDL_HOME>/rules`
- `src/ndl/rules/loader.py`：新增 `load_rule_text()` 与 `load_default_rules(user_rules_path=...)`；默认规则加载顺序为 builtin 优先、用户规则按 id 覆盖 builtin；`ServiceContainer` 默认改用 `load_default_rules(user_rules_path=rules_dir())`
- `src/ndl/application/services/rule_update.py`：新增 `RemoteRuleManifest` / `RemoteRuleEntry` schema、`RuleUpdatePlan` / `RuleUpdateItem`、`RuleUpdateService.plan_update()` / `apply_update()`；manifest 支持 `version: 1` + `rules[{id,url,sha256?}]`
- 远程更新行为：先下载 manifest，再下载全部 YAML；可选 SHA-256 校验；每条规则用 Pydantic schema 校验；manifest id 必须等于 YAML rule id；全部通过后才生成写入计划
- `src/ndl/cli/main.py`：新增 `ndl rules update --manifest-url <url> [--yes]`；也支持 `NDL_RULES_MANIFEST_URL`；输出 status/id/name/version/target 摘要表；默认要求确认后写入
- 安全边界：非法 remote bundle、checksum mismatch、id mismatch 都不会替换 `<NDL_HOME>/rules` 里已有文件；无默认远程 feed，必须显式传 URL 或环境变量
- 测试：`tests/unit/application/services/test_rule_update.py` 覆盖写入、unchanged、非法 bundle 不替换、checksum mismatch；CLI 覆盖确认写入、拒绝确认、非法 bundle、缺失 manifest；loader 覆盖用户规则覆盖 builtin
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/CHANGELOG/AGENTS/P5 plan/本文件同步到 P5.3 完成、P5.4 next
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`、`pre-commit run --all-files` 全部通过

**P5.2 `ndl search` CLI 实施**

- `src/ndl/cli/main.py`：新增 `@app.command("search")`；必填 keyword；可选 repeatable `--rule` 传给 `SearchService.search(..., rule_ids=...)`；可选 `--limit` 截断输出行
- CLI 输出：搜索结果用 Rich 表格渲染 `source / title / author / url`；空结果输出 `No search results.`
- CLI 校验：空 keyword、空 rule id、未知/不可搜索 rule id 均抛 `InvalidArgumentError`；错误详情列出可用 searchable rule id
- `src/ndl/application/container.py`：新增只读 `list_rules()`，供 CLI 在搜索前验证 `--rule` 选择；不触发 SQLite engine 创建
- 测试：`tests/unit/cli/test_main.py` 新增 5 个 CliRunner 用例（mocked search results、`--rule` + `--limit`、空结果、空 keyword、未知 rule id）；`tests/unit/application/test_container.py` 新增 `list_rules()` 顺序测试
- 文档：README/README.zh-CN/docs/index/docs/user-guide/docs/developer/CHANGELOG/AGENTS/P5 plan/本文件同步到 P5.2 完成、P5.3 next
- 质量门：`ruff check .`、`ruff format --check .`、`mypy src/ndl`、`pytest --cov=ndl --cov-report=term --cov-report=xml`、`pre-commit run --all-files` 全部通过

**P5.1 Search Domain + Service 实施**

- `src/ndl/core/models.py`：新增 `SearchResult` 冻结领域模型（title/author/url/source_rule_id/source_name），field_validator 保证非空 strip
- `src/ndl/parsers/html_search.py`：`parse_search(rule, html, *, base_url)` 复用 `extract_text` + selector DSL，author 字段缺失时 fallback 为 None；container 缺失抛 `SelectorNotFoundError`
- `src/ndl/application/services/search.py`：`SearchService.search(keyword, rule_ids=None)`；并发 `asyncio.create_task` + `as_completed`，关键词 `urllib.parse.quote_plus`；只对 `rule.enabled and rule.search is not None` 的规则执行；每个 fetcher 独立 `aclose()`
- `src/ndl/application/container.py`：`ServiceContainer.search_service()` 工厂方法
- `src/ndl/builtin_rules/example_static.yaml`：增加声明式 `search` 块（`url_template={keyword}` placeholder + results_container/items + fields.title/author/url）
- 测试：`tests/unit/parsers/test_html_search.py`（6 例）+ `tests/unit/application/services/test_search.py`（6 例），全部用 mocked HTTP 或 inline HTML

**开发环境恢复**

- 检测到 `.venv/bin/ruff` 是 ELF Linux x86-64，macOS 上无法执行
- 安装 `uv 0.11.13`（aarch64-apple-darwin），`uv sync --extra dev` 重建 `.venv` 为原生 macOS arm64
- `pyproject.toml` classifiers 补上 Python 3.13 / 3.14
- `.github/workflows/ci.yml` test matrix 从 `["3.10", "3.11", "3.12"]` 扩到 `["3.10", "3.11", "3.12", "3.13", "3.14"]`

**代码 / 仓库治理**

- 7 个 `__init__.py` / `__main__.py` 补齐 `from __future__ import annotations`（项目约定要求每个模块都有）
- 137 个文件的 `100644 → 100755` mode 噪音批量 `chmod 644` 清零
- 当时同步了 README.md / README.zh-CN.md / docs/index.md / docs/developer/README.md / AGENTS.md 的 P5 状态行；最新交接状态以后续 P6/P7 小节和本文件顶部摘要为准

**架构改进 + SQLite ResourceWarning 修复**

- Python 3.14 收紧了 sqlite3 connection 生命周期检查，出现 11 条 `ResourceWarning: unclosed database`
- `ServiceContainer` 增加 `close()` 方法 + `__enter__`/`__exit__` 上下文管理器协议；`close()` 是幂等的，仅在 `_engine` 被懒加载后才 dispose
- `cli/main.py` 全部 6 处 `ServiceContainer()` 调用改用 `with` 块（library list/show/remove + download/convert/update）
- `web/app.py` lifespan 退出时 `service_container.close()`
- 测试侧：`tests/unit/storage/test_database.py` 重写用 `engine` / `factory` fixture；`tests/unit/web/test_app.py` 加 `make_container` fixture（factory 模式 + teardown 自动 close）；`tests/unit/cli/test_main.py` / `tests/unit/application/test_container.py` / `tests/unit/application/services/test_update.py` 改用 `with ServiceContainer()`
- 结果：11 → 0 warnings；136 个测试全过；coverage 提升到 89.81%

### 本轮（2026-05-01）审查修补要点

- `AGENTS.md`、`docs/developer/README.md`、设计文档实现状态、关键文件清单当时已同步到 P0-P4 完成、P5 计划待实施
- `LibraryRepository.append_chapters()` 现在会在小说状态变化但无新增章节时同步更新 `last_updated`
- `tests/unit/storage/test_repository.py` 增加回归测试，覆盖“状态更新但追加 0 章”的追更边界
- 清理 `storage.repository._coerce_status()` 的不必要 `type: ignore`
- 完整质量门通过：ruff、format check、mypy、pytest coverage、pre-commit

### 本轮（2026-05-01）P4.1 完成要点

- 新增 `docs/superpowers/plans/2026-05-01-ndl-p4-update-scheduling.md`，把 P4 拆为手动 update service/CLI、APScheduler 接入、Web 手动触发与状态展示
- `src/ndl/application/services/update.py` 新增 `UpdateService` 与 `UpdateResult`；`update_all()` 遍历书库中非 completed 且有 `source_url` 的条目，单本失败会记录为 result，不中断整批
- `UpdateService.update_novel()` 重新抓取目录页，对比已存章节 index，只 fetch 缺失章节，再通过 `LibraryService.append_chapters()` 追加入库
- `src/ndl/storage/repository.py` 新增 `append_chapters()`，在单事务内过滤重复 index、追加章节、更新 `last_updated` 与最新状态
- `ServiceContainer.update_service()` 接好规则解析、fetcher/parser factory 与 progress callback
- CLI 新增 `ndl update --all --accept-disclaimer`；未给 `--all` 时返回用户错误；输出 Rich 表格（id/title/status/new/total/message）
- 测试新增 `tests/unit/application/services/test_update.py` 与 CLI mocked HTTP 覆盖，确保只抓缺失章节、跳过 completed/无 source_url 条目
- README、README.zh-CN、docs/user-guide、docs/index、docs/developer、CHANGELOG 已同步 P4.1 状态

### 本轮（2026-05-01）P4.2 完成要点

- 新增依赖 `apscheduler>=3.10`（当前 lock 为 3.11.2，附带 `tzlocal`）
- 新增 `src/ndl/scheduler/update_job.py`：`UpdateScheduler` 封装 APScheduler `AsyncIOScheduler`，注册 interval job `ndl-update-all`，`max_instances=1`、`coalesce=True`，并记录 `UpdateSchedulerState`
- `UpdateScheduler.run_once()` 调用注入的 `update_all` coroutine；Web 侧注入的是 `service_container.update_service().update_all`，保证 CLI 与调度器复用同一业务入口
- `src/ndl/web/app.py` 增加 lifespan；`create_app()` 默认 `enable_scheduler=False`，测试和直接 app factory 不启动后台调度；`create_serve_app()` 从环境读取调度开关与间隔
- `ndl serve` 增加 `--scheduler/--no-scheduler` 与 `--update-interval-hours`，并把 uvicorn factory 目标改为 `ndl.web.app:create_serve_app`
- 新增 scheduler 单元测试覆盖 start/shutdown、interval job 参数、run_once 成功与用户错误记录；Web 测试覆盖默认关闭与显式启用时 lifespan 启停；CLI 测试覆盖新 serve 参数和环境传递
- README、README.zh-CN、docs/user-guide、docs/index、docs/developer、CHANGELOG、P4 plan 已同步 P4.2 状态

### 本轮（2026-05-01）P4.3 完成要点

- Web 首页 toolbar 新增 `Update all` 表单，提交到 `POST /updates`
- `src/ndl/web/app.py` 新增 `/updates` 路由，调用 `service_container.update_service().update_all()`；NDLError 转为用户安全错误页
- 新增 `src/ndl/web/templates/update_results.html`，展示每本书 `id/title/status/new/total/message`，标题链接回书籍详情
- CSS 增加 `.update-panel` / `.panel-heading` / toolbar button 样式，沿用现有本地工具界面风格
- Web 测试新增 mocked HTTP 追更路径：已保存 1 章时只抓第 2 章并追加；空库更新渲染空状态
- 新增 `docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md`，P4 完成后下一步进入 P5.1 Search domain + service
- README、README.zh-CN、docs/user-guide、docs/index、docs/developer、CHANGELOG、P4 plan、本文件已同步 P4.3 状态

### 本轮（2026-05-01）P3.5 完成要点

- `docs/user-guide/README.md` 重写：CLI 参考补齐 `ndl convert` / `ndl download --no-save` / `ndl library list/show/remove` / `ndl serve` 与 Web UI 走查；新增 `<NDL_HOME>/{library.db,disclaimer.accepted,downloads/}` 状态表
- `docs/index.md` 状态行从 "P2 next" 同步到 "P3 Web UI core flow done, P3.5 polish in progress"，并把当前 capabilities 列表补齐 library / serve
- `README.zh-CN.md` 与英文 README 对齐：P2 已完成、P3 在打磨；用法块加上 `ndl library list` 和 `ndl serve --accept-disclaimer`，把 `ndl update --all` 单独移到 P4+ 规划
- `src/ndl/web/templates/index.html` 空态加一句操作引导（保留 "No saved novels" 字面，不破坏 TestClient 断言）
- `src/ndl/web/templates/download_job.html` + `static/js/app.js` 新增 `data-job-result` 块；当 SSE `status` 事件返回 `succeeded` 时渲染输出路径 `code` 与 `/library/{novel_id}` 链接，`failed` 时显示 `error_message`；CSS 加 `.job-result` 样式
- 不新增依赖；HTMX 仍未 vendored
- CHANGELOG 加 P3.5 条目；P3 plan 标 P3.5 implemented

### 本轮（2026-05-01）P3.4 完成要点

- 新增 `ndl serve` CLI 命令，支持 `--host`、`--port`、`--reload`、`--accept-disclaimer`、`--allow-public-host`
- 启动前复用 `ensure_download_disclaimer()`，首次未确认时与 `ndl download` 使用一致的用户提示/退出路径
- 默认 bind 为 `127.0.0.1`；`0.0.0.0` 等非本地 bind 默认拒绝，必须显式加 `--allow-public-host`
- `_run_web_server()` 封装 `uvicorn.run("ndl.web.app:create_app", factory=True, ...)`，便于 CLI 测试 monkeypatch，避免启动真实 server
- CLI 测试新增 4 个用例，覆盖免责声明 gate、uvicorn 参数、公共 host 拒绝与显式允许

### 本轮（2026-05-01）P3.3 完成要点

- 首页新增下载表单：URL、格式（epub/txt）、Save checkbox
- 新增 `src/ndl/web/jobs.py`，提供 in-memory `JobRegistry` 与 `DownloadJob`
- 新增 `POST /downloads`，用 `FastAPI BackgroundTasks` 跑下载；表单用 stdlib `parse_qs` 解析，避免新增 `python-multipart`
- Web 下载复用 `ServiceContainer.download()` + `ConvertService`；保存开启时调用 `library_service().save(novel)`，未勾选 Save 时跳过入库
- 输出文件默认写到 `NDL_HOME/downloads`，测试通过 `create_app(output_dir=...)` 注入临时目录
- 新增 `/downloads/{job_id}/events` SSE，输出 `ProgressEvent.model_dump_json()` 和最终 status event；前端用 native `EventSource`，HTMX 仍未 vendored
- Web 测试扩展到 7 个：mocked HTTP 下载入库、no-save、不写正文、SSE progress/status、缺失 URL 400

### 本轮（2026-05-01）P3.2 完成要点

- `GET /` 继续使用 `LibraryService.list()` 摘要，不加载章节正文；列表标题链接到 `/library/{id}`
- 新增 `GET /library/{id}`，渲染小说标题、作者、规则、来源 URL、抓取时间、章节标题和字数
- 新增 `error.html`，缺失 ID 返回 HTTP 404，并以 `UserError.user_message()` 风格显示错误信息
- `tests/unit/web/test_app.py` 扩展到 4 个测试：空库、列表链接、详情页不泄漏正文、缺失 ID 404

### 本轮（2026-05-01）P3.1 完成要点

- P3 runtime dependencies 写入 `pyproject.toml` / `uv.lock`：`fastapi`, `uvicorn[standard]`, `jinja2`, `sse-starlette`
- 新增 `src/ndl/web/app.py`，`create_app(container=...)` 可注入测试容器，首页通过 `LibraryService.list()` 渲染本地库摘要
- 新增 `src/ndl/web/templates/` 与 `src/ndl/web/static/css/app.css`，第一屏是书库工具界面，不做营销页
- 新增 `tests/unit/web/test_app.py`，覆盖空库首页和种子库首页；不会展开章节正文

### 本轮（2026-05-01）P3 计划创建要点

- 新增 `docs/superpowers/plans/2026-05-01-ndl-p3-web-ui.md`
- P3 依赖决策：`fastapi>=0.110`, `uvicorn[standard]>=0.27`, `jinja2>=3.1`, `sse-starlette>=2.0`
- P3 切片顺序：Web skeleton → read-only library → download form + SSE progress → `ndl serve` → docs/polish
- README 状态更新为 P2 已完成、P3 Web UI next，并把 `ndl library list` 移入当前可用命令

### 本轮（2026-05-01）P2.4 完成要点

**CLI 行为**

- 新增 `library` Typer 子应用：`ndl library list` / `show <id>` / `remove <id>`
- `list` 输出 `id / title / author / status / chapter_count / fetched_at`
- `show` 输出小说头部信息和章节标题/字数，不输出章节正文
- `remove` 使用 `LibraryService.remove()` 级联删除；`--yes` / `-y` 可跳过确认
- `download` 在成功写出目标文件后默认保存下载得到的 `Novel`；`--no-save` 可关闭入库

**测试**

- `tests/unit/cli/test_main.py` 新增 `NDL_HOME=tmp_path/ndl-home` 隔离库覆盖
- 覆盖 mocked HTTP 下载后自动保存、`--no-save` 空库、`library show` 不泄漏正文、`library remove --yes` 后列表为空

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
2. Read docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md（活动的 P7 plan）
3. Read docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md（已完成的 P6 plan）
4. Read docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md（已完成的 P5 plan，历史参考）
5. Read AGENTS.md + docs/agents/issue-tracker.md（约定）
6. 检查仓库状态：git log --oneline -10 + git status --short；当前预期存在未提交 P5.1-P5.4 + 治理/文档变更 + P6.1-P6.4 browser/release work + P7.1 verifier
7. 确认本文件 §1 的"已完成"列表与代码实际情况一致：
   - src/ndl/core/        ✅ P1.1
   - src/ndl/rules/       ✅ P1.1
   - src/ndl/parsers/     ✅ P1.2 + P1.4 TXT reader
   - src/ndl/fetchers/    ✅ P1.3 + P6.1 BrowserFetcher
   - src/ndl/converters/  ✅ P1.4
   - src/ndl/application/ ✅ P1.5 + P2.3 library + P4.1 update service
   - src/ndl/scheduler/   ✅ P4.2 APScheduler wrapper
   - src/ndl/cli/         ✅ P1.6 + P2.4 library commands + P3.4 serve + P4.1 update + P4.2 scheduler flags
   - src/ndl/storage/     ✅ P2.1-P2.2 + P4.1 append_chapters
   - src/ndl/web/         ✅ P3.1-P3.5 + P4.3 update controls
   - src/ndl/parsers/html_search.py     ✅ P5.1
   - src/ndl/application/services/search.py  ✅ P5.1
   - src/ndl/cli/main.py search command      ✅ P5.2
   - src/ndl/application/services/rule_update.py ✅ P5.3
   - <NDL_HOME>/rules default loading path         ✅ P5.3
   - src/ndl/web/templates/search_results.html     ✅ P5.4
   - src/ndl/web/app.py /search route              ✅ P5.4
   - src/ndl/fetchers/browser.py                   ✅ P6.1
   - src/ndl/rules/schema.py BrowserRule           ✅ P6.2
   - src/ndl/cli/main.py doctor browser            ✅ P6.3
   - docs/developer/release.md                     ✅ P6.4
   - scripts/verify_distribution.py                ✅ P7.1
8. 跑一遍质量门（见上节）确认绿；如果某项失败，先修复再推进
9. P7.1 已完成；继续 P7.2 前先更新/确认 P7 plan 范围
10. 若要扩大 milestone 范围，先写/更新 plan，再实现；完成后更新 CHANGELOG.md、对应 plan、本文件
```

### 工程风格约定（已在前 6 阶段固化，必须延续）

- **子模块平铺**：每个职责一个 `.py`，私有 helper 用 `_xxx.py`，`__init__.py` 仅做 import re-export + `__all__`
- **薄包装类**：纯函数承担逻辑（如 `parse_index(rule, html, ...)`），Protocol 实现作为绑定 rule 的薄类（如 `HtmlParser` / `HttpFetcher`）
- **类型严格**：mypy `--strict` 必须过；`python_version = "3.10"` —— 不要用 `Self` 等 3.11+ 语法
- **`from __future__ import annotations`** 每个模块顶部都加（包括 `__init__.py` / `__main__.py`，2026-05-11 已统一补齐）
- **零冗余注释**：模块单行 docstring + 公开函数单行 docstring；不要 WHAT 注释
- **错误层级对齐 `core/errors.py`**：`UserError` / `RuleError` / `FetchError` / `ParseError` / `StorageError` / `ConvertError`，新错误类必须落在某个分支下
- **测试结构镜像源码**：`tests/unit/<package>/test_<module>.py`；契约测试在 `tests/contract/`
- **不要新增依赖除非 plan 已写明**：已落地依赖按 P1-P6 plan 阶段化引入；P7.1 verifier 刻意只用 stdlib。新增 runtime/dev/browser 依赖前先更新 plan。
- **`ServiceContainer` 是上下文管理器**（2026-05-11 引入）：CLI 命令和测试中创建 `ServiceContainer()` 必须用 `with` 块或显式 `container.close()`，确保 SQLAlchemy engine 在使用后被 dispose；这是 Python 3.14 上避免 `ResourceWarning: unclosed database` 的必要步骤

---

## 3. 下一步预备信息

P7 是当前活动 milestone。`docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md` 已创建，P7.1 distribution verification 已实现；下一步是 P7.2 release notes draft。

**P7 当前边界**

1. 不 bump 版本、不创建 tag、不发 GitHub Release、不上传 PyPI，除非 maintainer 明确要求。
2. Release-candidate 工作只做可重复验证、文档和人工发布前的 gate。
3. 自动测试仍不得访问真实小说站点；browser 相关测试继续使用 fake session / mocked HTTP。

**P7.1 已实现命令**

```bash
uv build --wheel --sdist --out-dir /private/tmp/ndl-p7-dist
uv run python scripts/verify_distribution.py /private/tmp/ndl-p7-dist/ndl-*.whl /private/tmp/ndl-p7-dist/ndl-*.tar.gz
```

verifier 检查 wheel/sdist 中的 builtin rule、Web templates/static assets，以及 wheel metadata 中的 version、extras、browser Playwright dependency。

**P7.2 建议输出**

- 把 `CHANGELOG.md` 巨大的 Unreleased 条目整理成 maintainer 可审阅的 v0.1 release notes draft。
- 用户价值优先：下载/转换、书库、更新、搜索、远程规则、Web UI、可选 browser、release verification。
- 保留合规边界：no commercial platforms、no login/CAPTCHA/paywall/Cloudflare bypass、no proxy pools。
- 不要删除详细 changelog；可以新增 release-note 小节或独立文档，保持完整审计轨迹。

**历史实现速查（P2-P6）**

- `ServiceContainer.list_rules() -> list[SourceRule]`：CLI 搜索前验证 searchable rule id
- `ServiceContainer.search_service() -> SearchService`
- `SearchService.search(keyword: str, *, rule_ids: list[str] | None = None) -> list[SearchResult]`
- `ndl search <keyword> [--rule RULE_ID ...] [--limit N]`
- 搜索结果表格字段：`source / title / author / url`
- `RuleUpdateService.plan_update()` / `apply_update()` 与 `ndl rules update --manifest-url <url> [--yes]`
- 默认规则加载会包含 `<NDL_HOME>/rules/*.yaml` 并按 rule id 覆盖 builtin
- Web `GET /search` 复用 `SearchService`，结果页每条结果可 POST 到 `/downloads`
- 合规边界继续沿用：免责声明、robots.txt、限速/并发约束不可绕过；不支持商业平台 / 登录 / 验证码 / Cloudflare / paywall 绕过

P3.1 已落地清单：

1. 更新 `pyproject.toml` runtime dependencies，加入 P3 已批准依赖
2. 新建 `src/ndl/web/` package，包含 FastAPI app factory、templates、static 目录
3. `GET /` 返回本地书库 UI shell（第一屏是实际工具界面，不做营销 landing）
4. `tests/unit/web/` 使用 `TestClient` 覆盖 app factory 与首页 200
5. 不启动 scheduler、不接真实网络、不做下载表单；这些留给 P3.2/P3.3

P3.2 已落地清单：

1. `GET /` 正式作为 read-only library list，保持 `LibraryService.list()` 摘要调用，不加载正文
2. 新增 `GET /library/{id}`，显示小说元数据和章节列表，不展示章节正文
3. 缺失 ID 返回用户可见 404 页面/模板，复用 `NDLError.user_message()` 风格，不暴露 traceback
4. TestClient 用临时 DB seed 小说，覆盖列表、详情、缺失 ID
5. 不做下载表单和 SSE；留给 P3.3

P3.3 已落地清单：

1. 首页增加下载表单：URL、输出格式、保存/不保存选择
2. Web 下载仍通过 `ServiceContainer.download()` + `ConvertService`，保持 robots/rate-limit/disclaimer 约束
3. 建一个最小 in-memory job registry/progress channel，将 `ProgressEvent` 序列化为 SSE
4. 测试只用 mocked HTTP routes 和临时 DB，覆盖 web-triggered download 可保存到库
5. 失败时返回用户可见错误，不暴露 traceback；不做调度/追更

P3.4 落地清单：

1. 新增 `ndl serve` CLI 命令：`--host`, `--port`, `--reload`, `--accept-disclaimer`
2. 复用 `ensure_download_disclaimer()`；首次 `ndl serve` 未确认时应给出和 download 一致的退出码/提示
3. 默认 host 为 `127.0.0.1`；公共 bind（如 `0.0.0.0`）需要明确处理，避免静默暴露
4. 通过 `uvicorn` 启动 `ndl.web:create_app` 或等价 app factory
5. CliRunner 测试覆盖免责声明 gate 和参数校验，不启动真实 server

P3.5 已落地清单：

1. 补齐 focused CSS，让 Web UI 保持本地工具风格：紧凑、可扫读、下载/书库区域清晰
2. 更新 README 与 docs/user-guide 中的当前 CLI + Web 命令，反映 P2/P3 已落地能力
3. 文档说明状态存储位置：`NDL_HOME`、`library.db`、免责声明 marker、Web 下载输出目录
4. 保持无 Node/npm、无前端构建链；P3.5 未新增依赖
5. 已跑完整质量门并更新 CHANGELOG、P3 plan、本文件

P2.4 已落地清单：

1. `ndl library list` — 表格输出 `id / title / author / status / chapter_count / fetched_at`
2. `ndl library show <id>` — 显示头部信息 + 章节列表（不展开正文）
3. `ndl library remove <id>` — 级联删除，`--yes` 跳过确认
4. `ndl download` 默认在写完文件后调用 `library_service().save(novel)`，通过 `--no-save` 退出
5. `CliRunner` 测试用 `NDL_HOME=tmp_path/ndl-home` 隔离 DB

注意：P2.3 把 export 方法刻意从 LibraryService 拿掉；后续若做导出命令，CLI 直接 `library.get(id)` + `convert_service.convert(novel, output)` 组合即可。

P2 退出条件已满足：

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

阶段化落地状态（P2 之后）：

- ✅ 存储：SQLite + SQLAlchemy 2.0 Mapped style + WAL（P2.1 已落地，仓储/服务/CLI 在 P2.2–P2.4）
- ✅ Web：FastAPI + Jinja2 + SSE 已落地到 P3.5；HTMX 尚未使用
- ✅ 调度：APScheduler AsyncIO（P4.2 已落地于 `src/ndl/scheduler/`）
- ✅ Playwright optional extra（P6.1 已落地为 `browser` extra；真实 Chromium runtime 由使用者执行 `playwright install chromium` 安装）
- ⏳ 日志：`structlog`（后续 observability/release-hardening 可再评估）
- ⏳ i18n：`babel`（后续 i18n 需求明确后再评估）

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
│       │   ├── 2026-04-30-ndl-p2-library.md          ← P2 计划（已完成）
│       │   ├── 2026-05-01-ndl-p3-web-ui.md           ← P3 计划（已完成）
│       │   ├── 2026-05-01-ndl-p4-update-scheduling.md ← P4 计划（已完成）
│       │   ├── 2026-05-01-ndl-p5-search-rules.md     ← P5 计划（已完成）
│       │   ├── 2026-05-13-ndl-p6-browser-release.md  ← P6 计划（已完成）
│       │   └── 2026-05-13-ndl-p7-release-candidate.md ← P7 计划（活动）
│       └── specs/
│           └── 2026-04-20-ndl-design.md              ← 设计基础（v0.1 全套）
├── pyproject.toml                                    ← 依赖与质量工具配置
├── scripts/verify_distribution.py                    ← P7.1 wheel/sdist verifier
├── src/ndl/
│   ├── core/        ✅ P1.1 + P5.1 SearchResult model
│   ├── rules/       ✅ P1.1 + P5.3 user rule loading + P6.2 BrowserRule
│   ├── parsers/     ✅ P1.2 + P1.4 TXT reader + P5.1 html_search.py
│   ├── fetchers/    ✅ P1.3 + P6.1 BrowserFetcher + P6.3 browser diagnostics
│   ├── converters/  ✅ P1.4
│   ├── application/ ✅ P1.5 + P2.3 library service + P4.1 update service + P5.1 SearchService + P5.2 list_rules() + P5.3 RuleUpdateService + 2026-05-11 ServiceContainer.close() / context manager
│   ├── scheduler/   ✅ P4.2 recurring update jobs
│   ├── cli/         ✅ P1.6 + P2.4 library commands + P3.4 serve + P4 update/serve scheduler flags + P5.2 ndl search + P5.3 rules update + P6.3 doctor browser + 2026-05-11 with-block engine cleanup
│   ├── storage/     ✅ P2.1-P2.2 + P4.1 append-only updates
│   ├── web/         ✅ P3.1-P3.5 + P4.3 update controls/results + P5.4 search UI + 2026-05-11 lifespan engine dispose
│   └── builtin_rules/example_static.yaml             ← 测试用规则（2026-05-11 增加 search 块）
└── tests/
    ├── contract/                                     ← 端到端契约测试 + fixtures
    └── unit/                                         ← 镜像 src/ndl 结构，含 tests/unit/scripts/test_verify_distribution.py
```
