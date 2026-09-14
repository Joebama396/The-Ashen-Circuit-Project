"""Interactive discovered/unknown enemy gallery for the BESTIARY state."""

import pygame

from pixel_ui import label, panel, text_width


TITLE = 'TITLE'
BESTIARY = 'BESTIARY'

WHITE = (234, 230, 211)
MUTED = (123, 132, 145)
CYAN = (75, 211, 214)
GOLD = (232, 175, 66)
PURPLE = (135, 91, 170)


# Adding a monster requires one new dictionary. Threat Level describes enemy
# danger only; The Ashen Circuit has no player XP or character-level system.
MONSTER_ENTRIES = (
    {'key': 'scout', 'name': 'Dominion Scout',
     'classification': 'Dominion Recon', 'threat_level': 1,
     'stats': {'hp': 115, 'mp': 0, 'attack': 24, 'defense': 12, 'speed': 14},
     'lore': 'Forward observers sent to map the Engine before heavier troops arrive.'},
    {'key': 'drone', 'name': 'Repair Drone',
     'classification': 'Magitek Construct', 'threat_level': 1,
     'stats': {'hp': 90, 'mp': 12, 'attack': 21, 'defense': 14, 'speed': 16},
     'lore': 'A tireless maintenance unit repurposed to mend Dominion battle lines.'},
    {'key': 'mite', 'name': 'Wire Mite',
     'classification': 'Vermin Automaton', 'threat_level': 1,
     'stats': {'hp': 72, 'mp': 0, 'attack': 18, 'defense': 8, 'speed': 24},
     'lore': 'A cable-feeding machine that nests inside warm conduits and exposed relays.'},
    {'key': 'guard', 'name': 'Iron Guard',
     'classification': 'Heavy Infantry', 'threat_level': 2,
     'stats': {'hp': 185, 'mp': 0, 'attack': 32, 'defense': 27, 'speed': 13},
     'lore': 'Armored occupation troops assigned to hold narrow halls at any cost.'},
    {'key': 'wisp', 'name': 'Aether Wisp',
     'classification': 'Aetheric Entity', 'threat_level': 2,
     'stats': {'hp': 130, 'mp': 36, 'attack': 21, 'defense': 12, 'speed': 26},
     'lore': 'A fragment of living current drawn from the Engine ancient power grid.'},
    {'key': 'soldier', 'name': 'Dominion Lancer',
     'classification': 'Assault Infantry', 'threat_level': 3,
     'stats': {'hp': 210, 'mp': 0, 'attack': 38, 'defense': 25, 'speed': 19},
     'lore': 'A disciplined shock trooper carrying a magitek lance through hostile ruins.'},
    {'key': 'golem', 'name': 'Furnace Golem',
     'classification': 'Foundry Construct', 'threat_level': 4,
     'stats': {'hp': 330, 'mp': 0, 'attack': 45, 'defense': 35, 'speed': 10},
     'lore': 'A walking crucible whose cracked core still burns with industrial heat.'},
    {'key': 'serpent', 'name': 'Coolant Serpent',
     'classification': 'Cryonic Beast', 'threat_level': 4,
     'stats': {'hp': 240, 'mp': 34, 'attack': 39, 'defense': 22, 'speed': 23},
     'lore': 'An Engine guardian adapted to hunt through flooded pumps and frozen pipes.'},
    {'key': 'vael', 'name': 'Commander Vael',
     'classification': 'Dominion Commander', 'threat_level': 7,
     'stats': {'hp': 1900, 'mp': 80, 'attack': 48, 'defense': 42, 'speed': 26},
     'lore': 'The occupation commander who intends to turn the Caelus Engine into a weapon.'},
    {'key': 'dragon', 'name': 'Vharos',
     'classification': 'Ancient Weapon', 'threat_level': 10,
     'stats': {'hp': 4600, 'mp': 160, 'attack': 61, 'defense': 55, 'speed': 24},
     'lore': 'An ashen dragon bound into the Engine as its living focusing array.'},
)


def wrap_lines(value, width=31, limit=3):
    lines = []
    current = ''
    for word in str(value).split():
        proposed = (current + ' ' + word).strip()
        if len(proposed) > width and current:
            lines.append(current)
            current = word
        else:
            current = proposed
    if current:
        lines.append(current)
    if len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1][:max(0, width - 2)] + '..'
    return lines


