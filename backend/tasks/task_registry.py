"""Central task registry for OpenEnv validator and Gradio dropdown integration."""

from __future__ import annotations
from typing import Any, Dict, List, Union

from tasks.task_easy import TaskEasy
from tasks.task_medium import TaskMedium
from tasks.task_hard import TaskHard

TaskInstance = Union[TaskEasy, TaskMedium, TaskHard]

TASK_REGISTRY: Dict[str, TaskInstance] = {
    "easy": TaskEasy(),
    "medium": TaskMedium(),
    "hard": TaskHard(),
}


def get_available_tasks() -> List[str]:
    """Return list of registered task names (for dropdowns / inference loops)."""
    return list(TASK_REGISTRY.keys())


def load_task(task_name: str) -> TaskInstance:
    """Load a task instance by name. Raises KeyError if not found."""
    if task_name not in TASK_REGISTRY:
        raise KeyError(
            f"Unknown task '{task_name}'. Available: {get_available_tasks()}"
        )
    return TASK_REGISTRY[task_name]
