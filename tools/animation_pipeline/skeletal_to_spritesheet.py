"""
Skeletal Animation → Sprite Sheet Converter

Composites body-part images into animation frames using JSON animation
definitions, then assembles them into a sprite sheet compatible with
the existing DeskFox AnimationController.

Usage:
    python skeletal_to_spritesheet.py animations/fox.json
    python skeletal_to_spritesheet.py animations/fox.json --preview
"""

import json
import math
import os
import sys
import argparse
from typing import Dict, List, Tuple, Optional

import pygame

# --- Easing functions ---

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def ease_in_out(t: float) -> float:
    """Smooth easing - natural looking motion."""
    return t * t * (3 - 2 * t)

def ease_out(t: float) -> float:
    return 1 - (1 - t) * (1 - t)

def ease_in(t: float) -> float:
    return t * t

EASING_MAP = {
    "linear": lambda t: t,
    "ease_in_out": ease_in_out,
    "ease_out": ease_out,
    "ease_in": ease_in,
}


def interpolate_keyframes(keyframes: List[Dict], frame: int, framerate: int = 15) -> Dict:
    """Interpolate between keyframes to get part transform at the given frame."""
    prev_kf = None
    next_kf = None

    for kf in keyframes:
        kf_frame = kf.get("frame", 0)
        if kf_frame <= frame:
            prev_kf = kf
        if kf_frame >= frame and next_kf is None:
            next_kf = kf
            break

    if prev_kf is None:
        return dict(next_kf.items()) if next_kf else {}
    if next_kf is None or next_kf.get("frame", 0) == prev_kf.get("frame", 0):
        return dict(prev_kf.items())

    duration = next_kf["frame"] - prev_kf["frame"]
    if duration == 0:
        return dict(prev_kf.items())

    raw_t = (frame - prev_kf["frame"]) / duration
    easing_name = prev_kf.get("easing", "ease_in_out")
    t = EASING_MAP.get(easing_name, ease_in_out)(raw_t)

    result = {}
    for key in ["x", "y", "rotation", "scale_x", "scale_y"]:
        result[key] = lerp(prev_kf.get(key, 0), next_kf.get(key, 0), t)
    return result


