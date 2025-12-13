"""Centralized configuration loader for SMO project.

This module provides a single source of truth for configuration loading
that can be used by agent.py, web_dashboard.py, and tui_dashboard.py.
"""

import yaml
from pathlib import Path
from typing import Dict, Any

# Project root and config path
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

# Default configuration
DEFAULT_CONFIG = {
    "refresh": {
        "cpu": 2,
        "memory": 5,
        "disk": 10,
        "network": 5,
        "process": 2
    },
    "logging": {
        "format": "json"
    },
    "agent": {
        "snapshot_interval": 2
    },
    "display": {
        "show_snapshot_info": True,
        "pretty_max_depth": 2,
        "pretty_max_length": 1200
    },
    "alerts": {
        "cpu_percent": 80,
        "memory_percent": 85,
        "disk_usage": 90,
        "network_bytes_sent": 1000000
    }
}


def _deep_merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def load_config() -> Dict[str, Any]:
    """Load YAML config with deep merge fallback.
    
    Returns:
        Dictionary containing the merged configuration
    """
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged = _deep_merge_dicts(DEFAULT_CONFIG, data)
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False


def get_config_path() -> Path:
    """Get the path to the config file.
    
    Returns:
        Path object pointing to config.yaml
    """
    return CONFIG_PATH
