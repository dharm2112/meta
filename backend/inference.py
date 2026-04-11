"""Inference pipeline: sequential evaluation loop over all tasks.

Tasks are processed ONE AT A TIME through a ``TaskQueue`` with a
configurable inter-task delay (default 3 s).  Each individual LLM call
inside the agent is further throttled by the shared ``global_rate_limiter``
(10 RPM), so the system is rate-limit-safe under any load.

STDOUT FORMAT (required by OpenEnv):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Environment variables
---------------------
MOCK_INFERENCE=1        Skip real execution and return deterministic mock results
                        (useful in CI / unit-test contexts to avoid API calls).
INTER_TASK_DELAY_SECONDS  Pause between tasks (default: 3.0)
MAX_REQUESTS_PER_MINUTE   Global RPM cap for the LiteLLM agent (default: 10)
MIN_DELAY_SECONDS         Per-call floor delay in seconds (default: 6.0)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# ── Path setup (needed in Docker builds) ─────────────────────────────────────
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    # When run directly from the backend directory
    from baseline import BaselineAgent
    from env.environment import CodeReviewEnv
    from grader.task_graders import get_grader
    from rl.q_learning import QLearningReviewAgent
    from tasks.task_registry import get_available_tasks
    from openai_agent import LiteLLMReviewAgent
    from task_queue import TaskQueue
except ImportError:
    # When imported from root-level inference.py (Docker / platform runner)
    from backend.baseline import BaselineAgent
    from backend.env.environment import CodeReviewEnv
    from backend.grader.task_graders import get_grader
    from backend.rl.q_learning import QLearningReviewAgent
    from backend.tasks.task_registry import get_available_tasks
    from backend.openai_agent import LiteLLMReviewAgent
    from backend.task_queue import TaskQueue

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Environment configuration ─────────────────────────────────────────────────
API_KEY       = os.environ.get("API_KEY")
API_BASE_URL  = os.environ.get("API_BASE_URL")
MODEL_NAME    = os.environ.get("MODEL_NAME", "gpt-4o-mini")
MOCK_INFERENCE = os.environ.get("MOCK_INFERENCE", "0").strip() == "1"

BENCHMARK = "code-review-env"


# ── OpenEnv logging helpers ───────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val  = error if error else "null"
    done_val   = str(done).lower()
    print(
        f"[STEP]  step={step} action={action} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END]   success={str(success).lower()} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Single-task runner (enqueued into TaskQueue) ──────────────────────────────

def _run_single_task(task_name: str, agent: Any) -> Dict[str, Any]:
    """Run one complete evaluation episode for ``task_name``.

    This function is designed to be called inside the TaskQueue so that
    tasks are never executed concurrently.

    Returns a result dict compatible with the OpenEnv summary format.
    """
    env    = CodeReviewEnv()
    grader = get_grader(task_name)

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs     = env.reset(task_name)
        done    = False
        rewards: List[float] = []

        while not done:
            try:
                action = agent.act(obs, env.state())
            except Exception as act_err:
                logger.error("[inference] agent.act error on %s: %s", task_name, act_err)
                # Force a safe terminal action so the episode ends cleanly
                action = {"action_type": "escalate", "text": f"agent error: {act_err}"}

            action_str  = action.get("action_type", "unknown")
            obs, reward, done, info = env.step(action)
            rewards.append(reward)
            # info dict from env._build_info() has 'episode_status', not 'error'
            episode_status = info.get("episode_status", "") if isinstance(info, dict) else ""
            step_error = episode_status if "error" in episode_status else None
            log_step(
                step=env.state().get("current_step", len(rewards)),
                action=action_str,
                reward=reward,
                done=done,
                error=step_error,
            )

        state  = env.state()
        score  = grader.grade_episode(state["actions_taken"])
        # pass_threshold lives in the task dict, not on the grader object
        pass_threshold = grader.task.get("pass_threshold", 0.5)
        passed = score >= pass_threshold

        log_end(success=passed, steps=len(rewards), score=score, rewards=rewards)

        return {
            "task":    task_name,
            "score":   score,
            "success": passed,
            "steps":   len(rewards),
        }

    except Exception as exc:
        logger.error("[inference] Fatal error in task %s: %s", task_name, exc, exc_info=True)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return {
            "task":    task_name,
            "score":   0.0,
            "success": False,
            "steps":   0,
            "error":   str(exc),
        }


# ── Mock path (for CI / unit tests) ───────────────────────────────────────────

def _run_mock() -> List[Dict[str, Any]]:
    """Return deterministic mock results without making any API calls."""
    mock_tasks = [
        "easy_auth_001",
        "easy_csrf_001",
        "hard_security_001",
        "medium_null_001",
        "medium_race_001",
    ]
    results = []
    for task_name in mock_tasks:
        log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
        log_step(step=1, action="inspect_diff", reward=0.15, done=False, error=None)
        log_step(step=2, action="comment",      reward=0.15, done=False, error=None)
        log_step(step=3, action="reject",       reward=0.50, done=True,  error=None)
        log_end(success=True, steps=3, score=0.80, rewards=[0.15, 0.15, 0.50])
        results.append({"task": task_name, "score": 0.80, "success": True, "steps": 3})
    return results


# ── Main entry point ──────────────────────────────────────────────────────────

def run_inference(agent: Any = None) -> List[Dict[str, Any]]:
    """Run one evaluation episode per task and return a list of result dicts.

    Tasks are processed sequentially via ``TaskQueue`` with a configurable
    inter-task delay to avoid bursting the API rate limit.

    Set ``MOCK_INFERENCE=1`` to skip real calls (useful for CI pipelines).
    """
    if MOCK_INFERENCE:
        logger.info("[inference] MOCK_INFERENCE=1 — returning deterministic mock results.")
        return _run_mock()

    # Resolve agent
    if agent is None:
        if API_KEY and API_BASE_URL:
            agent = LiteLLMReviewAgent()
        else:
            logger.warning(
                "[inference] API_KEY / API_BASE_URL not set — falling back to BaselineAgent."
            )
            agent = BaselineAgent()

    task_names = get_available_tasks()
    logger.info("[inference] Evaluating %d task(s): %s", len(task_names), task_names)

    # Build a queue that processes tasks one-at-a-time with an inter-task pause.
    # The agent's internal calls are additionally throttled by global_rate_limiter.
    queue = TaskQueue()  # inter_task_delay read from INTER_TASK_DELAY_SECONDS env var
    for task_name in task_names:
        queue.enqueue(_run_single_task, task_name, agent)

    raw_results = queue.run_all()

    # Normalise any error entries returned by the TaskQueue
    results: List[Dict[str, Any]] = []
    for item in raw_results:
        if isinstance(item, dict) and "error" in item and "task" not in item:
            results.append({
                "task":    f"unknown_task_{item.get('task_num', '?')}",
                "score":   0.0,
                "success": False,
                "steps":   0,
                "error":   item["error"],
            })
        else:
            results.append(item)

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sequential evaluation over all PR review tasks")
    parser.add_argument("--agent",      choices=["heuristic", "rl", "llm"], default="llm")
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    parser.add_argument("--model",      default=None, help="Model name override")
    args = parser.parse_args()

    if args.agent == "llm":
        if not API_KEY or not API_BASE_URL:
            raise SystemExit("ERROR: Set API_KEY and API_BASE_URL environment variables.")
        agent = LiteLLMReviewAgent(model=args.model)
    elif args.agent == "rl":
        agent = QLearningReviewAgent.load(args.checkpoint)
        agent.epsilon = 0.0
    else:
        agent = BaselineAgent()

    final_results = run_inference(agent=agent)

    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    for r in final_results:
        status = "✓" if r.get("success") else "✗"
        print(f"  {status} {r['task']:25s}  score={r['score']:.2f}  steps={r.get('steps', 0)}")
    print("=" * 40)
    print(json.dumps(final_results, indent=2))
