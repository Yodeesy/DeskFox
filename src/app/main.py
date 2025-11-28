# main.py

import customtkinter as ctk
import tkinter as tk
from config_manager import load_config
from pet_desktop import DesktopPet
import sys

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
        "ranges": {"bye": (0, 119)}
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
}

# Default configuration used if the config file does not exist
DEFAULT_CONFIG = {
    "rest_interval_minutes": 60,
    "rest_duration_seconds": 30,
    "current_x": 100,  # Saved position at last close
    "current_y": 100
}

# Load application configuration at startup
app_config = load_config(DEFAULT_CONFIG)

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

        # 3. Store tk_root in the pet instance for use by SettingsWindow and States
        pet.tk_root = tk_root

        # 4. Start the main application loop
        pet.run()

    except Exception as e:
        print(f"Program startup failed or fatal error during runtime: {e}")
        sys.exit(1)

    finally:
        # Ensure tk_root is properly destroyed upon exit
        if 'tk_root' in locals() and tk_root.winfo_exists():
            tk_root.destroy()