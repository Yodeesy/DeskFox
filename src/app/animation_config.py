"""Sprite-sheet animation metadata.

Each entry defines the source file, frame dimensions, total frame count,
and named playback ranges used by the animation system.
"""

from __future__ import annotations

from typing import Any, Dict

ANIMATION_CONFIG: Dict[str, Any] = {
    "idle": {
        "filepath": "assets/idle.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"idle": (0, 119)},
    },
    "dragging": [
        {
            "prefix": "drag_A",
            "filepath": "assets/dragging_1.png",
            "frame_w": 350, "frame_h": 350,
            "total_frames": 120,
            "ranges": {
                "start": (0, 12),
                "hold": (12, 119),
                "release": (0, 12),
            },
        },
        {
            "prefix": "drag_B",
            "filepath": "assets/dragging_2.png",
            "frame_w": 350, "frame_h": 350,
            "total_frames": 120,
            "ranges": {
                "start": (0, 24),
                "hold": (24, 119),
                "release": (0, 24),
            },
        },
    ],
    "display": {
        "filepath": "assets/display.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"display": (0, 119)},
    },
    "teleport": {
        "filepath": "assets/teleport.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"teleport": (0, 119)},
    },
    "magic": {
        "filepath": "assets/magic.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {
            "magic_start": (0, 103),
            "magic_keep": (103, 119),
        },
    },
    "fishing": {
        "filepath": "assets/fishing.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"fishing": (0, 119)},
    },
    "result": {
        "filepath": "assets/result.jpg",
        "frame_w": 150, "frame_h": 150,
    },
    "bye": {
        "filepath": "assets/bye.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"bye": (0, 80)},
    },
    "angry": {
        "filepath": "assets/angry.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"angry": (0, 119)},
    },
    "upset": {
        "filepath": "assets/upset.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"upset": (0, 119)},
    },
    "butterfly": {
        "filepath": "assets/butterfly.png",
        "frame_w": 350, "frame_h": 350,
        "total_frames": 120,
        "ranges": {"butterfly": (0, 112)},
    },
}
