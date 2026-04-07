---
title: Code Review Assistant
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
tags:
  - openenv
---

# Code Review Assistant

An OpenEnv-compliant RL benchmark environment where AI agents review pull requests. The environment simulates the real-world task of code review: agents read PR metadata, inspect diffs and files, post review comments, and make an approve/reject/escalate decision — exactly what a human reviewer does on GitHub every day.

No live GitHub access, no LLM judge in the scoring path. Tasks are offline JSON cases with deterministic, reproducible grading.

## Environment Description & Motivation

Code review is one of the most time-consuming tasks in software engineering. This environment lets AI agents practice it in a safe, offline, fully deterministic setting. Each episode is a self-contained PR case with:

- A bug report (issue title + body)
- A PR summary
- Changed files with diffs
- Additional context files

The agent must investigate the PR, identify the defect, and make the correct decision — just like a real code reviewer.

## Action Space

Actions are typed via `ActionModel` (Pydantic `BaseModel`):

| Action | Parameters | Effect |
|--------|-----------|--------|
| `inspect_diff` | `path` (required) | Reveals the diff for a changed file |
| `inspect_file` | `path` (required) | Reveals full contents of any available file |
| `comment` | `text` (required) | Posts a review comment (graded for keywords) |
| `approve` | `text` (optional) | Approves the PR — **terminal** |
| `reject` | `text` (optional) | Rejects the PR — **terminal** |
| `escalate` | `text` (optional) | Escalates for human review — **terminal** |

```python
# Example action
{"action_type": "inspect_diff", "path": "routes/admin.py"}
```

## Observation Space

Observations are typed via `ObservationModel` (Pydantic `BaseModel`):

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Current task identifier |
| `difficulty` | `str` | `easy`, `medium`, or `hard` |
| `summary` | `str` | PR summary text |
| `issue_title` | `str` | Bug report title |
| `issue_body` | `str` | Bug report body |
| `changed_files` | `list[str]` | Files with diffs available |
| `available_files` | `list[str]` | All files available to inspect |
| `available_actions` | `list[str]` | Valid action types |
| `latest_event` | `dict` | Result of the last action (kind, title, content, path) |

## State

Returned by `state()`, typed via `StateModel`:

| Field | Type |
|-------|------|
| `task_id` | `str` |
| `current_step` | `int` |
| `max_steps` | `int` |
| `done` | `bool` |
| `total_reward` | `float` |
| `actions_taken` | `list[dict]` |
| `inspected_diffs` | `list[str]` |
| `inspected_files` | `list[str]` |
| `final_decision` | `str \| null` |

## Tasks

Three offline PR review cases of increasing difficulty:

### Easy — `easy_auth_001` (threshold 0.7)
**Missing admin check on export endpoint.** A single-file PR where the authorization decorator was removed from an admin export route. The agent should inspect the diff, comment about the missing admin role check, and reject.

### Medium — `medium_null_001` (threshold 0.6)
**Null handling broken in service layer.** A two-file PR where the controller was patched but the background service still processes null emails. The agent must inspect both files to find the deeper bug, comment, and reject.

### Hard — `hard_security_001` (threshold 0.5)
**Auth fallback policy requires escalation.** A policy-sensitive change where a stale service token can bypass auth. The correct decision is to escalate for human review, not just reject. Requires reading both the code and the security policy document.

## Reward Function

Scores are deterministic and clamped to `[0.0, 1.0]`. Partial progress signals are provided at every step:

| Component | Weight | Signal Type |
|-----------|--------|-------------|
| Relevant diff inspected | 0.15 | Partial progress |
| Relevant file inspected | 0.10 | Partial progress |
| Bug type identified in comment | 0.15 | Partial progress |
| Root cause identified in comment | 0.10 | Partial progress |
| Correct final decision | 0.50 | Terminal |

**Penalties** (clamped so score never goes below 0.0):
- Irrelevant file inspection: −0.05
- Repeated action: −0.02
- Hallucinated/irrelevant comment: −0.03

## Baseline Scores

Reproducible scores from the deterministic heuristic baseline (`python baseline.py`):

| Task | Baseline Score | Status | Threshold |
|------|---------------|--------|-----------|
| `easy_auth_001` | **0.80** | PASS | 0.70 |
| `medium_null_001` | **0.90** | PASS | 0.60 |
| `hard_security_001` | **1.00** | PASS | 0.50 |

RL agent scores after 1500 episodes of Q-learning (`python inference.py --agent rl`):

| Task | RL Score | Status |
|------|----------|--------|
| `easy_auth_001` | **0.90** | PASS |
| `medium_null_001` | **0.65** | PASS |
| `hard_security_001` | **0.60** | PASS |

## Project Structure

