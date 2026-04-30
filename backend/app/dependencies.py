"""Shared FastAPI dependencies."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

# Async engine and session factory
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


def get_settings():
    """Provide application settings as a dependency."""
    from app.config import settings as _settings
    return _settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_ctx() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for background tasks."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
