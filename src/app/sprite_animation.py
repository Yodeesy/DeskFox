"""Sprite-sheet loading and animation-frame control.

Provides utilities to extract and scale frames from sprite sheets, and an
``AnimationController`` class that handles frame indexing, playback rules
(one-shot, loop, reverse), and sequence transitions.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from utils import resource_path


def load_frames_from_sheet(
    filepath: str,
    frame_w: float,
    frame_h: float,
    target_w: int,
    target_h: int,
    target_frames: int,
    no_scaling: bool = False,
) -> List[pygame.Surface]:
    """Extract and scale animation frames from a sprite sheet image.

    Frames are read left-to-right, top-to-bottom. If the sheet fails to
    load, a fallback placeholder frame is returned.

    Args:
        filepath: Path to the sprite sheet PNG.
        frame_w: Width of a single source frame in pixels.
        frame_h: Height of a single source frame in pixels.
        target_w: Desired output frame width (scaling).
        target_h: Desired output frame height (scaling).
        target_frames: Total number of frames to extract.
        no_scaling: If True, keep frames at their original size.

    Returns:
        A list of ``pygame.Surface`` objects, one per frame.
    """
    absolute_path: str = resource_path(filepath)
    frames: List[pygame.Surface] = []
    frame_w = math.ceil(frame_w)
    frame_h = math.ceil(frame_h)

    try:
        sprite_sheet: pygame.Surface = pygame.image.load(
            absolute_path
        ).convert_alpha()
    except Exception:
        # Create a visible fallback placeholder so the app doesn't crash.
        placeholder: pygame.Surface = pygame.Surface(
            (frame_w, frame_h), pygame.SRCALPHA
        )
        placeholder.fill((0, 0, 0, 0))
        pygame.draw.circle(
            placeholder, (255, 100, 100, 180),
            (frame_w // 2, frame_h // 2), frame_w // 2 - 1,
        )
        frames.append(placeholder)
        return [
            pygame.transform.smoothscale(f, (target_w, target_h)).convert_alpha()
            for f in frames
        ]

    for y in range(0, sprite_sheet.get_height(), frame_h):
        for x in range(0, sprite_sheet.get_width(), frame_w):
            if len(frames) >= target_frames:
                break

            frame_rect: pygame.Rect = pygame.Rect(x, y, frame_w, frame_h)
            if frame_rect.width > 0 and frame_rect.height > 0:
                frame: pygame.Surface = (
                    sprite_sheet.subsurface(frame_rect).convert_alpha()
                )
                frames.append(frame)

        if len(frames) >= target_frames:
            break

    if not frames:
        # Sheet loaded but was empty; still provide a fallback.
        test_frame: pygame.Surface = pygame.Surface(
            (target_w, target_h), pygame.SRCALPHA
        )
        test_frame.fill((0, 0, 0, 0))
        pygame.draw.circle(
            test_frame, (255, 100, 100, 180),
            (target_w // 2, target_h // 2), 50,
        )
        frames = [test_frame]
    elif not no_scaling:
        frames = [
            pygame.transform.smoothscale(f, (target_w, target_h)).convert_alpha()
            for f in frames
        ]
    else:
        frames = [f.convert_alpha() for f in frames]

    return frames


def load_animation(
    pet_instance: Any,
    animation_name: str,
    config_key: Optional[str] = None,
    no_scaling: bool = False,
    is_magic_type: bool = False,
) -> None:
    """Load animation frames and frame ranges from the animation config.

    Args:
        pet_instance: The ``DesktopPet`` instance.
        animation_name: Key for the animation in the pet's config.
        config_key: Override for the config lookup key (defaults to
            ``animation_name``).
        no_scaling: If True, do not scale frames to the pet's size.
        is_magic_type: If True, this animation has named sub-ranges
            (e.g. ``magic_start``, ``magic_keep``).
    """
    pet: Any = pet_instance
    if config_key is None:
        config_key = animation_name

    anim_config: Dict[str, Any] = pet.animation_config[config_key]
    frames: List[pygame.Surface] = load_frames_from_sheet(
        anim_config["filepath"],
        anim_config["frame_w"],
        anim_config["frame_h"],
        pet.width,
        pet.height,
        anim_config["total_frames"],
        no_scaling=no_scaling,
    )

    pet.all_animations[animation_name] = frames

    if is_magic_type:
        for sub_name, ranges in anim_config["ranges"].items():
            pet.animation_ranges[f"{sub_name}"] = ranges
    else:
        pet.animation_ranges[animation_name] = (
            anim_config["ranges"][animation_name]
        )


def load_dragging_animations(pet_instance: Any) -> None:
    """Load all dragging animation variants from the animation config.

    Each variant (e.g. ``drag_A``, ``drag_B``) registers frame lists and
    sub-range entries (``start``, ``hold``, ``release``) on the pet.

    Args:
        pet_instance: The ``DesktopPet`` instance.
    """
    pet: Any = pet_instance
    dragging_options: List[Dict[str, Any]] = pet.animation_config["dragging"]
    pet.available_drag_prefixes = []

    for group in dragging_options:
        prefix: str = group["prefix"]
        pet.available_drag_prefixes.append(prefix)

        drag_frames: List[pygame.Surface] = load_frames_from_sheet(
            group["filepath"],
            group["frame_w"],
            group["frame_h"],
            pet.width,
            pet.height,
            group["total_frames"],
        )
        frame_key: str = f"{prefix}_frames"

        if drag_frames:
            pet.all_animations[frame_key] = drag_frames

        for sub_name, ranges in group["ranges"].items():
            pet.animation_ranges[f"{prefix}_{sub_name}"] = ranges


def register_animation_metadata(
    pet_instance: Any,
    animation_name: str,
    config_key: Optional[str] = None,
    no_scaling: bool = False,
    is_magic_type: bool = False,
) -> None:
    """Register animation metadata without loading frames.

    Stores filepath, dimensions, and frame count on the controller so
    frames can be loaded on demand when the animation is first played.

    Args:
        pet_instance: The ``DesktopPet`` instance.
        animation_name: Key for the animation in the pet's config.
        config_key: Override for the config lookup key.
        no_scaling: If True, do not scale frames to the pet's size.
        is_magic_type: If True, register sub-ranges (e.g. magic_start, magic_keep).
    """
    pet: Any = pet_instance
    if config_key is None:
        config_key = animation_name

    anim_config: Dict[str, Any] = pet.animation_config[config_key]

    pet.animator.register_metadata(
        source_name=animation_name,
        filepath=anim_config["filepath"],
        frame_w=anim_config["frame_w"],
        frame_h=anim_config["frame_h"],
        total_frames=anim_config["total_frames"],
        target_w=pet.width,
        target_h=pet.height,
        no_scaling=no_scaling,
    )

    if is_magic_type:
        for sub_name, ranges in anim_config["ranges"].items():
            pet.animation_ranges[f"{sub_name}"] = ranges
    else:
        pet.animation_ranges[animation_name] = (
            anim_config["ranges"][animation_name]
        )


def register_dragging_metadata(pet_instance: Any) -> None:
    """Register dragging animation metadata without loading frames.

    Args:
        pet_instance: The ``DesktopPet`` instance.
    """
    pet: Any = pet_instance
    dragging_options: List[Dict[str, Any]] = pet.animation_config["dragging"]
    pet.available_drag_prefixes = []

    for group in dragging_options:
        prefix: str = group["prefix"]
        pet.available_drag_prefixes.append(prefix)

        frame_key: str = f"{prefix}_frames"

        pet.animator.register_metadata(
            source_name=frame_key,
            filepath=group["filepath"],
            frame_w=group["frame_w"],
            frame_h=group["frame_h"],
            total_frames=group["total_frames"],
            target_w=pet.width,
            target_h=pet.height,
            no_scaling=False,
        )

        for sub_name, ranges in group["ranges"].items():
            pet.animation_ranges[f"{prefix}_{sub_name}"] = ranges


class AnimationController:
    """Manages playback of named animation sequences.

    Supports three playback modes:
        - ``loop_reverse`` — play forward to the last frame, then reverse
          back to the first frame and repeat.
        - ``one_shot`` — play forward once and stop.
        - ``one_shot_reverse`` — play backward from the last frame once
          and stop.

    Call ``set_animation(name)`` to switch sequences, then call
    ``update_frame()`` each tick. Finished one-shot sequences are detected
    via ``check_finished_and_advance()``.
    """

    ANIMATION_RULES: Dict[str, Dict[str, str]] = {
        "idle":         {"type": "loop_reverse"},
        "start":        {"type": "one_shot"},
        "hold":         {"type": "loop_reverse"},
        "release":      {"type": "one_shot_reverse"},
        "display":      {"type": "loop_reverse"},
        "teleport":     {"type": "one_shot"},
        "magic_start":  {"type": "one_shot"},
        "magic_keep":   {"type": "loop_reverse"},
        "fishing":      {"type": "one_shot"},
        "bye":          {"type": "one_shot"},
        "upset":        {"type": "loop_reverse"},
        "angry":        {"type": "one_shot"},
        "butterfly":    {"type": "loop_reverse"},
    }

    MAX_CACHED: int = 3

    def __init__(
        self,
        animations_data: Dict[str, List[pygame.Surface]],
        animation_ranges: Dict[str, Tuple[int, int]],
    ) -> None:
        """Initialize the controller with pre-loaded frames and ranges.

        Args:
            animations_data: Mapping from source keys (e.g. ``'idle'``,
                ``'drag_A_frames'``) to lists of frame surfaces.
            animation_ranges: Mapping from sequence names (e.g.
                ``'idle'``, ``'drag_A_start'``) to ``(start, end)``
                frame index tuples.
        """
        self.animations: Dict[str, List[pygame.Surface]] = animations_data
        self.animation_ranges: Dict[str, Tuple[int, int]] = animation_ranges
        self.current_sequence_name: Optional[str] = None

        self.current_frames: List[pygame.Surface] = []
        self.total_frames: int = 0
        self.current_index: float = 0.0
        self.direction: int = 1
        self.start_frame: int = 0
        self.end_frame: int = 0
        self.is_playing_one_shot: bool = False
        self.is_finished: bool = False
        self.next_sequence_on_finish: Optional[str] = None

        # Lazy-loading state.
        self._anim_metadata: Dict[str, Dict[str, Any]] = {}
        self._frame_cache: Dict[str, List[pygame.Surface]] = {}
        self._cache_order: List[str] = []

    def register_metadata(
        self,
        source_name: str,
        filepath: str,
        frame_w: float,
        frame_h: float,
        total_frames: int,
        target_w: int,
        target_h: int,
        no_scaling: bool = False,
    ) -> None:
        """Store animation metadata for on-demand frame loading.

        Args:
            source_name: Cache key (e.g. ``'idle'``, ``'drag_A_frames'``).
            filepath: Path to the sprite sheet PNG.
            frame_w: Source frame width in pixels.
            frame_h: Source frame height in pixels.
            target_w: Desired output frame width.
            target_h: Desired output frame height.
            total_frames: Total number of frames to extract.
            no_scaling: If True, keep frames at original size.
        """
        self._anim_metadata[source_name] = {
            "filepath": filepath,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "target_w": target_w,
            "target_h": target_h,
            "total_frames": total_frames,
            "no_scaling": no_scaling,
        }

    def _prewarm(self, source_name: str) -> None:
        """Load and cache frames for *source_name* immediately.

        Args:
            source_name: Cache key (e.g. ``'idle'``, ``'drag_A_frames'``).
        """
        if source_name in self._frame_cache:
            return
        if source_name not in self._anim_metadata:
            return
        meta = self._anim_metadata[source_name]
        frames = load_frames_from_sheet(
            meta["filepath"],
            meta["frame_w"],
            meta["frame_h"],
            meta["target_w"],
            meta["target_h"],
            meta["total_frames"],
            no_scaling=meta["no_scaling"],
        )
        self._frame_cache[source_name] = frames
        self.animations[source_name] = frames

    def _access_cache(self, source_name: str) -> None:
        """Mark *source_name* as most-recently-used; evict LRU if over limit.

        Args:
            source_name: Cache key to promote in the LRU order.
        """
        if source_name in self._cache_order:
            self._cache_order.remove(source_name)
        self._cache_order.append(source_name)

        while len(self._cache_order) > self.MAX_CACHED:
            evict_name = self._cache_order.pop(0)
            if evict_name in self._frame_cache:
                del self._frame_cache[evict_name]
            if evict_name in self.animations:
                del self.animations[evict_name]

    def set_animation(
        self,
        sequence_name: str,
        next_sequence: Optional[str] = None,
    ) -> None:
        """Switch to a new animation sequence.

        Args:
            sequence_name: The sequence to play (e.g. ``'drag_A_start'``).
            next_sequence: Optional name of the sequence to auto-transition
                to when a one-shot finishes.
        """
        if sequence_name == self.current_sequence_name:
            return

        # Parse sequence name to find the frame source.
        parts: List[str] = sequence_name.split("_")

        if parts[0] == "drag":
            prefix: str = f"{parts[0]}_{parts[1]}"
            sub_name: str = parts[2]
            frame_source_name: str = f"{prefix}_frames"
        elif sequence_name in ("magic_start", "magic_keep"):
            sub_name = sequence_name
            frame_source_name = "magic"
        else:
            sub_name = sequence_name
            frame_source_name = sequence_name

        rule: Optional[Dict[str, str]] = self.ANIMATION_RULES.get(
            sub_name if parts[0] == "drag" else sequence_name
        )

        if not rule or (frame_source_name not in self.animations and frame_source_name not in self._anim_metadata):
            return

        self.current_sequence_name = sequence_name

        # Lazy-load frames on cache miss.
        if frame_source_name not in self._frame_cache:
            if frame_source_name in self._anim_metadata:
                self._prewarm(frame_source_name)
            elif frame_source_name not in self.animations:
                return
            else:
                # Legacy path: frames were pre-loaded into self.animations.
                self._frame_cache[frame_source_name] = (
                    self.animations[frame_source_name]
                )
                self._cache_order.append(frame_source_name)

        self._access_cache(frame_source_name)
        self.current_frames = self._frame_cache[frame_source_name]
        self.total_frames = len(self.current_frames)

        if sequence_name in self.animation_ranges:
            self.start_frame, self.end_frame = (
                self.animation_ranges[sequence_name]
            )
        else:
            self.start_frame, self.end_frame = 0, self.total_frames - 1

        self.is_playing_one_shot = rule["type"].startswith("one_shot")
        self.is_finished = False

        if rule["type"] == "one_shot_reverse":
            self.current_index = float(self.end_frame)
            self.direction = -1
        else:
            self.current_index = float(self.start_frame)
            self.direction = 1

        self.next_sequence_on_finish = next_sequence

    def update_frame(self) -> None:
        """Advance the frame index according to the current playback rule."""
        if self.total_frames <= 1 or self.is_finished:
            return

        self.current_index += self.direction

        if self.is_playing_one_shot:
            if self.direction == 1 and self.current_index > self.end_frame:
                self.current_index = float(self.end_frame)
                self.is_finished = True
            elif (
                self.direction == -1
                and self.current_index < self.start_frame
            ):
                self.current_index = float(self.start_frame)
                self.is_finished = True
            return

        # Loop-reverse: bounce at boundaries.
        if self.current_index > self.end_frame:
            self.direction = -1
            self.current_index = (
                float(self.end_frame - 1)
                if self.end_frame > self.start_frame
                else float(self.start_frame)
            )
        elif self.current_index < self.start_frame:
            self.direction = 1
            self.current_index = (
                float(self.start_frame + 1)
                if self.end_frame > self.start_frame
                else float(self.start_frame)
            )

    def get_current_frame(self) -> pygame.Surface:
        """Return the current frame surface.

        Returns:
            The ``pygame.Surface`` for the current frame index, or a
            minimal transparent surface if no frames are loaded.
        """
        if not self.current_frames:
            return pygame.Surface((1, 1), pygame.SRCALPHA)

        index: int = max(
            0, min(int(self.current_index), self.total_frames - 1)
        )
        return self.current_frames[index]

    def check_finished_and_advance(self) -> Optional[Any]:
        """Check if a one-shot has finished and auto-advance if configured.

        Returns:
            The name of the next sequence if auto-advanced, ``True`` if
            the one-shot finished with no next sequence configured, or
            ``None`` if still playing.
        """
        if self.is_finished and self.is_playing_one_shot:
            self.is_finished = False

            if self.next_sequence_on_finish:
                name_to_advance: Optional[str] = self.next_sequence_on_finish
                self.next_sequence_on_finish = None
                self.set_animation(name_to_advance)
                return name_to_advance

            return True

        return None
