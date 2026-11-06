"""Async SQLAlchemy database lifecycle and session management.

PostgreSQL is the production database. SQLite is retained for local development and
unit tests. Schema creation is provided for development; production schema evolution
must use Alembic migrations.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from persistence.models import Base

logger = logging.getLogger(__name__)

_POSTGRES_DRIVERS = frozenset({"postgresql+asyncpg"})
_SQLITE_DRIVERS = frozenset({"sqlite+aiosqlite"})


def _validate_database_url(database_url: str | URL) -> URL:
    try:
        parsed = make_url(database_url)
    except Exception as exc:
        raise ValueError("invalid_database_url") from exc

    if parsed.drivername not in _POSTGRES_DRIVERS | _SQLITE_DRIVERS:
        raise ValueError("unsupported_async_database_driver")
    if parsed.drivername in _POSTGRES_DRIVERS and not parsed.host:
        raise ValueError("postgresql_host_required")
    if parsed.drivername in _POSTGRES_DRIVERS and not parsed.database:
        raise ValueError("postgresql_database_required")
    return parsed


def build_engine(
    database_url: str | URL,
    *,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: float = 30.0,
    pool_recycle_seconds: int = 1800,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async engine with bounded PostgreSQL pooling and health checks."""
    if pool_size < 1 or max_overflow < 0 or pool_timeout <= 0 or pool_recycle_seconds < 1:
        raise ValueError("invalid_database_pool_configuration")

    parsed = _validate_database_url(database_url)
    common: dict[str, Any] = {
        "echo": echo,
        "pool_pre_ping": True,
        "pool_recycle": pool_recycle_seconds,
    }

    if parsed.drivername in _POSTGRES_DRIVERS:
        common.update(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            connect_args={"server_settings": {"application_name": "omnisphere-360"}},
        )
    else:
        common["connect_args"] = {"check_same_thread": False}
        if parsed.database in (None, "", ":memory:"):
            common["poolclass"] = StaticPool

    return create_async_engine(parsed, **common)


def build_session_factory(
    engine: AsyncEngine,
    *,
    expire_on_commit: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Build a typed factory; sessions are never shared across concurrent tasks."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def session_scope(
    sessions: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield one session, committing on success and rolling back on failure."""
    async with sessions() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def get_session(
    sessions: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """FastAPI-compatible dependency that always closes and rolls back failed work."""
    async with sessions() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise


async def initialize_schema(engine: AsyncEngine) -> None:
    """Create missing tables for development/test use only; use Alembic in production."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


class Database:
    """Owns one engine and session factory for an application lifespan."""

    def __init__(self, database_url: str | URL, **engine_options: Any) -> None:
        self.engine = build_engine(database_url, **engine_options)
        self.sessions = build_session_factory(self.engine)
        self._closed = False

    async def initialize(self, *, create_schema: bool = False) -> None:
        if self._closed:
            raise RuntimeError("database_closed")
        if create_schema:
            await initialize_schema(self.engine)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._closed:
            raise RuntimeError("database_closed")
        async with session_scope(self.sessions) as session:
            yield session

    async def close(self) -> None:
        if not self._closed:
            await self.engine.dispose()
            self._closed = True

    async def __aenter__(self) -> Database:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.close()
