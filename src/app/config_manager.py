"""Configuration persistence layer.

Reads a default (read-only) config bundled with the app and merges it with
user-writable state saved to ``%APPDATA%``. Only a whitelisted set of keys
are persisted across sessions.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

APP_NAME: str = "DeskFox"
DEFAULT_CONFIG_FILE_NAME: str = "src/config/pet_config.json"
USER_DATA_FILE_NAME: str = "user_data.json"

PERSISTENT_CONFIG_KEYS: List[str] = [
    "current_x",
    "current_y",
    "last_read_index",
    "rest_interval_minutes",
    "rest_duration_seconds",
]


def get_user_data_path() -> str:
    """Return the path to the user-writable config file.

    Uses the Windows ``%APPDATA%`` directory (Roaming profile). Falls back
    to ``%LOCALAPPDATA%`` or the user home directory if unavailable.

    Returns:
        Full path to ``user_data.json`` inside the app's AppData folder.
    """
    app_data_dir: str = os.environ.get("APPDATA", "")

    if not app_data_dir:
        app_data_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")

    config_dir = os.path.join(app_data_dir, APP_NAME)
    os.makedirs(config_dir, exist_ok=True)

    return os.path.join(config_dir, USER_DATA_FILE_NAME)


def load_config(default_config: Dict[str, Any]) -> Dict[str, Any]:
    """Load and merge persisted config with the built-in defaults.

    Reads ``user_data.json`` from the AppData directory. If the file does
    not exist or is malformed, the default config is returned unchanged.

    Args:
        default_config: The full default configuration dictionary.

    Returns:
        A merged dictionary: defaults overlaid with any persisted values.
    """
    user_config_path = get_user_data_path()

    if not os.path.exists(user_config_path):
        return default_config

    try:
        with open(user_config_path, "r", encoding="utf-8") as f:
            loaded_data: Dict[str, Any] = json.load(f)
            config = default_config.copy()
            config.update(loaded_data)
            return config
    except json.JSONDecodeError:
        return default_config
    except Exception:
        return default_config


def save_config(
    full_config_data: Dict[str, Any], keys_to_save: List[str]
) -> None:
    """Persist a filtered subset of the configuration to disk.

    Only keys listed in ``keys_to_save`` are written; all other values
    are discarded before writing.

    Args:
        full_config_data: The complete runtime configuration dictionary.
        keys_to_save: List of key names to persist.
    """
    data_to_save = {
        key: full_config_data[key]
        for key in keys_to_save
        if key in full_config_data
    }

    if not data_to_save:
        return

    user_config_path = get_user_data_path()

    try:
        tmp_path = user_config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, user_config_path)
    except Exception as e:
        print(f"Error saving config: {e}")
