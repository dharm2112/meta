try:
    from backend.tasks.task_registry import TASK_REGISTRY, get_available_tasks, get_task_catalog, load_task
except ImportError:
    from tasks.task_registry import TASK_REGISTRY, get_available_tasks, get_task_catalog, load_task

__all__ = ["TASK_REGISTRY", "get_available_tasks", "get_task_catalog", "load_task"]
