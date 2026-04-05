"""Typed action model for the interactive PR review environment."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, model_validator


VALID_ACTIONS = (
    "inspect_diff",
    "inspect_file",
    "comment",
    "approve",
    "reject",
    "escalate",
)

PATH_ACTIONS = {"inspect_diff", "inspect_file"}
TEXT_ACTIONS = {"comment", "approve", "reject", "escalate"}


class ActionModel(BaseModel):
    """Structured action consumed by step()."""

    action_type: str
    path: Optional[str] = None
    text: Optional[str] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ActionModel":
        if self.action_type not in VALID_ACTIONS:
            raise ValueError(f"Invalid action_type '{self.action_type}'. Must be one of {VALID_ACTIONS}")
        if self.action_type in PATH_ACTIONS and not self.path:
            raise ValueError(f"action_type '{self.action_type}' requires 'path'")
        if self.action_type in TEXT_ACTIONS and not (self.text or "").strip():
            raise ValueError(f"action_type '{self.action_type}' requires non-empty 'text'")
        return self
