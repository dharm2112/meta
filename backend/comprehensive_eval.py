#!/usr/bin/env python3
"""
Comprehensive Hackathon Evaluation Script
Tests all core functionality and features
"""
import sys
import traceback
from pathlib import Path

# Test results storage
results = {
    'phase1': {},
    'phase2': {},
    'errors': []
}

def test_section(name):
    """Decorator for test sections"""
    def decorator(func):
        def wrapper():
            print(f"\n{'='*60}")
            print(f"Testing: {name}")
            print('='*60)
            try:
                result = func()
                results['phase1' if 'PHASE1' in name else 'phase2'][name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'details': result
                }
                print(f"✓ {name}: PASS")
                return result
            except Exception as e:
                error_msg = f"{name}: {str(e)}\n{traceback.format_exc()}"
                results['errors'].append(error_msg)
                results['phase1' if 'PHASE1' in name else 'phase2'][name] = {
                    'status': 'ERROR',
                    'details': str(e)
                }
                print(f"✗ {name}: ERROR - {str(e)}")
                return None
        return wrapper
    return decorator


# PHASE 1: Core Functionality Tests
@test_section("PHASE1-1: Load All 5 Tasks")
def test_task_loading():
    from tasks.loader import load_all_tasks
    
    tasks = load_all_tasks()
    print(f"  Found {len(tasks)} tasks")
    
    for task_id, task in tasks.items():
        print(f"  - {task_id}: {task.get('title', 'No title')}")
    
    assert len(tasks) >= 5, f"Expected at least 5 tasks, found {len(tasks)}"
    
    # Verify task structure
    required_keys = ['title', 'description', 'vulnerable_code', 'review_items']
    for task_id, task in tasks.items():
        for key in required_keys:
            assert key in task, f"Task {task_id} missing key: {key}"
    
    return {'task_count': len(tasks), 'task_ids': list(tasks.keys())}


@test_section("PHASE1-2: Environment Reset/Step Lifecycle")
def test_environment_lifecycle():
    from env import CodeReviewEnv
    
    env = CodeReviewEnv()
    
    # Test reset
    state = env.reset()
    print(f"  Initial state keys: {list(state.keys())}")
    assert 'vulnerable_code' in state
    assert 'review_items' in state
    assert env.current_step == 0
    
    # Test step
    action = {
        'comment_index': 0,
        'severity': 'critical',
        'action': 'flag'
    }
    
    next_state, reward, done, info = env.step(action)
    print(f"  After step - reward: {reward}, done: {done}, step: {env.current_step}")
    assert env.current_step == 1
    assert isinstance(reward, (int, float))
    assert isinstance(done, bool)
    
    return {'reset_ok': True, 'step_ok': True, 'state_keys': list(state.keys())}


@test_section("PHASE1-3: Reward Scoring - Perfect Episode")
def test_perfect_episode():
    from env import CodeReviewEnv
    
    env = CodeReviewEnv()
    state = env.reset()
    
    total_reward = 0
    steps = 0
    
    # Get the current task's review items
    task_id = env.current_task_id
    task = env.tasks[task_id]
    review_items = task['review_items']
    
    print(f"  Task: {task_id}")
    print(f"  Review items: {len(review_items)}")
    
    # Try to get perfect score by flagging all critical items
    for idx, item in enumerate(review_items):
        if env.current_step >= env.max_steps:
            break
            
        action = {
            'comment_index': idx,
            'severity': item.get('severity', 'medium'),
            'action': 'flag'
        }
        
        next_state, reward, done, info = env.step(action)
        total_reward += reward
        steps += 1
        print(f"  Step {steps}: reward={reward:.2f}, cumulative={total_reward:.2f}")
        
        if done:
            break
    
    print(f"  Total reward: {total_reward:.2f} over {steps} steps")
    return {'total_reward': total_reward, 'steps': steps}


@test_section("PHASE1-4: Q-Learning Agent Init and Mini-Episode")
def test_qlearning_agent():
    from rl.q_learning import QLearningAgent
    from env import CodeReviewEnv
    
    env = CodeReviewEnv()
    state = env.reset()
    
    agent = QLearningAgent(
        learning_rate=0.1,
        discount_factor=0.95,
        epsilon=0.1
    )
    
    print(f"  Agent initialized with lr={agent.learning_rate}, gamma={agent.discount_factor}")
    
    # Run mini-episode (5 steps)
    total_reward = 0
    for step in range(5):
        action = agent.choose_action(state)
        print(f"  Step {step+1}: action={action}")
        
        next_state, reward, done, info = env.step(action)
        agent.update(state, action, reward, next_state)
        
        total_reward += reward
        state = next_state
        
        if done:
            break
    
    print(f"  Mini-episode reward: {total_reward:.2f}")
    print(f"  Q-table size: {len(agent.q_table)}")
    
    return {'episode_reward': total_reward, 'q_table_size': len(agent.q_table)}


