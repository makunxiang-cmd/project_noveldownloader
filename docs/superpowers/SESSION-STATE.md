# NDL 项目会话状态快照

> 用途：跨会话接力的状态记录。每当用户在新会话中说 **"继续"** / **"resume"** / **"开始执行 P0 scaffold 计划"** 时，Claude Code 应先读取本文件再决定下一步动作。
>
> 最后更新：2026-04-20（会话首次交接点：P0 计划已写就，等待用户完成重命名 + GitHub 仓库建立）

---

## 0. 项目一句话描述

**NDL (NOVELDOWNLOADER)**：基于 Python 的规则驱动中文小说下载器 + 格式转换工具，MIT 开源，计划托管在 <https://github.com/makunxiang-cmd/project_noveldownloader>。

---

## 1. 已完成里程碑

| # | 里程碑 | 产出 | 状态 |
|---|---|---|---|
| M1 | 需求澄清（8 轮问答） | 对话记录 | ✅ |
| M2 | 架构方案比选（推荐方案 B：规则驱动 + FastAPI+HTMX + APScheduler） | 用户批准"方案 B" | ✅ |
| M3 | 设计文档分节评审（§1–§5 逐节批准） | `docs/superpowers/specs/2026-04-20-ndl-design.md`（774 行） | ✅ |
| M4 | 设计文档自审（占位符、一致性、范围、歧义） | 已修复 3 处：部分失败语义 / download_jobs.status 分离 / §12.3 目录改名决议 | ✅ |
| M5 | P0 脚手架实现计划 | `docs/superpowers/plans/2026-04-20-ndl-p0-scaffold.md`（10 个任务，TDD） | ✅ |
| M6 | P0 计划自审 | 已修复 Windows 跨 shell 兼容性（Task 9 Step 1 三套语法） | ✅ |
| M7 | 执行方式选择 | **用户选定：Subagent-Driven 模式** | ✅ |

---

## 2. 当前阻塞点（用户会话外完成）

以下 3 项必须由用户在 Claude Code 会话外完成，因为 Windows 锁文件句柄 + 需要浏览器操作：

### 🔒 Prerequisite 1：重命名项目目录

**从**：`D:\个人内容\programs\NDL\`
**到**：`D:\个人内容\programs\project_noveldownloader\`

PowerShell 操作：
```powershell
cd "D:\个人内容\programs\"
Rename-Item -Path "NDL" -NewName "project_noveldownloader"
Test-Path "D:\个人内容\programs\project_noveldownloader\docs\superpowers\SESSION-STATE.md"
# 预期：True
```

### 🔒 Prerequisite 2：安装 `uv`（如果未装）

```powershell
uv --version   # 先探测；有输出就跳过下面的安装
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 🔒 Prerequisite 3：GitHub 仓库

去 <https://github.com/new> 创建：
- Owner：`makunxiang-cmd`
- Name：`project_noveldownloader`
- Public，**不勾选**任何 "Add README / .gitignore / license"
- 预期仓库 URL：`https://github.com/makunxiang-cmd/project_noveldownloader`

---

## 3. 下次会话启动协议

### 用户应做的事
1. 确认上面 3 项 Prerequisite 全部完成
2. 在 `D:\个人内容\programs\project_noveldownloader\` 启动新 Claude Code 会话
3. 发送启动指令，例如：

   > 开始执行 P0 scaffold 计划，使用 Subagent-Driven 模式

### Claude Code 应做的事（严格顺序）

```
1. Read docs/superpowers/SESSION-STATE.md（本文件）
2. Read docs/superpowers/plans/2026-04-20-ndl-p0-scaffold.md（完整计划）
3. 用户可能未读过 plan 摘要，简报一下 10 个任务的标题清单
4. 确认 Prerequisite 1/2/3 完成：
   - pwd 包含 "project_noveldownloader"（Prereq 1）
   - uv --version 返回版本号（Prereq 2）
   - 可选：验证 GitHub 仓库存在（`gh repo view makunxiang-cmd/project_noveldownloader`）
5. 若任一 Prerequisite 未完成 → 停下来问用户，不要盲目推进
6. 全部就绪 → 调用 superpowers:subagent-driven-development 技能
7. 按 Task 1 → 2 → ... → 10 顺序派发 subagent
   - 每个 Task 一个 fresh subagent（带上相关上下文与 TDD 步骤）
   - subagent 完成后，当前会话做代码审查（两阶段：first-pass + 确认）
   - 通过后提示用户 commit，然后进入下一个 Task
