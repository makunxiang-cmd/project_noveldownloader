"""Application service wiring for NDL."""

from __future__ import annotations

from ndl.application.container import ServiceContainer
from ndl.application.services import ConvertService, DownloadService

__all__ = ["ConvertService", "DownloadService", "ServiceContainer"]
