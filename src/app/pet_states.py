"""State machine implementations for all pet behaviors.

Each concrete state encapsulates the animation, input handling, and
transition logic for a specific pet activity (idle, dragging, fishing,
resting, etc.). States receive a reference to the ``DesktopPet`` context
and interact with it through a common interface.
"""

from __future__ import annotations

import random
from typing import Any, Optional, Tuple

import pygame
import win32con
import win32gui

import window_manager as wm
from config_manager import save_config


class PetState:
    """Base class for all states in the pet state machine."""

    def __init__(self, pet_context: Any) -> None:
        """Initialize state with a reference to the DesktopPet context.

        Args:
            pet_context: The ``DesktopPet`` instance that owns this state.
        """
        self.pet: Any = pet_context

    def enter(self) -> None:
        """Called once when this state becomes active."""

    def exit(self) -> None:
        """Called once when this state is about to be replaced."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle a single Pygame event dispatched by the main loop.

        Args:
            event: A ``pygame.event.Event`` object.
        """

    def handle_input(self) -> None:
        """Handle continuous input (held keys/buttons) and transitions."""

    def update(self) -> None:
        """Advance state logic every frame."""
        self.pet.animator.update_frame()


# --- Concrete state implementations ---


class IdleState(PetState):
    """Default waiting state — plays the idle animation."""

    def enter(self) -> None:
        self.pet.animator.set_animation("idle")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Left-click on the sprite transitions to DraggingState.

        Args:
            event: The Pygame event to handle.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_rel_pos: Tuple[int, int] = pygame.mouse.get_pos()
            if self.pet.is_click_on_sprite(
                mouse_rel_pos[0], mouse_rel_pos[1]
            ):
                self.pet.change_state(DraggingState(self.pet))

    def handle_input(self) -> None:
        pass

    def update(self) -> None:
        """Advance the idle animation.

        Timer-based transitions (Teleport, Fishing, Upset) are checked
        by ``DesktopPet.update()`` callbacks.
        """
        super().update()


