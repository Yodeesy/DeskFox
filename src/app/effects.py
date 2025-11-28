# effects.py
import pygame
import random


class Raindrop:
    """Represents a single particle in a rain effect."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.reset()

    def reset(self):
        """Resets the raindrop's position and attributes for recycling."""
        self.x = random.randint(0, self.screen_w)
        # Start from above the screen
        self.y = random.randint(-self.screen_h * 2, 0)
        self.length = random.randint(20, 50)
        self.speed = random.randint(10, 25)
        # Ensure alpha for visibility
        alpha = random.randint(150, 200)
        self.color = (200, 200, 255, alpha)

    def update(self):
        """Moves the raindrop downwards."""
        self.y += self.speed
        if self.y > self.screen_h + self.length:
            # Recycle the raindrop when it moves off-screen
            self.reset()
            # Adjust speed and length slightly for variation upon reset
            self.speed = random.randint(10, 25)
            self.length = random.randint(20, 50)

    def draw(self, surface):
        """Draws the raindrop line onto the given surface."""
        # Draw line from (x, y) to (x, y + length)
        # We use int() cast for coordinates as draw functions often require them
        pygame.draw.line(surface, self.color, (self.x, int(self.y)), (self.x, int(self.y + self.length)), 1)


class DynamicEffectController:
    """Manages a collection of Raindrop objects to create a rain effect."""

    def __init__(self, screen_w, screen_h, count=300):
        self.screen_w = screen_w
        self.screen_h = screen_h
        # Initialize the specified number of raindrops
        self.drops = [Raindrop(screen_w, screen_h) for _ in range(count)]

        self.dark_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        darkness = 30
        self.dark_overlay.fill((0, 0, 0, darkness))

    def update_and_draw(self, surface):
        """
        Updates the position of all drops and draws them onto the surface,
        including a darkening overlay for atmospheric effect.
        """
        # Blit the darkening layer onto the main surface
        surface.blit(self.dark_overlay, (0, 0))

        # Update and draw each individual raindrop
        for drop in self.drops:
            drop.update()
            drop.draw(surface)