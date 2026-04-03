"""FastAPI backend for the Code Review Assistant premium UI."""

from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, load_task
from grader.task_graders import get_grader

app = FastAPI(title="Code Review Assistant API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Session state (single user demo)
_env = CodeReviewEnv()
_session: dict = {}


class ActionRequest(BaseModel):
    action_type: str
    comment: str = ""


@app.get("/api/tasks")
def get_tasks():
    tasks = get_available_tasks()
    meta = {
        "easy":   {"label": "Easy",   "icon": "🟢", "desc": "Style & documentation review"},
        "medium": {"label": "Medium", "icon": "🟡", "desc": "Security bug detection"},
        "hard":   {"label": "Hard",   "icon": "🔴", "desc": "Auth bypass & performance issues"},
    }
    return {"tasks": [{"id": t, **meta[t]} for t in tasks]}


@app.post("/api/reset/{task_name}")
def reset(task_name: str):
    if task_name not in get_available_tasks():
        return JSONResponse(status_code=400, content={"error": "Unknown task"})
    task = load_task(task_name)
    grader = get_grader(task_name)
    obs = _env.reset(task)
    _session.update({"task_name": task_name, "task": task, "grader": grader, "done": False})
    return {
        "observation": obs,
        "task_name": task_name,
        "difficulty": task.get_difficulty(),
        "description": task.get_description(),
        "expected_issue_count": len(task.get_expected_issues()),
    }


@app.post("/api/step")
def step(req: ActionRequest):
    if not _session:
        return JSONResponse(status_code=400, content={"error": "Call /api/reset first"})
    if _session.get("done"):
        return JSONResponse(status_code=400, content={"error": "Episode done. Reset first."})

    action = {"action_type": req.action_type}
    if req.comment:
        action["comment"] = req.comment

    try:
        obs, reward, done, info = _env.step(action)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    _session["done"] = done
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


@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=7860, reload=False)
