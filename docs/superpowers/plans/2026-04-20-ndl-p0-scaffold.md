# NDL P0 脚手架实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `project_noveldownloader` 仓库的完整脚手架：git 仓库、Python 包骨架（`src/ndl`）、`ndl --version` 可运行的 CLI、全套质量门禁（ruff / mypy / pytest / pre-commit）、GitHub Actions CI、必需的法律与社区文件（LICENSE、DISCLAIMER、CONTRIBUTING 等）、MkDocs 文档站雏形。P0 完成后整个项目处于"全绿基线"，可作为 P1 MVP 开发的起点。

**Architecture:** 使用 `uv` 作为包管理器 + `hatchling` 作为构建后端，遵循 src-layout。Python 3.10+。CLI 由 `typer` 驱动，测试用 `pytest` + `typer.testing.CliRunner`。CI 在三平台（Ubuntu / macOS / Windows）× 三 Python 版本（3.10 / 3.11 / 3.12）矩阵运行。

**Tech Stack:** Python 3.10+ · uv · hatchling · typer · rich · pytest · ruff · mypy · pre-commit · GitHub Actions · MkDocs Material

**Reference:** 设计文档 `docs/superpowers/specs/2026-04-20-ndl-design.md`（此计划是该 spec 的第 0 阶段实现）

---

## 前置要求（会话外执行）

此计划依赖以下两项**不能在当前 Claude Code 会话中完成**的操作：

### Prerequisite 1：重命名本地项目目录

**为何在会话外**：当前会话的工作目录锁定在 `D:\个人内容\programs\NDL\`；在会话内重命名父目录会导致 Windows "access denied" 或后续绝对路径引用失效。

**操作**（用户手动）：

1. **关闭本 Claude Code 会话**
2. 打开 PowerShell，切换到项目父目录：
   ```powershell
   cd "D:\个人内容\programs\"
   ```
3. 重命名目录：
   ```powershell
   Rename-Item -Path "NDL" -NewName "project_noveldownloader"
   ```
4. 验证：
   ```powershell
   Test-Path "D:\个人内容\programs\project_noveldownloader\docs\superpowers\plans\2026-04-20-ndl-p0-scaffold.md"
   ```
   预期输出：`True`
5. 在新目录 `D:\个人内容\programs\project_noveldownloader\` 打开新的 Claude Code 会话继续本计划

### Prerequisite 2：安装 `uv` 包管理器

如未安装 `uv`，在 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

验证：

```bash
uv --version
```

预期输出类似 `uv 0.4.x` 或更新。

### Prerequisite 3：GitHub 仓库准备

在 github.com 创建空仓库 `makunxiang-cmd/project_noveldownloader`（不要勾选"添加 README/LICENSE/.gitignore"，我们会自己生成全部文件）。记录仓库 URL：`https://github.com/makunxiang-cmd/project_noveldownloader`。

---

## 文件结构规划（P0 将创建的完整文件列表）

```
project_noveldownloader/
├── .github/
│   ├── workflows/
│   │   └── ci.yml                    # GitHub Actions CI
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── rule_request.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── mkdocs.yml                    # MkDocs 配置
│   ├── index.md                      # 文档首页
│   ├── superpowers/
│   │   ├── specs/
│   │   │   └── 2026-04-20-ndl-design.md    # 已存在
│   │   └── plans/
│   │       └── 2026-04-20-ndl-p0-scaffold.md  # 本文件
│   ├── user-guide/                   # 暂留空 README.md 占位
│   ├── rule-authoring/               # 暂留空 README.md 占位
│   └── developer/                    # 暂留空 README.md 占位
├── src/
│   └── ndl/
│       ├── __init__.py               # __version__ = "0.1.0"
│       ├── __main__.py               # python -m ndl 入口
│       └── cli/
│           ├── __init__.py
│           └── main.py               # typer app；--version
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # pytest 共享 fixtures（初版为空壳）
│   └── unit/
│       ├── __init__.py
│       └── cli/
│           ├── __init__.py
│           └── test_main.py          # 测试 ndl --version
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── pyproject.toml                    # PEP 621；项目元信息 + 依赖 + ruff/mypy 配置
├── README.md                         # 英文主版
├── README.zh-CN.md                   # 中文版
├── LICENSE                           # MIT
├── DISCLAIMER.md                     # 法律免责 + 伦理守则
├── CONTRIBUTING.md                   # 贡献指南
├── CODE_OF_CONDUCT.md                # Contributor Covenant 2.1
├── SECURITY.md                       # 漏洞报告渠道
└── CHANGELOG.md                      # keep-a-changelog 格式
```

---

## 任务拆解

### Task 1：初始化 git 仓库 + 基础 `.gitignore`

**Files:**
- Create: `.gitignore`
- Initialize: `.git/`

- [ ] **Step 1: 初始化 git 仓库**

在项目根目录运行：

```bash
git init
git branch -M main
```

预期输出：`Initialized empty Git repository in .../project_noveldownloader/.git/`

- [ ] **Step 2: 设置远程仓库**

```bash
git remote add origin https://github.com/makunxiang-cmd/project_noveldownloader.git
git remote -v
```

预期输出：

```
origin  https://github.com/makunxiang-cmd/project_noveldownloader.git (fetch)
origin  https://github.com/makunxiang-cmd/project_noveldownloader.git (push)
```

