# story_display.py
import customtkinter as ctk
from tkinter import messagebox
from typing import Union, Dict
from config_manager import save_config

# 设置外观和主题 (与主程序保持一致)
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class StoryDisplayWindow(ctk.CTkToplevel):
    """
    一个独立的、临时的窗口，用于展示漂流瓶故事内容（古老羊皮卷样式）。
    这个窗口不依赖于 SettingsWindow。
    """

    def __init__(self, master, story: Dict, story_id: int, pet_instance):
        super().__init__(master)

        self.pet = pet_instance

        self.story_title = story.get("title", "無題的羊皮卷")
        self.story_author = story.get("author", "匿名旅人")
        self.story_content = story.get("content", "內容已被海水浸濕。")
        self.story_id = story_id

        self.title(f"漂流瓶 ID: {story_id}")
        self.gui_width = 700
        self.gui_height = 900
        self.geometry(f"{self.gui_width}x{self.gui_height}")
        self.resizable(True, True)
        self.attributes('-topmost', True)
        self.transient(master)  # 绑定到主窗口
        self.main_frame = None

        # 确保点击窗口标题栏的“X”按钮时也能销毁窗口
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # 居中显示窗口
        self.set_initial_position()

        self.create_widgets()

    def set_initial_position(self):
        """計算並設定視窗初始位置為螢幕中心。"""
        self.update_idletasks()
        screen_w = self.pet.full_screen_width
        screen_h = self.pet.full_screen_height

        start_x = (screen_w // 2) - (self.gui_width // 2)
        start_y = (screen_h // 2) - (self.gui_height // 2)

        self.wm_geometry(f"+{int(start_x)}+{int(start_y)}")

    def create_widgets(self):
        """创建并放置所有 UI 元件（羊皮卷模拟）。"""
        # 主框架使用网格布局，更灵活
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 配置网格权重，使文本框可以扩展
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 标题
        title_label = ctk.CTkLabel(
            self.main_frame,
            text=f"漂流瓶 ({self.story_id})",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f39c12"
        )
        title_label.pack(pady=(15, 10))

        # 故事内容区域 - 使用pack布局并允许扩展
        story_textbox = ctk.CTkTextbox(
            self.main_frame,
            wrap="word",
            font=ctk.CTkFont(size=14, family="Courier"),
            text_color="#4b3832",
            fg_color="#fcfcfc"
        )

        full_text = f"{self.story_title}\n{self.story_author}\n\n{self.story_content}"
        story_textbox.insert("0.0", full_text)
        story_textbox.configure(state="disabled")

        # 使用fill和expand确保文本框填满可用空间
        story_textbox.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10)
        )

        # 关闭按钮
        close_button = ctk.CTkButton(
            self.main_frame,
            text="Close",
            command=self.destroy,
            fg_color="#34495e"
        )
        close_button.pack(pady=(0, 10))

        # 确保窗口显示在最前面
        self.lift()
        self.focus_force()


def show_story_prompt(master, content: Union[str, Dict], story_id: int = None, pet_instance=None):
    """
    弹出确认对话框，询问用户是否打开漂流瓶，并在确认后打开 StoryDisplayWindow。
    """
    # --- 1) 暂时让 master 置顶 ---
    try:
        master.attributes('-topmost', True)
    except Exception:
        pass

    try:
        if story_id:
            if messagebox.askyesno(
                "上钩啦！",
                f"迷途的旅人哟，狐狸钓到了一个漂流瓶！\n你想要打开看看吗？",
                parent=master
            ):
                save_config(master.config, pet_instance.persistent_keys)
                return StoryDisplayWindow(master, content, story_id, pet_instance)

        else:
            messagebox.showinfo("悲伤的事情发生了...", content, parent=master)

    finally:
        # --- 4) 恢复 master 的置顶状态 ---
        try:
            master.attributes('-topmost', False)
        except Exception:
            pass