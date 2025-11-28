# sprite_animation.py

import pygame
import math
from utils import resource_path  # Kept commented as per original

def load_frames_from_sheet(filepath, frame_w, frame_h, target_w, target_h, target_frames, no_scaling=False):
    """
    Loads, extracts, and scales animation frames from a sprite sheet.
    Creates default test frames if loading fails.

    Args:
        filepath (str): Path to the sprite sheet image.
        frame_w (int): Width of a single frame in the source sheet.
        frame_h (int): Height of a single frame in the source sheet.
        target_w (int): Desired final width for the scaled frame.
        target_h (int): Desired final height for the scaled frame.
        target_frames (int): Total number of frames to extract.
        no_scaling (bool): If True, frames are loaded but not scaled to target_w/h.

    Returns:
        list: A list of pygame.Surface objects (animation frames).
    """
    absolute_path = resource_path(filepath)
    frames = []
    frame_w = math.ceil(frame_w)
    frame_h = math.ceil(frame_h)

    try:
        sprite_sheet = pygame.image.load(absolute_path).convert_alpha()

    except Exception as e:
        # Failed to load image, create a visible test image as fallback.
        sprite_sheet = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        sprite_sheet.fill((0, 0, 0, 0))
        pygame.draw.circle(sprite_sheet, (255, 100, 100, 180), (frame_w // 2, frame_h // 2), frame_w // 2 - 1)

        frames.append(sprite_sheet)
        return [pygame.transform.smoothscale(f, (target_w, target_h)).convert_alpha() for f in frames]

    # Iterate through the sprite sheet to extract frames
    for y in range(0, sprite_sheet.get_height(), frame_h):
        for x in range(0, sprite_sheet.get_width(), frame_w):
            if len(frames) >= target_frames:
                break

            frame_rect = pygame.Rect(x, y, frame_w, frame_h)

            if frame_rect.width > 0 and frame_rect.height > 0:
                # Extract and convert frame to alpha format
                frame = sprite_sheet.subsurface(frame_rect).convert_alpha()
                frames.append(frame)
        if len(frames) >= target_frames:
            break

    # Fallback if no frames were extracted (e.g., file loaded but sheet is empty)
    if not frames:
        test_frame = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        test_frame.fill((0, 0, 0, 0))
        pygame.draw.circle(test_frame, (255, 100, 100, 180), (target_w // 2, target_h // 2), 50)
        frames = [test_frame]
    else:
        # Conditional scaling: scale frames or just ensure alpha conversion.
        if not no_scaling:
            frames = [pygame.transform.smoothscale(f, (target_w, target_h)).convert_alpha() for f in frames]
        else:
            frames = [f.convert_alpha() for f in frames]

    return frames


class AnimationController:
    """
    Manages multiple animation sequences, handles frame indexing, looping rules,
    and transitions between sequences.
    """
    # Defines the playback rules for different animation sub-sequences
    ANIMATION_RULES = {
        'idle': {'type': 'loop_reverse'},  # Loop and reverse direction when boundaries reached
        'start': {'type': 'one_shot'},  # Play once forward
        'hold': {'type': 'loop_reverse'},
        'release': {'type': 'one_shot_reverse'},  # Play once backward
        'display': {'type': 'loop_reverse'},
        'teleport': {'type': 'one_shot'},
        'magic_start': {'type': 'one_shot'},
        'magic_keep': {'type': 'loop_reverse'},
        'fishing': {'type': 'one_shot'},
        'bye': {'type': 'one_shot'},
        'upset': {'type': 'loop_reverse'},
        "angry": {"type": "one_shot"},
    }

    def __init__(self, animations_data, animation_ranges):
        """
        Initializes the controller with loaded frames and frame ranges.

        Args:
            animations_data (dict): Mapping animation source keys (e.g., 'idle', 'drag_A_frames') to lists of frames.
            animation_ranges (dict): Mapping sequence names (e.g., 'idle', 'drag_A_start') to (start, end) frame indices.
        """
        self.animations = animations_data
        self.animation_ranges = animation_ranges
        self.current_sequence_name = None

        # Run-time State
        self.current_frames = []
        self.total_frames = 0
        self.current_index = 0.0  # Use float for smoother index updates if needed
        self.direction = 1  # 1: forward, -1: reverse
        self.start_frame = 0  # Start index for the current sequence playback
        self.end_frame = 0  # End index for the current sequence playback
        self.is_playing_one_shot = False
        self.is_finished = False
        self.next_sequence_on_finish = None  # Name of the sequence to switch to after a one-shot finishes

    def set_animation(self, sequence_name, next_sequence=None):
        """
        Switches to a new animation sequence and resets index and playback state.

        Args:
            sequence_name (str): The name of the sequence to switch to (e.g., 'drag_A_start').
            next_sequence (str, optional): The sequence name to transition to upon completion of a one-shot animation.
        """
        if sequence_name == self.current_sequence_name:
            return

        # 1. Determine Frame Source and Sub-sequence Name
        parts = sequence_name.split('_')

        if parts[0] == 'drag':
            # Example: 'drag_A_start' -> prefix 'drag_A', sub_name 'start', source 'drag_A_frames'
            prefix = f"{parts[0]}_{parts[1]}"
            sub_name = parts[2]
            frame_source_name = f"{prefix}_frames"
        elif sequence_name in ['magic_start', 'magic_keep']:
            # Handle Magic animations which share the same source sheet
            prefix = None
            sub_name = sequence_name
            frame_source_name = 'magic'
        else:
            # Simple animation name (e.g., 'idle', 'teleport')
            prefix = None
            sub_name = sequence_name
            frame_source_name = sequence_name

        rule = self.ANIMATION_RULES.get(sub_name if prefix else sequence_name)

        if not rule or frame_source_name not in self.animations:
            return

        # 2. Update Frame List and Range
        self.current_sequence_name = sequence_name
        self.current_frames = self.animations[frame_source_name]
        self.total_frames = len(self.current_frames)

        # Get playback range from ranges dictionary
        if sequence_name in self.animation_ranges:
            self.start_frame, self.end_frame = self.animation_ranges[sequence_name]
        else:
            # Fallback: use the entire frame list
            self.start_frame, self.end_frame = 0, self.total_frames - 1

        # 3. Set Playback State and Direction
        self.is_playing_one_shot = (rule['type'].startswith('one_shot'))
        self.is_finished = False

        if rule['type'] == 'one_shot_reverse':
            # Reverse animation (e.g., 'release'): Start at the end frame, move backward.
            self.current_index = float(self.end_frame)
            self.direction = -1
        else:
            # Forward animation (e.g., 'start', 'loop'): Start at the start frame, move forward.
            self.current_index = float(self.start_frame)
            self.direction = 1

        # Save the next sequence name for transition
        self.next_sequence_on_finish = next_sequence

    def update_frame(self):
        """
        Updates the animation frame index for the current sequence based on its rule.
        """
        if self.total_frames <= 1 or self.is_finished:
            return

        self.current_index += self.direction

        # --- One-Shot Logic ---
        if self.is_playing_one_shot:

            # Forward playback, reached end boundary
            if self.direction == 1 and self.current_index > self.end_frame:
                self.current_index = float(self.end_frame)
                self.is_finished = True

            # Reverse playback, reached start boundary
            elif self.direction == -1 and self.current_index < self.start_frame:
                self.current_index = float(self.start_frame)
                self.is_finished = True

            return

        # --- Loop Logic (Loop & Reverse) ---

        # Looping forward, reached end boundary
        if self.current_index > self.end_frame:
            self.direction = -1
            # Adjust index to prevent immediate flip back if range is too small
            self.current_index = float(self.end_frame - 1) if self.end_frame > self.start_frame else float(
                self.start_frame)

        # Looping backward, reached start boundary
        elif self.current_index < self.start_frame:
            self.direction = 1
            self.current_index = float(self.start_frame + 1) if self.end_frame > self.start_frame else float(
                self.start_frame)

    def get_current_frame(self):
        """Returns the current Pygame Surface frame."""
        if not self.current_frames:
            # Safe fallback: return a minimal transparent Surface
            return pygame.Surface((1, 1), pygame.SRCALPHA)

        # Ensure index is within the bounds [0, total_frames - 1]
        index = max(0, min(int(self.current_index), self.total_frames - 1))
        return self.current_frames[index]

    def check_finished_and_advance(self):
        """
        Checks if a one-shot animation has finished.
        If finished, it handles the transition to the next predefined sequence.

        Returns:
            str/bool/None: The name of the sequence switched to (str),
                           True if finished but no next sequence, or None if still playing.
        """
        if self.is_finished and self.is_playing_one_shot:

            # Reset finished flag immediately to allow next state to react
            self.is_finished = False

            # 1. Check for a predefined next sequence (e.g., magic_start -> magic_keep)
            if self.next_sequence_on_finish:
                name_to_advance = self.next_sequence_on_finish

                # Clear next_sequence flag
                self.next_sequence_on_finish = None

                # Transition to the next sequence
                self.set_animation(name_to_advance)

                return name_to_advance

            # 2. No predefined next sequence (e.g., teleport finished -> needs state change)
            return True

        return None