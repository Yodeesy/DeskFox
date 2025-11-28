# window_manager.py

import ctypes
from ctypes import Structure, c_short, c_long, c_byte, c_uint, c_int, byref, c_void_p
import numpy as np
import pygame
import win32con
import win32gui

# === Windows API References ===
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# === Windows API Structures Definitions ===
class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class SIZE(Structure):
    _fields_ = [("cx", c_long), ("cy", c_long)]


class BLENDFUNCTION(Structure):
    _fields_ = [("BlendOp", c_byte), ("BlendFlags", c_byte), ("SourceConstantAlpha", c_byte), ("AlphaFormat", c_byte)]


class BITMAPINFO(Structure):
    _fields_ = [
        ("biSize", c_uint), ("biWidth", c_int), ("biHeight", c_int),
        ("biPlanes", c_short), ("biBitCount", c_short), ("biCompression", c_uint),
        ("biSizeImage", c_uint), ("biXPelsPerMeter", c_long), ("biYPelsPerMeter", c_long),
        ("biClrUsed", c_uint), ("biClrImportant", c_uint)
    ]


# === Windows API Constants ===
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01


def convert_to_bgra(surface):
    """
    Converts a Pygame Surface to BGRA byte data with pre-multiplied alpha,
    which is required for UpdateLayeredWindow.
    """
    rgba_data = pygame.image.tostring(surface, "RGBA")
    width, height = surface.get_size()

    # Convert RGBA data to a NumPy array
    arr = np.frombuffer(rgba_data, dtype=np.uint8).reshape(height, width, 4)

    # Separate R, G, B, A channels
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    # Critical: Pre-multiplied Alpha
    a_f = a / 255.0
    r_pre = (r * a_f).astype(np.uint8)
    g_pre = (g * a_f).astype(np.uint8)
    b_pre = (b * a_f).astype(np.uint8)

    # Re-stack into BGRA order
    bgra = np.dstack([b_pre, g_pre, r_pre, a])

    return bgra.tobytes()


def update_layered_window(hwnd, surface, window_x, window_y):
    """
    Updates the content and position of the layered window using UpdateLayeredWindow.
    - hwnd: Window handle
    - surface: Pygame Surface object
    - window_x, window_y: Absolute screen coordinates of the window
    """
    width, height = surface.get_size()

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.biSize = ctypes.sizeof(BITMAPINFO)
    bmi.biWidth = width
    bmi.biHeight = -height  # Negative height for top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    ppv_bits = c_void_p()
    # Create DIB Section
    hbitmap = gdi32.CreateDIBSection(hdc_screen, byref(bmi), 0, byref(ppv_bits), None, 0)
    old_bitmap = gdi32.SelectObject(hdc_mem, hbitmap)

    try:
        # 1. Prepare BGRA data
        bgra_data = convert_to_bgra(surface)

        # 2. Copy data to DIB Section
        ctypes.memmove(ppv_bits, bgra_data, width * height * 4)

        # 3. Prepare Blend Function
        blend = BLENDFUNCTION()
        blend.BlendOp = AC_SRC_OVER
        blend.SourceConstantAlpha = 255
        blend.AlphaFormat = AC_SRC_ALPHA

        # 4. Prepare size and position
        size = SIZE(width, height)
        src = POINT(0, 0)  # Starting point in the source DC
        dst = POINT(window_x, window_y)  # Destination point on screen

        # 5. Call the core Win32 function
        user32.UpdateLayeredWindow(
            hwnd, hdc_screen, byref(dst), byref(size),
            hdc_mem, byref(src), 0, byref(blend), ULW_ALPHA
        )

    finally:
        # Cleanup GDI objects
        gdi32.SelectObject(hdc_mem, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)


def setup_layered_window(hwnd, width, height, start_x, start_y):
    """
    Sets the window style for a layered, borderless, topmost, transparent window.
    """
    # === Modify Window Extended Style ===
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

    # Flags for layering, topmost, no taskbar entry, and no activation
    new_ex_style = (ex_style
                    | win32con.WS_EX_LAYERED
                    | win32con.WS_EX_TOPMOST
                    | win32con.WS_EX_TOOLWINDOW
                    | win32con.WS_EX_NOACTIVATE)

    # Ensure window can receive click events (by removing WS_EX_TRANSPARENT)
    new_ex_style &= ~win32con.WS_EX_TRANSPARENT

    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)

    # Set initial window position
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,  # Ensures Z-order is on top
        start_x, start_y,
        width, height,
        win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
    )
    print("✅ Desktop pet window configured: Always on top, transparent background, hidden from taskbar")


def get_mouse_screen_pos():
    """Retrieves the absolute screen coordinates of the mouse cursor."""
    point = POINT()
    user32.GetCursorPos(byref(point))
    return (point.x, point.y)


def set_window_position(hwnd, x, y, width, height, is_topmost=False):
    """
    Sets the window position and size.
    """
    flags = win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW

    if is_topmost:
        z_order = win32con.HWND_TOPMOST
    else:
        z_order = 0  # Maintain current Z-order

    win32gui.SetWindowPos(
        hwnd,
        z_order,
        x, y,
        width, height,
        flags | win32con.SWP_NOSIZE
    )