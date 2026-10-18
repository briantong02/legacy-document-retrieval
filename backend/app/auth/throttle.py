"""Sliding-window login throttle.

Failed sign-in attempts consume Active Directory lockout attempts, so repeated bad
passwords through this application can lock a real domain account. Attempts are counted
per username and per client address and rejected here before reaching the directory.

The application runs as a single process, so an in-memory counter is sufficient.
"""

import threading
import time
from collections import defaultdict, deque

from app.core.config import get_settings

settings = get_settings()

_lock = threading.Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)


def _prune(key: str, now: float) -> deque[float]:
    window_start = now - settings.login_attempt_window_seconds
    timestamps = _attempts[key]
    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()
    return timestamps


def is_throttled(*keys: str) -> bool:
    """True when any of the given keys has exhausted its attempt budget."""
    now = time.monotonic()
    with _lock:
        for key in keys:
            if key and len(_prune(key, now)) >= settings.login_max_attempts:
                return True
    return False


def record_failure(*keys: str) -> None:
    now = time.monotonic()
    with _lock:
        for key in keys:
            if key:
                _prune(key, now).append(now)


def reset(*keys: str) -> None:
    """Clear the counters for the given keys, called after a successful sign-in."""
    with _lock:
        for key in keys:
            _attempts.pop(key, None)


def clear_all() -> None:
    """Test helper: drop every counter."""
    with _lock:
        _attempts.clear()
