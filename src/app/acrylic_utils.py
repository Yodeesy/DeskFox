"""Shared Windows DWM acrylic effect utility for CTkToplevel windows.

Provides constants and helper methods to apply frosted-glass backgrounds
to CustomTkinter popup windows on Windows 10/11.
"""

from __future__ import annotations

import ctypes

# DWM (Desktop Window Manager) effect constants.
DWM_EC_ENABLE_ACRYLIC: int = 3
WCA_ACCENT_POLICY: int = 19
DWMWA_USE_IMMERSIVE_DARK_MODE: int = 20

# Fox-theme color palette shared across settings and story windows.
ACCENT_ORANGE: str = "#e67e22"
ACCENT_ORANGE_HOVER: str = "#d35400"
CARD_BG: tuple[str, str] = ("gray18", "gray14")
CARD_BORDER: tuple[str, str] = ("gray28", "gray24")
TEXT_PRIMARY: tuple[str, str] = ("gray90", "gray95")
TEXT_SECONDARY: tuple[str, str] = ("gray60", "gray65")


def force_render_fix(window: object) -> None:
    """Force a render pass to ensure all CTK widgets are painted.

    Should be called shortly after widget creation and again after the
    acrylic effect is applied.

    Args:
        window: A ``ctk.CTkToplevel`` instance.
    """
    try:
        window.update_idletasks()
        window.update()
        window.event_generate("<Configure>")
    except Exception:
        pass


def apply_acrylic_effect(window: object) -> None:
    """Attempt to apply Windows 10/11 acrylic blur to a CTkToplevel.

    Best-effort cosmetic enhancement. Failures (e.g. on older Windows
    versions) are silently ignored.

    ``fg_color="transparent"`` must be set on the window BEFORE widget
    creation to avoid the white-screen bug on certain GPU/driver combos.

    Args:
        window: A ``ctk.CTkToplevel`` instance with transparent fg_color.
    """
    class MARGINS(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth", ctypes.c_int),
            ("cxRightWidth", ctypes.c_int),
            ("cyTopHeight", ctypes.c_int),
            ("cyBottomHeight", ctypes.c_int),
        ]

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_int),
            ("AnimationId", ctypes.c_int),
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENT_POLICY)),
            ("SizeOfData", ctypes.c_size_t),
        ]

    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        # Extend the DWM frame into the entire client area.
        margins = MARGINS(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
            hwnd, ctypes.byref(margins)
        )

        # Configure the acrylic accent policy.
        policy = ACCENT_POLICY()
        policy.AccentState = DWM_EC_ENABLE_ACRYLIC
        policy.AccentFlags = 0
        policy.GradientColor = 0x01FFFFFF

        wca_data = WINDOWCOMPOSITIONATTRIBDATA()
        wca_data.Attribute = WCA_ACCENT_POLICY
        wca_data.SizeOfData = ctypes.sizeof(policy)
        wca_data.Data = ctypes.pointer(policy)

        ctypes.windll.user32.SetWindowCompositionAttribute(
            hwnd, wca_data
        )

        # Enable dark mode for a more modern acrylic appearance.
        try:
            dark_mode = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode), ctypes.sizeof(ctypes.c_int),
            )
        except Exception:
            pass

    except Exception:
        pass

    # Force repaint after DWM changes.
    window.after(50, lambda: force_render_fix(window))
