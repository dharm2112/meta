"""FastAPI backend for the offline PR review environment."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from baseline import BaselineAgent
from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, get_task_catalog, load_task
from tasks.dynamic_loader import create_dynamic_task, validate_uploaded_files
from tasks.dynamic_store import store_dynamic_task, get_dynamic_task, list_dynamic_tasks
from grader.task_graders import get_grader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Security: Configurable CORS origins (no wildcard)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5173,http://localhost:8000"
).split(",")

app = FastAPI(title="Code Review Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
    allow_credentials=True,
)

# Built frontend directory (populated by Docker build)
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Session state (single user demo)
_env = CodeReviewEnv()
_session: dict = {}
_baseline_agent = BaselineAgent()

# Cache for task catalog (performance optimization)
_task_catalog_cache: dict | None = None


class ActionRequest(BaseModel):
    action_type: str
    path: str | None = None
    text: str | None = None


@app.get("/api/tasks")
def get_tasks():
    """Get all available tasks with metadata (static + dynamic)."""
    global _task_catalog_cache
    
    # Build static tasks (cached)
    if _task_catalog_cache is None:
        meta = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        tasks = []
        for item in get_task_catalog():
            tasks.append(
                {
                    "id": item["id"],
                    "label": item["label"],
                    "difficulty": item["difficulty"],
                    "icon": meta[item["difficulty"]],
                    "desc": item["description"],
                    "issue_title": item["issue_title"],
                    "pass_threshold": item["pass_threshold"],
                }
            )
        _task_catalog_cache = {"tasks": tasks}
    
    # Add dynamic uploaded tasks (not cached)
    result = {"tasks": _task_catalog_cache["tasks"].copy()}
    dynamic_tasks = list_dynamic_tasks()
    
    for dt in dynamic_tasks:
        result["tasks"].append({
            "id": dt["id"],
            "label": dt["label"],
            "difficulty": "custom",
            "icon": "📤",
            "desc": dt["description"],
            "issue_title": dt["label"],
            "pass_threshold": 0.5,
            "is_custom_upload": True,
        })
    
    return result


@app.post("/api/upload")
async def upload_code(
    title: str = Form(...),
    description: str = Form(...),
    files: list[UploadFile] = File(...),
    original_files: list[UploadFile] = File(default=[]),
):
    """
    Upload custom code for review.
    
    Args:
        title: PR/Issue title
        description: PR description
        files: Modified/new files to review
        original_files: Original versions (optional, for diff generation)
    
    Returns:
        Created task ID and metadata
    """
    try:
        # Validate file count
        total_files = len(files) + len(original_files)
        if total_files > 20:
            return JSONResponse(status_code=400, content={"error": "Maximum 20 files allowed"})
        
        # Read and validate files
        changed_files = {}
        max_size = 1 * 1024 * 1024  # 1MB
        
        # Build original files map
        originals = {}
        for orig in original_files:
            content = await orig.read()
            if len(content) > max_size:
                return JSONResponse(status_code=400, content={"error": f"File '{orig.filename}' exceeds 1MB limit"})
            originals[orig.filename] = content.decode("utf-8", errors="replace")
        
        # Process modified files
        for f in files:
            content = await f.read()
            if len(content) > max_size:
                return JSONResponse(status_code=400, content={"error": f"File '{f.filename}' exceeds 1MB limit"})
            
            modified_content = content.decode("utf-8", errors="replace")
            
            # Check if we have original version
            if f.filename in originals:
                changed_files[f.filename] = {
                    "original": originals[f.filename],
                    "modified": modified_content,
                }
            else:
                # New file - no original
                changed_files[f.filename] = {
                    "modified": modified_content,
                }
        
        if not changed_files:
            return JSONResponse(status_code=400, content={"error": "No files uploaded"})
        
        # Create dynamic task
        task = create_dynamic_task(
            title=title,
            description=description,
            changed_files=changed_files,
            issue_body=description,
        )
        
        # Store task
        task_id = store_dynamic_task(task)
        
        logger.info(f"Created custom task: {task_id} with {len(changed_files)} files")
        
        return {
            "task_id": task_id,
            "label": title,
            "description": description,
            "changed_files": list(changed_files.keys()),
            "message": f"Task created successfully. Select '{task_id}' to start review.",
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/upload/{task_id}")
def delete_upload(task_id: str):
    """Delete an uploaded task."""
    from tasks.dynamic_store import delete_dynamic_task
    
    if delete_dynamic_task(task_id):
        logger.info(f"Deleted custom task: {task_id}")
        return {"message": f"Task {task_id} deleted"}
    else:
        return JSONResponse(status_code=404, content={"error": "Task not found"})


@app.post("/api/reset/{task_name}")
def reset(task_name: str):
    """Reset environment with a specific task (static or dynamic)."""
    # Check if it's a dynamic uploaded task
    dynamic_task = get_dynamic_task(task_name)
    
    if dynamic_task:
        # Use the uploaded task
        task = dynamic_task
        grader = get_grader(task_name, is_custom=True)
    elif task_name in get_available_tasks():
        # Use static task
        task = load_task(task_name)
        grader = get_grader(task_name)
    else:
        logger.warning(f"Unknown task requested: {task_name}")
        return JSONResponse(status_code=400, content={"error": "Unknown task"})
    
    try:
        obs = _env.reset(task)
        _session.update({"task_name": task_name, "task": task, "grader": grader, "obs": obs, "done": False})
        logger.info(f"Task {task_name} reset successfully")
        return {
            "observation": obs,
            "state": _env.state(),
            "task_id": task["id"],
            "difficulty": task["difficulty"],
            "description": task["description"],
            "issue_title": task["issue_title"],
            "issue_body": task["issue_body"],
            "is_custom_upload": task.get("is_custom_upload", False),
        }
    except Exception as e:
        logger.error(f"Error resetting task {task_name}: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/step")
def step(req: ActionRequest):
    if not _session:
        return JSONResponse(status_code=400, content={"error": "Call /api/reset first"})
    if _session.get("done"):
        return JSONResponse(status_code=400, content={"error": "Episode done. Reset first."})

    action = {"action_type": req.action_type}
    if req.path:
        action["path"] = req.path
    if req.text:
        action["text"] = req.text

    try:
        obs, reward, done, info = _env.step(action)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    _session["done"] = done
    _session["obs"] = obs
    state = _env.state()

    result = {
        "observation": obs,
        "reward": reward,
        "done": done,
        "info": info,
        "state": state,
        "score": None,
        "report": None,
    }

    if done:
        score = _session["grader"].grade_episode(state["actions_taken"])
        report = _session["grader"].generate_grade_report()
        result["score"] = score
        result["report"] = report

    return result


@app.get("/api/state")
def get_state():
    if not _session:
        return {"state": None}
    return {"state": _env.state(), "done": _session.get("done", False)}


@app.post("/api/auto_action")
def auto_action():
    """Let the heuristic baseline agent pick the next action and execute it."""
    if not _session:
        return JSONResponse(status_code=400, content={"error": "Call /api/reset first"})
    if _session.get("done"):
        return JSONResponse(status_code=400, content={"error": "Episode done. Reset first."})
    obs = _session["obs"]
    state = _env.state()
    action = _baseline_agent.act(obs, state)
    result = step(ActionRequest(**action))
    # Include the chosen action so the frontend knows what was done
    result["action"] = action
    return result


# ── Serve built frontend (production / Docker) ──────────────────────
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """SPA fallback: serve index.html for any non-API route."""
        target = STATIC_DIR / full_path
        if full_path and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    print("Starting Code Review Assistant API on http://0.0.0.0:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
