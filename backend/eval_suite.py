"""Comprehensive evaluation suite for RL agents."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from env.environment import CodeReviewEnv
from grader.task_graders import get_grader
from tasks.task_registry import get_available_tasks
from rl.q_learning import QLearningReviewAgent
from baseline import BaselineAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_agent(agent, task_ids: List[str]) -> Dict[str, Any]:
    """
    Comprehensive evaluation of an agent across all tasks.
    
    Returns detailed metrics including:
    - Per-task scores
    - Pass/fail status
    - Average performance
    - Step efficiency
    - Decision correctness
    """
    env = CodeReviewEnv()
    results = []
    
    for task_id in task_ids:
        logger.info(f"Evaluating task: {task_id}")
        grader = get_grader(task_id)
        
        try:
            obs = env.reset(task_id)
            done = False
            steps = 0
            
            while not done:
                action = agent.act(obs, env.state())
                obs, reward, done, info = env.step(action)
                steps += 1
            
            state = env.state()
            score = grader.grade_episode(state["actions_taken"])
            report = grader.generate_grade_report()
            
            results.append({
                "task_id": task_id,
                "difficulty": report["difficulty"],
                "score": score,
                "status": report["grade_status"],
                "steps": steps,
                "decision": state["final_decision"],
                "correct_decision": report["correct_decision"],
                "decision_correct": report["decision_correct"],
                "evidence_score": report["evidence_score"],
                "issue_identification_score": report["issue_identification_score"],
                "decision_score": report["decision_score"],
                "penalties": report["penalties"],
                "threshold": report["pass_threshold"],
            })
            
        except Exception as e:
            logger.error(f"Error evaluating {task_id}: {e}")
            results.append({
                "task_id": task_id,
                "score": 0.0,
                "status": "ERROR",
                "error": str(e),
            })
    
    # Compute aggregate metrics
    scores = [r["score"] for r in results if "error" not in r]
    passed = [r for r in results if r.get("status") == "PASS"]
    
    summary = {
        "total_tasks": len(results),
        "passed": len(passed),
        "failed": len(results) - len(passed),
        "pass_rate": len(passed) / len(results) if results else 0.0,
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "avg_steps": sum(r.get("steps", 0) for r in results) / len(results),
        "decision_accuracy": sum(1 for r in results if r.get("decision_correct")) / len(results),
    }
    
    return {
        "summary": summary,
        "results": results,
    }


def compare_agents(agents: Dict[str, Any], task_ids: List[str]) -> Dict[str, Any]:
    """Compare multiple agents on the same tasks."""
    logger.info(f"Comparing {len(agents)} agents")
    
    comparisons = {}
    for agent_name, agent in agents.items():
        logger.info(f"Evaluating agent: {agent_name}")
        comparisons[agent_name] = evaluate_agent(agent, task_ids)
    
    # Build comparison table
    comparison_table = []
    for task_id in task_ids:
        row = {"task_id": task_id}
        for agent_name in agents.keys():
            agent_result = next(
                (r for r in comparisons[agent_name]["results"] if r["task_id"] == task_id),
                {"score": 0.0}
            )
            row[agent_name] = agent_result["score"]
        comparison_table.append(row)
    
    return {
        "individual_evaluations": comparisons,
        "comparison_table": comparison_table,
    }


def main():
    parser = argparse.ArgumentParser(description="Comprehensive agent evaluation suite")
    parser.add_argument("--agent", choices=["baseline", "rl", "compare"], default="baseline")
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    task_ids = get_available_tasks()
    
    if args.agent == "baseline":
        agent = BaselineAgent()
        results = evaluate_agent(agent, task_ids)
        
    elif args.agent == "rl":
        agent = QLearningReviewAgent.load(args.checkpoint)
        agent.epsilon = 0.0  # Disable exploration
        results = evaluate_agent(agent, task_ids)
        
    elif args.agent == "compare":
        baseline = BaselineAgent()
        rl_agent = QLearningReviewAgent.load(args.checkpoint)
        rl_agent.epsilon = 0.0
        
        agents = {
            "baseline": baseline,
            "rl": rl_agent,
        }
        results = compare_agents(agents, task_ids)
    
    # Print results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    
    if args.agent == "compare":
        print("\nComparison Summary:")
        for agent_name, eval_data in results["individual_evaluations"].items():
            summary = eval_data["summary"]
            print(f"\n{agent_name.upper()}:")
            print(f"  Pass Rate: {summary['pass_rate']:.1%} ({summary['passed']}/{summary['total_tasks']})")
            print(f"  Avg Score: {summary['avg_score']:.3f}")
            print(f"  Decision Accuracy: {summary['decision_accuracy']:.1%}")
        
        print("\nPer-Task Comparison:")
        print(f"{'Task':<25} {'Baseline':<10} {'RL':<10} {'Winner'}")
        print("-" * 60)
        for row in results["comparison_table"]:
            baseline_score = row.get("baseline", 0.0)
            rl_score = row.get("rl", 0.0)
            winner = "RL" if rl_score > baseline_score else "Baseline" if baseline_score > rl_score else "Tie"
            print(f"{row['task_id']:<25} {baseline_score:<10.3f} {rl_score:<10.3f} {winner}")
    else:
        summary = results["summary"]
        print(f"\nOverall Performance:")
        print(f"  Tasks: {summary['total_tasks']}")
        print(f"  Passed: {summary['passed']} ({summary['pass_rate']:.1%})")
        print(f"  Avg Score: {summary['avg_score']:.3f}")
        print(f"  Score Range: [{summary['min_score']:.3f}, {summary['max_score']:.3f}]")
        print(f"  Avg Steps: {summary['avg_steps']:.1f}")
        print(f"  Decision Accuracy: {summary['decision_accuracy']:.1%}")
        
        print(f"\nPer-Task Results:")
        print(f"{'Task':<25} {'Score':<8} {'Steps':<6} {'Status':<8} {'Threshold'}")
        print("-" * 60)
        for r in results["results"]:
            if "error" in r:
                print(f"{r['task_id']:<25} ERROR: {r['error']}")
            else:
                print(f"{r['task_id']:<25} {r['score']:<8.3f} {r['steps']:<6} {r['status']:<8} {r.get('threshold', 0.0):.2f}")
    
    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
