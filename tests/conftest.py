"""
Pytest configuration for async tests.
"""

import os

# Set environment to testing mode to use NullPool (no connection reuse)
os.environ["TESTING"] = "true"
