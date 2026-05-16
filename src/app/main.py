"""DeskFox desktop pet application entry point.

Initializes the Tkinter root, loads configuration, creates the
``DesktopPet`` instance, and starts the main event loop.
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from animation_config import ANIMATION_CONFIG
from config_manager import (
    DEFAULT_CONFIG_FILE_NAME,
    PERSISTENT_CONFIG_KEYS,
    load_config,
)
from pet_desktop import DesktopPet
from utils import check_single_instance, resource_path

# Prevent CTK from changing the process DPI mode, which would cause
# the Pygame window size to be incorrect on high-DPI displays.
try:
    ctk.deactivate_automatic_dpi_awareness()
except AttributeError:
    pass

# --- Global constants ---

WIDTH: int = 150
HEIGHT: int = 150
FPS: int = 20

# Load the bundled default settings from the config JSON file.
try:
    default_path: str = resource_path(DEFAULT_CONFIG_FILE_NAME)
    with open(default_path, "r", encoding="utf-8") as f:
        DEFAULT_SETTINGS: Dict[str, Any] = json.load(f)
except Exception:
    DEFAULT_SETTINGS = {
        "web_service_url": "https://deskfox.deno.dev",
        "pathname": "/stories",
        "max_fox_story_num": 7,
        "fox_story_possibility": 0.61,
        "fishing_cooldown_minutes": 10,
        "fishing_success_rate": 0.6489,
        "upset_interval_minutes": 7,
        "angry_possibility": 0.54,
    }

# Runtime state defaults (merged with settings at startup).
DEFAULT_CONFIG: Dict[str, Any] = {
    "rest_interval_minutes": 30,
    "rest_duration_seconds": 30,
    "current_x": 100,
    "current_y": 100,
    "last_read_index": 0,
}

FULL_DEFAULT_CONFIG: Dict[str, Any] = DEFAULT_SETTINGS.copy()
FULL_DEFAULT_CONFIG.update(DEFAULT_CONFIG)

app_config: Dict[str, Any] = load_config(FULL_DEFAULT_CONFIG)


if __name__ == "__main__":
    check_single_instance()

    try:
        tk_root: tk.Tk = tk.Tk()
        tk_root.withdraw()
        tk_root.config = app_config

        pet: DesktopPet = DesktopPet(
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            animation_config=ANIMATION_CONFIG,
            initial_config=app_config,
        )
        pet.persistent_keys = PERSISTENT_CONFIG_KEYS
        pet.tk_root = tk_root
        pet._start_queue_poller()

        pet.run()

    except Exception as e:
        print(f"Program startup failed or fatal error during runtime: {e}")
        sys.exit(1)

    finally:
        if "tk_root" in locals() and tk_root.winfo_exists():
            tk_root.destroy()
