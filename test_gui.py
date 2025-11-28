# settings_gui_temp.py
# 需要安装 customtkinter 和 pygame 才能运行此测试
# WARNING: This is a TEMPORARY, standalone version for UI design ONLY.
# IT DOES NOT FUNCTIONALLY CONTROL THE DESKTOP PET.
# All pet state transitions and configuration updates are disabled or simulated.
#

import pygame
from tkinter import messagebox
import customtkinter as ctk
import os
import sys
import winreg
import ctypes
import webbrowser


# 模拟 DesktopPet 的配置和状态，仅用于初始化
class MockPet:
    """模拟 DesktopPet 实例，提供最基本的属性和方法，避免 NameError。"""

    # 模拟配置属性
    config = {
        "rest_interval_minutes": 60,
        "rest_duration_seconds": 30
    }

    # 模拟窗口位置和大小（用于 set_initial_position 逻辑）
    current_window_pos = [500, 300]
    width = 100

    # 模拟状态检查（避免 import 循环）
    class state:
        __class__ = 'IdleState'  # 仅用于模拟 __class__.__name__ 检查
        __name__ = 'IdleState'

    # 模拟方法
    def change_state(self, new_state):
        pass  # 无操作

    def update_rest_config(self, interval_ms, duration_ms):
        print(f"Mock: Updated rest config to {interval_ms / 60000}m, {duration_ms / 1000}s")
        pass  # 无操作

    def update_display_follow(self):
        pass  # 无操作

    def update_idletasks(self):
        pass  # 无操作

    def winfo_exists(self):
        return True  # 模拟窗口存在


# DWM Effect Constants (for Acrylic effect)
DWM_EC_ENABLE_ACRYLIC = 3
WCA_ACCENT_POLICY = 19
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# Set theme and appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


# --- 模拟 config_manager.save_config ---
def save_config(config):
    print(f"Mock: Configuration saved/updated.")
    pass


# --- 模拟状态类 ---
# 简单的占位类
class DisplayState:
    pass


class IdleState:
    pass


