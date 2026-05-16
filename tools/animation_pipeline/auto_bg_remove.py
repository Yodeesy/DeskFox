"""
Auto Background Removal for Animation Frames

Uses rembg (AI-based) to automatically remove backgrounds from
extracted PNG frames. Reduces manual抠图 work to zero.

Installation:
    pip install rembg

Usage:
    python auto_bg_remove.py extracted_sprites/idle/ output/clean_idle/
    python auto_bg_remove.py extracted_sprites/fishing/ output/clean_fishing/ --threshold 0.5
"""

import os
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def remove_bg_single(input_path: str, output_path: str, threshold: float = 0.5):
    """Remove background from a single image."""
    try:
        from rembg import remove
        from PIL import Image

        with open(input_path, "rb") as f:
            input_data = f.read()

        output_data = remove(input_data, alpha_matting=True,
                            alpha_matting_foreground_threshold=int(threshold * 255))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(output_data)

        return True, input_path
    except ImportError:
        print("ERROR: rembg not installed. Run: pip install rembg")
        sys.exit(1)
    except Exception as e:
        return False, f"{input_path}: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Auto-remove backgrounds from animation frame PNGs using rembg AI"
    )
    parser.add_argument("input_dir", help="Directory containing frame PNGs")
    parser.add_argument("output_dir", help="Output directory for cleaned PNGs")
    parser.add_argument("--threshold", type=float, default=0.5,
                       help="Alpha matting threshold (0.0-1.0, default: 0.5)")
    parser.add_argument("--workers", type=int, default=4,
                       help="Parallel workers (default: 4)")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    if not input_path.is_dir():
        print(f"ERROR: Input directory not found: {args.input_dir}")
        sys.exit(1)

    png_files = sorted(input_path.glob("*.png"))
    if not png_files:
        print(f"No PNG files found in {args.input_dir}")
        sys.exit(1)

    print(f"Processing {len(png_files)} frames with {args.workers} workers...")

    tasks = []
    for png in png_files:
        out_path = os.path.join(args.output_dir, png.name)
        tasks.append((str(png), out_path, args.threshold))

    success_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(remove_bg_single, inp, out, thresh): inp
            for inp, out, thresh in tasks
        }
        for future in as_completed(futures):
            ok, msg = future.result()
            if ok:
                success_count += 1
            else:
                print(f"  FAILED: {msg}")

    print(f"✅ Done. {success_count}/{len(png_files)} frames processed.")
    print(f"   Cleaned frames saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
