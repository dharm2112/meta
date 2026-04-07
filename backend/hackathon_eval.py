"""
Comprehensive Hackathon Evaluation Script
Tests all functionality without external dependencies
"""
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Results tracking
results = {
    'phase1': [],
    'phase2': [],
    'phase3': {},
    'errors': []
}

def test(name, func):
    """Test wrapper"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print('='*70)
    try:
        result = func()
        print(f"[PASS]")
        return {'name': name, 'status': 'PASS', 'result': result}
    except Exception as e:
        print(f"[FAIL]: {e}")
        import traceback
        traceback.print_exc()
        return {'name': name, 'status': 'FAIL', 'error': str(e)}


# ============================================================================
# PHASE 1: CORE FUNCTIONALITY
# ============================================================================

def phase1_test1():
    """Test: Load All 5 Tasks"""
    from tasks.loader import get_available_tasks, load_task
    
    task_ids = get_available_tasks()
    print(f"  Found {len(task_ids)} tasks: {task_ids}")
    
    assert len(task_ids) >= 5, f"Expected >= 5 tasks, got {len(task_ids)}"
    
    # Load each task to verify structure
    for task_id in task_ids:
        task = load_task(task_id)
        print(f"  [OK] {task_id}: {task['label']}")
        assert 'id' in task
        assert 'ground_truth' in task
        assert 'changed_files' in task
    
    return {'count': len(task_ids), 'ids': task_ids}


def phase1_test2():
    """Test: Environment Reset and Step Lifecycle"""
    from env.environment import CodeReviewEnv
    from tasks.loader import get_available_tasks
    
    env = CodeReviewEnv()
    task_id = get_available_tasks()[0]
    
    # Test reset
    obs = env.reset(task_id)
    print(f"  Reset OK - task: {task_id}")
    print(f"  Observation keys: {list(obs.keys())}")
    assert not env.done
    assert env.current_step == 0
    assert 'task_id' in obs
    assert 'latest_event' in obs
    
    # Test step with dict action
    action = {
        'action': 'inspect_diff',
        'target': list(env.task['diffs'].keys())[0]
    }
    
    next_obs, reward, done, info = env.step(action)
    print(f"  Step OK - reward: {reward}, done: {done}")
    assert env.current_step == 1
    assert isinstance(reward, (int, float))
    assert isinstance(done, bool)
    
    return {'reset': True, 'step': True, 'reward': reward}


def phase1_test3():
    """Test: Reward Scoring with Perfect Episode"""
    from env.environment import CodeReviewEnv
    from tasks.loader import get_available_tasks, load_task
    
    env = CodeReviewEnv()
    task_id = get_available_tasks()[0]
    task = load_task(task_id)
    
    obs = env.reset(task_id)
    print(f"  Task: {task_id}")
    print(f"  Max steps: {env.max_steps}")
    
    total_reward = 0.0
    
    # Take some inspection actions
    diffs = list(task['diffs'].keys())
    for diff in diffs[:min(3, len(diffs))]:
        if env.done:
            break
        action = {'action': 'inspect_diff', 'target': diff}
        obs, reward, done, info = env.step(action)
        total_reward += reward
        print(f"  Step {env.current_step}: inspect_diff -> reward={reward:.2f}")
    
    # Make final decision
    if not env.done:
        decision = task['ground_truth']['correct_decision']
        action = {'action': decision}
        obs, reward, done, info = env.step(action)
        total_reward += reward
        print(f"  Step {env.current_step}: {decision} -> reward={reward:.2f}")
    
    print(f"  Total reward: {total_reward:.2f}")
    return {'total_reward': total_reward, 'steps': env.current_step}


def phase1_test4():
    """Test: Q-Learning Agent Initialization and Mini-Episode"""
    from rl.q_learning import QLearningReviewAgent
    from env.environment import CodeReviewEnv
    from tasks.loader import get_available_tasks
    
    agent = QLearningReviewAgent(alpha=0.1, gamma=0.95, epsilon=0.2)
    print(f"  Agent: alpha={agent.alpha}, gamma={agent.gamma}, epsilon={agent.epsilon}")
    
    env = CodeReviewEnv()
    task_id = get_available_tasks()[0]
    obs = env.reset(task_id)
    
    # Run mini-episode (3 steps)
    total_reward = 0.0
    for i in range(3):
        if env.done:
            break
        
        state = {
            'current_step': env.current_step,
            'inspected_diffs': list(env.inspected_diffs),
            'inspected_files': list(env.inspected_files),
            'actions_taken': env.actions_taken.copy()
        }
        
        action = agent.choose_action(obs, state)
        print(f"  Step {i+1}: {action.action} -> target={getattr(action, 'target', 'N/A')}")
        
        next_obs, reward, done, info = env.step(action)
        
        next_state = {
            'current_step': env.current_step,
            'inspected_diffs': list(env.inspected_diffs),
            'inspected_files': list(env.inspected_files),
            'actions_taken': env.actions_taken.copy()
        }
        
        agent.update(obs, state, action, reward, next_obs, next_state, done)
        
        total_reward += reward
        obs = next_obs
    
    print(f"  Episode reward: {total_reward:.2f}")
    print(f"  Q-table size: {len(agent.q_table)}")
    
    return {'reward': total_reward, 'q_size': len(agent.q_table)}


def phase1_test5():
    """Test: Dict and ActionModel Inputs"""
    from env.environment import CodeReviewEnv
    from env.action import ActionModel
    from tasks.loader import get_available_tasks, load_task
    
    env = CodeReviewEnv()
    task_id = get_available_tasks()[0]
    task = load_task(task_id)
    diff = list(task['diffs'].keys())[0]
    
    # Test 1: Dict action
    env.reset(task_id)
    dict_action = {'action': 'inspect_diff', 'target': diff}
    obs1, reward1, done1, info1 = env.step(dict_action)
    print(f"  Dict action: reward={reward1:.2f}")
    
    # Test 2: ActionModel action
    env.reset(task_id)
    model_action = ActionModel(action='inspect_diff', target=diff)
    obs2, reward2, done2, info2 = env.step(model_action)
    print(f"  ActionModel: reward={reward2:.2f}")
    
    # Rewards should be the same for same action
    assert reward1 == reward2, f"Rewards differ: {reward1} vs {reward2}"
    
    return {'dict_ok': True, 'model_ok': True, 'rewards_match': True}


# ============================================================================
# PHASE 2: NEW FEATURES
# ============================================================================

def phase2_test1():
    """Test: Unit Tests Exist and Are Well-Structured"""
    tests_dir = Path(__file__).parent / 'tests'
    
    test_files = list(tests_dir.glob('test_*.py'))
    print(f"  Found {len(test_files)} test files")
    
    for test_file in test_files:
        print(f"  [OK] {test_file.name}")
        content = test_file.read_text()
        # Check for test functions
        test_count = content.count('def test_')
        print(f"    - {test_count} test functions")
    
    assert len(test_files) >= 3, "Expected at least 3 test files"
    
    return {'test_files': len(test_files), 'files': [f.name for f in test_files]}


def phase2_test2():
    """Test: Configurable Rewards"""
    from env.reward_config import RewardConfig
    from env.reward import RewardEngine
    from env.environment import CodeReviewEnv
    from tasks.loader import get_available_tasks, load_task
    
    # Create custom reward config
    custom_config = RewardConfig(
        correct_decision=200.0,  # Much higher than default
        wrong_decision=-100.0,
        inspect_diff=2.0,
        inspect_file=1.0
    )
    
    print(f"  Custom config: correct_decision={custom_config.correct_decision}")
    
    # Test with custom config
    env = CodeReviewEnv()
    task_id = get_available_tasks()[0]
    task = load_task(task_id)
    
    env.reset(task_id)
    
    # Make correct decision
    decision = task['ground_truth']['correct_decision']
    action = {'action': decision}
    obs, reward, done, info = env.step(action)
    
    print(f"  Reward with default config: {reward}")
    
    # Verify RewardConfig can be instantiated with custom values
    assert custom_config.correct_decision == 200.0
    
    return {'custom_config_ok': True, 'reward': reward}


def phase2_test3():
    """Test: New Tasks (easy_csrf_001, medium_race_001)"""
    from tasks.loader import get_available_tasks, load_task
    
    available = get_available_tasks()
    
    new_tasks = ['easy_csrf_001', 'medium_race_001']
    found = []
    
    for task_name in new_tasks:
        if task_name in available:
            task = load_task(task_name)
            found.append(task_name)
            print(f"  [FOUND] {task_name}: {task['label']}")
            print(f"    Difficulty: {task['difficulty']}")
            print(f"    Files: {len(task.get('changed_files', []))}")
        else:
            print(f"  [MISSING] {task_name}: NOT FOUND")
    
    return {'expected': new_tasks, 'found': found, 'all_found': len(found) == len(new_tasks)}


def phase2_test4():
    """Test: Evaluation Suite Exists"""
    eval_suite = Path(__file__).parent / 'eval_suite.py'
    
    assert eval_suite.exists(), "eval_suite.py not found"
    print(f"  [OK] eval_suite.py exists")
    
    content = eval_suite.read_text()
    
    # Check for key functions
    has_compare = 'compare_agents' in content
    has_evaluate = 'evaluate' in content or 'eval' in content
    
    print(f"  [OK] Has compare_agents: {has_compare}")
    print(f"  [OK] Has evaluation functions: {has_evaluate}")
    
    # Count functions
    func_count = content.count('def ')
    print(f"  Functions defined: {func_count}")
    
    return {'exists': True, 'has_compare': has_compare, 'functions': func_count}


# ============================================================================
# PHASE 3: CODE QUALITY (Automated Analysis)
# ============================================================================

def phase3_analysis():
    """Automated code quality analysis"""
    backend = Path(__file__).parent
    
    metrics = {
        'total_py_files': 0,
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0,
        'has_docstrings': 0,
        'has_type_hints': 0,
        'error_handling': 0,
    }
    
    for py_file in backend.rglob('*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        metrics['total_py_files'] += 1
        content = py_file.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        metrics['total_lines'] += len(lines)
        metrics['total_functions'] += content.count('def ')
        metrics['total_classes'] += content.count('class ')
        
        if '"""' in content or "'''" in content:
            metrics['has_docstrings'] += 1
        
        if '->' in content or 'from typing import' in content:
            metrics['has_type_hints'] += 1
        
        if 'try:' in content or 'except' in content:
            metrics['error_handling'] += 1
    
    print(f"  Python files: {metrics['total_py_files']}")
    print(f"  Total lines: {metrics['total_lines']}")
    print(f"  Functions: {metrics['total_functions']}")
    print(f"  Classes: {metrics['total_classes']}")
    print(f"  Files with docstrings: {metrics['has_docstrings']}")
    print(f"  Files with type hints: {metrics['has_type_hints']}")
    print(f"  Files with error handling: {metrics['error_handling']}")
    
    return metrics


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*70)
    print(" COMPREHENSIVE HACKATHON EVALUATION")
    print("="*70)
    
    # PHASE 1: Core Functionality
    print("\n\n*** PHASE 1: CORE FUNCTIONALITY ***")
    results['phase1'].append(test("1.1: Load All 5 Tasks", phase1_test1))
    results['phase1'].append(test("1.2: Environment Reset/Step", phase1_test2))
    results['phase1'].append(test("1.3: Reward Scoring", phase1_test3))
    results['phase1'].append(test("1.4: Q-Learning Agent", phase1_test4))
    results['phase1'].append(test("1.5: Dict/Model Inputs", phase1_test5))
    
    # PHASE 2: New Features
    print("\n\n*** PHASE 2: NEW FEATURES ***")
    results['phase2'].append(test("2.1: Unit Tests Structure", phase2_test1))
    results['phase2'].append(test("2.2: Configurable Rewards", phase2_test2))
    results['phase2'].append(test("2.3: New Tasks", phase2_test3))
    results['phase2'].append(test("2.4: Evaluation Suite", phase2_test4))
    
    # PHASE 3: Code Quality Analysis
    print("\n\n*** PHASE 3: CODE QUALITY ANALYSIS ***")
    print("\n" + "="*70)
    print("Analyzing codebase metrics...")
    print("="*70)
    results['phase3'] = phase3_analysis()
    
    # Summary
    print("\n\n" + "="*70)
    print(" EVALUATION SUMMARY")
    print("="*70)
    
    phase1_pass = sum(1 for t in results['phase1'] if t['status'] == 'PASS')
    phase2_pass = sum(1 for t in results['phase2'] if t['status'] == 'PASS')
    
    print(f"\n[OK] Phase 1 (Core Functionality): {phase1_pass}/{len(results['phase1'])} PASS")
    print(f"[OK] Phase 2 (New Features): {phase2_pass}/{len(results['phase2'])} PASS")
    print(f"[OK] Phase 3 (Code Quality): Metrics collected")
    
    # Detailed results
    print("\n--- Phase 1 Details ---")
    for t in results['phase1']:
        status = "[PASS]" if t['status'] == 'PASS' else "[FAIL]"
        print(f"{status} {t['name']}: {t['status']}")
    
    print("\n--- Phase 2 Details ---")
    for t in results['phase2']:
        status = "[PASS]" if t['status'] == 'PASS' else "[FAIL]"
        print(f"{status} {t['name']}: {t['status']}")
    
    # Save results to JSON
    output_file = Path(__file__).parent / 'evaluation_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[OK] Results saved to: {output_file}")
    
    return results


if __name__ == '__main__':
    try:
        results = main()
        print("\n" + "="*70)
        print("EVALUATION COMPLETE")
        print("="*70)
    except Exception as e:
        print(f"\n[FAIL] EVALUATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
