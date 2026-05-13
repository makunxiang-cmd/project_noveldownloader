"""Remote rule update service."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ndl.core.errors import InvalidArgumentError, RuleLoadError, RuleValidationError
from ndl.rules import SourceRule, load_rule_text

RuleUpdateStatus = Literal["added", "updated", "unchanged"]
_ENV_ALLOW_INSECURE = "NDL_RULES_ALLOW_INSECURE"


class RemoteRuleEntry(BaseModel):
    """One rule reference in a remote manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    url: str = Field(min_length=1)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)

    @field_validator("sha256")
    @classmethod
    def _lower_checksum(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None


class RemoteRuleManifest(BaseModel):
    """Remote rule manifest schema."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    rules: list[RemoteRuleEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _rule_ids_are_unique(self) -> RemoteRuleManifest:
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("manifest rule ids must be unique")
        return self


@dataclass(frozen=True)
class RuleUpdateItem:
    """A validated remote rule ready to be written."""

    rule: SourceRule
    source_url: str
    target_path: Path
    status: RuleUpdateStatus
    content: str


@dataclass(frozen=True)
class RuleUpdatePlan:
    """A complete remote rule update plan."""

    manifest_url: str
    rules_dir: Path
    items: list[RuleUpdateItem]

    @property
    def changed_count(self) -> int:
        """Return the number of rules that would be added or updated."""
        return sum(1 for item in self.items if item.status != "unchanged")


class RuleUpdateService:
    """Fetch, validate, and install remote YAML source rules."""

    def __init__(
        self,
        *,
        rules_dir: Path,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._rules_dir = rules_dir
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def aclose(self) -> None:
        """Close the owned HTTP client."""
        if self._owns_client:
            await self._client.aclose()

    async def plan_update(self, manifest_url: str) -> RuleUpdatePlan:
        """Return a validated update plan without writing files."""
        _require_secure_scheme(manifest_url, label="manifest URL")
        manifest_text = await self._fetch_text(manifest_url)
        manifest = _parse_manifest(manifest_text, source_name=manifest_url)
        rule_urls = [urljoin(manifest_url, entry.url) for entry in manifest.rules]
        for url in rule_urls:
            _require_secure_scheme(url, label="rule URL")
        contents = await asyncio.gather(*(self._fetch_text(url) for url in rule_urls))
        items: list[RuleUpdateItem] = []
        for entry, rule_url, content in zip(manifest.rules, rule_urls, contents, strict=True):
            _validate_checksum(entry, content, source_name=rule_url)
            rule = load_rule_text(content, source_name=rule_url)
            if rule.id != entry.id:
                raise RuleValidationError(
                    "Remote rule id does not match manifest entry.",
                    detail=f"Manifest id: {entry.id}\nRule id: {rule.id}\nURL: {rule_url}",
                )
            target_path = self._rules_dir / f"{rule.id}.yaml"
            items.append(
                RuleUpdateItem(
                    rule=rule,
                    source_url=rule_url,
                    target_path=target_path,
                    status=_target_status(target_path, content),
                    content=content,
                )
            )
        return RuleUpdatePlan(manifest_url=manifest_url, rules_dir=self._rules_dir, items=items)

    def apply_update(self, plan: RuleUpdatePlan) -> None:
        """Write all changed rules from a previously validated plan."""
        plan.rules_dir.mkdir(parents=True, exist_ok=True)
        for item in plan.items:
            if item.status == "unchanged":
                continue
            temp_path = item.target_path.with_suffix(f"{item.target_path.suffix}.tmp")
            temp_path.write_text(item.content, encoding="utf-8")
            temp_path.replace(item.target_path)

    async def _fetch_text(self, url: str) -> str:
        try:
            response = await self._client.get(url)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RuleLoadError(
                "Network error while fetching remote rule metadata.", detail=str(exc)
            ) from exc
        if response.status_code >= 400:
            raise RuleLoadError(
                "Remote rule metadata request failed.",
                detail=f"URL: {url}\nHTTP status: {response.status_code}",
            )
        return response.text


def _require_secure_scheme(url: str, *, label: str) -> None:
    scheme = urlparse(url).scheme.lower()
    if scheme == "https":
        return
    if scheme == "http" and os.environ.get(_ENV_ALLOW_INSECURE, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    raise InvalidArgumentError(
        f"Refusing to fetch remote rule data over {scheme or 'an unknown'} scheme.",
        detail=(
            f"{label}: {url}\n"
            "NDL only fetches remote rules over https. Set "
            f"{_ENV_ALLOW_INSECURE}=1 to allow http (for local mirrors or testing only)."
        ),
    )


def _parse_manifest(text: str, *, source_name: str) -> RemoteRuleManifest:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuleLoadError(
            f"Could not parse remote rule manifest: {source_name}", detail=str(exc)
        ) from exc
    try:
        return RemoteRuleManifest.model_validate(raw)
    except ValueError as exc:
        raise RuleValidationError(
            f"Remote rule manifest validation failed: {source_name}", detail=str(exc)
        ) from exc


def _validate_checksum(entry: RemoteRuleEntry, content: str, *, source_name: str) -> None:
    if entry.sha256 is None:
        return
    actual = sha256(content.encode("utf-8")).hexdigest()
    if actual != entry.sha256:
        raise RuleValidationError(
            "Remote rule checksum mismatch.",
            detail=f"Rule id: {entry.id}\nURL: {source_name}\nExpected: {entry.sha256}\nActual: {actual}",
        )


def _target_status(path: Path, content: str) -> RuleUpdateStatus:
    if not path.exists():
        return "added"
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError:
        return "updated"
    return "unchanged" if existing == content else "updated"
