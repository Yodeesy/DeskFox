"""
Assemble Individual PNG Frames into a Unified Spritesheet

Takes a directory of individual frame PNGs and packs them into a single
sprite sheet compatible with DeskFox's AnimationController.

Usage:
    python frames_to_spritesheet.py output/clean_idle/ idle_spritesheet.png
    python frames_to_spritesheet.py frames/ output.png --columns 12
"""

import math
import os
import sys
import argparse
from pathlib import Path

import pygame


def main():
    parser = argparse.ArgumentParser(
        description="Pack individual PNG frames into a sprite sheet"
    )
    parser.add_argument("input_dir", help="Directory containing frame PNGs (sorted by name)")
    parser.add_argument("output", help="Output sprite sheet PNG path")
    parser.add_argument("--columns", type=int, default=None,
                       help="Number of columns (auto-calculate if omitted)")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    if not input_path.is_dir():
        print(f"ERROR: Input directory not found: {args.input_dir}")
        sys.exit(1)

    png_files = sorted(input_path.glob("*.png"))
    if not png_files:
        print(f"No PNG files found in {args.input_dir}")
        sys.exit(1)

    pygame.init()
    pygame.display.set_mode((1, 1))

    frames = []
    for png in png_files:
        try:
            img = pygame.image.load(str(png)).convert_alpha()
            frames.append(img)
        except Exception as e:
            print(f"WARNING: Could not load {png}: {e}")

    if not frames:
        print("ERROR: No valid frames loaded.")
        sys.exit(1)

    frame_w = frames[0].get_width()
    frame_h = frames[0].get_height()

    columns = args.columns or int(math.ceil(math.sqrt(len(frames))))
    rows = int(math.ceil(len(frames) / columns))

    sheet_w = columns * frame_w
    sheet_h = rows * frame_h

    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    sheet.fill((0, 0, 0, 0))

    for i, frame in enumerate(frames):
        col = i % columns
        row = i // columns
        sheet.blit(frame, (col * frame_w, row * frame_h))

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    pygame.image.save(sheet, args.output)

    print(f"✅ Sprite sheet saved: {args.output}")
    print(f"   Size: {sheet_w}x{sheet_h}, Frames: {len(frames)}, "
          f"Grid: {columns}x{rows}, Frame: {frame_w}x{frame_h}")
    print()
    print("Add to ANIMATION_CONFIG in main.py:")
    print(f'  "framename": {{')
    print(f'      "filepath": "{args.output}",')
    print(f'      "frame_w": {frame_w},')
    print(f'      "frame_h": {frame_h},')
    print(f'      "total_frames": {len(frames)},')
    print(f'      "ranges": {{"framename": (0, {len(frames) - 1})}}')
    print(f'  }}')

    pygame.quit()


if __name__ == "__main__":
    main()