class SettingsWindow(ctk.CTkToplevel):
    """
    A CustomTkinter Toplevel window for managing desktop pet settings.
    (TEMP VERSION: Uses MockPet for standalone operation)
    """

    def __init__(self, master, pet_instance):
        # 🌟 临时修改：忽略传入的 pet_instance，使用 MockPet 🌟
        self.pet = MockPet()
        # 原始代码中 master 是 tk_root，但配置在 pet_instance 中。
        # 在这个临时版本中，我们直接从 MockPet 中获取配置。

        super().__init__(master)
        self.title("Desktop Pet Settings (Temp UI)")

        # Initial dimensions
        self.gui_width = 479
        self.gui_height = 574
        self.geometry(f"{self.gui_width}x{self.gui_height}")

        self.resizable(False, False)
        self.attributes('-topmost', True)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        # Initialize autostart variable based on current registry status
        initial_autostart = self._check_autostart()
        self.autostart_var = ctk.BooleanVar(value=initial_autostart)

        # StringVars for input fields
        # 1. Rest Interval (read from MockPet.config)
        self.interval_var = ctk.StringVar(value=str(self.pet.config.get("rest_interval_minutes", 60)))

        # 2. Rest Duration (read from MockPet.config)
        self.duration_var = ctk.StringVar(value=str(self.pet.config.get("rest_duration_seconds", 30)))

        # 🌟 临时修改：移除配置绑定和跟随逻辑 🌟
        # self.bind('<Configure>', self.on_gui_configure) # 移除
        self.after(200, lambda: print("Mock: Change state to DisplayState (Disabled)"))
        self.after(100, self.apply_acrylic_effect)
        self.create_widgets()

    # 🌟 临时修改：on_gui_configure 🌟
    def on_gui_configure(self, event):
        """TEMP: Triggers the pet's follow logic in real-time when the GUI window is moved."""
        if event.widget == self:
            # 简化状态检查，避免导入依赖
            if self.pet.state.__name__ == 'DisplayState':
                self.pet.update_display_follow()

    # 🌟 临时修改：set_initial_position 🌟
    def set_initial_position(self):
        """TEMP: Calculates and sets the initial position of the GUI window to be near the pet."""
        self.update_idletasks()  # Tkinter method

        # 1. Get pet window information (using MockPet)
        pet_x = self.pet.current_window_pos[0]
        pet_y = self.pet.current_window_pos[1]
        pet_w = self.pet.width

        # 2. Get screen dimensions (使用 Pygame 模拟)
        screen_modes = pygame.display.get_desktop_sizes()
        screen_w, screen_h = screen_modes[0]

        # 3. Determine initial X coordinate (prefer placing to the right)
        gap = 10
        target_x_right = pet_x + pet_w + gap

        # ... (位置计算逻辑不变) ...
        if target_x_right + self.gui_width < screen_w:
            start_x = target_x_right
        else:
            target_x_left = pet_x - self.gui_width - gap
            if target_x_left >= 0:
                start_x = target_x_left
            else:
                start_x = pet_x + (pet_w // 2) - (self.gui_width // 2)

        # 4. Determine Y coordinate
        start_y = pet_y
        if start_y + self.gui_height > screen_h:
            start_y = screen_h - self.gui_height
        start_y = max(0, start_y)

        self.wm_geometry(f"+{int(start_x)}+{int(start_y)}")

    def create_widgets(self):
        # ... (代码不变) ...
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 0. GitHub Link  ---
        link_label = ctk.CTkLabel(
            self.main_frame,
            text="More info? 🔜 GitHub",
            text_color="#3498db",
            font=ctk.CTkFont(underline=True, size=14, weight="bold")
        )
        link_label.bind("<Button-1>", self.open_github_link)
        link_label.configure(cursor="hand2")
        link_label.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="n")

        # --- 1. Autostart Setting ---
        autostart_check = ctk.CTkCheckBox(
            self.main_frame,
            text="Launch on Startup",
            variable=self.autostart_var,
            command=self.toggle_autostart,
            text_color="#D4D4D4",
            font=ctk.CTkFont(weight="bold")
        )
        autostart_check.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # --- 2. Eye Rest Reminder Area ---
        rest_frame = ctk.CTkFrame(self.main_frame)
        rest_frame.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

        # Area Title
        ctk.CTkLabel(
            rest_frame,
            text="--- Eye Rest Reminder Settings ---",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="n")

        # Interval Setting
        ctk.CTkLabel(rest_frame, text="Rest Interval (min):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        interval_entry = ctk.CTkEntry(rest_frame, width=80, textvariable=self.interval_var)
        interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Duration Setting
        ctk.CTkLabel(rest_frame, text="Rest Duration (sec):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        duration_entry = ctk.CTkEntry(rest_frame, width=80, textvariable=self.duration_var)
        duration_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        save_button = ctk.CTkButton(rest_frame, text="Save Settings", command=self.save_rest_settings)
        save_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        # --- 3. Exit Button ---
        exit_button = ctk.CTkButton(
            self.main_frame,
            text="Exit Desktop Pet",
            command=self.confirm_exit,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        exit_button.grid(row=3, column=0, padx=5, pady=10, sticky="ew")

    def save_rest_settings(self):
        """TEMP: Validates input, updates MockPet, and calls mock save_config."""
        try:
            # 1. Get and clean input
            interval_str = self.interval_var.get().strip()
            duration_str = self.duration_var.get().strip()

            if not interval_str or not duration_str:
                raise ValueError("Interval and duration cannot be empty.")

            # 2. Convert to integer and validate type
            try:
                interval = int(interval_str)
                duration = int(duration_str)
            except ValueError:
                raise ValueError("Input values must be positive integers.")

            # 3. Validation (unchanged)
            MIN_INTERVAL = 2
            MAX_INTERVAL = 120
            if not (MIN_INTERVAL <= interval <= MAX_INTERVAL):
                raise ValueError(f"Rest interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} minutes.")

            MIN_DURATION = 15
            MAX_DURATION = 300
            if not (MIN_DURATION <= duration <= MAX_DURATION):
                raise ValueError(f"Rest duration must be between {MIN_DURATION} and {MAX_DURATION} seconds.")

            # 4. Validation passed, update configuration
            self.pet.config["rest_interval_minutes"] = interval
            self.pet.config["rest_duration_seconds"] = duration

            # 🌟 临时修改：调用 MockPet 的更新方法 🌟
            self.pet.update_rest_config(interval * 60 * 1000, duration * 1000)

            # 🌟 临时修改：调用 Mock 的保存方法 🌟
            save_config(self.pet.config)

            messagebox.showinfo("Settings Saved", "Eye rest reminder settings have been saved!", parent=self)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self)

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)

    def open_github_link(self, event=None):
        # ... (代码不变) ...
        github_url = "https://github.com/Yodeesy/DeskFox.git"
        webbrowser.open_new_tab(github_url)

    def apply_acrylic_effect(self):
        # ... (代码不变，依赖 ctypes 和 win32 API) ...
        """Attempts to apply Windows 10/11 Acrylic or Mica blur effect."""

        self.set_initial_position()  # 确保在应用效果前位置正确

        try:
            self.wm_attributes("-transparentcolor", "")
            if hasattr(self, 'main_frame'):
                self.main_frame.configure(fg_color="transparent")
            self.configure(fg_color='transparent')
            self.overrideredirect(True)
        except Exception:
            pass

        # Define DWM Structures (保持不变)
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int),
            ]

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int), ("AnimationId", ctypes.c_int)
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(ACCENT_POLICY)),
                ("SizeOfData", ctypes.c_size_t)
            ]

        # 3. DWM API call
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

            # --- A. 强制 DWM 渲染接管整个客户区 ---
            margins = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                hwnd, ctypes.byref(margins)
            )

            # --- B. 应用亚克力样式 ---
            policy = ACCENT_POLICY()
            policy.AccentState = DWM_EC_ENABLE_ACRYLIC
            policy.AccentFlags = 0
            policy.GradientColor = 0x01FFFFFF

            wca_data = WINDOWCOMPOSITIONATTRIBDATA()
            wca_data.Attribute = WCA_ACCENT_POLICY
            wca_data.SizeOfData = ctypes.sizeof(policy)
            wca_data.Data = ctypes.pointer(policy)

            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, wca_data)

            # --- C. 设置深色模式 ---
            try:
                dark_mode = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(dark_mode), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass

        except Exception:
            pass

    def _get_app_path(self):
        # ... (代码不变) ...
        """Gets the full executable path and wraps it in double quotes."""
        app_path = os.path.abspath(sys.executable)
        return f'"{app_path}"'

    def _check_autostart(self):
        # ... (代码不变) ...
        """Checks if the autostart registry key exists."""
        RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "DesktopPet"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Autostart check failed: {e}")
            return False

    def _set_autostart(self, enable: bool):
        # ... (代码不变) ...
        """Sets or deletes the autostart registry entry."""
        RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "DesktopPet"
        app_path = self._get_app_path()

        if enable:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
                return True
            except Exception:
                return False
        else:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
                    winreg.DeleteValue(key, APP_NAME)
                return True
            except FileNotFoundError:
                return True
            except Exception as e:
                messagebox.showerror("Autostart Error", f"Failed to delete registry entry. Error: {e}", parent=self)
                return False

    def toggle_autostart(self):
        # ... (代码不变) ...
        """Handles the CheckBox click: attempts to set/unset autostart."""
        is_on = self.autostart_var.get()
        success = self._set_autostart(is_on)

        if success:
            status = "enabled" if is_on else "disabled"
            messagebox.showinfo("Autostart Setting", f"Launch on Startup is successfully {status}.", parent=self)
        else:
            action = "enable" if is_on else "disable"
            messagebox.showerror("Autostart Error",
                                 f"Failed to {action} autostart. Please try running the application as administrator.",
                                 parent=self)
            self.autostart_var.set(not is_on)

    def confirm_exit(self):
        """TEMP: Prompts user for confirmation and simulates application exit."""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the desktop pet program?", parent=self):
            print("Mock: Simulating application shutdown.")
            self.destroy()
            sys.exit(0)

    def close_window(self):
        """TEMP: Closes the settings window and performs mock state change."""
        self.destroy()

        # 🌟 临时修改：移除 win32gui 依赖和实际状态切换 🌟
        # if self.pet.state.__class__.__name__ == 'DisplayState':
        #     self.pet.change_state(IdleState(self.pet))
        print("Mock: Settings closed. State transition disabled.")

        # 移除 win32gui.SetWindowPos 逻辑，因为它需要 pet.hwnd


# --- 测试代码 ---
if __name__ == '__main__':
    # 模拟 Tkinter 主根
    root = ctk.CTk()
    root.title("Hidden Root")
    root.geometry("0x0")  # 保持隐藏
    root.withdraw()

    # 实例化 SettingsWindow。传入 None 作为 pet_instance，因为它会被 MockPet 忽略。
    settings = SettingsWindow(root, None)

    # 启动主循环，让窗口显示
    root.mainloop()