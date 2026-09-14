"""Three-slot JSON save browser used by the title-screen state machine."""

import json
from pathlib import Path

import pygame

from pixel_ui import label, panel, text_width


TITLE = "TITLE"
SAVE_MENU = "SAVE_MENU"
GAMEPLAY = "GAMEPLAY"

WHITE = (234, 230, 211)
MUTED = (123, 132, 145)
CYAN = (75, 211, 214)
GOLD = (232, 175, 66)
RED = (201, 66, 73)


def format_playtime(seconds):
    """Convert stored seconds to an unambiguous HH:MM:SS string."""
    if isinstance(seconds, str) and seconds.count(':') == 2:
        try:
            hours, minutes, secs = (max(0, int(part))
                                    for part in seconds.split(':'))
            return f"{hours:02}:{minutes:02}:{secs:02}"
        except ValueError:
            pass
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def read_save_slots(paths, location_names=None, objective_resolver=None):
    """Read up to three JSON saves and return UI-safe slot dictionaries.

    Older Ashen Circuit saves did not contain a metadata block. Their leader,
    room key, and playtime are converted on read so Slot 1 stays compatible.
    """
    location_names = location_names or {}
    slots = []
    for index, raw_path in enumerate(list(paths)[:3], start=1):
        path = Path(raw_path)
        if not path.exists():
            slots.append({'slot': index, 'occupied': False, 'path': path})
            continue
        try:
            data = json.loads(path.read_text())
            metadata = data.get('metadata', {})
            party = data.get('party') or [{}]
            leader = party[0] if isinstance(party[0], dict) else {}
            room_key = data.get('room', '')
            objective = metadata.get('objective')
            if not objective and objective_resolver is not None:
                objective = objective_resolver(data)
            slots.append({
                'slot': index,
                'occupied': True,
                'path': path,
                'name': str(metadata.get('name') or leader.get('name') or 'Rian'),
                'location': str(metadata.get('location') or
                                location_names.get(room_key, room_key or 'Unknown')),
                'objective': str(objective or 'Reach the Central Dynamo'),
                'playtime': format_playtime(
                    metadata.get('playtime', data.get('playtime', 0))),
            })
        except (OSError, ValueError, TypeError, KeyError):
            slots.append({
                'slot': index, 'occupied': False, 'corrupt': True, 'path': path})
    while len(slots) < 3:
        slots.append({'slot': len(slots) + 1, 'occupied': False, 'path': None})
    return slots


class SaveMenu:
    """Render and control the three vertical save cards."""

    def __init__(self, *, slot_paths=None, data_provider=None, on_load=None,
                 location_names=None, objective_resolver=None):
        self.slot_paths = slot_paths or (lambda: ())
        self.data_provider = data_provider
        self.on_load = on_load or (lambda slot: False)
        self.location_names = location_names or {}
        self.objective_resolver = objective_resolver
        self.selected_slot = 0
        self.elapsed = 0.0
        self.slots = []
        self.refresh()

    def refresh(self):
        if self.data_provider is not None:
            supplied = list(self.data_provider())[:3]
            self.slots = []
            for index in range(3):
                raw = supplied[index] if index < len(supplied) else {}
                slot = dict(raw)
                slot.setdefault('slot', index + 1)
                slot.setdefault('occupied', False)
                if slot['occupied']:
                    slot.setdefault('name', 'Rian')
                    slot.setdefault('location', 'Unknown')
                    slot.setdefault('objective', 'Reach the Central Dynamo')
                    slot['playtime'] = format_playtime(slot.get('playtime', 0))
                self.slots.append(slot)
        else:
            self.slots = read_save_slots(
                self.slot_paths(), self.location_names, self.objective_resolver)
        return self.slots

    def handle_input(self, event):
        """Handle navigation and return TITLE, SAVE_MENU, or GAMEPLAY."""
        if event.type != pygame.KEYDOWN:
            return SAVE_MENU
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected_slot = (self.selected_slot - 1) % 3
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected_slot = (self.selected_slot + 1) % 3
        elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x):
            return TITLE
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                           pygame.K_z):
            self.refresh()
            slot = self.slots[self.selected_slot]
            if slot.get('occupied') and self.on_load(self.selected_slot + 1) is not False:
                return GAMEPLAY
        return SAVE_MENU

    def update(self, dt):
        self.elapsed += max(0.0, dt)

    @staticmethod
    def _centered(surface, value, y, color=WHITE):
        x = (surface.get_width() - text_width(value)) // 2
        label(surface, value, x, y, color)

    def _draw_card(self, screen, index, slot, y):
        selected = index == self.selected_slot
        accent = GOLD if selected else CYAN
        panel(screen, (11, y, 298, 39), accent=accent)
        if selected:
            pygame.draw.rect(screen, GOLD, (10, y - 1, 300, 41), 1)
        prefix = '> ' if selected else '  '
        label(screen, f"{prefix}SLOT {index + 1}", 18, y + 4, accent)
        if slot.get('corrupt'):
            self._centered(screen, '-- UNREADABLE SAVE --', y + 17, RED)
        elif not slot.get('occupied'):
            self._centered(screen, '-- EMPTY SLOT --', y + 17, MUTED)
        else:
            label(screen, f"NAME: {slot['name']}", 103, y + 3, WHITE,
                  limit=32)
            label(screen, f"LOCATION: {slot['location']}", 24, y + 12,
                  WHITE, limit=45)
            label(screen, f"OBJECTIVE: {slot['objective']}", 24, y + 21,
                  WHITE, limit=45)
            label(screen, f"PLAYTIME: {slot['playtime']}", 24, y + 30,
                  WHITE, limit=45)

    def draw(self, screen):
        """Draw three distinct vertically arranged save cards."""
        self.refresh()
        self._centered(screen, 'SELECT SAVE', 8, GOLD)
        self._centered(screen, 'ENTER / SPACE  LOAD', 18, CYAN)
        for index, slot in enumerate(self.slots):
            self._draw_card(screen, index, slot, 30 + index * 43)
        self._centered(screen, 'ESC / BACKSPACE  TITLE', 164, MUTED)
