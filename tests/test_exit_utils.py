import os
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from exit_utils import graceful_exit


class GracefulExitTests(unittest.TestCase):
    def test_playing_audio_fades_and_every_subsystem_shuts_down(self):
        with patch('exit_utils.pygame.mixer.get_init', return_value=(48000, -16, 2)), \
                patch('exit_utils.pygame.mixer.music.get_busy', return_value=True), \
                patch('exit_utils.pygame.mixer.get_busy', return_value=True), \
                patch('exit_utils.pygame.mixer.music.fadeout') as music_fade, \
                patch('exit_utils.pygame.mixer.fadeout') as channel_fade, \
                patch('exit_utils.pygame.time.wait') as wait_mock, \
                patch('exit_utils.pygame.mixer.music.stop') as music_stop, \
                patch('exit_utils.pygame.mixer.stop') as mixer_stop, \
                patch('exit_utils.pygame.joystick.quit') as joystick_quit, \
                patch('exit_utils.pygame.mixer.quit') as mixer_quit, \
                patch('exit_utils.pygame.quit') as pygame_quit, \
                patch('exit_utils.sys.exit', side_effect=SystemExit) as process_exit:
            with self.assertRaises(SystemExit):
                graceful_exit(exit_code=3, fade_ms=250)
        music_fade.assert_called_once_with(250)
        channel_fade.assert_called_once_with(250)
        wait_mock.assert_called_once_with(250)
        music_stop.assert_called_once_with()
        mixer_stop.assert_called_once_with()
        joystick_quit.assert_called_once_with()
        mixer_quit.assert_called_once_with()
        pygame_quit.assert_called_once_with()
        process_exit.assert_called_once_with(3)

    def test_shutdown_skips_delay_when_audio_is_idle(self):
        with patch('exit_utils.pygame.mixer.get_init', return_value=(48000, -16, 2)), \
                patch('exit_utils.pygame.mixer.music.get_busy', return_value=False), \
                patch('exit_utils.pygame.mixer.get_busy', return_value=False), \
                patch('exit_utils.pygame.time.wait') as wait_mock, \
                patch('exit_utils.sys.exit', side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                graceful_exit()
        wait_mock.assert_not_called()


class ExitStateIntegrationTests(unittest.TestCase):
    def setUp(self):
        pygame.init()

    def tearDown(self):
        pygame.quit()

    def test_window_close_uses_the_same_exit_state_and_utility(self):
        from pathlib import Path
        import tempfile
        import game

        with tempfile.TemporaryDirectory(prefix='ashen-exit-') as folder, \
                patch.object(game, 'SAVE', Path(folder) / 'save.json'), \
                patch.object(game.Game, 'make_music', side_effect=pygame.error):
            instance = game.Game()
            with patch('game.graceful_exit', side_effect=SystemExit) as shutdown:
                with self.assertRaises(SystemExit):
                    instance.event(pygame.event.Event(pygame.QUIT))
                self.assertEqual('EXIT', instance.app_state)
                shutdown.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
