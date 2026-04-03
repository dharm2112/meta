"""FastAPI backend for the Code Review Assistant — JSON-only API."""

from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json

try:
    from groq import Groq
except ImportError:
    Groq = None

from env.environment import CodeReviewEnv
from tasks.task_registry import get_available_tasks, load_task
from grader.task_graders import get_grader

app = FastAPI(title="Code Review Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    _session.update({"task_name": task_name, "task": task, "grader": grader, "obs": obs, "done": False})
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
    if not _session or _session.get("done"):
        return JSONResponse(status_code=400, content={"error": "Invalid session or episode already done. Reset first."})

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "GROQ_API_KEY environment variable is missing on server!"})

    if Groq is None:
        return JSONResponse(status_code=500, content={"error": "Groq package not installed. Run pip install groq"})

    try:
        client = Groq(api_key=api_key)
        state_dict = _env.state()
        obs = _session.get("obs", {})

        system_prompt = """You are an automated code review AI agent.
Your goal is to review a Pull Request diff. You can read, comment on issues, request changes, or approve the PR.
You MUST return your decision as a valid JSON object matching exactly this schema:
{"action_type": "view_file" | "comment_issue" | "approve_pr" | "request_changes", "comment": "explain the issue if action_type is comment_issue"}

Do not include any other text, markdown, or explanation, just the raw JSON object.
"""
        user_prompt = f"""
Currently available information:
Diff:
{obs.get('diff', 'None')}

Target Issues:
{obs.get('issues', [])}

Actions taken so far by you:
{state_dict.get('actions_taken', [])}

Determine the very next logical step. If you haven't commented on the known issues, do so now one by one. If all found, request changes. If non found, approve.
Respond ONLY with JSON.
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.0
        )

        content = chat_completion.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        if content.startswith("```"):
            content = content[3:-3]

        data = json.loads(content)

        valid_actions = ["view_file", "comment_issue", "approve_pr", "request_changes"]
        if data.get("action_type") not in valid_actions:
            data["action_type"] = "view_file"

        return data

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    print("Starting Code Review Assistant API on http://0.0.0.0:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
