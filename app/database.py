"""
Database configuration module for async SQLAlchemy 2.x with asyncpg.

This module provides:
- AsyncEngine: Async database engine with connection pooling
- AsyncSession: Async session factory for database operations
- Context managers for both regular and transactional sessions
"""

import os
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def _is_valid_database_url(url: str) -> bool:
    """
    Validate that the database URL is properly formatted for PostgreSQL asyncpg.

    Args:
        url: The database URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Check scheme is postgresql+asyncpg
        if parsed.scheme != "postgresql+asyncpg":
            return False

        # Check required components: username, password, hostname, port, database
        # Note: Both username and password are required for secure database connections
        if not all([parsed.username, parsed.password, parsed.hostname, parsed.port]):
            return False

        # Validate port is in valid range
        if not (1 <= parsed.port <= 65535):
            return False

        # Database name from path (should be /database_name)
        db_name = parsed.path.lstrip("/")
        if not db_name:
            return False

        return True
    except Exception:
        return False


def _get_database_url() -> str:
    """
    Get database URL from environment or construct from individual components.

    Returns:
        The database URL string for asyncpg connection

    Raises:
        ValueError: If DATABASE_URL is invalid or required components are missing
    """
    if database_url := os.getenv("DATABASE_URL"):
        # If DATABASE_URL is set, convert to async if using postgresql://
        # (docker-compose sets this with postgresql://, not postgresql+asyncpg://)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Validate the URL format
        if not _is_valid_database_url(database_url):
            raise ValueError(
                f"Invalid DATABASE_URL format. Expected: "
                f"postgresql+asyncpg://user:password@host:port/database. "
                f"Got: {database_url}"
            )
        return database_url

    # Fallback: construct from individual environment variables (for local dev)
    postgres_user = os.getenv("POSTGRES_USER", "booksy_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "booksy_password")
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "booksy")

    # Validate required components
    if not postgres_user or not postgres_host or not postgres_db:
        raise ValueError(
            "Missing required database configuration. "
            "Please set POSTGRES_USER, POSTGRES_HOST, and POSTGRES_DB environment variables."
        )

    # Validate port
    try:
        port = int(postgres_port)
        if not (1 <= port <= 65535):
            raise ValueError(f"Invalid POSTGRES_PORT: {port}. Port must be between 1 and 65535.")
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(
                f"Invalid POSTGRES_PORT: {postgres_port}. Port must be a valid integer."
            ) from e
        raise

    return f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"


def _create_engine() -> AsyncEngine:
    """
    Create and configure AsyncEngine for async database operations.

    Connection pooling configuration (configurable via environment variables):
    - pool_size: connections kept in pool for reuse (default: 10)
    - max_overflow: additional connections created when pool is exhausted (default: 10)
    - pool_recycle: recycle connections after N seconds (default: 3600 = 1 hour)
    - pool_pre_ping: test connections before using to detect dead connections (always: True)

    Environment variables:
    - DB_POOL_SIZE: Number of connections to keep in pool (default: 10)
    - DB_MAX_OVERFLOW: Additional connections above pool_size (default: 10)
    - DB_POOL_RECYCLE: Seconds before recycling connections (default: 3600)

    Returns:
        Configured AsyncEngine instance

    Raises:
        ValueError: If pool configuration values are invalid
    """
    database_url = _get_database_url()

    # Parse pool configuration from environment with sensible defaults
    try:
        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    except ValueError as e:
        raise ValueError(f"Invalid pool configuration: {e}") from e

    if pool_size <= 0:
        raise ValueError(f"DB_POOL_SIZE must be positive, got: {pool_size}")
    if max_overflow < 0:
        raise ValueError(f"DB_MAX_OVERFLOW must be non-negative, got: {max_overflow}")
    if pool_recycle <= 0:
        raise ValueError(f"DB_POOL_RECYCLE must be positive, got: {pool_recycle}")

    # Determine pooling strategy based on environment
    # Use NullPool for testing to avoid connection persistence issues
    # Use standard pooling for development/production with connection reuse
    if os.getenv("TESTING") == "true":
        # NullPool: Don't reuse connections (fresh connection per request)
        # Good for testing to avoid state leakage between tests
        engine = create_async_engine(
            database_url,
            echo=os.getenv("SQL_ECHO", "true").lower() == "true",  # Log SQL queries
            poolclass=NullPool,
        )
    else:
        # QueuePool (default for async): Connection reuse with size limits
        # - pool_size: connections kept in pool for reuse
        # - max_overflow: additional connections when pool exhausted
        # - pool_recycle: recycle connections after N seconds (prevents stale connections)
        # - pool_pre_ping: test connections before use (detects dead connections)
        engine = create_async_engine(
            database_url,
            echo=os.getenv("SQL_ECHO", "true").lower() == "true",  # Log SQL queries
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Test connections before use
        )
    return engine


# Initialize the async engine
engine: AsyncEngine = _create_engine()

# Create async session factory
# bind=engine: Associates sessions with the engine
# class_=AsyncSession: Use async-capable session class
# expire_on_commit=False: Don't expire objects after commit (optional, for easier testing)
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Don't auto-flush on query (more control over transactions)
    autocommit=False,  # Don't auto-commit (explicit transaction management)
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI that provides an async session.

    Usage in route handlers:
        @app.get("/items")
        async def list_items(session: AsyncSession = Depends(get_session)):
            result = await session.execute(...)
            return result

    This is a generator function that FastAPI automatically manages:
    - Creates a new session for each request
    - Yields the session to the route handler
    - Closes the session after the request completes (even if an error occurs)

    Yields:
        An AsyncSession instance for database operations
    """
    async with async_session_factory() as session:
        yield session


# Usage examples for different context manager patterns:
#
# PATTERN 1: Regular session (auto-close on exit)
# ---
# async with async_session_factory() as session:
#     result = await session.execute(...)
#     await session.commit()
#
# What it does:
# - Creates a new session
# - On exit: automatically closes the session (regardless of success/error)
# - You must manually call await session.commit() to persist changes
# - If an error occurs before commit(), changes are lost (rolled back)
#
# PATTERN 2: Explicit transaction (auto-commit/rollback)
# ---
# async with async_session_factory() as session:
#     async with session.begin():
#         result = await session.execute(...)
#         # No explicit commit needed!
#
# What it does:
# - session.begin() starts an explicit transaction
# - Changes are automatically committed on successful exit
# - On ANY exception within the context: automatic rollback (changes discarded)
# - On success: automatic commit (changes persisted)
# - This is "all-or-nothing" semantics - very safe for atomic operations
#
# PATTERN 3: Multiple operations (savepoints)
# ---
# async with async_session_factory() as session:
#     async with session.begin():
#         await session.execute(insert_stmt_1)
#         # Nested transaction (savepoint)
#         try:
#             async with session.begin_nested():
#                 await session.execute(insert_stmt_2)
#         except Exception:
#             pass  # Rollback insert_stmt_2 only
#         # insert_stmt_1 still intact
#
# What it does:
# - session.begin_nested() creates a savepoint within the transaction
# - Rollback of nested context only affects operations within it
# - Perfect for handling partial failures
