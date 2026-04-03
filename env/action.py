"""Typed action model for agent-environment interaction."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator


VALID_ACTIONS = ("view_file", "comment_issue", "approve_pr", "request_changes")


class ActionModel(BaseModel):
    """Structured action consumed by step()."""

    action_type: str
    comment: Optional[str] = None

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"Invalid action_type '{v}'. Must be one of {VALID_ACTIONS}")
        return v


if __name__ == "__main__":
    a = ActionModel(action_type="comment_issue", comment="SQL injection detected")
    print(a.model_dump())

    try:
        ActionModel(action_type="invalid")
    except Exception as e:
        print(f"Validation error: {e}")
