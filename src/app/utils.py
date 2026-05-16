"""Utility functions for resource path resolution and single-instance enforcement."""

from __future__ import annotations

import os
import sys
from typing import Optional

import win32api
import win32event
import winerror

MUTEX_NAME: str = "DeskFox"
_mutex_handle_ref: Optional[int] = None


def check_single_instance() -> None:
    """Ensure only one instance of the application is running.

    Creates a named Windows mutex. If the mutex already exists, the
    application exits immediately to prevent duplicate instances.
    """
    try:
        mutex_handle = win32event.CreateMutex(None, 1, MUTEX_NAME)
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            print("Another instance is already running. Exiting.")
            sys.exit(0)

        global _mutex_handle_ref
        _mutex_handle_ref = mutex_handle

    except Exception as e:
        print(f"Mutex check failed: {e}. Continuing startup.")


def get_project_root() -> str:
    """Return the project root directory (two levels above this file)."""
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_file_dir))
    return project_root


def resource_path(relative_path: str) -> str:
    """Get the absolute path to a resource file.

    Works in both development environments and PyInstaller-bundled
    executables. When bundled, PyInstaller extracts resources to a
    temporary directory referenced by ``sys._MEIPASS``.

    Args:
        relative_path: Path relative to the project root
            (e.g. ``'assets/image.png'``).

    Returns:
        The normalized absolute path to the resource.
    """
    try:
        base_path: str = sys._MEIPASS
    except Exception:
        base_path = get_project_root()

    full_path = os.path.join(base_path, relative_path)
    return os.path.normpath(full_path)