class DraggingState(PetState):
    """Pet is being held and moved by the mouse.

    Supports elastic edge resistance and smooth following physics. Plays
    a three-stage animation: start → hold → release. On release, randomly
    transitions to IdleState or AngryState.
    """

    # Elastic-boundary tuning constants.
    ELASTIC_MARGIN: int = 64          # px from screen edge where resistance begins
    ELASTIC_STRENGTH: float = 0.6489  # resistance multiplier
    SMOOTH_FACTOR: float = 0.397      # lerp factor for smooth following

    def enter(self) -> None:
        """Set up drag state: capture mouse offset, pick a drag animation
        variant, and ensure topmost z-order for smooth interaction."""
        win32gui.SetWindowPos(
            self.pet.hwnd, win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )

        self.pet.drag_start_pos = wm.get_mouse_screen_pos()
        self.pet.drag_window_pos = (
            self.pet.current_window_pos[0],
            self.pet.current_window_pos[1],
        )

        selected_prefix: str = random.choice(
            self.pet.available_drag_prefixes
        )
        self.start_anim_name: str = f"{selected_prefix}_start"
        self.hold_anim_name: str = f"{selected_prefix}_hold"
        self.release_anim_name: str = f"{selected_prefix}_release"

        self.pet.animator.set_animation(self.start_anim_name)

        self.current_drag_stage: str = "start"
        self.can_release: bool = False

        if not hasattr(self.pet, "current_smooth_pos"):
            self.pet.current_smooth_pos = [
                self.pet.current_window_pos[0],
                self.pet.current_window_pos[1],
            ]
        self.pet.current_smooth_pos = [
            float(self.pet.current_window_pos[0]),
            float(self.pet.current_window_pos[1]),
        ]

    def exit(self) -> None:
        """Clean up drag state and persist the final window position."""
        self.pet.drag_start_pos = None
        self.pet.drag_window_pos = None
        self.pet.reset_upset_timer()
        save_config(self.pet.tk_root.config, self.pet.persistent_keys)

    def handle_event(self, event: pygame.event.Event) -> None:
        """All events during drag are handled by ``handle_input`` instead."""
        pass

    def handle_input(self) -> None:
        """Check for mouse release to trigger the release animation."""
        mouse_pressed: bool = pygame.mouse.get_pressed()[0]

        if (
            not mouse_pressed
            and self.current_drag_stage != "release"
            and self.can_release
        ):
            self.pet.animator.set_animation(self.release_anim_name)
            self.current_drag_stage = "release"
            self.can_release = False

    def update(self) -> None:
        """Advance the drag animation and update window position.

        Manages the three-stage sequence (start → hold → release), then
        transitions to IdleState or AngryState when release completes.
        """
        super().update()

        if self.pet.animator.check_finished_and_advance():
            current_anim_name: str = self.pet.animator.current_sequence_name

            if "start" in current_anim_name:
                self.pet.animator.set_animation(self.hold_anim_name)
                self.current_drag_stage = "hold"
                self.can_release = True

            elif "release" in current_anim_name:
                if random.random() < self.pet.angry_possibility:
                    self.pet.change_state(AngryState(self.pet))
                else:
                    self.pet.change_state(IdleState(self.pet))
                return

        if self.current_drag_stage in ("start", "hold"):
            self._update_position()

    def _update_position(self) -> None:
        """Apply elastic boundary logic and smooth the window position."""
        try:
            current_mouse_pos: Tuple[int, int] = wm.get_mouse_screen_pos()
            dx: int = current_mouse_pos[0] - self.pet.drag_start_pos[0]
            dy: int = current_mouse_pos[1] - self.pet.drag_start_pos[1]

            new_x: float = self.pet.drag_window_pos[0] + dx
            new_y: float = self.pet.drag_window_pos[1] + dy

            screen_modes = pygame.display.get_desktop_sizes()
            if screen_modes:
                screen_width: int
                screen_height: int
                screen_width, screen_height = screen_modes[0]
            else:
                screen_width = pygame.display.Info().current_w
                screen_height = pygame.display.Info().current_h

            margin: int = self.ELASTIC_MARGIN

            # Compute elastic offset near screen edges.
            elastic_dx: float = 0.0
            elastic_dy: float = 0.0

            if new_x < margin:
                elastic_dx = (margin - new_x) * self.ELASTIC_STRENGTH
            elif new_x > screen_width - self.pet.width - margin:
                elastic_dx = -(
                    new_x - (screen_width - self.pet.width - margin)
                ) * self.ELASTIC_STRENGTH

            if new_y < margin:
                elastic_dy = (margin - new_y) * self.ELASTIC_STRENGTH
            elif new_y > screen_height - self.pet.height - margin:
                elastic_dy = -(
                    new_y - (screen_height - self.pet.height - margin)
                ) * self.ELASTIC_STRENGTH

            new_x += elastic_dx
            new_y += elastic_dy

            # Clamp to screen.
            target_x: float = max(
                0, min(new_x, screen_width - self.pet.width)
            )
            target_y: float = max(
                0, min(new_y, screen_height - self.pet.height)
            )

            # Smooth interpolation.
            self.pet.current_smooth_pos[0] += (
                target_x - self.pet.current_smooth_pos[0]
            ) * self.SMOOTH_FACTOR
            self.pet.current_smooth_pos[1] += (
                target_y - self.pet.current_smooth_pos[1]
            ) * self.SMOOTH_FACTOR

            final_x: int = int(self.pet.current_smooth_pos[0])
            final_y: int = int(self.pet.current_smooth_pos[1])

            wm.set_window_position(
                self.pet.hwnd, final_x, final_y,
                self.pet.width, self.pet.height,
            )

            self.pet.current_window_pos[0] = final_x
            self.pet.current_window_pos[1] = final_y

            self.pet.tk_root.config["current_x"] = final_x
            self.pet.tk_root.config["current_y"] = final_y

        except Exception:
            self.pet.change_state(IdleState(self.pet))


class DisplayState(PetState):
    """Pet follows the Settings GUI window at its enlarged display size."""

    def enter(self) -> None:
        """Switch to display mode and start the display animation."""
        self.pet.set_display_mode(True)
        self.pet.animator.set_animation("display")

    def exit(self) -> None:
        """Restore normal size and window style."""
        self.pet.set_display_mode(False)

    def update(self) -> None:
        """Follow the settings window position."""
        super().update()
        self.pet.update_display_follow()


class TeleportState(PetState):
    """First stage of rest mode — plays teleport animation then goes full-screen."""

    def enter(self) -> None:
        """Reset angry counter and start the teleport animation."""
        self.pet.angry_counter = 0
        self.pet.animator.set_animation("teleport")

    def update(self) -> None:
        """Transition to MagicState when the teleport animation finishes."""
        super().update()
        if self.pet.animator.check_finished_and_advance():
            self.pet.teleport_and_enlarge()
            self.pet.change_state(MagicState(self.pet))


class MagicState(PetState):
    """Second stage of rest mode — full-screen effects with countdown."""

    def enter(self) -> None:
        self.pet.animator.set_animation(
            "magic_start", next_sequence="magic_keep"
        )
        self.pet.start_dynamic_effect()
        self.rest_start_time: int = pygame.time.get_ticks()
        self.rest_duration_ms: int = self.pet.rest_duration_ms

    def update(self) -> None:
        super().update()
        self.pet.animator.check_finished_and_advance()

        elapsed: int = pygame.time.get_ticks() - self.rest_start_time
        if elapsed > self.rest_duration_ms:
            self.pet.set_display_mode(False)
            self.pet.change_state(IdleState(self.pet))

    def exit(self) -> None:
        self.pet.stop_dynamic_effect()
        self.pet.reset_rest_timer()


