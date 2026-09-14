"""Persistent audio and battle settings for the title-screen OPTIONS state."""

import json
from pathlib import Path

import pygame

from pixel_ui import label, panel, text_width


TITLE = 'TITLE'
OPTIONS = 'OPTIONS'

DEFAULT_SETTINGS = {
    'music_volume': 80,
    'sfx_volume': 80,
    'battle_system': 'Active',
}

WHITE = (234, 230, 211)
MUTED = (123, 132, 145)
CYAN = (75, 211, 214)
GOLD = (232, 175, 66)
GREEN = (76, 177, 101)


def clamp_volume(value):
    """Normalize a volume to one of the eleven 10% steps."""
    try:
        value = int(round(float(value) / 10.0) * 10)
    except (TypeError, ValueError):
        value = 80
    return max(0, min(100, value))


def normalize_settings(raw=None):
    raw = raw if isinstance(raw, dict) else {}
    battle = raw.get('battle_system', DEFAULT_SETTINGS['battle_system'])
    return {
        'music_volume': clamp_volume(
            raw.get('music_volume', DEFAULT_SETTINGS['music_volume'])),
        'sfx_volume': clamp_volume(
            raw.get('sfx_volume', DEFAULT_SETTINGS['sfx_volume'])),
        'battle_system': battle if battle in ('Wait', 'Active') else 'Active',
    }


def load_settings(path):
    if path is None:
        return dict(DEFAULT_SETTINGS)
    path = Path(path)
    try:
        return normalize_settings(json.loads(path.read_text()))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(path, settings):
    """Atomically persist normalized settings when a path is configured."""
    settings = normalize_settings(settings)
    if path is None:
        return settings
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(settings, indent=2))
    temporary.replace(path)
    return settings


class OptionsMenu:
    """Four-row options screen with keyboard and Xbox input support."""

    ITEMS = ('Music Volume', 'SFX Volume', 'Battle System', 'Back')

    def __init__(self, *, settings_path=None, initial_settings=None,
                 on_music_volume=None, on_sfx_volume=None,
                 on_battle_system=None, test_sfx=None):
        self.settings_path = settings_path
        loaded = load_settings(self._path()) if settings_path else {}
        self.settings = normalize_settings({**(initial_settings or {}), **loaded})
        self.on_music_volume = on_music_volume or (lambda volume: None)
        self.on_sfx_volume = on_sfx_volume or (lambda volume: None)
        self.on_battle_system = on_battle_system or (lambda mode: None)
        self.test_sfx = test_sfx or (lambda volume: None)
        self.selected_index = 0
        self.axis_latch = [0, 0]
        self.elapsed = 0.0
        self.apply_settings()

    def _path(self):
        return self.settings_path() if callable(self.settings_path) else self.settings_path

    def apply_settings(self):
        self.on_music_volume(self.settings['music_volume'] / 100.0)
        self.on_sfx_volume(self.settings['sfx_volume'] / 100.0)
        self.on_battle_system(self.settings['battle_system'])

    def save(self):
        self.settings = save_settings(self._path(), self.settings)
        return self.settings

    def reset_selection(self):
        self.selected_index = 0
        self.axis_latch = [0, 0]

    def set_battle_system(self, mode):
        if mode in ('Wait', 'Active'):
            self.settings['battle_system'] = mode
            self.on_battle_system(mode)

    def _adjust(self, direction):
        if self.selected_index == 0:
            value = clamp_volume(self.settings['music_volume'] + direction * 10)
            self.settings['music_volume'] = value
            self.on_music_volume(value / 100.0)
        elif self.selected_index == 1:
            value = clamp_volume(self.settings['sfx_volume'] + direction * 10)
            self.settings['sfx_volume'] = value
            volume = value / 100.0
            self.on_sfx_volume(volume)
            self.test_sfx(volume)
        elif self.selected_index == 2:
            mode = 'Wait' if self.settings['battle_system'] == 'Active' else 'Active'
            self.settings['battle_system'] = mode
            self.on_battle_system(mode)

    def _key_from_event(self, event):
        if event.type == pygame.KEYDOWN:
            return event.key
        if event.type == pygame.JOYBUTTONDOWN:
            return {
                0: pygame.K_RETURN, 1: pygame.K_ESCAPE,
                11: pygame.K_UP, 12: pygame.K_DOWN,
                13: pygame.K_LEFT, 14: pygame.K_RIGHT,
            }.get(event.button)
        if event.type == pygame.JOYHATMOTION and event.value != (0, 0):
            if event.value[0]:
                return pygame.K_RIGHT if event.value[0] > 0 else pygame.K_LEFT
            return pygame.K_UP if event.value[1] > 0 else pygame.K_DOWN
        if event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
            old = self.axis_latch[event.axis]
            new = 1 if event.value > .55 else -1 if event.value < -.55 else 0
            self.axis_latch[event.axis] = new
            if not new or new == old:
                return None
            if event.axis == 0:
                return pygame.K_RIGHT if new > 0 else pygame.K_LEFT
            return pygame.K_DOWN if new > 0 else pygame.K_UP
        return None

    def handle_input(self, event):
        """Handle an input event and return OPTIONS or TITLE."""
        key = self._key_from_event(event)
        if key is None:
            return OPTIONS
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.ITEMS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.ITEMS)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._adjust(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._adjust(1)
        elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x):
            self.save()
            return TITLE
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                     pygame.K_z) and self.selected_index == 3:
            self.save()
            return TITLE
        return OPTIONS

    def update(self, dt):
        self.elapsed += max(0.0, dt)

    @staticmethod
    def _centered(surface, value, y, color=WHITE, scale=1):
        x = (surface.get_width() - text_width(value, scale)) // 2
        label(surface, value, x, y, color, scale=scale)

    @staticmethod
    def _draw_slider(screen, y, percent, selected):
        x, width, height = 143, 89, 8
        pygame.draw.rect(screen, (8, 14, 22), (x, y, width, height))
        pygame.draw.rect(screen, GOLD if selected else MUTED,
                         (x, y, width, height), 1)
        fill = round((width - 4) * percent / 100)
        if fill:
            pygame.draw.rect(screen, GREEN if selected else CYAN,
                             (x + 2, y + 2, fill, height - 4))
        label(screen, f'{percent:3}%', 239, y, GOLD if selected else WHITE)

    def draw(self, screen):
        """Draw audio sliders, battle toggle, and Back row."""
        panel(screen, (31, 28, 258, 127))
        self._centered(screen, 'OPTIONS', 37, GOLD, scale=2)
        rows = (66, 87, 108, 133)
        for index, (item, y) in enumerate(zip(self.ITEMS, rows)):
            selected = index == self.selected_index
            color = GOLD if selected else WHITE
            label(screen, ('> ' if selected else '  ') + item, 45, y, color)
            if index == 0:
                self._draw_slider(screen, y, self.settings['music_volume'], selected)
            elif index == 1:
                self._draw_slider(screen, y, self.settings['sfx_volume'], selected)
            elif index == 2:
                label(screen, f"< {self.settings['battle_system']} >", 198, y, color)
        self._centered(screen, 'D-PAD / STICK / WASD   A: SELECT   B: BACK',
                       164, MUTED)