```
meta/
├── Dockerfile                  # Multi-stage build (Node + Python)
├── README.md
├── backend/
│   ├── app.py                  # FastAPI server + static frontend serving
│   ├── baseline.py             # Deterministic heuristic agent
│   ├── openai_agent.py         # OpenAI API-based agent
│   ├── inference.py            # Batch evaluation (heuristic / rl / openai)
│   ├── train_rl.py             # Q-learning training CLI
│   ├── eval_rl.py              # Q-learning evaluation CLI
│   ├── openenv.yaml            # OpenEnv manifest
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── env/                    # OpenEnv environment
│   │   ├── action.py           # ActionModel (Pydantic)
│   │   ├── observation.py      # ObservationModel (Pydantic)
│   │   ├── state.py            # StateModel (Pydantic)
│   │   ├── reward.py           # Deterministic RewardEngine
│   │   └── environment.py      # CodeReviewEnv (reset/step/state)
│   ├── grader/                 # Episode grading
│   │   ├── grader.py           # TaskGrader
│   │   └── task_graders.py     # Factory
│   ├── tasks/                  # Task registry + JSON data
│   │   ├── data/
│   │   │   ├── easy_auth_001.json
│   │   │   ├── medium_null_001.json
│   │   │   └── hard_security_001.json
│   │   ├── loader.py
│   │   └── task_registry.py
│   └── rl/                     # Reinforcement learning
│       ├── action_space.py     # Discrete macro-action adapter
│       └── q_learning.py       # Tabular Q-learning agent
└── frontend/                   # React UI
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   └── services/api.js
    ├── package.json
    └── vite.config.js
```

## Setup & Usage

### Local development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

### Run baseline evaluation

```bash
cd backend
python baseline.py --task all
python inference.py --agent heuristic
```

### Run with OpenAI API

```bash
cd backend
export OPENAI_API_KEY="sk-..."
python inference.py --agent openai --model gpt-4o-mini
```

### Train & evaluate RL agent

```bash
cd backend
python train_rl.py --episodes 1500
python eval_rl.py --checkpoint checkpoints/q_learning_policy.json
python inference.py --agent rl
```

### Pipeline test

```bash
cd backend
python scripts/test_pipeline.py
```

## Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
# Open http://localhost:7860
```

## Deploy to Hugging Face Spaces

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) — select **Docker** SDK.
2. Push this repository:
   ```bash
   cd meta
   git init && git add . && git commit -m "Initial deploy"
   git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/code-review-assistant
   git push origin main
   ```
3. The Space auto-builds and serves at `https://YOUR_USERNAME-code-review-assistant.hf.space`.

## OpenEnv Spec

The environment implements the full OpenEnv interface:

- **Typed models**: `ActionModel`, `ObservationModel`, `StateModel` (all Pydantic `BaseModel`)
- **`reset(task)`** → returns initial observation dict
- **`step(action)`** → returns `(observation, reward, done, info)`
- **`state()`** → returns current state dict
- **`openenv.yaml`** — environment metadata, action/observation schemas, task list, grader config

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tasks` | List all task metadata (static + uploaded) |
| `POST` | `/api/reset/{task_id}` | Start an episode |
| `POST` | `/api/step` | Execute an action |
| `GET` | `/api/state` | Get current state |
| `POST` | `/api/auto_action` | Baseline agent picks next action |
| `POST` | `/api/upload` | Upload custom code for review |
| `DELETE` | `/api/upload/{task_id}` | Delete an uploaded task |

The container starts the FastAPI backend on port `7860`, which is compatible with a Hugging Face Docker Space contest deployment.

## Custom Code Upload

You can upload your own code files for the AI agent to review. This enables dynamic code review scenarios beyond the built-in tasks.

### Upload via UI

1. Click **"Upload Custom Code"** in the toolbar
2. Fill in the PR title and description
3. Drag & drop or select modified files
4. Optionally add original file versions for automatic diff generation
5. Click **"Upload & Create Task"**
6. Select the new task from the dropdown and start reviewing

### Upload via API

```bash
# Upload files for review
curl -X POST http://localhost:8000/api/upload \
  -F "title=Fix authentication bug" \
  -F "description=Remove admin check from public endpoint" \
  -F "files=@path/to/modified_file.py" \
  -F "original_files=@path/to/original_file.py"

# Response:
# {
#   "task_id": "upload_20240407_120000_abc12345",
#   "label": "Fix authentication bug",
#   "changed_files": ["modified_file.py"],
#   "message": "Task created successfully..."
# }

# Start review session with uploaded task
curl -X POST http://localhost:8000/api/reset/upload_20240407_120000_abc12345
```

### Upload Limits

- Maximum 10 files per upload
- Maximum 1MB per file
- Uploaded tasks expire after 1 hour (configurable)
- Grading uses "review_only" mode (scores coverage, not correctness)
