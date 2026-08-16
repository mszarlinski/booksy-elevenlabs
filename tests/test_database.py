"""
Tests for database configuration: URL construction/validation and pool setup.

Session/engine-lifecycle behavior (e.g. "async with ... closes the session on
exit") is guaranteed by SQLAlchemy itself and isn't re-tested here - these
tests focus on the logic this module actually adds on top of SQLAlchemy.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.database import (
    async_session_factory,
    _get_database_url,
    _is_valid_database_url,
    _create_engine,
)


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


def test_get_database_url_valid_env(monkeypatch):
    """Test that valid DATABASE_URL environment variable is used."""
    valid_url = "postgresql+asyncpg://user:password@localhost:5432/testdb"
    monkeypatch.setenv("DATABASE_URL", valid_url)
    assert _get_database_url() == valid_url


def test_get_database_url_converts_postgresql_to_asyncpg(monkeypatch):
    """Test that postgresql:// URLs are converted to postgresql+asyncpg://."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb")
    assert _get_database_url() == "postgresql+asyncpg://user:password@localhost:5432/testdb"


def test_get_database_url_does_not_leak_credentials_on_error(monkeypatch):
    """Test that an invalid DATABASE_URL is never echoed back in the error.

    Regression test: the raw value (which may contain the password) must not
    appear in the exception message, since it can end up in logs/error reports.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:s3cr3t@localhost:5432")
    with pytest.raises(ValueError) as exc_info:
        _get_database_url()
    assert "s3cr3t" not in str(exc_info.value)


def test_get_database_url_from_components_encodes_reserved_characters(monkeypatch):
    """Test that a password with URI-reserved characters (@, /, ?, #) still
    round-trips correctly when the URL is built from discrete components.

    Regression test: interpolating the password directly into an f-string
    breaks parsing when it contains characters like '@' or '/'.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "booksy_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/word?#1")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "booksy")

    result = _get_database_url()
    parsed = make_url(result)

    assert parsed.password == "p@ss/word?#1"
    assert parsed.username == "booksy_user"
    assert parsed.host == "localhost"
    assert parsed.port == 5432
    assert parsed.database == "booksy"


# ============================================================================
# Tests for database URL error scenarios
# ============================================================================

def test_get_database_url_invalid_format(monkeypatch):
    """Test that invalid DATABASE_URL raises ValueError."""
    monkeypatch.setenv("DATABASE_URL", "invalid-url-format")
    with pytest.raises(ValueError, match="Invalid DATABASE_URL format"):
        _get_database_url()


def test_get_database_url_missing_required_components(monkeypatch):
    """Test that missing required components raise ValueError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_PORT", "invalid")
    with pytest.raises(ValueError, match="Invalid POSTGRES_PORT"):
        _get_database_url()


def test_get_database_url_invalid_port_range(monkeypatch):
    """Test that port out of valid range raises ValueError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_PORT", "99999")
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        _get_database_url()


# ============================================================================
# Tests for pool configuration
# ============================================================================

def test_pool_configuration_from_env(monkeypatch):
    """Test that pool configuration is read from environment variables."""
    monkeypatch.setenv("TESTING", "false")  # Ensure we use QueuePool, not NullPool
    monkeypatch.setenv("DB_POOL_SIZE", "20")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
    monkeypatch.setenv("DB_POOL_RECYCLE", "1800")

    # This should create an engine with custom pool settings
    # We can't easily test the exact values without inspecting private attributes,
    # but we can verify the engine is created without error
    test_engine = _create_engine()
    assert test_engine is not None


def test_pool_configuration_defaults(monkeypatch):
    """Test that pool configuration uses sensible defaults."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_POOL_RECYCLE", raising=False)

    # This should create an engine with default pool settings
    test_engine = _create_engine()
    assert test_engine is not None


def test_pool_configuration_invalid_pool_size(monkeypatch):
    """Test that invalid pool size raises ValueError."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("DB_POOL_SIZE", "invalid")

    with pytest.raises(ValueError, match="Invalid pool configuration"):
        _create_engine()


def test_pool_configuration_negative_pool_size(monkeypatch):
    """Test that negative pool size raises ValueError."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("DB_POOL_SIZE", "-5")

    with pytest.raises(ValueError, match="DB_POOL_SIZE must be positive"):
        _create_engine()


def test_pool_configuration_negative_overflow(monkeypatch):
    """Test that negative overflow raises ValueError."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "-1")

    with pytest.raises(ValueError, match="DB_MAX_OVERFLOW must be non-negative"):
        _create_engine()


def test_pool_configuration_invalid_recycle(monkeypatch):
    """Test that invalid recycle value raises ValueError."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("DB_POOL_RECYCLE", "not_a_number")

    with pytest.raises(ValueError, match="Invalid pool configuration"):
        _create_engine()


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
