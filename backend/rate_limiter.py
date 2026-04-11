"""Global thread-safe rate limiter for LLM API calls.

Uses a sliding-window algorithm to enforce a maximum number of
requests per minute (RPM). All API calls share a single module-level
instance so that bursts accumulated across multiple tasks or threads
are correctly throttled.

Configuration via environment variables:
    MAX_REQUESTS_PER_MINUTE  (default: 10)
    MIN_DELAY_SECONDS        (default: 6.0  — 60s / 10 RPM)
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window rate limiter for external API calls.

    Combines two complementary strategies:
    1. **Minimum per-call delay**: Never fires calls faster than
       ``min_delay_seconds`` apart, regardless of window capacity.
    2. **Sliding-window cap**: Tracks timestamps of the last N calls
       in a 60-second window; blocks if the window is full.

    Args:
        requests_per_minute: Maximum API calls allowed per 60-second window.
        min_delay_seconds:   Hard floor between consecutive calls.
    """

    _WINDOW_SECONDS: float = 60.0

    def __init__(
        self,
        requests_per_minute: int = 10,
        min_delay_seconds: float = 6.0,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.min_delay_seconds = min_delay_seconds

        self._call_timestamps: deque[float] = deque()
        self._last_call_time: float = 0.0
        self._lock = Lock()

    # ── Public API ───────────────────────────────────────────────────

    def acquire(self) -> None:
        """Block until an API call slot is available, then claim it.

        Call this **immediately before** each LLM API request.
        """
        with self._lock:
            self._apply_min_delay()
            self._apply_window_cap()
            now = time.monotonic()
            self._call_timestamps.append(now)
            self._last_call_time = now

    @property
    def active_request_count(self) -> int:
        """Number of requests recorded in the current 60-second window."""
        with self._lock:
            self._evict_old_timestamps(time.monotonic())
            return len(self._call_timestamps)

    def reset(self) -> None:
        """Clear all state. Primarily useful in unit tests."""
        with self._lock:
            self._call_timestamps.clear()
            self._last_call_time = 0.0

    # ── Internal helpers ─────────────────────────────────────────────

    def _apply_min_delay(self) -> None:
        """Sleep if less than ``min_delay_seconds`` has passed since the last call."""
        now = time.monotonic()
        elapsed = now - self._last_call_time
        if elapsed < self.min_delay_seconds:
            wait = self.min_delay_seconds - elapsed
            logger.debug("[RateLimiter] Min-delay throttle: sleeping %.2fs", wait)
            time.sleep(wait)

    def _apply_window_cap(self) -> None:
        """Sleep until the oldest in-window request ages out if window is full."""
        now = time.monotonic()
        self._evict_old_timestamps(now)

        if len(self._call_timestamps) >= self.requests_per_minute:
            # The oldest timestamp that is still within the window
            oldest = self._call_timestamps[0]
            # Wait until oldest is >60s ago (plus a tiny safety buffer)
            wait = (oldest + self._WINDOW_SECONDS) - now + 0.05
            if wait > 0:
                logger.info(
                    "[RateLimiter] Window saturated (%d/%d RPM). "
                    "Waiting %.1fs for a slot to free up…",
                    len(self._call_timestamps),
                    self.requests_per_minute,
                    wait,
                )
                time.sleep(wait)
                now = time.monotonic()
                self._evict_old_timestamps(now)

    def _evict_old_timestamps(self, now: float) -> None:
        """Remove timestamps that have fallen outside the 60-second window."""
        cutoff = now - self._WINDOW_SECONDS
        while self._call_timestamps and self._call_timestamps[0] <= cutoff:
            self._call_timestamps.popleft()


# ── Module-level singleton ────────────────────────────────────────────────────
# All LiteLLMReviewAgent instances and evaluation loops import and share this
# single limiter, giving us a unified view of API usage.

global_rate_limiter = RateLimiter(
    requests_per_minute=int(os.environ.get("MAX_REQUESTS_PER_MINUTE", "10")),
    min_delay_seconds=float(os.environ.get("MIN_DELAY_SECONDS", "6.0")),
)