class BestiaryMenu:
    """Browse monster records and hide undiscovered entries."""

    def __init__(self, *, monsters=None, discovered=None, preview_provider=None,
                 on_enter=None, on_exit=None):
        self.monsters = tuple(monsters or MONSTER_ENTRIES)
        self.discovered = discovered or (lambda: set())
        self.preview_provider = preview_provider or (lambda key: None)
        self.on_enter = on_enter or (lambda: None)
        self.on_exit = on_exit or (lambda: None)
        self.selected_index = 0
        self.axis_latch = [0, 0]
        self.elapsed = 0.0
        self.active = False

    def enter(self):
        self.selected_index = 0
        self.axis_latch = [0, 0]
        self.active = True
        self.on_enter()

    def exit(self):
        if self.active:
            self.active = False
            self.on_exit()

    def update(self, dt):
        self.elapsed += max(0.0, dt)

    def _key_from_event(self, event):
        if event.type == pygame.KEYDOWN:
            return event.key
        if event.type == pygame.JOYBUTTONDOWN:
            return {
                1: pygame.K_ESCAPE,
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
        key = self._key_from_event(event)
        if key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a):
            self.selected_index = (self.selected_index - 1) % len(self.monsters)
        elif key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d):
            self.selected_index = (self.selected_index + 1) % len(self.monsters)
        elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x):
            return TITLE
        return BESTIARY

    @staticmethod
    def _centered(surface, value, y, color=WHITE, scale=1):
        x = (surface.get_width() - text_width(value, scale)) // 2
        label(surface, value, x, y, color, scale=scale)

    def _draw_list(self, screen, known):
        panel(screen, (5, 24, 101, 142))
        visible = 8
        start = max(0, min(self.selected_index - visible // 2,
                           len(self.monsters) - visible))
        for row, index in enumerate(range(start, min(start + visible,
                                                     len(self.monsters)))):
            monster = self.monsters[index]
            selected = index == self.selected_index
            discovered = monster['key'] in known
            name = monster['name'] if discovered else '???'
            color = GOLD if selected else WHITE if discovered else MUTED
            label(screen, ('> ' if selected else '  ') + name,
                  11, 34 + row * 16, color, limit=15)
        if start:
            label(screen, 'UP', 89, 27, CYAN)
        if start + visible < len(self.monsters):
            label(screen, 'DN', 89, 155, CYAN)

    def _draw_unknown(self, screen):
        self._centered(screen, '?', 51, MUTED, scale=4)
        label(screen, '???', 203, 34, MUTED, scale=2)
        label(screen, 'CLASS', 203, 54, GOLD)
        label(screen, 'UNKNOWN', 203, 65, MUTED)
        label(screen, 'THREAT LV', 203, 82, GOLD)
        label(screen, '???', 203, 93, MUTED)
        label(screen, 'HP  ???   MP  ???', 116, 112, MUTED)
        label(screen, 'ATK ???  DEF ???  SPD ???', 116, 123, MUTED)
        for row, line in enumerate(wrap_lines(
                'Encounter this enemy to unlock its field record.')):
            label(screen, line, 116, 141 + row * 9, MUTED)

    def _draw_known(self, screen, monster):
        image = self.preview_provider(monster['key'])
        if image is not None:
            screen.blit(image, (113, 29))
        label(screen, monster['name'], 203, 34, GOLD, limit=18)
        label(screen, 'CLASS', 203, 49, CYAN)
        for row, line in enumerate(wrap_lines(monster['classification'], 17, 2)):
            label(screen, line, 203, 59 + row * 9, WHITE)
        label(screen, 'THREAT LV', 203, 81, CYAN)
        label(screen, monster['threat_level'], 269, 81, GOLD)
        stats = monster['stats']
        label(screen, f"HP {stats['hp']:4}   MP {stats['mp']:3}", 116, 112, WHITE)
        label(screen,
              f"ATK {stats['attack']:3}  DEF {stats['defense']:3}  SPD {stats['speed']:3}",
              116, 123, WHITE)
        for row, line in enumerate(wrap_lines(monster['lore'])):
            label(screen, line, 116, 141 + row * 9, WHITE)

    def draw(self, screen):
        known = set(self.discovered())
        self._centered(screen, 'BESTIARY', 5, GOLD, scale=2)
        self._draw_list(screen, known)
        panel(screen, (109, 24, 206, 142))
        panel(screen, (112, 28, 82, 78), accent=PURPLE)
        monster = self.monsters[self.selected_index]
        if monster['key'] in known:
            self._draw_known(screen, monster)
        else:
            self._draw_unknown(screen)
        self._centered(screen, 'D-PAD / STICK / WASD: BROWSE   B: BACK',
                       171, MUTED)
