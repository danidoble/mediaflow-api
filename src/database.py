from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from src.config import settings

# Async engine with PostgreSQL connection pooling via asyncpg
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def task_session() -> AsyncGenerator[AsyncSession, None]:
    """Session for use inside Celery tasks (asyncio.run context).

    Uses NullPool so asyncpg never reuses connections across event loops.
    Each call creates a fresh connection that is closed when the context exits.
    """
    task_engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(task_engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await task_engine.dispose()