- [ ] **Step 3: 创建 `.gitignore`**

文件路径：`.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtualenvs
.venv/
venv/
env/
ENV/

# uv (注意：uv.lock 要提交到仓库以锁定依赖，所以此处不列入忽略)
.uv/

# Testing & coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
coverage.xml
*.cover

# Type checking
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini

# NDL runtime data (shouldn't be in repo)
*.db
*.sqlite
*.sqlite3
*.log
.ndl/

# Docs build
site/

# Playwright
.cache/ms-playwright/

# Python versions
.python-version
```

**注意**：`uv.lock` 一般要提交到仓库（锁定依赖版本），下一步中我们将从忽略名单中移除。此处先加入防止 uv init 生成的 lock 被意外忽略。

- [ ] **Step 4: 从 `.gitignore` 移除 `uv.lock`**

编辑 `.gitignore`，删除 `uv.lock` 那一行（或将其改为注释 `# uv.lock  # we commit this`）。

- [ ] **Step 5: 验证 `.gitignore` 生效**

```bash
git status
```

预期输出：

```
On branch main
No commits yet
Untracked files:
  .gitignore
```

- [ ] **Step 6: 初次提交（仅 .gitignore，建立主分支）**

```bash
git add .gitignore
git commit -m "chore: initialize repo with .gitignore"
```

预期输出：`[main (root-commit) xxxxxxx] chore: initialize repo with .gitignore`

---

### Task 2：创建社区与法律文件

**Files:**
- Create: `LICENSE`
- Create: `DISCLAIMER.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`

- [ ] **Step 1: 创建 `LICENSE`（MIT）**

文件路径：`LICENSE`

```
MIT License

Copyright (c) 2026 makunxiang-cmd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: 创建 `DISCLAIMER.md`**

文件路径：`DISCLAIMER.md`

```markdown
# DISCLAIMER · 法律与伦理声明

## 中文版本

### 用途声明

NDL（NOVELDOWNLOADER）仅用于以下场景：

- 个人学习与教育研究
- 合法授权内容的本地备份
- 公有领域作品的采集与整理
- 自建网站、CC 许可内容的归档

### 用户责任

使用者须**自行承担**使用本软件所产生的任何法律责任。在使用 NDL 前，您须确认：

- 您对目标内容拥有合法的访问权限
- 您的使用符合所在司法管辖区的法律规定
- 您尊重目标网站的服务条款（ToS）与 `robots.txt`
- 您不会将 NDL 用于绕过付费墙、破解 DRM、或访问盗版聚合站点

### 软件立场

NDL 项目**不内置**以下能力：

- 对商业正版小说站（起点、番茄、晋江、七猫等）的规则适配
- 账号登录、Cookie 注入、CAPTCHA 自动识别
- Cloudflare / WAF 绕过机制
- 代理池 / IP 轮换

### DMCA 响应

如您认为本仓库或其分发的规则文件侵犯了您的版权，请通过 `SECURITY.md` 列出的渠道联系维护者。我们将在 **7 个工作日内**响应。

### 伦理守则（社区契约）

所有贡献到本仓库的规则文件必须：

1. 默认尊重目标站点的 `robots.txt`
2. `rate_limit.min_interval_ms >= 500`，`max_concurrency <= 3`
3. User-Agent 字段包含 NDL 标识与项目主页 URL
4. 不针对盗版聚合站 / 商业付费内容

违反上述约束的 PR 将被拒绝。

---

## English Version

### Purpose

NDL (NOVELDOWNLOADER) is intended for:

- Personal study and educational research
- Local backups of legally-authorized content
- Archiving of public-domain works
- Self-hosted sites and CC-licensed content

### User Responsibility

Users assume **full legal responsibility** for their use of this software. Before using NDL, you must confirm that:

- You have lawful access rights to the target content
- Your use complies with your jurisdiction's laws
- You respect the target website's Terms of Service and `robots.txt`
- You will not use NDL to circumvent paywalls, break DRM, or access piracy aggregators

### Project Stance

NDL does **not** bundle:

- Rules for commercial novel platforms (Qidian, Fanqie, Jinjiang, Qimao, etc.)
- Account login, cookie injection, or automated CAPTCHA solving
- Cloudflare / WAF bypass mechanisms
- Proxy pools / IP rotation

### DMCA Response

If you believe this repository or its distributed rule files infringe your copyright, please contact the maintainer via the channels listed in `SECURITY.md`. We will respond within **7 business days**.

### Community Ethics

Rule files contributed to this repository must:

1. Respect the target site's `robots.txt` by default
2. Use `rate_limit.min_interval_ms >= 500` and `max_concurrency <= 3`
3. Include the NDL identifier and project homepage URL in the User-Agent
4. Not target piracy aggregators or commercial paywalled content

Pull requests violating these constraints will be declined.
```

- [ ] **Step 3: 创建 `CODE_OF_CONDUCT.md`**

文件路径：`CODE_OF_CONDUCT.md`

使用 Contributor Covenant 2.1 标准模板（短版）：

```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity
and orientation.

## Our Standards

Examples of behavior that contributes to a positive environment:

* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes
* Focusing on what is best for the overall community

Examples of unacceptable behavior:

