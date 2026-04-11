"""Comprehensive evaluation suite for RL and LLM agents.

Tasks are processed sequentially through ``TaskQueue``.  For LLM-based
agents every individual call is already throttled by ``global_rate_limiter``
inside the agent itself.  The ``TaskQueue`` adds an additional inter-task
pause to drain the sliding-window between episodes.

Usage
-----
    python eval_suite.py --agent baseline
    python eval_suite.py --agent rl --checkpoint checkpoints/q_learning_policy.json
    python eval_suite.py --agent compare
    python eval_suite.py --agent baseline --output results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    from env.environment import CodeReviewEnv
    from grader.task_graders import get_grader
    from tasks.task_registry import get_available_tasks
    from rl.q_learning import QLearningReviewAgent
    from baseline import BaselineAgent
    from task_queue import TaskQueue
except ImportError:
    from backend.env.environment import CodeReviewEnv
    from backend.grader.task_graders import get_grader
    from backend.tasks.task_registry import get_available_tasks
    from backend.rl.q_learning import QLearningReviewAgent
    from backend.baseline import BaselineAgent
    from backend.task_queue import TaskQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Seconds to wait between agent.act() calls within a single task episode.
# For LLM agents the global_rate_limiter already enforces this; this constant
# acts as an extra safety margin for synchronous baseline/RL calls.
_INTRA_TASK_STEP_DELAY: float = 0.0   # no extra delay for non-LLM agents

# Seconds to wait between tasks (applies even for non-LLM agents for consistency).
_DEFAULT_INTER_TASK_DELAY: float = 3.0


# ── Single-task evaluation (run inside TaskQueue) ─────────────────────────────

def _evaluate_single_task(
    task_id: str,
    agent: Any,
    step_delay: float = _INTRA_TASK_STEP_DELAY,
) -> Dict[str, Any]:
    """Run one complete episode for ``task_id`` and return detailed metrics.

    Args:
        task_id:     Identifier of the task to evaluate.
        agent:       Any agent with an ``.act(obs, state) -> action`` method.
        step_delay:  Optional extra sleep between steps (useful when testing
                     without a rate limiter to keep logs readable).

    Returns:
        A result dict with per-task scores, steps, and breakdown metrics.
    """
    env    = CodeReviewEnv()
    grader = get_grader(task_id)

    try:
        logger.info("[eval_suite] Starting task: %s", task_id)
        obs  = env.reset(task_id)
        done = False
        steps = 0

        while not done:
            action = agent.act(obs, env.state())
            obs, reward, done, info = env.step(action)
            steps += 1

            if step_delay > 0:
                time.sleep(step_delay)

        state  = env.state()
        score  = grader.grade_episode(state["actions_taken"])
        report = grader.generate_grade_report()

        logger.info(
            "[eval_suite] Finished %s — score=%.3f status=%s steps=%d",
            task_id, score, report.get("grade_status", "?"), steps,
        )

        return {
            "task_id":                  task_id,
            "difficulty":               report["difficulty"],
            "score":                    score,
            "status":                   report["grade_status"],
            "steps":                    steps,
            "decision":                 state["final_decision"],
            "correct_decision":         report["correct_decision"],
            "decision_correct":         report["decision_correct"],
            "evidence_score":           report["evidence_score"],
            "issue_identification_score": report["issue_identification_score"],
            "decision_score":           report["decision_score"],
            "penalties":                report["penalties"],
            "threshold":                report["pass_threshold"],
        }

    except Exception as exc:
        logger.error("[eval_suite] Error evaluating %s: %s", task_id, exc, exc_info=True)
        return {
            "task_id": task_id,
            "score":   0.0,
            "status":  "ERROR",
            "error":   str(exc),
        }


# ── Public evaluation API ─────────────────────────────────────────────────────

def evaluate_agent(
    agent: Any,
    task_ids: List[str],
    inter_task_delay: float = _DEFAULT_INTER_TASK_DELAY,
    step_delay: float = _INTRA_TASK_STEP_DELAY,
) -> Dict[str, Any]:
    """Evaluate ``agent`` on each task in ``task_ids`` sequentially.

    Tasks are dispatched through a ``TaskQueue`` with ``inter_task_delay``
    seconds between each episode so that LLM rate-limit windows are respected.

    Returns a dict with ``summary`` and per-task ``results``.
    """
    queue = TaskQueue(inter_task_delay=inter_task_delay)
    for task_id in task_ids:
        queue.enqueue(_evaluate_single_task, task_id, agent, step_delay)

    raw_results: List[Any] = queue.run_all()

    # Flatten TaskQueue error wrappers into uniform result dicts
    results: List[Dict[str, Any]] = []
    for item in raw_results:
        if isinstance(item, dict) and "error" in item and "task_id" not in item:
            results.append({
                "task_id": f"unknown_task_{item.get('task_num', '?')}",
                "score":   0.0,
                "status":  "ERROR",
                "error":   item["error"],
            })
        else:
            results.append(item)

    # Aggregate metrics
    scores = [r["score"] for r in results if "error" not in r]
    passed = [r for r in results if r.get("status") == "PASS"]

    summary = {
        "total_tasks":        len(results),
        "passed":             len(passed),
        "failed":             len(results) - len(passed),
        "pass_rate":          len(passed) / len(results) if results else 0.0,
        "avg_score":          sum(scores) / len(scores) if scores else 0.0,
        "min_score":          min(scores) if scores else 0.0,
        "max_score":          max(scores) if scores else 0.0,
        "avg_steps":          sum(r.get("steps", 0) for r in results) / len(results),
        "decision_accuracy":  (
            sum(1 for r in results if r.get("decision_correct")) / len(results)
            if results else 0.0
        ),
    }

    return {"summary": summary, "results": results}


def compare_agents(
    agents: Dict[str, Any],
    task_ids: List[str],
    inter_task_delay: float = _DEFAULT_INTER_TASK_DELAY,
) -> Dict[str, Any]:
    """Compare multiple agents across the same task set.

    Each agent is evaluated sequentially (one agent at a time, one task at
    a time) to avoid concurrent API bursts.

    Returns per-agent evaluations and a side-by-side comparison table.
    """
    logger.info("[eval_suite] Comparing %d agent(s) on %d tasks.", len(agents), len(task_ids))

    comparisons: Dict[str, Any] = {}
    for agent_name, agent in agents.items():
        logger.info("[eval_suite] Evaluating agent: %s", agent_name)
        comparisons[agent_name] = evaluate_agent(
            agent, task_ids, inter_task_delay=inter_task_delay
        )

    # Build side-by-side comparison table
    comparison_table = []
    for task_id in task_ids:
        row: Dict[str, Any] = {"task_id": task_id}
        for agent_name in agents:
            agent_result = next(
                (r for r in comparisons[agent_name]["results"] if r["task_id"] == task_id),
                {"score": 0.0},
            )
            row[agent_name] = agent_result["score"]
        comparison_table.append(row)

    return {
        "individual_evaluations": comparisons,
        "comparison_table":       comparison_table,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Comprehensive agent evaluation suite")
    parser.add_argument("--agent",      choices=["baseline", "rl", "compare"], default="baseline")
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    parser.add_argument("--output",     default=None, help="Save results to JSON file")
    parser.add_argument("--verbose",    action="store_true", help="Detailed logging")
    parser.add_argument(
        "--inter-task-delay",
        type=float,
        default=_DEFAULT_INTER_TASK_DELAY,
        help="Seconds between tasks (default: %(default)s)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    task_ids = get_available_tasks()

    if args.agent == "baseline":
        agent   = BaselineAgent()
        results = evaluate_agent(
            agent, task_ids,
            inter_task_delay=args.inter_task_delay,
        )

    elif args.agent == "rl":
        agent = QLearningReviewAgent.load(args.checkpoint)
        agent.epsilon = 0.0
        results = evaluate_agent(
            agent, task_ids,
            inter_task_delay=args.inter_task_delay,
        )

    elif args.agent == "compare":
        baseline = BaselineAgent()
        rl_agent = QLearningReviewAgent.load(args.checkpoint)
        rl_agent.epsilon = 0.0
        results = compare_agents(
            {"baseline": baseline, "rl": rl_agent},
            task_ids,
            inter_task_delay=args.inter_task_delay,
        )

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    if args.agent == "compare":
        print("\nComparison Summary:")
        for agent_name, eval_data in results["individual_evaluations"].items():
            s = eval_data["summary"]
            print(f"\n{agent_name.upper()}:")
            print(f"  Pass Rate:        {s['pass_rate']:.1%} ({s['passed']}/{s['total_tasks']})")
            print(f"  Avg Score:        {s['avg_score']:.3f}")
            print(f"  Decision Accuracy:{s['decision_accuracy']:.1%}")

        print("\nPer-Task Comparison:")
        print(f"{'Task':<25} {'Baseline':<10} {'RL':<10} {'Winner'}")
        print("-" * 60)
        for row in results["comparison_table"]:
            b = row.get("baseline", 0.0)
            r = row.get("rl", 0.0)
            winner = "RL" if r > b else "Baseline" if b > r else "Tie"
            print(f"{row['task_id']:<25} {b:<10.3f} {r:<10.3f} {winner}")

    else:
        s = results["summary"]
        print(f"\nOverall Performance:")
        print(f"  Tasks:             {s['total_tasks']}")
        print(f"  Passed:            {s['passed']} ({s['pass_rate']:.1%})")
        print(f"  Avg Score:         {s['avg_score']:.3f}")
        print(f"  Score Range:       [{s['min_score']:.3f}, {s['max_score']:.3f}]")
        print(f"  Avg Steps:         {s['avg_steps']:.1f}")
        print(f"  Decision Accuracy: {s['decision_accuracy']:.1%}")

        print(f"\nPer-Task Results:")
        print(f"{'Task':<25} {'Score':<8} {'Steps':<6} {'Status':<8} {'Threshold'}")
        print("-" * 60)
        for r in results["results"]:
            if "error" in r:
                print(f"{r['task_id']:<25} ERROR: {r['error']}")
            else:
                print(
                    f"{r['task_id']:<25} {r['score']:<8.3f} "
                    f"{r.get('steps', 0):<6} {r['status']:<8} "
                    f"{r.get('threshold', 0.0):.2f}"
                )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to %s", output_path)

    print("=" * 60)


if __name__ == "__main__":
    main()
