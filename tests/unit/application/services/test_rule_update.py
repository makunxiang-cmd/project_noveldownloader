"""Unit tests for remote rule updates."""

from __future__ import annotations

import textwrap
from hashlib import sha256

import httpx
import pytest
import respx

from ndl.application.services.rule_update import RuleUpdateService
from ndl.core.errors import InvalidArgumentError, RuleValidationError

MANIFEST_URL = "https://rules.example.test/manifest.yaml"
RULE_URL = "https://rules.example.test/rules/remote_rule.yaml"
REMOTE_RULE_YAML = """
id: remote_rule
name: Remote Rule
version: 1.0.0
author: Tests
priority: 25
url_patterns:
  - pattern: "https://remote.test/book/*"
    type: glob
index:
  novel:
    title: { selector: "h1" }
    author: { selector: ".author" }
  chapter_list:
    container: "#chapters"
    items: "a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_plans_and_applies_valid_remote_rules(tmp_path) -> None:
    rules_dir = tmp_path / "rules"
    _mock_manifest(REMOTE_RULE_YAML)
    service = RuleUpdateService(rules_dir=rules_dir)

    try:
        plan = await service.plan_update(MANIFEST_URL)
        service.apply_update(plan)
    finally:
        await service.aclose()

    assert plan.changed_count == 1
    assert plan.items[0].status == "added"
    assert (rules_dir / "remote_rule.yaml").read_text(encoding="utf-8") == textwrap.dedent(
        REMOTE_RULE_YAML
    )


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_reports_unchanged_existing_rule(tmp_path) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "remote_rule.yaml").write_text(textwrap.dedent(REMOTE_RULE_YAML), encoding="utf-8")
    _mock_manifest(REMOTE_RULE_YAML)
    service = RuleUpdateService(rules_dir=rules_dir)

    try:
        plan = await service.plan_update(MANIFEST_URL)
    finally:
        await service.aclose()

    assert plan.changed_count == 0
    assert plan.items[0].status == "unchanged"


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_rejects_invalid_bundle_without_writing(tmp_path) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    existing = "existing content"
    target = rules_dir / "remote_rule.yaml"
    target.write_text(existing, encoding="utf-8")
    _mock_manifest("id: remote_rule\n")
    service = RuleUpdateService(rules_dir=rules_dir)

    try:
        with pytest.raises(RuleValidationError):
            await service.plan_update(MANIFEST_URL)
    finally:
        await service.aclose()

    assert target.read_text(encoding="utf-8") == existing


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_rejects_checksum_mismatch(tmp_path) -> None:
    manifest = """
version: 1
rules:
  - id: remote_rule
    url: /rules/remote_rule.yaml
    sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""
    respx.get(MANIFEST_URL).mock(return_value=httpx.Response(200, text=textwrap.dedent(manifest)))
    respx.get(RULE_URL).mock(
        return_value=httpx.Response(200, text=textwrap.dedent(REMOTE_RULE_YAML))
    )
    service = RuleUpdateService(rules_dir=tmp_path / "rules")

    try:
        with pytest.raises(RuleValidationError, match="checksum"):
            await service.plan_update(MANIFEST_URL)
    finally:
        await service.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_rejects_http_manifest_by_default(tmp_path) -> None:
    service = RuleUpdateService(rules_dir=tmp_path / "rules")

    try:
        with pytest.raises(InvalidArgumentError, match="http scheme"):
            await service.plan_update("http://rules.example.test/manifest.yaml")
    finally:
        await service.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_rule_update_allows_http_when_insecure_env_set(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NDL_RULES_ALLOW_INSECURE", "1")
    http_manifest_url = "http://rules.example.test/manifest.yaml"
    http_rule_url = "http://rules.example.test/rules/remote_rule.yaml"
    digest = sha256(textwrap.dedent(REMOTE_RULE_YAML).encode("utf-8")).hexdigest()
    manifest = f"""
version: 1
rules:
  - id: remote_rule
    url: /rules/remote_rule.yaml
    sha256: {digest}
"""
    respx.get(http_manifest_url).mock(
        return_value=httpx.Response(200, text=textwrap.dedent(manifest))
    )
    respx.get(http_rule_url).mock(
        return_value=httpx.Response(200, text=textwrap.dedent(REMOTE_RULE_YAML))
    )
    service = RuleUpdateService(rules_dir=tmp_path / "rules")

    try:
        plan = await service.plan_update(http_manifest_url)
    finally:
        await service.aclose()

    assert plan.changed_count == 1


def _mock_manifest(rule_yaml: str) -> None:
    digest = sha256(textwrap.dedent(rule_yaml).encode("utf-8")).hexdigest()
    manifest = f"""
version: 1
rules:
  - id: remote_rule
    url: /rules/remote_rule.yaml
    sha256: {digest}
"""
    respx.get(MANIFEST_URL).mock(return_value=httpx.Response(200, text=textwrap.dedent(manifest)))
    respx.get(RULE_URL).mock(return_value=httpx.Response(200, text=textwrap.dedent(rule_yaml)))
