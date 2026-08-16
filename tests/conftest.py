"""
Pytest configuration for async tests.
"""

import os

# Must run before app.database's module-level engine is first created: forces
# NullPool so pooled connections aren't reused across TestClient's per-request
# event loops (QueuePool + reuse raises "Future attached to a different loop").
os.environ["TESTING"] = "true"
