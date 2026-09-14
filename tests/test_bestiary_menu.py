import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

import game
from bestiary_menu import (BESTIARY, MONSTER_ENTRIES, TITLE, BestiaryMenu)


class BestiaryMenuTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.known = {'scout'}
        self.previews = []
        self.entered = Mock()
        self.exited = Mock()
        self.menu = BestiaryMenu(
            discovered=lambda: self.known,
            preview_provider=self.preview,
            on_enter=self.entered,
            on_exit=self.exited)

    def tearDown(self):
        pygame.quit()

    def preview(self, key):
        self.previews.append(key)
        return pygame.Surface((80, 76), pygame.SRCALPHA)

    def key(self, key):
        return self.menu.handle_input(
            pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_data_covers_every_runtime_enemy_with_required_fields(self):
        self.assertEqual(set(game.ENEMIES),
                         {monster['key'] for monster in MONSTER_ENTRIES})
        for monster in MONSTER_ENTRIES:
            self.assertTrue({'name', 'classification', 'threat_level',
                             'stats', 'lore'} <= set(monster))
            self.assertEqual({'hp', 'mp', 'attack', 'defense', 'speed'},
                             set(monster['stats']))

    def test_keyboard_cycles_in_all_four_directions(self):
        self.assertEqual(BESTIARY, self.key(pygame.K_LEFT))
        self.assertEqual(len(MONSTER_ENTRIES) - 1, self.menu.selected_index)
        self.key(pygame.K_d)
        self.assertEqual(0, self.menu.selected_index)
        self.key(pygame.K_s)
        self.assertEqual(1, self.menu.selected_index)
        self.key(pygame.K_w)
        self.assertEqual(0, self.menu.selected_index)

    def test_xbox_hat_stick_and_cancel_are_supported(self):
        self.menu.handle_input(pygame.event.Event(
            pygame.JOYHATMOTION, value=(1, 0)))
        self.assertEqual(1, self.menu.selected_index)
        self.menu.handle_input(pygame.event.Event(
            pygame.JOYAXISMOTION, axis=1, value=1.0))
        self.assertEqual(2, self.menu.selected_index)
        self.assertEqual(TITLE, self.menu.handle_input(pygame.event.Event(
            pygame.JOYBUTTONDOWN, button=1)))

    def test_enter_and_exit_invoke_music_lifecycle_hooks(self):
        self.menu.enter()
        self.entered.assert_called_once_with()
        self.menu.exit()
        self.exited.assert_called_once_with()
        self.menu.exit()
        self.exited.assert_called_once_with()

    def test_unknown_entry_hides_preview_until_discovered(self):
        surface = pygame.Surface((320, 180))
        self.menu.selected_index = 1
        self.menu.draw(surface)
        self.assertEqual([], self.previews)
        self.known.add('drone')
        self.menu.draw(surface)
        self.assertEqual(['drone'], self.previews)

    def test_escape_and_backspace_return_to_title(self):
        self.assertEqual(TITLE, self.key(pygame.K_ESCAPE))
        self.assertEqual(TITLE, self.key(pygame.K_BACKSPACE))


class GameBestiaryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-bestiary-')
        self.savepatch = patch.object(
            game, 'SAVE', Path(self.temp.name) / 'save.json')
        self.savepatch.start()
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            self.g = game.Game()

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def test_contact_discovers_enemies_and_save_persists_them(self):
        self.g.state = 'field'
        self.g.start_battle(['scout', 'drone'])
        self.assertEqual({'scout', 'drone'}, self.g.discovered_enemies)
        self.g.state = 'field'
        self.g.save()
        data = json.loads(game.SAVE.read_text())
        self.assertEqual(['drone', 'scout'], data['discovered_enemies'])

    def test_runtime_preview_reuses_enemy_renderer(self):
        image = self.g.bestiary_preview('dragon')
        self.assertEqual((80, 76), image.get_size())
        self.assertGreater(pygame.mask.from_surface(image).count(), 0)

    def test_bestiary_switches_to_battle_music_then_requests_title_music(self):
        self.g.music_ready = True
        self.g.title_screen.selected_index = 3
        with patch('game.pygame.mixer.music.load') as load_mock, \
                patch('game.pygame.mixer.music.play') as play_mock, \
                patch('game.pygame.mixer.music.stop') as stop_mock:
            self.g.event(pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertEqual(BESTIARY, self.g.app_state)
            load_mock.assert_called_with(str(self.g.battle_music_path))
            play_mock.assert_called_with(-1, fade_ms=250)
            self.assertTrue(self.g.bestiary_music_playing)
            with patch.object(self.g.title_screen, 'play_music') as title_music:
                self.g.event(pygame.event.Event(
                    pygame.KEYDOWN, key=pygame.K_ESCAPE))
                self.assertEqual(TITLE, self.g.app_state)
                title_music.assert_called_once_with()
            self.assertFalse(self.g.bestiary_music_playing)
            self.assertTrue(stop_mock.called)


if __name__ == '__main__':
    unittest.main()
