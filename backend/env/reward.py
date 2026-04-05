"""Deterministic reward engine for interactive PR review tasks."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def clamp_score(score: float) -> float:
    return min(max(score, 0.0), 1.0)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().replace("_", " ").split())


def _contains_any(text: str, phrases: Iterable[str]) -> Tuple[bool, List[str]]:
    normalized = _normalize(text)
    hits: List[str] = []
    for phrase in phrases:
        normalized_phrase = _normalize(phrase)
        if normalized_phrase and normalized_phrase in normalized:
            hits.append(phrase)
    return bool(hits), hits


class RewardEngine:
    """Scores evidence gathering, issue identification, and final decisions."""

    RELEVANT_DIFF_WEIGHT = 0.15
    RELEVANT_FILE_WEIGHT = 0.10
    BUG_TYPE_WEIGHT = 0.15
    ROOT_CAUSE_WEIGHT = 0.10
    FINAL_DECISION_WEIGHT = 0.50
    IRRELEVANT_INSPECTION_PENALTY = 0.03
    REPEATED_ACTION_PENALTY = 0.02
    HALLUCINATED_COMMENT_PENALTY = 0.05

    @classmethod
    def score_actions(cls, task: Dict[str, Any], actions_taken: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        ground_truth = task["ground_truth"]
        relevant_files = set(ground_truth["relevant_files"])
        changed_files = set(task["changed_files"])
        relevant_changed_files = relevant_files & changed_files

        inspected_diffs = {action["path"] for action in actions_taken if action["action_type"] == "inspect_diff" and action.get("path")}
        inspected_files = {action["path"] for action in actions_taken if action["action_type"] == "inspect_file" and action.get("path")}
        comments = [action.get("text", "") for action in actions_taken if action["action_type"] == "comment"]
        final_actions = [action for action in actions_taken if action["action_type"] in {"approve", "reject", "escalate"}]
        final_decision = final_actions[-1]["action_type"] if final_actions else None

        evidence_score = 0.0
        if inspected_diffs & relevant_changed_files:
            evidence_score += cls.RELEVANT_DIFF_WEIGHT
        if inspected_files & relevant_files:
            evidence_score += cls.RELEVANT_FILE_WEIGHT

        comment_text = "\n".join(comments)
        bug_type_hit, bug_hits = _contains_any(comment_text, [ground_truth["bug_type"], *ground_truth["keywords"]])
        root_cause_hit, root_hits = _contains_any(comment_text, ground_truth["root_cause_keywords"])

        issue_score = 0.0
        if bug_type_hit:
            issue_score += cls.BUG_TYPE_WEIGHT
        if root_cause_hit:
            issue_score += cls.ROOT_CAUSE_WEIGHT

        decision_score = cls.FINAL_DECISION_WEIGHT if final_decision == ground_truth["correct_decision"] else 0.0

        irrelevant_inspections = 0
        seen_actions = set()
        repeated_actions = 0
        hallucinated_comments = 0

        for action in actions_taken:
            action_key = (action["action_type"], action.get("path"), _normalize(action.get("text") or ""))
            if action_key in seen_actions:
                repeated_actions += 1
            else:
                seen_actions.add(action_key)

            if action["action_type"] == "inspect_diff" and action.get("path") not in relevant_changed_files:
                irrelevant_inspections += 1
            if action["action_type"] == "inspect_file" and action.get("path") not in relevant_files:
                irrelevant_inspections += 1
            if action["action_type"] == "comment":
                comment_hit, _ = _contains_any(action.get("text", ""), [ground_truth["bug_type"], *ground_truth["keywords"], *ground_truth["root_cause_keywords"]])
                if not comment_hit:
                    hallucinated_comments += 1

        penalties = (
            irrelevant_inspections * cls.IRRELEVANT_INSPECTION_PENALTY
            + repeated_actions * cls.REPEATED_ACTION_PENALTY
            + hallucinated_comments * cls.HALLUCINATED_COMMENT_PENALTY
        )

        raw_score = evidence_score + issue_score + decision_score - penalties
        score = clamp_score(raw_score)
        breakdown = {
            "evidence_score": round(evidence_score, 4),
            "issue_identification_score": round(issue_score, 4),
            "decision_score": round(decision_score, 4),
            "penalties": round(penalties, 4),
            "final_decision": final_decision,
            "correct_decision": ground_truth["correct_decision"],
            "bug_type_hit": bug_type_hit,
            "root_cause_hit": root_cause_hit,
            "keyword_hits": sorted(set(bug_hits + root_hits)),
            "inspected_diffs": sorted(inspected_diffs),
            "inspected_files": sorted(inspected_files),
            "irrelevant_inspections": irrelevant_inspections,
            "repeated_actions": repeated_actions,
            "hallucinated_comments": hallucinated_comments,
        }
        return round(score, 4), breakdown
