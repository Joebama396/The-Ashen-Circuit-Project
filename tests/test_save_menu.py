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
from save_menu import GAMEPLAY, SAVE_MENU, TITLE, SaveMenu, read_save_slots


class SaveMenuTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-slots-')
        root = Path(self.temp.name)
        self.paths = [root / 'save.json', root / 'save-2.json',
                      root / 'save-3.json']
        self.loaded = []

    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()

    def key(self, menu, key):
        return menu.handle_input(
            pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_reader_loads_metadata_and_keeps_empty_slot(self):
        self.paths[0].write_text(json.dumps({
            'metadata': {'name': 'Rian', 'location': 'Central Dynamo',
                         'objective': 'Sever the relays', 'playtime': 3723}}))
        self.paths[2].write_text(json.dumps({
            'room': 'gate', 'playtime': 65, 'party': [{}]}))
        slots = read_save_slots(self.paths, {'gate': 'Broken Processional'})
        self.assertEqual(
            ('Rian', 'Central Dynamo', 'Sever the relays', '01:02:03'),
            tuple(slots[0][key] for key in
                  ('name', 'location', 'objective', 'playtime')))
        self.assertFalse(slots[1]['occupied'])
        self.assertEqual('Broken Processional', slots[2]['location'])
        self.assertEqual('00:01:05', slots[2]['playtime'])

    def test_navigation_wraps_and_only_populated_slot_loads(self):
        self.paths[0].write_text(json.dumps({'room': 'gate', 'playtime': 0}))
        menu = SaveMenu(slot_paths=lambda: self.paths,
                        on_load=lambda slot: self.loaded.append(slot) or True)
        self.assertEqual(SAVE_MENU, self.key(menu, pygame.K_UP))
        self.assertEqual(2, menu.selected_slot)
        self.assertEqual(SAVE_MENU, self.key(menu, pygame.K_SPACE))
        self.assertEqual([], self.loaded)
        self.key(menu, pygame.K_DOWN)
        self.assertEqual(0, menu.selected_slot)
        self.assertEqual(GAMEPLAY, self.key(menu, pygame.K_RETURN))
        self.assertEqual([1], self.loaded)

    def test_escape_and_backspace_return_to_title(self):
        menu = SaveMenu(slot_paths=lambda: self.paths)
        self.assertEqual(TITLE, self.key(menu, pygame.K_ESCAPE))
        self.assertEqual(TITLE, self.key(menu, pygame.K_BACKSPACE))

    def test_draw_renders_three_distinct_cards(self):
        self.paths[1].write_text(json.dumps({
            'metadata': {'name': 'Rian', 'location': 'Mnemonic Archive',
                         'objective': 'Defeat Commander Vael',
                         'playtime': 500}}))
        menu = SaveMenu(slot_paths=lambda: self.paths)
        surface = pygame.Surface((320, 180))
        surface.fill((8, 9, 18))
        menu.draw(surface)
        for y in (30, 73, 116):
            self.assertNotEqual((8, 9, 18), surface.get_at((11, y))[:3])


class GameSaveSlotIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-game-slots-')
        self.savepatch = patch.object(
            game, 'SAVE', Path(self.temp.name) / 'save.json')
        self.savepatch.start()
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            self.g = game.Game()
        self.g.state = 'field'

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def test_game_saves_and_loads_the_active_slot(self):
        self.g.active_save_slot = 2
        self.g.room = 'archive'
        self.g.playtime = 3661
        self.g.save()
        path = game.save_path_for_slot(2)
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual('Rian', data['metadata']['name'])
        self.assertEqual('Mnemonic Archive', data['metadata']['location'])
        self.assertEqual('Reach the Central Dynamo',
                         data['metadata']['objective'])
        self.g.room = 'gate'
        self.assertTrue(self.g.load_from_title(2))
        self.assertEqual(('archive', 2),
                         (self.g.room, self.g.active_save_slot))

    def test_objective_metadata_tracks_story_without_levels(self):
        cases = (
            (set(), 'Reach the Central Dynamo'),
            ({'seen_nexus'}, 'Sever the relays (3 remaining)'),
            ({'relay_a'}, 'Sever the relays (2 remaining)'),
            ({'relay_a', 'relay_b', 'relay_c'}, 'Defeat Commander Vael'),
            ({'relay_a', 'relay_b', 'relay_c', 'vael_down'},
             'Enter the Dragon Cradle'),
            ({'pre_dragon'}, 'Defeat Vharos'),
            ({'dragon_down'}, 'Vharos defeated'),
        )
        for flags, expected in cases:
            with self.subTest(flags=flags):
                self.assertEqual(expected, game.objective_for_progress(flags))


if __name__ == '__main__':
    unittest.main()
