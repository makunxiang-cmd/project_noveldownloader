# NDL - NOVELDOWNLOADER

> 规则驱动的中文小说下载与格式转换工具

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[English](README.md)

## 项目状态

v0.2.0 是最新已发布版本，发行在 PyPI 上的名字是 `ndl-storykit`。当前源码已回到
下一轮开发版本 `0.3.0.dev0`。已实现范围包括：下载、TXT/EPUB 转换、书库管理、搜索、规则更新、
支持规则选择的可选浏览器渲染、本地 Web UI，以及可审计的打包校验。当前接手快照见
`docs/superpowers/SESSION-STATE.md`。

## 当前可用

- 使用 `ndl rules validate` 校验 YAML 站点规则
- 安装 YAML 规则后，将匹配规则的静态 HTML 站点下载为 TXT 或 EPUB
- 将本地 TXT 转换为 TXT 或带样式的 EPUB
- 通过 `ndl library list/show/remove` 管理本地 SQLite 书库
- 通过 `ndl update --all` 刷新已保存的连载小说
- 通过 `ndl search` 搜索规则文件声明的来源索引
- 通过 `ndl rules update` 安装已校验的远程 YAML 规则
- 当规则声明 `fetcher.type: browser` 时，可选使用 Playwright 浏览器渲染页面，并支持规则声明等待/视口控制
- 使用 `scripts/verify_distribution.py` 校验 release wheel/sdist 内容
- 在本地 Web UI 中搜索、下载、手动刷新书库，`ndl serve` 运行时也可按间隔自动刷新
- 通过 `ndl serve` 启动本地 Web UI（默认绑定 `127.0.0.1`）
- 下载时强制 robots.txt、域名限速、重试策略与首跑合法使用免责声明

## 路线图功能

- 下载静态 HTML 小说站点，可选 Playwright 支持 JS 渲染页面
- TXT 与 EPUB 格式转换，可独立使用或下载后自动转换
- SQLite 本地书库管理，追踪连载小说并增量更新
- 通过规则文件定义的搜索端点进行多源搜索
- 规则驱动架构：新增站点只需写 YAML，不需要写 Python
- CLI 与本地 Web UI 双模式，共享数据

## 明确不做

- 不支持商业正版平台（起点、番茄、晋江、七猫）
- 不绕过付费墙、Cloudflare、CAPTCHA、DRM
- 不提供账号登录、代理池等功能

详见 [`DISCLAIMER.md`](DISCLAIMER.md)。

## 开发环境安装

```bash
uv sync
uv run ndl --version
```

需要浏览器渲染的规则还需安装可选 extra 和 Chromium：

```bash
uv sync --extra browser
uv run playwright install chromium
uv run ndl doctor browser
```

已发布到 PyPI，发行名为 `ndl-storykit`。Python import 路径仍为 `ndl`，
CLI 命令仍为 `ndl`：

```bash
pip install ndl-storykit
pip install 'ndl-storykit[browser]'   # 启用 Playwright 浏览器 fetcher
```

## 使用

```bash
ndl download <url> -o book.epub --accept-disclaimer
ndl convert book.txt -o book.epub
ndl library list
ndl update --all --accept-disclaimer
ndl search "关键词"
ndl rules update --manifest-url <manifest-url>
ndl doctor browser
ndl serve --accept-disclaimer
ndl rules validate my-rule.yaml
```

## 贡献

参见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。尤其欢迎站点规则贡献，无需 Python 编程。

## 许可证

[MIT](LICENSE)
