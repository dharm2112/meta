from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# --- Typed Models ---

@dataclass
class MetadataModel:
    lines_changed: int
    task_type: str


@dataclass
class ObservationModel:
    file_name: str
    diff: str
    issues: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActionModel:
    action_type: str
    comment: Optional[str] = None

    VALID_ACTIONS: Tuple[str, ...] = (
        "view_file",
        "comment_issue",
        "approve_pr",
        "request_changes",
    )

    def validate(self) -> bool:
        return self.action_type in self.VALID_ACTIONS


@dataclass
class StateModel:
    current_step: int
    done: bool
    actions_taken: List[Dict[str, Any]]
    total_reward: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --- Reward Table (modular, replaceable by grader) ---

REWARD_TABLE: Dict[str, float] = {
    "view_file": 0.00,
    "comment_issue": 0.10,
    "approve_pr": 0.30,
    "request_changes": 0.30,
}

INVALID_ACTION_PENALTY: float = -0.05

TERMINAL_ACTIONS = frozenset({"approve_pr", "request_changes"})

DEFAULT_PR_DATA: Dict[str, Any] = {
    "file_name": "login.py",
    "diff": (
        '- cursor.execute("SELECT * FROM users WHERE id=" + user_id)\n'
        '+ cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
    ),
    "issues": ["sql_injection"],
    "metadata": {
        "lines_changed": 12,
        "task_type": "security_bug_detection",
        "author": "dev-bot",
        "pr_number": 42,
    },
}


# --- Environment ---

class CodeReviewEnv:
    """OpenEnv-compatible Code Review benchmark environment."""

    def __init__(self, max_steps: int = 10, pr_data: Optional[Dict[str, Any]] = None) -> None:
        self.max_steps = max_steps
        self._pr_data_template = pr_data if pr_data is not None else copy.deepcopy(DEFAULT_PR_DATA)

        self.pr_data: Dict[str, Any] = {}
        self.done: bool = True
        self.current_step: int = 0
        self.actions_taken: List[Dict[str, Any]] = []
        self.total_reward: float = 0.0

    def load_task(self, task: Any) -> None:
        """Load a task instance and update the PR data template."""
        self._pr_data_template = copy.deepcopy(task.get_pr_data())

    def reset(self, task: Optional[Any] = None) -> Dict[str, Any]:
        """Initialise a new episode and return the first observation."""
        if task is not None:
            if isinstance(task, str):
                from tasks.task_registry import load_task as _load
                task = _load(task)
            self.load_task(task)

        self.pr_data = copy.deepcopy(self._pr_data_template)
        self.done = False
        self.current_step = 0
        self.actions_taken = []
        self.total_reward = 0.0
        return self._build_observation().to_dict()

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Execute one agent action and advance the environment."""
        if self.done:
            raise RuntimeError("Episode has ended. Call reset() to start a new episode.")

        if not isinstance(action, dict):
            raise ValueError(f"action must be a dict, got {type(action).__name__}")
        if "action_type" not in action:
            raise ValueError("action dict must contain 'action_type' key")

        action_model = ActionModel(action_type=action["action_type"], comment=action.get("comment"))

        reward = self._compute_reward(action_model)
        self.total_reward += reward

        self.actions_taken.append({
            "action_type": action_model.action_type,
            "comment": action_model.comment,
            "step": self.current_step,
        })

        self.current_step += 1

        if action_model.action_type in TERMINAL_ACTIONS or self.current_step >= self.max_steps:
            self.done = True

        return self._build_observation().to_dict(), reward, self.done, self._build_info()

    def state(self) -> Dict[str, Any]:
        """Return a read-only snapshot of the environment state."""
        return StateModel(
            current_step=self.current_step,
            done=self.done,
            actions_taken=copy.deepcopy(self.actions_taken),
            total_reward=round(self.total_reward, 4),
        ).to_dict()

    def _build_observation(self) -> ObservationModel:
        return ObservationModel(
            file_name=self.pr_data["file_name"],
            diff=self.pr_data["diff"],
            issues=list(self.pr_data["issues"]),
            metadata=dict(self.pr_data["metadata"]),
        )

    @staticmethod
    def _compute_reward(action: ActionModel) -> float:
        if not action.validate():
            return INVALID_ACTION_PENALTY
        return REWARD_TABLE.get(action.action_type, 0.0)

    def _build_info(self) -> Dict[str, Any]:
        if self.done:
            last = self.actions_taken[-1]["action_type"] if self.actions_taken else None
            if last in TERMINAL_ACTIONS:
                status = f"terminated_by_{last}"
            elif self.current_step >= self.max_steps:
                status = "max_steps_reached"
            else:
                status = "terminated"
        else:
            status = "in_progress"

        return {
            "actions_taken": copy.deepcopy(self.actions_taken),
            "current_step": self.current_step,
            "episode_status": status,
        }


# --- Example Usage ---

if __name__ == "__main__":
    from tasks.task_registry import get_available_tasks, load_task

    env = CodeReviewEnv()

    # Run all registered tasks
    for task_name in get_available_tasks():
        task = load_task(task_name)
        obs = env.reset(task)
        print(f"\n[{task_name}] {task.get_description()}")
        print(f"  file: {obs['file_name']}, issues: {obs['issues']}")

        obs, reward, done, info = env.step({"action_type": "view_file"})
        obs, reward, done, info = env.step({
            "action_type": "comment_issue",
            "comment": f"Issues found: {task.get_expected_issues()}",
        })
        obs, reward, done, info = env.step({"action_type": "request_changes"})
        print(f"  final state: {env.state()}")

    # Also works with string shorthand
    obs = env.reset(task="easy")
    print(f"\n[string shorthand] file: {obs['file_name']}")
