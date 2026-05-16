"""Core desktop pet — window, state machine, timers, and render loop."""

from __future__ import annotations

import queue
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import pygame
import win32con
import win32gui

import window_manager as wm
from window_manager import LayeredWindowRenderer
from effects import DynamicEffectController, MeteorEffectController
from pet_states import (
    ButterflyState,
    FishingState,
    IdleState,
    MagicState,
    TeleportState,
    UpsetState,
)
from settings_gui import SettingsWindow
from sprite_animation import (
    AnimationController,
    register_animation_metadata,
    register_dragging_metadata,
)
from story_display import show_story_prompt
from story_manager import StoryManager


class DesktopPet:
    """Manages the Pygame application loop, window, state machine, and
    resource loading.

    This is the central orchestrator that owns the layered window, loads
    all animation assets, runs the frame loop, and delegates per-state
    behavior to ``PetState`` subclasses.
    """

    # Easing factor for smooth following (0–1; smaller = smoother/delayed).
    FOLLOW_EASING_RATE: float = 0.2

    # Display-mode window dimensions.
    DISPLAY_WIDTH: int = 350
    DISPLAY_HEIGHT: int = 350

    # Height (px) of the head hover zone from the top of the window.
    HEAD_HOVER_HEIGHT: int = 49

    # Minimum alpha value for a pixel to count as "solid" for click detection.
    SPRITE_CLICK_ALPHA_MIN: int = 10

    # Mouse hover threshold in ms (easter-egg constant).
    HOVER_THRESHOLD_MS: float = 1989.0604

    # Number of raindrop particles during the magic rest effect.
    EFFECT_RAINDROP_COUNT: int = 600
    # Number of meteor particles during the magic rest effect.
    EFFECT_METEOR_COUNT: int = 60

    # Short delay after layered-window setup (seconds).
    WINDOW_SETUP_DELAY_S: float = 0.1

    # Queue-poller tuning.
    QUEUE_POLL_INTERVAL_MS: int = 50
    QUEUE_IDLE_INTERVAL_MS: int = 250
    QUEUE_MAX_TIME_MS: int = 16
    QUEUE_MAX_ITEMS_PER_TICK: int = 3

    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        animation_config: Dict[str, Any],
        initial_config: Dict[str, Any],
    ) -> None:
        """Initialize the desktop pet with display, config, and animations.

        Sets up the layered window, loads animation metadata, pre-warms the
        idle animation, and initializes timers and the tkinter event bridge.

        Args:
            width: Pet window width in pixels.
            height: Pet window height in pixels.
            fps: Target frames per second for the render loop.
            animation_config: Spritesheet metadata from animation_config.py.
            initial_config: Runtime settings loaded from disk + defaults.
        """
        pygame.init()

        # --- Configuration ---
        self.config: Dict[str, Any] = initial_config
        self.animation_config: Dict[str, Any] = animation_config
        self.persistent_keys: Optional[List[str]] = None

        self.rest_interval_ms: int = (
            self.config.get("rest_interval_minutes", 60) * 60 * 1000
        )
        self.rest_duration_ms: int = (
            self.config.get("rest_duration_seconds", 30) * 1000
        )
        self.fishing_cooldown_ms: int = (
            self.config.get("fishing_cooldown_minutes", 10) * 60 * 1000
        )
        self.upset_interval_ms: int = (
            self.config.get("upset_interval_minutes", 7) * 60 * 1000
        )
        self.angry_possibility: float = self.config.get(
            "angry_possibility", 0.5
        )
        self.fishing_success_rate: float = self.config.get(
            "fishing_success_rate", 0.50
        )
        self.fox_story_possibility: float = self.config.get(
            "fox_story_possibility", 0.5
        )
        self.max_fox_story_num: int = self.config.get(
            "max_fox_story_num", 7
        )
        self.last_read_index: int = self.config.get("last_read_index", 0)

        # --- Timers ---
        self.rest_timer_start_time: int = pygame.time.get_ticks()
        self.fishing_timer_start_time: int = pygame.time.get_ticks()
        self.upset_timer_start_time: int = pygame.time.get_ticks()
        self.angry_counter: int = 0
        self.havering_start_time: int = pygame.time.get_ticks()

        # --- Window geometry ---
        self.width: int = width
        self.height: int = height
        self.original_width: int = width
        self.original_height: int = height
        self.display_width: int = self.DISPLAY_WIDTH
        self.display_height: int = self.DISPLAY_HEIGHT
        self.head_hover_height: int = self.HEAD_HOVER_HEIGHT
        self.fps: int = fps
        self.running: bool = True
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self._renderer: LayeredWindowRenderer = LayeredWindowRenderer()

        # --- Web service / stories ---
        self.web_service_url: str = self.config.get(
            "web_service_url", "https://deskfox.deno.dev"
        )
        self.pathname: str = self.config.get("pathname", "/stories")
        self.story_manager: StoryManager = StoryManager(
            self, self.web_service_url, self.pathname
        )

        # --- Native window setup ---
        pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        self.hwnd: int = pygame.display.get_wm_info()["window"]

        screen_modes = pygame.display.get_desktop_sizes()
        if screen_modes:
            self.full_screen_width: int
            self.full_screen_height: int
            self.full_screen_width, self.full_screen_height = screen_modes[0]
        else:
            self.full_screen_width = pygame.display.Info().current_w
            self.full_screen_height = pygame.display.Info().current_h

        start_x: int = self.config.get(
            "current_x",
            (self.full_screen_width - self.width) // 2,
        )
        start_y: int = self.config.get(
            "current_y",
            (self.full_screen_height - self.height) // 2,
        )

        self.current_window_pos: List[int] = [start_x, start_y]
        self.position_before_display: List[int] = [start_x, start_y]

        try:
            wm.setup_layered_window(
                self.hwnd, self.width, self.height, start_x, start_y
            )
            time.sleep(self.WINDOW_SETUP_DELAY_S)
        except Exception:
            pass

        # --- Animations ---
        self.all_animations: Dict[str, List[pygame.Surface]] = {}
        self.animation_ranges: Dict[str, Tuple[int, int]] = {}
        self.animator: AnimationController = AnimationController(
            self.all_animations, self.animation_ranges
        )
        self._register_animation_metadata()

        # --- Runtime state ---
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.drag_window_pos: Optional[Tuple[int, int]] = None
        self.draw_surface: pygame.Surface = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA
        )

        self.state: Optional[Any] = None
        self.change_state(IdleState(self))
        self.settings_window: Optional[SettingsWindow] = None
        self.dynamic_effect: Optional[DynamicEffectController] = None
        self.tk_root: Optional[Any] = None

        self._tk_queue: queue.Queue = queue.Queue()
        self._poller_id: Optional[str] = None
        self.if_first_havering: bool = True

    # --- Animation loading ---

    def _register_animation_metadata(self) -> None:
        """Register animation metadata for all animations without loading frames.

        Frames are loaded on demand by AnimationController when the
        animation is first played.
        """
        register_animation_metadata(self, "idle")
        register_animation_metadata(self, "display", no_scaling=True)
        register_animation_metadata(self, "teleport")
        register_animation_metadata(
            self, "magic", no_scaling=True, is_magic_type=True,
        )
        register_animation_metadata(self, "fishing")
        register_animation_metadata(self, "bye")
        register_animation_metadata(self, "upset")
        register_animation_metadata(self, "angry")
        register_animation_metadata(self, "butterfly")
        register_dragging_metadata(self)

        # Pre-warm the idle animation so startup doesn't show a blank frame.
        # Other animations are lazy-loaded on first use via set_animation().
        self.animator._prewarm("idle")

    # --- Queue poller (Tkinter event bridge) ---

    def _start_queue_poller(self) -> None:
        """Start the periodic Tkinter queue poller.

        Must be called from the main thread after ``self.tk_root`` is set.
        """
        if self._poller_id:
            try:
                self.tk_root.after_cancel(self._poller_id)
            except Exception:
                pass

        self._poller_id = self.tk_root.after(
            self.QUEUE_POLL_INTERVAL_MS, self._process_queue
        )

    def _process_queue(self) -> None:
        """Process items from the thread-safe queue on the main thread.

        Handles ``story_result`` tuples from async story fetches. The
        polling interval adapts: 50ms when items are being processed,
        250ms when idle.
        """
        start_time: float = time.time()

        processed: int = 0
        while processed < self.QUEUE_MAX_ITEMS_PER_TICK:
            if (time.time() - start_time) * 1000 >= self.QUEUE_MAX_TIME_MS:
                break
            try:
                item: Any = self._tk_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "story_result":
                    _, is_successful, payload, story_id = item
                    try:
                        self.handle_fishing_result(
                            is_successful=is_successful,
                            story_data_or_error=payload,
                            story_id=story_id,
                        )
                    except Exception:
                        import traceback
                        traceback.print_exc()
                else:
                    pass
                processed += 1
            except queue.Empty:
                break

        interval: int = (
            self.QUEUE_IDLE_INTERVAL_MS if processed == 0
            else self.QUEUE_POLL_INTERVAL_MS
        )

        if self.tk_root and self.tk_root.winfo_exists():
            self._poller_id = self.tk_root.after(
                interval, self._process_queue
            )
        else:
            pass

    def handle_fishing_result(
        self,
        is_successful: bool,
        story_data_or_error: Union[Dict[str, Any], str],
        story_id: Optional[int] = None,
    ) -> None:
        """Handle the result of an async fishing story fetch.

        Called on the main thread. If successful, increments the story
        index and displays the story window; otherwise shows an error.

        Args:
            is_successful: Whether a valid story dict was fetched.
            story_data_or_error: The story dict or an error message string.
            story_id: The story index (used to open the display window).
        """
        if is_successful and story_data_or_error and story_id is not None:
            self.update_fox_story_index()
            show_story_prompt(
                self.tk_root, story_data_or_error, story_id, self
            )
        else:
            fail_message: str = (
                story_data_or_error
                if story_data_or_error
                else "The network is on strike T-T\n"
                     "The bottle drifted away on its own..."
            )
            show_story_prompt(self.tk_root, fail_message)

    # --- Effects ---

    def start_dynamic_effect(self) -> None:
        """Start a random visual effect (rain or meteor shower) at equal probability."""
        if random.random() < 0.5:
            self.dynamic_effect = DynamicEffectController(
                self.width, self.height, count=self.EFFECT_RAINDROP_COUNT,
            )
        else:
            self.dynamic_effect = MeteorEffectController(
                self.width, self.height, count=self.EFFECT_METEOR_COUNT,
            )

    def stop_dynamic_effect(self) -> None:
        """Stop and discard the active dynamic effect controller."""
        self.dynamic_effect = None

    # --- Frame update ---

    def update(self) -> None:
        """Run per-frame logic: state update, hover checks, timers."""
        self.state.update()

        is_hovering: bool = self.is_mouse_over_head()

        if is_hovering and isinstance(self.state, IdleState):
            if self.if_first_havering:
                self.havering_start_time = pygame.time.get_ticks()
                self.if_first_havering = False

            if self._is_hovering_ready():
                self.change_state(ButterflyState(self))

        elif not is_hovering and isinstance(self.state, ButterflyState):
            self.change_state(IdleState(self))
            self.if_first_havering = True

        self._check_rest_timer()
        self._check_fishing_timer()
        self._check_upset_timer()

    def _is_hovering_ready(self) -> bool:
        """Return True when the mouse has hovered long enough.

        The threshold value is a tribute/easter-egg constant.
        """
        current_time: int = pygame.time.get_ticks()
        elapsed_time: int = current_time - self.havering_start_time
        return elapsed_time >= self.HOVER_THRESHOLD_MS

    def _check_rest_timer(self) -> None:
        """Trigger TeleportState when the rest interval elapses."""
        current_time: int = pygame.time.get_ticks()
        elapsed_time: int = current_time - self.rest_timer_start_time

        if isinstance(self.state, IdleState) and (
            elapsed_time >= self.rest_interval_ms
        ):
            self.change_state(TeleportState(self))

    def _check_fishing_timer(self) -> None:
        """Trigger FishingState when the fishing cooldown elapses."""
        current_time: int = pygame.time.get_ticks()
        elapsed_time: int = current_time - self.fishing_timer_start_time

        if isinstance(self.state, IdleState) and (
            elapsed_time >= self.fishing_cooldown_ms
        ):
            self.change_state(FishingState(self))

    def _check_upset_timer(self) -> None:
        """Trigger UpsetState when the upset interval elapses."""
        current_time: int = pygame.time.get_ticks()
        elapsed_time: int = current_time - self.upset_timer_start_time

        if isinstance(self.state, IdleState) and (
            elapsed_time >= self.upset_interval_ms
        ):
            self.change_state(UpsetState(self))

    # --- Window movement ---

    def smooth_move_to_target(self, target_x: int, target_y: int) -> None:
        """Move the window toward *target* using an easing function.

        Args:
            target_x: Desired screen X position.
            target_y: Desired screen Y position.
        """
        current_x: int
        current_y: int
        current_x, current_y = self.current_window_pos

        dx: float = target_x - current_x
        dy: float = target_y - current_y

        if abs(dx) < 1 and abs(dy) < 1:
            new_x: int = target_x
            new_y: int = target_y
        else:
            move_x: float = dx * self.FOLLOW_EASING_RATE
            move_y: float = dy * self.FOLLOW_EASING_RATE
            new_x = int(current_x + move_x)
            new_y = int(current_y + move_y)

        wm.set_window_position(
            self.hwnd, new_x, new_y, self.width, self.height,
        )
        self.current_window_pos[0] = new_x
        self.current_window_pos[1] = new_y

    def update_display_follow(self) -> None:
        """Move the pet to follow the settings GUI window position."""
        gui_window: Optional[SettingsWindow] = self.settings_window

        if gui_window and gui_window.winfo_exists():
            gui_x: int = gui_window.winfo_rootx()
            gui_y: int = gui_window.winfo_rooty()
            gui_w: int = gui_window.winfo_width()
            gui_h: int = gui_window.winfo_height()

            margin: int = 10
            pet_w: int = self.width
            pet_h: int = self.height

            target_x: int = gui_x + gui_w - pet_w - margin + 50
            target_y: int = gui_y + gui_h - pet_h - margin + 50

            self.smooth_move_to_target(target_x, target_y)

    def set_display_mode(self, is_display_mode: bool) -> None:
        """Toggle between small (default) and large (display) window sizes.

        When entering display mode, the window is enlarged and made
        top-most so it stays visible above the settings GUI. On exit,
        the original size and Z-order are restored.

        Args:
            is_display_mode: True to enter enlarged mode, False to restore.
        """
        if is_display_mode:
            self.position_before_display = [
                self.current_window_pos[0],
                self.current_window_pos[1],
            ]

            target_w: int = self.display_width
            target_h: int = self.display_height

            pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
            self.draw_surface = pygame.Surface(
                (target_w, target_h), pygame.SRCALPHA
            )
            self.width = target_w
            self.height = target_h

            wm.setup_layered_window(
                self.hwnd, target_w, target_h,
                self.current_window_pos[0],
                self.current_window_pos[1],
            )

            win32gui.SetWindowPos(
                self.hwnd, win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )
        else:
            target_w = self.original_width
            target_h = self.original_height

            self.width = target_w
            self.height = target_h

            pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
            self.draw_surface = pygame.Surface(
                (target_w, target_h), pygame.SRCALPHA
            )

            target_x: int = self.position_before_display[0]
            target_y: int = self.position_before_display[1]

            wm.setup_layered_window(
                self.hwnd, target_w, target_h, target_x, target_y,
            )

            win32gui.SetWindowPos(
                self.hwnd, win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )

            self.current_window_pos[0] = target_x
            self.current_window_pos[1] = target_y

    def teleport_and_enlarge(self) -> None:
        """Instantly move the window to cover the entire screen.

        Used by the Magic rest state for the full-screen effect.
        """
        target_w: int = self.full_screen_width
        target_h: int = self.full_screen_height
        target_x: int = 0
        target_y: int = 0

        self.position_before_display = [
            self.current_window_pos[0],
            self.current_window_pos[1],
        ]

        pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
        self.draw_surface = pygame.Surface(
            (target_w, target_h), pygame.SRCALPHA
        )
        self.width = target_w
        self.height = target_h

        wm.set_window_position(
            self.hwnd, target_x, target_y, target_w, target_h,
        )
        wm.setup_layered_window(
            self.hwnd, target_w, target_h, target_x, target_y,
        )

        win32gui.SetWindowPos(
            self.hwnd, win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )

        self.current_window_pos[0] = target_x
        self.current_window_pos[1] = target_y

    # --- Timer resets ---

    def reset_rest_timer(self) -> None:
        """Reset the eye-rest interval timer to the current time."""
        self.rest_timer_start_time = pygame.time.get_ticks()

    def reset_fishing_cooldown(self) -> None:
        """Reset the fishing cooldown timer to the current time."""
        self.fishing_timer_start_time = pygame.time.get_ticks()

    def reset_upset_timer(self) -> None:
        """Reset the upset interval timer to the current time."""
        self.upset_timer_start_time = pygame.time.get_ticks()

    def update_fox_story_index(self) -> None:
        """Increment the story index, wrapping around at the max count."""
        if self.last_read_index + 1 >= self.max_fox_story_num:
            self.last_read_index = 0
        else:
            self.last_read_index += 1

        self.tk_root.config["last_read_index"] = self.last_read_index

    def update_rest_config(self, interval_ms: int, duration_ms: int) -> None:
        """Update rest reminder interval and duration from the GUI.

        Args:
            interval_ms: New rest interval in milliseconds.
            duration_ms: New rest duration in milliseconds.
        """
        self.rest_interval_ms = interval_ms
        self.rest_duration_ms = duration_ms
        self.rest_timer_start_time = pygame.time.get_ticks()

    # --- Settings window ---

    def open_settings(self) -> None:
        """Open or bring-to-front the settings window."""
        if (
            not hasattr(self, "settings_window")
            or self.settings_window is None
            or not self.settings_window.winfo_exists()
        ):
            self.settings_window = SettingsWindow(self.tk_root, self)
        else:
            self.settings_window.lift()

    # --- State management ---

    def change_state(self, new_state: Any) -> None:
        """Transition to a new state, calling exit/enter as appropriate.

        Args:
            new_state: The target ``PetState`` instance.
        """
        if self.state is not None:
            self.state.exit()

        self.state = new_state
        self.state.enter()

    # --- Input detection ---

    def is_mouse_over_head(self) -> bool:
        """Return True if the mouse cursor is over the pet's head region.

        The head region is defined as the top ``head_hover_height`` pixels
        of the window. Only active at the original (small) window size.
        """
        if self.width != self.original_width or self.height != self.original_height:
            return False

        if not pygame.mouse.get_focused():
            return False

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pygame.mouse.get_pos()
        is_in_window: bool = (
            0 <= mouse_x < self.width and 0 <= mouse_y < self.height
        )
        if not is_in_window:
            return False

        return mouse_y < self.head_hover_height

    def is_click_on_sprite(self, mouse_x: int, mouse_y: int) -> bool:
        """Check whether a mouse click lands on a non-transparent pixel.

        Args:
            mouse_x: X position relative to the pet window.
            mouse_y: Y position relative to the pet window.

        Returns:
            True if the pixel at the click position has alpha > 10.
        """
        current_frame: pygame.Surface = self.animator.get_current_frame()

        if (
            0 <= mouse_x < self.original_width
            and 0 <= mouse_y < self.original_height
        ):
            try:
                pixel_color: Tuple[int, int, int, int] = (
                    current_frame.get_at((mouse_x, mouse_y))
                )
                alpha: int = pixel_color[3]
                return alpha > self.SPRITE_CLICK_ALPHA_MIN
            except IndexError:
                return False
        return False

    # --- Render ---

    def render(self) -> None:
        """Composite the current frame and effects onto the layered window."""
        self.draw_surface.fill((0, 0, 0, 0))

        pet_frame: pygame.Surface = self.animator.get_current_frame()

        pet_x: int = (self.width - pet_frame.get_width()) // 2
        pet_y: int = (self.height - pet_frame.get_height()) // 2

        # Draw dynamic effect (rain or meteor shower) behind the pet during
        # the magic keep phase.
        if (
            isinstance(self.state, MagicState)
            and self.animator.current_sequence_name == "magic_keep"
            and self.dynamic_effect
        ):
            self.dynamic_effect.update_and_draw(self.draw_surface)

        self.draw_surface.blit(pet_frame, (pet_x, pet_y))

        self._renderer.render(
            self.hwnd, self.draw_surface,
            self.current_window_pos[0],
            self.current_window_pos[1],
        )

    def trigger_exit(self) -> None:
        """Signal the main loop and Tkinter to exit (called by ByeState)."""
        self.running = False
        if self.tk_root:
            self.tk_root.quit()

    # --- Main loop ---

    def run(self) -> None:
        """Run the main application loop.

        Alternates between processing Tkinter events, Pygame events,
        game logic updates, and rendering. Runs until ``self.running``
        is set to False.
        """

        def check_tk_root() -> None:
            """Process pending Tkinter GUI events."""
            try:
                self.tk_root.update_idletasks()
                self.tk_root.update()
            except Exception:
                import traceback
                traceback.print_exc()

        while self.running:
            check_tk_root()

            is_exiting: bool = (
                self.state.__class__.__name__ == "ByeState"
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 3
                ):
                    if not is_exiting:
                        self.open_settings()
                    continue

                if not is_exiting:
                    self.state.handle_event(event)

            if not self.running:
                break

            self.state.handle_input()
            self.update()
            self.render()
            self.clock.tick(self.fps)

        self.cleanup()

    def cleanup(self) -> None:
        """Shut down Pygame and exit the process."""
        self._renderer.destroy()
        pygame.quit()
        sys.exit()
