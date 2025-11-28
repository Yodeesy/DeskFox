# utils.py
# Utility functions, primarily for handling resource paths in a production environment.

import os
import sys

def get_project_root():
    """自动获取项目根目录"""
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_file_dir))
    return project_root

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
        base_path = get_project_root()

    full_path = os.path.join(base_path, relative_path)
    return os.path.normpath(full_path)
