"""FastAPI backend for the offline PR review environment."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from baseline import BaselineAgent
from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, get_task_catalog, load_task
from grader.task_graders import get_grader

app = FastAPI(title="Code Review Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Built frontend directory (populated by Docker build)
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Session state (single user demo)
_env = CodeReviewEnv()
_session: dict = {}
_baseline_agent = BaselineAgent()


class ActionRequest(BaseModel):
    action_type: str
    path: str | None = None
    text: str | None = None


@app.get("/api/tasks")
def get_tasks():
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
    return {"tasks": tasks}


@app.post("/api/reset/{task_name}")
def reset(task_name: str):
    if task_name not in get_available_tasks():
        return JSONResponse(status_code=400, content={"error": "Unknown task"})
    task = load_task(task_name)
    grader = get_grader(task_name)
    obs = _env.reset(task)
    _session.update({"task_name": task_name, "task": task, "grader": grader, "obs": obs, "done": False})
    return {
        "observation": obs,
        "state": _env.state(),
        "task_id": task["id"],
        "difficulty": task["difficulty"],
        "description": task["description"],
        "issue_title": task["issue_title"],
        "issue_body": task["issue_body"],
    }


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