```

---

## 4. P0 计划的 10 个任务（速览）

| Task | 主题 | 核心文件 |
|---|---|---|
| 1 | 项目骨架 + `pyproject.toml` + 包初始化 | `pyproject.toml`, `src/ndl/__init__.py`, `src/ndl/__main__.py` |
| 2 | CLI 入口 + `--version` 测试驱动 | `src/ndl/cli/main.py`, `tests/unit/cli/test_main.py` |
| 3 | 质量工具链配置 | `ruff`/`mypy`/`pytest` in `pyproject.toml`, `.pre-commit-config.yaml` |
| 4 | `.gitignore` + `.editorconfig` + git 初始化 | `.gitignore`, `.editorconfig` |
| 5 | GitHub Actions CI 矩阵 | `.github/workflows/ci.yml`（3 OS × 3 Python） |
| 6 | Issue/PR 模板 | `.github/ISSUE_TEMPLATE/*.md`, `.github/PULL_REQUEST_TEMPLATE.md` |
| 7 | 法律与社区文件 | `LICENSE`（MIT）, `DISCLAIMER.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md` |
| 8 | 双语 README + MkDocs 骨架 | `README.md`, `README.zh-CN.md`, `docs/mkdocs.yml`, `docs/index.md` |
| 9 | 端到端验证（干净重装 + 全质量门禁） | 无新建文件，跑 ruff/mypy/pytest 全绿 |
| 10 | 首次推送到 GitHub + 打 tag `v0.1.0-dev0` | git remote add + push |

> 详细 TDD 步骤、代码片段、命令、预期输出均在 `docs/superpowers/plans/2026-04-20-ndl-p0-scaffold.md` 中。**Subagent 必须读取完整 plan，不能只依赖本摘要。**

---

## 5. 关键设计决策备忘

以下是设计阶段拍板的 14 条 ADR 核心决策（完整表在 spec 文档 §2）：

- **架构**：Clean/Onion（core ← infrastructure ← application ← interfaces）
- **HTTP 层**：`httpx` 默认，`playwright` 作为可选 extras `ndl[browser]`
- **解析**：`selectolax` 主，`lxml` 降级
- **规则**：YAML + Pydantic v2 schema，三层加载（builtin → remote repo → user custom）
- **存储**：SQLite + SQLAlchemy 2.0 Mapped style + WAL 模式
- **Web**：FastAPI + HTMX + Jinja2 + SSE，**零 Node.js**
- **调度**：APScheduler AsyncIO
- **CLI**：Typer + rich 进度条
- **EPUB**：`ebooklib`
- **日志**：`structlog`（JSON 结构化）
- **跨平台路径**：`platformdirs`
- **i18n**：`babel`（zh_CN + en_US）
- **包管理 / 构建**：`uv` + `hatchling`
- **质量工具**：`ruff` + `mypy --strict` + `pytest` + `pre-commit`

**伦理硬约束（不可协商）**：
- 严格尊重 `robots.txt`
- 限速：每域名默认 1 请求/秒，可配置但不能关
- 不内置：Cloudflare 绕过、商业平台（起点/番茄/晋江）、登录/验证码破解
- CI 中用 rule-lint 强制上述约束

---

## 6. P1–P7 路线图（仅提醒，不展开）

P0 完成后，按顺序规划：

- **P1** Core 领域模型 + Pydantic schema（1 周）
- **P2** HTTP fetcher + 规则引擎 + 第一条 demo 规则（1.5 周）
- **P3** 存储层（SQLAlchemy repo 模式） + Download 服务（1 周）
- **P4** CLI 命令补齐（search / download / convert / library）（1 周）
- **P5** EPUB / TXT / Markdown 转换器（1 周）
- **P6** FastAPI + HTMX Web UI + SSE 进度推送（1.5 周）
- **P7** APScheduler 增量更新 + 文档站点上线（1 周）

**MVP（P0–P4）预计 5–6 周；完整 P0–P7 约 8–10 周。**

每个阶段开始前重走 brainstorming → writing-plans → subagent-driven-development 流程。每份 plan 独立产出可运行软件。

---

## 7. 用户身份与偏好（持久化要点）

- **GitHub**：`makunxiang-cmd`
- **目标仓库**：`project_noveldownloader`
- **协作语言**：中文为主
- **流程偏好**：**先计划 → 问细节 → 再执行**；输出前要自检可靠性
- **决策风格**：评估完选项后倾向"按你推荐的来"，信任 Claude 的判断但要看到 trade-off
- **开源定位**：MIT，无商业目的，合规优先

---

## 8. 文件清单

会话结束时本目录应仅有以下内容（已核实）：

```
D:\个人内容\programs\NDL\          ← 即将重命名为 project_noveldownloader
├── .claude/
│   └── settings.local.json        ← 权限白名单，保留
├── .remember/
│   ├── logs/autonomous/           ← Claude Code 运行时，空目录，保留
│   └── tmp/                       ← 同上
└── docs/
    └── superpowers/
        ├── SESSION-STATE.md       ← 本文件
        ├── plans/
        │   └── 2026-04-20-ndl-p0-scaffold.md
        └── specs/
            └── 2026-04-20-ndl-design.md
```

**P0 执行后，根目录会新增**：`pyproject.toml`、`src/`、`tests/`、`.github/`、`README.md`、`LICENSE` 等（完整清单见 plan 文件）。
