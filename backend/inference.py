"""Inference pipeline: batch evaluation loop over all tasks."""

from __future__ import annotations
import json
from typing import Any, Dict, List

from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, load_task
from grader.task_graders import get_grader
from grader.score_utils import format_score_for_logging
from baseline import BaselineAgent

PASS_THRESHOLDS = {"easy": 0.7, "medium": 0.6, "hard": 0.5}


def run_inference(agent=None) -> List[Dict[str, Any]]:
    """Run one episode per task; return list of result dicts."""
    if agent is None:
        agent = BaselineAgent()

    env = CodeReviewEnv()
    results = []

    for task_name in get_available_tasks():
        task = load_task(task_name)
        grader = get_grader(task_name)

        obs = env.reset(task)
        done = False
        step = 0

        print(f"\n[START] task={task_name}")

        while not done:
            action = agent.act(obs, env.state())
            obs, reward, done, info = env.step(action)
            print(f"[STEP]  task={task_name} step={step} action={action['action_type']} reward={reward:.4f}")
            step += 1

        score = grader.grade_episode(env.state()["actions_taken"])
        report = grader.generate_grade_report()
        status = report["grade_status"]

        print(format_score_for_logging(task_name, score, status))
        print(f"[END]   final_score={score:.4f}")

        results.append({
            "task": task_name,
            "score": score,
            "status": status,
            "steps": step,
            "report": report,
        })

    return results


if __name__ == "__main__":
    results = run_inference()
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    for r in results:
        print(f"  {r['task']:8s}  score={r['score']:.4f}  {r['status']}")
    print("=" * 40)
    print(json.dumps([{k: v for k, v in r.items() if k != "report"} for r in results], indent=2))
