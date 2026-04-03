"""Score computation helpers."""

from __future__ import annotations
from typing import List, Set


def clamp_score(score: float) -> float:
    """Clamp score to [0.0, 1.0]."""
    return min(max(score, 0.0), 1.0)


def compute_detection_accuracy(expected: List[str], detected: List[str]) -> float:
    """Fraction of expected issues that were detected."""
    if not expected:
        return 1.0
    hits = len(set(expected) & set(detected))
    return hits / len(expected)


def compute_decision_accuracy(
    final_action: str,
    expected_issues: List[str],
    detected_issues: List[str],
) -> float:
    """1.0 if final decision is correct, 0.0 otherwise."""
    undetected = set(expected_issues) - set(detected_issues)
    if final_action == "request_changes" and undetected:
        return 1.0
    if final_action == "approve_pr" and not undetected:
        return 1.0
    if final_action == "request_changes" and not undetected:
        return 0.5  # conservative but issues were all found
    return 0.0


def format_score_for_logging(task_name: str, score: float, status: str) -> str:
    """Structured log line for inference pipeline."""
    return f"[RESULT] task={task_name} score={score:.4f} status={status}"


if __name__ == "__main__":
    print(clamp_score(1.5))   # 1.0
    print(clamp_score(-0.3))  # 0.0
    print(compute_detection_accuracy(["a", "b", "c"], ["a", "c"]))  # 0.6667
    print(compute_decision_accuracy("request_changes", ["a"], []))  # 1.0
    print(format_score_for_logging("medium", 0.62, "PASS"))
