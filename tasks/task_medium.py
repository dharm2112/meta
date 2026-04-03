"""Medium benchmark task: security and testing review."""

from __future__ import annotations
from typing import Any, Dict, List
from generator.pr_generator import PRGenerator


class TaskMedium:
    """Simulates a PR with SQL injection, missing tests, and a logic bug."""

    def get_task_name(self) -> str:
        return "security_and_testing_review"

    def get_pr_data(self) -> Dict[str, Any]:
        return PRGenerator.generate_medium_pr()

    def get_expected_issues(self) -> List[str]:
        return ["sql_injection", "missing_unit_tests", "logic_bug"]

    def get_difficulty(self) -> str:
        return "medium"

    def get_description(self) -> str:
        return "Detect a SQL injection vulnerability, flag missing tests, and find a logic bug."
