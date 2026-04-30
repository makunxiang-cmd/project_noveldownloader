# NDL - NOVELDOWNLOADER

> 规则驱动的中文小说下载与格式转换工具

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[English](README.md)

## 项目状态

开发中。P0 脚手架与 P1 MVP 下载/转换路径已实现；下一步进入 P2 书库持久化。首发版本 v0.1 将包含 MVP 功能：下载、TXT/EPUB 转换、书库管理。切片进度见 `docs/superpowers/plans/2026-04-29-ndl-p1-mvp.md`。

## 功能（规划中）

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

## 安装（即将推出）

```bash
pip install ndl
pip install ndl[browser]
```

## 使用预览

```bash
ndl download <url> -o book.epub --accept-disclaimer
ndl convert book.txt -o book.epub
ndl rules validate my-rule.yaml
ndl library list
ndl update --all
ndl serve
```

## 贡献

参见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。尤其欢迎站点规则贡献，无需 Python 编程。

## 许可证

[MIT](LICENSE)
