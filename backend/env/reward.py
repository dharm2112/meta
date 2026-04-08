"""Deterministic reward engine for interactive PR review tasks."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

try:
    from backend.env.reward_config import default_config, RewardConfig
except ImportError:
    from env.reward_config import default_config, RewardConfig


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
    
    # Default weights (now configurable via RewardConfig)
    RELEVANT_DIFF_WEIGHT = default_config.relevant_diff_weight
    RELEVANT_FILE_WEIGHT = default_config.relevant_file_weight
    BUG_TYPE_WEIGHT = default_config.bug_type_weight
    ROOT_CAUSE_WEIGHT = default_config.root_cause_weight
    FINAL_DECISION_WEIGHT = default_config.final_decision_weight
    IRRELEVANT_INSPECTION_PENALTY = default_config.irrelevant_inspection_penalty
    REPEATED_ACTION_PENALTY = default_config.repeated_action_penalty
    HALLUCINATED_COMMENT_PENALTY = default_config.hallucinated_comment_penalty

    @classmethod
    def score_actions(
        cls, 
        task: Dict[str, Any], 
        actions_taken: List[Dict[str, Any]],
        config: RewardConfig | None = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score actions with validation of task structure.
        
        Args:
            task: Task specification with ground_truth
            actions_taken: List of actions executed
            config: Optional custom reward configuration (uses default if None)
        
        Returns:
            Tuple of (score, breakdown_dict)
        """
        # Use custom config if provided
        if config is not None:
            diff_weight = config.relevant_diff_weight
            file_weight = config.relevant_file_weight
            bug_weight = config.bug_type_weight
            root_weight = config.root_cause_weight
            decision_weight = config.final_decision_weight
            irrel_penalty = config.irrelevant_inspection_penalty
            repeat_penalty = config.repeated_action_penalty
            halluc_penalty = config.hallucinated_comment_penalty
        else:
            diff_weight = cls.RELEVANT_DIFF_WEIGHT
            file_weight = cls.RELEVANT_FILE_WEIGHT
            bug_weight = cls.BUG_TYPE_WEIGHT
            root_weight = cls.ROOT_CAUSE_WEIGHT
            decision_weight = cls.FINAL_DECISION_WEIGHT
            irrel_penalty = cls.IRRELEVANT_INSPECTION_PENALTY
            repeat_penalty = cls.REPEATED_ACTION_PENALTY
            halluc_penalty = cls.HALLUCINATED_COMMENT_PENALTY
        
        # Validate required task fields
        required_fields = ["ground_truth", "changed_files"]
        for field in required_fields:
            if field not in task:
                raise ValueError(f"Task missing required field: '{field}'")
        
        ground_truth = task["ground_truth"]
        
        # Validate ground_truth structure
        required_gt_fields = ["relevant_files", "bug_type", "keywords", "root_cause_keywords", "correct_decision"]
        for field in required_gt_fields:
            if field not in ground_truth:
                raise ValueError(f"Task ground_truth missing required field: '{field}'")
        
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
            evidence_score += diff_weight
        if inspected_files & relevant_files:
            evidence_score += file_weight

        comment_text = "\n".join(comments)
        bug_type_hit, bug_hits = _contains_any(comment_text, [ground_truth["bug_type"], *ground_truth["keywords"]])
        root_cause_hit, root_hits = _contains_any(comment_text, ground_truth["root_cause_keywords"])

        issue_score = 0.0
        if bug_type_hit:
            issue_score += bug_weight
        if root_cause_hit:
            issue_score += root_weight

        decision_score = decision_weight if final_decision == ground_truth["correct_decision"] else 0.0

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
            irrelevant_inspections * irrel_penalty
            + repeated_actions * repeat_penalty
            + hallucinated_comments * halluc_penalty
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
