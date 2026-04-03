"""Modular reward engine for step-level and terminal scoring."""

from __future__ import annotations
from typing import Any, Dict, List


class RewardEngine:
    """Computes step rewards and terminal bonuses for code review actions."""

    CORRECT_DETECTION = 0.10
    INCORRECT_DETECTION = -0.05
    CORRECT_REQUEST_CHANGES = 0.30
    CORRECT_APPROVE = 0.30
    INCORRECT_APPROVE = -0.40
    ALL_ISSUES_BONUS = 0.40
    MISSED_CRITICAL_PENALTY = -0.20

    @staticmethod
    def compute_step_reward(
        action: Dict[str, Any],
        expected_issues: List[str],
        detected_issues: List[str],
    ) -> float:
        """Compute reward for a single step action."""
        action_type = action.get("action_type", "")
        comment = (action.get("comment") or "").lower()

        if action_type == "comment_issue":
            hit = any(issue in comment for issue in expected_issues)
            return RewardEngine.CORRECT_DETECTION if hit else RewardEngine.INCORRECT_DETECTION

        if action_type == "request_changes":
            undetected = set(expected_issues) - set(detected_issues)
            return RewardEngine.CORRECT_REQUEST_CHANGES if undetected else RewardEngine.CORRECT_REQUEST_CHANGES * 0.5

        if action_type == "approve_pr":
            undetected = set(expected_issues) - set(detected_issues)
            return RewardEngine.CORRECT_APPROVE if not undetected else RewardEngine.INCORRECT_APPROVE

        return 0.0

    @staticmethod
    def compute_terminal_reward(
        expected_issues: List[str],
        detected_issues: List[str],
    ) -> float:
        """Bonus/penalty applied at episode end."""
        undetected = set(expected_issues) - set(detected_issues)
        if not undetected:
            return RewardEngine.ALL_ISSUES_BONUS
        return RewardEngine.MISSED_CRITICAL_PENALTY * len(undetected)

    @staticmethod
    def compute_total_reward(step_rewards: List[float], terminal_reward: float) -> float:
        """Sum all step rewards and the terminal bonus."""
        return sum(step_rewards) + terminal_reward


if __name__ == "__main__":
    engine = RewardEngine()

    r1 = engine.compute_step_reward(
        {"action_type": "comment_issue", "comment": "sql_injection found"},
        ["sql_injection", "logic_bug"], [],
    )
    print(f"comment hit: {r1}")

    r2 = engine.compute_step_reward(
        {"action_type": "comment_issue", "comment": "looks fine"},
        ["sql_injection"], [],
    )
    print(f"comment miss: {r2}")

    t = engine.compute_terminal_reward(["sql_injection"], ["sql_injection"])
    print(f"terminal (all detected): {t}")

    total = engine.compute_total_reward([r1, r2], t)
    print(f"total: {total}")
