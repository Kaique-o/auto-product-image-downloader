import asyncio
import time
from typing import Optional

class RateLimiter:
    """
    Thread-safe Token Bucket Rate Limiter.
    Ensures that we don't overwhelm external APIs with too many requests.
    Supports both async (for future expansions) and sync (for workers) acquisition.
    """
    def __init__(self, requests_per_second: float):
        self.rate = requests_per_second
        self.capacity = max(1.0, requests_per_second)
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire a token asynchronously.
        Blocks using asyncio.sleep if the bucket is empty.
        """
        async with self._lock:
            while self.tokens < 1:
                now = time.monotonic()
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self._add_tokens()
            self.tokens -= 1

    def acquire_sync(self):
        """
        Acquire a token synchronously using time.sleep.
        Safe for use inside background QThreads where an event loop might not be running.
        """
        while True:
            self._add_tokens()
            if self.tokens >= 1:
                self.tokens -= 1
                return
            
            # Simple busy-wait with sleep to avoid high CPU usage
            wait_time = (1 - self.tokens) / self.rate
            time.sleep(wait_time)

    def _add_tokens(self):
        """Refills the token bucket based on time elapsed."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
