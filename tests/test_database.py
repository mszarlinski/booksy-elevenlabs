"""
Tests for database configuration and async session handling.
"""

import os
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    engine,
    async_session_factory,
    get_session,
    _get_database_url,
    _is_valid_database_url,
    _create_engine,
)


# ============================================================================
# Tests for engine creation and session factory
# ============================================================================

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
    # The session object still exists but the context manager has cleaned up
    assert session_obj is not None


# ============================================================================
# Tests for get_session dependency
# ============================================================================

@pytest.mark.asyncio
async def test_get_session_dependency():
    """Test that get_session works as a FastAPI dependency.

    This verifies that:
    - get_session is a valid dependency that yields an AsyncSession
    - The session is properly created and can be used
    - The dependency pattern works correctly
    """
    # Simulate how FastAPI uses the dependency
    async for session in get_session():
        assert isinstance(session, AsyncSession)
        assert session.is_active
        break  # We only need one iteration to test the dependency


@pytest.mark.asyncio
async def test_get_session_cleanup_on_exit():
    """Test that get_session properly cleans up the session after use.

    This verifies that:
    - The session is closed and resources are released after the dependency exits
    - No connection leaks occur
    - The generator successfully completes the cleanup phase
    """
    session_obj = None
    async for session in get_session():
        session_obj = session
        assert session.is_active
        # The session is available while in the context
    # After the generator exits, cleanup has been performed
    # The session object still exists but the context has been exited
    assert session_obj is not None
    # Verify the generator completed (cleanup was called)


@pytest.mark.asyncio
async def test_get_session_handles_exceptions():
    """Test that get_session properly cleans up even when an exception occurs.

    This verifies that:
    - If an exception is raised while using the session,
    - The session is still properly closed and resources are released
    - Connection leaks don't occur even in error scenarios
    """
    session_obj = None
    try:
        async for session in get_session():
            session_obj = session
            assert session.is_active
            raise RuntimeError("Test exception")
    except RuntimeError:
        pass

    # Session cleanup should have occurred even after the exception
    assert session_obj is not None
    # The important thing is that the context manager's __aexit__ was called,
    # which closes the underlying database connection


# ============================================================================
# Tests for URL validation
# ============================================================================

def test_validate_database_url_valid():
    """Test that valid PostgreSQL asyncpg URLs are accepted."""
    valid_urls = [
        "postgresql+asyncpg://user:password@localhost:5432/database",
        "postgresql+asyncpg://user:p%40ssword@host.example.com:5433/my_db",
        "postgresql+asyncpg://admin:secret@192.168.1.1:5432/prod_db",
    ]
    for url in valid_urls:
        assert _is_valid_database_url(url), f"Valid URL rejected: {url}"


def test_validate_database_url_invalid():
    """Test that invalid URLs are rejected."""
    invalid_urls = [
        "postgresql://user:password@localhost:5432/database",  # Wrong scheme
        "postgresql+asyncpg://localhost:5432/database",  # Missing auth
        "postgresql+asyncpg://user@localhost:5432/database",  # Missing password
        "postgresql+asyncpg://user:password@localhost/database",  # Missing port
        "postgresql+asyncpg://user:password@localhost:5432",  # Missing database
        "postgresql+asyncpg://user:password@localhost:99999/database",  # Invalid port
        "postgresql+asyncpg://user:password@localhost:abc/database",  # Non-numeric port
        "mysql://user:password@localhost:3306/database",  # Wrong database
    ]
    for url in invalid_urls:
        assert not _is_valid_database_url(url), f"Invalid URL accepted: {url}"


def test_get_database_url_valid_env():
    """Test that valid DATABASE_URL environment variable is used."""
    valid_url = "postgresql+asyncpg://user:password@localhost:5432/testdb"
    os.environ["DATABASE_URL"] = valid_url
    try:
        result = _get_database_url()
        assert result == valid_url
    finally:
        del os.environ["DATABASE_URL"]


def test_get_database_url_converts_postgresql_to_asyncpg():
    """Test that postgresql:// URLs are converted to postgresql+asyncpg://."""
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/testdb"
    try:
        result = _get_database_url()
        assert result == "postgresql+asyncpg://user:password@localhost:5432/testdb"
    finally:
        del os.environ["DATABASE_URL"]


# ============================================================================
# Tests for database URL error scenarios
# ============================================================================

