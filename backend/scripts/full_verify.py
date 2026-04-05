"""Full verification: API contracts, baseline run, score analysis."""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


TASKS = ["easy_auth_001", "medium_null_001", "hard_security_001"]

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Verify reset() / step() / state() contracts
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("PHASE 1: VERIFY reset() / step() / state() CONTRACTS")
print("=" * 70)

for task in TASKS:
    print(f"\n--- {task} ---")

    # reset()
    r = api("POST", f"/api/reset/{task}")
    assert "observation" in r, f"reset missing observation: {list(r.keys())}"
    assert "state" in r, f"reset missing state: {list(r.keys())}"
    obs = r["observation"]
    state = r["state"]
    assert obs["task_id"] == task, f"task_id mismatch: {obs['task_id']}"
    assert obs["changed_files"], "changed_files empty"
    assert obs["available_actions"], "available_actions empty"
    assert state["current_step"] == 0, f"step should be 0, got {state['current_step']}"
    assert state["actions_taken"] == [], "actions_taken should be empty"
    print(f"  reset() OK  task_id={obs['task_id']}  changed_files={obs['changed_files']}  actions={obs['available_actions']}")

    # state()
    s = api("GET", "/api/state")
    assert s["state"]["current_step"] == 0
    assert s["done"] is False
    print("  state() OK  step=0 done=False")

    # step() with valid action
    action = {"action_type": "inspect_diff", "path": obs["changed_files"][0]}
    r = api("POST", "/api/step", action)
    assert "reward" in r, "step missing reward"
    assert "observation" in r, "step missing observation"
    assert "done" in r, "step missing done"
    assert "state" in r, "step missing state"
    assert r["state"]["current_step"] == 1
    assert len(r["state"]["actions_taken"]) == 1
    assert r["state"]["actions_taken"][0]["action_type"] == "inspect_diff"
    print(f"  step()  OK  reward={r['reward']:.4f} done={r['done']} step=1 action_recorded=True")

    # state() after step
    s = api("GET", "/api/state")
    assert s["state"]["current_step"] == 1
    print("  state() OK  step=1 after step (consistent)")

    # step() with invalid action
    try:
        api("POST", "/api/step", {"action_type": "invalid_action"})
        print("  step(invalid) FAIL  should have returned error")
    except urllib.error.HTTPError as e:
        print(f"  step(invalid) OK  correctly returned HTTP {e.code}")

print("\n[PASS] ALL API CONTRACTS VERIFIED")

# ═══════════════════════════════════════════════════════════════
# PHASE 2: Run heuristic baseline on all tasks (3 runs each)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 2: RUN MODEL ON EASY / MEDIUM / HARD (3 runs each)")
print("=" * 70)

NUM_RUNS = 3
all_results = {}

for task in TASKS:
    all_results[task] = []
    for run_i in range(NUM_RUNS):
        # Reset
        r = api("POST", f"/api/reset/{task}")
        obs = r["observation"]

        steps_log = []
        done = False
        step_num = 0

        while not done:
            r = api("POST", "/api/auto_action")
            action = r["action"]
            reward = r["reward"]
            done = r["done"]
            state = r["state"]

            steps_log.append({
                "step": step_num,
                "action_type": action["action_type"],
                "path": action.get("path", ""),
                "text": action.get("text", "")[:80] if action.get("text") else "",
                "reward": reward,
            })
            step_num += 1

        score = r.get("score", 0)
        report = r.get("report", {})

        all_results[task].append({
            "run": run_i + 1,
            "score": score,
            "status": report.get("grade_status", "?"),
            "steps": step_num,
            "final_action": steps_log[-1]["action_type"],
            "steps_log": steps_log,
            "report": report,
        })

# ═══════════════════════════════════════════════════════════════
# PHASE 3: Detailed logs and decisions
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 3: DETAILED LOGS & FINAL DECISIONS")
print("=" * 70)

for task in TASKS:
    print(f"\n{'─' * 60}")
    print(f"TASK: {task}")
    print(f"{'─' * 60}")
    for result in all_results[task]:
        print(f"\n  Run {result['run']}:")
        for s in result["steps_log"]:
            detail = s["path"] or s["text"] or ""
            if detail:
                detail = f"  ({detail})"
            print(f"    Step {s['step']}: {s['action_type']}{detail}  -> reward={s['reward']:.4f}")
        print(f"    => FINAL DECISION: {result['final_action']}  SCORE: {result['score']:.4f}  STATUS: {result['status']}")

        # Grade report breakdown
        report = result["report"]
        if "checks" in report:
            print(f"    => Grade breakdown:")
            for check in report["checks"]:
                name = check.get("name", "?")
                passed = check.get("passed", False)
                weight = check.get("weight", 0)
                mark = "PASS" if passed else "FAIL"
                print(f"       [{mark}] {name} (weight={weight})")

# ═══════════════════════════════════════════════════════════════
# PHASE 4: Score comparison & consistency
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 4: SCORE COMPARISON & CONSISTENCY")
print("=" * 70)

# Known baseline reference scores
BASELINE_REF = {"easy_auth_001": 0.80, "medium_null_001": 0.90, "hard_security_001": 1.00}

print(f"\n{'Task':<22} {'Run1':>6} {'Run2':>6} {'Run3':>6} {'Avg':>6} {'StdDev':>7} {'Baseline':>9} {'Match':>6}")
print("-" * 70)

total_scores = []
for task in TASKS:
    scores = [r["score"] for r in all_results[task]]
    avg = sum(scores) / len(scores)
    stddev = (sum((s - avg) ** 2 for s in scores) / len(scores)) ** 0.5
    ref = BASELINE_REF[task]
    match = "YES" if abs(avg - ref) < 0.01 else "NO"
    total_scores.extend(scores)

    scores_str = "  ".join(f"{s:.2f}" for s in scores)
    print(f"{task:<22} {scores[0]:>6.2f} {scores[1]:>6.2f} {scores[2]:>6.2f} {avg:>6.2f} {stddev:>7.4f} {ref:>9.2f} {match:>6}")

overall_avg = sum(total_scores) / len(total_scores)
overall_stddev = (sum((s - overall_avg) ** 2 for s in total_scores) / len(total_scores)) ** 0.5

print("-" * 70)
print(f"{'OVERALL':<22} {'':>6} {'':>6} {'':>6} {overall_avg:>6.2f} {overall_stddev:>7.4f}")

print(f"\nAverage Score:  {overall_avg:.4f}")
print(f"Std Deviation:  {overall_stddev:.4f}")
print(f"Consistency:    {'DETERMINISTIC (stddev=0)' if overall_stddev == 0 else f'Variable (stddev={overall_stddev:.4f})'}")

all_pass = all(r["status"] == "PASS" for task in TASKS for r in all_results[task])
print(f"All PASS:       {all_pass}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
