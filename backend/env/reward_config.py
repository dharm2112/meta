"""Reward configuration for code review environment."""

import os
from typing import Dict


class RewardConfig:
    """Configurable reward weights for scoring episodes."""
    
    def __init__(self):
        """Initialize with defaults or environment variables."""
        # Evidence gathering weights
        self.relevant_diff_weight = float(os.getenv("REWARD_RELEVANT_DIFF", "0.15"))
        self.relevant_file_weight = float(os.getenv("REWARD_RELEVANT_FILE", "0.10"))
        
        # Issue identification weights
        self.bug_type_weight = float(os.getenv("REWARD_BUG_TYPE", "0.15"))
        self.root_cause_weight = float(os.getenv("REWARD_ROOT_CAUSE", "0.10"))
        
        # Decision weight
        self.final_decision_weight = float(os.getenv("REWARD_FINAL_DECISION", "0.50"))
        
        # Penalties
        self.irrelevant_inspection_penalty = float(os.getenv("PENALTY_IRRELEVANT", "0.03"))
        self.repeated_action_penalty = float(os.getenv("PENALTY_REPEATED", "0.02"))
        self.hallucinated_comment_penalty = float(os.getenv("PENALTY_HALLUCINATED", "0.05"))
        
        self._validate()
    
    def _validate(self):
        """Ensure weights sum correctly and are in valid ranges."""
        total_positive = (
            self.relevant_diff_weight +
            self.relevant_file_weight +
            self.bug_type_weight +
            self.root_cause_weight +
            self.final_decision_weight
        )
        
        if abs(total_positive - 1.0) > 0.01:
            raise ValueError(
                f"Reward weights must sum to 1.0, got {total_positive:.3f}. "
                "Adjust REWARD_* environment variables."
            )
        
        # Validate all are positive
        for attr, value in self.__dict__.items():
            if attr.startswith("_"):
                continue
            if value < 0:
                raise ValueError(f"{attr} must be non-negative, got {value}")
    
    def to_dict(self) -> Dict[str, float]:
        """Export configuration as dictionary."""
        return {
            "relevant_diff_weight": self.relevant_diff_weight,
            "relevant_file_weight": self.relevant_file_weight,
            "bug_type_weight": self.bug_type_weight,
            "root_cause_weight": self.root_cause_weight,
            "final_decision_weight": self.final_decision_weight,
            "irrelevant_inspection_penalty": self.irrelevant_inspection_penalty,
            "repeated_action_penalty": self.repeated_action_penalty,
            "hallucinated_comment_penalty": self.hallucinated_comment_penalty,
        }
    
    @classmethod
    def from_dict(cls, config: Dict[str, float]) -> "RewardConfig":
        """Create configuration from dictionary."""
        instance = cls.__new__(cls)
        for key, value in config.items():
            setattr(instance, key, value)
        instance._validate()
        return instance


# Global default configuration
default_config = RewardConfig()
