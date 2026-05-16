"""Story display window shown after a successful fishing attempt."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Dict, Optional, Union

import customtkinter as ctk

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

PARCHMENT_BG: tuple[str, str] = ("#faf8f5", "#2a2520")
PARCHMENT_TEXT: tuple[str, str] = ("#3e3028", "#d4c8bc")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class StoryDisplayWindow(ctk.CTkToplevel):
    """A temporary popup displaying a retrieved story in parchment style.

    This window is independent of the SettingsWindow and appears after
    the user confirms they want to open a fished-up message bottle.
    """

    def __init__(
        self,
        master: Any,
        story: Dict[str, str],
        story_id: int,
        pet_instance: Any,
    ) -> None:
        """Create the story display window with card-based layout.

        Args:
            master: The Tkinter root window.
            story: Dictionary with ``title``, ``author``, and ``content`` keys.
            story_id: The numeric story index (shown as a badge).
            pet_instance: The ``DesktopPet`` instance.
        """
        super().__init__(master)

        self.pet: Any = pet_instance
        self.story_title: str = story.get("title", "Untitled Parchment")
        self.story_author: str = story.get("author", "Anonymous Traveler")
        self.story_content: str = story.get(
            "content", "Content washed away by the sea."
        )
        self.story_id: int = story_id

        self.title("Message Bottle")
        self.gui_width: int = 600
        self.gui_height: int = 750
        self.geometry(f"{self.gui_width}x{self.gui_height}")
        self.minsize(500, 400)
        self.attributes("-topmost", True)
        self.transient(master)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Transparent background must be set BEFORE widget creation to avoid
        # the white-screen bug on certain GPU/driver combinations.
        try:
            self.configure(fg_color="transparent")
        except Exception:
            pass

        self.set_initial_position()
        self.create_widgets()

        self.after(150, lambda: apply_acrylic_effect(self))
        self.after(50, lambda: force_render_fix(self))

    # --- Geometry ---

    def set_initial_position(self) -> None:
        """Center the window on the screen."""
        self.update_idletasks()
        screen_w: int = self.pet.full_screen_width
        screen_h: int = self.pet.full_screen_height

        start_x = (screen_w // 2) - (self.gui_width // 2)
        start_y = (screen_h // 2) - (self.gui_height // 2)

        self.wm_geometry(f"+{int(start_x)}+{int(start_y)}")

    # --- Widgets ---

    def create_widgets(self) -> None:
        """Build the card-based story UI with header, content, and close."""
        # --- Header bar ---
        header_frame: ctk.CTkFrame = ctk.CTkFrame(
            self, fg_color="transparent",
        )
        header_frame.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            header_frame,
            text="📜 Message Bottle",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Story ID badge pill.
        badge: ctk.CTkFrame = ctk.CTkFrame(
            header_frame,
            corner_radius=10,
            fg_color=ACCENT_ORANGE,
        )
        badge.pack(side="right", pady=(4, 0))

        ctk.CTkLabel(
            badge,
            text=f"#{self.story_id}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
        ).pack(padx=10, pady=2)

        # --- Separator ---
        sep: ctk.CTkFrame = ctk.CTkFrame(
            self, height=1, fg_color=CARD_BORDER,
        )
        sep.pack(fill="x", padx=16, pady=(4, 8))

        # --- Content card ---
        card: ctk.CTkFrame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=CARD_BG,
            border_width=1, border_color=CARD_BORDER,
        )
        card.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        card.grid_rowconfigure(3, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=self.story_title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
            wraplength=540,
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            card,
            text=f"by {self.story_author}",
            font=ctk.CTkFont(size=13, slant="italic"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # Card-internal separator.
        card_sep: ctk.CTkFrame = ctk.CTkFrame(
            card, height=1, fg_color=CARD_BORDER,
        )
        card_sep.pack(fill="x", padx=16, pady=(0, 8))

        textbox: ctk.CTkTextbox = ctk.CTkTextbox(
            card,
            wrap="word",
            font=ctk.CTkFont(size=14),
            text_color=PARCHMENT_TEXT,
            fg_color=PARCHMENT_BG,
            border_width=0,
            corner_radius=8,
        )
        textbox.insert("1.0", self.story_content)
        textbox.configure(state="disabled")
        textbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # --- Close button ---
        close_button: ctk.CTkButton = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            fg_color=ACCENT_ORANGE,
            hover_color=ACCENT_ORANGE_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            height=36,
        )
        close_button.pack(fill="x", padx=12, pady=(0, 14))
        close_button.configure(cursor="hand2")

        self.lift()
        self.focus_force()

def show_story_prompt(
    master: Any,
    content: Union[str, Dict[str, Any]],
    story_id: Optional[int] = None,
    pet_instance: Optional[Any] = None,
) -> Optional[StoryDisplayWindow]:
    """Display a confirmation dialog before opening a story window.

    If the fetch was successful (``story_id`` is set), the user is asked
    whether to open the bottle. Otherwise a simple error/info message is
    shown.

    The master window is temporarily made top-most during the dialog to
    ensure it is visible above the pet window, then restored afterward.

    Args:
        master: The Tkinter root window.
        content: Either a story dict with ``title``/``author``/``content``
            keys, or an error message string.
        story_id: The story index if the fetch succeeded, or None on failure.
        pet_instance: The ``DesktopPet`` instance for saving config.

    Returns:
        A ``StoryDisplayWindow`` if the user confirms, or None otherwise.
    """
    try:
        master.attributes("-topmost", True)
    except Exception:
        pass

    try:
        if story_id:
            if messagebox.askyesno(
                "🍾 Got one!",
                "A lost traveler — the fox reeled in a message bottle!\n"
                "Would you like to open it?",
                parent=master,
            ):
                save_config(master.config, pet_instance.persistent_keys)
                return StoryDisplayWindow(
                    master, content, story_id, pet_instance
                )
        else:
            messagebox.showinfo(
                "Something sad happened...", content, parent=master
            )
    finally:
        try:
            master.attributes("-topmost", False)
        except Exception:
            pass

    return None
