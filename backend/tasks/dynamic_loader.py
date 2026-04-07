"""Dynamic task generation from user-uploaded code."""

from __future__ import annotations

import uuid
import difflib
from datetime import datetime
from typing import Dict, Any, List


def generate_task_id() -> str:
    """Generate a unique task ID for uploaded content."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"upload_{timestamp}_{short_uuid}"


def create_diff(original: str, modified: str, filename: str) -> str:
    """Create unified diff from original and modified file contents."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    
    return "".join(diff)


def create_dynamic_task(
    title: str,
    description: str,
    changed_files: Dict[str, Dict[str, str]],
    context_files: Dict[str, str] | None = None,
    issue_body: str | None = None,
    ground_truth: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Create a task dictionary from uploaded content.
    
    Args:
        title: PR/Issue title
        description: PR description/summary
        changed_files: Dict of {path: {"original": str, "modified": str}} or {path: {"diff": str}}
        context_files: Optional dict of {path: content} for additional context
        issue_body: Optional detailed issue description
        ground_truth: Optional ground truth for scoring (if known)
    
    Returns:
        Task dictionary compatible with CodeReviewEnv
    """
    task_id = generate_task_id()
    
    # Process changed files and generate diffs
    diffs = {}
    files = {}
    changed_paths = []
    
    for path, content in changed_files.items():
        changed_paths.append(path)
        
        # If diff is provided directly, use it
        if "diff" in content:
            diffs[path] = content["diff"]
            # Store modified version as the file content
            if "modified" in content:
                files[path] = content["modified"]
        
        # If original and modified are provided, generate diff
        elif "original" in content and "modified" in content:
            diffs[path] = create_diff(content["original"], content["modified"], path)
            files[path] = content["modified"]
        
        # If only modified is provided (new file)
        elif "modified" in content:
            files[path] = content["modified"]
            # Generate diff showing entire file as added
            diffs[path] = create_diff("", content["modified"], path)
    
    # Add context files
    if context_files:
        files.update(context_files)
    
    # Build available files list (all files that can be inspected)
    available_files = list(set(changed_paths + list(context_files.keys() if context_files else [])))
    
    # Create task structure
    task = {
        "id": task_id,
        "difficulty": "custom",
        "label": title,
        "description": description,
        "issue_title": title,
        "issue_body": issue_body or description,
        "changed_files": changed_paths,
        "available_files": available_files,
        "diffs": diffs,
        "files": files,
        "pass_threshold": 0.5,  # Default for custom uploads
        "is_custom_upload": True,
        "uploaded_at": datetime.now().isoformat(),
    }
    
    # Add ground truth if provided (for testing)
    if ground_truth:
        task["ground_truth"] = ground_truth
    
    return task


def validate_uploaded_files(files: List[Dict[str, Any]], max_size_mb: float = 1.0, max_files: int = 10) -> tuple[bool, str | None]:
    """
    Validate uploaded files for size and count limits.
    
    Returns:
        (is_valid, error_message)
    """
    if len(files) > max_files:
        return False, f"Too many files: maximum {max_files} files allowed"
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    for file_info in files:
        size = file_info.get("size", 0)
        if size > max_size_bytes:
            filename = file_info.get("filename", "unknown")
            return False, f"File '{filename}' exceeds {max_size_mb}MB limit"
    
    return True, None


# Example usage for testing
if __name__ == "__main__":
    # Example: Simple file modification
    test_task = create_dynamic_task(
        title="Fix authentication bug",
        description="Remove admin check from public endpoint",
        changed_files={
            "api/routes.py": {
                "original": "@admin_required\ndef export_data():\n    return data",
                "modified": "def export_data():\n    return data"
            }
        },
        context_files={
            "api/__init__.py": "from .routes import *"
        }
    )
    
    print(f"Generated task: {test_task['id']}")
    print(f"Changed files: {test_task['changed_files']}")
    print(f"Available files: {test_task['available_files']}")
    print(f"Diff sample:\n{test_task['diffs']['api/routes.py'][:200]}")
