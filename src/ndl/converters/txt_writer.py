"""TXT writer for Novel objects."""

from __future__ import annotations

from pathlib import Path

from ndl.core.errors import ConvertError
from ndl.core.models import Chapter, Novel


class TxtWriter:
    """Write a Novel as UTF-8 plain text."""

    def write(self, novel: Novel, output_path: Path) -> Path:
        """Write `novel` to `output_path` and return the path."""
        return write_txt(novel, output_path)


def write_txt(novel: Novel, output_path: Path) -> Path:
    """Write a Novel as UTF-8 TXT."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(render_txt(novel))
    except OSError as exc:
        raise ConvertError(
            "Failed to write TXT output.",
            detail=f"Path: {output_path}\n{exc}",
        ) from exc
    return output_path


def render_txt(novel: Novel) -> str:
    """Render a Novel into the canonical NDL TXT representation."""
    sections = [_render_header(novel)]
    sections.extend(_render_chapter(chapter) for chapter in novel.chapters)
    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def _render_header(novel: Novel) -> str:
    lines = [
        f"# {novel.title}",
        f"作者:{novel.author}",
    ]
    if novel.source_url:
        lines.append(f"来源:{novel.source_url}")
    lines.extend(
        [
            f"规则:{novel.source_rule_id}",
            f"状态:{novel.status}",
        ]
    )
    if novel.summary:
        lines.extend(["", "简介:", novel.summary.strip()])
    lines.extend(["", "正文"])
    return "\n".join(lines)


def _render_chapter(chapter: Chapter) -> str:
    content = chapter.content.strip()
    if content:
        return f"## {chapter.title}\n\n{content}"
    return f"## {chapter.title}"
