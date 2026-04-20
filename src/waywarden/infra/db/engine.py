"""Async SQLAlchemy engine and session factory.

Reads ``AppConfig.database_url`` and creates an ``AsyncEngine`` backed by
the ``psycopg`` async driver (``postgresql+psycopg://``).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from waywarden.config.settings import AppConfig
from waywarden.infra.db.metadata import metadata


def build_engine(config: AppConfig) -> AsyncEngine:
    """Create an async engine from *config*.

    Raises ``ValueError`` when ``database_url`` is empty or when the URL
    does not use an async-capable Postgres driver.
    """
    url = config.database_url

    if not url:
        raise ValueError("database_url must be set")

    # Enforce async Postgres driver
    if "postgresql+" not in url and url.startswith("postgresql+"):
        raise ValueError(
            f"database_url must use an async driver: {url!r}. "
            "Use 'postgresql+psycopg://' or 'postgresql+asyncpg://'."
        )

    # Also reject bare postgresql:// (sync-only)
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        raise ValueError(
            f"database_url must use an async driver: {url!r}. "
            "Use 'postgresql+psycopg://' or 'postgresql+asyncpg://'."
        )

    engine = create_async_engine(url, echo=False)
    return engine


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a configured ``async_sessionmaker`` bound to *engine*."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


__all__ = ["build_engine", "build_session_factory", "metadata"]
