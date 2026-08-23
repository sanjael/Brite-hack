import json
import os
from typing import Optional
from src.policy.models import PolicyFileConfig


def load_policy_config(config_path: Optional[str] = None) -> PolicyFileConfig:
    """
    Loads policy config from JSON file. Defaults to config/policy.json relative to project root.
    """
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "policy.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Policy configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return PolicyFileConfig(**data)
