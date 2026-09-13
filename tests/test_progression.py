import json
import os
from pathlib import Path
import tempfile
import unittest
from collections import Counter, deque
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import game
from progression import ALL_TOMES, ARTS, STAT_ITEMS, STATS, make_treasure


class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ashen-growth-')
        self.savepatch = patch.object(game, 'SAVE', Path(self.temp.name)/'save.json')
        self.savepatch.start()
        with patch.object(game.Game, 'make_music', side_effect=pygame.error):
            self.g = game.Game()
        self.g.state = 'field'

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def open(self, room, slot=0):
        g = self.g
        g.room = room
        g.state = 'field'
        chest = g.treasure[room][slot]
        g.px, g.py = chest.pos
        self.assertTrue(g.open_chest(chest))
        return chest

    def key(self, key):
        self.g.event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_every_tome_has_one_chest_and_every_stat_has_three_tiers(self):
        chests = [c for v in self.g.treasure.values() for c in v]
        tomes = Counter(c.tome for c in chests if c.tome)
        self.assertEqual(set(tomes), ALL_TOMES)
        self.assertTrue(all(count == 1 for count in tomes.values()))
        self.assertEqual(73, len(chests))
        items = {name for c in chests for name, count in c.items}
        self.assertTrue(set(STAT_ITEMS) <= items)
        self.assertEqual(self.g.treasure, make_treasure(game.ROOMS))

    def test_fresh_party_only_has_basic_commands_until_tomes_are_found(self):
        g = self.g
        for h in g.party:
            h.gauge = 100
            self.assertTrue(g.command_available(h, 'Attack'))
            self.assertTrue(g.command_available(h, 'Defend'))
            self.assertFalse(g.command_available(h, h.skill))
            for art, _ in ARTS[h.name]:
                self.assertFalse(g.command_available(h, art))
        g.flags.update(('relay_a', 'relay_b', 'relay_c', 'vael_down'))
        self.assertFalse(g.ready_links())
        g.submenu = 'Arts'
        self.assertTrue(g.get_submenu(g.party[0])[0].startswith('('))

    def test_opening_teaches_only_the_matching_character(self):
        self.open('gate')
        self.assertTrue(self.g.knows(self.g.party[0], 'Frost Edge'))
        self.assertFalse(self.g.knows(self.g.party[1], 'Frost Edge'))
        self.assertEqual({'Frost Edge'}, self.g.learned)

    def test_chests_require_proximity_and_only_pay_out_once_after_reload(self):
        g = self.g
        chest = g.treasure['gate'][0]
        self.assertFalse(g.open_chest(chest))
        self.open('gate')
        items = dict(g.items)
        g.load()
        self.assertFalse(g.open_chest(chest))
        self.assertEqual(items, g.items)
        g.transition('intake')
        g.transition('gate')
        g.px, g.py = chest.pos
        g.state = 'field'
        self.assertFalse(g.open_chest(chest))

    def test_xbox_interaction_opens_chest_then_assigns_boost_with_preview(self):
        g = self.g
        g.px, g.py = g.treasure['gate'][0].pos
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertIn('Frost Edge', g.learned)
        g.state = 'field'
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=7))
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertEqual('bag', g.state)
        g.bag_index = g.bag_options().index('Strength +1')
        power = g.party[1].pow
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        g.event(pygame.event.Event(pygame.JOYHATMOTION, value=(0, -1)))
        self.assertEqual(1, g.bag_hero)
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertEqual(power, g.party[1].pow)
        self.assertTrue(g.bag_confirm)
        g.draw()
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertEqual(power + 1, g.party[1].pow)
        self.assertEqual(0, g.items['Strength +1'])

    def test_cancel_never_consumes_permanent_items(self):
        g = self.g
        g.items['HP +50'] = 1
        g.state = 'bag'
        g.bag_index = g.bag_options().index('HP +50')
        hp = g.party[0].maxhp
        self.key(pygame.K_z)
        self.key(pygame.K_z)
        self.key(pygame.K_x)
        self.key(pygame.K_x)
        self.assertEqual(1, g.items['HP +50'])
        self.assertEqual(hp, g.party[0].maxhp)

    def test_all_stat_items_persist_and_do_not_turn_into_repeatable_growth(self):
        g = self.g
        g.state = 'bag'
        for name, (stat, amount) in STAT_ITEMS.items():
            g.items[name] = 1
            old = getattr(g.party[2], stat)
            self.assertTrue(g.use_field_item(name, 2))
            self.assertEqual(old + amount, getattr(g.party[2], stat))
            self.assertFalse(g.use_field_item(name, 2))
        expected = {s: getattr(g.party[2], s) for s in STATS}
        g.load()
        self.assertEqual(expected, {s: getattr(g.party[2], s) for s in STATS})
        self.assertFalse(game.SAVE.with_suffix('.tmp').exists())

    def test_hp_mp_boosts_fill_only_added_capacity_and_do_not_revive(self):
        g = self.g
        g.state = 'bag'
        h = g.party[0]
        h.hp, h.mp = 100, 12
        g.items.update({'HP +50': 2, 'MP +15': 1})
        g.use_field_item('HP +50', 0)
        g.use_field_item('MP +15', 0)
        self.assertEqual((150, 27), (h.hp, h.mp))
        h.hp = 0
        g.use_field_item('HP +50', 0)
        self.assertEqual(0, h.hp)

    def test_speed_strength_magic_defense_and_resistance_affect_combat(self):
        g = self.g
        h = g.party[0]
        enemy = game.Enemy('scout')
        enemy.hp = 10000
        with patch.object(game.random, 'randint', return_value=0):
            old = g.damage(h, enemy, 40)
            h.pow += 5
            self.assertGreater(g.damage(h, enemy, 40), old)
            old = g.damage(h, enemy, 40, True)
            h.mag += 5
            self.assertGreater(g.damage(h, enemy, 40, True), old)
            for key, stat, turn in [('scout', 'defense', 0), ('dragon', 'resist', 2)]:
                e = game.Enemy(key)
                e.turn = turn
                h.hp = h.maxhp
                g.resolve_enemy_turn(e, h)
                damage = h.maxhp-h.hp
                setattr(h, stat, 5)
                h.hp = h.maxhp
                e.turn = turn
                g.resolve_enemy_turn(e, h)
                self.assertEqual(damage-5, h.maxhp-h.hp)
        speed = h.recharge()
        h.spd += 5
        self.assertGreater(h.recharge(), speed)

    def test_victory_grants_no_automatic_stats_or_techniques(self):
        g = self.g
        before = [vars(h).copy() for h in g.party]
        g.state = 'battle'
        g.enemies = [game.Enemy('drone')]
        g.enemies[0].hp = 0
        g.check_battle()
        self.assertEqual('victory', g.state)
        for h, values in zip(g.party, before):
            for stat in STATS:
                self.assertEqual(values[stat], getattr(h, stat))
        self.assertFalse(g.learned)

    def test_link_needs_its_tome_and_every_participants_charge(self):
        g = self.g
        self.open('nexus')
        for h in g.party:
            h.gauge = 100
            h.atb = 100
        self.assertIn('Aurora Circuit', g.ready_links())
        self.assertNotIn('Plague Canister', g.ready_links())
        g.party[1].atb = 99
        self.assertNotIn('Aurora Circuit', g.ready_links())

    def test_legacy_save_keeps_story_and_backs_up_before_growth_migration(self):
        g = self.g
        g.room = 'nexus'
        g.flags = {'seen_gate', 'relay_a'}
        g.party[0].hp = 111
        g.save()
        data = json.loads(game.SAVE.read_text())
        data['save_version'] = 2
        for key in ('learned_tomes', 'opened_chests'):
            data.pop(key)
        for h in data['party']:
            h.pop('stats')
        old = json.dumps(data)
        game.SAVE.write_text(old)
        g.load()
        self.assertEqual(('nexus', 111), (g.room, g.party[0].hp))
        self.assertIn('relay_a', g.flags)
        self.assertFalse(g.learned)
        self.assertEqual(old, game.SAVE.with_name('save-before-tomes.json').read_text())

    def test_bad_save_is_not_silently_replaced(self):
        game.SAVE.write_text('{bad')
        self.g.load()
        self.assertEqual('title', self.g.state)
        self.assertEqual('{bad', game.SAVE.read_text())

    def test_field_menu_toggles_and_persists_active_wait_mode(self):
        g = self.g
        self.assertEqual('Active', g.battle_mode)
        g.state = 'menu'
        g.room_menu = g.menu_options().index('Battle Mode: Active')
        self.key(pygame.K_z)
        self.assertEqual('Wait', g.battle_mode)
        self.assertIn('Battle Mode: Wait', g.menu_options())
        g.save()
        g.battle_mode = 'Active'
        g.load()
        self.assertEqual('Wait', g.battle_mode)

    def test_required_route_and_every_tome_are_reachable_without_shortcut_keys(self):
        seen = {'gate'}
        todo = deque(seen)
        while todo:
            room = todo.popleft()
            for dest in game.LINKS[room]:
                if tuple(sorted((room, dest))) not in game.LOCKS and dest not in seen:
                    seen.add(dest)
                    todo.append(dest)
        # The workshop is optional, with three keyed entrances. None of the
        # required route or the technique tomes depends on spending a key.
        self.assertEqual(set(game.ROOMS)-{'workshop'}, seen)
        self.assertTrue(all(c.room in seen for cs in self.g.treasure.values()
                            for c in cs if c.tome))
        self.assertGreater(len(game.LOCKS), len(game.RELAY_ROOM))
        for room, chests in self.g.treasure.items():
            self.g.room = room
            for chest in chests:
                self.assertTrue(self.g.world.walkable(chest.pos))

    def test_controller_can_draw_empty_and_full_inventories_and_all_manual_pages(self):
        g = self.g
        for items in ({}, {name: 1 for name in STAT_ITEMS}):
            g.items = {'Potion': 0, **items}
            g.state = 'bag'
            for index in range(max(1, len(g.bag_options()))):
                g.bag_index = index
                g.draw()
        g.state = 'manual'
        for typ, count in [('party', 4), ('links', 3)]:
            g.manual_type = typ
            for page in range(count):
                g.manual_page = page
                g.draw()


if __name__ == '__main__':
    unittest.main()
