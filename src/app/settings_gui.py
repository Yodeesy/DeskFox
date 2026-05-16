"""Settings window for configuring the desktop pet.

Provides a CustomTkinter Toplevel with rest reminder controls, autostart
toggle, and a link to the introduction site. When open, the pet enters
DisplayState and follows the window.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from tkinter import messagebox
from typing import Any, Optional

import customtkinter as ctk
import win32con
import win32gui
import winreg

from acrylic_utils import (
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    CARD_BG,
    CARD_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    apply_acrylic_effect,
    force_render_fix,
)
from config_manager import save_config
from pet_states import ByeState, DisplayState, IdleState

DANGER_RED: str = "#c0392b"
SWITCH_ON: str = "#e67e22"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class SettingsWindow(ctk.CTkToplevel):
    """A top-level settings window docked near the pet.

    Controls:
        - Rest interval / duration inputs with validation.
        - Autostart checkbox (Windows registry run key).
        - Intro site and GitHub links.
        - Exit button with confirmation.
    """

    def __init__(self, master: Any, pet_instance: Any) -> None:
        """Create the settings window with widgets and acrylic background.

        Args:
            master: The Tkinter root window.
            pet_instance: The ``DesktopPet`` instance to configure.
        """
        super().__init__(master)
        self.pet: Any = pet_instance
        self.title("DeskFox")

        self.gui_width: int = 479
        self.gui_height: int = 730
        self.geometry(f"{self.gui_width}x{self.gui_height}")

        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        initial_autostart: bool = self._check_autostart()
        self.autostart_var: ctk.BooleanVar = ctk.BooleanVar(
            value=initial_autostart
        )

        self.interval_var: ctk.StringVar = ctk.StringVar(
            value=str(master.config.get("rest_interval_minutes", 60))
        )
        self.duration_var: ctk.StringVar = ctk.StringVar(
            value=str(master.config.get("rest_duration_seconds", 30))
        )

        # Set the window background transparent *before* creating widgets so
        # CustomTkinter paints them directly onto a transparent canvas.  This
        # avoids the white-screen bug where widgets become invisible after the
        # background is changed post-render on certain GPU/driver combos.
        try:
            self.configure(fg_color="transparent")
        except Exception:
            pass

        self.bind("<Configure>", self.on_gui_configure)

        # Delay the state change until after the window is mapped.
        self.after(
            200,
            lambda: self.pet.change_state(DisplayState(self.pet)),
        )

        self.set_initial_position()
        self.create_widgets()

        # Apply Windows acrylic blur effect.
        self.after(150, lambda: apply_acrylic_effect(self))

        # Force a render pass so widgets are visible immediately.
        self.after(50, lambda: force_render_fix(self))

    # --- Geometry ---

    def on_gui_configure(self, event: Any) -> None:
        """Handle GUI window movement and constrain within screen bounds.

        When the user drags the settings window, the pet follows via
        ``update_display_follow``.
        """
        if event.widget != self:
            return

        new_x_proposed: int = event.x
        new_y_proposed: int = event.y

        screen_w: int = self.pet.full_screen_width
        screen_h: int = self.pet.full_screen_height
        win_w: int = self.gui_width
        win_h: int = self.gui_height

        max_x: int = screen_w - win_w
        max_y: int = screen_h - win_h

        new_x_constrained: int = max(0, min(new_x_proposed, max_x))
        new_y_constrained: int = max(0, min(new_y_proposed, max_y))

        if (
            new_x_proposed != new_x_constrained
            or new_y_proposed != new_y_constrained
        ):
            self.wm_geometry(
                f"+{int(new_x_constrained)}+{int(new_y_constrained)}"
            )
            return

        if self.pet.state.__class__.__name__ == "DisplayState":
            self.pet.update_display_follow()

    def set_initial_position(self) -> None:
        """Place the settings window next to the pet (preferring right side)."""
        self.update_idletasks()

        pet_x: int = self.pet.current_window_pos[0]
        pet_y: int = self.pet.current_window_pos[1]
        pet_w: int = self.pet.width

        screen_w: int = self.pet.full_screen_width
        screen_h: int = self.pet.full_screen_height

        gap: int = 10
        target_x_right: int = pet_x + pet_w + gap

        if target_x_right + self.gui_width < screen_w:
            start_x: int = target_x_right
        else:
            target_x_left: int = pet_x - self.gui_width - gap
            if target_x_left >= 0:
                start_x = target_x_left
            else:
                start_x = pet_x + (pet_w // 2) - (self.gui_width // 2)

        start_y: int = pet_y
        if start_y + self.gui_height > screen_h:
            start_y = screen_h - self.gui_height
        start_y = max(0, start_y)

        self.wm_geometry(f"+{int(start_x)}+{int(start_y)}")

    # --- Widgets ---

    def create_widgets(self) -> None:
        """Build the card-based settings UI."""
        # --- Header bar ---
        header_frame: ctk.CTkFrame = ctk.CTkFrame(
            self, fg_color="transparent",
        )
        header_frame.pack(fill="x", padx=16, pady=(16, 4))

        title_label: ctk.CTkLabel = ctk.CTkLabel(
            header_frame,
            text="🦊 DeskFox",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        title_label.pack(side="left")

        version_label: ctk.CTkLabel = ctk.CTkLabel(
            header_frame,
            text="v1.2.0",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        )
        version_label.pack(side="right", pady=(6, 0))

        # Separator.
        sep: ctk.CTkFrame = ctk.CTkFrame(
            self, height=1, fg_color=CARD_BORDER,
        )
        sep.pack(fill="x", padx=16, pady=(4, 8))

        # --- Links card ---
        links_card: ctk.CTkFrame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=CARD_BG,
            border_width=1, border_color=CARD_BORDER,
        )
        links_card.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            links_card,
            text="🔗 Links",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=14, pady=(12, 6))

        links_row: ctk.CTkFrame = ctk.CTkFrame(
            links_card, fg_color="transparent",
        )
        links_row.pack(fill="x", padx=14, pady=(0, 12))

        intro_btn: ctk.CTkButton = ctk.CTkButton(
            links_row,
            text="Intro Site",
            command=self.open_intro_website,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            width=100,
            height=32,
        )
        intro_btn.pack(side="left", padx=(0, 10))
        intro_btn.configure(cursor="hand2")

        github_link: ctk.CTkLabel = ctk.CTkLabel(
            links_row,
            text="GitHub →",
            text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(underline=True, size=13),
        )
        github_link.pack(side="left", padx=(4, 0))
        github_link.bind("<Button-1>", self.open_github_link)
        github_link.configure(cursor="hand2")

        # --- General card ---
        general_card: ctk.CTkFrame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=CARD_BG,
            border_width=1, border_color=CARD_BORDER,
        )
        general_card.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            general_card,
            text="⚙️ General",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=14, pady=(12, 6))

        autostart_row: ctk.CTkFrame = ctk.CTkFrame(
            general_card, fg_color="transparent",
        )
        autostart_row.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            autostart_row,
            text="Launch on Startup",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        autostart_switch: ctk.CTkSwitch = ctk.CTkSwitch(
            autostart_row,
            text="",
            variable=self.autostart_var,
            command=self.toggle_autostart,
            progress_color=SWITCH_ON,
            button_color=TEXT_PRIMARY,
            button_hover_color=ACCENT_ORANGE,
            width=48,
        )
        autostart_switch.pack(side="right")

        # --- Eye Rest card ---
        rest_card: ctk.CTkFrame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=CARD_BG,
            border_width=1, border_color=CARD_BORDER,
        )
        rest_card.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            rest_card,
            text="👁️ Eye Rest Reminder",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=14, pady=(12, 10))

        # Interval row.
        interval_row: ctk.CTkFrame = ctk.CTkFrame(
            rest_card, fg_color="transparent",
        )
        interval_row.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            interval_row,
            text="Rest Interval",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        interval_suffix: ctk.CTkLabel = ctk.CTkLabel(
            interval_row,
            text="min",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        )
        interval_suffix.pack(side="right", padx=(0, 4))

        interval_entry: ctk.CTkEntry = ctk.CTkEntry(
            interval_row,
            width=60,
            textvariable=self.interval_var,
            justify="center",
        )
        interval_entry.pack(side="right", padx=(0, 6))

        # Duration row.
        duration_row: ctk.CTkFrame = ctk.CTkFrame(
            rest_card, fg_color="transparent",
        )
        duration_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            duration_row,
            text="Rest Duration",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        duration_suffix: ctk.CTkLabel = ctk.CTkLabel(
            duration_row,
            text="sec",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        )
        duration_suffix.pack(side="right", padx=(0, 4))

        duration_entry: ctk.CTkEntry = ctk.CTkEntry(
            duration_row,
            width=60,
            textvariable=self.duration_var,
            justify="center",
        )
        duration_entry.pack(side="right", padx=(0, 6))

        save_btn: ctk.CTkButton = ctk.CTkButton(
            rest_card,
            text="💾 Save Settings",
            command=self.save_rest_settings,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            height=36,
        )
        save_btn.pack(fill="x", padx=14, pady=(0, 14))

        # --- Exit card ---
        exit_card: ctk.CTkFrame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=CARD_BG,
            border_width=1, border_color=CARD_BORDER,
        )
        exit_card.pack(fill="x", padx=12, pady=(0, 12))

        exit_btn: ctk.CTkButton = ctk.CTkButton(
            exit_card,
            text="👋 Exit DeskFox",
            command=self.confirm_exit,
            fg_color="transparent",
            hover_color=("gray25", "gray20"),
            text_color=DANGER_RED,
            text_color_disabled=DANGER_RED,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            height=36,
            border_width=1,
            border_color=DANGER_RED,
        )
        exit_btn.pack(fill="x", padx=14, pady=14)

        # Spacer — fills remaining height so content stays above the display-mode fox.
        # Window is 730 px tall; fox covers the bottom ~310 px (y=420..730).
        spacer: ctk.CTkFrame = ctk.CTkFrame(
            self, fg_color="transparent",
        )
        spacer.pack(fill="both", expand=True)

    # --- Actions ---

    def save_rest_settings(self) -> None:
        """Validate and persist the eye-rest reminder settings."""
        try:
            interval_str: str = self.interval_var.get().strip()
            duration_str: str = self.duration_var.get().strip()

            if not interval_str or not duration_str:
                raise ValueError("Interval and duration cannot be empty.")

            try:
                interval: int = int(interval_str)
                duration: int = int(duration_str)
            except ValueError:
                raise ValueError("Input values must be positive integers.")

            MIN_INTERVAL: int = 30
            if not (MIN_INTERVAL <= interval):
                raise ValueError(
                    f"Rest interval must be at least {MIN_INTERVAL} minutes."
                )

            MIN_DURATION: int = 10
            MAX_DURATION: int = 60
            if not (MIN_DURATION <= duration <= MAX_DURATION):
                raise ValueError(
                    f"Rest duration must be between {MIN_DURATION} and "
                    f"{MAX_DURATION} seconds."
                )

            self.master.config["rest_interval_minutes"] = interval
            self.master.config["rest_duration_seconds"] = duration

            self.pet.update_rest_config(
                interval * 60 * 1000, duration * 1000
            )

            save_config(self.master.config, self.pet.persistent_keys)

            messagebox.showinfo(
                "Settings Saved",
                "Eye rest reminder settings have been saved!",
                parent=self,
            )

        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self)

        except Exception as e:
            messagebox.showerror(
                "Error", f"An unexpected error occurred: {e}", parent=self
            )

    def open_intro_website(self) -> None:
        """Open the DeskFox introduction site in the default browser."""
        webbrowser.open_new_tab("https://deskfox.deno.dev")

    def open_github_link(self, event: Any = None) -> None:
        """Open the GitHub repository in the default browser."""
        webbrowser.open_new_tab("https://github.com/Yodeesy/DeskFox.git")

    # --- Autostart ---

    def _get_app_path(self) -> str:
        """Return the executable path wrapped in double quotes.

        Required for reliable registry value storage when the path
        contains spaces.
        """
        app_path: str = os.path.abspath(sys.executable)
        return f'"{app_path}"'

    def _check_autostart(self) -> bool:
        """Check whether the autostart registry key exists.

        Returns:
            True if the ``DesktopPet`` value is present in the
            ``HKCU\\...\\Run`` registry key.
        """
        RUN_KEY: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME: str = "DesktopPet"

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
            ) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _set_autostart(self, enable: bool) -> bool:
        """Add or remove the autostart registry entry.

        Args:
            enable: If True, create the registry value; if False, delete it.

        Returns:
            True on success, False on failure.
        """
        RUN_KEY: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME: str = "DesktopPet"
        app_path: str = self._get_app_path()

        if enable:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    winreg.SetValueEx(
                        key, APP_NAME, 0, winreg.REG_SZ, app_path
                    )
                return True
            except Exception:
                return False
        else:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                    winreg.KEY_ALL_ACCESS,
                ) as key:
                    winreg.DeleteValue(key, APP_NAME)
                return True
            except FileNotFoundError:
                return True
            except Exception as e:
                messagebox.showerror(
                    "Autostart Error",
                    f"Failed to delete registry entry. Error: {e}",
                    parent=self,
                )
                return False

    def toggle_autostart(self) -> None:
        """Handle the autostart checkbox toggle."""
        is_on: bool = self.autostart_var.get()
        success: bool = self._set_autostart(is_on)

        if success:
            status: str = "enabled" if is_on else "disabled"
            messagebox.showinfo(
                "Autostart Setting",
                f"Launch on Startup is successfully {status}.",
                parent=self,
            )
        else:
            action: str = "enable" if is_on else "disable"
            messagebox.showerror(
                "Autostart Error",
                f"Failed to {action} autostart. "
                f"Please try running the application as administrator.",
                parent=self,
            )
            self.autostart_var.set(not is_on)

    # --- Window lifecycle ---

    def confirm_exit(self) -> None:
        """Prompt for confirmation and initiate application exit."""
        if messagebox.askyesno(
            "Confirm Exit",
            "Are you sure you want to exit the desktop pet program?",
            parent=self,
        ):
            self.destroy()
            self.pet.change_state(ByeState(self.pet))

    def close_window(self) -> None:
        """Close the settings window and restore pet to IdleState."""
        self.destroy()

        if self.pet.state.__class__.__name__ == "DisplayState":
            self.pet.change_state(IdleState(self.pet))

        try:
            win32gui.SetWindowPos(
                self.pet.hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )
        except Exception:
            pass