* Use of sexualized language or imagery, and sexual attention of any kind
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or email address,
  without their explicit permission

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the project maintainers at the email listed in `SECURITY.md`.
All complaints will be reviewed and investigated promptly and fairly.

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.1, available at
<https://www.contributor-covenant.org/version/2/1/code_of_conduct.html>.

[homepage]: https://www.contributor-covenant.org
```

- [ ] **Step 4: 创建 `SECURITY.md`**

文件路径：`SECURITY.md`

```markdown
# Security & Reporting Policy

## Supported Versions

Only the latest minor release on PyPI receives security fixes. Pre-release versions (0.x) may not be maintained once a newer 0.y is published.

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

Report privately by:

1. Opening a [GitHub Security Advisory draft](https://github.com/makunxiang-cmd/project_noveldownloader/security/advisories/new) (preferred)
2. Emailing the maintainer: (TODO: add contact email before v0.1 release)

Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- (Optional) Suggested fix

We aim to:

- Acknowledge within **48 hours**
- Provide an initial assessment within **7 days**
- Release a fix within **30 days** for critical issues

## DMCA / Copyright Notices

For copyright concerns regarding bundled rule files or distributed content, use the same channels above. See `DISCLAIMER.md` for our stance.
```

**注意**：`SECURITY.md` 中 "TODO: add contact email before v0.1 release" 是**有意保留**的占位。P6（v0.1 发布前）必须决定联系邮箱。

- [ ] **Step 5: 创建 `CONTRIBUTING.md`**

文件路径：`CONTRIBUTING.md`

```markdown
# Contributing to NDL

Thank you for your interest in contributing!

## Quick Start

```bash
# Clone
git clone https://github.com/makunxiang-cmd/project_noveldownloader.git
cd project_noveldownloader

# Install uv (https://docs.astral.sh/uv/)
# Then sync dependencies:
uv sync --all-extras

# Run tests
uv run pytest

# Run linter/formatter
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/ndl

# Install pre-commit hooks (runs linters before each commit)
uv run pre-commit install
```

## What to Contribute

### 1. New Site Rules (Most Welcome)

NDL is rule-driven. Adding support for a new site does NOT require writing Python.

1. Fork the repo
2. Create a YAML rule under `src/ndl/builtin_rules/<your_site>.yaml` (for PR) or `~/.ndl/rules/custom/` (for personal use)
3. Add a contract test fixture under `tests/contract/fixtures/<rule_id>/` containing `index.html`, `chapter.html`, `expected.json`
4. Run `uv run pytest tests/contract/ -k <rule_id>`
5. Submit PR

Rules violating `DISCLAIMER.md` § "Community Ethics" will be declined.

### 2. Bug Reports

Use the bug report template. Include:

- NDL version (`ndl --version`)
- OS + Python version
- Minimal URL / YAML / command to reproduce
- Full traceback with `--log-level debug`

### 3. Feature Requests

Open a feature request issue and describe:

- The problem you're trying to solve (not the solution)
- Alternative approaches you considered
- Whether you'd be willing to implement it

### 4. Code Contributions

1. Open an issue to discuss before large PRs (> 200 LOC)
2. Follow the existing architecture (see `docs/developer/architecture.md`)
3. TDD: every PR with code must include tests
4. All CI checks must pass

## Development Conventions

- **Formatting**: `ruff format` (configured in `pyproject.toml`)
- **Linting**: `ruff check` must pass
- **Typing**: `mypy --strict` on `src/ndl`
- **Testing**: `pytest`; aim for 80%+ coverage; 90%+ on `core/`, `rules/`, `converters/`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`

## License

By contributing, you agree your contributions will be licensed under the MIT License.
```

- [ ] **Step 6: 创建 `CHANGELOG.md`**

文件路径：`CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- P0 scaffold: project structure, CI, linting/type/test tooling, MkDocs skeleton
- `ndl --version` command

[Unreleased]: https://github.com/makunxiang-cmd/project_noveldownloader/commits/main
```

- [ ] **Step 7: 提交**

```bash
git add LICENSE DISCLAIMER.md CODE_OF_CONDUCT.md SECURITY.md CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: add license, disclaimer, community files"
```

---

### Task 3：创建 README（中英双语）

**Files:**
- Create: `README.md`
- Create: `README.zh-CN.md`
- Create: `.editorconfig`

- [ ] **Step 1: 创建 `README.md`（英文主版）**

文件路径：`README.md`

```markdown
# NDL — NOVELDOWNLOADER

> Rule-driven Chinese novel downloader and format converter

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

🇨🇳 [简体中文](README.zh-CN.md)

## Status

🚧 **Under active development** — currently in P0 scaffold stage. First release (v0.1) targets MVP features (download + TXT/EPUB convert + library management).

## What It Does (Planned)

- **Download** Chinese web novels from static HTML sites (Playwright for JS-heavy sites as an optional extra)
- **Convert** between TXT and EPUB formats, standalone or post-download
- **Library** management with SQLite persistence; track ongoing novels and check for updates
- **Search** across multiple sites via rule-defined search endpoints
- **Rule-driven** architecture — add new sites by writing YAML, not Python
- **CLI + local Web UI** — use either, both share state

## Non-Goals

NDL does not and will not:

- Support commercial platforms (Qidian, Fanqie, Jinjiang, Qimao)
- Bypass paywalls, Cloudflare, CAPTCHAs, or DRM
- Include login/account features or proxy pools

See [`DISCLAIMER.md`](DISCLAIMER.md) for full ethics/legal stance.

## Install (coming soon)

```bash
# Once v0.1 is on PyPI:
pip install ndl              # Core (HTTP fetcher only)
pip install ndl[browser]     # With Playwright for JS-rendered sites
```

## Usage Preview (coming soon)

```bash
ndl download <url> -o book.epub        # Download and convert
ndl convert book.txt -o book.epub      # Standalone conversion
ndl library list                        # Browse downloaded novels
ndl update --all                        # Check for new chapters
ndl serve                               # Start local Web UI at http://localhost:8000
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Rule contributions especially welcome — no Python needed.

## License

[MIT](LICENSE)
```

- [ ] **Step 2: 创建 `README.zh-CN.md`**

文件路径：`README.zh-CN.md`

```markdown
# NDL — NOVELDOWNLOADER

> 规则驱动的中文小说下载与格式转换工具

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

🇬🇧 [English](README.md)

## 项目状态

🚧 **开发中** — 当前处于 P0 脚手架阶段。首发版本 (v0.1) 将包含 MVP 功能（下载 + TXT/EPUB 转换 + 书库管理）。

## 功能（规划中）

- **下载**静态 HTML 小说站点（可选 Playwright 支持 JS 渲染页面）
- **格式转换** TXT ↔ EPUB，可独立使用或下载后自动转换
- **书库管理**：SQLite 持久化，追更连载小说、增量更新
- **多源搜索**：规则文件中定义的搜索端点聚合
- **规则驱动**架构——新增站点只需写 YAML，不需 Python
- **CLI + 本地 Web UI** 双模式，共享数据

## 明确不做

- 不支持商业正版平台（起点、番茄、晋江、七猫）
- 不绕过付费墙、Cloudflare、CAPTCHA、DRM
- 不提供账号登录、代理池等功能

详见 [`DISCLAIMER.md`](DISCLAIMER.md)。

## 安装（即将推出）

```bash
# v0.1 发布后：
pip install ndl              # 核心（仅 HTTP fetcher）
pip install ndl[browser]     # 含 Playwright，支持 JS 渲染站点
```

## 使用预览（即将推出）

```bash
ndl download <url> -o book.epub        # 下载并转换
ndl convert book.txt -o book.epub      # 独立转换
ndl library list                        # 浏览已下载的小说
ndl update --all                        # 检查所有连载更新
ndl serve                               # 启动本地 Web UI 于 http://localhost:8000
```

## 贡献

参见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。尤其欢迎**站点规则贡献**，无需 Python 编程。

## 许可证

[MIT](LICENSE)
```

- [ ] **Step 3: 创建 `.editorconfig`**

文件路径：`.editorconfig`

```ini
# EditorConfig is awesome: https://EditorConfig.org

root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.{md,yml,yaml,json,toml}]
indent_size = 2

