"""Schema validation utilities for OpenEnv compatibility."""

from __future__ import annotations
from typing import Any, Dict

from env.action import ActionModel
from env.observation import ObservationModel
from env.state import StateModel


def validate_action(action_dict: Dict[str, Any]) -> ActionModel:
    """Validate and return a typed ActionModel from a raw dictionary."""
    return ActionModel(**action_dict)


def validate_observation(obs_dict: Dict[str, Any]) -> ObservationModel:
    """Validate and return a typed ObservationModel from a raw dictionary."""
    return ObservationModel(**obs_dict)


def validate_state(state_dict: Dict[str, Any]) -> StateModel:
    """Validate and return a typed StateModel from a raw dictionary."""
    return StateModel(**state_dict)


if __name__ == "__main__":
    action = validate_action({"action_type": "approve_pr"})
    print("Action:", action.model_dump())

    obs = validate_observation({
        "file_name": "login.py",
        "diff": "...",
        "issues": ["sql_injection"],
        "metadata": {"lines_changed": 12, "difficulty": "medium"},
    })
    print("Observation:", obs.model_dump())

    state = validate_state({
        "current_step": 2,
        "done": False,
        "actions_taken": [{"action_type": "view_file", "comment": None, "step": 0}],
        "total_reward": 0.1,
        "current_file": "login.py",
    })
    print("State:", state.model_dump())

    # Invalid action test
    try:
        validate_action({"action_type": "hack_server"})
    except Exception as e:
        print(f"Caught: {e}")
