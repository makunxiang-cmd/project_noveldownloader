"""SQLite engine and session factory with NDL PRAGMA defaults."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ndl.storage.models import Base


def create_database_engine(path: Path | str | None = None, *, echo: bool = False) -> Engine:
    """Build a SQLite engine with WAL + foreign_keys=ON applied on every connection."""
    url = _resolve_url(path)
    engine = create_engine(url, echo=echo, future=True)
    _install_pragma_listener(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a sessionmaker bound to `engine`."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_schema(engine: Engine) -> None:
    """Create all NDL tables on `engine` if they do not exist."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a session that commits on success and rolls back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _resolve_url(path: Path | str | None) -> str:
    if path is None:
        return "sqlite:///:memory:"
    if isinstance(path, str) and path.startswith("sqlite"):
        return path
    return f"sqlite:///{Path(path).expanduser()}"


def _install_pragma_listener(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
