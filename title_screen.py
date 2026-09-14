"""Front-end state machine and title menu for The Ashen Circuit.

The game keeps its detailed exploration/combat substates in ``Game.state``.
This module owns the five top-level application states so front-end navigation
can grow without coupling it to battle logic.
"""

from pathlib import Path
import random

import pygame

from exit_utils import graceful_exit
from pixel_ui import label, panel, text_width
from bestiary_menu import BestiaryMenu
from options_menu import OptionsMenu
from save_menu import SaveMenu


TITLE = "TITLE"
SAVE_MENU = "SAVE_MENU"
OPTIONS = "OPTIONS"
BESTIARY = "BESTIARY"
GAMEPLAY = "GAMEPLAY"
EXIT = "EXIT"
APP_STATES = (TITLE, SAVE_MENU, OPTIONS, BESTIARY, GAMEPLAY, EXIT)

MENU_OPTIONS = ("New Game", "Load Game", "Options", "Bestiary", "Exit")

INK = (8, 9, 18)
WHITE = (234, 230, 211)
MUTED = (123, 132, 145)
CYAN = (75, 211, 214)
GOLD = (232, 175, 66)
RED = (201, 66, 73)


class TitleScreen:
    """Own the title, save, options, and bestiary front-end screens.

    Callbacks keep this class reusable: it requests game actions without
    importing the main ``Game`` class. ``draw(screen)`` expects the game's
    320x180 UI surface, but also works as a standalone Pygame screen.
    """

    def __init__(self, *, on_new_game=None, on_load_game=None,
                 save_exists=None, get_battle_mode=None,
                 toggle_battle_mode=None, music_path=None, save_menu=None,
                 options_menu=None, bestiary_menu=None, on_exit=None):
        self.state = TITLE
        self.selected_index = 0
        self.submenu_index = 0
        self.elapsed = 0.0
        self.on_new_game = on_new_game or (lambda: True)
        self.on_load_game = on_load_game or (lambda: False)
        self.save_exists = save_exists or (lambda: False)
        self.get_battle_mode = get_battle_mode or (lambda: "Active")
        self.toggle_battle_mode = toggle_battle_mode or (lambda: None)
        self.on_exit = on_exit or graceful_exit
        self.music_path = Path(music_path) if music_path else None
        self.music_ready = False
        self.music_playing = False
        self.save_menu = save_menu or SaveMenu(
            data_provider=self._legacy_slot_data,
            on_load=lambda slot: self.on_load_game())
        self.options_menu = options_menu or OptionsMenu(
            initial_settings={'battle_system': self.get_battle_mode()},
            on_battle_system=self._set_legacy_battle_mode)
        self.bestiary_menu = bestiary_menu or BestiaryMenu()
        rng = random.Random(0xA5E1)
        self.stars = [(rng.randrange(320), rng.randrange(180),
                       rng.choice((1, 1, 1, 2))) for _ in range(76)]
        self.initialize_music()

    def _set_legacy_battle_mode(self, mode):
        if mode != self.get_battle_mode():
            self.toggle_battle_mode()

    def _legacy_slot_data(self):
        """Keep the standalone class compatible with its original callbacks."""
        occupied = self.save_exists()
        return [
            {'occupied': occupied, 'name': 'Rian', 'location': 'Unknown',
             'objective': 'Reach the Central Dynamo', 'playtime': 0},
            {'occupied': False},
            {'occupied': False},
        ]

    # pygame.mixer.music is a single global stream. Each play hook reloads the
    # requested track so battle and menu music can safely share that stream.
    def initialize_music(self, music_path=None):
        """Prepare the optional menu track; missing placeholder files are safe."""
        if music_path is not None:
            self.music_path = Path(music_path)
        if self.music_path is None or not self.music_path.exists():
            return False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.music.load(str(self.music_path))
            self.music_ready = True
        except (pygame.error, OSError):
            self.music_ready = False
        return self.music_ready

    def play_music(self):
        """Load and loop menu music. This is a no-op until a track is supplied."""
        if not self.music_ready and not self.initialize_music():
            return False
        try:
            pygame.mixer.music.load(str(self.music_path))
            pygame.mixer.music.play(-1)
            self.music_playing = True
        except (pygame.error, OSError):
            self.music_ready = False
            self.music_playing = False
        return self.music_playing

    def stop_music(self):
        if self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False

    def set_state(self, state):
        if state not in APP_STATES:
            raise ValueError(f"Unknown application state: {state}")
        previous = self.state
        if previous == BESTIARY and state != BESTIARY:
            self.bestiary_menu.exit()
        if state in (GAMEPLAY, EXIT):
            self.stop_music()
        elif self.state == GAMEPLAY:
            self.play_music()
        self.state = state
        self.submenu_index = 0
        if state == SAVE_MENU:
            self.save_menu.selected_slot = 0
            self.save_menu.refresh()
        elif state == OPTIONS:
            self.options_menu.reset_selection()
        elif state == BESTIARY and previous != BESTIARY:
            self.stop_music()
            self.bestiary_menu.enter()

    def _move(self, amount, count):
        if count:
            self.submenu_index = (self.submenu_index + amount) % count

    def _activate_title_choice(self):
        choice = MENU_OPTIONS[self.selected_index]
        if choice == "New Game":
            self.set_state(GAMEPLAY)
            self.on_new_game()
        elif choice == "Load Game":
            self.set_state(SAVE_MENU)
        elif choice == "Options":
            self.set_state(OPTIONS)
        elif choice == "Bestiary":
            self.set_state(BESTIARY)
        elif choice == "Exit":
            self.set_state(EXIT)
            self.on_exit()

    def handle_input(self, event):
        """Handle one Pygame event and return the resulting app state."""
        if self.state in (GAMEPLAY, EXIT):
            return self.state
        if self.state == OPTIONS:
            next_state = self.options_menu.handle_input(event)
            if next_state != OPTIONS:
                self.set_state(next_state)
            return self.state
        if self.state == BESTIARY:
            next_state = self.bestiary_menu.handle_input(event)
            if next_state != BESTIARY:
                self.set_state(next_state)
            return self.state
        if event.type != pygame.KEYDOWN:
            return self.state
        key = event.key
        if self.state == TITLE:
            if key == pygame.K_n:
                self.selected_index = 0
                self._activate_title_choice()
            elif key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(MENU_OPTIONS)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(MENU_OPTIONS)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                         pygame.K_z):
                self._activate_title_choice()
        elif self.state == SAVE_MENU:
            next_state = self.save_menu.handle_input(event)
            if next_state != SAVE_MENU:
                self.set_state(next_state)
        return self.state

    def update(self, dt):
        """Advance title-screen animation; ``dt`` is measured in seconds."""
        self.elapsed += max(0.0, dt)
        if self.state == SAVE_MENU:
            self.save_menu.update(dt)
        elif self.state == OPTIONS:
            self.options_menu.update(dt)
        elif self.state == BESTIARY:
            self.bestiary_menu.update(dt)

    @staticmethod
    def _centered(surface, value, y, color=WHITE, scale=1):
        x = (surface.get_width() - text_width(value, scale)) // 2
        label(surface, value, x, y, color, scale=scale)

    def _draw_backdrop(self, screen):
        screen.fill(INK)
        for x, y, size in self.stars:
            shade = 70 + size * 28
            pygame.draw.rect(screen, (shade, shade, shade + 18),
                             (x, y, size, size))
        # The angular silhouette preserves the existing title's visual identity.
        pygame.draw.polygon(screen, (42, 30, 58), (
            (35, 92), (92, 55), (145, 81), (172, 45), (196, 82),
            (286, 58), (244, 105), (286, 125), (193, 112),
            (160, 148), (127, 111), (45, 128), (77, 105)))

    def _draw_title(self, screen):
        self._draw_backdrop(screen)
        self._centered(screen, "THE ASHEN", 17, GOLD, scale=2)
        self._centered(screen, "CIRCUIT", 34, CYAN, scale=2)
        self._centered(screen, "AN ORIGINAL 16-BIT DUNGEON RPG", 54, WHITE)
        panel(screen, (91, 68, 138, 92))
        pulse = GOLD if int(self.elapsed * 3) % 2 == 0 else CYAN
        for index, option in enumerate(MENU_OPTIONS):
            selected = index == self.selected_index
            prefix = "> " if selected else "  "
            label(screen, prefix + option, 109, 79 + index * 14,
                  pulse if selected else WHITE)
        self._centered(screen, "ARROWS / WASD   ENTER / SPACE", 168, MUTED)

    def _draw_save_menu(self, screen):
        self._draw_backdrop(screen)
        self.save_menu.draw(screen)

    def _draw_options(self, screen):
        self._draw_backdrop(screen)
        self.options_menu.draw(screen)

    def _draw_bestiary(self, screen):
        self._draw_backdrop(screen)
        self.bestiary_menu.draw(screen)

    def draw(self, screen):
        """Draw the active front-end state to ``screen``."""
        if self.state == TITLE:
            self._draw_title(screen)
        elif self.state == SAVE_MENU:
            self._draw_save_menu(screen)
        elif self.state == OPTIONS:
            self._draw_options(screen)
        elif self.state == BESTIARY:
            self._draw_bestiary(screen)
        elif self.state == EXIT:
            screen.fill(INK)
            self._centered(screen, 'SHUTTING DOWN', 84, MUTED)
        else:
            screen.fill(INK)


def run_demo():
    """Run the title state machine by itself for quick visual testing."""
    pygame.init()
    screen = pygame.display.set_mode((640, 360))
    canvas = pygame.Surface((320, 180))
    clock = pygame.time.Clock()
    title = TitleScreen()
    running = True
    while running and title.state != GAMEPLAY:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                title.set_state(EXIT)
                title.on_exit()
            else:
                title.handle_input(event)
        title.update(dt)
        title.draw(canvas)
        screen.blit(pygame.transform.scale(canvas, screen.get_size()), (0, 0))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    run_demo()
