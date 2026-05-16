"""
Convert split parts + manifest into a skeletal animation definition.

Reads a manifest.json from the part splitter and generates an idle.json
that reconstructs the original pose, ready for the skeletal animation pipeline.

Usage:
    python parts_to_animation.py my_animations/fox/parts/ my_animations/fox/ --canvas 350 350
    python parts_to_animation.py my_animations/fox/parts/ my_animations/fox/ --preview
"""

import os, sys, json, argparse
import pygame


def load_manifest(parts_dir: str) -> tuple:
    """Load manifest.json and part images."""
    manifest_path = os.path.join(parts_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"ERROR: {manifest_path} not found")
        sys.exit(1)

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    parts = {}
    for name, rect in manifest.get("parts", {}).items():
        img_path = os.path.join(parts_dir, f"{name}.png")
        if os.path.exists(img_path):
            img = pygame.image.load(img_path)
            parts[name] = {
                "image_path": f"{name}.png",
                "width": img.get_width(),
                "height": img.get_height(),
                "source_x": rect[0],
                "source_y": rect[1],
                "source_w": rect[2],
                "source_h": rect[3],
            }

    return manifest, parts


def guess_anchor(part_name: str, pw: int, ph: int) -> list:
    """Guess joint point relative to part image (for reference only)."""
    cx, cy = pw // 2, ph // 2
    defaults = {
        "head": [cx, ph], "left_ear": [pw, ph], "right_ear": [0, ph],
        "body": [cx, 0], "left_arm": [pw // 3, 0], "right_arm": [pw * 2 // 3, 0],
        "left_hand": [cx, 0], "right_hand": [cx, 0],
        "left_leg": [cx, 0], "right_leg": [cx, 0], "tail": [pw // 4, ph // 2],
    }
    return defaults.get(part_name, [cx, cy])


def make_default_keyframes(name: str, anchor: list, joint: list, z: int) -> list:
    """Generate subtle idle-motion keyframes. Duration = 60 frames, 30 fps = 2s cycle."""
    base = {"x": 0, "y": 0, "rotation": 0, "scale_x": 1.0, "scale_y": 1.0}

    if name in ("body", "head"):
        return [
            {**base, "frame": 0,  "y": 0,  "easing": "ease_in_out"},
            {**base, "frame": 15, "y": -3, "easing": "ease_in_out"},
            {**base, "frame": 30, "y": 0,  "easing": "ease_in_out"},
            {**base, "frame": 45, "y": 2,  "easing": "ease_in_out"},
            {**base, "frame": 60, "y": 0,  "easing": "ease_in_out"},
        ]

    if "ear" in name:
        rot = -5 if "left" in name else 5
        return [
            {**base, "frame": 0,  "rotation": 0,   "easing": "ease_in_out"},
            {**base, "frame": 20, "rotation": rot, "easing": "ease_in_out"},
            {**base, "frame": 40, "rotation": -2,  "easing": "ease_in_out"},
            {**base, "frame": 60, "rotation": 0,   "easing": "ease_in_out"},
        ]

    if "tail" in name:
        return [
            {**base, "frame": 0,  "rotation": 0,  "easing": "ease_in_out"},
            {**base, "frame": 15, "rotation": 8,  "easing": "ease_in_out"},
            {**base, "frame": 30, "rotation": -4, "easing": "ease_in_out"},
            {**base, "frame": 45, "rotation": 5,  "easing": "ease_in_out"},
            {**base, "frame": 60, "rotation": 0,  "easing": "ease_in_out"},
        ]

    if "arm" in name or "hand" in name:
        return [
            {**base, "frame": 0,  "y": 0,  "easing": "ease_in_out"},
            {**base, "frame": 30, "y": 2,  "easing": "ease_in_out"},
            {**base, "frame": 60, "y": 0,  "easing": "ease_in_out"},
        ]

    if "leg" in name:
        return [
            {**base, "frame": 0,  "y": 0,  "easing": "ease_in_out"},
            {**base, "frame": 30, "y": 1,  "easing": "ease_in_out"},
            {**base, "frame": 60, "y": 0,  "easing": "ease_in_out"},
        ]

    return [
        {**base, "frame": 0,  "easing": "ease_in_out"},
        {**base, "frame": 60, "easing": "ease_in_out"},
    ]


def guess_z(part_name: str) -> int:
    """Guess render order."""
    z_order = {
        "tail": 0,
        "left_ear": 1,
        "right_ear": 1,
        "left_leg": 2,
        "right_leg": 2,
        "body": 3,
        "left_arm": 4,
        "right_arm": 4,
        "left_hand": 5,
        "right_hand": 5,
        "head": 6,
    }
    return z_order.get(part_name, 3)


def main():
    parser = argparse.ArgumentParser(
        description="Generate skeletal animation from split parts + manifest"
    )
    parser.add_argument("parts_dir", help="Directory containing part PNGs + manifest.json")
    parser.add_argument("output_dir", help="Output directory for animation JSON and parts")
    parser.add_argument("--canvas", nargs=2, type=int, default=[350, 350],
                       metavar=("W", "H"), help="Canvas size (default: 350 350)")
    parser.add_argument("--preview", action="store_true", help="Preview the assembled pose")
    parser.add_argument("-n", "--name", default="idle", help="Animation name (default: idle)")
    args = parser.parse_args()

    pygame.init()

    manifest, parts = load_manifest(args.parts_dir)
    src_w, src_h = manifest["source_size"]
    canvas_w, canvas_h = args.canvas
    scale = canvas_w / src_w  # uniform scale

    print(f"Source: {src_w}x{src_h} → Canvas: {canvas_w}x{canvas_h} (scale: {scale:.3f})")
    print(f"Found {len(parts)} parts: {', '.join(sorted(parts.keys()))}")

    # Prepare output
    os.makedirs(args.output_dir, exist_ok=True)
    out_parts_dir = os.path.join(args.output_dir, "parts")
    os.makedirs(out_parts_dir, exist_ok=True)

    # Copy part images to output directory and resize
    anim_parts = {}
    for name, info in parts.items():
        src_img = pygame.image.load(os.path.join(args.parts_dir, info["image_path"]))
        new_w = max(1, int(info["source_w"] * scale))
        new_h = max(1, int(info["source_h"] * scale))
        scaled_img = pygame.transform.smoothscale(src_img, (new_w, new_h))
        dest_path = os.path.join(out_parts_dir, f"{name}.png")
        pygame.image.save(scaled_img, dest_path)
        print(f"  Copied & scaled: {name}.png ({info['source_w']}x{info['source_h']} → {new_w}x{new_h})")

    # Calculate positions for the idle keyframe.
    #
    # In skeletal_to_spritesheet.py, the transform formula is:
    #   pos_x = x - anchor[0] + canvas_w / 2
    #   pos_y = y - anchor[1] + canvas_h / 2
    #
    # We want the part's top-left to be at (sx*scale, sy*scale) on canvas.
    # With x=0, y=0:
    #   anchor[0] = canvas_w/2 - sx*scale
    #   anchor[1] = canvas_h/2 - sy*scale

    anim_def = {
        "name": args.name,
        "source": manifest["source_size"],
        "canvas": {"width": canvas_w, "height": canvas_h},
        "duration_frames": 60,
        "framerate": 30,
        "parts": {}
    }

    for name, info in parts.items():
        pw = max(1, int(info["source_w"] * scale))
        ph = max(1, int(info["source_h"] * scale))
        sx, sy = info["source_x"], info["source_y"]

        # Anchor: maps canvas center -> part top-left at scaled position
        anchor = [
            int(canvas_w / 2 - sx * scale),
            int(canvas_h / 2 - sy * scale),
        ]

        z = guess_z(name)
        # Joint point used as rotation center (relative to part image)
        joint = guess_anchor(name, pw, ph)

        anim_def["parts"][name] = {
            "image": f"parts/{name}.png",
            "anchor": anchor,
            "z": z,
            "_joint": joint,  # for reference, not used by engine
            "keyframes": make_default_keyframes(name, anchor, joint, z),
        }

    # Write animation JSON
    json_path = os.path.join(args.output_dir, f"{args.name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(anim_def, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {json_path}")

    # Print a config snippet for main.py
    print(f"\n--- Add to ANIMATION_CONFIG in main.py ---")
    total_frames = anim_def["duration_frames"]
    print(f'"{args.name}": {{')
    print(f'    "filepath": "assets/{args.name}.png",')
    print(f'    "frame_w": {canvas_w},')
    print(f'    "frame_h": {canvas_h},')
    print(f'    "total_frames": {total_frames},')
    print(f'    "ranges": {{"{args.name}": (0, {total_frames - 1})}}')
    print(f'}}')

    # Preview if requested
    if args.preview:
        from skeletal_to_spritesheet import render_animation
        print("\nLaunching preview...")
        frames = render_animation(anim_def, args.output_dir, preview=True)
        print(f"Rendered {len(frames)} frames")

    pygame.quit()


if __name__ == "__main__":
    main()
