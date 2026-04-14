from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from ea.settings import settings

# Sync engine — used by Alembic migrations only
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

# Async engine — used by FastAPI route handlers
async_engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
