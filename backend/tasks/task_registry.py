"""Central task registry backed by offline JSON task files."""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from backend.tasks.loader import get_available_tasks, get_task_catalog, load_task
except ImportError:
    from tasks.loader import get_available_tasks, get_task_catalog, load_task

TASK_REGISTRY: Dict[str, Dict[str, Any]] = {
    task_id: load_task(task_id) for task_id in get_available_tasks()
}

__all__ = ["TASK_REGISTRY", "get_available_tasks", "get_task_catalog", "load_task"]
