"""
Pytest configuration for async tests.
"""

import os

# Must be set before app.database is first imported by any test module: the
# async engine is a module-level singleton created at import time, and it
# picks NullPool (fresh connection per checkout) vs. QueuePool based on this
# flag. NullPool avoids reusing a pooled asyncpg connection across the
# separate event loops that FastAPI's synchronous TestClient can spin up per
# request, which otherwise raises "Future attached to a different loop".
os.environ["TESTING"] = "true"
