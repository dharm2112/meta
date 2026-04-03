"""Per-difficulty graders for easy, medium, and hard tasks."""

from __future__ import annotations
from typing import Any, Dict, List
from grader.grader import TaskGrader


class TaskEasyGrader(TaskGrader):
    """Grader for easy tasks: style and documentation issues."""

    def __init__(self):
        super().__init__(
            task_name="style_documentation_review",
            expected_issues=["missing_docstring", "unused_variable"],
        )


class TaskMediumGrader(TaskGrader):
    """Grader for medium tasks: security and testing issues."""

    def __init__(self):
        super().__init__(
            task_name="security_and_testing_review",
            expected_issues=["sql_injection", "missing_unit_tests", "logic_bug"],
        )


class TaskHardGrader(TaskGrader):
    """Grader for hard tasks: auth bypass, performance, flaky tests."""

    def __init__(self):
        super().__init__(
            task_name="security_and_performance_review",
            expected_issues=["authentication_bypass", "performance_regression", "flaky_test_behavior"],
        )


GRADER_REGISTRY: Dict[str, TaskGrader] = {
    "easy": TaskEasyGrader(),
    "medium": TaskMediumGrader(),
    "hard": TaskHardGrader(),
}


def get_grader(difficulty: str) -> TaskGrader:
    """Look up grader by difficulty. Raises KeyError if not found."""
    if difficulty not in GRADER_REGISTRY:
        raise KeyError(f"No grader for '{difficulty}'. Available: {list(GRADER_REGISTRY.keys())}")
    return GRADER_REGISTRY[difficulty]


if __name__ == "__main__":
    from grader.score_utils import format_score_for_logging

    # Medium grader demo
    grader = TaskMediumGrader()
    actions = [
        {"action_type": "view_file", "comment": None},
        {"action_type": "comment_issue", "comment": "sql_injection vulnerability in login.py"},
        {"action_type": "comment_issue", "comment": "logic_bug in auth check"},
        {"action_type": "request_changes", "comment": None},
    ]
    score = grader.grade_episode(actions)
    report = grader.generate_grade_report()
    print(format_score_for_logging(report["task_name"], score, report["grade_status"]))
    print(report)

    # All graders
    for diff in ["easy", "medium", "hard"]:
        g = get_grader(diff)
        s = g.grade_episode([], g.expected_issues)
        print(f"{diff}: {s:.4f}")
