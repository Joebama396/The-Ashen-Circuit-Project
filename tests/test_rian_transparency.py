import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import pygame
except ImportError:
    pygame = None

if pygame is not None:
    import game


@unittest.skipIf(pygame is None, 'pygame is not installed')
class RianTransparencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_source_strips_use_true_alpha_and_native_cell_sizes(self):
        battle_dir = Path(game.__file__).parent / 'assets' / 'characters' / 'battle'
        expected = {
            'rian_battle_guard_walk': (256, 64),
            'rian_battle_idle': (256, 64),
            'rian_fainted': (64, 64),
            'rian_hurt_recoil': (192, 64),
            'rian_sword_basic_upward_slash': (256, 64),
        }
        directions = ('front_down', 'back_up', 'profile_right')
        paths = []
        for prefix, (width, height) in expected.items():
            paths.extend(
                battle_dir / f'{prefix}_{direction}_{width}x{height}.png'
                for direction in directions)
        self.assertEqual(15, len(paths))
        self.assertTrue(all(path.is_file() for path in paths))

        for path in paths:
            with self.subTest(asset=path.name):
                prefix = next(name for name in expected
                              if path.name.startswith(name))
                sheet = pygame.image.load(str(path))
                self.assertEqual(expected[prefix], sheet.get_size())
                self.assertTrue(sheet.get_masks()[3])
                alphas = [sheet.get_at((x, y)).a
                          for y in range(sheet.get_height())
                          for x in range(sheet.get_width())]
                self.assertIn(0, alphas)
                self.assertIn(255, alphas)

    def test_every_loaded_rian_animation_keeps_its_transparent_matte(self):
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            instance = game.Game()

        self.assertEqual(15, len(instance.battle_directional_sheets))
        for name, sheet in instance.battle_directional_sheets.items():
            with self.subTest(animation=name):
                width, height = sheet.get_size()
                for point in ((0, 0), (width - 1, 0),
                              (0, height - 1), (width - 1, height - 1)):
                    self.assertEqual(0, sheet.get_at(point).a)

                opaque = 0
                forbidden_matte = 0
                for y in range(height):
                    for x in range(width):
                        color = sheet.get_at((x, y))
                        if color.a:
                            opaque += 1
                            rgb = color[:3]
                            forbidden_matte += int(
                                rgb in ((43, 49, 58), (61, 68, 78)) or
                                (rgb[0] >= 180 and rgb[2] >= 180 and
                                 rgb[1] <= 96 and abs(rgb[0] - rgb[2]) <= 64))
                self.assertGreater(opaque, 100)
                self.assertEqual(0, forbidden_matte)

    def test_rendered_frame_does_not_overwrite_background_with_matte(self):
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            instance = game.Game()
        backdrop = (17, 37, 53)

        for name, sheet in instance.battle_directional_sheets.items():
            with self.subTest(animation=name):
                target = pygame.Surface((64, 64))
                target.fill(backdrop)
                target.blit(sheet.subsurface((0, 0, 64, 64)), (0, 0))
                self.assertEqual(backdrop, target.get_at((0, 0))[:3])
                self.assertEqual(backdrop, target.get_at((63, 63))[:3])


if __name__ == '__main__':
    unittest.main()
