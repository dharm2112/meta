"""Typed observation model returned by reset() and step()."""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class ObservationModel(BaseModel):
    """Structured observation for the code review environment."""

    file_name: str
    diff: str
    issues: List[str]
    metadata: Dict[str, Any]


if __name__ == "__main__":
    obs = ObservationModel(
        file_name="login.py",
        diff="SELECT * FROM users WHERE id=" + "user_id",
        issues=["sql_injection"],
        metadata={"lines_changed": 12, "difficulty": "medium"},
    )
    print(obs.model_dump())
    print(obs.model_dump_json())
