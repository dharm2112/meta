"""OpenEnv inference entry point.

This wrapper runs the inference pipeline from the backend module.
Required by OpenEnv/Scaler platform at repository root.

STDOUT FORMAT (required by OpenEnv):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

from __future__ import annotations
import os
import sys

# Add backend to Python path for imports
_root_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.join(_root_dir, "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Import the actual inference logic
from backend.baseline import BaselineAgent
from backend.inference import run_inference

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="OpenEnv inference entry point")
    parser.add_argument("--agent", choices=["heuristic", "rl", "groq"], default="heuristic")
    parser.add_argument("--checkpoint", default="backend/checkpoints/q_learning_policy.json")
    parser.add_argument("--model", default=None, help="Model name override (only with --agent groq)")
    args = parser.parse_args()

    # Configure agent based on selection
    if args.agent == "groq":
        api_key = os.getenv("HF_TOKEN") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise SystemExit("ERROR: Set HF_TOKEN or GROQ_API_KEY environment variable.")
        from backend.openai_agent import GroqReviewAgent
        model = args.model or os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
        base_url = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
        agent = GroqReviewAgent(api_key=api_key, model=model, base_url=base_url)
    elif args.agent == "rl":
        from backend.rl.q_learning import QLearningReviewAgent
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
