import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from options_menu import OptionsMenu
from save_menu import SAVE_MENU, SaveMenu
from title_screen import MENU_OPTIONS, TitleScreen
from ui_sfx import UISfx


class UISfxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_supplied_effects_load_and_follow_volume(self):
        audio = Path(__file__).parents[1] / 'assets' / 'audio'
        bank = UISfx({
            'cursor': audio / 'ui_cursor.mp3',
            'close': audio / 'ui_close.mp3',
            'blocked': audio / 'ui_blocked.mp3'}, .35)
        self.assertEqual({'cursor', 'close', 'blocked'}, set(bank.sounds))
        self.assertTrue(all(abs(sound.get_volume() - .35) < .02
                            for sound in bank.sounds.values()))

    def test_title_navigation_and_entry_use_cursor(self):
        played = []
        menu = TitleScreen(play_sfx=played.append)
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        menu.selected_index = MENU_OPTIONS.index('Options')
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        self.assertEqual(['cursor', 'cursor'], played)

    def test_empty_save_is_blocked_and_cancel_closes(self):
        played = []
        with tempfile.TemporaryDirectory() as root:
            paths = [Path(root) / f'{index}.json' for index in range(3)]
            menu = SaveMenu(slot_paths=lambda: paths, play_sfx=played.append)
            self.assertEqual(SAVE_MENU, menu.handle_input(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)))
            menu.handle_input(pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(['blocked', 'close'], played)

    def test_options_limits_are_blocked_and_back_closes(self):
        played = []
        menu = OptionsMenu(initial_settings={'music_volume': 100},
                           play_sfx=played.append)
        menu.handle_input(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_RIGHT))
        menu.handle_input(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(['blocked', 'close'], played)

    def test_build_files_package_all_three_effects(self):
        root = Path(__file__).parents[1]
        build = (root / 'build.sh').read_text()
        spec = (root / 'ashen-circuit.spec').read_text()
        for name in ('ui_cursor.mp3', 'ui_close.mp3', 'ui_blocked.mp3'):
            self.assertIn(name, build)
            self.assertIn(name, spec)


if __name__ == '__main__':
    unittest.main()
