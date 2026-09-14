import tempfile
import unittest
from pathlib import Path

from PIL import Image

import battle_animations
from tools.build_battle_animation_atlas import (ACTOR_H, ACTOR_W, CELL_OFFSET,
                                                 FRAME_COUNT, FRAME_H, FRAME_W,
                                                 build)


class BattleAnimationTests(unittest.TestCase):
    def test_directional_fainted_assets_are_single_transparent_cells(self):
        battle_dir = Path(__file__).parents[1] / 'assets' / 'characters' / 'battle'
        for direction in ('front_down', 'back_up', 'profile_right'):
            path = battle_dir / f'rian_fainted_{direction}_64x64.png'
            with self.subTest(direction=direction):
                image = Image.open(path).convert('RGBA')
                self.assertEqual((64, 64), image.size)
                self.assertEqual(0, image.getpixel((0, 0))[3])
                self.assertEqual(255, image.getchannel('A').getextrema()[1])

    def test_clip_ranges_cover_master_once_in_declared_order(self):
        self.assertTrue(battle_animations.validate_clip_contract())
        frames = [frame for clip in battle_animations.BATTLE_CLIPS.values()
                  for frame in clip.frames]
        self.assertEqual(list(range(29)), frames)
        self.assertEqual(4, battle_animations.BATTLE_CLIPS['sword_basic'].count)
        self.assertEqual(3, battle_animations.BATTLE_CLIPS['hurt'].count)
        self.assertEqual(2, battle_animations.BATTLE_CLIPS['defeated'].count)

    def test_delta_time_sampling_loops_and_holds(self):
        idle = battle_animations.BATTLE_CLIPS['battle_idle']
        self.assertEqual((8, False), idle.sample(0))
        self.assertEqual((8, False), idle.sample(idle.duration))
        defeated = battle_animations.BATTLE_CLIPS['defeated']
        self.assertEqual((28, True), defeated.sample(defeated.duration + 10))
        self.assertTrue(defeated.hold_last)

    def test_priorities_make_hurt_and_defeat_uninterruptible_by_idle(self):
        clips = battle_animations.BATTLE_CLIPS
        self.assertGreater(clips['hurt'].priority, clips['sword_skill'].priority)
        self.assertGreater(clips['defeated'].priority, clips['hurt'].priority)

    def test_undersized_directional_strips_match_party_reference_scale(self):
        corrected = {
            'profile_right',
            'sword_basic_front_down',
            'sword_basic_back_up',
            'sword_basic_profile_right',
        }
        self.assertEqual(corrected,
                         set(battle_animations.RIAN_UNDERSIZED_DIRECTIONAL_KEYS))
        for key in corrected:
            with self.subTest(key=key):
                self.assertEqual(1.8,battle_animations.rian_directional_scale(key))
        self.assertEqual(1.0,battle_animations.rian_directional_scale('front_down'))
        self.assertEqual(1.0,battle_animations.rian_directional_scale('hurt_profile_right'))

        try:
            import pygame
        except ImportError:
            self.skipTest('pygame is not installed in this test environment')
        sheet=pygame.Surface((256,64),pygame.SRCALPHA)
        corrected_frame=battle_animations.scaled_directional_frame(
            sheet,0,'sword_basic_front_down')
        normal_frame=battle_animations.scaled_directional_frame(
            sheet,0,'front_down')
        self.assertEqual((115,115),corrected_frame.get_size())
        self.assertEqual((64,64),normal_frame.get_size())

    def test_builder_pads_cells_without_scaling_and_removes_magenta(self):
        with tempfile.TemporaryDirectory(prefix='ashen-animation-') as folder:
            source = Path(folder) / 'master.png'
            output = Path(folder) / 'atlas.png'
            master = Image.new('RGBA', (FRAME_COUNT * FRAME_W, FRAME_H),
                               (255, 0, 255, 255))
            for frame in range(FRAME_COUNT):
                master.putpixel((frame * FRAME_W + 3, 7), (120, 190, 240, 255))
            master.save(source)
            atlas = build(source, output)
            self.assertEqual((FRAME_COUNT * ACTOR_W, ACTOR_H), atlas.size)
            for frame in range(FRAME_COUNT):
                x = frame * ACTOR_W + CELL_OFFSET[0] + 3
                y = CELL_OFFSET[1] + 7
                self.assertEqual((120, 190, 240, 255), atlas.getpixel((x, y)))
                self.assertEqual(0, atlas.getpixel((frame * ACTOR_W, 0))[3])

    def test_runtime_renderer_uses_one_to_one_source_rects(self):
        try:
            import pygame
        except ImportError:
            self.skipTest('pygame is not installed in this test environment')
        pygame.init()
        sheet = pygame.Surface((29 * ACTOR_W, ACTOR_H), pygame.SRCALPHA)
        atlas = battle_animations.BattleAnimationAtlas(sheet)
        self.assertEqual((ACTOR_W, ACTOR_H), atlas.frame_rect(28).size)
        self.assertEqual(28 * ACTOR_W, atlas.frame_rect(28).x)
        with self.assertRaises(IndexError):
            atlas.frame_rect(29)


if __name__ == '__main__':
    unittest.main()
