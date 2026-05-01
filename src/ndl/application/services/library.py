"""Library service: domain-facing API over LibraryRepository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ndl.core.models import Chapter, Novel, NovelStatus
from ndl.storage.repository import LibraryRepository, NovelSummary


class LibraryService:
    """Save, list, get, and remove persisted novels."""

    def __init__(self, repository: LibraryRepository) -> None:
        self._repository = repository

    def save(self, novel: Novel) -> int:
        """Persist `novel` (upsert) and return its library id."""
        return self._repository.save(novel)

    def list(self) -> list[NovelSummary]:
        """Return library summaries ordered by id."""
        return self._repository.list()

    def get(self, novel_id: int) -> Novel | None:
        """Load a novel by id, or None if missing."""
        return self._repository.get(novel_id)

    def remove(self, novel_id: int) -> bool:
        """Delete the novel and its chapters; return True if a row was removed."""
        return self._repository.remove(novel_id)

    def append_chapters(
        self,
        novel_id: int,
        chapters: Sequence[Chapter],
        *,
        updated_at: datetime,
        status: NovelStatus | None = None,
    ) -> int:
        """Append new chapters to a saved novel."""
        return self._repository.append_chapters(
            novel_id,
            chapters,
            updated_at=updated_at,
            status=status,
        )
