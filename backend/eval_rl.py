from __future__ import annotations

import argparse
import json

from rl.q_learning import QLearningReviewAgent, evaluate_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a trained Q-learning PR review agent")
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    args = parser.parse_args()

    agent = QLearningReviewAgent.load(args.checkpoint)
    agent.epsilon = 0.0
    results = evaluate_agent(agent)

    print("=" * 48)
    print("Q-Learning Evaluation")
    print("=" * 48)
    for result in results:
        print(f"  {result['task']:18s} score={result['score']:.4f} status={result['status']}")
    print("=" * 48)
    print(json.dumps([{k: v for k, v in result.items() if k != 'report'} for result in results], indent=2))


if __name__ == "__main__":
    main()