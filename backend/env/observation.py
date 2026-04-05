"""Typed observation model returned by reset() and step()."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ObservationEventModel(BaseModel):
    kind: str
    title: str
    path: Optional[str] = None
    content: str


class ObservationModel(BaseModel):
    """Structured observation for the interactive code review environment."""

    task_id: str
    difficulty: str
    summary: str
    issue_title: str
    issue_body: str
    changed_files: List[str]
    available_files: List[str]
    available_actions: List[str]
    latest_event: ObservationEventModel
