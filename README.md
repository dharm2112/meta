# 🔍 Code Review Assistant — Full-Stack Application

> **HumanEval for code review** — train and benchmark AI agents on the task senior engineers spend 40% of their time doing.

[![PyPI](https://img.shields.io/pypi/v/code-review-env)](https://pypi.org/project/code-review-env)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-compliant-blue)](openenv.yaml)

## 📁 Project Structure

```
meta/
├── backend/           ← FastAPI Python backend (all core logic)
│   ├── app.py                 # FastAPI server (JSON-only API)
│   ├── baseline.py            # Baseline agents (stub + GPT-4)
│   ├── inference.py           # Batch evaluation pipeline
│   ├── requirements.txt
│   ├── scripts/               # Utility scripts
│   │   └── test_pipeline.py   # End-to-end pipeline test
│   ├── env/                   # Environment core
│   ├── tasks/                 # Task definitions (easy/medium/hard)
│   ├── grader/                # Grading system
│   └── generator/             # PR data generators
│
├── frontend/          ← React (Vite) frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/        # TaskSelector, PRViewer, ActionPanel, etc.
│   │   └── services/api.js    # Axios API layer
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 🚀 Getting Started

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### API Routes

| Method | Endpoint            | Description                  |
|--------|---------------------|------------------------------|
| GET    | `/api/tasks`        | List available tasks         |
| POST   | `/api/reset/{task}` | Reset env with a task        |
| POST   | `/api/step`         | Execute an action            |
| GET    | `/api/state`        | Get current environment state|
| POST   | `/api/auto_action`  | AI-suggested next action     |

---

## 🎯 What Is This?

An **OpenEnv-compliant reinforcement learning benchmark** where AI agents review pull requests:

1. Receive a PR diff as observation
2. Navigate files, identify issues (bugs, security flaws, style problems)
3. Leave comments and make approve/reject decisions
4. Get scored 0.0 → 1.0 based on accuracy

---

## ⚡ Quickstart

```bash
pip install code-review-env

# Run baseline (no API key needed)
python baseline.py --task all

# Output:
# Task easy    : 0.7500  [PASS]
# Task medium  : 0.6200  [PASS]
# Task hard    : 0.5100  [PASS]
```

```python
from env.environment import CodeReviewEnv
from tasks.task_registry import load_task

env = CodeReviewEnv()
obs = env.reset(task="medium")

obs, reward, done, info = env.step({
    "action_type": "comment_issue",
    "comment": "sql_injection detected in login.py"
})

state = env.state()
```

---

## 🏗️ Project Structure

```
code-review-env/
├── env/
│   ├── environment.py     # Core env: reset / step / state
│   ├── action.py          # Pydantic ActionModel
│   ├── observation.py     # Pydantic ObservationModel
│   ├── state.py           # Pydantic StateModel
│   ├── schema.py          # validate_action / validate_observation / validate_state
│   └── reward.py          # RewardEngine
├── generator/
│   └── pr_generator.py    # Deterministic PR generator (easy/medium/hard)
├── tasks/
│   ├── task_easy.py       # Style & documentation review
│   ├── task_medium.py     # Security bug detection
│   ├── task_hard.py       # Auth bypass + performance regression
│   └── task_registry.py   # TASK_REGISTRY, load_task(), get_available_tasks()
├── grader/
│   ├── grader.py          # Base TaskGrader
│   ├── task_graders.py    # Easy/Medium/Hard graders + GRADER_REGISTRY
│   └── score_utils.py     # clamp_score, detection/decision accuracy
├── baseline.py            # Deterministic baseline agent (+ optional GPT-4)
├── inference.py           # Batch inference loop
├── app.py                 # Gradio web UI (HuggingFace Spaces)
├── openenv.yaml           # OpenEnv validator config
├── Dockerfile             # Container deployment
└── pyproject.toml         # PyPI packaging
```

---

## 📊 The Three Tasks

| Task | Difficulty | Issues | Pass Threshold | GPT-4 Baseline |
|------|-----------|--------|---------------|----------------|
| Style & Documentation | Easy | missing_docstring, unused_variable | ≥ 0.70 | ~0.75 |
| Bug Detection & Tests | Medium | sql_injection, missing_unit_tests, logic_bug | ≥ 0.60 | ~0.62 |
| Complex Refactoring | Hard | authentication_bypass, performance_regression, flaky_test_behavior | ≥ 0.50 | ~0.51 |

---

## 🎮 Actions

| Action | Description | Reward |
|--------|-------------|--------|
| `view_file` | Read the PR file | 0.00 |
| `comment_issue` | Flag a detected issue | +0.10 (hit) / −0.05 (miss) |
| `request_changes` | Reject the PR | +0.30 |
| `approve_pr` | Approve the PR | +0.30 (correct) / −0.40 (incorrect) |

---

## 🧪 Inference Pipeline

```bash
python inference.py

# [START] task=easy
# [STEP]  task=easy step=0 action=view_file reward=0.0000
# [STEP]  task=easy step=1 action=comment_issue reward=0.1000
# [RESULT] task=style_documentation_review score=0.7500 status=PASS
# [END]   final_score=0.7500
```

---

## 🚀 Gradio Web Demo

```bash
pip install "code-review-env[ui]"
python app.py
# → http://localhost:7860
```

Or deploy to HuggingFace Spaces using the included `Dockerfile`.

---

## 🐳 Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

---

## 🔧 OpenAI Baseline

```bash
export OPENAI_API_KEY="sk-..."
python baseline.py --task all --agent gpt4
```

---

## 📐 Schema Validation

```python
from env.schema import validate_action, validate_observation, validate_state

action = validate_action({"action_type": "approve_pr"})
# Raises ValidationError for invalid action types
```

---

## 📚 Citation

```bibtex
@software{code_review_env_2024,
  title  = {Code Review Assistant: An OpenEnv Environment for AI Code Review Agents},
  year   = {2024},
  url    = {https://github.com/username/code-review-env}
}
```

---

## 📄 License

MIT
