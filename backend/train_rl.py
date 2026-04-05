from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure the backend directory is on sys.path (needed in Docker builds)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from rl.q_learning import evaluate_agent, train_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a tabular Q-learning agent for offline PR review")
    parser.add_argument("--episodes", type=int, default=1500)
    parser.add_argument("--alpha", type=float, default=0.35)
    parser.add_argument("--gamma", type=float, default=0.90)
    parser.add_argument("--epsilon", type=float, default=0.20)
    parser.add_argument("--epsilon-min", type=float, default=0.02)
    parser.add_argument("--epsilon-decay", type=float, default=0.995)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--checkpoint", default="checkpoints/q_learning_policy.json")
    args = parser.parse_args()

    agent, history = train_agent(
        episodes=args.episodes,
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        seed=args.seed,
    )
    agent.save(args.checkpoint)
    results = evaluate_agent(agent)

    print("=" * 48)
    print("Q-Learning Training Complete")
    print("=" * 48)
    print(f"episodes={args.episodes}")
    print(f"checkpoint={args.checkpoint}")
    print("evaluation:")
    for result in results:
        print(f"  {result['task']:18s} score={result['score']:.4f} status={result['status']}")
    print("=" * 48)
    print(json.dumps({"history_tail": history[-5:], "results": [{k: v for k, v in result.items() if k != 'report'} for result in results]}, indent=2))


if __name__ == "__main__":
    main()