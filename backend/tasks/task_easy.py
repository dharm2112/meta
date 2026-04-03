"""Easy benchmark task: style and documentation review."""

from __future__ import annotations
from typing import Any, Dict, List
from generator.pr_generator import PRGenerator


class TaskEasy:
    """Simulates a PR with style violations, missing docstrings, and unused variables."""

    def get_task_name(self) -> str:
        return "style_documentation_review"

    def get_pr_data(self) -> Dict[str, Any]:
        return PRGenerator.generate_easy_pr()

    def get_expected_issues(self) -> List[str]:
        return ["missing_docstring", "unused_variable"]

    def get_difficulty(self) -> str:
        return "easy"

    def get_description(self) -> str:
        return "Detect formatting and documentation issues in a utility function."
