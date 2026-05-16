import json
import sys
from pathlib import Path
from typing import Dict

# ----------------------------------------------------------------------
# 1. 导入实际的 StoryManager 和最小化依赖
# ----------------------------------------------------------------------

# 直接导入实际的 StoryManager 类
from src.app.story_manager import StoryManager


class MockDesktopPet:
    """最小化的桌面宠物上下文模拟，仅用于满足 StoryManager 构造函数的依赖。"""

    def __init__(self):
        self.tk_root = None  # 忽略 Tkinter 依赖


# ----------------------------------------------------------------------
# 2. 核心逻辑函数
# ----------------------------------------------------------------------

def load_local_stories() -> Dict[int, str]:
    """
    加载本地 stories.json 文件中的所有故事，并将其内容（字典）
    序列化为 JSON 字符串，以便 StoryManager 正确处理。
    """
    story_path = Path("temp") / "stories.json"

    if not story_path.exists():
        print(f"ERROR: 故事文件未找到: {story_path.resolve()}")
        sys.exit(1)

    try:
        with story_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items() if v and isinstance(v, dict)}
    except (json.JSONDecodeError, Exception) as e:
        print(f"ERROR: 无法解析或读取 stories.json: {e}")
        sys.exit(1)

def batch_upload_stories(manager: StoryManager, stories: Dict[int, str]):
    """
    遍历本地故事字典，并逐个上传到 Web 服务。
    """
    total_count = len(stories)
    success_count = 0

    print(f"\n--- 开始批量上传 ({total_count} 个故事) ---")

    # 按照 ID 升序上传，确保顺序
    sorted_story_ids = sorted(stories.keys())

    for index in sorted_story_ids:
        content = stories[index]

        print(f"\n[{success_count + 1}/{total_count}] 正在上传 ID {index}...")

        # 调用 StoryManager 的同步写入方法
        result = manager.write_data_sync(index, content)

        # 假设 StoryManager.write_data_sync 的输出中包含 "写入成功" 字符串
        if result and "写入成功" in result:
            print(f"  ✅ 成功: ID {index} 上传成功。")
            success_count += 1
        else:
            print(f"  ❌ 失败: ID {index} 上传失败。服务器响应: {result}")

    print("\n" + "-" * 50)
    print(f"批量上传完成：成功 {success_count} 个，失败 {total_count - success_count} 个。")
    print("-" * 50)


# ----------------------------------------------------------------------
# 3. 主执行块
# ----------------------------------------------------------------------

if __name__ == "__main__":

    # --- 配置 Web 服务连接 ---
    WEB_BASE_URL = "https://deskfox.deno.dev"
    WEB_PATHNAME = "/stories"
    # ---------------------------

    print("-" * 50)
    print("--- Deskfox 故事批量上传器 ---")
    print(f"目标 Web 服务: {WEB_BASE_URL}{WEB_PATHNAME}")
    print("-" * 50)

    # 1. 加载本地故事
    local_stories = load_local_stories()
    print(f"本地故事加载成功，共 {len(local_stories)} 个。")

    if not local_stories:
        print("没有故事可供上传。退出。")
        sys.exit(0)

    # 2. 初始化 StoryManager
    mock_pet = MockDesktopPet()
    story_manager = StoryManager(
        pet_context=mock_pet,
        base_url=WEB_BASE_URL,
        pathname=WEB_PATHNAME
    )

    # 3. 执行批量上传
    batch_upload_stories(story_manager, local_stories)