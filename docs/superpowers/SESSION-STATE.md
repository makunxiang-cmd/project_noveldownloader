# NDL 项目会话状态快照

> 用途：跨会话接力的状态记录。新会话开始时，接手的 agent 应先读取本文件，再读取当前活动 plan，再决定下一步动作。
>
> 最后更新：2026-05-01（P4.3 Web Update Trigger + Status 完成：首页新增 `Update all` 表单，`POST /updates` 调用 `UpdateService.update_all()` 并渲染每本书结果表；P4 plan 标记完成；新增 P5 Search and Remote Rules 计划。下一步进入 P5.1 Search domain + service）

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

### 当前活动 Plan

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

当前活动计划：**`docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md`** —— P5 Search and Remote Rules 计划：

- P5.1 ⏳ planned — Search Domain + Service
- P5.2 ⏳ planned — `ndl search`
- P5.3 ⏳ planned — Remote Rule Update
- P5.4 ⏳ planned — Web Search Surface

### 质量门当前状态

```
ruff check / format     ✅
mypy --strict (48 文件) ✅
pytest                  ✅ 123 passed
coverage                ✅ 89.40%（fail_under=80）
```

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
2. Read docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md（活动 plan）
3. Read AGENTS.md + docs/agents/issue-tracker.md（约定）
4. 检查仓库状态：git log --oneline -10 + git status，确认是否存在未提交切片变更
5. 确认本文件 §1 的"已完成"列表与代码实际情况一致：
   - src/ndl/core/        ✅ P1.1
   - src/ndl/rules/       ✅ P1.1
   - src/ndl/parsers/     ✅ P1.2 + P1.4 TXT reader
   - src/ndl/fetchers/    ✅ P1.3
   - src/ndl/converters/  ✅ P1.4
   - src/ndl/application/ ✅ P1.5 + P2.3 library + P4.1 update service
   - src/ndl/scheduler/   ✅ P4.2 APScheduler wrapper
   - src/ndl/cli/         ✅ P1.6 + P2.4 library commands + P3.4 serve + P4.1 update + P4.2 scheduler flags
   - src/ndl/storage/     ✅ P2.1-P2.2 + P4.1 append_chapters
   - src/ndl/web/         ✅ P3.1-P3.5 + P4.3 update controls
6. 跑一遍质量门（见上节）确认绿；如果某项失败，先修复再推进
7. P4 全部已完成；下一步进入 P5.1 Search domain + service
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

## 3. 下一步（P5.1 Search Domain + Service）的预备信息

P4 已经完成追更核心、CLI、定时调度和 Web 手动入口。接手 agent 应按 `docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md` 实施 P5.1。

- P5.1 应先定义搜索结果领域模型和服务层，不急着做 CLI/Web
- 搜索能力必须由规则声明驱动；如需扩展 rule schema，保持向后兼容并补 fixtures
- 测试继续使用 bundled fixture 或 mocked HTTP，不接真实网络
- 不要把商业平台、登录、验证码、Cloudflare 或 paywall 绕过放入搜索范围
- 合规边界继续沿用：免责声明、robots.txt、限速/并发约束不可绕过

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
- ⏳ Playwright extras（P2+，按需）
- ⏳ 日志：`structlog`（P5 阶段）
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
│       │   ├── 2026-04-30-ndl-p2-library.md          ← P2 计划（已完成）
│       │   └── 2026-05-01-ndl-p3-web-ui.md           ← 当前活动 plan
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
│   ├── cli/         ✅ P1.6 + P2.4 library commands + P3.4 serve
│   ├── storage/     ✅ P2.1-P2.2
│   ├── web/         ✅ P3.1-P3.5
│   └── builtin_rules/example_static.yaml             ← 测试用规则
└── tests/
    ├── contract/                                     ← 端到端契约测试 + fixtures
    └── unit/                                         ← 镜像 src/ndl 结构
```
