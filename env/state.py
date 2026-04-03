"""Typed state model returned by state()."""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class StateModel(BaseModel):
    """Read-only snapshot of environment state."""

    current_step: int
    done: bool
    actions_taken: List[Dict[str, Any]]
    total_reward: float
    current_file: str = ""


if __name__ == "__main__":
    s = StateModel(
        current_step=2,
        done=False,
        actions_taken=[{"action_type": "view_file", "comment": None, "step": 0}],
        total_reward=0.1,
        current_file="login.py",
    )
    print(s.model_dump())
    print(s.model_dump_json())
