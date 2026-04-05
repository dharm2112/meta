"""Task grader lookup backed by offline task data."""

from __future__ import annotations

from grader.grader import TaskGrader
from tasks.task_registry import load_task


def get_grader(task_id: str) -> TaskGrader:
    return TaskGrader(load_task(task_id))
