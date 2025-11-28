# config_manager.py

import json
import os
from typing import Dict, Any
from utils import resource_path

CONFIG_FILE_NAME = resource_path("src/config/pet_config.json")


def load_config(default_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempts to load the configuration from a file.
    Returns the default configuration if the file does not exist or fails to load.

    Args:
        default_config: The baseline configuration dictionary.

    Returns:
        The loaded and merged configuration dictionary.
    """
    config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)

    if not os.path.exists(config_path):
        # Configuration file not found, use default.
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

            # Merge logic: Update default config with loaded data to ensure missing keys use defaults.
            config = default_config.copy()
            config.update(loaded_data)
            return config

    except json.JSONDecodeError:
        # Error during JSON parsing (e.g., malformed file).
        return default_config
    except Exception:
        # Catch other reading errors (e.g., permission issues).
        return default_config


def save_config(config_data: Dict[str, Any]):
    """
    Saves the current configuration dictionary to the JSON file.

    Args:
        config_data: The configuration dictionary to save.
    """
    config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            # Use indent=4 for readable JSON formatting
            json.dump(config_data, f, indent=4, ensure_ascii=False)

    except Exception:
        # Error during file writing (e.g., permission issues).
        pass