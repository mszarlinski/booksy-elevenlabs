import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

DEFAULT_TTL = timedelta(hours=24)


class InMemoryIdempotencyStore:
    def __init__(
        self,
        ttl: timedelta = DEFAULT_TTL,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._ttl = ttl
        self._clock = clock
        self._entries: dict[str, tuple[dict, datetime]] = {}
        self._lock = threading.Lock()

    def get_or_create(self, key: str, compute: Callable[[], dict]) -> dict:
        with self._lock:
            cached = self._get(key)
            if cached is not None:
                return cached

            result = compute()
            self._entries[key] = (result, self._clock() + self._ttl)
            return result

    def _get(self, key: str) -> dict | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        result, expires_at = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return result


_store = InMemoryIdempotencyStore()


def get_idempotency_store() -> InMemoryIdempotencyStore:
    return _store
