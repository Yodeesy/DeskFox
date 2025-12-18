# utils.py
# Utility functions, primarily for handling resource paths in a production environment.

import os
import win32event
import win32api
import winerror
import sys

MUTEX_NAME = "DeskFox"


def check_single_instance():
    """
    检查并确保应用程序只有一个实例在运行。
    如果检测到已有实例，则立即退出程序。
    """
    try:
        # 尝试创建一个命名互斥锁（Named Mutex）
        # 如果互斥锁已存在，win32event.CreateMutex 会返回一个已存在的句柄，
        # 并且 win32api.GetLastError() 会返回 winerror.ERROR_ALREADY_EXISTS。

        mutex_handle = win32event.CreateMutex(None, 1, MUTEX_NAME)

        # 检查错误码
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            print("檢測到應用程序已在運行。阻止重複啟動。")

            # 立即退出程序，不进行任何初始化
            sys.exit(0)

        # 如果是第一个实例，mutex_handle 将保持开启状态，直到程序退出。
        global _mutex_handle_ref
        _mutex_handle_ref = mutex_handle

    except Exception as e:
        # 如果 Mutex 检查失败（例如，权限问题），则记录错误并允许继续运行
        print(f"Mutex 檢查失敗: {e}. 應用程序將繼續啟動。")

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

