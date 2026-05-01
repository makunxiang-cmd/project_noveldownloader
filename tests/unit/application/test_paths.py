"""Tests for the NDL_HOME path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ndl.application.paths import library_db_path, ndl_home


def test_default_home_is_dot_ndl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NDL_HOME", raising=False)
    assert ndl_home() == Path.home() / ".ndl"


def test_env_overrides_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NDL_HOME", str(tmp_path))
    assert ndl_home() == tmp_path
    assert library_db_path() == tmp_path / "library.db"


def test_user_expansion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NDL_HOME", "~/custom-ndl")
    assert ndl_home() == tmp_path / "custom-ndl"
