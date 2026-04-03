"""End-to-end pipeline test: env + tasks + grader."""

from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, load_task
from grader.task_graders import get_grader

env = CodeReviewEnv()

for difficulty in get_available_tasks():
    task = load_task(difficulty)
    obs = env.reset(task)

    env.step({"action_type": "view_file"})
    for issue in task.get_expected_issues():
        env.step({"action_type": "comment_issue", "comment": f"{issue} detected"})
    env.step({"action_type": "request_changes"})

    grader = get_grader(difficulty)
    score = grader.grade_episode(env.state()["actions_taken"])
    report = grader.generate_grade_report()

    print(f"[{difficulty}] score={score:.4f} status={report['grade_status']}")
    print(f"  expected: {report['issues_expected']}")
    print(f"  detected: {report['issues_detected']}")
    print(f"  detection_acc: {report['detection_accuracy']}")
    print()
