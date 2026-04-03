"""Base grader for episode-level evaluation."""

from __future__ import annotations
from typing import Any, Dict, List
from grader.score_utils import clamp_score, compute_detection_accuracy, compute_decision_accuracy


class TaskGrader:
    """Grades a completed episode against expected issues."""

    DETECTION_WEIGHT = 0.60
    DECISION_WEIGHT = 0.40

    def __init__(self, task_name: str = "", expected_issues: List[str] = None):
        self.task_name = task_name
        self.expected_issues = expected_issues or []
        self._last_report: Dict[str, Any] = {}

    def grade_episode(
        self,
        actions_taken: List[Dict[str, Any]],
        expected_issues: List[str] = None,
    ) -> float:
        """Grade a full episode. Returns normalized score in [0.0, 1.0]."""
        expected = expected_issues or self.expected_issues
        detected = self._extract_detected_issues(actions_taken, expected)
        final_action = self._extract_final_action(actions_taken)

        detection_acc = compute_detection_accuracy(expected, detected)
        decision_acc = compute_decision_accuracy(final_action, expected, detected)

        raw = (detection_acc * self.DETECTION_WEIGHT) + (decision_acc * self.DECISION_WEIGHT)
        score = self.normalize_score(raw)

        status = "PASS" if score >= 0.50 else "FAIL"
        self._last_report = {
            "task_name": self.task_name,
            "issues_expected": expected,
            "issues_detected": detected,
            "detection_accuracy": round(detection_acc, 4),
            "decision_correct": decision_acc == 1.0,
            "final_score": score,
            "grade_status": status,
        }
        return score

    def normalize_score(self, raw_score: float) -> float:
        """Clamp raw score to [0.0, 1.0]."""
        return clamp_score(raw_score)

    def generate_grade_report(self) -> Dict[str, Any]:
        """Return the report from the last grade_episode call."""
        return dict(self._last_report)

    @staticmethod
    def _extract_detected_issues(
        actions: List[Dict[str, Any]],
        expected: List[str],
    ) -> List[str]:
        """Parse comment actions to find which expected issues were mentioned."""
        detected: List[str] = []
        for a in actions:
            if a.get("action_type") != "comment_issue":
                continue
            comment = (a.get("comment") or "").lower()
            for issue in expected:
                if issue in comment and issue not in detected:
                    detected.append(issue)
        return detected

    @staticmethod
    def _extract_final_action(actions: List[Dict[str, Any]]) -> str:
        """Return the last action_type in the episode."""
        if not actions:
            return ""
        return actions[-1].get("action_type", "")


if __name__ == "__main__":
    grader = TaskGrader(task_name="demo", expected_issues=["sql_injection", "logic_bug"])
    actions = [
        {"action_type": "view_file", "comment": None},
        {"action_type": "comment_issue", "comment": "Found sql_injection in query"},
        {"action_type": "request_changes", "comment": None},
    ]
    score = grader.grade_episode(actions)
    print(f"Score: {score}")
    print(f"Report: {grader.generate_grade_report()}")
