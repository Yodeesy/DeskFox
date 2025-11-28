# settings_gui.py

import pygame
from src.app.config_manager import save_config
from src.app.pet_states import DisplayState, IdleState, ByeState
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import winreg
import ctypes
import webbrowser

# DWM Effect Constants (for Acrylic effect)
DWM_EC_ENABLE_ACRYLIC = 3  # Acrylic effect (Win 10/11)
WCA_ACCENT_POLICY = 19
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


# Set theme and appearance
ctk.set_appearance_mode("System")  # Supports 'Light', 'Dark', 'System'
ctk.set_default_color_theme("dark-blue")  # Options: 'blue', 'green', 'dark-blue'


class SettingsWindow(ctk.CTkToplevel):
    """
    A CustomTkinter Toplevel window for managing desktop pet settings.
    It follows the pet window when opened.
    """

    def __init__(self, master, pet_instance):
        super().__init__(master)
        self.pet = pet_instance
        self.title("Desktop Pet Settings")

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
        # 1. Rest Interval (read from config)
        self.interval_var = ctk.StringVar(value=str(master.config.get("rest_interval_minutes", 60)))

        # 2. Rest Duration (read from config)
        self.duration_var = ctk.StringVar(value=str(master.config.get("rest_duration_seconds", 30)))

        # Bind the window configure event for real-time pet following
        self.bind('<Configure>', self.on_gui_configure)

        # Delay state change to DisplayState until the window is displayed
        self.after(200, lambda: self.pet.change_state(DisplayState(self.pet)))

        # Attempt to apply Windows acrylic effect
        self.after(100, self.apply_acrylic_effect)
        self.create_widgets()

    def on_gui_configure(self, event):
        """
        Triggers the pet's follow logic in real-time when the GUI window is moved.
        """
        # Only process events on the Toplevel window itself
        if event.widget == self:
            # Check if the pet is in the DisplayState to ensure following logic is active
            if self.pet.state.__class__.__name__ == 'DisplayState':
                self.pet.update_display_follow()

    def set_initial_position(self):
        """Calculates and sets the initial position of the GUI window to be near the pet."""
        self.update_idletasks()

        # 1. Get pet window information
        pet_x = self.pet.current_window_pos[0]
        pet_y = self.pet.current_window_pos[1]
        pet_w = self.pet.width

        # 2. Get screen dimensions
        screen_modes = pygame.display.get_desktop_sizes()
        screen_w, screen_h = screen_modes[0]

        # 3. Determine initial X coordinate (prefer placing to the right)
        gap = 10
        target_x_right = pet_x + pet_w + gap

        if target_x_right + self.gui_width < screen_w:
            start_x = target_x_right
        else:
            # Try placing to the left
            target_x_left = pet_x - self.gui_width - gap
            if target_x_left >= 0:
                start_x = target_x_left
            else:
                # Center over the pet as a last resort
                start_x = pet_x + (pet_w // 2) - (self.gui_width // 2)

        # 4. Determine Y coordinate (top-aligned, bounded by screen edges)
        start_y = pet_y

        # Ensure it doesn't go off the bottom edge
        if start_y + self.gui_height > screen_h:
            start_y = screen_h - self.gui_height

        # Ensure it doesn't go off the top edge
        start_y = max(0, start_y)

        # Apply the calculated position: "WxH+X+Y" format
        self.wm_geometry(f"+{int(start_x)}+{int(start_y)}")

    def create_widgets(self):
        """Creates and places all UI elements (widgets) in the window."""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 0. GitHub Link  ---
        link_label = ctk.CTkLabel(
            self.main_frame,
            text="More info? 🔜 GitHub",
            text_color="#3498db",
            font=ctk.CTkFont(underline=True, size=14, weight="bold")
        )
        # 绑定左键点击事件
        link_label.bind("<Button-1>", self.open_github_link)
        # 增加鼠标悬停手型
        link_label.configure(cursor="hand2")
        # 将其放置在顶部
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
            fg_color="#e74c3c",  # Dark red background
            hover_color="#c0392b"
        )
        exit_button.grid(row=3, column=0, padx=5, pady=10, sticky="ew")

    def save_rest_settings(self):
        """Validates input, saves rest settings, updates the pet, and saves config to file."""
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

            # 3. Validate interval (minutes)
            MIN_INTERVAL = 2
            MAX_INTERVAL = 120
            if not (MIN_INTERVAL <= interval <= MAX_INTERVAL):
                raise ValueError(f"Rest interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} minutes.")

            # 4. Validate duration (seconds)
            MIN_DURATION = 15
            MAX_DURATION = 300
            if not (MIN_DURATION <= duration <= MAX_DURATION):
                raise ValueError(f"Rest duration must be between {MIN_DURATION} and {MAX_DURATION} seconds.")

            # 5. Validation passed, update configuration
            self.master.config["rest_interval_minutes"] = interval
            self.master.config["rest_duration_seconds"] = duration

            # Notify Pet to update internal variables (convert to milliseconds)
            self.pet.update_rest_config(interval * 60 * 1000, duration * 1000)

            # Save configuration to file
            save_config(self.master.config)

            messagebox.showinfo("Settings Saved", "Eye rest reminder settings have been saved!", parent=self)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self)

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)

    def open_github_link(self, event=None):
        """Link to GitHub repo."""
        github_url = "https://github.com/Yodeesy/DeskFox.git"
        webbrowser.open_new_tab(github_url)

    def apply_acrylic_effect(self):
        """Attempts to apply Windows 10/11 Acrylic or Mica blur effect."""

        # 1. Ensure position is set before applying DWM effects
        self.set_initial_position()

        # 2. Attempt transparent color key method for CustomTkinter
        try:
            # Use magenta as the transparent color key
            self.wm_attributes("-transparentcolor", "")

            if hasattr(self, 'main_frame'):
                self.main_frame.configure(fg_color="transparent")

            self.configure(fg_color='transparent')
            self.overrideredirect(True)

        except Exception:
            pass  # Ignore failure if transparent color is not supported

        # Define ACCENT_POLICY structure
        # 结构 A: MARGINS 用于 DwmExtendFrameIntoClientArea
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int),
            ]

        # 结构 B: ACCENT_POLICY 用于 SetWindowCompositionAttribute
        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int)
            ]

        # 结构 C: WINDOWCOMPOSITIONATTRIBDATA
        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.POINTER(ACCENT_POLICY)),
                ("SizeOfData", ctypes.c_size_t)
            ]

        # 3. DWM API call (applying Acrylic effect)
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

            # --- A. 强制 DWM 渲染接管整个客户区 ---
            margins = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                hwnd, ctypes.byref(margins)
            )

            # --- B. 应用亚克力样式 ---

            policy = ACCENT_POLICY()
            policy.AccentState = DWM_EC_ENABLE_ACRYLIC  # 亚克力
            policy.AccentFlags = 0
            # GradientColor = AARRGGBB (Alpha, Red, Green, Blue)
            # 0x01FFFFFF 是浅色（白色）带极低透明度，效果更自然。
            policy.GradientColor = 0x01FFFFFF

            wca_data = WINDOWCOMPOSITIONATTRIBDATA()
            wca_data.Attribute = WCA_ACCENT_POLICY
            wca_data.SizeOfData = ctypes.sizeof(policy)
            wca_data.Data = ctypes.pointer(policy)

            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, wca_data)

            # --- C. 设置深色模式（让亚克力效果更现代）---
            try:
                dark_mode = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(dark_mode), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass  # 忽略旧版系统不支持此属性的错误

        except Exception:
            # DWM API call failed (e.g., non-Windows OS, old Windows version)
            pass

    def _get_app_path(self):
        """
        Gets the full executable path and wraps it in double quotes
        for reliable registry writing.
        """
        app_path = os.path.abspath(sys.executable)

        # Critical: Wrap path in quotes to handle spaces in the file path
        return f'"{app_path}"'

    def _check_autostart(self):
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
            # Handle permission or other read errors silently or log them
            # We skip the messagebox.showerror here to avoid blocking startup
            print(f"Autostart check failed: {e}")
            return False

    def _set_autostart(self, enable: bool):
        """Sets or deletes the autostart registry entry."""
        RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "DesktopPet"
        app_path = self._get_app_path()

        if enable:
            # 1. Enable autostart
            try:
                # Open key with write permission
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    # Write key value (REG_SZ string type)
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
                return True
            except Exception:
                return False
        else:
            # 2. Disable autostart (delete key)
            try:
                # Open key with deletion permission
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
                    winreg.DeleteValue(key, APP_NAME)
                return True
            except FileNotFoundError:
                # Key value already doesn't exist, consider it successful
                return True
            except Exception as e:
                # Show error for deletion failure
                messagebox.showerror("Autostart Error", f"Failed to delete registry entry. Error: {e}", parent=self)
                return False

    def toggle_autostart(self):
        """Handles the CheckBox click: attempts to set/unset autostart."""
        is_on = self.autostart_var.get()
        success = self._set_autostart(is_on)

        if success:
            status = "enabled" if is_on else "disabled"
            messagebox.showinfo("Autostart Setting", f"Launch on Startup is successfully {status}.", parent=self)
        else:
            # If setting failed (likely permission issues), display error and revert CheckBox state
            action = "enable" if is_on else "disable"
            messagebox.showerror("Autostart Error",
                                 f"Failed to {action} autostart. Please try running the application as administrator.",
                                 parent=self)
            self.autostart_var.set(not is_on)

    def confirm_exit(self):
        """Prompts user for confirmation and initiates application exit."""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the desktop pet program?", parent=self):
            self.destroy()  # Close the settings window
            # change state to say bye
            self.pet.change_state(ByeState(self.pet))

    def close_window(self):
        """Closes the settings window and returns the pet to the Idle state if it was following."""
        self.destroy()

        if self.pet.state.__class__.__name__ == 'DisplayState':
            self.pet.change_state(IdleState(self.pet))

        import win32con
        import win32gui

        try:
            win32gui.SetWindowPos(
                self.pet.hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
        except Exception as e:
            print(f"Error resetting window Z-order: {e}")