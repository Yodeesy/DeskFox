"""Low-level Win32 layered-window management.

Handles creating, positioning, and rendering transparent Pygame windows
via ``UpdateLayeredWindow`` with pre-multiplied alpha blending.
"""

from __future__ import annotations

import ctypes
from ctypes import (
    Structure,
    byref,
    c_byte,
    c_int,
    c_long,
    c_short,
    c_uint,
    c_void_p,
)
from typing import Any, Optional, Tuple

import numpy as np
import pygame
import win32con
import win32gui

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


# --- Windows API structure definitions ---

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class SIZE(Structure):
    _fields_ = [("cx", c_long), ("cy", c_long)]


class BLENDFUNCTION(Structure):
    _fields_ = [
        ("BlendOp", c_byte),
        ("BlendFlags", c_byte),
        ("SourceConstantAlpha", c_byte),
        ("AlphaFormat", c_byte),
    ]


class BITMAPINFO(Structure):
    _fields_ = [
        ("biSize", c_uint),
        ("biWidth", c_int),
        ("biHeight", c_int),
        ("biPlanes", c_short),
        ("biBitCount", c_short),
        ("biCompression", c_uint),
        ("biSizeImage", c_uint),
        ("biXPelsPerMeter", c_long),
        ("biYPelsPerMeter", c_long),
        ("biClrUsed", c_uint),
        ("biClrImportant", c_uint),
    ]


ULW_ALPHA: int = 0x00000002
AC_SRC_OVER: int = 0x00
AC_SRC_ALPHA: int = 0x01


def convert_to_bgra(surface: pygame.Surface) -> bytes:
    """Convert a Pygame RGBA surface to pre-multiplied BGRA bytes.

    ``UpdateLayeredWindow`` requires pre-multiplied alpha in BGRA byte
    order. This function performs the conversion using NumPy for speed.

    Args:
        surface: A ``pygame.Surface`` in RGBA format.

    Returns:
        A byte string ready to be copied into a DIB section.
    """
    rgba_data: bytes = pygame.image.tostring(surface, "RGBA")
    width, height = surface.get_size()

    arr = np.frombuffer(rgba_data, dtype=np.uint8).reshape(height, width, 4)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    a_f = a / 255.0
    r_pre = (r * a_f).astype(np.uint8)
    g_pre = (g * a_f).astype(np.uint8)
    b_pre = (b * a_f).astype(np.uint8)

    bgra = np.dstack([b_pre, g_pre, r_pre, a])
    return bgra.tobytes()


def update_layered_window(
    hwnd: int, surface: pygame.Surface, window_x: int, window_y: int
) -> None:
    """Render *surface* onto the layered window at the given screen position.

    Creates a temporary DIB section, copies the pre-multiplied BGRA pixel
    data into it, and calls ``UpdateLayeredWindow``. All GDI resources are
    cleaned up in a ``finally`` block.

    Args:
        hwnd: Native window handle.
        surface: ``pygame.Surface`` containing the frame to display.
        window_x: Absolute screen X coordinate.
        window_y: Absolute screen Y coordinate.
    """
    width, height = surface.get_size()

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.biSize = ctypes.sizeof(BITMAPINFO)
    bmi.biWidth = width
    bmi.biHeight = -height  # Negative for top-down DIB.
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    ppv_bits = c_void_p()
    hbitmap = gdi32.CreateDIBSection(
        hdc_screen, byref(bmi), 0, byref(ppv_bits), None, 0
    )
    old_bitmap = gdi32.SelectObject(hdc_mem, hbitmap)

    try:
        bgra_data = convert_to_bgra(surface)
        ctypes.memmove(ppv_bits, bgra_data, width * height * 4)

        blend = BLENDFUNCTION()
        blend.BlendOp = AC_SRC_OVER
        blend.SourceConstantAlpha = 255
        blend.AlphaFormat = AC_SRC_ALPHA

        size = SIZE(width, height)
        src = POINT(0, 0)
        dst = POINT(window_x, window_y)

        user32.UpdateLayeredWindow(
            hwnd, hdc_screen, byref(dst), byref(size),
            hdc_mem, byref(src), 0, byref(blend), ULW_ALPHA,
        )
    finally:
        gdi32.SelectObject(hdc_mem, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)


def setup_layered_window(
    hwnd: int, width: int, height: int, start_x: int, start_y: int
) -> None:
    """Configure a window as layered, borderless, and top-most.

    Sets the extended window style to ``WS_EX_LAYERED | WS_EX_TOPMOST |
    WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE``, removes ``WS_EX_TRANSPARENT``
    so the window can receive clicks, and positions it at the given
    coordinates.

    Args:
        hwnd: Native window handle.
        width: Desired window width in pixels.
        height: Desired window height in pixels.
        start_x: Initial screen X position.
        start_y: Initial screen Y position.
    """
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

    new_ex_style = (
        ex_style
        | win32con.WS_EX_LAYERED
        | win32con.WS_EX_TOPMOST
        | win32con.WS_EX_TOOLWINDOW
        | win32con.WS_EX_NOACTIVATE
    )
    new_ex_style &= ~win32con.WS_EX_TRANSPARENT

    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)

    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        start_x, start_y,
        width, height,
        win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE,
    )


