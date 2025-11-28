# pet_desktop.py

import pygame
import sys
import win32con
import win32gui
# Import created modules
import window_manager as wm
from pet_states import IdleState, TeleportState, MagicState, FishingState, UpsetState
from settings_gui import SettingsWindow
from sprite_animation import load_frames_from_sheet, AnimationController
from effects import DynamicEffectController


class DesktopPet:
    """Manages the Pygame application loop, window handling, state machine, and resource loading."""

    # Constant: Easing rate for smooth window following
    FOLLOW_EASING_RATE = 0.2  # Value between 0 and 1. Smaller value means smoother/delayed following.

    def __init__(self, width, height, fps, animation_config, initial_config):
        pygame.init()

        # --- Configuration Initialization ---
        self.config = initial_config
        self.rest_interval_ms = self.config.get("rest_interval_minutes", 60) * 60 * 1000
        self.rest_duration_ms = self.config.get("rest_duration_seconds", 30) * 1000
        self.fishing_cooldown_ms = self.config.get("fishing_cooldown_minutes", 60) * 60 * 1000
        self.upset_interval_ms = self.config.get("upset_interval_minutes", 7) * 60 * 1000
        self.angry_possibility = self.config.get("angry_possibility", 0.5)

        # Timer start point (in milliseconds since Pygame init)
        self.rest_timer_start_time = pygame.time.get_ticks()
        self.fishing_timer_start_time = pygame.time.get_ticks()
        self.upset_timer_start_time = pygame.time.get_ticks()
        self.angry_counter = 0

        # --- Size and Performance ---
        self.width = width
        self.height = height
        self.original_width = width
        self.original_height = height
        self.display_width = 350  # Default size for settings follow mode
        self.display_height = 350
        self.fps = fps
        self.running = True
        self.clock = pygame.time.Clock()

        # --- Window Setup ---
        pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        self.hwnd = pygame.display.get_wm_info()["window"]

        # Calculate initial position (screen center)
        # Get screen resolution
        screen_modes = pygame.display.get_desktop_sizes()
        if screen_modes and screen_modes[0] != -1:
            self.full_screen_width, self.full_screen_height = screen_modes[0]
        else:
            self.full_screen_width = pygame.display.Info().current_w
            self.full_screen_height = pygame.display.Info().current_h
        start_x = (self.full_screen_width - self.width) // 2
        start_y = (self.full_screen_height - self.height) // 2

        # Store current window position (mutable list [x, y])
        self.current_window_pos = [start_x, start_y]
        self.position_before_display = [start_x, start_y]  # Position to return to after large mode

        # Configure layered window style
        try:
            wm.setup_layered_window(self.hwnd, self.width, self.height, start_x, start_y)
        except Exception as e:
            # Handle window configuration failure, often harmless in initial Pygame setup
            pass

        # --- Animation Loading ---
        all_animations = {}
        self.animation_ranges = {}

        # Load Idle animation
        idle_config = animation_config["idle"]
        idle_frames = load_frames_from_sheet(
            idle_config["filepath"], idle_config["frame_w"], idle_config["frame_h"],
            self.width, self.height, idle_config["total_frames"]
        )
        all_animations['idle'] = idle_frames
        self.animation_ranges["idle"] = idle_config["ranges"]["idle"]

        # Load Display animation
        display_config = animation_config["display"]
        display_frames = load_frames_from_sheet(
            display_config["filepath"], display_config["frame_w"], display_config["frame_h"],
            self.width, self.height, display_config["total_frames"], no_scaling=True  # Frames not scaled at load time
        )
        all_animations['display'] = display_frames
        self.animation_ranges['display'] = display_config["ranges"]["display"]

        # Load Teleport animation
        teleport_config = animation_config["teleport"]
        teleport_frames = load_frames_from_sheet(
            teleport_config["filepath"], teleport_config["frame_w"], teleport_config["frame_h"],
            self.width, self.height, teleport_config["total_frames"]
        )
        all_animations['teleport'] = teleport_frames
        self.animation_ranges['teleport'] = teleport_config["ranges"]["teleport"]

        # Load Magic animation (for full screen effect)
        magic_config = animation_config["magic"]
        magic_frames = load_frames_from_sheet(
            magic_config["filepath"], magic_config["frame_w"], magic_config["frame_h"],
            self.width, self.height, magic_config["total_frames"], no_scaling=True  # Frames not scaled at load time
        )
        all_animations['magic'] = magic_frames
        for sub_name, ranges in magic_config["ranges"].items():
            self.animation_ranges[f"{sub_name}"] = ranges

        # Load Fishing animation
        fishing_config = animation_config["fishing"]
        fishing_frames = load_frames_from_sheet(
            fishing_config["filepath"], fishing_config["frame_w"], fishing_config["frame_h"],
            self.width, self.height, fishing_config["total_frames"]
        )
        all_animations['fishing'] = fishing_frames
        self.animation_ranges['fishing'] = fishing_config["ranges"]["fishing"]

        # Load Bye animation
        bye_config = animation_config["bye"]
        bye_frames = load_frames_from_sheet(
            bye_config["filepath"], bye_config["frame_w"], bye_config["frame_h"],
            self.width, self.height, bye_config["total_frames"]
        )
        all_animations['bye'] = bye_frames
        self.animation_ranges['bye'] = bye_config["ranges"]["bye"]

        # Load Upset animation
        upset_config = animation_config["upset"]
        upset_frames = load_frames_from_sheet(
            upset_config["filepath"], upset_config["frame_w"], upset_config["frame_h"],
            self.width, self.height, upset_config["total_frames"]
        )
        all_animations['upset'] = upset_frames
        self.animation_ranges['upset'] = upset_config["ranges"]["upset"]

        # Load Angry animation
        angry_config = animation_config["angry"]
        angry_frames = load_frames_from_sheet(
            angry_config["filepath"], angry_config["frame_w"], angry_config["frame_h"],
            self.width, self.height, angry_config["total_frames"]
        )
        all_animations['angry'] = angry_frames
        self.animation_ranges['angry'] = angry_config["ranges"]["angry"]

        # Load all Dragging options
        dragging_options = animation_config["dragging"]
        self.available_drag_prefixes = []  # e.g., ['drag_A', 'drag_B']

        for group in dragging_options:
            prefix = group["prefix"]
            self.available_drag_prefixes.append(prefix)

            drag_frames = load_frames_from_sheet(
                group["filepath"],
                group["frame_w"],
                group["frame_h"],
                self.width,
                self.height,
                group["total_frames"]
            )
            frame_key = f"{prefix}_frames"

            if drag_frames:
                all_animations[frame_key] = drag_frames

            # Store frame ranges for sub-sequences (e.g., self.animation_ranges['drag_A_start'])
            for sub_name, ranges in group["ranges"].items():
                self.animation_ranges[f"{prefix}_{sub_name}"] = ranges

        self.animator = AnimationController(all_animations, self.animation_ranges)

        # --- Runtime State and Resources ---
        self.drag_start_pos = None  # Mouse screen position at drag start
        self.drag_window_pos = None  # Window position at drag start

        # Drawing surface (used for transparent rendering)
        self.draw_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        self.state = None
        self.change_state(IdleState(self))
        self.settings_window = None
        self.dynamic_effect = None
        self.tk_root = None  # Tkinter root will be set by main.py

    def start_dynamic_effect(self):
        """Initializes and starts the dynamic effect controller (e.g., rain)."""
        # The effect controller uses the CURRENT window size (which should be full screen)
        self.dynamic_effect = DynamicEffectController(
            self.width,
            self.height,
            count=600  # Default count increased for better visibility
        )

    def stop_dynamic_effect(self):
        """Stops the dynamic effect by clearing the controller instance."""
        self.dynamic_effect = None

    def update(self):
        """
        Handles state updates, animation advancement, and eye rest timer checks.
        """
        # Update the current state logic (animation, position, transitions)
        self.state.update()

        # Check the reminder timers
        self._check_rest_timer()
        self._check_fishing_timer()
        self._check_upset_timer()

    def _check_rest_timer(self):
        """
        Checks if the rest interval has been reached and triggers the Teleport State if conditions are met.
        """
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.rest_timer_start_time

        # Conditions for triggering rest:
        # 1. Pet must be in the IdleState (avoiding interruption during interaction)
        # 2. Elapsed time must be greater than or equal to the interval
        if (self.state.__class__ is IdleState) and (elapsed_time >= self.rest_interval_ms):
            # Trigger state change: Enter Teleport state
            self.change_state(TeleportState(self))

    def _check_fishing_timer(self):
        """
        Checks if the fishing interval has been reached and triggers the Fishing State if conditions are met.
        """
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.fishing_timer_start_time

        # Conditions for triggering rest:
        # 1. Pet must be in the IdleState (avoiding interruption during interaction)
        # 2. Elapsed time must be greater than or equal to the interval
        if (self.state.__class__ is IdleState) and (elapsed_time >= self.fishing_cooldown_ms):
            # Trigger state change: Enter Fishing state
            self.change_state(FishingState(self))

    def _check_upset_timer(self):
        """
        Checks if the upset has been reached and triggers the Upset State if conditions are met.
        """
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.upset_timer_start_time
        if (self.state.__class__ is IdleState) and (elapsed_time >= self.upset_interval_ms):
            self.change_state(UpsetState(self))

    def smooth_move_to_target(self, target_x, target_y):
        """
        Moves the Pygame window smoothly towards the target position using an easing algorithm.
        """
        current_x, current_y = self.current_window_pos

        dx = target_x - current_x
        dy = target_y - current_y

        # If the distance is minimal, snap to target to prevent jitter
        if abs(dx) < 1 and abs(dy) < 1:
            new_x = target_x
            new_y = target_y
        else:
            # Calculate movement step (applying easing factor)
            move_x = dx * self.FOLLOW_EASING_RATE
            move_y = dy * self.FOLLOW_EASING_RATE

            new_x = int(current_x + move_x)
            new_y = int(current_y + move_y)

        # Update the Win32 window position
        wm.set_window_position(
            self.hwnd,
            new_x,
            new_y,
            self.width,
            self.height
        )

        # Update internal stored position
        self.current_window_pos[0] = new_x
        self.current_window_pos[1] = new_y

    def update_display_follow(self):
        """
        Called by the GUI's <Configure> event to update the pet's target position
        when following the settings window.
        """
        gui_window = self.settings_window

        if gui_window and gui_window.winfo_exists():
            # 1. Get GUI window screen position and size
            gui_x = gui_window.winfo_rootx()
            gui_y = gui_window.winfo_rooty()
            gui_w = gui_window.winfo_width()
            gui_h = gui_window.winfo_height()

            # 2. Calculate pet target position (e.g., bottom-right corner of the GUI)
            margin = 10
            pet_w = self.width
            pet_h = self.height

            # Target position calculation adjusted for aesthetics
            target_x = gui_x + gui_w - pet_w - margin + 50
            target_y = gui_y + gui_h - pet_h - margin + 50

            # 3. Execute smooth movement
            self.smooth_move_to_target(target_x, target_y)

    def set_display_mode(self, is_display_mode):
        """
        Controls the pet window's size, position, and top-most status for settings following.
        """
        if is_display_mode:
            # Enter Display Mode: Save current position, enlarge window, make top-most
            self.position_before_display = [self.current_window_pos[0], self.current_window_pos[1]]

            target_w = self.display_width
            target_h = self.display_height

            # Force Pygame to update Surface and window information
            pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
            self.draw_surface = pygame.Surface((target_w, target_h), pygame.SRCALPHA)

            # Update Pygame internal dimensions
            self.width = target_w
            self.height = target_h

            # Reconfigure layered window
            wm.setup_layered_window(self.hwnd, target_w, target_h, self.current_window_pos[0],
                                    self.current_window_pos[1])

            # Force top-most status
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        else:
            # Exit Display Mode: Restore original size and position
            target_w = self.original_width
            target_h = self.original_height

            self.width = target_w
            self.height = target_h

            pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
            self.draw_surface = pygame.Surface((target_w, target_h), pygame.SRCALPHA)

            # Restore to the position before entering display mode
            target_x = self.position_before_display[0]
            target_y = self.position_before_display[1]

            wm.setup_layered_window(self.hwnd, target_w, target_h, target_x, target_y)

            # Remove top-most status
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

            # Update internal position
            self.current_window_pos[0] = target_x
            self.current_window_pos[1] = target_y

    def teleport_and_enlarge(self):
        """
        Instantly moves the pet window to the screen center (0, 0 for full screen)
        and resizes it to the full-screen dimensions for the Magic state.
        """

        # 1. Determine target dimensions (Full Screen)
        target_w = self.full_screen_width
        target_h = self.full_screen_height

        # 2. Target position is the top-left corner
        target_x = 0
        target_y = 0

        # 3. Save current position for later restoration
        self.position_before_display = [self.current_window_pos[0], self.current_window_pos[1]]

        # 4. Update Pygame internal size and Surface
        pygame.display.set_mode((target_w, target_h), pygame.NOFRAME)
        self.draw_surface = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        self.width = target_w
        self.height = target_h

        # 5. Force Win32 window resize and reposition (Teleport)
        wm.set_window_position(
            self.hwnd,
            target_x,
            target_y,
            target_w,
            target_h
        )

        # 6. Reconfigure layered window
        wm.setup_layered_window(self.hwnd, target_w, target_h, target_x, target_y)

        # 7. Force top-most status
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        # 8. Update internal position
        self.current_window_pos[0] = target_x
        self.current_window_pos[1] = target_y

    def reset_rest_timer(self):
        """
        Resets the eye rest timer, starting the interval countdown from the current time.
        Called after the rest state exits.
        """
        self.rest_timer_start_time = pygame.time.get_ticks()

    def reset_fishing_cooldown(self):
        """
        Resets the fishing timer, starting the interval countdown from the current time.
        Called after the fishing state exits.
        """
        self.fishing_timer_start_time = pygame.time.get_ticks()

    def reset_upset_timer(self):
        """
        Resets the upset timer, starting the interval countdown from the current time.
        Called after the upset state exits.
        """
        self.upset_timer_start_time = pygame.time.get_ticks()

    def update_rest_config(self, interval_ms, duration_ms):
        """
        Called by the GUI to update the rest reminder interval and duration.

        Args:
            interval_ms (int): New rest interval in milliseconds.
            duration_ms (int): New rest duration in milliseconds.
        """

        self.rest_interval_ms = interval_ms
        self.rest_duration_ms = duration_ms

        # Immediately reset the timer to start calculating the new interval
        self.rest_timer_start_time = pygame.time.get_ticks()

    def open_settings(self):
        """Opens or activates the settings window."""
        # Avoid creating duplicate windows
        if not hasattr(self,
                       'settings_window') or self.settings_window is None or not self.settings_window.winfo_exists():
            # Pass the Tk root and the pet instance
            self.settings_window = SettingsWindow(self.tk_root, self)

        # If the window exists, bring it to the front
        else:
            self.settings_window.lift()

    def change_state(self, new_state):
        """Switches the pet to a new state."""
        if self.state is not None:
            self.state.exit()

        self.state = new_state
        self.state.enter()

    def is_click_on_sprite(self, mouse_x, mouse_y):
        """Checks if the mouse click is on a non-transparent area of the pet sprite."""
        current_frame = self.animator.get_current_frame()
        # Check if within window bounds
        # Note: Must use original_width/height as collision should only happen in the small window size
        if 0 <= mouse_x < self.original_width and 0 <= mouse_y < self.original_height:
            try:
                # Get Alpha value at the click position
                pixel_color = current_frame.get_at((mouse_x, mouse_y))
                alpha = pixel_color[3]  # Alpha channel
                return alpha > 10
            except IndexError:
                return False
        return False

    def render(self):
        """Renders the current frame and dynamic effects to the layered window."""

        # 1. Clear Surface with transparent color
        self.draw_surface.fill((0, 0, 0, 0))

        # Get the current animation frame
        pet_frame = self.animator.get_current_frame()

        # Calculate center position relative to draw_surface
        pet_x = (self.width - pet_frame.get_width()) // 2
        pet_y = (self.height - pet_frame.get_height()) // 2

        # Draw full-screen dynamic background in MagicState
        if isinstance(self.state, MagicState) and self.animator.current_sequence_name == 'magic_keep' and self.dynamic_effect:
            # 1. Draw dynamic effect over the entire draw_surface
            self.dynamic_effect.update_and_draw(self.draw_surface)

        # 2. Draw the pet sprite frame (on top of effects)
        self.draw_surface.blit(pet_frame, (pet_x, pet_y))

        # 3. Call window_manager to update the layered window
        wm.update_layered_window(
            self.hwnd,
            self.draw_surface,
            self.current_window_pos[0],
            self.current_window_pos[1]
        )

    def trigger_exit(self):
        """Triggered by ByeState"""
        self.running = False  # Set the main loop exit flag
        if self.tk_root:
            self.tk_root.quit()

    def run(self):
        """Main application loop."""

        def check_tk_root():
            """Handles events for the hidden Tkinter root and any Toplevel windows."""
            try:
                # Process Tkinter events (button clicks, window updates)
                self.tk_root.update_idletasks()
                self.tk_root.update()
            except Exception:
                # Ignore common Tkinter errors that occur when the root window is destroyed
                pass

        while self.running:
            check_tk_root()

            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    # Right-click: open settings window
                    self.open_settings()

                self.state.handle_event(event)

            if not self.running:
                break

            # --- Game Logic Update ---
            self.state.handle_input()
            self.update()

            # --- Rendering ---
            self.render()

            # Cap frame rate
            self.clock.tick(self.fps)

        self.cleanup()

    def cleanup(self):
        """Cleans up Pygame and exits the application."""
        pygame.quit()
        sys.exit()