[*.{html,css,js}]
indent_size = 2

[Makefile]
indent_style = tab
```

- [ ] **Step 4: 提交**

```bash
git add README.md README.zh-CN.md .editorconfig
git commit -m "docs: add bilingual README and editorconfig"
```

---

### Task 4：创建 `pyproject.toml` 与 Python 包骨架

**Files:**
- Create: `pyproject.toml`
- Create: `src/ndl/__init__.py`
- Create: `src/ndl/__main__.py`
- Create: `src/ndl/cli/__init__.py`
- Create: `src/ndl/cli/main.py`

- [ ] **Step 1: 创建 `pyproject.toml`（P0 最小依赖集）**

文件路径：`pyproject.toml`

```toml
[project]
name = "ndl"
version = "0.1.0.dev0"
description = "NOVELDOWNLOADER: rule-driven Chinese novel downloader and format converter"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "makunxiang-cmd" }]
requires-python = ">=3.10"
keywords = ["novel", "downloader", "chinese", "epub", "crawler"]
classifiers = [
  "Development Status :: 2 - Pre-Alpha",
  "Intended Audience :: End Users/Desktop",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Internet :: WWW/HTTP",
  "Topic :: Text Processing :: Markup",
]

# P0 依赖：保持最小，仅够 `ndl --version` 运行。
# 后续 P1 起会逐步添加 httpx / pydantic / SQLAlchemy 等。
dependencies = [
  "typer>=0.12",
  "rich>=13.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pytest-cov>=4.1",
  "ruff>=0.3",
  "mypy>=1.8",
  "pre-commit>=3.6",
]

[project.scripts]
ndl = "ndl.cli.main:app"

[project.urls]
Homepage = "https://github.com/makunxiang-cmd/project_noveldownloader"
Repository = "https://github.com/makunxiang-cmd/project_noveldownloader"
Issues = "https://github.com/makunxiang-cmd/project_noveldownloader/issues"
Changelog = "https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/CHANGELOG.md"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ndl"]

