from __future__ import annotations

from typing import Dict, List


class ReviewActionAdapter:
    """Maps discrete RL action ids to environment actions."""

    COMMENT_LABELS = (
        "authorization",
        "null_handling",
        "security_policy",
        "generic",
    )

    def available_action_ids(self, observation: Dict[str, object]) -> List[str]:
        action_ids: List[str] = []
        for path in observation.get("changed_files", []):
            action_ids.append(f"inspect_diff::{path}")
        for path in observation.get("available_files", []):
            action_ids.append(f"inspect_file::{path}")
        for label in self.COMMENT_LABELS:
            action_ids.append(f"comment::{label}")
        action_ids.extend(["approve", "reject", "escalate"])
        return action_ids

    def to_env_action(self, action_id: str, observation: Dict[str, object], state: Dict[str, object]) -> Dict[str, str]:
        if action_id.startswith("inspect_diff::"):
            return {"action_type": "inspect_diff", "path": action_id.split("::", 1)[1]}
        if action_id.startswith("inspect_file::"):
            return {"action_type": "inspect_file", "path": action_id.split("::", 1)[1]}
        if action_id.startswith("comment::"):
            label = action_id.split("::", 1)[1]
            return {"action_type": "comment", "text": self.comment_text(label)}
        if action_id == "approve":
            return {"action_type": "approve", "text": self.decision_text("approve", observation, state)}
        if action_id == "reject":
            return {"action_type": "reject", "text": self.decision_text("reject", observation, state)}
        if action_id == "escalate":
            return {"action_type": "escalate", "text": self.decision_text("escalate", observation, state)}
        raise KeyError(f"Unknown action id '{action_id}'")

    @staticmethod
    def infer_context(observation: Dict[str, object]) -> str:
        latest_event = observation.get("latest_event", {}) or {}
        context = " ".join(
            [
                str(observation.get("issue_title", "")),
                str(observation.get("issue_body", "")),
                str(observation.get("summary", "")),
                str(latest_event.get("content", "")),
            ]
        ).lower()
        if any(token in context for token in ["admin", "authorization", "role", "export endpoint"]):
            return "authorization"
        if any(token in context for token in ["null", "none", "missing email", "background jobs", "service layer"]):
            return "null_handling"
        if any(token in context for token in ["policy", "fallback", "service token", "human review", "stale token"]):
            return "security_policy"
        return "generic"

    def comment_text(self, label: str) -> str:
        templates = {
            "authorization": "Authorization issue: the patch still lacks the admin role check, so an authenticated user can reach the protected export path.",
            "null_handling": "Null-handling issue: the controller guard helps one path, but the service layer still processes a missing email from background jobs.",
            "security_policy": "Security policy concern: the fallback path can still accept a stale service token, so this auth change needs human review.",
            "generic": "The patch still leaves an unresolved defect and needs additional review.",
        }
        return templates[label]

    def decision_text(self, decision: str, observation: Dict[str, object], state: Dict[str, object]) -> str:
        context = self.infer_context(observation)
        if decision == "approve":
            return "Approving because the available evidence looks complete and no blocking issue remains."
        if decision == "reject":
            reasons = {
                "authorization": "Rejecting because the export route still lacks an admin authorization guard.",
                "null_handling": "Rejecting because the service layer still mishandles missing email input outside the controller path.",
                "security_policy": "Rejecting because the auth fallback behavior is still risky and unresolved.",
                "generic": "Rejecting because the review still shows a substantive defect.",
            }
            return reasons[context]
        if decision == "escalate":
            reasons = {
                "authorization": "Escalating because this access-control change needs human review.",
                "null_handling": "Escalating because the fix path is incomplete and needs manual review.",
                "security_policy": "Escalating because policy-sensitive auth fallback behavior still requires human review.",
                "generic": "Escalating because the review outcome is still uncertain.",
            }
            return reasons[context]
        raise KeyError(f"Unknown decision '{decision}'")