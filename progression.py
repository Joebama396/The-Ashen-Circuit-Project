"""Finite dungeon treasure, learned techniques, and permanent character growth."""
from dataclasses import dataclass
import math

import pygame
from pixel_ui import label, panel

ARTS = {
    'Rian': [('Frost Edge', 6), ('Crystal Guard', 7), ('Glacial Formation', 12)],
    'Marek': [('Rail Shot', 6), ('Galvanize', 7), ('Chain Mend', 14), ('Defibrillate', 18)],
    'Tess': [('Venom Cut', 5), ('Corrode', 7), ('Wither', 7), ('Nerve Toxin', 11)],
    'Brann': [('Frag Grenade', 7), ('Incendiary', 9), ('Shaped Charge', 12)],
}
PERSONAL = {"Winter's Standard": 'Rian', 'Second Spark': 'Marek',
            'Toxic Bloom': 'Tess', 'Grand Payload': 'Brann'}
# The second value is retained for old art tools; story phases no longer teach Links.
LINKS_TECH = {
    'Aurora Circuit': ((0, 1), 0), 'Plague Canister': ((2, 3), 0),
    'Cryotoxin': ((0, 2), 1), 'Thermal Fracture': ((0, 3), 1),
    'Neuroshock': ((1, 2), 1), 'Thunderhead': ((1, 3), 1),
    'Permafrost Protocol': ((0, 1, 2), 2), 'Extinction Event': ((1, 2, 3), 2),
    'Zero Hour': ((0, 1, 2, 3), 3),
}
OWNERS = {name: hero for hero, arts in ARTS.items() for name, _ in arts}
OWNERS.update(PERSONAL)
ALL_TOMES = frozenset(OWNERS) | frozenset(LINKS_TECH)
COSTS = {name: cost for arts in ARTS.values() for name, cost in arts}
CONSUMABLES = ('Potion', 'Ether', 'Phoenix Gear', 'Bomb')
# All seven attributes have actual combat effects. Speed improves hidden recharge.
STATS = {'pow': ('Strength', (1, 3, 5)), 'mag': ('Magic', (1, 3, 5)),
         'defense': ('Defense', (1, 3, 5)), 'resist': ('Resistance', (1, 3, 5)),
         'spd': ('Speed', (1, 3, 5)), 'maxhp': ('HP', (10, 30, 50)),
         'maxmp': ('MP', (3, 8, 15))}
STAT_ITEMS = {f'{name} +{amount}': (stat, amount)
              for stat, (name, tiers) in STATS.items() for amount in tiers}
WHITE, GOLD, CYAN, MUTED = (235, 231, 218), (235, 179, 77), (78, 211, 219), (103, 118, 133)

# Every technique has exactly one physical source, including personal commands.
TOME_ROOMS = {
    'gate': ('Frost Edge', 'Galvanize', 'Venom Cut', 'Frag Grenade'),
    'intake': ("Winter's Standard", 'Second Spark'),
    'lift': ('Toxic Bloom', 'Grand Payload'),
    'barracks': ('Crystal Guard', 'Rail Shot'),
    'nexus': ('Aurora Circuit', 'Plague Canister'),
    'west_hall': ('Corrode',), 'archive': ('Cryotoxin', 'Glacial Formation'),
    'vault': ('Thermal Fracture',), 'relay_a': ('Permafrost Protocol',),
    'north_hall': ('Incendiary',), 'foundry': ('Thunderhead',),
    'furnace': ('Shaped Charge',), 'relay_b': ('Extinction Event',),
    'east_hall': ('Wither',), 'pumps': ('Chain Mend',),
    'reservoir': ('Neuroshock',), 'relay_c': ('Defibrillate',),
    'lower': ('Nerve Toxin',), 'ante': ('Zero Hour',),
}


@dataclass(frozen=True)
class Chest:
    uid: str
    room: str
    pos: tuple
    tome: str | None
    items: tuple


def make_treasure(rooms):
    """Stable IDs and deterministic contents: revisiting never rerolls treasure."""
    result = {}
    attributes = tuple(STATS)
    points = ((76, 80), (244, 81), (82, 136))
    for index, (room, (_, danger, _)) in enumerate(rooms.items()):
        tomes = TOME_ROOMS.get(room, ())
        tier = 0 if danger <= 1 else 1 if danger <= 3 else 2
        positions = ((76, 80), (244, 81), (82, 136), (244, 136)) if room == 'gate' else points
        chests = []
        for slot, pos in enumerate(positions):
            stat = attributes[(index * 3 + slot) % len(attributes)]
            title, tiers = STATS[stat]
            loot = [(f'{title} +{tiers[tier]}', 1)]
            if slot == 2:
                # A second growth item rewards sweeping each room thoroughly.
                vital = 'HP' if index % 2 == 0 else 'MP'
                value = STATS['maxhp' if vital == 'HP' else 'maxmp'][1][tier]
                loot.append((f'{vital} +{value}', 1))
            supply = 'Ether' if slot == 1 else 'Potion'
            loot.append((supply, 1))
            if room in ('brig', 'ante', 'workshop') and slot == 2:
                loot.append(('Phoenix Gear', 1))
            chests.append(Chest(f'{room}:chest:{slot}', room, pos,
                                tomes[slot] if slot < len(tomes) else None, tuple(loot)))
        result[room] = tuple(chests)
    return result


