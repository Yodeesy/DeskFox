# config_manager.py

import json
import os
from typing import Dict, Any

# --- 全局常量定义 ---
# 应用程序名称，用于创建 Windows AppData 目录下的文件夹
APP_NAME = "DeskFox"
# 默认配置文件的名称（用于 resource_path 定位程序包内的只读文件）
DEFAULT_CONFIG_FILE_NAME = "src/config/pet_config.json"
# 用户数据文件的名称（用于 get_user_data_path 定位用户可写文件）
USER_DATA_FILE_NAME = "user_data.json"

PERSISTENT_CONFIG_KEYS = [
    "current_x",
    "current_y",
    "last_read_index",
    "rest_interval_minutes",
    "rest_duration_seconds",
]

def get_user_data_path() -> str:
    """
    计算并返回 Windows 系统上用户可写配置文件的标准路径 (%APPDATA% 目录)。
    """

    # 1. 获取 APPDATA 目录路径 (优先 Roaming)
    # C:\Users\<Username>\AppData\Roaming
    app_data_dir = os.environ.get('APPDATA')

    # 如果 APPDATA 不存在，退回到 LOCALAPPDATA 或用户主目录
    if not app_data_dir:
        app_data_dir = os.environ.get('LOCALAPPDATA') or os.path.expanduser("~")

    # 2. 创建应用程序专用的配置目录，例如 ...Roaming\MyPetApp
    config_dir = os.path.join(app_data_dir, APP_NAME)

    # 3. 确保目录存在 (初次运行时创建)
    os.makedirs(config_dir, exist_ok=True)

    # 4. 组合用户可写文件的完整路径
    return os.path.join(config_dir, USER_DATA_FILE_NAME)


def load_config(default_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    尝试从用户可写目录加载 user_data.json，并与内置的 default_config 合并。

    Args:
        default_config: 默认配置字典，通常是通过 resource_path 读取的 pet_config.json 内容。

    Returns:
        合并后的配置字典。
    """
    # 获取用户可写文件的路径
    user_config_path = get_user_data_path()

    # 如果用户文件不存在，直接返回默认配置
    if not os.path.exists(user_config_path):
        return default_config

    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

            # 核心逻辑：复制默认配置，并用用户数据覆盖
            config = default_config.copy()
            config.update(loaded_data)
            return config

    except json.JSONDecodeError:
        # JSON 解析错误，退回到默认配置
        return default_config
    except Exception:
        # 其他读取错误，退回到默认配置
        return default_config

def save_config(full_config_data: Dict[str, Any], keys_to_save: list):
    """
    Saves a filtered subset of the configuration to the user-writable file.

    Args:
        full_config_data: 完整的配置字典 (app_config)。
        keys_to_save: 需要持久化到磁盘的键列表。
    """

    # 1. 过滤数据：只保留需要保存的键值对
    data_to_save = {
        key: full_config_data[key]
        for key in keys_to_save
        if key in full_config_data  # 确保键在字典中存在
    }

    # 如果要保存的数据为空，则无需继续写入文件
    if not data_to_save:
        return

    # 2. 获取用户可写文件的路径
    user_config_path = get_user_data_path()

    try:
        with open(user_config_path, 'w', encoding='utf-8') as f:
            # 写入过滤后的数据 (data_to_save)，确保只包含用户状态
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    except Exception as e:
        # 文件写入错误
        print(f"Error saving config: {e}")
        pass