# ───── Ruff 配置 ─────
[tool.ruff]
line-length = 100
target-version = "py310"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
  "E",    # pycodestyle errors
  "W",    # pycodestyle warnings
  "F",    # pyflakes
  "I",    # isort
  "B",    # flake8-bugbear
  "C4",   # flake8-comprehensions
  "UP",   # pyupgrade
  "N",    # pep8-naming
  "SIM",  # flake8-simplify
  "RUF",  # ruff-specific
]
ignore = [
  "E501",  # line-too-long (format handles it)
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["B011"]  # allow assert False in tests

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

# ───── Mypy 配置 ─────
[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_return_any = true
show_error_codes = true
files = ["src/ndl"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false

# ───── Pytest 配置 ─────
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = [
  "-ra",
  "--strict-markers",
  "--strict-config",
  "--import-mode=importlib",
]
asyncio_mode = "auto"
markers = [
  "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]

# ───── Coverage 配置 ─────
[tool.coverage.run]
source = ["src/ndl"]
branch = true

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "def __repr__",
  "raise NotImplementedError",
  "if TYPE_CHECKING:",
  "\\.\\.\\.",
]
fail_under = 80
```

- [ ] **Step 2: 创建 `src/ndl/__init__.py`**

文件路径：`src/ndl/__init__.py`

```python
"""NDL — NOVELDOWNLOADER: rule-driven Chinese novel downloader."""

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
```

- [ ] **Step 3: 创建 `src/ndl/__main__.py`**

文件路径：`src/ndl/__main__.py`

```python
"""Allow `python -m ndl` invocation equivalent to the `ndl` script."""

from ndl.cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 4: 创建 `src/ndl/cli/__init__.py`**

文件路径：`src/ndl/cli/__init__.py`

```python
"""CLI package for NDL."""
```

- [ ] **Step 5: 创建 `src/ndl/cli/main.py`（先写骨架，下一个 Task 用 TDD 补 --version）**

文件路径：`src/ndl/cli/main.py`

```python
"""Typer CLI entry point for NDL."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="ndl",
    help="NDL — NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _callback() -> None:
    """NDL — rule-driven Chinese novel downloader and format converter."""
```

- [ ] **Step 6: 运行 `uv sync` 建立虚拟环境与 lock 文件**

```bash
uv sync --all-extras
```

预期输出：

```
Using Python 3.12.x
Creating virtualenv at: .venv
...
Resolved XX packages in XXXms
Installed XX packages in XXXms
```

并且应生成 `.venv/` 目录与 `uv.lock` 文件。

- [ ] **Step 7: 验证包可安装且 CLI 脚本已注册**

```bash
uv run ndl
```

预期输出（typer 因 `no_args_is_help=True` 自动输出帮助）：

```
Usage: ndl [OPTIONS] COMMAND [ARGS]...

  NDL — rule-driven Chinese novel downloader and format converter.

Options:
  --help  Show this message and exit.
```

- [ ] **Step 8: 提交**

```bash
git add pyproject.toml uv.lock src/ndl/
git commit -m "feat: scaffold ndl python package with typer CLI"
```

---

### Task 5：TDD 实现 `ndl --version`

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/cli/__init__.py`
- Create: `tests/unit/cli/test_main.py`
- Modify: `src/ndl/cli/main.py`

- [ ] **Step 1: 创建测试包结构（空 `__init__.py` 文件）**

文件路径：`tests/__init__.py` — 空文件
文件路径：`tests/unit/__init__.py` — 空文件
文件路径：`tests/unit/cli/__init__.py` — 空文件

这 3 个文件内容均为空（0 字节）。

- [ ] **Step 2: 创建 `tests/conftest.py`（P0 阶段最小骨架）**

文件路径：`tests/conftest.py`

```python
"""Shared pytest fixtures for NDL test suite.

P0: empty scaffold. Fixtures will be added as tests require them.
"""

from __future__ import annotations
```

- [ ] **Step 3: 先写失败的测试**

文件路径：`tests/unit/cli/test_main.py`

```python
"""Tests for the NDL CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from ndl import __version__
from ndl.cli.main import app

runner = CliRunner()


def test_version_flag_outputs_version_string() -> None:
    """`ndl --version` prints the package version and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.stdout
    assert __version__ in result.stdout


def test_version_short_flag_outputs_version_string() -> None:
    """`ndl -V` is the short form of --version."""
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0, result.stdout
    assert __version__ in result.stdout
```

- [ ] **Step 4: 运行测试，确认失败**

```bash
uv run pytest tests/unit/cli/test_main.py -v
```

预期输出中应有：

```
FAILED tests/unit/cli/test_main.py::test_version_flag_outputs_version_string
FAILED tests/unit/cli/test_main.py::test_version_short_flag_outputs_version_string
```

原因：`--version` 选项未实现（typer 会返回非零退出码 + "No such option" 错误）。

- [ ] **Step 5: 实现 `--version` 以让测试通过**

将 `src/ndl/cli/main.py` 全文替换为：

```python
"""Typer CLI entry point for NDL."""

from __future__ import annotations

import typer

from ndl import __version__

app = typer.Typer(
    name="ndl",
    help="NDL — NOVELDOWNLOADER: rule-driven Chinese novel downloader.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    """Print version and exit when --version flag is supplied."""
    if value:
        typer.echo(f"NDL {__version__}")
        raise typer.Exit()


@app.callback()
def _callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """NDL — rule-driven Chinese novel downloader and format converter."""
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
uv run pytest tests/unit/cli/test_main.py -v
```

预期输出：

```
tests/unit/cli/test_main.py::test_version_flag_outputs_version_string PASSED
tests/unit/cli/test_main.py::test_version_short_flag_outputs_version_string PASSED

======= 2 passed in X.XXs =======
```

- [ ] **Step 7: 手动验证 CLI 在真实终端的行为**

```bash
uv run ndl --version
```

预期输出：

```
NDL 0.1.0.dev0
```

- [ ] **Step 8: 提交**

```bash
git add tests/ src/ndl/cli/main.py
git commit -m "feat(cli): add --version / -V flag with TDD tests"
```

---

### Task 6：配置 pre-commit、Ruff lint/format

**Files:**
- Create: `.pre-commit-config.yaml`
- Verify: `pyproject.toml` ruff section (already present from Task 4)

- [ ] **Step 1: 创建 `.pre-commit-config.yaml`**

文件路径：`.pre-commit-config.yaml`

```yaml
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: check-merge-conflict
      - id: mixed-line-ending
        args: ["--fix=lf"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.7
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        files: ^src/ndl/
        additional_dependencies:
          - "typer>=0.12"
          - "rich>=13.7"
```

- [ ] **Step 2: 手动运行 ruff 格式化，修正任何既有格式差异**

```bash
uv run ruff format .
uv run ruff check --fix .
```

预期：可能对刚创建的文件做微小调整（如缩进、引号风格）。再次运行应无变动：

```bash
uv run ruff check .
```

预期输出：`All checks passed!`

- [ ] **Step 3: 运行 mypy 验证类型**

```bash
uv run mypy src/ndl
```

预期输出：`Success: no issues found in X source files`

- [ ] **Step 4: 安装 pre-commit hooks 到本地 git**

```bash
uv run pre-commit install
```

预期输出：`pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 5: 对所有已纳管文件跑一遍 pre-commit 以确认配置正确**

```bash
uv run pre-commit run --all-files
```

预期：**首次运行**可能修正一些末尾空白、换行符；之后再运行应全绿。如首次有修正，将修正内容也加入下一步的提交。

- [ ] **Step 6: 提交**

```bash
git add .pre-commit-config.yaml
# 如果 Step 5 修正了其它文件，也一并加入：
git add -u
git commit -m "chore: add pre-commit hooks (ruff + mypy + misc)"
```

---

### Task 7：建立 GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/rule_request.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: 创建 `.github/workflows/ci.yml`**

文件路径：`.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint + Format + Type
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Ruff lint
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy
        run: uv run mypy src/ndl

  test:
    name: Test (Py${{ matrix.python }} on ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python ${{ matrix.python }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run pytest
        run: uv run pytest --cov=ndl --cov-report=xml --cov-report=term

      - name: Upload coverage (ubuntu + 3.12 only)
        if: matrix.os == 'ubuntu-latest' && matrix.python == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.xml
```

- [ ] **Step 2: 创建 `.github/ISSUE_TEMPLATE/bug_report.md`**

文件路径：`.github/ISSUE_TEMPLATE/bug_report.md`

```markdown
---
name: Bug report
about: Report a defect in NDL
title: "[bug] "
labels: bug
assignees: ''
---

## Summary

<!-- One-sentence description of the bug. -->

## Environment

- NDL version: `ndl --version` →
- OS + version:
- Python version: `python --version` →
- Installed extras (e.g., `[browser]`):

## Steps to Reproduce

1.
2.
3.

## Expected Behavior

<!-- What you expected to happen. -->

## Actual Behavior

<!-- What actually happened, including any error messages. -->

## Full Traceback

Run the failing command with `--log-level debug` and paste here:

```
(paste traceback)
```

## Additional Context

<!-- Rule YAML being used, URL (redacted if needed), screenshots, etc. -->
```

- [ ] **Step 3: 创建 `.github/ISSUE_TEMPLATE/rule_request.md`**

文件路径：`.github/ISSUE_TEMPLATE/rule_request.md`

```markdown
---
name: Rule request
about: Request a new site rule or report a broken rule
title: "[rule] "
labels: rule
assignees: ''
---

## Site

- Site name (pinyin or English):
- Example URL (redacted if you prefer):

## Type

- [ ] New rule request (site not yet supported)
- [ ] Broken rule (rule exists but fails)

## Ethics Check

- [ ] The site is NOT a commercial platform (Qidian / Fanqie / Jinjiang / Qimao / 7mao / etc.)
- [ ] The site does NOT have a paywall for the content
- [ ] I've reviewed `DISCLAIMER.md` and confirm this request complies

Rule requests violating the above will be declined. See `DISCLAIMER.md`.

## For Broken Rules

- Which rule id: (see `ndl rules list`)
- What changed: (site redesign? specific selector broken?)
- Sample HTML fixture (attach `index.html` and `chapter.html` from browser "save as"):

## Additional Context
```

- [ ] **Step 4: 创建 `.github/ISSUE_TEMPLATE/feature_request.md`**

文件路径：`.github/ISSUE_TEMPLATE/feature_request.md`

```markdown
---
name: Feature request
about: Suggest a new feature or enhancement
title: "[feat] "
labels: enhancement
assignees: ''
---

## Problem

<!-- What user problem are you trying to solve? -->

## Proposed Solution

<!-- Your preferred approach. Code/mockup/ascii diagrams welcome. -->

## Alternatives Considered

<!-- What else you thought about. -->

## Willing to Implement?

- [ ] Yes, I'd like to contribute the implementation
- [ ] No, just suggesting
```

- [ ] **Step 5: 创建 `.github/PULL_REQUEST_TEMPLATE.md`**

文件路径：`.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Summary

<!-- What does this PR do? -->

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Rule addition/update
- [ ] Documentation
- [ ] Refactor / chore

## Related Issues

<!-- Fixes #123 / Closes #456 / Refs #789 -->

## Checklist

- [ ] Tests added / updated for new behavior
- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run mypy src/ndl` passes
- [ ] `uv run pytest` passes
- [ ] CHANGELOG.md updated (for user-facing changes)
- [ ] Documentation updated (if behavior/API changed)

## For Rule Contributions

- [ ] Contract fixtures added under `tests/contract/fixtures/<rule_id>/`
- [ ] `rate_limit.min_interval_ms >= 500`
- [ ] `max_concurrency <= 3`
- [ ] User-Agent includes NDL identifier
- [ ] If `ignore_robots: true`, `ignore_justification` is provided
- [ ] Target site is not commercial/paywalled (see `DISCLAIMER.md`)
```

- [ ] **Step 6: 提交**

```bash
git add .github/
git commit -m "ci: add GitHub Actions CI + issue/PR templates"
```

---

### Task 8：创建 MkDocs 文档站骨架

**Files:**
- Create: `docs/mkdocs.yml`
- Create: `docs/index.md`
- Create: `docs/user-guide/README.md`
- Create: `docs/rule-authoring/README.md`
- Create: `docs/developer/README.md`

- [ ] **Step 1: 创建 `docs/mkdocs.yml`**

文件路径：`docs/mkdocs.yml`

```yaml
site_name: NDL — NOVELDOWNLOADER
site_description: Rule-driven Chinese novel downloader and format converter
site_url: https://makunxiang-cmd.github.io/project_noveldownloader/
repo_url: https://github.com/makunxiang-cmd/project_noveldownloader
repo_name: makunxiang-cmd/project_noveldownloader
edit_uri: edit/main/docs/
docs_dir: .

theme:
  name: material
  language: en
  features:
    - content.code.copy
    - content.code.annotate
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.footer
    - search.highlight
    - search.suggest
    - toc.follow
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.tabbed:
      alternate_style: true
  - tables
  - toc:
      permalink: true

nav:
  - Home: index.md
  - User Guide: user-guide/README.md
  - Rule Authoring: rule-authoring/README.md
  - Developer: developer/README.md
```

- [ ] **Step 2: 创建 `docs/index.md`**

文件路径：`docs/index.md`

```markdown
# NDL — NOVELDOWNLOADER

Welcome to the NDL documentation.

**Status:** Under active development (P0 scaffold stage). Full content will be populated as the project advances through its [roadmap](../README.md#status).

## Sections

- [User Guide](user-guide/README.md) — installation, CLI reference, Web UI walkthrough, configuration
- [Rule Authoring](rule-authoring/README.md) — writing YAML rules to support new sites
- [Developer](developer/README.md) — architecture, contribution workflow, rule contract tests

## See Also

- [Design Specification](superpowers/specs/2026-04-20-ndl-design.md) — the complete design document

## License

NDL is released under the [MIT License](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/LICENSE). See also the [Disclaimer](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/DISCLAIMER.md) for legal and ethical stance.
```

- [ ] **Step 3: 为三个子目录各创建 `README.md` 占位**

文件路径：`docs/user-guide/README.md`

```markdown
# User Guide

Coming with P1 MVP release. Planned sections:

- Installation
- CLI reference
- Web UI walkthrough
- Configuration (`~/.ndl/config.toml`)
- Troubleshooting
```

文件路径：`docs/rule-authoring/README.md`

```markdown
# Rule Authoring Guide

Coming with P1 MVP release. Planned sections:

- Writing your first rule (step-by-step)
- Selector DSL reference
- Full rule schema reference
- Testing rules locally (contract fixtures)
- Submitting a rule PR
```

文件路径：`docs/developer/README.md`

```markdown
# Developer Guide

Coming with P1 MVP release. Planned sections:

- Architecture overview (matches `docs/superpowers/specs/2026-04-20-ndl-design.md`)
- Development workflow (uv, ruff, mypy, pytest)
- Adding a new fetcher / parser / converter
- Rule contract tests explained
- Release process
```

- [ ] **Step 4: 提交**

```bash
git add docs/
git commit -m "docs: add mkdocs skeleton with material theme"
```

---

### Task 9：端到端验证

**Files:** (无新建)

- [ ] **Step 1: 从干净状态重装依赖（模拟新克隆者体验）**

Unix / macOS / git-bash：
```bash
rm -rf .venv
uv sync --all-extras
```

Windows PowerShell：
```powershell
Remove-Item -Recurse -Force .venv
uv sync --all-extras
```

Windows cmd：
```cmd
rmdir /s /q .venv
uv sync --all-extras
```

预期：`.venv/` 重新创建，所有依赖安装成功。

- [ ] **Step 2: 跑完整质量门禁**

```bash
uv run ruff check .
```

预期：`All checks passed!`

```bash
uv run ruff format --check .
```

预期：`X files already formatted`

```bash
uv run mypy src/ndl
```

预期：`Success: no issues found in X source files`

```bash
uv run pytest -v
```

预期：

```
tests/unit/cli/test_main.py::test_version_flag_outputs_version_string PASSED
tests/unit/cli/test_main.py::test_version_short_flag_outputs_version_string PASSED

======= 2 passed in X.XXs =======
```

- [ ] **Step 3: 手动跑 CLI**

```bash
uv run ndl --version
```

预期：`NDL 0.1.0.dev0`

```bash
uv run ndl --help
```

预期：

```
Usage: ndl [OPTIONS] COMMAND [ARGS]...

  NDL — rule-driven Chinese novel downloader and format converter.

Options:
  -V, --version  Show version and exit.
  --help         Show this message and exit.
```

```bash
uv run python -m ndl --version
```

预期：`NDL 0.1.0.dev0`（验证 `__main__.py` 入口也工作）

- [ ] **Step 4: 检查所有文件已被 git 追踪**

```bash
git status
```

预期输出：

```
On branch main
nothing to commit, working tree clean
```

- [ ] **Step 5: 查看提交历史**

```bash
git log --oneline
```

预期输出（顺序从新到旧）：

```
xxxxxxx docs: add mkdocs skeleton with material theme
xxxxxxx ci: add GitHub Actions CI + issue/PR templates
xxxxxxx chore: add pre-commit hooks (ruff + mypy + misc)
xxxxxxx feat(cli): add --version / -V flag with TDD tests
xxxxxxx feat: scaffold ndl python package with typer CLI
xxxxxxx docs: add bilingual README and editorconfig
xxxxxxx docs: add license, disclaimer, community files
xxxxxxx chore: initialize repo with .gitignore
```

---

### Task 10：首次推送到 GitHub + 验证 CI

**Files:** (无文件变更)

- [ ] **Step 1: 推送到 GitHub**

```bash
git push -u origin main
```

预期：推送成功，GitHub 显示 8 个提交。

- [ ] **Step 2: 在浏览器打开 GitHub Actions 页面验证 CI**

访问：`https://github.com/makunxiang-cmd/project_noveldownloader/actions`

预期：
- 一个 CI workflow 运行被触发
- `lint` job 通过
- `test` 矩阵 9 个组合（3 OS × 3 Python）全部通过

如果某个组合失败：记录错误日志，作为后续修复任务（常见 Windows 特有问题：行尾、路径分隔符）。

- [ ] **Step 3: 将 CHANGELOG.md 的 "Unreleased" 标记为 P0 完成状态**

修改 `CHANGELOG.md`，在 `## [Unreleased]` 下追加（或修订）：

```markdown
## [Unreleased]

### Added
- P0 scaffold complete: project structure, CI, linting/type/test tooling, MkDocs skeleton
- `ndl --version` / `ndl -V` CLI command
- Community files: LICENSE (MIT), DISCLAIMER, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- Issue templates (bug / rule / feature) and PR template
- GitHub Actions CI: lint + format + mypy + test matrix (3 OS × 3 Python)

[Unreleased]: https://github.com/makunxiang-cmd/project_noveldownloader/commits/main
```

- [ ] **Step 4: 提交并推送**

```bash
git add CHANGELOG.md
git commit -m "docs: mark P0 scaffold complete in CHANGELOG"
git push
```

- [ ] **Step 5: 在 GitHub 仓库设置中启用以下（手动步骤，非 CLI）**

访问 `https://github.com/makunxiang-cmd/project_noveldownloader/settings`：

1. **General** → 设置仓库描述：`Rule-driven Chinese novel downloader and format converter`
2. **General** → 设置主页 URL：`https://makunxiang-cmd.github.io/project_noveldownloader/`（P6 时 MkDocs 发布后生效）
3. **Branches** → 添加 `main` 分支保护规则：
   - 勾选 "Require a pull request before merging"
   - 勾选 "Require status checks to pass before merging" → 选择 `lint` 和 `test` 所有 matrix 组合
4. **Actions → General** → 确认允许 Actions 运行
5. **Security → Code security and analysis** → 启用 Dependabot alerts + security updates

---

## 完成标准（Definition of Done）

P0 脚手架完成 = 以下全部成立：

- [x] 本地 `.venv` 可从空状态重建（`uv sync --all-extras`）
- [x] `uv run ndl --version` 输出 `NDL 0.1.0.dev0`
- [x] `uv run pytest` 通过（2 个测试）
- [x] `uv run ruff check .` 通过
- [x] `uv run ruff format --check .` 通过
- [x] `uv run mypy src/ndl` 通过
- [x] `uv run pre-commit run --all-files` 通过
- [x] GitHub Actions CI 在 `lint` + 9 个 `test` 矩阵组合全绿
- [x] GitHub 仓库主分支受保护（PR + 必需状态检查）
- [x] 8+ 个有意义的提交历史，主题清晰

## 下一步

P0 完成后，进入 **P1 MVP 实现**。P1 计划将在独立的文档中编写，范围包括：

- `core/` 领域模型与异常树
- `rules/` YAML schema + 加载器 + 选择器 DSL 执行
- `fetchers/http.py` + 限速 + 重试 + robots.txt
- `parsers/html_index.py` + `html_chapter.py`
- `converters/txt_writer.py` + `epub_writer.py`
- `application/services/download.py` + `convert.py`
- `cli/commands/download.py` + `convert.py`
- 2 条示例内置规则 + 规则契约测试基础设施
- 中文 i18n 基础设施（babel）

**P1 启动条件**：P0 所有"完成标准"打勾，GitHub CI 绿色运行一周以上稳定。
