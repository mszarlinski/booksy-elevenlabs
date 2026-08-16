"""
Pytest configuration for async tests.
"""

import os

import pytest

# Set environment to testing mode to use NullPool (no connection reuse)
os.environ["TESTING"] = "true"


@pytest.fixture
def anyio_backend():
    """Configure pytest-asyncio to use asyncio backend."""
    return "asyncio"
