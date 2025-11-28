# pet_states.py

import win32con
import win32gui
import pygame
import random
import window_manager as wm


class PetState:
    """Base Class for all Pet States in the state machine."""

    def __init__(self, pet_context):
        # Reference to the DesktopPet instance (context)
        self.pet = pet_context

    def enter(self):
        """Logic executed upon entering the state (initialization)."""
        pass

    def exit(self):
        """Logic executed upon exiting the state (cleanup)."""
        pass

    def handle_event(self, event):
        """Handles a single Pygame event dispatched by the main loop."""
        pass

    def handle_input(self):
        """Handles continuous input events (e.g., mouse button held, key states) and state transitions."""
        pass

    def update(self):
        """Updates state logic every frame."""
        self.pet.animator.update_frame()


# --- Concrete State Implementations ---

class IdleState(PetState):
    """Pet Idle State: Plays the standby animation, waiting for drag or automatic behavior (rest timer)."""

    def enter(self):
        # Log entry
        self.pet.animator.set_animation('idle')

    def handle_event(self, event):
        """Detects left mouse button down for dragging."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            mouse_rel_pos = pygame.mouse.get_pos()

            # Check if the click is on a non-transparent area of the sprite
            if self.pet.is_click_on_sprite(mouse_rel_pos[0], mouse_rel_pos[1]):
                # Switch to DraggingState
                self.pet.change_state(DraggingState(self.pet))

    def handle_input(self):
        pass

    def update(self):
        super().update()
        # Idle state remains here, waiting for the rest timer to trigger a TeleportState change (in DesktopPet.update)


class DraggingState(PetState):
    """Pet Dragging State: Pet is being held and moved by the mouse."""

    def enter(self):
        # Force top-most status for the window to ensure mouse capture
        win32gui.SetWindowPos(self.pet.hwnd, win32con.HWND_TOPMOST,
                              0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        # Record starting positions
        self.pet.drag_start_pos = wm.get_mouse_screen_pos()
        self.pet.drag_window_pos = (self.pet.current_window_pos[0], self.pet.current_window_pos[1])

        # 1. Select a random drag animation set
        selected_prefix = random.choice(self.pet.available_drag_prefixes)

        # Store the full animation names for the current group
        self.start_anim_name = f"{selected_prefix}_start"
        self.hold_anim_name = f"{selected_prefix}_hold"
        self.release_anim_name = f"{selected_prefix}_release"

        # 2. Start the pick-up animation (one-shot)
        self.pet.animator.set_animation(self.start_anim_name)

        # 3. Track current sub-state
        self.current_drag_stage = 'start'
        self.can_release = False  # Cannot transition to release until 'start' animation is done

        # Initialize smooth position tracking for drag physics
        if not hasattr(self.pet, 'current_smooth_pos'):
            self.pet.current_smooth_pos = [self.pet.current_window_pos[0], self.pet.current_window_pos[1]]
        # Reset smooth position to current window position for continuity
        self.pet.current_smooth_pos = [float(self.pet.current_window_pos[0]), float(self.pet.current_window_pos[1])]

    def exit(self):
        self.pet.drag_start_pos = None
        self.pet.drag_window_pos = None
        self.pet.reset_upset_timer()  # Reset upset timer

    def handle_event(self, event):
        pass

    def handle_input(self):
        """Checks for mouse button release to trigger the release animation."""
        mouse_pressed = pygame.mouse.get_pressed()[0]

        # Check for mouse release if we are not already playing the release animation
        if not mouse_pressed and self.current_drag_stage != 'release' and self.can_release:
            # Trigger release animation (one-shot, reverse playback)
            self.pet.animator.set_animation(self.release_anim_name)
            self.current_drag_stage = 'release'
            self.can_release = False

    def update(self):
        super().update()

        # 1. Check if the current animation sequence has finished
        if self.pet.animator.check_finished_and_advance():
            current_anim_name = self.pet.animator.current_sequence_name

            # Transition from 'start' to 'hold'
            if 'start' in current_anim_name:
                self.pet.animator.set_animation(self.hold_anim_name)
                self.current_drag_stage = 'hold'
                self.can_release = True

            # Transition from 'release' back to Idle, or to Angry
            elif 'release' in current_anim_name:
                if random.random() < self.pet.angry_possibility:
                    self.pet.change_state(AngryState(self.pet))
                else:
                    self.pet.change_state(IdleState(self.pet))
                return

        # 2. Update position only if held (in 'start' or 'hold' phase)
        if self.current_drag_stage == 'start' or self.current_drag_stage == 'hold':
            self._update_position()

    def _update_position(self):
        """Handles position update, boundary checking, elastic effects, and smoothing."""
        try:
            # Get current absolute mouse position
            current_mouse_pos = wm.get_mouse_screen_pos()

            # Calculate mouse movement distance
            dx = current_mouse_pos[0] - self.pet.drag_start_pos[0]
            dy = current_mouse_pos[1] - self.pet.drag_start_pos[1]

            # Calculate new window position based on drag start
            new_x = self.pet.drag_window_pos[0] + dx
            new_y = self.pet.drag_window_pos[1] + dy

            # Get screen resolution
            screen_modes = pygame.display.get_desktop_sizes()
            if screen_modes and screen_modes[0] != -1:
                screen_width, screen_height = screen_modes[0]
            else:
                screen_width = pygame.display.Info().current_w
                screen_height = pygame.display.Info().current_h

            # --- Elastic Boundary and Smoothing Logic ---

            ELASTIC_MARGIN = 64
            ELASTIC_STRENGTH = 0.6489
            SMOOTH_FACTOR = 0.397

            elastic_dx, elastic_dy = 0.0, 0.0

            # Calculate elastic offset for boundaries
            if new_x < ELASTIC_MARGIN:
                elastic_dx = (ELASTIC_MARGIN - new_x) * ELASTIC_STRENGTH
            elif new_x > screen_width - self.pet.width - ELASTIC_MARGIN:
                elastic_dx = -(new_x - (screen_width - self.pet.width - ELASTIC_MARGIN)) * ELASTIC_STRENGTH

            if new_y < ELASTIC_MARGIN:
                elastic_dy = (ELASTIC_MARGIN - new_y) * ELASTIC_STRENGTH
            elif new_y > screen_height - self.pet.height - ELASTIC_MARGIN:
                elastic_dy = -(new_y - (screen_height - self.pet.height - ELASTIC_MARGIN)) * ELASTIC_STRENGTH

            # Apply elastic offset
            new_x += elastic_dx
            new_y += elastic_dy

            # Clamp the target position strictly within the screen bounds (0 to max)
            target_x = max(0, min(new_x, screen_width - self.pet.width))
            target_y = max(0, min(new_y, screen_height - self.pet.height))

            # Apply smooth movement to the target position
            self.pet.current_smooth_pos[0] += (target_x - self.pet.current_smooth_pos[0]) * SMOOTH_FACTOR
            self.pet.current_smooth_pos[1] += (target_y - self.pet.current_smooth_pos[1]) * SMOOTH_FACTOR

            final_x = int(self.pet.current_smooth_pos[0])
            final_y = int(self.pet.current_smooth_pos[1])

            # Move window
            wm.set_window_position(self.pet.hwnd, final_x, final_y, self.pet.width, self.pet.height)

            # Update stored window position
            self.pet.current_window_pos[0] = final_x
            self.pet.current_window_pos[1] = final_y

        except Exception:
            # Safety fallback: switch back to IdleState on error (e.g., if Pygame window is missing)
            self.pet.change_state(IdleState(self.pet))


class DisplayState(PetState):
    """Pet Display State: Follows the GUI window and maintains the enlarged size."""

    def enter(self):
        # Adjust pet window size, position, and top-most status
        self.pet.set_display_mode(True)
        # Set the follow animation
        self.pet.animator.set_animation('display')

    def exit(self):
        # Restore pet window to original size and position
        self.pet.set_display_mode(False)

    def update(self):
        super().update()

        # Continuously follow the GUI window
        self.pet.update_display_follow()


class TeleportState(PetState):
    """
    First stage of rest mode: Plays teleport animation, then instantly moves and resizes
    the window to full screen center.
    """

    def enter(self):
        self.pet.angry_counter = 0  # Reset pet's angry counter
        # Set animation: one-shot 'teleport'
        self.pet.animator.set_animation('teleport')

    def update(self):
        super().update()

        # Check if the teleport animation has finished
        if self.pet.animator.check_finished_and_advance():
            # --- Critical Action: Teleport and Enlarge ---
            self.pet.teleport_and_enlarge()

            # Switch to the next stage (MagicState)
            self.pet.change_state(MagicState(self.pet))

    def exit(self):
        pass


# ---

class MagicState(PetState):
    """
    Second stage of rest mode: Performs rest duration countdown with full-screen effects.
    (All interaction is typically disabled here).
    """

    def enter(self):
        # 1. Set animation: one-shot 'magic_start' transitions to looping 'magic_keep'
        self.pet.animator.set_animation('magic_start', next_sequence='magic_keep')

        # 2. Start the full-screen dynamic effect
        self.pet.start_dynamic_effect()

        # 3. Record rest start time and duration
        self.rest_start_time = pygame.time.get_ticks()
        self.rest_duration_ms = self.pet.rest_duration_ms

    def update(self):
        super().update()

        # Continuously check for animation sequence transitions (start -> keep)
        self.pet.animator.check_finished_and_advance()

        # 1. Check if the rest duration is over
        if (pygame.time.get_ticks() - self.rest_start_time) > self.rest_duration_ms:
            # Restore window size to normal and switch back to IdleState
            self.pet.set_display_mode(False)
            self.pet.change_state(IdleState(self.pet))
            return

    def exit(self):
        # 1. Stop the full-screen dynamic effect
        self.pet.stop_dynamic_effect()

        # 2. Reset the main eye-rest timer in DesktopPet
        self.pet.reset_rest_timer()


class FishingState(PetState):
    """
    狐狸钓鱼状态。负责播放钓鱼动画、计时，并在时间结束后触发结果。
    """

    def __init__(self, pet):
        super().__init__(pet)
        # 钓鱼成功率（本地处理）
        self.success_rate = self.pet.config.get('fishing_success_rate', 0.50)

    def enter(self):
        """进入钓鱼状态：切换到钓鱼动画"""
        print("Starting one-shot fishing animation.")
        self.pet.animator.set_animation('fishing')


    def update(self):
        """在每一帧更新状态：检查动画是否播放完毕。"""
        super().update()  # 确保这一行会更新 animators，推进帧数

        # 🌟 关键：检查动画是否播放完毕 🌟
        if self.pet.animator.check_finished_and_advance():
            self.handle_fishing_finished()
            self.pet.change_state(IdleState(self.pet))

    def handle_fishing_finished(self):
        """处理动画播放完毕后的逻辑：决定成功/失败、重置冷却、切换状态。"""

        # 1. 关键：重置冷却计时器
        self.pet.reset_fishing_cooldown()

        # 2. 决定是否成功并获取故事 (与之前逻辑相同)
        is_successful = random.random() < self.success_rate
        story_content = None
        story_id_to_fetch = None

        if is_successful:
            # 假设 self.pet.story_manager 存在
            story_id_to_fetch = self.pet.story_manager.get_next_story_id()

            if story_id_to_fetch is not None:
                # 假设 fetch_story_sync() 存在
                story_content = self.pet.story_manager.fetch_story_sync(story_id_to_fetch)

            if story_content:
                self.pet.handle_fishing_result(True, story_content, story_id_to_fetch)
            else:
                self.pet.handle_fishing_result(False, "漂流瓶自己跑走了...（真的不是狐狸放跑的哇！！）")
        else:
            self.pet.handle_fishing_result(False)

class ByeState(PetState):
    """
    告别动画，用户退出程序时播放
    """
    def enter(self):
        print(f"Enter Bye State.")
        self.pet.animator.set_animation('bye')

    def update(self):
        super().update()
        if self.pet.animator.check_finished_and_advance():
            print(f"Bye State finished.")
            self.pet.state = None
            self.pet.trigger_exit()

    def exit(self):
        pass

class UpsetState(PetState):
    """
    用户在一定时间内未互动触发
    """
    def enter(self):
        print(f"Enter Upset State.")
        self._move_to_random_corner()
        self.pet.animator.set_animation('upset')

    def _move_to_random_corner(self):
        """计算并移动宠物到屏幕的四个角落之一。"""

        # 获取宠物尺寸和屏幕尺寸
        pet_w = self.pet.width
        pet_h = self.pet.height
        screen_w = self.pet.full_screen_width
        screen_h = self.pet.full_screen_height

        # 定义四个角落的目标位置 (x, y)
        # 注意：需要减去宠物自身的宽度/高度，才能让宠物的左上角位于目标点
        corners = [
            (0, 0),  # 左上角
            (screen_w - pet_w, 0),  # 右上角
            (0, screen_h - pet_h),  # 左下角
            (screen_w - pet_w, screen_h - pet_h)  # 右下角
        ]

        # 随机选择一个角落
        target_x, target_y = random.choice(corners)

        # 立即移动窗口到目标位置 (使用 DesktopPet 中已有的 Win32 移动函数)
        wm.set_window_position(
            self.pet.hwnd,
            target_x,
            target_y,
            pet_w,
            pet_h
        )

        # 更新 DesktopPet 内部存储的位置信息
        self.pet.current_window_pos[0] = target_x
        self.pet.current_window_pos[1] = target_y

    def update(self):
        super().update()

    def handle_event(self, event):
        """Detects left mouse button down for dragging."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            mouse_rel_pos = pygame.mouse.get_pos()

            # Check if the click is on a non-transparent area of the sprite
            if self.pet.is_click_on_sprite(mouse_rel_pos[0], mouse_rel_pos[1]):
                # Switch to DraggingState
                self.pet.change_state(DraggingState(self.pet))

    def exit(self):
        print(f"Exiting Upset State.")
        self.pet.reset_upset_timer()

class AngryState(PetState):
    """
    用户执行dragging后概率触发
    """
    def enter(self):
        self.pet.animator.set_animation('angry')

    def update(self):
        super().update()
        if self.pet.animator.check_finished_and_advance():
            if self.pet.angry_counter >= 10:
                self.pet.change_state(TeleportState(self.pet))
            else:
                self.pet.angry_counter += 1
                self.pet.change_state(IdleState(self.pet))

    def exit(self):
        pass