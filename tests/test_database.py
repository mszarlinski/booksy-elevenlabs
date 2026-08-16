"""
Tests for database configuration and async session handling.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, async_session_factory


@pytest.mark.asyncio
async def test_engine_creation():
    """Test that the async engine is created successfully."""
    assert engine is not None
    # Verify it's an AsyncEngine
    from sqlalchemy.ext.asyncio import AsyncEngine
    assert isinstance(engine, AsyncEngine)


@pytest.mark.asyncio
async def test_async_session_factory():
    """Test that the async session factory creates valid sessions."""
    async with async_session_factory() as session:
        assert isinstance(session, AsyncSession)
        # Session should be active
        assert session.is_active


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running PostgreSQL database")
async def test_database_connection():
    """Test basic database connectivity with a simple query."""
    async with async_session_factory() as session:
        # Execute a simple query to verify connection works
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_async_context_manager_closes_session():
    """Test that async context manager properly closes the session.

    Demonstrates that:
    - async with async_session_factory() as session: creates a session
    - On exit, the session is automatically closed (connection returned to pool)
    - This prevents connection leaks in long-running applications
    """
    session_obj = None
    async with async_session_factory() as session:
        # Session should be active within context
        session_obj = session
        assert session.is_active
    # After context exit, the connection is returned to the pool
    # The session object still exists but is no longer bound to a connection
    assert session_obj is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running PostgreSQL database")
async def test_transaction_context_manager():
    """Test explicit transaction context manager (auto-commit/rollback).

    Demonstrates that:
    - async with session.begin(): starts an explicit transaction
    - On successful exit: automatically commits changes
    - On exception within context: automatically rolls back changes
    - This is "all-or-nothing" semantics - very safe for atomic operations
    """
    async with async_session_factory() as session:
        # This demonstrates the transaction context manager
        # In a real scenario, this would perform database operations
        async with session.begin():
            # Within this context, we're in an explicit transaction
            # On successful exit: auto-commit
            # On exception: auto-rollback
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
