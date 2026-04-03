"""Hard benchmark task: auth bypass, performance regression, flaky tests."""

from __future__ import annotations
from typing import Any, Dict, List
from generator.pr_generator import PRGenerator


class TaskHard:
    """Simulates a PR with authentication bypass, performance regression, and flaky test behavior."""

    def get_task_name(self) -> str:
        return "security_and_performance_review"

    def get_pr_data(self) -> Dict[str, Any]:
        return PRGenerator.generate_hard_pr()

    def get_expected_issues(self) -> List[str]:
        return ["authentication_bypass", "performance_regression", "flaky_test_behavior"]

    def get_difficulty(self) -> str:
        return "hard"

    def get_description(self) -> str:
        return "Detect an authentication bypass, a performance regression, and flaky test behavior."
