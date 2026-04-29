"""Selector DSL execution utilities."""

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from ndl.core.errors import EmptyContentError, SelectorNotFoundError
from ndl.rules.schema import CleanRule, Selector

SelectorValue = str | list[str]


def extract_selector(rule: Selector, root: Any, *, base_url: str | None = None) -> SelectorValue:
    """Extract a value from an HTMLParser or selectolax node using a Selector."""
    nodes = [root] if rule.selector == "self" else list(root.css(rule.selector))
    if not nodes:
        if rule.default is not None:
            return [rule.default] if rule.multiple else rule.default
        raise SelectorNotFoundError(rule.selector)

    values = [_extract_node_value(node, rule, base_url=base_url) for node in nodes]
    if rule.multiple:
        return values
    return values[0]


def clean_html_content(html: str, clean: CleanRule) -> str:
    """Convert HTML content to normalized paragraph text."""
    parser = HTMLParser(html)
    for selector in clean.remove_selectors:
        for node in parser.css(selector):
            node.decompose()

    text = unescape(parser.text(separator="\n"))
    for pattern in clean.strip_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)

    paragraphs = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()) if clean.normalize_whitespace else raw_line.strip()
        if len(line) >= clean.min_paragraph_length:
            paragraphs.append(line)

    content = "\n\n".join(paragraphs).strip()
    if not content:
        raise EmptyContentError("Chapter content is empty after cleaning.")
    return content


def _extract_node_value(node: Any, rule: Selector, *, base_url: str | None) -> str:
    match rule.attr:
        case "text":
            value = node.text(separator="\n")
        case "html":
            value = node.html
        case "href" | "src":
            value = node.attributes.get(rule.attr, "")
        case _:
            value = node.attributes.get(rule.attr, "")

    value = unescape(str(value))
    if rule.strip:
        value = value.strip()
    if rule.regex is not None:
        match_result = re.search(rule.regex, value, flags=re.MULTILINE)
        if match_result is None:
            if rule.default is not None:
                value = rule.default
            else:
                raise SelectorNotFoundError(rule.selector)
        else:
            value = match_result.group(rule.regex_group)
            if rule.strip:
                value = value.strip()
    if rule.resolve == "relative" and base_url:
        value = urljoin(base_url, value)
    return str(rule.map.get(value, value))
