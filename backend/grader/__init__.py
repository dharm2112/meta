try:
    from backend.grader.grader import TaskGrader
    from backend.grader.task_graders import get_grader
except ImportError:
    from grader.grader import TaskGrader
    from grader.task_graders import get_grader

__all__ = ["TaskGrader", "get_grader"]
