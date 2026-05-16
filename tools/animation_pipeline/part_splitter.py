"""
Interactive Part Splitter — Split a character image into body parts.

Usage:
    python part_splitter.py assets/fox_clean.png -o my_animations/fox/parts/
"""

import os, sys, json, argparse
import pygame

# Presets for a fox-eared humanoid character
DEFAULT_PARTS = [
    "head",
    "left_ear",
    "right_ear",
    "body",
    "left_arm",
    "right_arm",
    "left_hand",
    "right_hand",
    "left_leg",
    "right_leg",
    "tail",
]

COLORS = [
    (255, 80, 80), (80, 180, 255), (80, 255, 120), (255, 220, 60),
    (220, 120, 255), (255, 140, 60), (60, 220, 220), (255, 120, 180),
    (180, 220, 80), (255, 200, 100), (160, 140, 255),
]

FONT_SIZE = 16


def run_splitter(image_path: str, output_dir: str):
    pygame.init()

    screen_info = pygame.display.Info()
    max_display_h = int(screen_info.current_h * 0.82)

    img_raw = pygame.image.load(image_path)
    img_w, img_h = img_raw.get_size()

    scale = 1.0
    if img_h > max_display_h:
        scale = max_display_h / img_h
        display_w = int(img_w * scale)
        display_h = int(img_h * scale)
    else:
        display_w = img_w
        display_h = img_h

    sidebar_w = 260
    win_w = display_w + sidebar_w
    win_h = max(display_h, 600)
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption("Part Splitter — 左键框选 / 中键拖拽已有区域 / 右键取消")

    img = img_raw.convert_alpha()
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont("microsoftyahei", FONT_SIZE)
        small = pygame.font.SysFont("microsoftyahei", 13)
    except Exception:
        font = pygame.font.Font(None, FONT_SIZE)
        small = pygame.font.Font(None, 14)

    # State
    parts = {}          # name -> (x, y, w, h)
    parts_list = list(DEFAULT_PARTS)
    cur_idx = 0
    dragging = False
    drag_start = (0, 0)
    drag_end = (0, 0)
    hovered_part = None
    moving_part = None
    move_offset = (0, 0)
    show_gaps = False
    running = True
    msg = "TAB: 切换部件 | 左键拖拽框选 | 中键拖拽移动 | S: 保存 | G: 显示缝隙 | R: 重置"
    msg_timer = 0

    while running:
        mx, my = pygame.mouse.get_pos()
        img_x = max(0, (display_w - int(img_w * scale)) // 2)
        img_y = 0

        ix = (mx - img_x) / scale
        iy = (my - img_y) / scale

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    cur_idx = (cur_idx + 1) % len(parts_list)
                    msg = f"当前部件 [{cur_idx + 1}/{len(parts_list)}]: {parts_list[cur_idx]}"
                    msg_timer = 180
                elif event.key == pygame.K_s:
                    save_parts(parts, parts_list, img, output_dir, show_gaps)
                    msg = f"已保存 {len(parts)} 个部件到 {output_dir}/"
                    msg_timer = 180
                elif event.key == pygame.K_d:
                    if hovered_part and hovered_part in parts:
                        del parts[hovered_part]
                        msg = f"已删除: {hovered_part}"
                        msg_timer = 60
                elif event.key == pygame.K_r:
                    parts.clear()
                    cur_idx = 0
                    msg = "已清除所有框选"
                    msg_timer = 60
                elif event.key == pygame.K_g:
                    show_gaps = not show_gaps
                    msg = "缝隙预览: 开 (红色区域=未被任何部件覆盖)" if show_gaps else "缝隙预览: 关"
                    msg_timer = 120

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left — start new rect
                    # Check if clicking on existing rect to move
                    hit = None
                    for name, (px, py, pw, ph) in parts.items():
                        rx = img_x + px * scale
                        ry = img_y + py * scale
                        if rx <= mx <= rx + pw * scale and ry <= my <= ry + ph * scale:
                            hit = name
                            break
                    if hit:
                        moving_part = hit
                        px, py, pw, ph = parts[hit]
                        move_offset = (ix - px, iy - py)
                    else:
                        dragging = True
                        drag_start = (ix, iy)
                        drag_end = (ix, iy)

                elif event.button == 2:  # Middle — also move
                    hit = None
                    for name, (px, py, pw, ph) in parts.items():
                        rx = img_x + px * scale
                        ry = img_y + py * scale
                        if rx <= mx <= rx + pw * scale and ry <= my <= ry + ph * scale:
                            hit = name
                            break
                    if hit:
                        moving_part = hit
                        px, py, pw, ph = parts[hit]
                        move_offset = (ix - px, iy - py)

                elif event.button == 3:  # Right — cancel
                    dragging = False
                    moving_part = None

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2) and dragging:
                    dragging = False
                    x1, y1 = drag_start
                    x2, y2 = drag_end
                    rx, ry = int(min(x1, x2)), int(min(y1, y2))
                    rw, rh = int(abs(x2 - x1)), int(abs(y2 - y1))
                    if rw > 8 and rh > 8:
                        name = parts_list[cur_idx]
                        parts[name] = (rx, ry, rw, rh)
                        cur_idx = (cur_idx + 1) % len(parts_list)
                        msg = f"已选: {name} → 下一个: {parts_list[cur_idx]}"
                        msg_timer = 180
                if event.button in (1, 2) and moving_part:
                    name = moving_part
                    px, py, pw, ph = parts[name]
                    px = max(0, min(int(px), img_w - pw))
                    py = max(0, min(int(py), img_h - ph))
                    parts[name] = (px, py, pw, ph)
                    moving_part = None

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    drag_end = (max(0, min(int(ix), img_w)), max(0, min(int(iy), img_h)))
                if moving_part:
                    px, py, pw, ph = parts[moving_part]
                    nx = int(ix - move_offset[0])
                    ny = int(iy - move_offset[1])
                    parts[moving_part] = (nx, ny, pw, ph)

        # --- Draw ---
        screen.fill((40, 40, 44))

        # Transparency checkerboard
        for cy in range(0, display_h, 16):
            for cx in range(0, display_w, 16):
                c = (180, 180, 180) if ((cx // 16) + (cy // 16)) % 2 == 0 else (140, 140, 140)
                pygame.draw.rect(screen, c, (cx, cy, 16, 16))

        scaled_img = pygame.transform.smoothscale(img, (int(img_w * scale), int(img_h * scale)))
        screen.blit(scaled_img, (img_x, img_y))

        # Gap overlay
        if show_gaps and parts:
            gap_surf = pygame.Surface((int(img_w * scale), int(img_h * scale)), pygame.SRCALPHA)
            uncovered = find_uncovered_pixels(img, parts)
            for (px, py) in uncovered:
                sx = int(px * scale)
                sy = int(py * scale)
                gap_surf.fill((255, 0, 0, 100), (sx, sy, max(1, int(scale)), max(1, int(scale))))
            screen.blit(gap_surf, (img_x, img_y))

        # Draw saved part rects
        hovered_part = None
        for name, (px, py, pw, ph) in parts.items():
            rx, ry = img_x + px * scale, img_y + py * scale
            rw, rh = pw * scale, ph * scale
            c_idx = parts_list.index(name) % len(COLORS) if name in parts_list else 0
            color = COLORS[c_idx]
            rect = pygame.Rect(rx, ry, rw, rh)
            if rect.collidepoint(mx, my):
                hovered_part = name
                pygame.draw.rect(screen, (255, 255, 255), rect, 3)
            else:
                pygame.draw.rect(screen, color, rect, 2)
            lbl = small.render(name, True, color)
            ly = ry - 16 if ry > 16 else ry + rh + 2
            screen.blit(lbl, (rx + 2, ly))

        # Drag preview
        if dragging:
            x1, y1 = drag_start
            x2, y2 = drag_end
            rx = min(x1, x2) * scale + img_x
            ry = min(y1, y2) * scale + img_y
            rw = abs(x2 - x1) * scale
            rh = abs(y2 - y1) * scale
            pygame.draw.rect(screen, (255, 255, 0), (rx, ry, rw, rh), 2)

        # --- Sidebar ---
        sx = display_w + 12
        sy = 8

        screen.blit(font.render("Parts", True, (255, 255, 255)), (sx, sy))
        sy += 24

        for i, name in enumerate(parts_list):
            color = COLORS[i % len(COLORS)]
            marker = "»" if i == cur_idx else " "
            done = "✓" if name in parts else " "
            t = small.render(f"{marker} [{done}] {name}", True, color)
            screen.blit(t, (sx, sy))
            sy += 17

        sy += 14
        screen.blit(font.render("Controls", True, (180, 180, 180)), (sx, sy))
        sy += 20
        for line in [
            "TAB — 切换下一个部件",
            "左键拖拽 — 框选区域",
            "左/中键拖拽框 — 移动",
            "右键 — 取消操作",
            "D — 删除悬停框",
            "G — 缝隙预览 (红色)",
            "S — 保存所有部件",
            "R — 清除全部",
            "ESC — 退出",
        ]:
            t = small.render(line, True, (150, 150, 150))
            screen.blit(t, (sx, sy))
            sy += 16

        sy += 14
        covered_pct = coverage_pct(img, parts)
        screen.blit(font.render(f"覆盖率: {covered_pct:.0f}%", True,
                                (100, 255, 100) if covered_pct > 90 else (255, 200, 60)), (sx, sy))
        sy += 22
        screen.blit(small.render("缝隙 = 部件移动后", True, (200, 160, 100)), (sx, sy))
        screen.blit(small.render("暴露的空白区域", True, (200, 160, 100)), (sx, sy + 15))
        screen.blit(small.render("需后期补绘/修复", True, (200, 160, 100)), (sx, sy + 30))

        # Message bar
        if msg_timer > 0:
            msg_timer -= 1
        t = small.render(msg, True, (255, 255, 100))
        screen.blit(t, (8, win_h - 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def find_uncovered_pixels(img: pygame.Surface, parts: dict) -> list:
    """Find pixels not covered by any part rect. Sampled for performance."""
    w, h = img.get_size()
    uncovered = []
    step = max(2, min(w, h) // 128)  # Sample every N pixels
    for y in range(0, h, step):
        for x in range(0, w, step):
            # Check if pixel has any alpha
            if img.get_at((x, y)).a > 0:
                covered = False
                for (px, py, pw, ph) in parts.values():
                    if px <= x < px + pw and py <= y < py + ph:
                        covered = True
                        break
                if not covered:
                    uncovered.append((x, y))
    return uncovered


def coverage_pct(img: pygame.Surface, parts: dict) -> float:
    """Percentage of non-transparent pixels covered by parts."""
    w, h = img.get_size()
    total_opaque = 0
    covered_opaque = 0
    step = max(2, min(w, h) // 128)
    for y in range(0, h, step):
        for x in range(0, w, step):
            if img.get_at((x, y)).a > 0:
                total_opaque += 1
                for (px, py, pw, ph) in parts.values():
                    if px <= x < px + pw and py <= y < py + ph:
                        covered_opaque += 1
                        break
    return (covered_opaque / total_opaque * 100) if total_opaque > 0 else 0


def save_parts(parts: dict, parts_list: list, img: pygame.Surface,
               output_dir: str, show_gaps: bool = False):
    """Crop and save each part, plus a gap diagnostic image."""
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    for name in parts_list:
        if name not in parts:
            continue
        px, py, pw, ph = parts[name]
        cropped = pygame.Surface((pw, ph), pygame.SRCALPHA)
        cropped.blit(img, (0, 0), (px, py, pw, ph))
        path = os.path.join(output_dir, f"{name}.png")
        pygame.image.save(cropped, path)
        saved.append(name)

    # Gap diagnostic image
    uncovered = find_uncovered_pixels(img, parts)
    gap_img = img.copy()
    for (px, py) in uncovered:
        gap_img.set_at((px, py), (255, 0, 0, 255))
    gap_path = os.path.join(output_dir, "_gaps.png")
    pygame.image.save(gap_img, gap_path)

    # Manifest
    manifest = {
        "source_size": list(img.get_size()),
        "parts": {n: list(parts[n]) for n in saved},
        "uncovered_pixels_sample": len(uncovered),
        "coverage_pct": round(coverage_pct(img, parts), 1),
    }
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Saved {len(saved)} parts to {output_dir}/")
    for n in saved:
        print(f"  {n}.png  rect={parts[n]}")
    print(f"\n  _gaps.png  — 红色=未被覆盖的像素 (部件移动后会暴露)")
    print(f"  manifest.json — 部件坐标信息")
    print(f"  覆盖率: {manifest['coverage_pct']:.1f}%")
    print(f"\nTIP: 覆盖率 < 100% 是正常的 (部件间缝隙)。")
    print(f"      移动部件后暴露的空白区域需后期补绘/修复。")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Split character image into body parts")
    parser.add_argument("image", help="Path to character PNG (transparent bg)")
    parser.add_argument("-o", "--output", default=None,
                      help="Output dir (default: <image>_parts/)")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: {args.image} not found")
        sys.exit(1)

    output_dir = args.output or os.path.splitext(args.image)[0] + "_parts"
    run_splitter(args.image, output_dir)


if __name__ == "__main__":
    main()
