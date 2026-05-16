"""Visual effect system for the desktop pet.

Provides rain and meteor-shower particle effects used during the Magic/Rest
state.  Each effect controller pre-renders its particle template and dark
overlay once, then reuses them across all particles for performance.
"""

from __future__ import annotations

import random

import pygame


class Raindrop:
    """A single rain particle that falls downward and recycles off-screen."""

    def __init__(
        self, screen_w: int, screen_h: int,
        template: pygame.Surface,
    ) -> None:
        """Create a raindrop particle.

        Args:
            screen_w: Full screen width in pixels.
            screen_h: Full screen height in pixels.
            template: Pre-rendered raindrop surface shared by all drops.
        """
        self.screen_w: int = screen_w
        self.screen_h: int = screen_h
        self._template: pygame.Surface = template
        self.reset()

    def reset(self) -> None:
        """Reset the drop to a random position above the screen boundary."""
        self.x: int = random.randint(0, self.screen_w)
        self.y: float = float(random.randint(-self.screen_h * 2, 0))
        self.speed: float = float(random.randint(10, 25))

    def update(self) -> None:
        """Move the drop downward; recycle it when it leaves the screen."""
        self.y += self.speed
        if self.y > self.screen_h + 60:
            self.reset()
            self.speed = float(random.randint(10, 25))

    def draw(self, surface: pygame.Surface) -> None:
        """Blit the pre-rendered raindrop template onto *surface*."""
        surface.blit(self._template, (self.x, int(self.y)))


