"""Unit tests for action validation."""

import pytest
from pydantic import ValidationError
from env.action import ActionModel


class TestActionModel:
    """Test action validation with Pydantic."""
    
    def test_valid_inspect_diff(self):
        """Test valid inspect_diff action."""
        action = ActionModel(action_type="inspect_diff", path="file.py")
        assert action.action_type == "inspect_diff"
        assert action.path == "file.py"
    
    def test_valid_comment(self):
        """Test valid comment action."""
        action = ActionModel(action_type="comment", text="Bug found here")
        assert action.action_type == "comment"
        assert action.text == "Bug found here"
    
    def test_invalid_action_type(self):
        """Test that invalid action types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ActionModel(action_type="invalid_action")
        
        assert "Invalid action_type" in str(exc_info.value)
    
    def test_inspect_diff_requires_path(self):
        """Test that inspect_diff requires path."""
        with pytest.raises(ValidationError) as exc_info:
            ActionModel(action_type="inspect_diff")
        
        assert "path" in str(exc_info.value).lower()
    
    def test_comment_requires_text(self):
        """Test that comment requires non-empty text."""
        with pytest.raises(ValidationError) as exc_info:
            ActionModel(action_type="comment", text="")
        
        assert "text" in str(exc_info.value).lower()
