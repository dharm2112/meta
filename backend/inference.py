"""Inference pipeline: batch evaluation loop over all tasks.

STDOUT FORMAT (required by OpenEnv):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure the backend directory is on sys.path (needed in Docker builds)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    # When imported from root inference.py
    from backend.baseline import BaselineAgent
    from backend.env.environment import CodeReviewEnv
    from backend.grader.task_graders import get_grader
    from backend.rl.q_learning import QLearningReviewAgent
    from backend.tasks.task_registry import get_available_tasks
except ImportError:
    # When run directly from backend directory
    from baseline import BaselineAgent
    from env.environment import CodeReviewEnv
    from grader.task_graders import get_grader
    from rl.q_learning import QLearningReviewAgent
    from tasks.task_registry import get_available_tasks

# ── Required environment variables ───────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional — if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

BENCHMARK = "code-review-env"


# ── Logging helpers (exact OpenEnv format) ───────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Main inference loop ──────────────────────────────────────────────
def run_inference(agent=None) -> List[Dict[str, Any]]:
    """Run one episode per task; return list of result dicts."""
    if agent is None:
        agent = BaselineAgent()

    env = CodeReviewEnv()
    results = []

    for task_name in get_available_tasks():
        grader = get_grader(task_name)

        rewards: List[float] = []
        steps_taken = 0
        score = 0.0
        success = False

        log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

        try:
            obs = env.reset(task_name)
            done = False

            while not done:
                action = agent.act(obs, env.state())
                obs, reward, done, info = env.step(action)
                steps_taken += 1
                rewards.append(reward)
                error = info.get("error") if isinstance(info, dict) else None

                log_step(
                    step=steps_taken,
                    action=action["action_type"],
                    reward=reward,
                    done=done,
                    error=error,
                )

            score = grader.grade_episode(env.state()["actions_taken"])
            score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
            success = score > 0.0

        except Exception as exc:
            score = 0.0
            success = False
            print(f"[DEBUG] Episode error: {exc}", flush=True)

        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

        results.append({
            "task": task_name,
            "score": score,
            "success": success,
            "steps": steps_taken,
        })

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation over all PR review tasks")
    parser.add_argument("--agent", choices=["heuristic", "rl", "groq"], default="heuristic")
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    parser.add_argument("--model", default=None, help="Model name override (only with --agent groq)")
    args = parser.parse_args()

    if args.agent == "groq":
        api_key = HF_TOKEN or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise SystemExit("ERROR: Set HF_TOKEN or GROQ_API_KEY environment variable.")
        from openai_agent import GroqReviewAgent
        model = args.model or MODEL_NAME
        agent = GroqReviewAgent(api_key=api_key, model=model, base_url=API_BASE_URL)
    elif args.agent == "rl":
        agent = QLearningReviewAgent.load(args.checkpoint)
        agent.epsilon = 0.0
    else:
        agent = BaselineAgent()

    results = run_inference(agent=agent)
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    for r in results:
        print(f"  {r['task']:8s}  score={r['score']:.2f}  success={r['success']}")
    print("=" * 40)
    print(json.dumps(results, indent=2))
