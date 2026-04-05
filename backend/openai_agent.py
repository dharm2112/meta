"""Groq API-based review agent for the offline PR review environment."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]


SYSTEM_PROMPT = """\
You are a senior software engineer reviewing a pull request.

You will receive the current observation (PR metadata, diffs, files) and state
(actions taken so far, step count).  Respond with exactly ONE JSON action object.

Available actions:
- {"action_type": "inspect_diff", "path": "<file>"}  – reveal the diff of a changed file
- {"action_type": "inspect_file", "path": "<file>"}  – reveal full contents of a file
- {"action_type": "comment", "text": "<your review comment>"}  – post a review comment
- {"action_type": "approve", "text": "<reason>"}  – approve the PR (terminal)
- {"action_type": "reject", "text": "<reason>"}   – reject the PR (terminal)
- {"action_type": "escalate", "text": "<reason>"}  – escalate for human review (terminal)

Strategy:
1. First inspect diffs of changed files to understand what changed.
2. Inspect additional files if needed for context.
3. Leave a comment identifying the bug and root cause.
4. Make a final decision: approve, reject, or escalate.

IMPORTANT: Respond with ONLY the JSON action object, no markdown, no explanation.
"""


class GroqReviewAgent:
    """Uses an OpenAI-compatible API to decide actions."""

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
        base_url: str | None = None,
    ) -> None:
        if OpenAI is None:
            raise ImportError("Install the openai package: pip install openai>=1.0")
        self.client = OpenAI(
            api_key=api_key or os.getenv("HF_TOKEN") or os.getenv("GROQ_API_KEY"),
            base_url=base_url or os.getenv("API_BASE_URL") or self.DEFAULT_BASE_URL,
        )
        self.model = model

    def act(self, observation: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        user_content = json.dumps(
            {"observation": _slim_obs(observation), "state": _slim_state(state)},
            indent=2,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        action = json.loads(raw)
        if "action_type" not in action:
            raise ValueError(f"Model returned invalid action: {raw}")
        return action


def _slim_obs(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the fields the model needs."""
    return {
        "task_id": obs.get("task_id"),
        "difficulty": obs.get("difficulty"),
        "summary": obs.get("summary"),
        "issue_title": obs.get("issue_title"),
        "issue_body": obs.get("issue_body"),
        "changed_files": obs.get("changed_files"),
        "available_files": obs.get("available_files"),
        "available_actions": obs.get("available_actions"),
        "latest_event": obs.get("latest_event"),
    }


def _slim_state(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "current_step": state.get("current_step"),
        "max_steps": state.get("max_steps"),
        "inspected_diffs": state.get("inspected_diffs"),
        "inspected_files": state.get("inspected_files"),
        "actions_taken": [
            {"step": a["step"], "action_type": a["action_type"], "path": a.get("path")}
            for a in state.get("actions_taken", [])
        ],
    }
