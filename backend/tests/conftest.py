"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return {
        "id": "test_task_001",
        "difficulty": "easy",
        "description": "Test authorization bug",
        "summary": "Missing admin check on export endpoint",
        "issue_title": "Authorization missing",
        "issue_body": "Users can access admin endpoint",
        "changed_files": ["routes/admin.py"],
        "diffs": {
            "routes/admin.py": "@@ -1,3 +1,3 @@\n def export():\n-    return data\n+    if user: return data"
        },
        "files": {
            "routes/admin.py": "def export():\n    if user: return data"
        },
        "ground_truth": {
            "correct_decision": "reject",
            "relevant_files": ["routes/admin.py"],
            "bug_type": "authorization",
            "keywords": ["admin", "role", "authorization"],
            "root_cause_keywords": ["missing admin check", "role validation"],
            "uncertain": False
        },
        "pass_threshold": 0.7,
        "max_steps": 6
    }