class DynamicEffectController:
    """Manages a collection of raindrops and renders them every frame.

    Uses a pre-rendered raindrop texture and a downscaled dark overlay
    to minimise per-frame draw calls and memory.
    """

    # Pre-rendered raindrop texture dimensions.
    DROP_TEMPLATE_W: int = 4
    DROP_TEMPLATE_H: int = 60
    # Dark overlay downscale factor (1 = full resolution).
    OVERLAY_SCALE: int = 4

    def __init__(
        self, screen_w: int, screen_h: int, count: int = 300,
    ) -> None:
        """Create a rain effect controller with *count* raindrop particles.

        Args:
            screen_w: Full screen width in pixels.
            screen_h: Full screen height in pixels.
            count: Number of raindrop particles to spawn (default 300).
        """
        self.screen_w: int = screen_w
        self.screen_h: int = screen_h

        # Pre-render a single raindrop texture (light blue gradient line).
        self._drop_template: pygame.Surface = pygame.Surface(
            (self.DROP_TEMPLATE_W, self.DROP_TEMPLATE_H), pygame.SRCALPHA,
        )
        self._drop_template.fill((0, 0, 0, 0))
        for i in range(self.DROP_TEMPLATE_H):
            alpha: int = max(0, 200 - i * 3)
            pygame.draw.line(
                self._drop_template,
                (200, 200, 255, alpha),
                (self.DROP_TEMPLATE_W // 2, i),
                (self.DROP_TEMPLATE_W // 2, i),
                1,
            )

        self.drops: list[Raindrop] = [
            Raindrop(screen_w, screen_h, self._drop_template)
            for _ in range(count)
        ]

        # Dark overlay at reduced resolution.
        overlay_w: int = max(1, screen_w // self.OVERLAY_SCALE)
        overlay_h: int = max(1, screen_h // self.OVERLAY_SCALE)
        small_overlay: pygame.Surface = pygame.Surface(
            (overlay_w, overlay_h), pygame.SRCALPHA,
        )
        small_overlay.fill((0, 0, 0, 30))
        self.dark_overlay: pygame.Surface = pygame.transform.scale(
            small_overlay, (screen_w, screen_h),
        )

    def update_and_draw(self, surface: pygame.Surface) -> None:
        """Update all drops and composite them onto *surface*.

        A dark overlay is drawn first to create an atmospheric dimming
        effect behind the rain particles.
        """
        surface.blit(self.dark_overlay, (0, 0))

        for drop in self.drops:
            drop.update()
            drop.draw(surface)


class Meteor:
    """A single meteor particle that streaks diagonally and recycles off-screen.

    Each meteor picks one of several pre-rendered templates (short / medium /
    long trail, slightly different angles), so the shower looks more natural.
    Movement is down-left, radiating from a point above-right of the screen.
    """

    def __init__(
        self, screen_w: int, screen_h: int,
        templates: list[pygame.Surface],
        angles: list[tuple[float, float]],
    ) -> None:
        """Create a meteor particle.

        Args:
            screen_w: Full screen width in pixels.
            screen_h: Full screen height in pixels.
            templates: Pre-rendered meteor trail surfaces (variant lengths).
            angles: (cos, sin) direction tuples matching each template variant.
        """
        self.screen_w: int = screen_w
        self.screen_h: int = screen_h
        self._templates: list[pygame.Surface] = templates
        self._angles: list[tuple[float, float]] = angles
        self._template: pygame.Surface = templates[0]  # set in reset()
        self._cos: float = angles[0][0]
        self._sin: float = angles[0][1]
        self.reset()

    def reset(self) -> None:
        """Randomise position, template variant, and speed."""
        idx: int = random.randint(0, len(self._templates) - 1)
        self._template = self._templates[idx]
        self._cos, self._sin = self._angles[idx]

        self.x: float = float(
            random.randint(0, self.screen_w + self.screen_w // 2),
        )
        self.y: float = float(random.randint(-self.screen_h, -20))
        base: float = float(random.randint(8, 18))
        self.speed_x: float = -base * self._sin
        self.speed_y: float = base * self._cos

    def update(self) -> None:
        """Advance the meteor; recycle when it leaves the screen."""
        self.x += self.speed_x
        self.y += self.speed_y
        if self.y > self.screen_h + 160 or self.x < -300:
            self.reset()

    def draw(self, surface: pygame.Surface) -> None:
        """Blit the pre-rendered meteor template onto *surface*."""
        surface.blit(self._template, (int(self.x), int(self.y)))


class MeteorEffectController:
    """Manages a meteor-shower particle system and renders it every frame.

    Pre-renders several tapered streak templates (varied length and angle)
    with a bright white head that fades to warm amber — the classic
    shooting-star look.  A downscaled dark overlay helps the bright streaks
    read against light desktop backgrounds.
    """

    # Trail lengths and corresponding angles (degrees from vertical).
    _VARIANTS: list[tuple[int, float]] = [
        (60, 18.0),   # short, shallow
        (90, 23.0),   # medium, medium angle
        (130, 28.0),  # long, steeper
    ]
    # Template base height before rotation (enough for taper + head glow).
    _TRAIL_H: int = 12
    # Dark overlay downscale factor (1 = full resolution).
    OVERLAY_SCALE: int = 4

    def __init__(
        self, screen_w: int, screen_h: int, count: int = 100,
    ) -> None:
        """Create a meteor shower controller with *count* meteor particles.

        Args:
            screen_w: Full screen width in pixels.
            screen_h: Full screen height in pixels.
            count: Number of meteor particles to spawn (default 100).
        """
        self.screen_w: int = screen_w
        self.screen_h: int = screen_h

        # Build one tapered, glowing template per variant.
        self._templates: list[pygame.Surface] = []
        self._angles: list[tuple[float, float]] = []

        import math as _math
        for trail_len, angle_deg in self._VARIANTS:
            rad: float = _math.radians(angle_deg)
            self._angles.append((_math.cos(rad), _math.sin(rad)))

            raw: pygame.Surface = pygame.Surface(
                (trail_len, self._TRAIL_H), pygame.SRCALPHA,
            )
            raw.fill((0, 0, 0, 0))
            half_h: int = self._TRAIL_H // 2

            # Tapered trail: wide bright head → thin warm tail.
            for x in range(trail_len):
                t: float = x / trail_len  # 0=head, 1=tail
                # Exponential fade — trail vanishes quickly.
                alpha: int = int(255 * (1.0 - t) ** 1.8)
                if alpha <= 0:
                    continue
                # Bright white head → warm amber tail.
                r: int = 255
                g: int = int(255 * (1.0 - t * 0.45))
                b: int = int(200 * (1.0 - t * 0.65))
                # Width tapers from 5 px (head) to 1 px (tail).
                width: int = max(1, int(5 * (1.0 - t) + 1))
                start_y: int = half_h - width // 2
                for y_off in range(width):
                    raw.set_at((x, start_y + y_off), (r, g, b, alpha))

            # Bright head glow (small radial gradient).
            glow_r: int = 4
            for dx in range(-glow_r, glow_r + 1):
                for dy in range(-glow_r, glow_r + 1):
                    dist: float = (dx * dx + dy * dy) ** 0.5
                    if dist > glow_r:
                        continue
                    glow_a: int = int(200 * (1.0 - dist / glow_r))
                    px: int = dx
                    py: int = half_h + dy
                    if 0 <= px < trail_len and 0 <= py < self._TRAIL_H:
                        existing: tuple = raw.get_at((px, py))
                        new_a: int = min(255, existing[3] + glow_a)
                        raw.set_at((px, py), (255, 255, 240, new_a))

            self._templates.append(
                pygame.transform.rotate(raw, angle_deg),
            )

        self.meteors: list[Meteor] = [
            Meteor(screen_w, screen_h, self._templates, self._angles)
            for _ in range(count)
        ]

        # Dark overlay at reduced resolution.
        overlay_w: int = max(1, screen_w // self.OVERLAY_SCALE)
        overlay_h: int = max(1, screen_h // self.OVERLAY_SCALE)
        small_overlay: pygame.Surface = pygame.Surface(
            (overlay_w, overlay_h), pygame.SRCALPHA,
        )
        small_overlay.fill((0, 0, 0, 30))
        self.dark_overlay: pygame.Surface = pygame.transform.scale(
            small_overlay, (screen_w, screen_h),
        )

    def update_and_draw(self, surface: pygame.Surface) -> None:
        """Update all meteors and composite them onto *surface*.

        A dark overlay is drawn first to make the bright meteor streaks
        visible against the desktop background.
        """
        surface.blit(self.dark_overlay, (0, 0))

        for meteor in self.meteors:
            meteor.update()
            meteor.draw(surface)
