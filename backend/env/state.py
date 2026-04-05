"""Typed state model returned by state()."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StateModel(BaseModel):
    """Read-only snapshot of environment state."""

    task_id: str
    current_step: int
    max_steps: int
    done: bool
    total_reward: float
    actions_taken: List[Dict[str, Any]]
    inspected_diffs: List[str]
    inspected_files: List[str]
    final_decision: Optional[str] = None
