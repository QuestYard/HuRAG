from typing import Any
import asyncio
import threading

class KVCache:
    """
    In-memory key-value cache.
    Rules:
    - max_size pairs upper limit
    - frequency (hit count) tracked
    - when full, evict the lowest-frequency evict_ratio pairs
    - O(1) read/probe with asyncio serialisation
    """

    def __init__(self, max_size: int=100, evict_ratio: float=0.2) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self.max_size: int = max_size
        self.evict_batch: int = max(1, int(max_size * evict_ratio))
        self._data: dict[Any, tuple[Any, int]] = {}
        self._lock = threading.Lock()

    # --- Synchronous API ---

    def get(self, key: Any) -> Any:
        """Return value and increment hit count."""
        with self._lock:
            if key not in self._data:
                return None
            value, freq = self._data[key]
            self._data[key] = (value, freq + 1)
            return value

    def put(self, key: Any, value: Any) -> None:
        """Insert or update key-value pair."""
        with self._lock:
            if key in self._data:
                _, freq = self._data[key]
                self._data[key] = (value, freq)
                return

            if len(self._data) >= self.max_size:
                self._evict()
            self._data[key] = (value, 1)

    def contains(self, key: Any) -> bool:
        """Check existence without changing frequency."""
        with self._lock:
            return key in self._data

    def _evict(self) -> None:
        """
        Evict evict_batch lowest-frequency items.
        NOTE: This is an internal method and should be called within a lock.
        """
        if not self._data:
            return

        ordered = sorted(self._data.items(), key=lambda kv: kv[1][1])
        for k, _ in ordered[: self.evict_batch]:
            del self._data[k]

    # --- Synchronous API ---

    async def aget(self, key: Any) -> Any:
        return await asyncio.to_thread(self.get, key)

    async def aput(self, key: Any, value: Any) -> None:
        return await asyncio.to_thread(self.put, key, value)

    async def acontains(self, key: Any) -> bool:
        return await asyncio.to_thread(self.contains, key)

    # --- Dunder Methods ---

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"KVCache({len(self._data)}/{self.max_size})"

