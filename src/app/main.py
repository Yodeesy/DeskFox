# main.py

import customtkinter as ctk
import tkinter as tk
from config_manager import DEFAULT_CONFIG_FILE_NAME, PERSISTENT_CONFIG_KEYS, load_config
from utils import resource_path
from pet_desktop import DesktopPet
import sys
import json

# --- Initialization and Configuration ---

# Critical fix: Deactivate automatic DPI scaling before starting Tkinter.
# This prevents CTK from changing the process's DPI mode, ensuring the Pygame window size remains correct.
try:
    ctk.deactivate_automatic_dpi_awareness()
except AttributeError:
    # Handles cases where CTK might not be fully initialized or the version is different.
    pass

# === Global Constants ===
WIDTH, HEIGHT = 150, 150  # Default window size for the idle state
FPS = 15  # Target frame rate

# Animation resource configuration dictionary
ANIMATION_CONFIG = {
    "idle": {
        "filepath": "assets/idle.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"idle": (0, 119)}
    },
    "dragging": [
        {
            "prefix": "drag_A",
            "filepath": "assets/dragging_1.png",
            "frame_w": 350,
            "frame_h": 350,
            "total_frames": 120,
            "ranges": {
                "start": (0, 12),  # Animation for picking up
                "hold": (12, 119),  # Loop animation while holding
                "release": (0, 12)  # Animation for releasing (will be played in reverse)
            }
        },
        {
            "prefix": "drag_B",
            "filepath": "assets/dragging_2.png",
            "frame_w": 350,
            "frame_h": 350,
            "total_frames": 120,
            "ranges": {
                "start": (0, 24),  # Animation for picking up
                "hold": (24, 119),  # Loop animation while holding
                "release": (0, 24)  # Animation for releasing (will be played in reverse)
            }
        }
    ],
    "display": {
        "filepath": "assets/display.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"display": (0, 119)}
    },
    "teleport": {
        "filepath": "assets/teleport.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"teleport": (0, 119)}
    },
    "magic": {
        "filepath": "assets/magic.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {
            "magic_start": (0, 103),
            "magic_keep": (103, 119),
        }
    },
    "fishing": {
        "filepath": "assets/fishing.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"fishing": (0, 119)}
    },
    "result": {
        "filepath": "assets/result.jpg",
        "frame_w": 150,
        "frame_h": 150
    },
    "bye": {
        "filepath": "assets/bye.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"bye": (0, 80)}
    },
    "angry": {
        "filepath": "assets/angry.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"angry": (0, 119)}
    },
    "upset": {
        "filepath": "assets/upset.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"upset": (0, 119)}
    },
    "butterfly": {
        "filepath": "assets/butterfly.png",
        "frame_w": 350,
        "frame_h": 350,
        "total_frames": 120,
        "ranges": {"butterfly": (0, 112)}
    }
}

try:
    default_path = resource_path(DEFAULT_CONFIG_FILE_NAME)
    with open(default_path, 'r', encoding='utf-8') as f:
        DEFAULT_SETTINGS = json.load(f)
except Exception:
    DEFAULT_SETTINGS = {
        "web_service_url": "https://deskfox.deno.dev",
        "pathname": "/stories",
        "max_fox_story_num": 7,
        "fox_story_possibility": 0.61,
        "fishing_cooldown_minutes": 10,
        "fishing_success_rate": 0.6489,
        "upset_interval_minutes": 7,
        "angry_possibility": 0.54
    }

# Default configuration used if the config file does not exist
DEFAULT_CONFIG = {
    "rest_interval_minutes": 30,
    "rest_duration_seconds": 30,
    "current_x": 100,
    "current_y": 100,
    "last_read_index": 0,
}

FULL_DEFAULT_CONFIG = DEFAULT_SETTINGS.copy() # 包含 pet_config.json 的业务参数
FULL_DEFAULT_CONFIG.update(DEFAULT_CONFIG)    # 添加/更新硬编码的状态参数

# Load application configuration at startup
app_config = load_config(FULL_DEFAULT_CONFIG)

if __name__ == "__main__":
    try:
        # 1. Initialize the hidden Tkinter main loop
        tk_root = tk.Tk()
        tk_root.withdraw()  # Hide the Tk root window
        tk_root.config = app_config

        # 2. Initialize the DesktopPet with configurations
        pet = DesktopPet(
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            animation_config=ANIMATION_CONFIG,
            initial_config=app_config
        )

        # 将持久化键列表传递给 Pet 实例
        pet.persistent_keys = PERSISTENT_CONFIG_KEYS

        # 3. Store tk_root in the pet instance for use by SettingsWindow and States
        pet.tk_root = tk_root
        # 启动轮询（主线程调用）
        pet._start_queue_poller()

        # 4. Start the main application loop
        pet.run()

    except Exception as e:
        print(f"Program startup failed or fatal error during runtime: {e}")
        sys.exit(1)

    finally:
        # Ensure tk_root is properly destroyed upon exit
        if 'tk_root' in locals() and tk_root.winfo_exists():
            tk_root.destroy()