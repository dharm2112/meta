"""End-to-end pipeline test: env + tasks + grader."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.environment import CodeReviewEnv
from baseline import BaselineAgent
from grader.task_graders import get_grader
from tasks.task_registry import get_available_tasks

env = CodeReviewEnv()
agent = BaselineAgent()

for task_id in get_available_tasks():
    obs = env.reset(task_id)
    done = False

    while not done:
        action = agent.act(obs, env.state())
        obs, reward, done, info = env.step(action)

    grader = get_grader(task_id)
    score = grader.grade_episode(env.state()["actions_taken"])
    report = grader.generate_grade_report()

    print(f"[{task_id}] score={score:.4f} status={report['grade_status']}")
    print(f"  decision: {report['submitted_decision']} (expected {report['correct_decision']})")
    print(f"  evidence={report['evidence_score']:.2f} issue={report['issue_identification_score']:.2f} penalties={report['penalties']:.2f}")
    print()
