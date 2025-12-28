"""
Database connection and session management.

Uses SQLAlchemy with async support for PostgreSQL.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Global engine and session factory
_engine = None
_async_session_factory = None


async def init_database() -> None:
    """Initialize the database connection and create tables."""
    global _engine, _async_session_factory

    settings = get_settings()

    logger.info("Initializing database", url=settings.memory.postgres_url.split("@")[-1])

    _engine = create_async_engine(
        settings.memory.postgres_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Create tables
    async with _engine.begin() as conn:
        from src.persistence.models import GoalModel, TaskModel, AgentStateModel  # noqa
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def close_database() -> None:
    """Close database connections."""
    global _engine, _async_session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connections closed")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    if _async_session_factory is None:
        await init_database()

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI."""
    async with get_async_session() as session:
        yield session
