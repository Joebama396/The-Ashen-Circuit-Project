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
from title_screen import (APP_STATES, BESTIARY, GAMEPLAY, MENU_OPTIONS,
                          EXIT, OPTIONS, SAVE_MENU, TITLE, TitleScreen)


class TitleScreenTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.actions = []
        self.has_save = False
        self.mode = 'Active'
        self.title = TitleScreen(
            on_new_game=lambda: self.actions.append('new'),
            on_load_game=lambda: self.actions.append('load') or True,
            save_exists=lambda: self.has_save,
            get_battle_mode=lambda: self.mode,
            toggle_battle_mode=self.toggle_mode)

    def tearDown(self):
        pygame.quit()

    def toggle_mode(self):
        self.mode = 'Wait' if self.mode == 'Active' else 'Active'

    def key(self, key):
        return self.title.handle_input(
            pygame.event.Event(pygame.KEYDOWN, key=key))

    def choose(self, name):
        self.title.selected_index = MENU_OPTIONS.index(name)
        return self.key(pygame.K_SPACE)

    def test_declares_all_top_level_states(self):
        self.assertEqual(
            (TITLE, SAVE_MENU, OPTIONS, BESTIARY, GAMEPLAY, EXIT), APP_STATES)

    def test_arrow_and_wasd_navigation_wrap(self):
        self.key(pygame.K_UP)
        self.assertEqual('Exit', MENU_OPTIONS[self.title.selected_index])
        self.key(pygame.K_s)
        self.assertEqual('New Game', MENU_OPTIONS[self.title.selected_index])
        self.key(pygame.K_w)
        self.assertEqual('Exit', MENU_OPTIONS[self.title.selected_index])

    def test_new_game_enters_gameplay(self):
        self.assertEqual(GAMEPLAY, self.choose('New Game'))
        self.assertEqual(['new'], self.actions)

    def test_load_game_opens_save_menu_then_loads_existing_save(self):
        self.assertEqual(SAVE_MENU, self.choose('Load Game'))
        self.has_save = True
        self.assertEqual(GAMEPLAY, self.key(pygame.K_RETURN))
        self.assertEqual(['load'], self.actions)

    def test_options_toggles_mode_and_escape_returns_to_title(self):
        self.assertEqual(OPTIONS, self.choose('Options'))
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RIGHT)
        self.assertEqual('Wait', self.mode)
        self.assertEqual(TITLE, self.key(pygame.K_ESCAPE))

    def test_bestiary_opens_and_returns(self):
        self.assertEqual(BESTIARY, self.choose('Bestiary'))
        self.assertEqual(TITLE, self.key(pygame.K_ESCAPE))

    def test_exit_enters_exit_state_then_runs_shutdown(self):
        exit_mock = Mock(side_effect=SystemExit)
        self.title.on_exit = exit_mock
        with self.assertRaises(SystemExit):
            self.choose('Exit')
        exit_mock.assert_called_once_with()
        self.assertEqual(EXIT, self.title.state)

    def test_draws_each_frontend_screen(self):
        surface = pygame.Surface((320, 180))
        blank = bytes(320 * 180 * 3)
        for state in (TITLE, SAVE_MENU, OPTIONS, BESTIARY):
            with self.subTest(state=state):
                self.title.set_state(state)
                self.title.update(1 / 60)
                self.title.draw(surface)
                self.assertNotEqual(blank, pygame.image.tostring(surface, 'RGB'))

    def test_supplied_menu_music_starts_and_loops(self):
        with tempfile.NamedTemporaryFile(suffix='.mp3') as music, \
                patch('title_screen.pygame.mixer.music.load') as load_mock, \
                patch('title_screen.pygame.mixer.music.play') as play_mock:
            title = TitleScreen(music_path=music.name)
        load_mock.assert_called_with(music.name)
        play_mock.assert_called_once_with(-1)
        self.assertTrue(title.music_playing)


class GameTitleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-title-')
        self.savepatch = patch.object(
            game, 'SAVE', Path(self.temp.name) / 'save.json')
        self.savepatch.start()
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            self.g = game.Game()

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def test_game_starts_at_title_and_new_game_reaches_gameplay(self):
        self.assertEqual(TITLE, self.g.app_state)
        self.assertEqual('title', self.g.state)
        self.g.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(GAMEPLAY, self.g.app_state)
        self.assertEqual('dialog', self.g.state)

    def test_game_routes_load_options_and_bestiary(self):
        for index, expected in ((1, SAVE_MENU), (2, OPTIONS), (3, BESTIARY)):
            with self.subTest(expected=expected):
                self.g.enter_title()
                self.g.title_screen.selected_index = index
                self.g.event(pygame.event.Event(
                    pygame.KEYDOWN, key=pygame.K_SPACE))
                self.assertEqual(expected, self.g.app_state)

    def test_game_uses_packaged_menu_theme(self):
        self.assertEqual('menu_theme.mp3', self.g.title_screen.music_path.name)


if __name__ == '__main__':
    unittest.main()
