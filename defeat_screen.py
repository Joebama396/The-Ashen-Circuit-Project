"""Rendering helpers for the held battle-defeat screen."""

import pygame


FADE_SECONDS = 3.5
DEATH_TEXT = 'You Died'
DEATH_RED = (0x8A, 0x00, 0x00)
BLACK = (0, 0, 0)


def fade_alpha(elapsed):
    """Return a clamped 0..255 alpha for the slow battlefield fade."""
    progress = max(0.0, min(1.0, float(elapsed) / FADE_SECONDS))
    return round(255 * progress)


def draw_defeat_screen(surface, elapsed, draw_characters, font):
    """Fade the existing scene, restore heroes, then draw an opaque title."""
    alpha = fade_alpha(elapsed)
    fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    fade.fill((*BLACK, alpha))
    surface.blit(fade, (0, 0))

    # Party sprites deliberately sit above the fade while the world disappears.
    draw_characters()

    # Use a non-alpha backing surface so nothing can bleed through the title.
    glyph = font.render(DEATH_TEXT, False, DEATH_RED)
    title = pygame.Surface(glyph.get_size())
    title.fill(BLACK)
    title.blit(glyph, (0, 0))
    rect = title.get_rect(center=surface.get_rect().center)
    surface.blit(title, rect)
    return alpha, rect
