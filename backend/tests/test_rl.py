"""Unit tests for Q-learning agent."""

import pytest
from rl.q_learning import QLearningReviewAgent


class TestQLearningReviewAgent:
    """Test Q-learning agent behavior."""
    
    def test_agent_initialization(self):
        """Test agent initializes with correct hyperparameters."""
        agent = QLearningReviewAgent(
            alpha=0.5,
            gamma=0.95,
            epsilon=0.3
        )
        
        assert agent.alpha == 0.5
        assert agent.gamma == 0.95
        assert agent.epsilon == 0.3
        assert len(agent.q_table) == 0
    
    def test_epsilon_decay(self):
        """Test epsilon decays correctly."""
        agent = QLearningReviewAgent(epsilon=0.5, epsilon_min=0.1, epsilon_decay=0.9)
        
        initial_epsilon = agent.epsilon
        agent.decay_epsilon()
        
        assert agent.epsilon < initial_epsilon
        assert agent.epsilon == 0.5 * 0.9
    
    def test_state_key_consistency(self):
        """Test state keys are consistent for same state."""
        agent = QLearningReviewAgent()
        
        obs = {
            "task_id": "test_task",
            "latest_event": {"kind": "summary"},
        }
        state = {
            "current_step": 1,
            "inspected_diffs": ["file1.py"],
            "inspected_files": [],
            "actions_taken": [],
        }
        
        key1 = agent.state_key(obs, state)
        key2 = agent.state_key(obs, state)
        
        assert key1 == key2
