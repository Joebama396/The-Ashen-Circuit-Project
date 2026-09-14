import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import pygame
except ImportError:
    pygame = None

if pygame is not None:
    import game
    from defeat_screen import (BLACK, DEATH_RED, DEATH_TEXT, FADE_SECONDS,
                               draw_defeat_screen, fade_alpha)


@unittest.skipIf(pygame is None, 'pygame is not installed')
class DefeatScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_fade_is_slow_and_clamped(self):
        self.assertEqual(0, fade_alpha(-1))
        self.assertLess(fade_alpha(1), 255)
        self.assertEqual(255, fade_alpha(FADE_SECONDS))
        self.assertEqual(255, fade_alpha(FADE_SECONDS + 99))

    def test_party_and_opaque_title_are_foreground(self):
        surface = pygame.Surface((320, 180))
        surface.fill((255, 255, 255))
        hero_pixel = (12, 200, 90)

        def draw_characters():
            surface.set_at((4, 4), hero_pixel)

        font = pygame.font.Font(None, 22)
        alpha, title_rect = draw_defeat_screen(
            surface, FADE_SECONDS, draw_characters, font)
        self.assertEqual(255, alpha)
        self.assertEqual(surface.get_rect().center, title_rect.center)
        self.assertEqual(hero_pixel, surface.get_at((4, 4))[:3])
        self.assertEqual(BLACK, surface.get_at(title_rect.topleft)[:3])

        colors = {surface.get_at((x, y))[:3]
                  for y in range(title_rect.top, title_rect.bottom)
                  for x in range(title_rect.left, title_rect.right)}
        self.assertIn(DEATH_RED, colors)
        self.assertEqual('You Died', DEATH_TEXT)

    def test_party_wipe_enters_defeat_state_and_starts_music(self):
        dead = Mock()
        dead.alive.return_value = False
        living_enemy = Mock()
        living_enemy.alive.return_value = True
        instance = game.Game.__new__(game.Game)
        instance.state = 'battle'
        instance.party = [dead]
        instance.enemies = [living_enemy]
        instance.stop_battle_music = Mock()
        instance.start_gameover_music = Mock()

        instance.check_battle()

        self.assertEqual('gameover', instance.state)
        self.assertEqual(0.0, instance.gameover_elapsed)
        instance.stop_battle_music.assert_called_once_with()
        instance.start_gameover_music.assert_called_once_with()

    def test_supplied_game_over_track_is_packaged_source(self):
        track = Path(game.__file__).parent / 'assets' / 'audio' / 'game_over.mp3'
        self.assertTrue(track.is_file())
        self.assertGreater(track.stat().st_size, 1_000_000)

    def test_directional_strips_work_without_optional_master_atlas(self):
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            instance = game.Game()
        rian = instance.world.heroes[0]
        rian.direction = 2
        self.assertIsNone(instance.world.battle_animation_atlas)
        self.assertTrue(instance.world.has_battle_clips(rian))
        self.assertTrue(instance.world.set_battle_clip(
            rian, 'defeated', restart=True, force=True))
        sheet, frame = instance.world._directional_frame(rian)
        self.assertEqual((64, 64), sheet.get_size())
        self.assertEqual(0, frame)


if __name__ == '__main__':
    unittest.main()
