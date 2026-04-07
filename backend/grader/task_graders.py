"""Task grader lookup backed by offline task data."""

from __future__ import annotations

from grader.grader import TaskGrader
from tasks.task_registry import load_task


def get_grader(task_id: str, is_custom: bool = False) -> TaskGrader:
    """
    Get a grader for a task.
    
    Args:
        task_id: Task identifier
        is_custom: If True, use custom task grading (review-only mode)
    
    Returns:
        TaskGrader instance
    """
    if is_custom:
        # For custom uploads, get from dynamic store
        from tasks.dynamic_store import get_dynamic_task
        task = get_dynamic_task(task_id)
        if task:
            return TaskGrader(task, review_only=True)
        raise ValueError(f"Custom task not found: {task_id}")
    
    return TaskGrader(load_task(task_id))
