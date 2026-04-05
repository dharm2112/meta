from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


TASKS_DIR = Path(__file__).resolve().parent / "data"
REQUIRED_KEYS = {
    "id",
    "label",
    "difficulty",
    "description",
    "summary",
    "issue_title",
    "issue_body",
    "changed_files",
    "diffs",
    "files",
    "ground_truth",
    "pass_threshold",
    "max_steps",
}


def _task_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


def _validate_task(task: Dict[str, Any]) -> Dict[str, Any]:
    missing = REQUIRED_KEYS - set(task.keys())
    if missing:
        raise ValueError(f"Task '{task.get('id', '<unknown>')}' missing keys: {sorted(missing)}")

    ground_truth = task["ground_truth"]
    for key in ["correct_decision", "relevant_files", "bug_type", "keywords", "root_cause_keywords", "uncertain"]:
        if key not in ground_truth:
            raise ValueError(f"Task '{task['id']}' missing ground_truth.{key}")

    return task


def load_task(task_id: str) -> Dict[str, Any]:
    path = _task_path(task_id)
    if not path.exists():
        raise KeyError(f"Unknown task '{task_id}'")
    with path.open("r", encoding="utf-8") as handle:
        return _validate_task(json.load(handle))


def get_available_tasks() -> List[str]:
    return sorted(path.stem for path in TASKS_DIR.glob("*.json"))


def get_task_catalog() -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    for task_id in get_available_tasks():
        task = load_task(task_id)
        catalog.append(
            {
                "id": task["id"],
                "label": task["label"],
                "difficulty": task["difficulty"],
                "description": task["description"],
                "issue_title": task["issue_title"],
                "pass_threshold": task["pass_threshold"],
            }
        )
    return catalog