def render_animation(anim_def: Dict, base_dir: str, preview: bool = False) -> List[pygame.Surface]:
    """Render all frames of an animation by compositing body parts."""
    canvas_w = anim_def.get("canvas", {}).get("width", 350)
    canvas_h = anim_def.get("canvas", {}).get("height", 350)
    framerate = anim_def.get("framerate", 15)

    # Set up display BEFORE loading images (convert_alpha needs it)
    screen = None
    if preview:
        pygame.init()
        screen = pygame.display.set_mode((canvas_w, canvas_h))
        pygame.display.set_caption(f"Preview: {anim_def.get('name', 'animation')}")
        clock = pygame.time.Clock()
    else:
        # Headless: need a tiny hidden display for convert_alpha
        pygame.display.set_mode((1, 1))

    # Determine total frames from all part keyframes
    total_frames = anim_def.get("duration_frames", 120)

    # Load part images
    parts = {}
    for part_name, part_def in anim_def.get("parts", {}).items():
        img_path = part_def["image"]
        if not os.path.isabs(img_path):
            img_path = os.path.join(base_dir, img_path)
        try:
            img = pygame.image.load(img_path).convert_alpha()
            parts[part_name] = {
                "image": img,
                "anchor": part_def.get("anchor", [0, 0]),
                "keyframes": part_def.get("keyframes", []),
                "z": part_def.get("z", 0),
            }
        except Exception as e:
            print(f"WARNING: Could not load {img_path}: {e}")

    # Sort parts by z-order
    sorted_parts = sorted(parts.items(), key=lambda x: x[1]["z"])

    frames = []

    for frame_idx in range(total_frames):
        canvas = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))

        for part_name, part_data in sorted_parts:
            img = part_data["image"]
            anchor = part_data["anchor"]
            transform = interpolate_keyframes(part_data["keyframes"], frame_idx, framerate)

            if not transform:
                continue

            # Apply scale
            sx = transform.get("scale_x", 1.0)
            sy = transform.get("scale_y", 1.0)
            scaled_w = int(img.get_width() * sx)
            scaled_h = int(img.get_height() * sy)
            if scaled_w > 0 and scaled_h > 0:
                scaled_img = pygame.transform.smoothscale(img, (scaled_w, scaled_h))
            else:
                continue

            # Apply rotation
            rotation = transform.get("rotation", 0)
            if rotation != 0:
                rotated_img = pygame.transform.rotate(scaled_img, -rotation)
            else:
                rotated_img = scaled_img

            # Calculate position (anchor-based)
            # The image's anchor point should be at (x, y) on canvas
            # anchor is relative to the part image (e.g., center of the part)
            pos_x = transform.get("x", 0) - anchor[0] + canvas_w // 2
            pos_y = transform.get("y", 0) - anchor[1] + canvas_h // 2

            # Adjust for rotation center (Pygame rotates around image center)
            if rotation != 0:
                rot_rect = rotated_img.get_rect()
                orig_rect = scaled_img.get_rect()
                pos_x -= (rot_rect.width - orig_rect.width) // 2
                pos_y -= (rot_rect.height - orig_rect.height) // 2

            canvas.blit(rotated_img, (int(pos_x), int(pos_y)))

        frames.append(canvas)

        if preview and screen:
            screen.fill((50, 50, 50))
            screen.blit(canvas, (0, 0))
            pygame.display.flip()
            clock.tick(framerate)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    preview = False

    if preview and screen:
        pygame.quit()

    return frames


def frames_to_spritesheet(frames: List[pygame.Surface], output_path: str,
                          columns: Optional[int] = None):
    """Assemble frames into a single sprite sheet image."""
    if not frames:
        print("ERROR: No frames to export.")
        return

    frame_w = frames[0].get_width()
    frame_h = frames[0].get_height()

    if columns is None:
        # Auto-calculate: prefer roughly square sheets
        columns = int(math.ceil(math.sqrt(len(frames))))

    rows = int(math.ceil(len(frames) / columns))

    sheet_w = columns * frame_w
    sheet_h = rows * frame_h

    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    sheet.fill((0, 0, 0, 0))

    for i, frame in enumerate(frames):
        col = i % columns
        row = i // columns
        sheet.blit(frame, (col * frame_w, row * frame_h))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pygame.image.save(sheet, output_path)
    print(f"✅ Sprite sheet saved: {output_path}")
    print(f"   Size: {sheet_w}x{sheet_h}, Frames: {len(frames)}, "
          f"Columns: {columns}, Frame: {frame_w}x{frame_h}")


