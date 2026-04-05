from __future__ import annotations

import copy
from typing import Any, Dict, Optional, Tuple

from env.action import ActionModel, VALID_ACTIONS
from env.observation import ObservationEventModel, ObservationModel
from env.reward import RewardEngine
from env.state import StateModel
from tasks.task_registry import load_task


TERMINAL_ACTIONS = frozenset({"approve", "reject", "escalate"})


class CodeReviewEnv:
    """Interactive offline PR review environment with deterministic scoring."""

    def __init__(self, max_steps: int = 6, task: Optional[Dict[str, Any]] = None) -> None:
        self.default_max_steps = max_steps
        self.task: Dict[str, Any] = copy.deepcopy(task) if task is not None else {}
        self.done = True
        self.current_step = 0
        self.max_steps = max_steps
        self.total_reward = 0.0
        self.actions_taken = []
        self.inspected_diffs = set()
        self.inspected_files = set()
        self.final_decision: Optional[str] = None
        self.latest_event = ObservationEventModel(
            kind="summary",
            title="No task loaded",
            content="Call reset() with a task id to start a review episode.",
        )

    def reset(self, task: Optional[Any] = None) -> Dict[str, Any]:
        if task is not None:
            self.task = copy.deepcopy(load_task(task) if isinstance(task, str) else task)
        if not self.task:
            raise ValueError("reset() requires a task id or task payload")

        self.done = False
        self.current_step = 0
        self.max_steps = int(self.task.get("max_steps", self.default_max_steps))
        self.total_reward = 0.0
        self.actions_taken = []
        self.inspected_diffs = set()
        self.inspected_files = set()
        self.final_decision = None
        self.latest_event = ObservationEventModel(
            kind="summary",
            title="PR summary",
            content=self.task["summary"],
        )
        return self._build_observation().model_dump()

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self.done:
            raise RuntimeError("Episode has ended. Call reset() to start a new episode.")

        previous_score, _ = RewardEngine.score_actions(self.task, self.actions_taken)
        action_model = ActionModel(**action)
        self.latest_event = self._handle_action(action_model)

        action_record = {
            "step": self.current_step,
            "action_type": action_model.action_type,
            "path": action_model.path,
            "text": action_model.text,
        }
        self.actions_taken.append(action_record)
        self.current_step += 1

        if action_model.action_type in TERMINAL_ACTIONS or self.current_step >= self.max_steps:
            self.done = True

        updated_score, breakdown = RewardEngine.score_actions(self.task, self.actions_taken)
        reward = round(updated_score - previous_score, 4)
        self.total_reward = updated_score

        return self._build_observation().model_dump(), reward, self.done, self._build_info(breakdown)

    def state(self) -> Dict[str, Any]:
        return StateModel(
            task_id=self.task["id"],
            current_step=self.current_step,
            max_steps=self.max_steps,
            done=self.done,
            total_reward=round(self.total_reward, 4),
            actions_taken=copy.deepcopy(self.actions_taken),
            inspected_diffs=sorted(self.inspected_diffs),
            inspected_files=sorted(self.inspected_files),
            final_decision=self.final_decision,
        ).model_dump()

    def _handle_action(self, action: ActionModel) -> ObservationEventModel:
        if action.action_type == "inspect_diff":
            if action.path not in self.task["changed_files"]:
                raise ValueError(f"Unknown changed file '{action.path}'")
            self.inspected_diffs.add(action.path)
            return ObservationEventModel(
                kind="diff",
                title="Diff revealed",
                path=action.path,
                content=self.task["diffs"][action.path],
            )

        if action.action_type == "inspect_file":
            if action.path not in self.task["files"]:
                raise ValueError(f"Unknown file '{action.path}'")
            self.inspected_files.add(action.path)
            return ObservationEventModel(
                kind="file",
                title="File revealed",
                path=action.path,
                content=self.task["files"][action.path],
            )

        if action.action_type == "comment":
            return ObservationEventModel(
                kind="comment",
                title="Comment recorded",
                content=action.text or "",
            )

        self.final_decision = action.action_type
        return ObservationEventModel(
            kind="decision",
            title="Final decision submitted",
            content=action.text or "",
        )

    def _build_observation(self) -> ObservationModel:
        return ObservationModel(
            task_id=self.task["id"],
            difficulty=self.task["difficulty"],
            summary=self.task["summary"],
            issue_title=self.task["issue_title"],
            issue_body=self.task["issue_body"],
            changed_files=list(self.task["changed_files"]),
            available_files=sorted(self.task["files"].keys()),
            available_actions=list(VALID_ACTIONS),
            latest_event=self.latest_event,
        )

    def _build_info(self, breakdown: Dict[str, Any]) -> Dict[str, Any]:
        status = "in_progress"
        if self.done and self.current_step >= self.max_steps and self.final_decision is None:
            status = "max_steps_reached"
        elif self.done and self.final_decision is not None:
            status = f"terminated_by_{self.final_decision}"

        return {
            "episode_status": status,
            "current_step": self.current_step,
            "score_breakdown": breakdown,
        }