class ProgressionMixin:
    def init_progression(self):
        self.learned = set()
        self.opened_chests = set()
        self.bag_index = 0
        self.bag_hero = None
        self.bag_pending = None
        self.bag_confirm = False
        self.bag_message = ''

    def knows(self, hero, command):
        return command in self.learned and OWNERS.get(command) == hero.name

    def known_arts(self, hero):
        return [(name, cost) for name, cost in ARTS[hero.name] if self.knows(hero, name)]

    def command_available(self, hero, command, link=False):
        if not hero.alive():
            return False
        if link:
            return command in self.ready_links()
        if command in ('Attack', 'Defend'):
            return True
        if command in CONSUMABLES:
            return self.items.get(command, 0) > 0
        if not self.knows(hero, command):
            return False
        return hero.gauge >= 100 if command == hero.skill else hero.mp >= COSTS[command]

    def nearest_chest(self, unopened=False):
        choices = [c for c in self.treasure[self.room]
                   if not unopened or c.uid not in self.opened_chests]
        return min(choices, key=lambda c: math.dist(c.pos, (self.px, self.py)), default=None)

    def chest_in_reach(self):
        chest = self.nearest_chest(unopened=True)
        return chest if chest and math.dist(chest.pos, (self.px, self.py)) <= 22 else None

    def open_chest(self, chest):
        if (self.state != 'field' or chest.room != self.room or
                chest not in self.treasure[self.room] or
                chest.uid in self.opened_chests or math.dist(chest.pos, (self.px, self.py)) > 22):
            return False
        self.opened_chests.add(chest.uid)
        lines = []
        if chest.tome:
            self.learned.add(chest.tome)
            who = OWNERS.get(chest.tome, 'The party')
            lines.append(('TOME FOUND', f'{who} learned {chest.tome}!'))
        for name, count in chest.items:
            self.items[name] = self.items.get(name, 0) + count
        lines.append(('CACHE OPENED', 'Found: ' + ', '.join(f'{name} x{count}' for name, count in chest.items) + '.'))
        if 'growth_help' not in self.flags:
            self.flags.add('growth_help')
            lines.extend([('MAREK', 'Training imprints. A whole library packed into a book. Read one and the technique is yours.'),
                          ('TESS', 'So Brann can finally say he learned explosions from a book.'),
                          ('BRANN', 'Several books. Some survived.'),
                          ('SYSTEM', 'No levels or XP. Find tomes for techniques. Open the field menu, then Items & Growth, to assign permanent stat boosts.')])
        self.start_dialog(lines)
        self.save()
        return True

    def bag_options(self):
        return [name for name in (*CONSUMABLES[:3], *STAT_ITEMS) if self.items.get(name, 0) > 0]

    def growth_preview(self, name, hero):
        if name in STAT_ITEMS:
            stat, amount = STAT_ITEMS[name]
            return f'{STATS[stat][0]}: {getattr(hero, stat)} -> {getattr(hero, stat) + amount}'
        if name == 'Potion':
            return f'HP: {hero.hp} -> {min(hero.maxhp, hero.hp + 140)}'
        if name == 'Ether':
            return f'MP: {hero.mp} -> {min(hero.maxmp, hero.mp + 30)}'
        return f'HP: {hero.hp} -> {max(1, hero.maxhp // 3)}'

    def use_field_item(self, name, index):
        if self.state != 'bag' or name not in self.bag_options() or not 0 <= index < 4:
            return False
        hero = self.party[index]
        if name in STAT_ITEMS:
            stat, amount = STAT_ITEMS[name]
            setattr(hero, stat, getattr(hero, stat) + amount)
            if stat == 'maxhp' and hero.alive():
                hero.hp += amount
            if stat == 'maxmp':
                hero.mp += amount
        elif name == 'Potion':
            if not hero.alive() or hero.hp >= hero.maxhp:
                self.bag_message = 'Choose an injured, conscious ally.'
                return False
            hero.hp = min(hero.maxhp, hero.hp + 140)
        elif name == 'Ether':
            if hero.mp >= hero.maxmp:
                self.bag_message = 'Their MP is already full.'
                return False
            hero.mp = min(hero.maxmp, hero.mp + 30)
        elif name == 'Phoenix Gear':
            if hero.alive():
                self.bag_message = 'Choose a fallen ally.'
                return False
            hero.hp = max(1, hero.maxhp // 3)
        else:
            return False
        self.items[name] -= 1
        self.bag_message = f'{hero.name}: {name} applied.'
        self.save()
        return True

    def bag_input(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        opts = self.bag_options()
        if key in (pygame.K_x, pygame.K_ESCAPE):
            if self.bag_confirm:
                self.bag_confirm = False
            elif self.bag_hero is not None:
                self.bag_hero = None
            else:
                self.state = 'menu'
            return
        if not opts:
            return
        self.bag_index %= len(opts)
        if key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a,
                   pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d):
            if self.bag_confirm:
                return
            delta = -1 if key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a) else 1
            if self.bag_hero is None:
                self.bag_index = (self.bag_index + delta) % len(opts)
            else:
                self.bag_hero = (self.bag_hero + delta) % 4
            self.bag_message = ''
        elif key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
            if self.bag_hero is None:
                self.bag_pending = opts[self.bag_index]
                self.bag_hero = 0
            elif not self.bag_confirm:
                self.bag_confirm = True
            else:
                self.use_field_item(self.bag_pending, self.bag_hero)
                self.bag_hero = None
                self.bag_confirm = False

    def draw_bag(self):
        self.canvas.fill((11, 18, 26))
        panel(self.canvas, (4, 4, 312, 172))
        label(self.canvas, 'ITEMS & GROWTH', 12, 12, GOLD, scale=2)
        label(self.canvas, 'PERMANENT BOOSTS - CHOOSE WHO RECEIVES THEM', 12, 31, CYAN)
        opts = self.bag_options()
        if not opts:
            label(self.canvas, 'Find supplies and stat items in chests.', 12, 55, WHITE)
        elif self.bag_hero is None:
            self.bag_index %= len(opts)
            start = self.bag_index // 9 * 9
            for row, name in enumerate(opts[start:start + 9], start):
                selected = row == self.bag_index
                label(self.canvas, ('> ' if selected else '  ') + name, 12, 48 + (row-start)*11, GOLD if selected else WHITE)
                label(self.canvas, f'x{self.items[name]}', 143, 48 + (row-start)*11, CYAN)
            label(self.canvas, f'{self.bag_index + 1}/{len(opts)}', 270, 48, MUTED)
            name = opts[self.bag_index]
            for i, hero in enumerate(self.party):
                label(self.canvas, hero.name, 179, 66+i*19, CYAN)
                label(self.canvas, self.growth_preview(name, hero), 179, 74+i*19, WHITE)
        else:
            name = self.bag_pending
            label(self.canvas, name, 12, 49, GOLD)
            for i, hero in enumerate(self.party):
                col = GOLD if i == self.bag_hero else WHITE
                label(self.canvas, ('> ' if i == self.bag_hero else '  ') + hero.name, 16, 66+i*19, col)
                label(self.canvas, self.growth_preview(name, hero), 98, 66+i*19, col)
            if self.bag_confirm:
                label(self.canvas, 'A: APPLY TO ' + self.party[self.bag_hero].name, 12, 148, GOLD)
        if self.bag_message:
            label(self.canvas, self.bag_message, 12, 149, CYAN, limit=73)
        label(self.canvas, 'D-PAD: SELECT   A: CONFIRM   B: BACK', 12, 165, MUTED)

    def draw_progression_manual(self):
        s = self.canvas
        s.fill((11, 18, 26))
        panel(s, (4, 4, 312, 172))
        if self.manual_type == 'party':
            i = self.manual_page % 4
            h = self.party[i]
            self.draw_party_member(i, 39, 83, 2, 1)
            label(s, h.name, 72, 12, GOLD, scale=2)
            label(s, h.job + ' / ' + h.element, 72, 30, CYAN)
            stats = [('HP', f'{h.hp}/{h.maxhp}'), ('MP', f'{h.mp}/{h.maxmp}'),
                     ('STR', h.pow), ('MAG', h.mag), ('DEF', h.defense), ('RES', h.resist), ('SPD', h.spd)]
            for n, (name, value) in enumerate(stats):
                label(s, f'{name} {value}', 72 + (n % 3) * 78, 44 + (n // 3)*11, WHITE)
            label(s, 'LEARNED TOMES', 12, 84, GOLD)
            label(s, h.skill + (' [LEARNED]' if self.knows(h, h.skill) else ' [FIND TOME]'), 12, 97, CYAN if self.knows(h, h.skill) else MUTED)
            for n, (art, cost) in enumerate(ARTS[h.name]):
                learned = self.knows(h, art)
                label(s, art + (f'  {cost} MP' if learned else '  [FIND TOME]'), 12, 109+n*11, WHITE if learned else MUTED)
            label(s, f'{i+1}/4  LEFT/RIGHT: CHARACTER   B: BACK', 12, 165, MUTED)
        else:
            names = list(LINKS_TECH)
            page = self.manual_page % 3
            label(s, 'LINK TOMES', 12, 12, GOLD, scale=2)
            label(s, 'FIND THE TOME. CHARGE EVERY PARTICIPANT.', 12, 34, CYAN)
            for row, name in enumerate(names[page*3:page*3+3]):
                learned = name in self.learned
                people, _ = LINKS_TECH[name]
                label(s, name, 12, 55+row*32, GOLD if learned else MUTED)
                label(s, ' + '.join(self.party[i].name for i in people), 12, 65+row*32, WHITE)
                label(s, 'LEARNED' if learned else 'FIND TOME', 12, 75+row*32, CYAN if learned else MUTED)
            label(s, f'{page+1}/3  LEFT/RIGHT: PAGE   B: BACK', 12, 165, MUTED)