def create_template_animation(output_dir: str):
    """Create a template animation definition and placeholder parts
    so the user can start experimenting immediately."""
    os.makedirs(output_dir, exist_ok=True)
    parts_dir = os.path.join(output_dir, "parts")
    os.makedirs(parts_dir, exist_ok=True)

    # Create simple placeholder part images
    pygame.init()
    # We need a minimal display to create surfaces properly
    pygame.display.set_mode((1, 1))

    # Body part
    body = pygame.Surface((120, 160), pygame.SRCALPHA)
    pygame.draw.ellipse(body, (255, 140, 60, 255), (10, 10, 100, 140))
    pygame.draw.ellipse(body, (255, 200, 160, 255), (30, 50, 60, 80))
    pygame.image.save(body, os.path.join(parts_dir, "body.png"))

    # Head
    head = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(head, (255, 140, 60, 255), (10, 10, 80, 80))
    # Ears
    pygame.draw.polygon(head, (255, 140, 60, 255), [(15, 15), (5, -20), (35, 10)])
    pygame.draw.polygon(head, (255, 140, 60, 255), [(65, 10), (85, -20), (75, 15)])
    # Eyes
    pygame.draw.ellipse(head, (0, 0, 0, 255), (30, 35, 10, 12))
    pygame.draw.ellipse(head, (0, 0, 0, 255), (55, 35, 10, 12))
    # Nose
    pygame.draw.ellipse(head, (0, 0, 0, 255), (42, 55, 8, 6))
    pygame.image.save(head, os.path.join(parts_dir, "head.png"))

    # Tail
    tail = pygame.Surface((80, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(tail, (255, 140, 60, 255), (0, 0, 80, 90))
    pygame.draw.ellipse(tail, (255, 255, 255, 255), (50, 0, 30, 30))
    pygame.image.save(tail, os.path.join(parts_dir, "tail.png"))

    # Template animation definition
    template = {
        "name": "idle",
        "canvas": {"width": 350, "height": 350},
        "duration_frames": 120,
        "framerate": 15,
        "parts": {
            "tail": {
                "image": "parts/tail.png",
                "anchor": [70, 80],
                "z": 0,
                "keyframes": [
                    {"frame": 0,  "x": 0, "y": 0, "rotation": 0,   "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 30, "x": 0, "y": 0, "rotation": 15,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 60, "x": 0, "y": 0, "rotation": 0,   "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 90, "x": 0, "y": 0, "rotation": -15, "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 120,"x": 0, "y": 0, "rotation": 0,   "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                ]
            },
            "body": {
                "image": "parts/body.png",
                "anchor": [60, 80],
                "z": 1,
                "keyframes": [
                    {"frame": 0,  "x": 0, "y": 0,  "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 60, "x": 0, "y": -8, "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 120,"x": 0, "y": 0,  "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                ]
            },
            "head": {
                "image": "parts/head.png",
                "anchor": [50, 50],
                "z": 2,
                "keyframes": [
                    {"frame": 0,  "x": 0, "y": 0,  "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 60, "x": 0, "y": -5, "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                    {"frame": 120,"x": 0, "y": 0,  "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
                ]
            },
        }
    }

    template_path = os.path.join(output_dir, "idle.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    pygame.quit()
    print(f"✅ Template created at: {output_dir}")
    print(f"   Animation: {template_path}")
    print(f"   Parts: {parts_dir}/")
    print()
    print("Next steps:")
    print("  1. Replace placeholder PNGs in parts/ with your own art")
    print("  2. Edit idle.json to define your animation")
    print(f"  3. Run: python {__file__} {output_dir}/idle.json --preview")
    print(f"  4. Export: python {__file__} {output_dir}/idle.json -o idle.png")


def main():
    parser = argparse.ArgumentParser(
        description="Convert skeletal animation definitions to sprite sheets"
    )
    parser.add_argument("anim_json", nargs="?", help="Path to animation JSON definition")
    parser.add_argument("-o", "--output", help="Output sprite sheet path (default: <anim_name>.png)")
    parser.add_argument("--preview", action="store_true", help="Preview animation in a window")
    parser.add_argument("--init", metavar="DIR", help="Create a template animation in DIR")
    args = parser.parse_args()

    if args.init:
        create_template_animation(args.init)
        return

    if not args.anim_json:
        parser.print_help()
        return

    with open(args.anim_json, "r", encoding="utf-8") as f:
        anim_def = json.load(f)

    base_dir = os.path.dirname(os.path.abspath(args.anim_json))

    print(f"Rendering '{anim_def.get('name', 'unknown')}' "
          f"({anim_def.get('duration_frames', 0)} frames)...")
    frames = render_animation(anim_def, base_dir, preview=args.preview)

    output_path = args.output or f"{anim_def.get('name', 'output')}.png"
    frames_to_spritesheet(frames, os.path.join(base_dir, output_path))


if __name__ == "__main__":
    main()
