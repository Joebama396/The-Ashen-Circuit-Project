import unittest
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

    def test_cleanup_handles_near_magenta_and_edge_white(self):
        source = pygame.Surface((7, 7))
        source.fill((249, 3, 249))
        pygame.draw.line(source, (253, 253, 253), (0, 0), (6, 0))
        pygame.draw.rect(source, (15, 20, 30), (2, 2, 3, 3))
        source.set_at((3, 3), (255, 255, 255))

        cleaned = game.prepare_rian_battle_sheet(source)

        self.assertEqual(0, cleaned.get_at((0, 0)).a)
        self.assertEqual(0, cleaned.get_at((0, 3)).a)
        self.assertEqual(255, cleaned.get_at((3, 3)).a)

    def test_every_loaded_rian_animation_has_transparent_matte(self):
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            instance = game.Game()

        self.assertGreaterEqual(len(instance.battle_directional_sheets), 15)
        for name, sheet in instance.battle_directional_sheets.items():
            with self.subTest(animation=name):
                width, height = sheet.get_size()
                for point in ((0, 0), (width - 1, 0),
                              (0, height - 1), (width - 1, height - 1)):
                    self.assertEqual(0, sheet.get_at(point).a)

                opaque = 0
                chroma = 0
                for y in range(height):
                    for x in range(width):
                        color = sheet.get_at((x, y))
                        if color.a:
                            opaque += 1
                            chroma += int(game._rian_chroma_pixel(color))
                self.assertGreater(opaque, 100)
                self.assertEqual(0, chroma)

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