@test_section("PHASE1-5: Dict and ActionModel Inputs")
def test_action_inputs():
    from env import CodeReviewEnv
    from rl.action_space import ActionModel
    
    env = CodeReviewEnv()
    env.reset()
    
    # Test dict action
    dict_action = {
        'comment_index': 0,
        'severity': 'high',
        'action': 'flag'
    }
    state1, reward1, done1, info1 = env.step(dict_action)
    print(f"  Dict action - reward: {reward1}")
    
    # Reset for second test
    env.reset()
    
    # Test ActionModel action
    model_action = ActionModel(
        comment_index=0,
        severity='high',
        action='flag'
    )
    state2, reward2, done2, info2 = env.step(model_action)
    print(f"  ActionModel - reward: {reward2}")
    
    return {'dict_works': True, 'model_works': True, 'rewards': [reward1, reward2]}


# PHASE 2: New Features Tests
@test_section("PHASE2-1: Configurable Rewards")
def test_configurable_rewards():
    from grader.reward import RewardConfig, RewardCalculator
    from env import CodeReviewEnv
    
    # Test custom config
    custom_config = RewardConfig(
        correct_flag=20.0,  # Increased from default 10.0
        incorrect_flag=-15.0,  # More penalty
        correct_pass=8.0
    )
    
    calculator = RewardCalculator(config=custom_config)
    env = CodeReviewEnv(reward_calculator=calculator)
    
    state = env.reset()
    task = env.tasks[env.current_task_id]
    
    # Flag first item
    first_item = task['review_items'][0]
    action = {
        'comment_index': 0,
        'severity': first_item.get('severity', 'medium'),
        'action': 'flag'
    }
    
    _, reward, _, _ = env.step(action)
    print(f"  Reward with custom config: {reward}")
    print(f"  Custom correct_flag: {custom_config.correct_flag}")
    
    # Verify reward is affected by custom config
    assert reward != 0, "Reward should not be zero"
    
    return {'custom_reward': reward, 'config_applied': True}


@test_section("PHASE2-2: New Tasks (easy_csrf_001, medium_race_001)")
def test_new_tasks():
    from tasks.loader import load_all_tasks
    
    tasks = load_all_tasks()
    
    # Check for new tasks
    new_tasks = ['easy_csrf_001', 'medium_race_001']
    found_tasks = []
    
    for task_name in new_tasks:
        if task_name in tasks:
            found_tasks.append(task_name)
            print(f"  ✓ Found: {task_name}")
            print(f"    Title: {tasks[task_name].get('title', 'N/A')}")
        else:
            print(f"  ✗ Missing: {task_name}")
    
    return {'found_tasks': found_tasks, 'expected': new_tasks}


@test_section("PHASE2-3: Evaluation Suite")
def test_evaluation_suite():
    import importlib.util
    
    # Check if eval_suite.py exists
    eval_suite_path = Path(__file__).parent / 'eval_suite.py'
    assert eval_suite_path.exists(), f"eval_suite.py not found at {eval_suite_path}"
    
    # Import and check for compare_agents function
    spec = importlib.util.spec_from_file_location("eval_suite", eval_suite_path)
    eval_suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eval_suite)
    
    assert hasattr(eval_suite, 'compare_agents'), "compare_agents function not found"
    print(f"  ✓ eval_suite.py exists")
    print(f"  ✓ compare_agents function found")
    
    # Check for other evaluation functions
    eval_functions = [name for name in dir(eval_suite) if not name.startswith('_')]
    print(f"  Available functions: {eval_functions}")
    
    return {'has_compare_agents': True, 'functions': eval_functions}


def run_all_tests():
    """Run all test sections"""
    print("\n" + "="*60)
    print("HACKATHON COMPREHENSIVE EVALUATION")
    print("="*60)
    
    # Phase 1 tests
    print("\n\n*** PHASE 1: CORE FUNCTIONALITY ***\n")
    test_task_loading()
    test_environment_lifecycle()
    test_perfect_episode()
    test_qlearning_agent()
    test_action_inputs()
    
    # Phase 2 tests
    print("\n\n*** PHASE 2: NEW FEATURES ***\n")
    test_configurable_rewards()
    test_new_tasks()
    test_evaluation_suite()
    
    # Summary
    print("\n\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    
    phase1_pass = sum(1 for v in results['phase1'].values() if v['status'] == 'PASS')
    phase1_total = len(results['phase1'])
    phase2_pass = sum(1 for v in results['phase2'].values() if v['status'] == 'PASS')
    phase2_total = len(results['phase2'])
    
    print(f"\nPhase 1: {phase1_pass}/{phase1_total} tests passed")
    print(f"Phase 2: {phase2_pass}/{phase2_total} tests passed")
    print(f"Total Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\n*** ERRORS ***")
        for error in results['errors']:
            print(f"\n{error}")
    
    return results


if __name__ == '__main__':
    results = run_all_tests()
    
    # Return exit code
    all_pass = all(
        v['status'] == 'PASS' 
        for phase in ['phase1', 'phase2'] 
        for v in results[phase].values()
    )
    sys.exit(0 if all_pass else 1)
