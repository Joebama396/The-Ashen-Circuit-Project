import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

import game
from options_menu import OPTIONS, TITLE, OptionsMenu, load_settings


class OptionsMenuTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-options-')
        self.path = Path(self.temp.name) / 'settings.json'
        self.music_calls = []
        self.sfx_calls = []
        self.test_calls = []
        self.battle_calls = []
        self.menu = OptionsMenu(
            settings_path=self.path,
            on_music_volume=self.music_calls.append,
            on_sfx_volume=self.sfx_calls.append,
            on_battle_system=self.battle_calls.append,
            test_sfx=self.test_calls.append)

    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()

    def key(self, key):
        return self.menu.handle_input(
            pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_keyboard_adjusts_both_sliders_in_ten_percent_steps(self):
        self.assertEqual(80, self.menu.settings['music_volume'])
        self.key(pygame.K_RIGHT)
        self.assertEqual(90, self.menu.settings['music_volume'])
        self.assertAlmostEqual(.9, self.music_calls[-1])
        self.key(pygame.K_s)
        self.key(pygame.K_a)
        self.assertEqual(70, self.menu.settings['sfx_volume'])
        self.assertAlmostEqual(.7, self.sfx_calls[-1])
        self.assertAlmostEqual(.7, self.test_calls[-1])

    def test_volumes_clamp_at_zero_and_one_hundred(self):
        for _ in range(20):
            self.key(pygame.K_LEFT)
        self.assertEqual(0, self.menu.settings['music_volume'])
        for _ in range(20):
            self.key(pygame.K_RIGHT)
        self.assertEqual(100, self.menu.settings['music_volume'])

    def test_battle_system_toggles_with_left_or_right(self):
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RIGHT)
        self.assertEqual('Wait', self.menu.settings['battle_system'])
        self.key(pygame.K_LEFT)
        self.assertEqual('Active', self.menu.settings['battle_system'])

    def test_back_confirm_and_cancel_save_settings(self):
        self.key(pygame.K_RIGHT)
        for _ in range(3):
            self.key(pygame.K_DOWN)
        self.assertEqual(TITLE, self.key(pygame.K_SPACE))
        self.assertEqual(90, load_settings(self.path)['music_volume'])
        self.menu.settings['sfx_volume'] = 30
        self.assertEqual(TITLE, self.key(pygame.K_BACKSPACE))
        self.assertEqual(30, load_settings(self.path)['sfx_volume'])

    def test_saved_preferences_load_in_a_new_menu(self):
        self.path.write_text(json.dumps({
            'music_volume': 20, 'sfx_volume': 60,
            'battle_system': 'Wait'}))
        loaded = OptionsMenu(settings_path=self.path)
        self.assertEqual({
            'music_volume': 20, 'sfx_volume': 60,
            'battle_system': 'Wait'}, loaded.settings)

    def test_raw_xbox_dpad_stick_and_buttons_are_supported(self):
        self.menu.handle_input(pygame.event.Event(
            pygame.JOYHATMOTION, value=(0, -1)))
        self.assertEqual(1, self.menu.selected_index)
        self.menu.handle_input(pygame.event.Event(
            pygame.JOYAXISMOTION, axis=0, value=1.0))
        self.assertEqual(90, self.menu.settings['sfx_volume'])
        self.assertEqual(TITLE, self.menu.handle_input(pygame.event.Event(
            pygame.JOYBUTTONDOWN, button=1)))

    def test_draw_contains_slider_fill_and_each_row(self):
        surface = pygame.Surface((320, 180))
        surface.fill((8, 9, 18))
        self.menu.draw(surface)
        self.assertNotEqual((8, 9, 18), surface.get_at((145, 68))[:3])
        self.assertNotEqual((8, 9, 18), surface.get_at((145, 89))[:3])


class GameOptionsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-game-options-')
        self.savepatch = patch.object(
            game, 'SAVE', Path(self.temp.name) / 'save.json')
        self.savepatch.start()
        game.settings_path().write_text(json.dumps({
            'music_volume': 30, 'sfx_volume': 60,
            'battle_system': 'Wait'}))
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            self.g = game.Game()

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def test_settings_apply_to_game_and_pygame_music(self):
        self.assertAlmostEqual(.3, self.g.music_volume)
        self.assertAlmostEqual(.6, self.g.sfx_volume)
        self.assertEqual('Wait', self.g.battle_mode)
        self.assertAlmostEqual(.3, pygame.mixer.music.get_volume(), places=2)

    def test_game_routes_xbox_navigation_and_cancel(self):
        self.g.title_screen.selected_index = 2
        self.g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertEqual(OPTIONS, self.g.app_state)
        self.g.event(pygame.event.Event(
            pygame.JOYHATMOTION, value=(1, 0)))
        self.assertEqual(40, self.g.title_screen.options_menu.settings['music_volume'])
        self.g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=1))
        self.assertEqual(TITLE, self.g.app_state)
        self.assertEqual(40, load_settings(game.settings_path())['music_volume'])


if __name__ == '__main__':
    unittest.main()
