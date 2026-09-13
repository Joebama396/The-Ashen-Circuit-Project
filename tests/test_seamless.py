import json
import itertools
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
import game
import combat_poses


class SeamlessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ashen-test-')
        self.savepatch=patch.object(game,'SAVE',Path(self.temp.name)/'save.json')
        self.savepatch.start()
        with patch.object(game.Game,'make_music',side_effect=pygame.error):
            self.g=game.Game()
        # These tests exercise animation and combat after discovering the tomes.
        # Fresh-party unlock rules are covered separately in test_progression.
        self.g.learned=set(game.ALL_TOMES)

    def tearDown(self):
        self.savepatch.stop()
        pygame.quit()
        self.temp.cleanup()

    def field(self, room='foundry'):
        g=self.g
        g.room=room;g.state='field';g.px,g.py=105,132
        g.world.arrive()
        return g

    def settle(self, max_frames=900):
        for _ in range(max_frames):
            self.g.world.update(1/60)
            if not self.g.world.busy:return
        self.fail('Animation did not settle')

    def battle(self, room='foundry'):
        g=self.field(room)
        p=g.world.patrols[0]
        g.world.contact=p
        g.start_battle([x.unit.key for x in p.pawns],p.boss)
        self.settle()
        for h in g.party:h.atb=100
        for e in g.enemies:e.atb=0
        g.select_ready_actor(force=True)
        return g

    def action(self, hero, command, link=False):
        if link:
            for index in game.LINKS_TECH[command][0]:self.g.party[index].atb=100
        else:hero.atb=100
        self.g.turn_actor=self.g.party.index(hero)
        if link:self.g.execute_link(command)
        else:self.g.execute(hero,command)
        if self.g.world.targeting:
            self.g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))
        self.settle()

    def test_visible_enemies_are_actual_battle_objects(self):
        g=self.field()
        patrol=g.world.patrols[0]
        g.world.contact=patrol
        before=[p.pos for p in g.world.heroes+patrol.pawns]
        g.start_battle([p.unit.key for p in patrol.pawns])
        self.assertEqual(before,[p.pos for p in g.world.heroes+patrol.pawns])
        self.assertEqual(g.enemies,[p.unit for p in patrol.pawns])

    def test_ground_and_enemy_art_do_not_switch_on_contact(self):
        g=self.field()
        pawn=g.world.patrols[0].pawns[0]
        g.world.draw_ground()
        ground=pygame.image.tostring(g.canvas,'RGB')
        art=pygame.image.tostring(g.world.enemy_image(pawn),'RGBA')
        g.start_battle([p.unit.key for p in g.world.patrols[0].pawns])
        g.world.draw_ground()
        self.assertEqual(ground,pygame.image.tostring(g.canvas,'RGB'))
        self.assertEqual(art,pygame.image.tostring(g.world.enemy_image(pawn),'RGBA'))

    def test_contact_not_step_counter_starts_combat(self):
        g=self.field('intake');g.world.grace=0
        g.steps=100000
        g.px,g.py=72,133
        for _ in range(20):g.world.update(1/60)
        self.assertEqual('field',g.state)
        p=g.world.patrols[0].pawns[0]
        g.px,g.py=p.pos
        g.world.update(1/60)
        self.assertEqual('battle',g.state)
        self.assertEqual('forming',g.world.phase)

    def test_every_room_can_stage_and_draw(self):
        for room in game.ROOMS:
            with self.subTest(room=room):
                self.g.flags=set()
                g=self.field(room)
                g.draw()
                if g.world.patrols:
                    patrol=g.world.patrols[0]
                    g.start_battle([p.unit.key for p in patrol.pawns],patrol.boss)
                    self.settle();g.draw()
                    positions=[p.pos for p in g.world.heroes]
                    self.assertEqual(4,len(set(positions)))
                    self.assertGreater(max(p[0] for p in positions)-min(p[0] for p in positions),80)
                    for p in positions:
                        self.assertTrue(g.world.walkable(p))
                        self.assertLessEqual(p[1],129)

    def test_melee_moves_and_damage_happens_at_impact(self):
        g=self.battle()
        hero=g.party[0];pawn=g.world.heroes[0]
        start=pawn.pos;hp=g.enemies[0].hp
        g.execute(hero,'Attack')
        self.assertTrue(g.world.targeting)
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))
        for _ in range(15):g.world.update(1/60)
        self.assertNotEqual(start,pawn.pos)
        self.assertEqual(hp,g.enemies[0].hp)
        self.settle()
        self.assertLess(g.enemies[0].hp,hp)
        self.assertNotEqual(start,pawn.pos)
        self.assertTrue(0<hero.atb<60)

    def test_melee_uses_ground_rush_nearby_and_jump_attack_at_range(self):
        g=self.battle();hero=g.party[0];pawn=g.world.heroes[0]
        target=g.world.active.pawns[0]
        target.x,target.y=220,90;target.home=target.pos
        pawn.x,pawn.y=170,90;pawn.home=pawn.pos;hero.atb=100
        g.world.target=target.unit;g.world.queue_action(hero,'Attack')
        self.assertEqual(['run'],g.world.action['motions'])
        self.settle()

        pawn.x,pawn.y=80,90;pawn.home=pawn.pos;hero.atb=100
        target.unit.hp=target.unit.maxhp
        for e in g.enemies:e.atb=0
        g.world.target=target.unit;g.world.queue_action(hero,'Attack')
        self.assertEqual(['jump'],g.world.action['motions'])
        g.world.update(.1)
        self.assertEqual('jump_start',pawn.animation_state)
        self.assertEqual(0,pawn.air)
        g.world.update(.13)
        self.assertEqual('overhead_raise',pawn.animation_state)
        self.assertGreater(pawn.air,6)
        g.world.update(.22)
        self.assertEqual('downward_landing_strike',pawn.animation_state)
        self.settle()

    def test_overworld_sets_four_directional_moving_states_and_sway_frames(self):
        g=self.field();g.world.grace=100
        pawn=g.world.heroes[0]
        for direction,(dx,dy),state in (
            (0,(0,-3),'moving_up'),(2,(0,3),'moving_down'),
            (3,(-3,0),'moving_left'),(1,(3,0),'moving_right')):
            with self.subTest(state=state):
                g.facing=direction;g.px=pawn.x+dx;g.py=pawn.y+dy
                g.world.update(1/60)
                self.assertEqual(state,pawn.animation_state)
        first=pawn.animation_frame
        g.px=pawn.x+3;g.facing=1;g.world.update(.12)
        self.assertEqual('moving_right',pawn.animation_state)
        self.assertNotEqual(first,pawn.animation_frame)

    def test_character_profiles_and_ranged_ready_recoil_states(self):
        g=self.battle()
        rian,marek,tess,brann=g.world.heroes
        self.assertEqual(rian.profile.jump_sequence,tess.profile.jump_sequence)
        self.assertEqual('swordsman',rian.profile.name)
        self.assertEqual('dual_daggers',tess.profile.name)
        self.assertEqual('pistol',marek.profile.name)
        self.assertEqual('grenadier',brann.profile.name)

        expected=((marek,'extended_isosceles','recoil','high_ready'),
                  (brann,'shouldered_firing','heavy_recoil','low_ready'))
        for pawn,firing,recoil,idle in expected:
            for e in g.enemies:e.atb=0
            pawn.unit.atb=100;g.world.target=g.world.active.pawns[0].unit
            g.world.queue_action(pawn.unit,'Attack')
            self.assertEqual(firing,pawn.animation_state)
            g.world.update(g.world.action['duration']*.20)
            self.assertEqual(firing,pawn.animation_state)
            g.world.update(g.world.action['duration']*.31)
            self.assertEqual(recoil,pawn.animation_state)
            self.settle()
            self.assertEqual(idle,pawn.animation_state)

    def test_named_idle_combat_stances_match_each_character_role(self):
        g=self.battle()
        self.assertEqual(
            ['low_sword_ready','high_ready','split_arm_profile','low_ready'],
            [p.animation_state for p in g.world.heroes])

    def test_arm_source_rects_change_without_swapping_the_body_rect(self):
        g=self.battle();pawn=g.world.heroes[0]
        body=g.world.combat_body_source_rect(pawn).copy()
        idle=(g.world.combat_arm_source_rect(pawn,'rear').copy(),
              g.world.combat_arm_source_rect(pawn,'front').copy())
        self.assertNotEqual(idle[0],idle[1])
        self.assertEqual(idle[0],pawn.rear_arm_source_rect)
        self.assertEqual(idle[1],pawn.front_arm_source_rect)
        g.world.set_animation(pawn,'overhead_raise',0)
        raised=(g.world.combat_arm_source_rect(pawn,'rear').copy(),
                g.world.combat_arm_source_rect(pawn,'front').copy())
        self.assertEqual(body,g.world.combat_body_source_rect(pawn))
        self.assertNotEqual(idle,raised)
        self.assertEqual(raised[0],pawn.rear_arm_source_rect)
        self.assertEqual(raised[1],pawn.front_arm_source_rect)

    def test_every_named_arm_rect_contains_pixels_and_stays_inside_atlas(self):
        g=self.battle()
        for pawn in g.world.heroes:
            for state in combat_poses.HERO_POSES[pawn.hero]:
                for layer in ('rear','front'):
                    rect=combat_poses.arm_source_rect(pawn.hero,state,layer)
                    self.assertTrue(g.world.arm_sheet.get_rect().contains(rect))
                    cell=g.world.arm_sheet.subsurface(rect)
                    arm_mask=pygame.mask.from_surface(cell)
                    self.assertGreater(arm_mask.count(),0)
                    w,h=cell.get_size()
                    for edge in (pygame.Rect(0,0,w,1),pygame.Rect(0,h-1,w,1),
                                 pygame.Rect(0,0,1,h),pygame.Rect(w-1,0,1,h)):
                        self.assertEqual(0,arm_mask.overlap_area(
                            pygame.mask.Mask(edge.size,fill=True),edge.topleft))

                    body_rect=combat_poses.body_source_rect(pawn.hero)
                    body_mask=pygame.mask.from_surface(
                        g.world.combat_body_sheet.subsurface(body_rect))
                    self.assertGreater(arm_mask.overlap_area(
                        body_mask,combat_poses.ARM_SOURCE_OFFSET),0)

    def test_combat_arm_pixels_are_sliced_from_the_authored_sprite_sheet(self):
        g=self.battle()
        source_colors={tuple(g.battle_sheet.get_at((x,y)))
                       for y in range(g.battle_sheet.get_height())
                       for x in range(g.battle_sheet.get_width())}
        for hero,states in combat_poses.HERO_POSES.items():
            for state in states:
                for layer in combat_poses.ARM_LAYERS:
                    cell=g.world.arm_sheet.subsurface(
                        combat_poses.arm_source_rect(hero,state,layer))
                    colors={tuple(cell.get_at((x,y)))
                            for y in range(cell.get_height())
                            for x in range(cell.get_width())
                            if cell.get_at((x,y)).a}
                    self.assertTrue(colors)
                    self.assertTrue(colors.issubset(source_colors))

    def test_combat_world_delegates_layer_stitching_to_sprite_rig(self):
        g=self.battle();pawn=g.world.heroes[1]
        self.assertIs(g.world.arm_sheet,g.world.combat_rig.arm_sheet)
        self.assertIs(g.world.combat_body_sheet,g.world.combat_rig.body_sheet)
        before=g.world.combat_body_source_rect(pawn).copy()
        g.world.set_animation(pawn,'extended_isosceles')
        self.assertEqual(before,g.world.combat_body_source_rect(pawn))

    def test_tess_uses_split_idle_but_rian_jump_state_triggers(self):
        g=self.battle();pawn=g.world.heroes[2];target=g.world.active.pawns[0]
        self.assertEqual('split_arm_profile',pawn.animation_state)
        pawn.x,pawn.y=70,105;pawn.home=pawn.pos
        target.x,target.y=230,90;target.home=target.pos
        pawn.unit.atb=100;g.world.target=target.unit
        g.world.queue_action(pawn.unit,'Attack')
        g.world.update(.1)
        self.assertEqual('jump_start',pawn.animation_state)
        g.world.update(.13)
        self.assertEqual('overhead_raise',pawn.animation_state)
        g.world.update(.22)
        self.assertEqual('downward_landing_strike',pawn.animation_state)

    def test_idle_battle_pose_differs_from_exploration_and_draws_weapon(self):
        g=self.battle();pawn=g.world.heroes[0]
        pawn.moving=False;g.turn_actor=-1
        g.canvas.fill((0,0,0,0));g.state='field';g.world.draw_pawn(pawn)
        field=pygame.image.tostring(g.canvas,'RGBA')
        g.canvas.fill((0,0,0,0));g.state='battle';g.world.phase='idle';g.world.draw_pawn(pawn)
        stance=pygame.image.tostring(g.canvas,'RGBA')
        self.assertNotEqual(field,stance)

    def test_battle_track_starts_on_contact_and_stops_on_final_enemy(self):
        g=self.field();g.music_ready=True
        with patch.object(pygame.mixer.music,'play') as play, \
             patch.object(pygame.mixer.music,'stop') as stop:
            patrol=g.world.patrols[0];g.world.contact=patrol
            g.start_battle([p.unit.key for p in patrol.pawns])
            play.assert_called_once_with(-1)
            started_stops=stop.call_count
            for enemy in g.enemies:enemy.hp=0
            g.check_battle()
            self.assertEqual(started_stops+1,stop.call_count)
            self.assertFalse(g.battle_music_playing)

    def test_controller_selects_a_different_visible_target(self):
        g=self.battle()
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
        first=g.world.target
        g.event(pygame.event.Event(pygame.JOYHATMOTION,value=(1,0)))
        second=g.world.target
        self.assertIsNot(first,second)
        hp1,hp2=first.hp,second.hp
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
        self.settle()
        self.assertEqual(hp1,first.hp)
        self.assertLess(second.hp,hp2)

    def test_commands_cannot_interrupt_animation(self):
        g=self.battle()
        self.g.execute(g.party[0],'Defend')
        original=g.world.action
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))
        self.assertIs(original,g.world.action)
        self.assertEqual(0,g.party[0].atb)

    def test_personal_and_link_are_disabled_until_charged(self):
        g=self.battle()
        for h in g.party:h.gauge=0;h.atb=0
        self.assertEqual([],g.ready_links())
        g.cmd=1
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))
        self.assertIsNone(g.world.action)
        self.assertIsNone(g.world.targeting)

    def test_link_consumes_every_participant_once(self):
        g=self.battle()
        for h in g.party:h.gauge=100;h.hp-=100
        for i in game.LINKS_TECH['Aurora Circuit'][0]:g.party[i].atb=100
        g.turn_actor=0;g.execute_link('Aurora Circuit')
        self.assertEqual([0,0,100,100],[h.atb for h in g.party])
        self.settle()
        self.assertTrue(all(0<h.atb<60 for h in g.party[:2]))
        self.assertEqual([100,100,100,100],[h.gauge for h in g.party])
        self.assertEqual('battle',g.state)

    def test_active_enemy_attacks_without_waiting_for_player_input(self):
        g=self.battle()
        for h in g.party:h.atb=0
        for e in g.enemies:e.atb=99
        before=sum(h.hp for h in g.party)
        for _ in range(600):
            g.world.update(1/60)
            if sum(h.hp for h in g.party)<before:break
        self.assertTrue(any(h.hp<h.maxhp for h in g.party))
        self.assertTrue(any(e.turn>0 for e in g.enemies))

    def test_enemy_animation_preserves_and_accepts_submenu_navigation(self):
        g=self.battle();g.submenu='Arts';g.target=0
        enemy=g.world.active.pawns[0];enemy.unit.atb=100
        with patch('random.choice',return_value=g.world.heroes[3]):
            g.world.schedule_ready_enemy()
        self.assertTrue(g.world.enemy_action_active)
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN))
        self.assertEqual('Arts',g.submenu)
        self.assertEqual(1,g.target)
        self.assertEqual(0,g.turn_actor)
        g.draw()
        self.settle()
        self.assertEqual('Arts',g.submenu)
        self.assertEqual(1,g.target)
        self.assertEqual(0,g.turn_actor)

    def test_player_choice_during_enemy_animation_is_buffered_not_lost(self):
        g=self.battle();hero=g.party[0];g.submenu='Arts';g.target=0
        target=g.world.active.pawns[0];before=target.unit.hp
        attacker=g.world.active.pawns[1];attacker.unit.atb=100
        with patch('random.choice',return_value=g.world.heroes[3]):
            g.world.schedule_ready_enemy()
        confirm=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z)
        g.battle_input(confirm)
        self.assertIsNotNone(g.world.targeting)
        g.battle_input(confirm)
        self.assertEqual('Frost Edge',g.world.pending_player['command'])
        self.settle()
        self.assertIsNone(g.world.pending_player)
        self.assertLess(target.unit.hp,before)

    def test_wait_mode_freezes_arts_and_link_clocks_only(self):
        g=self.battle();g.battle_mode='Wait'
        for submenu in ('Arts','Link'):
            with self.subTest(submenu=submenu):
                g.submenu=submenu
                for i,h in enumerate(g.party):h.atb=40+i;h.gauge=30+i
                for i,e in enumerate(g.enemies):e.atb=20+i
                before=([h.atb for h in g.party],[h.gauge for h in g.party],
                        [e.atb for e in g.enemies])
                g.world.update(.5)
                self.assertEqual(before,([h.atb for h in g.party],
                                         [h.gauge for h in g.party],
                                         [e.atb for e in g.enemies]))
        g.submenu='Item'
        before=[h.atb for h in g.party]+[e.atb for e in g.enemies]
        g.world.update(.5)
        after=[h.atb for h in g.party]+[e.atb for e in g.enemies]
        self.assertTrue(all(b>a for a,b in zip(before,after)))

    def test_active_mode_keeps_clocks_running_in_arts_and_link(self):
        g=self.battle();g.battle_mode='Active'
        for submenu in ('Arts','Link'):
            with self.subTest(submenu=submenu):
                g.submenu=submenu
                for h in g.party:h.atb=30
                for e in g.enemies:e.atb=20
                before=[h.atb for h in g.party]+[e.atb for e in g.enemies]
                g.world.update(.25)
                after=[h.atb for h in g.party]+[e.atb for e in g.enemies]
                self.assertTrue(all(b>a for a,b in zip(before,after)))

    def test_all_clocks_keep_filling_while_a_command_target_is_open(self):
        g=self.battle();hero=g.party[0]
        g.execute(hero,'Attack');self.assertTrue(g.world.targeting)
        before=[e.atb for e in g.enemies]
        for _ in range(30):g.world.update(1/60)
        self.assertTrue(all(e.atb>a for e,a in zip(g.enemies,before)))

    def test_xbox_bumpers_switch_between_ready_characters(self):
        g=self.battle();self.assertEqual(0,g.turn_actor)
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=5))
        self.assertEqual(1,g.turn_actor)
        g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=4))
        self.assertEqual(0,g.turn_actor)

    def test_every_art_and_personal_command_finishes(self):
        for i in range(4):
            names=[x[0] for x in game.ARTS[game.new_party()[i].name]]+[game.new_party()[i].skill]
            for name in names:
                with self.subTest(name=name):
                    g=self.battle();g.turn_actor=i
                    for h in g.party:h.mp=200;h.gauge=100;h.hp=h.maxhp-100
                    self.action(g.party[i],name)
                    self.assertIn(g.state,('battle','victory'))
                    g.draw()

    def test_all_links_animate_without_repeating_rewards(self):
        for name in game.LINKS_TECH:
            with self.subTest(name=name):
                g=self.battle()
                for h in g.party:h.gauge=100
                g.flags.update(('relay_a','relay_b','relay_c','vael_down'))
                self.action(g.party[0],name,link=True)
                gold=g.gold
                for _ in range(10):g.check_battle();g.world.update(1/60);g.draw()
                self.assertEqual(gold,g.gold)

    def test_victory_removes_patrol_without_teleport_and_saves(self):
        g=self.battle()
        for e in g.enemies:e.hp=1
        g.party[3].gauge=100
        self.action(g.party[3],'Grand Payload')
        self.assertEqual('victory',g.state)
        g.draw()  # A zero-enemy victory must remain renderable.
        end=g.world.heroes[0].pos
        g.end_victory()
        self.assertEqual('field',g.state)
        self.assertEqual(end,(g.px,g.py))
        self.assertEqual([],g.world.patrols)
        g.load()
        self.assertEqual([],g.world.patrols)
        self.assertEqual(end,(g.px,g.py))

    def test_returning_to_room_respawns_farmable_patrols(self):
        g=self.battle();potions=g.items['Potion']
        for e in g.enemies:e.hp=0
        g.check_battle();g.end_victory()
        self.assertEqual(potions+1,g.items['Potion'])
        g.transition('north_hall');g.transition('foundry')
        self.assertEqual(1,len(g.world.patrols))

    def test_all_declared_exits_are_reachable_including_fifth(self):
        for room,links in game.LINKS.items():
            for destination in links:
                with self.subTest(room=room,destination=destination):
                    g=self.field(room)
                    g.flags.update(('relay_a','relay_b','relay_c','vael_down'))
                    g.open_locks=set(game.LOCKS)
                    p=dict(g.world.exits())[destination]
                    g.px,g.py=p
                    g.move(0,0)
                    self.assertEqual(destination,g.room)

    def test_locked_shortcut_consumes_one_key_only(self):
        g=self.field('barracks');g.keys=2
        g.transition('workshop')
        self.assertEqual('barracks',g.room)
        self.assertEqual(1,g.keys)
        g.state='field';g.transition('workshop')
        self.assertEqual('workshop',g.room)
        g.transition('barracks');g.transition('workshop')
        self.assertEqual(1,g.keys)

    def test_boss_stays_visible_until_contact_and_stays_dead(self):
        g=self.field('bridge')
        self.assertEqual('field',g.state)
        self.assertEqual('vael',g.world.patrols[0].boss)
        p=g.world.patrols[0].pawns[0]
        g.px,g.py=p.pos;g.world.grace=0;g.world.update(1/60)
        self.assertEqual('battle',g.state)
        self.settle()
        for e in g.enemies:e.hp=0
        g.check_battle();g.end_victory()
        self.assertIn('vael_down',g.flags)
        g.load()
        self.assertEqual([],g.world.patrols)

    def test_dragon_fires_before_combat_in_same_room(self):
        g=self.field('cradle')
        p=g.world.patrols[0].pawns[0]
        g.px,g.py=p.pos;g.world.grace=0;g.world.update(1/60)
        self.assertEqual('dialog',g.state)
        self.assertTrue(any('CAELUS LANCE: FIRED' in line for _,line in g.dialog))
        pos=p.pos
        for _ in range(len(g.dialog)):g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))
        self.assertEqual('battle',g.state)
        self.assertEqual('cradle',g.room)
        self.assertEqual(pos,g.world.active.pawns[0].pos)
        self.settle()
        for e in g.enemies:e.hp=0
        g.check_battle();g.end_victory()
        self.assertEqual('ending',g.state)
        self.assertIn('dragon_down',g.flags)

    def test_legacy_save_loads_without_new_encounter_fields(self):
        g=self.field('intake');g.save()
        data=json.loads(game.SAVE.read_text())
        del data['cleared_encounters'];del data['save_version']
        game.SAVE.write_text(json.dumps(data))
        g.load()
        self.assertEqual('intake',g.room)
        self.assertEqual(1,len(g.world.patrols))
        for hero,pawn in zip(g.party,g.world.heroes):self.assertIs(hero,pawn.unit)

    def test_dead_leader_and_poison_victory_are_safe(self):
        g=self.battle()
        g.party[0].hp=0
        for e in g.enemies:e.hp=1;e.status['poison']=3
        while g.state=='battle':
            alive=next((e for e in g.enemies if e.alive()),None)
            if not alive:break
            alive.atb=100;alive.ready_stamp=0;g.world.schedule_ready_enemy();self.settle()
        self.assertEqual('victory',g.state)
        g.draw()

    def test_idle_silhouettes_clear_each_other_across_patrol_phases(self):
        for room in game.ROOMS:
            for phase in (0,2,5,9):
                with self.subTest(room=room,phase=phase):
                    g=self.field(room)
                    g.flags=set();g.world.arrive();g.world.clock=phase
                    if not g.world.patrols:continue
                    g.world.grace=100;g.world.update(1/60)
                    patrol=g.world.patrols[0];g.world.contact=patrol
                    g.start_battle([p.unit.key for p in patrol.pawns],patrol.boss)
                    self.settle();g.world.update(1/60)
                    actors=[]
                    for p in g.world.heroes:
                        direction={0:3,1:2,2:0,3:1}[p.direction]
                        source=g.party_sheet.subsurface(((direction*8)*32,p.hero*48,32,48))
                        scale=.82*game.CHARACTER_SCALE[p.hero]
                        image=pygame.transform.scale(source,(int(32*scale),int(48*scale)))
                        actors.append((p.unit.name,pygame.mask.from_surface(image),
                                       (int(p.x-image.get_width()/2),int(p.y-image.get_height()))))
                    for p in patrol.pawns:
                        image=g.world.enemy_image(p)
                        actors.append((p.unit.name,pygame.mask.from_surface(image),
                                       (int(p.x-40),int(p.y-69))))
                    for a,b in itertools.combinations(actors,2):
                        n,m,p=a;nn,mm,pp=b
                        self.assertEqual(0,m.overlap_area(mm,(pp[0]-p[0],pp[1]-p[1])),f'{n}/{nn}')


if __name__=='__main__':
    unittest.main()
