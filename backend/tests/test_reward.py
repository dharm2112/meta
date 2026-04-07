"""Unit tests for reward engine scoring logic."""

import pytest
from env.reward import RewardEngine


class TestRewardEngine:
    """Test deterministic reward scoring."""
    
    def test_score_perfect_episode(self):
        """Test scoring when agent does everything correctly."""
        task = {
            "id": "test_task",
            "changed_files": ["file1.py"],
            "ground_truth": {
                "relevant_files": ["file1.py"],
                "bug_type": "authorization",
                "keywords": ["admin", "role"],
                "root_cause_keywords": ["missing check"],
                "correct_decision": "reject",
            }
        }
        
        actions = [
            {"action_type": "inspect_diff", "path": "file1.py"},
            {"action_type": "comment", "text": "Missing admin role check"},
            {"action_type": "reject", "text": "Authorization bug"},
        ]
        
        score, breakdown = RewardEngine.score_actions(task, actions)
        
        # Should get full score
        assert score == 1.0
        assert breakdown["evidence_score"] == 0.15
        assert breakdown["decision_score"] == 0.50
        assert breakdown["final_decision"] == "reject"
    
    def test_score_wrong_decision(self):
        """Test scoring when final decision is incorrect."""
        task = {
            "id": "test_task",
            "changed_files": ["file1.py"],
            "ground_truth": {
                "relevant_files": ["file1.py"],
                "bug_type": "authorization",
                "keywords": ["admin"],
                "root_cause_keywords": ["missing check"],
                "correct_decision": "reject",
            }
        }
        
        actions = [
            {"action_type": "inspect_diff", "path": "file1.py"},
            {"action_type": "approve", "text": "Looks good"},  # WRONG!
        ]
        
        score, breakdown = RewardEngine.score_actions(task, actions)
        
        # Should not get decision score (0.50 penalty)
        assert breakdown["decision_score"] == 0.0
        assert breakdown["final_decision"] == "approve"
        assert score < 0.5
    
    def test_missing_task_fields_validation(self):
        """Test that missing required fields raise ValueError."""
        invalid_task = {"id": "test"}
        
        with pytest.raises(ValueError) as exc_info:
            RewardEngine.score_actions(invalid_task, [])
        
        assert "missing required field" in str(exc_info.value)
    
    def test_score_clamping(self):
        """Test that scores are clamped to [0.0, 1.0]."""
        task = {
            "id": "test_task",
            "changed_files": ["f1.py", "f2.py"],
            "ground_truth": {
                "relevant_files": ["f1.py"],
                "bug_type": "test",
                "keywords": ["test"],
                "root_cause_keywords": ["test"],
                "correct_decision": "approve",
            }
        }
        
        # Create lots of penalties
        actions = []
        for i in range(10):
            actions.append({"action_type": "inspect_diff", "path": "f2.py"})
        actions.append({"action_type": "reject", "text": "Wrong"})
        
        score, breakdown = RewardEngine.score_actions(task, actions)
        
        # Score should be clamped to 0.0 (not negative)
        assert score >= 0.0
        assert score <= 1.0
