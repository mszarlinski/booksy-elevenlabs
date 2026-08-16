"""Fixtures for repository tests."""

import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base

# Set testing mode
os.environ["TESTING"] = "true"


@pytest.fixture
async def async_engine():
    """Create async engine for tests."""
    # Use test database URL
    db_url = "postgresql+asyncpg://booksy_user:booksy_password@localhost:5432/booksy_test"

    engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=None,  # Use default QueuePool
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async session for tests."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()
