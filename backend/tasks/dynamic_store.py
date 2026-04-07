"""Temporary storage for user-uploaded dynamic tasks."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List


class DynamicTaskStore:
    """Thread-safe in-memory storage for uploaded tasks with TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize task store.
        
        Args:
            ttl_seconds: Time-to-live for tasks in seconds (default: 1 hour)
        """
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cleanup_thread = None
        self._running = False
    
    def store_task(self, task: Dict[str, Any]) -> str:
        """
        Store a task and return its ID.
        
        Args:
            task: Task dictionary (must contain 'id' field)
        
        Returns:
            Task ID
        """
        task_id = task["id"]
        
        with self._lock:
            self._tasks[task_id] = task
            self._timestamps[task_id] = datetime.now()
        
        return task_id
    
    def get_task(self, task_id: str) -> Dict[str, Any] | None:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Task dictionary or None if not found/expired
        """
        with self._lock:
            if task_id not in self._tasks:
                return None
            
            # Check if expired
            if self._is_expired(task_id):
                self._delete_task(task_id)
                return None
            
            return self._tasks[task_id]
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            return self._delete_task(task_id)
    
    def _delete_task(self, task_id: str) -> bool:
        """Internal delete (assumes lock is held)."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            del self._timestamps[task_id]
            return True
        return False
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        List all active (non-expired) tasks.
        
        Returns:
            List of task dictionaries
        """
        with self._lock:
            self._cleanup_expired()
            return [
                {
                    "id": task["id"],
                    "label": task.get("label", task.get("id")),
                    "difficulty": task.get("difficulty", "custom"),
                    "description": task.get("description", ""),
                    "uploaded_at": task.get("uploaded_at"),
                    "is_custom_upload": True,
                }
                for task in self._tasks.values()
            ]
    
    def cleanup_expired(self) -> int:
        """
        Remove expired tasks.
        
        Returns:
            Number of tasks removed
        """
        with self._lock:
            return self._cleanup_expired()
    
    def _cleanup_expired(self) -> int:
        """Internal cleanup (assumes lock is held)."""
        expired = [
            task_id for task_id in self._tasks.keys()
            if self._is_expired(task_id)
        ]
        
        for task_id in expired:
            self._delete_task(task_id)
        
        return len(expired)
    
    def _is_expired(self, task_id: str) -> bool:
        """Check if a task has expired."""
        if task_id not in self._timestamps:
            return True
        
        age = datetime.now() - self._timestamps[task_id]
        return age > self._ttl
    
    def start_background_cleanup(self, interval_seconds: int = 300):
        """
        Start background thread that periodically cleans up expired tasks.
        
        Args:
            interval_seconds: Cleanup interval (default: 5 minutes)
        """
        if self._running:
            return
        
        self._running = True
        
        def cleanup_loop():
            while self._running:
                time.sleep(interval_seconds)
                if self._running:
                    removed = self.cleanup_expired()
                    if removed > 0:
                        print(f"DynamicTaskStore: Cleaned up {removed} expired task(s)")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop_background_cleanup(self):
        """Stop the background cleanup thread."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)
    
    def clear(self):
        """Clear all tasks (for testing)."""
        with self._lock:
            self._tasks.clear()
            self._timestamps.clear()
    
    def __len__(self) -> int:
        """Return number of stored tasks."""
        with self._lock:
            return len(self._tasks)


# Global instance
_store = DynamicTaskStore()


# Public API
def get_store() -> DynamicTaskStore:
    """Get the global task store instance."""
    return _store


def store_dynamic_task(task: Dict[str, Any]) -> str:
    """Store a dynamic task."""
    return _store.store_task(task)


def get_dynamic_task(task_id: str) -> Dict[str, Any] | None:
    """Retrieve a dynamic task."""
    return _store.get_task(task_id)


def delete_dynamic_task(task_id: str) -> bool:
    """Delete a dynamic task."""
    return _store.delete_task(task_id)


def list_dynamic_tasks() -> List[Dict[str, Any]]:
    """List all dynamic tasks."""
    return _store.list_tasks()


def cleanup_expired_tasks() -> int:
    """Clean up expired tasks."""
    return _store.cleanup_expired()


# Initialize background cleanup on import
_store.start_background_cleanup()