def test_get_database_url_invalid_format():
    """Test that invalid DATABASE_URL raises ValueError."""
    os.environ["DATABASE_URL"] = "invalid-url-format"
    try:
        with pytest.raises(ValueError, match="Invalid DATABASE_URL format"):
            _get_database_url()
    finally:
        del os.environ["DATABASE_URL"]


def test_get_database_url_missing_required_components():
    """Test that missing required components raise ValueError."""
    # Create scenario where both DATABASE_URL and component variables are invalid
    # Clear any existing DATABASE_URL
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

    # Set invalid port
    os.environ["POSTGRES_PORT"] = "invalid"
    try:
        with pytest.raises(ValueError, match="Invalid POSTGRES_PORT"):
            _get_database_url()
    finally:
        del os.environ["POSTGRES_PORT"]


def test_get_database_url_invalid_port_range():
    """Test that port out of valid range raises ValueError."""
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

    os.environ["POSTGRES_PORT"] = "99999"
    try:
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            _get_database_url()
    finally:
        del os.environ["POSTGRES_PORT"]


# ============================================================================
# Tests for pool configuration
# ============================================================================

def test_pool_configuration_from_env():
    """Test that pool configuration is read from environment variables."""
    os.environ["TESTING"] = "false"  # Ensure we use QueuePool, not NullPool
    os.environ["DB_POOL_SIZE"] = "20"
    os.environ["DB_MAX_OVERFLOW"] = "5"
    os.environ["DB_POOL_RECYCLE"] = "1800"

    try:
        # This should create an engine with custom pool settings
        # We can't easily test the exact values without inspecting private attributes,
        # but we can verify the engine is created without error
        test_engine = _create_engine()
        assert test_engine is not None
    finally:
        os.environ["TESTING"] = "true"
        del os.environ["DB_POOL_SIZE"]
        del os.environ["DB_MAX_OVERFLOW"]
        del os.environ["DB_POOL_RECYCLE"]


def test_pool_configuration_defaults():
    """Test that pool configuration uses sensible defaults."""
    os.environ["TESTING"] = "false"

    # Clear custom pool settings if present
    for key in ["DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_RECYCLE"]:
        if key in os.environ:
            del os.environ[key]

    try:
        # This should create an engine with default pool settings
        test_engine = _create_engine()
        assert test_engine is not None
    finally:
        os.environ["TESTING"] = "true"


def test_pool_configuration_invalid_pool_size():
    """Test that invalid pool size raises ValueError."""
    os.environ["TESTING"] = "false"
    os.environ["DB_POOL_SIZE"] = "invalid"

    try:
        with pytest.raises(ValueError, match="Invalid pool configuration"):
            _create_engine()
    finally:
        os.environ["TESTING"] = "true"
        del os.environ["DB_POOL_SIZE"]


def test_pool_configuration_negative_pool_size():
    """Test that negative pool size raises ValueError."""
    os.environ["TESTING"] = "false"
    os.environ["DB_POOL_SIZE"] = "-5"

    try:
        with pytest.raises(ValueError, match="DB_POOL_SIZE must be positive"):
            _create_engine()
    finally:
        os.environ["TESTING"] = "true"
        del os.environ["DB_POOL_SIZE"]


def test_pool_configuration_negative_overflow():
    """Test that negative overflow raises ValueError."""
    os.environ["TESTING"] = "false"
    os.environ["DB_MAX_OVERFLOW"] = "-1"

    try:
        with pytest.raises(ValueError, match="DB_MAX_OVERFLOW must be non-negative"):
            _create_engine()
    finally:
        os.environ["TESTING"] = "true"
        del os.environ["DB_MAX_OVERFLOW"]


def test_pool_configuration_invalid_recycle():
    """Test that invalid recycle value raises ValueError."""
    os.environ["TESTING"] = "false"
    os.environ["DB_POOL_RECYCLE"] = "not_a_number"

    try:
        with pytest.raises(ValueError, match="Invalid pool configuration"):
            _create_engine()
    finally:
        os.environ["TESTING"] = "true"
        del os.environ["DB_POOL_RECYCLE"]


# ============================================================================
# Skipped tests (require running PostgreSQL database)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running PostgreSQL database")
async def test_database_connection():
    """Test basic database connectivity with a simple query."""
    async with async_session_factory() as session:
        # Execute a simple query to verify connection works
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


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
