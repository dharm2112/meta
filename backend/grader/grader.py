"""Base grader for episode-level evaluation."""

from __future__ import annotations
from typing import Any, Dict, List

from env.reward import RewardEngine


class TaskGrader:
    """Grades a completed episode against hidden task metadata."""

    def __init__(self, task: Dict[str, Any], review_only: bool = False):
        """
        Initialize grader.
        
        Args:
            task: Task dictionary
            review_only: If True, grade without ground truth (custom uploads)
        """
        self.task = task
        self.review_only = review_only
        self._last_report: Dict[str, Any] = {}

    def grade_episode(self, actions_taken: List[Dict[str, Any]]) -> float:
        """
        Grade the episode based on actions taken.
        
        For review_only mode (custom uploads), grades based on:
        - How many files were inspected
        - Whether comments were made
        - Whether a decision was reached
        """
        if self.review_only:
            return self._grade_review_only(actions_taken)
        
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
    
    def _grade_review_only(self, actions_taken: List[Dict[str, Any]]) -> float:
        """Grade custom upload based on review completeness."""
        inspected_diffs = set()
        inspected_files = set()
        comments = []
        final_decision = None
        
        changed_files = set(self.task.get("changed_files", []))
        
        for action in actions_taken:
            action_type = action.get("action_type")
            path = action.get("path")
            text = action.get("text", "")
            
            if action_type == "inspect_diff" and path:
                inspected_diffs.add(path)
            elif action_type == "inspect_file" and path:
                inspected_files.add(path)
            elif action_type == "comment" and text:
                comments.append(text)
            elif action_type in ("approve", "reject", "escalate"):
                final_decision = action_type
        
        # Calculate coverage score
        total_changed = len(changed_files) if changed_files else 1
        coverage = len(inspected_diffs & changed_files) / total_changed
        
        # Score components for review-only mode
        coverage_score = min(coverage, 1.0) * 0.40  # 40% for file coverage
        comment_score = min(len(comments) / 3, 1.0) * 0.30  # 30% for comments (up to 3)
        decision_score = 0.30 if final_decision else 0.0  # 30% for making a decision
        
        total_score = coverage_score + comment_score + decision_score
        
        # Build report
        self._last_report = {
            "task_id": self.task["id"],
            "difficulty": "custom",
            "issue_title": self.task.get("issue_title", "Custom Review"),
            "review_mode": "review_only",
            "inspected_diffs": list(inspected_diffs),
            "inspected_files": list(inspected_files),
            "changed_files": list(changed_files),
            "coverage": round(coverage, 2),
            "comments_made": len(comments),
            "comments_preview": [c[:100] + "..." if len(c) > 100 else c for c in comments[:3]],
            "submitted_decision": final_decision,
            "coverage_score": round(coverage_score, 4),
            "comment_score": round(comment_score, 4),
            "decision_score": round(decision_score, 4),
            "final_score": round(total_score, 4),
            "grade_status": "REVIEWED",
            "note": "Custom uploads are graded on review completeness, not correctness.",
        }
        
        return total_score

    def generate_grade_report(self) -> Dict[str, Any]:
        """Return the report from the last grade_episode call."""
        return dict(self._last_report)
