"""Base grader for episode-level evaluation."""

from __future__ import annotations
from typing import Any, Dict, List

from env.reward import RewardEngine


class TaskGrader:
    """Grades a completed episode against hidden task metadata."""

    def __init__(self, task: Dict[str, Any]):
        self.task = task
        self._last_report: Dict[str, Any] = {}

    def grade_episode(self, actions_taken: List[Dict[str, Any]]) -> float:
        score, breakdown = RewardEngine.score_actions(self.task, actions_taken)
        status = "PASS" if score >= float(self.task["pass_threshold"]) else "FAIL"

        self._last_report = {
            "task_id": self.task["id"],
            "difficulty": self.task["difficulty"],
            "issue_title": self.task["issue_title"],
            "bug_type": self.task["ground_truth"]["bug_type"],
            "relevant_files": self.task["ground_truth"]["relevant_files"],
            "submitted_decision": breakdown["final_decision"],
            "correct_decision": breakdown["correct_decision"],
            "decision_correct": breakdown["final_decision"] == breakdown["correct_decision"],
            "evidence_score": breakdown["evidence_score"],
            "issue_identification_score": breakdown["issue_identification_score"],
            "decision_score": breakdown["decision_score"],
            "penalties": breakdown["penalties"],
            "keyword_hits": breakdown["keyword_hits"],
            "root_cause_hit": breakdown["root_cause_hit"],
            "inspected_diffs": breakdown["inspected_diffs"],
            "inspected_files": breakdown["inspected_files"],
            "pass_threshold": self.task["pass_threshold"],
            "final_score": round(score, 4),
            "grade_status": status,
        }
        return score

    def generate_grade_report(self) -> Dict[str, Any]:
        """Return the report from the last grade_episode call."""
        return dict(self._last_report)
