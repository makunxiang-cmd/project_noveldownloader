"""TXT reader that parses chapter-like headings into Novel objects."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ndl.core.errors import ConvertError
from ndl.core.models import Chapter, Novel

_CHINESE_NUMERAL = "零〇一二三四五六七八九十百千万两壹贰叁肆伍陆柒捌玖拾佰仟"
_NUMBER = rf"[0-9{_CHINESE_NUMERAL}]+"
_FULLWIDTH_COLON = "\uff1a"
_COLON_CHARS = f":{_FULLWIDTH_COLON}"
_SPECIAL_HEADING = (
    "楔子",
    "序章",
    "序幕",
    "引子",
    "终章",
    "尾声",
    "后记",
    "番外",
    "外传",
)
_CHAPTER_HEADING_RE = re.compile(
    rf"^(?:第{_NUMBER}[章节回节卷部集]|卷{_NUMBER}|Chapter\s+{_NUMBER}\b|"
    rf"{'|'.join(_SPECIAL_HEADING)})(?:\s|[{_COLON_CHARS}、.-]|$).*$",
    re.IGNORECASE,
)
_MARKDOWN_HEADING_RE = re.compile(r"^#{2,6}\s+(?P<title>.+)$")
_AUTHOR_LABELS = (f"作者{_FULLWIDTH_COLON}", "作者:")
_SOURCE_LABELS = (f"来源{_FULLWIDTH_COLON}", "来源:")
_RULE_LABELS = (f"规则{_FULLWIDTH_COLON}", "规则:")
_STATUS_LABELS = (f"状态{_FULLWIDTH_COLON}", "状态:")
_METADATA_LABELS = _AUTHOR_LABELS + _SOURCE_LABELS + _RULE_LABELS + _STATUS_LABELS
_SUMMARY_LABELS = (f"简介{_FULLWIDTH_COLON}", "简介:", "Summary:")
_BODY_MARKERS = ("正文", "Content:")


class TxtReader:
    """Read a UTF-8 TXT file into the Novel intermediate representation."""

    def read(self, input_path: Path) -> Novel:
        """Read `input_path` into a Novel object."""
        return read_txt(input_path)


def read_txt(input_path: Path) -> Novel:
    """Read a UTF-8 TXT file into a Novel object."""
    try:
        text = input_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConvertError(
            "Failed to read TXT input.",
            detail=f"Path: {input_path}\n{exc}",
        ) from exc
    return parse_txt(text, source_path=input_path)


def parse_txt(text: str, *, source_path: Path) -> Novel:
    """Parse TXT content into a Novel object."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ConvertError("TXT input is empty.", detail=f"Path: {source_path}")

    lines = normalized.split("\n")
    headings = _find_headings(lines)
    first_heading_line = headings[0][0] if headings else len(lines)
    metadata = _parse_metadata(lines[:first_heading_line], source_path)
    chapters = (
        _parse_chapters(lines, headings, metadata.source_url)
        if headings
        else _single_chapter(lines, metadata.title, metadata.source_url, source_path)
    )

    return Novel(
        title=metadata.title,
        author=metadata.author,
        source_url=metadata.source_url,
        source_rule_id=metadata.source_rule_id,
        summary=metadata.summary,
        chapters=chapters,
        fetched_at=datetime.now(timezone.utc),
    )


class _TxtMetadata:
    def __init__(
        self,
        *,
        title: str,
        author: str,
        source_url: str | None,
        source_rule_id: str,
        summary: str | None,
    ) -> None:
        self.title = title
        self.author = author
        self.source_url = source_url
        self.source_rule_id = source_rule_id
        self.summary = summary


def _find_headings(lines: list[str]) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        title = _chapter_title(line)
        if title is not None:
            headings.append((index, title))
    return headings


def _chapter_title(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    markdown = _MARKDOWN_HEADING_RE.match(stripped)
    if markdown is not None:
        return markdown.group("title").strip()
    if _CHAPTER_HEADING_RE.match(stripped):
        return stripped
    return None


def _parse_metadata(lines: list[str], source_path: Path) -> _TxtMetadata:
    title = source_path.stem
    author = "unknown"
    source_url: str | None = None
    source_rule_id = "txt"
    summary = _summary_from(lines)
    title_set = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            title_set = True
        elif stripped.startswith(_AUTHOR_LABELS):
            author = _after_label(stripped)
        elif stripped.startswith(_SOURCE_LABELS):
            candidate = _after_label(stripped)
            if candidate.startswith(("http://", "https://")):
                source_url = candidate
        elif stripped.startswith(_RULE_LABELS):
            source_rule_id = _after_label(stripped) or source_rule_id
        elif not title_set and not _is_metadata_or_marker(stripped):
            title = stripped
            title_set = True

    return _TxtMetadata(
        title=title,
        author=author,
        source_url=source_url,
        source_rule_id=source_rule_id,
        summary=summary,
    )


def _summary_from(lines: list[str]) -> str | None:
    summary_lines: list[str] = []
    in_summary = False
    for line in lines:
        stripped = line.strip()
        if stripped in _SUMMARY_LABELS:
            in_summary = True
            continue
        if stripped in _BODY_MARKERS:
            in_summary = False
            continue
        if in_summary:
            summary_lines.append(line)
    summary = _clean_body(summary_lines)
    return summary or None


def _parse_chapters(
    lines: list[str],
    headings: list[tuple[int, str]],
    source_url: str | None,
) -> list[Chapter]:
    chapters: list[Chapter] = []
    for order, (line_index, title) in enumerate(headings):
        next_line_index = headings[order + 1][0] if order + 1 < len(headings) else len(lines)
        content = _clean_body(lines[line_index + 1 : next_line_index])
        chapters.append(Chapter(index=order, title=title, content=content, source_url=source_url))
    return chapters


def _single_chapter(
    lines: list[str],
    title: str,
    source_url: str | None,
    source_path: Path,
) -> list[Chapter]:
    content = _clean_body(_body_without_metadata(lines))
    if not content:
        raise ConvertError("TXT input has no chapter content.", detail=f"Path: {source_path}")
    return [Chapter(index=0, title=title, content=content, source_url=source_url)]


def _body_without_metadata(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        if line.strip() in _BODY_MARKERS:
            return lines[index + 1 :]

    body: list[str] = []
    skipped_title = False
    in_summary = False
    for line in lines:
        stripped = line.strip()
        if not stripped and not body:
            continue
        if stripped in _SUMMARY_LABELS:
            in_summary = True
            continue
        if in_summary:
            continue
        if _is_metadata_line(stripped):
            continue
        if not skipped_title and stripped:
            skipped_title = True
            continue
        body.append(line)
    return body


def _clean_body(lines: list[str]) -> str:
    trimmed = [line.rstrip() for line in lines]
    while trimmed and not trimmed[0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return "\n".join(trimmed).strip()


def _after_label(line: str) -> str:
    for separator in (_FULLWIDTH_COLON, ":"):
        if separator in line:
            return line.split(separator, 1)[1].strip()
    return ""


def _is_metadata_or_marker(line: str) -> bool:
    return _is_metadata_line(line) or line in _SUMMARY_LABELS or line in _BODY_MARKERS


def _is_metadata_line(line: str) -> bool:
    return line.startswith(_METADATA_LABELS)