class FishingState(PetState):
    """Plays the fishing animation and triggers an async story fetch on completion."""

    def __init__(self, pet: Any) -> None:
        """Capture the fishing success parameters from the pet config.

        Args:
            pet: The ``DesktopPet`` instance.
        """
        super().__init__(pet)
        self.success_rate: float = self.pet.fishing_success_rate
        self.fox_story_possibility: float = self.pet.fox_story_possibility

    def enter(self) -> None:
        self.pet.animator.set_animation("fishing")

    def update(self) -> None:
        super().update()

        if self.pet.animator.check_finished_and_advance():
            if not hasattr(self, "_fetch_started"):
                self.handle_fishing_finished()
                self._fetch_started: bool = True
            self.pet.change_state(IdleState(self.pet))

    def handle_fishing_finished(self) -> None:
        """Decide success/failure and initiate async story fetch if successful."""
        self.pet.reset_fishing_cooldown()

        is_successful: bool = random.random() < self.success_rate
        story_content: Optional[str] = None
        story_id_to_fetch: Optional[int] = None

        if is_successful:
            if random.random() < self.fox_story_possibility:
                story_id_to_fetch = self.pet.story_manager.get_next_story_id()
            else:
                low: int
                high: int
                low, high = self.pet.story_manager.NON_FOX_STORY_RANGE
                story_id_to_fetch = random.choice(range(low, high))

            if story_id_to_fetch is not None:
                self.pet.story_manager.fetch_story_async(story_id_to_fetch)
            else:
                self.pet.handle_fishing_result(
                    False,
                    "The bottle drifted away... (really, the fox didn't let it go!!)",
                )
        else:
            self.pet.handle_fishing_result(
                False, "The fox caught nothing T-T"
            )


class ByeState(PetState):
    """Farewell animation played when the user exits the application."""

    def enter(self) -> None:
        """Start the farewell animation."""
        self.pet.animator.set_animation("bye")

    def update(self) -> None:
        """Trigger application exit when the farewell animation finishes."""
        super().update()
        if self.pet.animator.check_finished_and_advance():
            self.pet.state = None
            self.pet.trigger_exit()


class UpsetState(PetState):
    """Triggered when the user has not interacted for a set interval."""

    def enter(self) -> None:
        self._move_to_random_corner()
        self.pet.animator.set_animation("upset")

    def _move_to_random_corner(self) -> None:
        """Teleport the pet to one of the four screen corners."""
        pet_w: int = self.pet.width
        pet_h: int = self.pet.height
        screen_w: int = self.pet.full_screen_width
        screen_h: int = self.pet.full_screen_height

        corners: list[Tuple[int, int]] = [
            (0, 0),
            (screen_w - pet_w, 0),
            (0, screen_h - pet_h),
            (screen_w - pet_w, screen_h - pet_h),
        ]
        target_x: int
        target_y: int
        target_x, target_y = random.choice(corners)

        wm.set_window_position(
            self.pet.hwnd, target_x, target_y, pet_w, pet_h
        )
        self.pet.current_window_pos[0] = target_x
        self.pet.current_window_pos[1] = target_y

    def update(self) -> None:
        super().update()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Left-click transitions to DraggingState.

        Args:
            event: The Pygame event to handle.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_rel_pos: Tuple[int, int] = pygame.mouse.get_pos()
            if self.pet.is_click_on_sprite(
                mouse_rel_pos[0], mouse_rel_pos[1]
            ):
                self.pet.change_state(DraggingState(self.pet))

    def exit(self) -> None:
        """Reset the upset timer on state exit."""
        self.pet.reset_upset_timer()


class AngryState(PetState):
    """Brief angry animation; may escalate to TeleportState after N repeats."""

    MAX_ANGRY_COUNT: int = 10

    def enter(self) -> None:
        """Play the angry one-shot animation."""
        self.pet.animator.set_animation("angry")

    def update(self) -> None:
        """Escalate to TeleportState if angry threshold reached, else go idle."""
        super().update()
        if self.pet.animator.check_finished_and_advance():
            if self.pet.angry_counter >= self.MAX_ANGRY_COUNT:
                self.pet.change_state(TeleportState(self.pet))
            else:
                self.pet.angry_counter += 1
                self.pet.change_state(IdleState(self.pet))


class ButterflyState(PetState):
    """Triggered when the mouse hovers over the pet's head area."""

    def enter(self) -> None:
        """Start the butterfly-chase loop animation."""
        self.pet.animator.set_animation("butterfly")

    def update(self) -> None:
        """Advance the looping butterfly animation."""
        super().update()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Left-click transitions to DraggingState.

        Args:
            event: The Pygame event to handle.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_rel_pos: Tuple[int, int] = pygame.mouse.get_pos()
            if self.pet.is_click_on_sprite(
                mouse_rel_pos[0], mouse_rel_pos[1]
            ):
                self.pet.change_state(DraggingState(self.pet))
