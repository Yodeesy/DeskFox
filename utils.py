# utils.py
# Utility functions, primarily for handling resource paths in a production environment.

import os
import sys

def resource_path(relative_path):
    """
    Get the absolute path to a resource file, compatible with both
    development environments and PyInstaller bundled executables.

    When bundled by PyInstaller, resources are extracted to a temporary folder
    referenced by sys._MEIPASS.

    Args:
        relative_path (str): The relative path to the resource
                             (e.g., 'assets/image.png').

    Returns:
        str: The absolute path to the resource file.
    """
    try:
        # PyInstaller creates a temp directory and sets this attribute
        base_path = sys._MEIPASS
    except Exception:
        # Fallback to the current directory for development or unbundled execution
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)