# story_manager.py

import requests
import threading
import sys
from typing import Dict

class StoryManager:
    def __init__(self, pet_context, base_url, pathname):
        self.pet = pet_context
        self.base_url = base_url
        self.pathname = pathname
        self.full_url = f"{self.base_url}{self.pathname}"
        self.last_read_index = 0

    def get_next_story_id(self):
        """
        确定下一个要从 API 获取的数据索引。
        """
        self.last_read_index = self.pet.last_read_index
        return self.last_read_index + 1

    def fetch_story_sync(self, index) -> Dict:
        """
        同步调用 Web GET API 获取指定索引的数据。
        """
        try:
            params = {'index': index}
            response = requests.get(self.full_url, params=params, timeout=5)

            if response.status_code == 200:
                raw_content = response.text
                try:
                    # 方法1: 先尝试标准的JSON解析
                    story_data = response.json()
                except ValueError as json_error:
                    print(f"DEBUG: JSON解析失败，尝试其他方法: {json_error}")

                    try:
                        # 方法2: 使用ast.literal_eval解析Python字面量
                        import ast
                        story_data = ast.literal_eval(raw_content)
                        print("DEBUG: 使用ast.literal_eval解析成功")
                    except (ValueError, SyntaxError) as ast_error:
                        return None

                # 验证必要的字段是否存在
                if isinstance(story_data, dict) and all(key in story_data for key in ['title', 'author', 'content']):

                    return story_data
                else:
                    print("ERROR: Response missing required fields or not a dict")
                    return None
            else:
                print(f"ERROR: Failed to fetch story. Status: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error during story fetch: {e}")
            return None

    def fetch_story_async(self, story_id):
        """
        在後台執行緒中異步執行網路請求，並將結果放入主執行緒隊列。

        這是修改後的邏輯：後台執行緒只負責網路I/O，並將結果放入 pet._tk_queue。
        主執行緒的 _process_queue 方法將會輪詢並處理這個結果。
        """

        def target():
            # 1. 異步調用 StoryManager 的獲取邏輯 (在後台執行緒中)
            story_data_or_error = self.fetch_story_sync(story_id)

            is_successful = isinstance(story_data_or_error, dict)
            payload = story_data_or_error

            # 2. 構造隊列項
            # 結構: ("story_result", is_successful, payload, story_id)
            queue_item = ("story_result", is_successful, payload, story_id)

            # 3. 關鍵：直接將結果放入線程安全的隊列
            try:
                # 使用 self.pet._tk_queue，這是 DesktopPet 實例中的 Queue 物件
                self.pet._tk_queue.put(queue_item)
            except Exception as e:
                # 只有在隊列對象無效時才會失敗
                print(f"ERROR: [Async Thread] Failed to push result to queue: {e}", file=sys.stderr, flush=True)

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()

    def write_data_sync(self, index, data):
        """
        同步调用 Web POST API 写入数据。

        Args:
            index (str or int): 想要写入的数据的索引。
            data (dict): 写入的数据。

        Returns:
            str: API 返回的成功/失败信息，如果失败返回 None。
        """
        try:
            json_payload = {
                "index": str(index),
                "data": data
            }
            # POST 请求不需要 URL 参数，数据在 JSON body 中
            response = requests.post(
                self.full_url,
                json=json_payload,
                timeout=5,
                headers={'Content-Type': 'application/json'}  # 显式设置 content-type
            )

            if response.status_code == 200:
                # API 返回两句话，写入成功或写入失败
                return response.text
            else:
                print(f"ERROR: Failed to write data. Status: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error during data write: {e}")
            return None