def get_mouse_screen_pos() -> Tuple[int, int]:
    """Return the absolute screen coordinates of the mouse cursor.

    Returns:
        A ``(x, y)`` tuple in screen coordinates.
    """
    point = POINT()
    user32.GetCursorPos(byref(point))
    return (point.x, point.y)


def set_window_position(
    hwnd: int, x: int, y: int, width: int, height: int,
    is_topmost: bool = False,
) -> None:
    """Move (but not resize) the window to a new screen position.

    Args:
        hwnd: Native window handle.
        x: New screen X coordinate.
        y: New screen Y coordinate.
        width: Current window width (required by SetWindowPos, not changed).
        height: Current window height (required by SetWindowPos, not changed).
        is_topmost: If True, also set ``HWND_TOPMOST`` Z-order.
    """
    flags = win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
    z_order = win32con.HWND_TOPMOST if is_topmost else 0

    win32gui.SetWindowPos(
        hwnd, z_order,
        x, y, width, height,
        flags | win32con.SWP_NOSIZE,
    )


class LayeredWindowRenderer:
    """Caches GDI resources across frames to avoid per-frame allocation.

    Creates the screen DC, memory DC, and DIB section once and reuses them
    until the surface dimensions change. Also pre-allocates the BGRA output
    buffer for ``convert_to_bgra``.
    """

    def __init__(self) -> None:
        self._hdc_screen: Optional[int] = None
        self._hdc_mem: Optional[int] = None
        self._hbitmap: Optional[int] = None
        self._ppv_bits: Any = None
        self._old_bitmap: Optional[int] = None
        self._cached_width: int = 0
        self._cached_height: int = 0
        self._bgra_out: Any = None

    def _ensure_resources(self, width: int, height: int) -> None:
        """Re/create GDI resources only when dimensions change.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
        """
        if width == self._cached_width and height == self._cached_height:
            return

        self._release_resources()

        self._hdc_screen = user32.GetDC(0)
        self._hdc_mem = gdi32.CreateCompatibleDC(self._hdc_screen)

        bmi = BITMAPINFO()
        bmi.biSize = ctypes.sizeof(BITMAPINFO)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        ppv_bits = c_void_p()
        self._hbitmap = gdi32.CreateDIBSection(
            self._hdc_screen, byref(bmi), 0, byref(ppv_bits), None, 0,
        )
        self._ppv_bits = ppv_bits
        self._old_bitmap = gdi32.SelectObject(self._hdc_mem, self._hbitmap)

        self._cached_width = width
        self._cached_height = height
        self._bgra_out = np.empty((height, width, 4), dtype=np.uint8)

    def _release_resources(self) -> None:
        """Release all cached GDI resources."""
        if self._old_bitmap is not None and self._hdc_mem is not None:
            gdi32.SelectObject(self._hdc_mem, self._old_bitmap)
            self._old_bitmap = None
        if self._hbitmap is not None:
            gdi32.DeleteObject(self._hbitmap)
            self._hbitmap = None
        if self._hdc_mem is not None:
            gdi32.DeleteDC(self._hdc_mem)
            self._hdc_mem = None
        if self._hdc_screen is not None:
            user32.ReleaseDC(0, self._hdc_screen)
            self._hdc_screen = None
        self._cached_width = 0
        self._cached_height = 0
        self._bgra_out = None

    def _convert_to_bgra(self, surface: pygame.Surface) -> bytes:
        """Convert RGBA surface to pre-multiplied BGRA bytes.

        Uses the pre-allocated ``_bgra_out`` buffer to avoid per-frame
        allocations.

        Args:
            surface: The Pygame surface to convert.

        Returns:
            A bytes buffer ready for ``UpdateLayeredWindow``.
        """
        rgba_data: bytes = pygame.image.tostring(surface, "RGBA")
        width, height = surface.get_size()

        arr = np.frombuffer(rgba_data, dtype=np.uint8).reshape(height, width, 4)
        r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
        a_f = a / 255.0

        self._bgra_out[..., 0] = (b * a_f).astype(np.uint8)
        self._bgra_out[..., 1] = (g * a_f).astype(np.uint8)
        self._bgra_out[..., 2] = (r * a_f).astype(np.uint8)
        self._bgra_out[..., 3] = a

        return self._bgra_out.tobytes()

    def render(
        self,
        hwnd: int,
        surface: pygame.Surface,
        window_x: int,
        window_y: int,
    ) -> None:
        """Render *surface* onto the layered window.

        Args:
            hwnd: Native window handle.
            surface: ``pygame.Surface`` containing the frame to display.
            window_x: Absolute screen X coordinate.
            window_y: Absolute screen Y coordinate.
        """
        width, height = surface.get_size()
        self._ensure_resources(width, height)

        bgra_data: bytes = self._convert_to_bgra(surface)
        ctypes.memmove(self._ppv_bits, bgra_data, width * height * 4)

        blend = BLENDFUNCTION()
        blend.BlendOp = AC_SRC_OVER
        blend.SourceConstantAlpha = 255
        blend.AlphaFormat = AC_SRC_ALPHA

        size = SIZE(width, height)
        src = POINT(0, 0)
        dst = POINT(window_x, window_y)

        user32.UpdateLayeredWindow(
            hwnd, self._hdc_screen, byref(dst), byref(size),
            self._hdc_mem, byref(src), 0, byref(blend), ULW_ALPHA,
        )

    def destroy(self) -> None:
        """Release all GDI resources. Call before shutdown."""
        self._release_resources()
