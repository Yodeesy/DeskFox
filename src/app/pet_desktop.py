# pet_desktop.py

import pygame
import sys
import win32con
import win32gui
import queue
import time
from typing import Union, Dict
# Import created modules
import window_manager as wm
from pet_states import IdleState, TeleportState, MagicState, FishingState, UpsetState, ButterflyState
from settings_gui import SettingsWindow
from sprite_animation import load_animation, load_dragging_animations, AnimationController
from effects import DynamicEffectController
from story_manager import StoryManager
from story_display import show_story_prompt


class DesktopPet:
    """Manages the Pygame application loop, window handling, state machine, and resource loading."""

    # Constant: Easing rate for smooth window following
    FOLLOW_EASING_RATE = 0.2  # Value between 0 and 1. Smaller value means smoother/delayed following.

    def __init__(self, width, height, fps, animation_config, initial_config):
        pygame.init()

        # --- Configuration Initialization ---
        self.config = initial_config
        self.animation_config = animation_config
        self.persistent_keys = None
        self.rest_interval_ms = self.config.get("rest_interval_minutes", 60) * 60 * 1000
        self.rest_duration_ms = self.config.get("rest_duration_seconds", 30) * 1000
        self.fishing_cooldown_ms = self.config.get("fishing_cooldown_minutes", 10) * 60 * 1000
        self.upset_interval_ms = self.config.get("upset_interval_minutes", 7) * 60 * 1000
        self.angry_possibility = self.config.get("angry_possibility", 0.5)
        self.fishing_success_rate = self.config.get('fishing_success_rate', 0.50)
        self.fox_story_possibility = self.config.get('fox_story_possibility', 0.5)
        self.max_fox_story_num = self.config.get("max_fox_story_num", 7)
        self.last_read_index = self.config.get("last_read_index", 0)

        # Timer start point (in milliseconds since Pygame init)
        self.rest_timer_start_time = pygame.time.get_ticks()
        self.fishing_timer_start_time = pygame.time.get_ticks()
        self.upset_timer_start_time = pygame.time.get_ticks()
        self.angry_counter = 0
        self.havering_start_time = pygame.time.get_ticks()

        # --- Size and Performance ---
        self.width = width
        self.height = height
        self.original_width = width
        self.original_height = height
        self.display_width = 350  # Default size for settings follow mode
        self.display_height = 350
        self.head_hover_height = 49
        self.fps = fps
        self.running = True
        self.clock = pygame.time.Clock()

        # --- Web Service and Story Management ---
        self.web_service_url = self.config.get("web_service_url", "https://deskfox.deno.dev")
        self.pathname = self.config.get("pathname", "/stories")
        self.story_manager = StoryManager(self, self.web_service_url, self.pathname)

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
        start_x = self.config.get("current_x", (self.full_screen_width - self.width) // 2)
        start_y = self.config.get("current_y", (self.full_screen_height - self.height) // 2)

        # Store current window position (mutable list [x, y])
        self.current_window_pos = [start_x, start_y]
        self.position_before_display = [start_x, start_y]  # Position to return to after large mode

        # Configure layered window style
        try:
            wm.setup_layered_window(self.hwnd, self.width, self.height, start_x, start_y)
            time.sleep(0.1)
        except Exception as e:
            # Handle window configuration failure, often harmless in initial Pygame setup
            pass

        # --- Animation Loading ---
        self.all_animations = {}
        self.animation_ranges = {}
        self._load_animations()
        self.animator = AnimationController(self.all_animations, self.animation_ranges)

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
        # 队列初始化
        self._tk_queue = queue.Queue()
        # 用于存储 after() 返回的 ID，以便取消重复的轮询
        self._poller_id = None
        self.if_first_havering = True

    def _load_animations(self):
        """加载所有动画"""
        # Load Idle animation
        load_animation(self, 'idle')
        # Load Display animation
        load_animation(self, 'display', no_scaling=True)
        # Load Teleport animation
        load_animation(self, 'teleport')
        # Load Magic animation (for full screen effect)
        load_animation(self, 'magic', no_scaling=True, is_magic_type=True)
        # Load Fishing animation
        load_animation(self, 'fishing')
        # Load Bye animation
        load_animation(self, 'bye')
        # Load Upset animation
        load_animation(self, 'upset')
        # Load Angry animation
        load_animation(self, 'angry')
        # Load Butterfly animation
        load_animation(self, 'butterfly')
        # Load all Dragging options
        load_dragging_animations(self)

    # --- Queue Poller Methods ---
    def _start_queue_poller(self):
        """
        [主執行緒調用] 啟動週期性輪詢隊列的機制。
        必須在 self.tk_root 被賦值且 GUI 啟動後調用一次。
        """
        if self._poller_id:
            try:
                self.tk_root.after_cancel(self._poller_id)
            except Exception:
                pass

        # 每 100ms 檢查一次隊列
        self._poller_id = self.tk_root.after(100, self._process_queue)
        print("DEBUG: Queue poller started.", flush=True)

    def _process_queue(self):
        """
        主线程处理事件队列
        """
        # 每轮最多处理 5 个事件
        MAX_ITEMS_PER_TICK = 5

        processed = 0
        while processed < MAX_ITEMS_PER_TICK:
            try:
                item = self._tk_queue.get_nowait()
            except queue.Empty:
                break

            processed += 1
            print(f"DEBUG: Queue item: {item}", flush=True)

            # 处理钓鱼结果
            if isinstance(item, tuple) and item[0] == "story_result":
                _, is_successful, payload, story_id = item
                self.handle_fishing_result(
                    is_successful=is_successful,
                    story_data_or_error=payload,
                    story_id=story_id
                )
            else:
                print(f"WARNING: Unknown item in queue: {item}", flush=True)

        # GUI 永远不会被阻塞
        if self.tk_root and self.tk_root.winfo_exists():
            self._poller_id = self.tk_root.after(250, self._process_queue)
        else:
            print("WARNING: Tk root destroyed, stopping poller", flush=True)

    def handle_fishing_result(self, is_successful, story_data_or_error: Union[Dict, str], story_id=None):
        """
        [在主线程中被调用] 处理异步钓鱼结果。如果成功，则调用 GUI 函数展示故事。
        """
        if is_successful and story_data_or_error and story_id:
            self.update_fox_story_index()
            show_story_prompt(self.tk_root, story_data_or_error, story_id, self)

        else:
            fail_message = story_data_or_error if story_data_or_error else "网络君罢工了T-T\n漂流瓶自己跑走了..."
            show_story_prompt(self.tk_root, fail_message)


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

        # 只有在 IdleState 或 ButterflyState 之間切換
        is_hovering = self.is_mouse_over_head()

        if is_hovering and isinstance(self.state, IdleState):
            # Only update havering_start_time when havering for the first time
            if self.if_first_havering:
                self.havering_start_time = pygame.time.get_ticks()
                self.if_first_havering = False

            if self._is_hovering_ready():
                # 懸停在頭部，從 Idle 進入 Butterfly 狀態
                self.change_state(ButterflyState(self))

        elif not is_hovering and isinstance(self.state, ButterflyState):
            # 鼠標移走，從 Butterfly 退出回到 Idle 狀態
            self.change_state(IdleState(self))
            self.if_first_havering = True

        # Check the reminder timers
        self._check_rest_timer()
        self._check_fishing_timer()
        self._check_upset_timer()

    def _is_hovering_ready(self):
        """
        Checks if the hover timer has expired.
        """
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.havering_start_time

        if elapsed_time >= 1989.0604:
            return True
        return False

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
        if isinstance(self.state, IdleState) and (elapsed_time >= self.fishing_cooldown_ms):
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

    def update_fox_story_index(self):
        """
        index += 1 when the index <= the max num,
        or reset the index to zero.
        """
        if self.last_read_index + 1 >= self.max_fox_story_num:
            self.last_read_index = 0
        else:
            self.last_read_index += 1

        self.tk_root.config["last_read_index"] = self.last_read_index

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

    def is_mouse_over_head(self):
        """
        实时检测鼠标是否悬停在 Pet 窗口的头部区域
        通过检查窗口焦点和鼠标位置来判断
        """
        # 只有在小尺寸（原始宽高）时才允许悬停触发
        if self.width != self.original_width or self.height != self.original_height:
            return False
        # 1. 检查鼠标是否在窗口内（获得焦点）
        if not pygame.mouse.get_focused():
            return False
        # 2. 获取当前鼠标位置
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # 3. 检查鼠标是否在窗口内
        is_in_window = 0 <= mouse_x < self.width and 0 <= mouse_y < self.height
        # 4. 如果不在窗口内，返回 False
        if not is_in_window:
            return False
        # 5. 检查是否在头部区域
        is_in_head = mouse_y < self.head_hover_height

        return is_in_head

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
            is_exiting = self.state.__class__.__name__ == 'ByeState'
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                # 检查右键点击事件
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    # 只有在非退出状态时，才允许右键打开设置
                    if not is_exiting:
                        # Right-click: open settings window
                        self.open_settings()
                    # 如果处于 ByeState，直接忽略该事件
                    continue
                # 仅将事件传递给状态机，如果宠物不在退出中
                if not is_exiting:
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