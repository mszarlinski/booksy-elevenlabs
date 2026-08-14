import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.idempotency import InMemoryIdempotencyStore


def test_get_or_create_computes_result_for_unknown_key():
    store = InMemoryIdempotencyStore()

    result = store.get_or_create("abc", lambda: {"id": "1"})

    assert result == {"id": "1"}


def test_get_or_create_returns_cached_result_without_recomputing():
    store = InMemoryIdempotencyStore()
    calls = []

    store.get_or_create("abc", lambda: calls.append(1) or {"id": "1"})
    result = store.get_or_create("abc", lambda: calls.append(2) or {"id": "2"})

    assert result == {"id": "1"}
    assert calls == [1]


def test_get_or_create_recomputes_after_ttl_expires():
    current = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = InMemoryIdempotencyStore(ttl=timedelta(seconds=10), clock=lambda: current)

    store.get_or_create("abc", lambda: {"id": "1"})
    current = current + timedelta(seconds=11)
    result = store.get_or_create("abc", lambda: {"id": "2"})

    assert result == {"id": "2"}


def test_get_or_create_computes_exactly_once_under_concurrent_access():
    store = InMemoryIdempotencyStore()
    call_count = 0
    count_lock = threading.Lock()

    def compute() -> dict:
        nonlocal call_count
        with count_lock:
            call_count += 1
        time.sleep(0.05)
        return {"id": "1"}

    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(lambda _: store.get_or_create("key", compute), range(50)))

    assert call_count == 1
    assert all(result == {"id": "1"} for result in results)
