"""Retry schedule for webhook deliveries (HR-212)."""

import hashlib

BASE_SECONDS = 30
MAX_DELAY = 3600
DEFAULT_MAX_ATTEMPTS = 8


def backoff_delay(event_id: str, attempt: int, retry_after: int | None = None) -> float:
    """Seconds to wait before the next attempt, after `attempt` attempts so far."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    base = min(BASE_SECONDS * 2 ** (attempt - 1), MAX_DELAY)
    h = int(hashlib.sha256(f"{event_id}:{attempt}".encode()).hexdigest()[:8], 16)
    delay = base * (0.9 + 0.2 * h / 0xFFFFFFFF)
    if retry_after is not None:
        delay = max(delay, retry_after)
    return min(delay, MAX_DELAY)
