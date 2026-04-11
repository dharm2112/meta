"""Sequential task queue for rate-limit-safe LLM evaluation.

Instead of launching multiple tasks simultaneously (which causes
burst API traffic and 429 errors), this queue processes tasks one
at a time with a configurable pause between each task.

The inter-task delay gives the 60-second rate-limit window time to
breathe, on top of the per-call throttling inside the agent itself.

Configuration via environment variable:
    INTER_TASK_DELAY_SECONDS  (default: 3.0)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

# Seconds to wait between finishing one task and starting the next.
# Tune via environment if your rate limit headroom differs.
DEFAULT_INTER_TASK_DELAY = float(os.environ.get("INTER_TASK_DELAY_SECONDS", "3.0"))


class TaskQueue:
    """Serialise evaluation tasks with controlled inter-task delays.

    Usage::

        queue = TaskQueue(inter_task_delay=3.0)
        queue.enqueue(run_single_task, task_id="easy_auth_001", agent=agent)
        queue.enqueue(run_single_task, task_id="easy_csrf_001", agent=agent)
        results = queue.run_all()   # blocks; returns list of results

    A failed task is recorded as ``{"error": "...", "task_num": N}``
    and the queue always continues to the next task.
    """

    def __init__(self, inter_task_delay: float = DEFAULT_INTER_TASK_DELAY) -> None:
        """
        Args:
            inter_task_delay: Seconds to pause between consecutive tasks.
                              Set to 0 to disable (useful for baseline/RL agents
                              that make no API calls).
        """
        self.inter_task_delay = inter_task_delay
        self._queue: List[Dict[str, Any]] = []

    # ── Queue management ─────────────────────────────────────────────

    def enqueue(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Add a callable to the back of the queue.

        Args:
            fn:     The function to call.
            *args:  Positional arguments forwarded to ``fn``.
            **kwargs: Keyword arguments forwarded to ``fn``.
        """
        self._queue.append({"fn": fn, "args": args, "kwargs": kwargs})
        logger.debug(
            "[TaskQueue] Enqueued task #%d (%s)", len(self._queue), fn.__name__
        )

    def run_all(self) -> List[Any]:
        """Execute all enqueued tasks sequentially and return their results.

        Tasks are dequeued after this call completes.

        Returns:
            A list of return values (one per task, in insertion order).
            Errors are captured as ``{"error": str, "task_num": int}``
            so downstream code can inspect them without the whole run failing.
        """
        results: List[Any] = []
        total = len(self._queue)
        logger.info("[TaskQueue] Starting sequential run: %d task(s).", total)

        for idx, item in enumerate(self._queue):
            task_num = idx + 1
            fn_name = item["fn"].__name__
            logger.info(
                "[TaskQueue] ── Task %d/%d ─ %s starting ──",
                task_num, total, fn_name,
            )
            try:
                result = item["fn"](*item["args"], **item["kwargs"])
                results.append(result)
                logger.info(
                    "[TaskQueue] ── Task %d/%d ─ %s done ──",
                    task_num, total, fn_name,
                )
            except Exception as exc:
                logger.error(
                    "[TaskQueue] Task %d/%d failed: %s",
                    task_num, total, exc,
                    exc_info=True,
                )
                results.append({"error": str(exc), "task_num": task_num})

            # Pause between tasks — skip after the very last one
            if idx < total - 1 and self.inter_task_delay > 0:
                logger.info(
                    "[TaskQueue] Sleeping %.1fs before next task…",
                    self.inter_task_delay,
                )
                time.sleep(self.inter_task_delay)

        self._queue.clear()
        logger.info("[TaskQueue] All %d task(s) complete.", total)
        return results
