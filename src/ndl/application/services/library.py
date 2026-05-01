"""Library service: domain-facing API over LibraryRepository."""

from __future__ import annotations

from ndl.core.models import Novel
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
