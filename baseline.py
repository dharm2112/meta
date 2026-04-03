"""Baseline agent: keyword-based stub (no API key) or GPT-4 (with OPENAI_API_KEY)."""

from __future__ import annotations
import os
import argparse
from typing import Any, Dict, List

from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, load_task
from grader.task_graders import get_grader


# --- Stub agent (deterministic, no API) ---

class BaselineAgent:
    """Deterministic keyword-based reviewer used as a reproducible baseline."""

    def act(self, observation: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """state is the env.state() dict, used to inspect actions_taken."""
        actions_taken = state.get("actions_taken", [])
        step = len(actions_taken)

        if step == 0:
            return {"action_type": "view_file"}

        issues = observation.get("issues", [])

        # Find which issues have already been commented on
        commented = set()
        for a in actions_taken:
            if a.get("action_type") == "comment_issue":
                comment = (a.get("comment") or "").lower()
                for issue in issues:
                    if issue in comment:
                        commented.add(issue)

        # Comment on any remaining issue
        for issue in issues:
            if issue not in commented:
                return {
                    "action_type": "comment_issue",
                    "comment": f"{issue} detected in {observation.get('file_name', 'file')}",
                }

        # All issues commented — request changes if any found, else approve
        if issues:
            return {"action_type": "request_changes"}
        return {"action_type": "approve_pr"}


# --- GPT-4 agent (optional) ---

class GPT4BaselineAgent:
    """OpenAI GPT-4 powered baseline agent. Requires OPENAI_API_KEY env var."""

    SYSTEM_PROMPT = (
        "You are an expert code reviewer. You will be given a code diff and must "
        "identify issues. Respond ONLY with valid JSON: "
        '{"action_type": "<view_file|comment_issue|approve_pr|request_changes>", '
        '"comment": "<optional comment>"}'
    )

    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI()
        except ImportError:
            raise ImportError("Install openai: pip install openai")

    def act(self, observation: Dict[str, Any], history: List[str]) -> Dict[str, Any]:
        import json
        prompt = (
            f"File: {observation['file_name']}\n"
            f"Diff:\n{observation['diff']}\n"
            f"Known issues: {observation['issues']}\n"
            f"Actions so far: {history}\n"
            "What is your next action?"
        )
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)


def run_task(task_name: str, agent) -> float:
    env = CodeReviewEnv()
    task = load_task(task_name)
    grader = get_grader(task_name)

    obs = env.reset(task)
    done = False

    while not done:
        action = agent.act(obs, env.state())
        obs, reward, done, info = env.step(action)

    score = grader.grade_episode(env.state()["actions_taken"])
    return score


def main():
    parser = argparse.ArgumentParser(description="Code Review Assistant Baseline")
    parser.add_argument("--task", default="all", choices=["all", "easy", "medium", "hard"])
    parser.add_argument("--agent", default="stub", choices=["stub", "gpt4"])
    args = parser.parse_args()

    agent = GPT4BaselineAgent() if args.agent == "gpt4" else BaselineAgent()
    tasks = get_available_tasks() if args.task == "all" else [args.task]

    print("=" * 40)
    print("Code Review Assistant — Baseline Run")
    print("=" * 40)
    for task_name in tasks:
        score = run_task(task_name, agent)
        status = "PASS" if score >= {"easy": 0.7, "medium": 0.6, "hard": 0.5}[task_name] else "FAIL"
        print(f"Task {task_name:8s}: {score:.4f}  [{status}]")
    print("=" * 40)


if __name__ == "__main__":
    main()
