import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, status
from app.config import get_settings


class InMemoryRateLimiter:
    """A clean, thread-safe in-memory rate limiter based on a sliding window.
    Limits submissions per (client_ip, widget_id) combination to prevent spam bursts.
    """

    def __init__(self):
        self._records = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(self, client_ip: str, widget_id: str):
        settings = get_settings()
        limit = settings.RATE_LIMIT_PER_MINUTE
        window_seconds = 60
        now = time.time()
        key = f"{client_ip}:{widget_id}"

        with self._lock:
            # Filter out timestamps older than the sliding window
            self._records[key] = [
                ts for ts in self._records[key] if now - ts < window_seconds
            ]

            if len(self._records[key]) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many submissions. Rate limit is {limit} requests per minute. Please wait before retrying."
                )

            # Record current request timestamp
            self._records[key].append(now)

    def reset(self):
        """Helper to reset rate limit records (useful in tests)."""
        with self._lock:
            self._records.clear()


# Global singleton instance
rate_limiter = InMemoryRateLimiter()
