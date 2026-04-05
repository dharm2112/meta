from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from env.environment import CodeReviewEnv
from grader.task_graders import get_grader
from rl.action_space import ReviewActionAdapter
from tasks.task_registry import get_available_tasks


class QLearningReviewAgent:
    """Tabular Q-learning agent over a discrete macro-action space."""

    def __init__(
        self,
        alpha: float = 0.35,
        gamma: float = 0.90,
        epsilon: float = 0.20,
        epsilon_min: float = 0.02,
        epsilon_decay: float = 0.995,
        adapter: Optional[ReviewActionAdapter] = None,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.adapter = adapter or ReviewActionAdapter()
        self.q_table: Dict[str, Dict[str, float]] = {}

    def act(self, observation: Dict[str, object], state: Dict[str, object], training: bool = False) -> Dict[str, str]:
        action_id = self.choose_action_id(observation, state, training=training)
        return self.adapter.to_env_action(action_id, observation, state)

    def choose_action_id(self, observation: Dict[str, object], state: Dict[str, object], training: bool = False) -> str:
        state_key = self.state_key(observation, state)
        available = self.adapter.available_action_ids(observation)
        self._ensure_state_actions(state_key, available)

        if training and random.random() < self.epsilon:
            return random.choice(available)

        ranked = self.q_table[state_key]
        best_value = max(ranked[action_id] for action_id in available)
        best_actions = [action_id for action_id in available if ranked[action_id] == best_value]
        return random.choice(best_actions)

    def update(
        self,
        observation: Dict[str, object],
        state: Dict[str, object],
        action_id: str,
        reward: float,
        next_observation: Dict[str, object],
        next_state: Dict[str, object],
        done: bool,
    ) -> None:
        state_key = self.state_key(observation, state)
        next_state_key = self.state_key(next_observation, next_state)
        available = self.adapter.available_action_ids(observation)
        next_available = self.adapter.available_action_ids(next_observation)
        self._ensure_state_actions(state_key, available)
        self._ensure_state_actions(next_state_key, next_available)

        current_q = self.q_table[state_key][action_id]
        future_q = 0.0 if done else max(self.q_table[next_state_key][candidate] for candidate in next_available)
        target = reward + (self.gamma * future_q)
        self.q_table[state_key][action_id] = current_q + self.alpha * (target - current_q)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def state_key(self, observation: Dict[str, object], state: Dict[str, object]) -> str:
        latest_event = observation.get("latest_event", {}) or {}
        comment_count = sum(1 for action in state.get("actions_taken", []) if action.get("action_type") == "comment")
        key = {
            "task_id": observation.get("task_id", ""),
            "step": state.get("current_step", 0),
            "inspected_diffs": sorted(state.get("inspected_diffs", [])),
            "inspected_files": sorted(state.get("inspected_files", [])),
            "comment_count": comment_count,
            "latest_kind": latest_event.get("kind", "summary"),
            "context": self.adapter.infer_context(observation),
        }
        return json.dumps(key, sort_keys=True)

    def _ensure_state_actions(self, state_key: str, action_ids: List[str]) -> None:
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        for action_id in action_ids:
            self.q_table[state_key].setdefault(action_id, 0.0)

    def save(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "q_table": self.q_table,
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str, adapter: Optional[ReviewActionAdapter] = None) -> "QLearningReviewAgent":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        agent = cls(
            alpha=payload.get("alpha", 0.35),
            gamma=payload.get("gamma", 0.90),
            epsilon=payload.get("epsilon", 0.0),
            epsilon_min=payload.get("epsilon_min", 0.02),
            epsilon_decay=payload.get("epsilon_decay", 0.995),
            adapter=adapter,
        )
        agent.q_table = {
            state_key: {action_id: float(value) for action_id, value in values.items()}
            for state_key, values in payload.get("q_table", {}).items()
        }
        return agent


def run_episode(env: CodeReviewEnv, agent: QLearningReviewAgent, task_id: str, training: bool = False) -> Tuple[float, Dict[str, object]]:
    observation = env.reset(task_id)
    state = env.state()
    done = False

    while not done:
        action_id = agent.choose_action_id(observation, state, training=training)
        action = agent.adapter.to_env_action(action_id, observation, state)
        next_observation, reward, done, _ = env.step(action)
        next_state = env.state()
        if training:
            agent.update(observation, state, action_id, reward, next_observation, next_state, done)
        observation = next_observation
        state = next_state

    grader = get_grader(task_id)
    score = grader.grade_episode(state["actions_taken"])
    return score, grader.generate_grade_report()


def train_agent(
    episodes: int = 1500,
    alpha: float = 0.35,
    gamma: float = 0.90,
    epsilon: float = 0.20,
    epsilon_min: float = 0.02,
    epsilon_decay: float = 0.995,
    seed: int = 7,
) -> Tuple[QLearningReviewAgent, List[Dict[str, object]]]:
    random.seed(seed)
    env = CodeReviewEnv()
    agent = QLearningReviewAgent(
        alpha=alpha,
        gamma=gamma,
        epsilon=epsilon,
        epsilon_min=epsilon_min,
        epsilon_decay=epsilon_decay,
    )
    task_ids = get_available_tasks()
    history: List[Dict[str, object]] = []

    for episode in range(1, episodes + 1):
        task_id = random.choice(task_ids)
        score, report = run_episode(env, agent, task_id, training=True)
        history.append(
            {
                "episode": episode,
                "task_id": task_id,
                "score": score,
                "status": report["grade_status"],
            }
        )
        agent.decay_epsilon()

    return agent, history


def evaluate_agent(agent: QLearningReviewAgent) -> List[Dict[str, object]]:
    env = CodeReviewEnv()
    results: List[Dict[str, object]] = []
    original_epsilon = agent.epsilon
    agent.epsilon = 0.0

    for task_id in get_available_tasks():
        score, report = run_episode(env, agent, task_id, training=False)
        results.append(
            {
                "task": task_id,
                "score": score,
                "status": report["grade_status"],
                "report": report,
            }
        )

    agent.epsilon = original_epsilon
    return results