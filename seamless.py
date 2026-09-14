"""Visible encounters and a single, shared exploration/combat stage.

No screenshots, alternate arenas, sprite resizing on contact, or battle wipes:
every actor retains its room coordinates when an encounter begins.
"""
from dataclasses import dataclass, field
import itertools
import math
import pygame
from battle_animations import BATTLE_CLIPS, BattleAnimationAtlas
from combat_poses import (HERO_COMBAT_PROFILES, RIAN_PROFILE, MAREK_PROFILE,
                          TESS_PROFILE, BRANN_PROFILE, CombatSpriteRig)
from pixel_ui import label, panel
from render_config import (ACTOR_CELL_H, ACTOR_CELL_W, ACTOR_GROUND_ANCHOR,
                           FORMATION_X, FORMATION_Y, GRID_X, GRID_Y, HALF_GRID, VIEW_H, VIEW_W,
                           WALK_BOUNDS, WORLD_GRID)

WHITE=(235,231,218)
CYAN=(78,211,219)
GOLD=(235,179,77)
GREEN=(112,207,119)
RED=(219,94,86)
MUTED=(76,88,99)
PURPLE=(177,115,212)
ELEMENT_COLORS=(CYAN, (130,224,238), GREEN, (250,145,67))
SUPPORT={'Defend', "Winter's Standard", 'Second Spark', 'Crystal Guard',
         'Glacial Formation', 'Galvanize', 'Chain Mend', 'Defibrillate',
         'Potion', 'Ether', 'Phoenix Gear', 'Aurora Circuit', 'Permafrost Protocol'}
SINGLE={'Attack', 'Frost Edge', 'Rail Shot', 'Venom Cut', 'Corrode', 'Wither',
        'Nerve Toxin', 'Shaped Charge', 'Bomb', 'Cryotoxin', 'Thermal Fracture',
        'Neuroshock'}
MELEE={'Attack', 'Frost Edge', 'Venom Cut', 'Cryotoxin', 'Thermal Fracture'}


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def facing(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    return (1 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 0)


MOVING_STATES={0:'moving_up',1:'moving_right',2:'moving_down',3:'moving_left'}


@dataclass
class Pawn:
    unit: object
    x: float
    y: float
    hero: int = -1
    direction: int = 2
    moving: bool = False
    goal: tuple = field(default_factory=tuple)
    home: tuple = field(default_factory=tuple)
    air: float = 0.
    profile: object = None
    animation_state: str = 'idle'
    animation_frame: int = 0
    animation_time: float = 0.
    animation_clip: str = ''
    animation_priority: int = 0
    animation_finished: bool = False
    body_source_rect: object = None
    rear_arm_source_rect: object = None
    front_arm_source_rect: object = None
    weapon_source_rect: object = None

    @property
    def pos(self):
        return self.x, self.y

    def step(self, goal, amount):
        gap=distance(self.pos, goal)
        self.moving=gap > .4
        if gap <= amount:
            self.x,self.y=goal
            return True
        self.direction=facing(self.pos, goal)
        self.x+=(goal[0]-self.x)*amount/gap
        self.y+=(goal[1]-self.y)*amount/gap
        return False


@dataclass
class Patrol:
    uid: str
    pawns: list
    boss: object = None


class WorldCombat:
    def __init__(self, game, rooms, links, locks, enemy_factory, link_tech):
        self.g=game
        self.rooms,self.links,self.locks=rooms,links,locks
        self.enemy_factory=enemy_factory
        self.link_tech=link_tech
        self.combat_rig=CombatSpriteRig(game.combat_body_sheet,game.combat_arm_sheet)
        self.battle_animation_atlas=(BattleAnimationAtlas(game.battle_animation_sheet)
                                     if game.battle_animation_sheet is not None else None)
        self.battle_directional_sheets=getattr(game,'battle_directional_sheets',{})
        self.battle_ready_sheet=game.battle_ready_sheet
        # Kept as public aliases for sprite/debug tooling. Rendering ownership
        # lives in CombatSpriteRig rather than the world/body draw loop.
        self.arm_sheet=self.combat_rig.arm_sheet
        self.combat_body_sheet=self.combat_rig.body_sheet
        self._collision_masks={}
        self.clock=0.
        self.reset()

    def reset(self):
        self.cleared=set()
        self.patrols=[]
        self.heroes=[]
        self.active=None
        self.contact=None
        self.pending_boss=None
        self.action=None
        self.pending_player=None
        self.enemy_queue=[]
        self.targeting=None
        self.target=None
        self.phase='field'
        self.phase_time=0.
        self.grace=1.
        self.floaters=[]
        self.round=1
        self.path=[]
        self.arrive()

    @property
    def busy(self):
        return self.phase in ('forming','readying','returning') or self.action is not None

    @property
    def enemy_action_active(self):
        return bool(self.action and self.action['enemy'])

    @property
    def clocks_paused(self):
        return self.g.battle_mode=='Wait' and self.g.submenu in ('Arts','Link')

    def set_animation(self,p,state,frame=None):
        if p.animation_state!=state:
            p.animation_state=state
            p.animation_time=0.
        p.animation_clip=''
        p.animation_priority=0
        p.animation_finished=False
        if frame is None:
            if state in MOVING_STATES.values():
                frame=int(p.animation_time*10)%8
            else:frame=0
        p.animation_frame=frame%8
        if p.hero>=0:
            p.rear_arm_source_rect=self.combat_rig.arm_rect(p.hero,state,'rear')
            p.front_arm_source_rect=self.combat_rig.arm_rect(p.hero,state,'front')
            p.weapon_source_rect=self.combat_rig.arm_rect(p.hero,state,'weapon')

    def has_battle_clips(self,p):
        """Rian can animate from either the atlas or directional strips."""
        return p.hero==0 and bool(self.battle_animation_atlas or
                                  self.battle_directional_sheets)

    def has_directional_clip(self,p,name):
        prefix={'sword_basic':'sword_basic_','battle_idle':'battle_idle_',
                'hurt':'hurt_','defeated':'defeated_'}.get(name,'')
        direction=('back_up' if p.direction==0 else
                   'front_down' if p.direction==2 else 'profile_right')
        return prefix+direction in self.battle_directional_sheets

    def set_battle_clip(self,p,name,restart=False,force=False):
        if not self.has_battle_clips(p) or name not in BATTLE_CLIPS:return False
        if self.battle_animation_atlas is None and not self.has_directional_clip(p,name):
            return False
        requested=BATTLE_CLIPS[name]
        active=BATTLE_CLIPS.get(p.animation_clip)
        if (not force and active and not p.animation_finished and
                active.priority>requested.priority):
            return False
        changed=p.animation_clip!=name or restart
        p.animation_clip=name
        p.animation_state=name
        p.animation_priority=requested.priority
        if changed:
            p.animation_time=0.
            p.animation_frame=requested.start
            p.animation_finished=False
        return True

    def update_battle_clip(self,p):
        clip=BATTLE_CLIPS.get(p.animation_clip)
        if not clip:return
        p.animation_frame,p.animation_finished=clip.sample(p.animation_time)
        if p.animation_finished and clip.next_clip:
            self.set_battle_clip(p,clip.next_clip,force=True)

    def battle_clip_active(self,p,minimum_priority=1):
        clip=BATTLE_CLIPS.get(p.animation_clip)
        return bool(clip and clip.priority>=minimum_priority and
                    (not p.animation_finished or clip.hold_last))

    def battle_clip_hit_ready(self,p):
        clip=BATTLE_CLIPS.get(p.animation_clip)
        if not clip or clip.impact_frame<0:return False
        frame,_=clip.sample(p.animation_time)
        return frame>=clip.start+clip.impact_frame

    def set_walk_animation(self,p):
        self.set_animation(p,MOVING_STATES[p.direction] if p.moving else 'idle')

    def collision_mask(self,p,state=None):
        """Return a union silhouette safe for either horizontal facing."""
        if p.hero>=0:
            state=state or p.profile.idle_state
            key=('hero',p.hero,state)
            if key not in self._collision_masks:
                union=pygame.mask.Mask((ACTOR_CELL_W,ACTOR_CELL_H))
                if state==p.profile.idle_state:
                    for direction in range(4):
                        image=self.battle_ready_sheet.subsurface(
                            self.g.battle_ready_source_rect(p.hero,direction))
                        union.draw(pygame.mask.from_surface(image),(0,0))
                # Reserve the decoupled rig too: actors may enter an attack
                # frame immediately after standing in a directional ready pose.
                for facing_right in (False,True):
                    image=pygame.Surface((ACTOR_CELL_W,ACTOR_CELL_H),pygame.SRCALPHA)
                    self.combat_rig.draw(image,p.hero,state,*ACTOR_GROUND_ANCHOR,
                                         facing_right)
                    union.draw(pygame.mask.from_surface(image),(0,0))
                padded=pygame.mask.Mask(union.get_size())
                for dx,dy in itertools.product((-1,0,1),repeat=2):
                    padded.draw(union,(dx,dy))
                union=padded
                self._collision_masks[key]=(union,ACTOR_GROUND_ANCHOR)
            return self._collision_masks[key]
        key=('enemy',p.unit.key)
        if key not in self._collision_masks:
            union=pygame.mask.Mask((80,76))
            saved=(p.direction,p.moving,self.clock)
            for direction,moving,clock in itertools.product((1,3),(False,True),(0.,1/7)):
                p.direction,p.moving,self.clock=direction,moving,clock
                union.draw(pygame.mask.from_surface(self.enemy_image(p)),(0,0))
            p.direction,p.moving,self.clock=saved
            padded=pygame.mask.Mask(union.get_size())
            for dx,dy in itertools.product((-1,0,1),repeat=2):
                padded.draw(union,(dx,dy))
            union=padded
            self._collision_masks[key]=(union,(40,69))
        return self._collision_masks[key]

    def exits(self):
        destinations=self.links[self.g.room]
        points=[(320,96),(608,192),(320,288),(32,192)]
        if len(destinations)>4:
            points[0]=(192,96)
            points.append((448,96))
        return list(zip(destinations, points))

    def blockers(self):
        # Only the feet collide; the tall machinery is depth-sorted at its base.
        return [pygame.Rect(48,192,48,20),pygame.Rect(544,192,48,20)]

    def walkable(self, p):
        left,right,top,bottom=WALK_BOUNDS
        return left<=p[0]<=right and top<=p[1]<=bottom and not any(
            r.inflate(WORLD_GRID//8,WORLD_GRID//10).collidepoint(p)
            for r in self.blockers())

    def clamp_point(self, p):
        """Return the nearest walkable point, preferring the room interior.

        A simple x-only fallback could leave side-door arrivals inside the
        collision base of the large doorway machinery. Search outward from the
        requested point instead so door retreats, arrivals, party trails, and
        combat destinations always land on usable floor.
        """
        left,right,top,bottom=WALK_BOUNDS
        x=round(max(left,min(right,p[0])))
        y=round(max(top,min(bottom,p[1])))
        if self.walkable((x,y)):return x,y
        center=(VIEW_W//2,VIEW_H//2)
        for radius in range(1,WORLD_GRID+1):
            ring=[]
            for offset in range(-radius,radius+1):
                ring.extend(((x+offset,y-radius),(x+offset,y+radius),
                             (x-radius,y+offset),(x+radius,y+offset)))
            ring.sort(key=lambda point:distance(point,center))
            for candidate in ring:
                if self.walkable(candidate):return candidate
        if self.walkable(center):return center
        raise RuntimeError(f'No walkable point near {p}')

    def door_interior_point(self,door,distance_in):
        """Find a safe position just inside a doorway."""
        center=(VIEW_W//2,VIEW_H//2)
        length=distance(door,center) or 1
        desired=(door[0]+(center[0]-door[0])*distance_in/length,
                 door[1]+(center[1]-door[1])*distance_in/length)
        return self.clamp_point(desired)

    def arrive(self, previous=None, repopulate=False):
        g=self.g
        self.action=None
        self.pending_player=None
        self.targeting=None
        self.target=None
        self.active=None
        self.contact=None
        self.pending_boss=None
        self.enemy_queue=[]
        self.phase='field'
        self.floaters=[]
        self.grace=1.1
        if previous is not None:
            center=(VIEW_W//2,VIEW_H//2)
            door=next((p for dest,p in self.exits() if dest==previous),(320,288))
            g.px,g.py=self.door_interior_point(door,38)
            g.facing=facing(door,center)
        else:
            # Loading an older save may restore coordinates written by the
            # former side-door retreat bug. Repair them before the party is
            # rebuilt so an affected save recovers automatically.
            g.px,g.py=self.clamp_point((g.px,g.py))
        # Preserve the familiar four-person trail, but keep everyone on-screen.
        self.heroes=[]
        trail_x=-1 if g.px>=130 else 1
        trail_y=-1 if g.py>110 else 1
        for i,h in enumerate(g.party):
            p=self.clamp_point((g.px+trail_x*i*WORLD_GRID,
                                g.py+trail_y*i*(WORLD_GRID//2)))
            self.heroes.append(Pawn(h,*p,i,g.facing,home=p,goal=p,
                                    profile=HERO_COMBAT_PROFILES[i]))
        self.path=[p.pos for p in reversed(self.heroes)]
        uid=f'{g.room}:0'
        if repopulate:
            self.cleared.discard(uid)
        self.patrols=[]
        if g.room in ('gate','barracks','workshop') or uid in self.cleared:
            return
        if g.room=='bridge':
            if 'vael_down' not in g.flags:
                self.patrols=[Patrol(uid,[self.make_enemy('vael',(352,176))],'vael')]
            return
        if g.room=='cradle':
            if 'dragon_down' not in g.flags:
                self.patrols=[Patrol(uid,[self.make_enemy('dragon',(352,192))],'dragon')]
            return
        formations={
            'intake': ('scout','drone'), 'lift': ('mite','drone'),
            'nexus': ('scout','drone'), 'west_hall': ('guard','mite'),
            'archive': ('wisp','mite'), 'vault': ('guard','soldier'),
            'relay_a': ('wisp','guard'), 'north_hall': ('soldier','drone'),
            'foundry': ('guard','drone','mite'), 'furnace': ('golem','drone'),
            'relay_b': ('golem','wisp'), 'east_hall': ('serpent','drone'),
            'pumps': ('serpent','mite'), 'reservoir': ('serpent','wisp'),
            'relay_c': ('guard','serpent'), 'lower': ('soldier','guard'),
            'brig': ('guard','drone'), 'shaft': ('mite','wisp','drone'),
            'ante': ('soldier','golem'),
        }
        layouts=[[(320,160),(448,224),(224,240)],
                 [(256,160),(416,224),(480,144)],
                 [(352,144),(256,224),(448,240)]]
        variant=list(self.rooms).index(g.room)%len(layouts)
        pawns=[self.make_enemy(k,p) for k,p in zip(formations.get(g.room,('drone',)),layouts[variant])]
        self.patrols=[Patrol(uid,pawns)]

    def make_enemy(self, key, pos):
        # Deeper wings must still matter after collecting permanent growth.
        enemy=self.enemy_factory(key,1+self.rooms[self.g.room][1]*.12)
        return Pawn(enemy,*pos,home=pos,goal=pos)

    def field_move(self, dx, dy):
        g=self.g
        proposed=(g.px+dx,g.py)
        if self.walkable(proposed):g.px=proposed[0]
        proposed=(g.px,g.py+dy)
        if self.walkable(proposed):g.py=proposed[1]
        if dx or dy:g.facing=facing((0,0),(dx,dy))
        for dest,p in self.exits():
            if distance((g.px,g.py),p)<14:
                # Retreat from a blocked/locked doorway before showing dialogue.
                g.px,g.py=self.door_interior_point(p,22)
                g.transition(dest)
                return

    def update_field(self, dt):
        g=self.g
        if not self.heroes:return
        leader=self.heroes[0]
        leader.moving=distance(leader.pos,(g.px,g.py))>.03
        leader.x,leader.y=g.px,g.py
        leader.direction=g.facing
        if not self.path or distance(self.path[-1],leader.pos)>.9:
            self.path.append(leader.pos)
            self.path=self.path[-220:]
        for i,p in enumerate(self.heroes[1:],1):
            if leader.moving:
                walked=0.
                goal=self.path[0]
                for a,b in zip(reversed(self.path[:-1]),reversed(self.path[1:])):
                    walked+=distance(a,b)
                    goal=a
                    if walked>=i*WORLD_GRID:break
                p.step(self.clamp_point(goal),120*dt)
            else:p.moving=False
        for p in self.heroes:self.set_walk_animation(p)
        if self.grace>0:self.grace=max(0,self.grace-dt)
        for patrol in self.patrols:
            for i,p in enumerate(patrol.pawns):
                old=p.pos
                if not patrol.boss:
                    phase=self.clock*.55+i*2+list(self.rooms).index(g.room)
                    p.x=p.home[0]+math.sin(phase)*14
                    p.y=p.home[1]+math.sin(phase*.8)*6
                    if distance(old,p.pos)>.01:p.direction=facing(old,p.pos)
                    p.moving=True
                radius=42 if patrol.boss=='dragon' else 26
                if not self.grace and distance(leader.pos,p.pos)<radius:
                    self.contact=patrol
                    if patrol.boss=='dragon' and 'pre_dragon' not in g.flags:
                        self.pending_boss=patrol
                        g.room_event('cradle')
                    else:g.start_battle([x.unit.key for x in patrol.pawns],patrol.boss)
                    return

    def begin(self, keys, boss=None):
        g=self.g
        self.active=self.contact
        if self.active is None:
            self.active=next((p for p in self.patrols if p.boss==boss and
                              [x.unit.key for x in p.pawns]==list(keys)),None)
        if self.active is None:
            points=[(320,160),(448,224),(224,240),(480,144)]
            self.active=Patrol(f'{g.room}:0',[self.make_enemy(k,p) for k,p in zip(keys,points)],boss)
            self.patrols.append(self.active)
        self.pending_boss=None
        self.target=None
        self.targeting=None
        self.action=None
        self.pending_player=None
        self.enemy_queue=[]
        self.round=1
        g.enemies=[p.unit for p in self.active.pawns]
        g.state='battle';g.boss=boss;g.cmd=0;g.submenu=None;g.log_wait=0
        g.turn_actor=-1
        g.log=['CONTACT! Take your positions.']
        for i,h in enumerate(g.party):
            h.guard=False;h.atb=(28,16,22,12)[i] if h.alive() else 0;h.ready_stamp=0
        for i,p in enumerate(self.active.pawns):
            p.unit.atb=18+i*9;p.unit.ready_stamp=0
        self.phase='forming';self.phase_time=0.
        self.stage_party()

    def stage_party(self):
        enemies=self.active.pawns
        cx=sum(p.x for p in enemies)/len(enemies)
        cy=sum(p.y for p in enemies)/len(enemies)
        # Every candidate derives from the shared 64-pixel world grid. The
        # 96x96 atlas cell is only transparent clearance around raw 64x80 art.
        candidates=[(x,y) for y in FORMATION_Y for x in FORMATION_X]
        # Machinery is depth-sorted scenery; only other actors reserve combat
        # cells. Foot collision still prevents exploration from walking through
        # the machine bases.
        static=[]
        for p in enemies:
            mask,anchor=self.collision_mask(p)
            static.append((mask,(round(p.x-anchor[0]),round(p.y-anchor[1]))))
        ideals=[(min(p.x for p in enemies)-WORLD_GRID,cy),
                (max(p.x for p in enemies)+WORLD_GRID,cy),
                (cx-WORLD_GRID//2,cy-WORLD_GRID//2),
                (cx+WORLD_GRID//2,cy+WORLD_GRID//2)]
        candidates=[q for q in candidates if self.walkable(q)]

        def mask_overlap(mask,origin,other,other_origin):
            return mask.overlap_area(other,(
                other_origin[0]-origin[0],other_origin[1]-origin[1]))

        entries=[]
        for i,p in enumerate(self.heroes):
            options=[]
            mask,anchor=self.collision_mask(p,p.profile.idle_state)
            for q in candidates:
                origin=(round(q[0]-anchor[0]),round(q[1]-anchor[1]))
                overlap=sum(mask_overlap(mask,origin,other,other_origin)
                            for other,other_origin in static)
                travel=distance(q,ideals[i])+distance(q,p.pos)*.12
                options.append((mask,origin,overlap,travel))
            entries.append(options)

        # Search collision-free assignments with the widest silhouettes first.
        # Candidate lists are already ordered by how closely they preserve the
        # authored battlefield spread, so the first complete solution is both
        # clear and fast to find during enemy contact.
        order=(3,0,2,1)
        ranked={i:sorted(range(len(candidates)),
                         key=lambda slot:(entries[i][slot][2],entries[i][slot][3]))
                for i in range(4)}
        chosen={}

        def compatible(hero,slot):
            mask,origin,static_overlap,_=entries[hero][slot]
            if static_overlap:return False
            for other,other_slot in chosen.items():
                other_mask,other_origin,_,_=entries[other][other_slot]
                if mask_overlap(mask,origin,other_mask,other_origin):return False
            return True

        def place(depth):
            if depth==len(order):return True
            hero=order[depth]
            for slot in ranked[hero]:
                if slot in chosen.values() or not compatible(hero,slot):continue
                chosen[hero]=slot
                if place(depth+1):return True
                del chosen[hero]
            return False

        if not place(0):
            # Extremely crowded modded encounters still receive deterministic
            # distinct slots instead of preventing combat from beginning.
            for hero in order:
                chosen[hero]=next(slot for slot in ranked[hero]
                                  if slot not in chosen.values())
        for i,slot in chosen.items():self.heroes[i].goal=candidates[slot]

    def request_action(self, hero, command, link=False):
        # Enemy animation and player menu ownership are independent. The user
        # can keep navigating and choose an action while a hostile animation is
        # playing; the choice is dispatched the instant that animation ends.
        if (self.busy and not self.enemy_action_active) or self.g.state!='battle':return
        if not hero.alive() or hero.atb<100:
            self.g.log=['That character is still charging.']
            return
        if not self.g.command_available(hero,command,link):
            self.g.log=['Technique unavailable: find its tome, charge, or restore MP.']
            return
        if command in SINGLE:
            alive=[p for p in self.active.pawns if p.unit.alive()]
            if not alive:return
            self.target=alive[0].unit
            self.targeting=(hero,command,link)
        else:self.queue_action(hero,command,link)

    def target_input(self, event):
        if not self.targeting:return False
        if event.type!=pygame.KEYDOWN:return True
        alive=[p.unit for p in self.active.pawns if p.unit.alive()]
        if event.key in (pygame.K_x,pygame.K_ESCAPE):
            self.targeting=None;self.target=None
        elif event.key in (pygame.K_LEFT,pygame.K_UP,pygame.K_a,pygame.K_w,
                            pygame.K_RIGHT,pygame.K_DOWN,pygame.K_d,pygame.K_s):
            index=alive.index(self.target) if self.target in alive else 0
            delta=-1 if event.key in (pygame.K_LEFT,pygame.K_UP,pygame.K_a,pygame.K_w) else 1
            self.target=alive[(index+delta)%len(alive)]
        elif event.key in (pygame.K_z,pygame.K_RETURN,pygame.K_SPACE):
            h,c,link=self.targeting
            self.targeting=None
            self.queue_action(h,c,link)
        return True

    def pawn_for(self, unit):
        return next((p for p in self.heroes+self.active.pawns if p.unit is unit),None)

    def landing(self,p,target,index=0,enemy=False):
        """Choose a new persistent place after acting instead of snapping home."""
        sign=-1 if p.x<target.x else 1
        candidates=[(p.x-sign*18,p.y+14),(p.x+sign*15,p.y-13),
                    (target.x+sign*(31+index*8),target.y-17+index*12),
                    (target.x+sign*(39+index*6),target.y+19-index*10)]
        occupied=[q for q in self.heroes+self.active.pawns if q is not p and q.unit.alive()]
        valid=[self.clamp_point(q) for q in candidates]
        valid=[(x,min(116,y)) for x,y in valid]
        def score(q):
            crowd=sum(max(0,27-distance(q,o.pos))*12 for o in occupied)
            return crowd+distance(q,p.pos)*.18
        return min(valid,key=score)

    def queue_action(self, hero, command, link=False):
        g=self.g
        if self.enemy_action_active:
            self.pending_player={'hero':hero,'command':command,'link':link,
                                 'target':self.target}
            g.log=[f'{command} queued.']
            return
        if self.busy:return
        actors=[self.heroes[i] for i in self.link_tech[command][0]] if link else [self.pawn_for(hero)]
        if any(p is None or not p.unit.alive() or p.unit.atb<100 for p in actors):return
        foes=[p for p in self.active.pawns if p.unit.alive()]
        if not foes:return
        target=self.pawn_for(self.target) if self.target and self.target.alive() else min(foes,key=lambda p:p.unit.hp)
        if command in SUPPORT:
            targets=[p for p in self.heroes if p.unit.alive()]
            if command in ('Potion','Galvanize','Crystal Guard'):
                targets=[min(targets,key=lambda p:p.unit.hp/p.unit.maxhp)]
            elif command=='Ether':targets=[min(self.heroes,key=lambda p:p.unit.mp/p.unit.maxmp)]
            elif command in ('Defibrillate','Phoenix Gear'):
                targets=[next((p for p in self.heroes if not p.unit.alive()),actors[0])]
            elif command=='Defend':targets=actors
        else:targets=[target] if command in SINGLE else foes
        melee=command in MELEE and any(p.hero in (0,2) for p in actors)
        destinations=[]
        endings=[]
        motions=[]
        for index,p in enumerate(actors):
            if melee and p.hero in (0,2):
                side=-1 if p.x<target.x else 1
                destinations.append(self.clamp_point((target.x+side*(23+index*6),target.y+4+index*9)))
                motions.append('jump' if distance(p.pos,target.pos)>=82 else 'run')
            else:
                destinations.append(self.clamp_point((p.x+(target.x-p.x)*.10,p.y-2)))
                motions.append('cast')
            endings.append(self.landing(p,target,index))
        for p in actors:p.unit.atb=0
        self.action={'name':command,'actors':actors,'targets':targets,'starts':[p.pos for p in actors],
                     'destinations':destinations,'endings':endings,'elapsed':0.,'duration':1.7 if link else 1.3,
                     'hit':False,'link':link,'enemy':False,'melee':melee,'motions':motions,
                     'resolve':lambda: g.resolve_link(command) if link else g.resolve_command(hero,command)}
        for p,motion in zip(actors,motions):
            if self.has_battle_clips(p):
                clip=('battle_dash' if command not in SUPPORT and
                      motion in ('run','jump') else 'battle_idle')
                self.set_battle_clip(p,clip,restart=True,force=True)
            elif motion=='jump' and p.profile in (RIAN_PROFILE,TESS_PROFILE):
                self.set_animation(p,'jump_start',0)
            elif command not in SUPPORT and p.profile is MAREK_PROFILE:
                self.set_animation(p,'extended_isosceles',0)
            elif command not in SUPPORT and p.profile is BRANN_PROFILE:
                self.set_animation(p,'shouldered_firing',0)
        self.phase='action';g.log=[command];g.log_wait=0

    def dispatch_pending_player(self):
        pending=self.pending_player
        self.pending_player=None
        if not pending or self.g.state!='battle':return
        self.target=pending['target']
        self.queue_action(pending['hero'],pending['command'],pending['link'])

    def queue_enemy(self,p):
        g=self.g
        if g.state!='battle' or not p.unit.alive():return
        targets=[h for h in self.heroes if h.unit.alive()]
        if not targets:g.check_battle();return
        # Choose once so the visual and resolved damage always agree.
        import random
        target=random.choice(targets)
        special=p.unit.key in ('vael','dragon') and (p.unit.turn+1)%3==0
        name=('Cradle Beam' if p.unit.key=='dragon' else 'Magitek Salvo') if special else p.unit.name+' attacks'
        melee=p.unit.key not in ('drone','wisp','dragon') and not special
        destination=self.clamp_point((target.x+(-19 if p.x<target.x else 19),target.y+2)) if melee else self.clamp_point((p.x+(target.x-p.x)*.08,p.y))
        ending=self.landing(p,target,enemy=True)
        p.unit.atb=0
        self.action={'name':name,'actors':[p],'targets':[target],'starts':[p.pos],
                     'destinations':[destination],'endings':[ending],'elapsed':0.,'duration':1.35 if special else 1.12,
                     'hit':False,'link':False,'enemy':True,'melee':melee,
                     'motions':['run' if melee else 'cast'],
                     'resolve':lambda p=p,t=target:g.resolve_enemy_turn(p.unit,t.unit)}
        self.phase='action';g.log=[name]

    def schedule_ready_enemy(self):
        if self.busy or self.g.state!='battle' or not self.active:return
        ready=[p for p in self.active.pawns if p.unit.alive() and p.unit.atb>=100]
        if ready:self.queue_enemy(min(ready,key=lambda p:p.unit.ready_stamp))

    def force_enemy_action(self):
        if not self.active:return
        enemy=next((p for p in self.active.pawns if p.unit.alive()),None)
        if enemy:enemy.unit.atb=100;enemy.unit.ready_stamp=self.clock;self.schedule_ready_enemy()

    def update_clocks(self,dt):
        g=self.g
        for h in g.party:
            if not h.alive():h.atb=0;continue
            before=h.atb
            h.atb=min(100,h.atb+h.atb_rate()*dt)
            h.gauge=min(100,h.gauge+h.recharge()*dt/4.2)
            if before<100<=h.atb:h.ready_stamp=self.clock
        if self.active:
            for p in self.active.pawns:
                e=p.unit
                if not e.alive():e.atb=0;continue
                before=e.atb
                speed=e.atb_rate()*(.55 if e.status.get('slow',0) else 1)
                e.atb=min(100,e.atb+speed*dt)
                if before<100<=e.atb:e.ready_stamp=self.clock
        # Do not retarget the command interface midway through any animation.
        if not self.action:g.select_ready_actor()

    def refresh_battle_animations(self):
        acting=self.action['actors'] if self.action else ()
        for p in self.heroes:
            if p in acting:continue
            if self.has_battle_clips(p):
                if not p.unit.alive():self.set_battle_clip(p,'defeated')
                elif p.animation_clip=='defeated':
                    self.set_battle_clip(p,'battle_idle',restart=True,force=True)
                elif self.battle_clip_active(p,2):continue
                elif p.moving:self.set_battle_clip(p,'battle_dash')
                else:self.set_battle_clip(p,'battle_idle')
                continue
            if not p.unit.alive():continue
            if self.phase=='forming' and p.moving:self.set_walk_animation(p)
            else:self.set_animation(p,p.profile.idle_state,0)

    def battle_roam(self,dt):
        """Everyone keeps their footing and shifts around the shared arena."""
        if not self.active:return
        acting=self.action['actors'] if self.action else ()
        pawns=self.heroes+self.active.pawns
        for index,p in enumerate(pawns):
            if any(p is actor for actor in acting) or not p.unit.alive():continue
            phase=self.clock*(.68+(index%3)*.08)+index*1.9
            radius=4 if p.hero>=0 else 6
            goal=self.clamp_point((p.home[0]+math.sin(phase)*radius,
                                    p.home[1]+math.sin(phase*.73+1.2)*3))
            saved=(p.x,p.y,p.direction,p.moving)
            p.step(goal,(12 if p.hero>=0 else 15)*dt)
            mask,anchor=self.collision_mask(p)
            origin=(int(p.x-anchor[0]),int(p.y-anchor[1]))
            blocked=False
            for other in pawns:
                if other is p or not other.unit.alive():continue
                other_mask,other_anchor=self.collision_mask(other)
                other_origin=(int(other.x-other_anchor[0]),
                              int(other.y-other_anchor[1]))
                if mask.overlap(other_mask,(other_origin[0]-origin[0],
                                            other_origin[1]-origin[1])):
                    blocked=True;break
            if blocked:p.x,p.y,p.direction,p.moving=saved

    def update(self, dt):
        self.clock+=dt
        for p in self.heroes:
            p.animation_time+=dt
        for f in self.floaters:f['ttl']-=dt
        self.floaters=[f for f in self.floaters if f['ttl']>0]
        g=self.g
        if g.state=='field':self.update_field(dt)
        elif g.state in ('battle','victory'):
            if self.phase=='forming':
                self.phase_time+=dt
                done=True
                for p in self.heroes:
                    reached=p.step(p.goal,115*dt)
                    done=reached and done
                if done:
                    self.phase='readying';self.phase_time=0.
                    for p in self.heroes:
                        p.moving=False
                        p.home=p.pos
                        nearest=min(self.active.pawns,key=lambda e:distance(e.pos,p.pos))
                        p.direction=1 if nearest.x>p.x else 3
                    g.log=['WEAPONS READY.']
            elif self.phase=='readying':
                self.phase_time+=dt
                if self.phase_time>=.42:
                    self.phase='idle'
                    g.log=['ACTIVE TIME: gauges are charging.']
            elif self.action:self.update_action(dt)
            if g.state=='battle' and self.phase not in ('forming','readying'):
                if not self.clocks_paused:self.update_clocks(dt)
                self.battle_roam(dt)
                if not self.clocks_paused:self.schedule_ready_enemy()
            if self.phase=='idle' and self.active:
                foes=[p for p in self.active.pawns if p.unit.alive()]
                if foes:
                    for p in self.heroes:
                        target=min(foes,key=lambda e:distance(e.pos,p.pos))
                        p.direction=1 if target.x>p.x else 3
                    for p in foes:
                        target=min(self.heroes,key=lambda h:distance(h.pos,p.pos))
                        p.direction=1 if target.x>p.x else 3
            if g.state in ('battle','victory'):
                self.refresh_battle_animations()
                for p in self.heroes:self.update_battle_clip(p)

    def update_action(self, dt):
        a=self.action
        a['elapsed']+=dt
        t=min(1,a['elapsed']/a['duration'])
        for p,start,impact,end,motion in zip(a['actors'],a['starts'],a['destinations'],a['endings'],a['motions']):
            jump_f=0.
            if motion=='jump' and t<.10:
                f=0.;source,destination=start,start
            elif motion=='jump' and t<.50:
                jump_f=(t-.10)/.40;f=jump_f;source,destination=start,impact
            elif t<.34:
                f=t/.34;source,destination=start,impact
            elif t<.64:
                f=1.;source,destination=impact,impact
            else:
                f=(t-.64)/.36;source,destination=impact,end
            f=f*f*(3-2*f)
            old=p.pos
            p.x=source[0]+(destination[0]-source[0])*f
            p.y=source[1]+(destination[1]-source[1])*f
            p.air=math.sin(jump_f*math.pi)*20 if motion=='jump' and .10<=t<.50 else 0
            p.moving=distance(old,p.pos)>.1
            if p.moving:p.direction=facing(old,p.pos)
            elif a['targets']:p.direction=facing(p.pos,a['targets'][0].pos)
            if not a['enemy'] and self.has_battle_clips(p):
                if a['name'] in SUPPORT:clip='battle_idle'
                else:
                    attack='sword_basic' if a['name']=='Attack' else 'sword_skill'
                    clip=(('battle_dash' if motion in ('run','jump') else 'battle_idle')
                          if t<.34 else
                          'battle_dash' if t>=.64 and p.moving else attack)
                self.set_battle_clip(p,clip)
            elif (not a['enemy'] and motion=='jump' and
                p.profile in (RIAN_PROFILE,TESS_PROFILE)):
                state=('jump_start' if t<.10 else 'overhead_raise' if t<.30
                       else 'downward_landing_strike' if t<.64 else p.profile.idle_state)
                self.set_animation(p,state,0)
            elif not a['enemy'] and a['name'] not in SUPPORT and p.profile is MAREK_PROFILE:
                self.set_animation(p,'extended_isosceles' if t<.46 else
                                   'recoil' if t<.58 else 'high_ready',0)
            elif not a['enemy'] and a['name'] not in SUPPORT and p.profile is BRANN_PROFILE:
                self.set_animation(p,'shouldered_firing' if t<.46 else
                                   'heavy_recoil' if t<.62 else 'low_ready',0)
            elif (not a['enemy'] and p.profile in (RIAN_PROFILE,TESS_PROFILE) and
                  a['name'] not in SUPPORT and .30<=t<.64):
                self.set_animation(p,'downward_landing_strike',0)
            elif p.moving:self.set_walk_animation(p)
            else:self.set_animation(p,p.profile.idle_state if p.profile else 'attack_cast',0)
        animated_impacts=[p for p in a['actors']
                          if self.has_battle_clips(p) and
                          BATTLE_CLIPS.get(p.animation_clip) and
                          BATTLE_CLIPS[p.animation_clip].impact_frame>=0]
        hit_ready=(all(self.battle_clip_hit_ready(p) for p in animated_impacts)
                   if animated_impacts else t>=.46)
        if hit_ready and not a['hit']:
            a['hit']=True
            everyone=self.heroes+self.active.pawns
            before=[(p,p.unit.hp,p.unit.mp if p.hero>=0 else 0) for p in everyone]
            a['resolve']()
            for p,hp,mp in before:
                delta=p.unit.hp-hp
                if delta:
                    self.floaters.append({'pos':p.pos,'value':f'+{delta}' if delta>0 else str(-delta),
                                          'color':GREEN if delta>0 else WHITE,'ttl':1.05})
                    if delta<0 and p.hero>=0 and self.has_battle_clips(p):
                        self.set_battle_clip(
                            p,'hurt' if p.unit.alive() else 'defeated',
                            restart=True,force=True)
                    elif (delta>0 and p.hero>=0 and self.has_battle_clips(p) and
                          p.animation_clip=='defeated'):
                        self.set_battle_clip(
                            p,'battle_idle',restart=True,force=True)
                elif p.hero>=0 and p.unit.mp>mp:
                    self.floaters.append({'pos':p.pos,'value':f'+{p.unit.mp-mp}MP','color':CYAN,'ttl':1.05})
        if t>=1:
            for p,end in zip(a['actors'],a['endings']):
                p.x,p.y=end;p.home=end;p.goal=end;p.moving=False;p.air=0
            self.action=None;self.phase='idle'
            if self.g.state=='battle':
                if a['enemy']:
                    self.g.finish_enemy_action(a['actors'][0].unit)
                    self.dispatch_pending_player()
                else:self.g.finish_hero_action(a['actors'],a['name'])

    def finish_victory(self):
        if self.active:
            self.cleared.add(self.active.uid)
            self.patrols=[p for p in self.patrols if p is not self.active]
        # The leader remains at the final room coordinate, not the room entrance.
        self.g.px,self.g.py=self.heroes[0].pos
        self.g.facing=self.heroes[0].direction
        self.path=[p.pos for p in reversed(self.heroes)]
        self.active=None;self.contact=None;self.target=None;self.targeting=None
        self.action=None;self.phase='field';self.enemy_queue=[];self.grace=1.1

    def palette(self):
        room=self.g.room
        if room in ('foundry','north_hall','furnace','relay_b','workshop'):
            return (42,38,38),(57,50,45),(85,67,52),(232,146,65)
        if room in ('pumps','reservoir','east_hall','relay_c'):
            return (27,45,52),(37,59,65),(50,85,91),CYAN
        if room in ('archive','west_hall','vault','relay_a'):
            return (38,34,49),(50,43,62),(76,61,88),PURPLE
        return (29,38,46),(39,50,58),(60,73,82),CYAN

    def draw_ground(self):
        s=self.g.canvas
        base,tile,edge,glow=self.palette()
        s.fill(base)
        pygame.draw.rect(s,(15,22,29),(0,34,VIEW_W,50))
        for x in range(0,VIEW_W,WORLD_GRID):
            pygame.draw.rect(s,tile,(x+2,42,WORLD_GRID-4,26))
            pygame.draw.line(s,edge,(x+6,42),(x+WORLD_GRID-6,42),2)
        pygame.draw.rect(s,(10,17,22),(0,72,VIEW_W,10))
        pygame.draw.line(s,edge,(0,82),(VIEW_W,82),4)
        # The placeholder room itself now exposes the same 64-pixel grid used
        # by collision and tactical placement.
        for y in range(96,VIEW_H,WORLD_GRID):
            for x in range(0,VIEW_W,WORLD_GRID):
                c=tuple(v+((x//WORLD_GRID+y//WORLD_GRID)%2)*3 for v in tile)
                pygame.draw.rect(s,c,(x+2,y+2,WORLD_GRID-4,WORLD_GRID-4))
                pygame.draw.line(s,base,(x+2,y+WORLD_GRID-3),
                                 (x+WORLD_GRID-3,y+WORLD_GRID-3),2)
                pygame.draw.rect(s,edge,(x+8,y+8,3,3))
        for x in (116,516):
            pygame.draw.rect(s,(20,28,33),(x,84,8,264))
            pygame.draw.line(s,edge,(x+2,84),(x+2,348),2)
        pygame.draw.rect(s,(19,27,32),(124,306,394,8))
        active=len(self.g.flags & {'relay_a','relay_b','relay_c'})<3
        pulse=glow if active else (77,123,112)
        for x in range(130,516,32):pygame.draw.rect(s,pulse,(x,308,12,2))
        # Room-specific insets remain visible throughout encounters.
        variant=list(self.rooms).index(self.g.room)
        if self.g.room in ('reservoir','pumps'):
            for x in range(148,504,24):
                y=318+int(math.sin(x*.05+self.clock)*4)
                pygame.draw.line(s,(60,115,127),(x,y),(x+14,y),2)
        elif self.g.room in ('foundry','furnace','north_hall'):
            for x in (174,466):
                pygame.draw.rect(s,(27,30,32),(x,90,6,188))
                for y in range(96,270,18):pygame.draw.line(s,edge,(x-6,y),(x+12,y),2)
        elif self.g.room in ('archive','vault'):
            for x in range(154,494,36):
                pygame.draw.rect(s,(25,25,37),(x,92,24,10))
                pygame.draw.rect(s,PURPLE,(x+6,94,10,2))
        if self.g.room.startswith('relay_') or self.g.room=='nexus':
            pygame.draw.ellipse(s,base,(246,144,152,80),6)
            pygame.draw.ellipse(s,edge,(256,152,132,62),2)
            pygame.draw.circle(s,pulse,(322,184),10,2)
        else:
            for n in range(3):
                x=162+(variant*46+n*122)%320
                y=112+(variant*22+n*74)%164
                pygame.draw.line(s,base,(x,y),(x+16,y+4),2)
                pygame.draw.line(s,edge,(x+6,y+6),(x+14,y+6),2)
        for dest,(x,y) in self.exits():
            locked=tuple(sorted((self.g.room,dest))) in self.locks and tuple(sorted((self.g.room,dest))) not in self.g.open_locks
            col=RED if locked else GOLD
            pygame.draw.rect(s,(13,21,27),(x-16,y-8,34,18))
            pygame.draw.line(s,col,(x-12,y+6),(x+12,y+6),4)
            if y==96:pygame.draw.polygon(s,col,[(x-6,y),(x,y-6),(x+6,y)])
            elif y==288:pygame.draw.polygon(s,col,[(x-6,y-4),(x,y+2),(x+6,y-4)])
            elif x<VIEW_W//2:pygame.draw.polygon(s,col,[(x+4,y-6),(x-2,y),(x+4,y+6)])
            else:pygame.draw.polygon(s,col,[(x-4,y-6),(x+2,y),(x-4,y+6)])

    def draw_machine(self, x):
        s=self.g.canvas
        base,tile,edge,glow=self.palette()
        pygame.draw.ellipse(s,(17,22,27),(x-8,220,60,16))
        pygame.draw.rect(s,(20,28,36),(x,140,44,88))
        pygame.draw.rect(s,(75,86,92),(x,140,36,80))
        pygame.draw.rect(s,(45,57,64),(x+4,146,28,64))
        pygame.draw.polygon(s,(105,116,119),[(x,140),(x+10,128),(x+46,128),(x+36,140)])
        pygame.draw.polygon(s,(32,41,48),[(x+36,140),(x+46,128),(x+46,212),(x+36,220)])
        pygame.draw.rect(s,(15,26,33),(x+8,156,20,24))
        pygame.draw.rect(s,glow,(x+12,162,12,8))
        for y in (190,198,206):pygame.draw.line(s,(25,35,43),(x+8,y),(x+26,y),2)

    def enemy_image(self, pawn):
        """Code-native pixel creatures, used unchanged on patrol and in combat."""
        key=pawn.unit.key
        s=pygame.Surface((80,76),pygame.SRCALPHA)
        x,y=40,69
        outline=(16,22,29)
        steel=(106,128,138)
        light=(167,186,187)
        dark=(46,63,72)
        flip=pawn.direction==3
        step=int(self.clock*7)%2 if pawn.moving else 0
        if key in ('guard','scout','soldier','vael'):
            coat={'guard':(76,94,113),'scout':(160,132,76),
                  'soldier':(157,71,68),'vael':(163,65,83)}[key]
            pygame.draw.rect(s,outline,(x-9,y-28,18,26))
            pygame.draw.rect(s,dark,(x-7,y-9,5,8-step))
            pygame.draw.rect(s,dark,(x+2,y-9,5,8+step))
            pygame.draw.rect(s,outline,(x-8,y-3-step,7,3))
            pygame.draw.rect(s,outline,(x+2,y-3+step,7,3))
            pygame.draw.rect(s,coat,(x-7,y-22,14,15))
            pygame.draw.rect(s,light,(x-6,y-22,5,5))
            pygame.draw.rect(s,steel,(x+2,y-22,6,5))
            pygame.draw.rect(s,(208,183,137),(x-4,y-29,9,7))
            pygame.draw.rect(s,steel,(x-6,y-33,13,7))
            pygame.draw.rect(s,dark,(x-3,y-27,10,3))
            pygame.draw.rect(s,(242,171,74),(x+4,y-27,2,1))
            pygame.draw.rect(s,(194,154,77),(x-7,y-10,14,2))
            if key in ('soldier','vael'):
                pygame.draw.line(s,outline,(x+10,y-2),(x+10,y-35),3)
                pygame.draw.polygon(s,light,[(x+7,y-33),(x+10,y-40),(x+13,y-33)])
            else:
                pygame.draw.rect(s,outline,(x+5,y-17,12,4))
                pygame.draw.rect(s,steel,(x+7,y-17,9,2))
        elif key=='drone':
            y-=3+int(math.sin(self.clock*3)*2)
            for side in (-1,1):
                pygame.draw.rect(s,outline,(x+side*14-4,y-17,8,7))
                pygame.draw.line(s,steel,(x+side*8,y-17),(x+side*14,y-15),3)
                pygame.draw.rect(s,CYAN,(x+side*14-2,y-10,4,3))
            pygame.draw.rect(s,outline,(x-10,y-24,20,18))
            pygame.draw.rect(s,steel,(x-8,y-23,16,12))
            pygame.draw.rect(s,light,(x-6,y-24,12,3))
            pygame.draw.rect(s,dark,(x-6,y-17,12,6))
            pygame.draw.rect(s,(255,190,84),(x-3,y-16,6,3))
            pygame.draw.line(s,light,(x,y-25),(x,y-29))
            pygame.draw.rect(s,RED,(x-1,y-30,3,2))
        elif key=='mite':
            for side in (-1,1):
                for i in range(3):
                    pygame.draw.lines(s,steel,False,[(x+side*5,y-9-i*2),
                                      (x+side*(11+i),y-12+i*4-step),
                                      (x+side*(15+i),y-4+i*2)],2)
            pygame.draw.ellipse(s,outline,(x-9,y-20,18,18))
            pygame.draw.rect(s,(119,85,149),(x-7,y-18,14,10))
            pygame.draw.rect(s,(187,129,181),(x-5,y-18,10,3))
            pygame.draw.rect(s,RED,(x+2,y-11,5,2))
        elif key=='golem':
            pygame.draw.rect(s,outline,(x-15,y-39,30,32))
            for dx in (-12,5):
                pygame.draw.rect(s,dark,(x+dx,y-10,8,10))
                pygame.draw.rect(s,outline,(x+dx-2,y-3,12,4))
            pygame.draw.rect(s,(117,92,62),(x-13,y-32,26,24))
            pygame.draw.rect(s,(172,143,88),(x-14,y-34,28,7))
            pygame.draw.rect(s,outline,(x-7,y-23,14,12))
            pygame.draw.rect(s,(250,144,56),(x-4,y-21,8,8))
            pygame.draw.rect(s,GOLD,(x-2,y-19,4,4))
            for dx in (-22,13):
                pygame.draw.rect(s,outline,(x+dx,y-27,10,21))
                pygame.draw.rect(s,(103,86,67),(x+dx+1,y-25,8,17))
            pygame.draw.rect(s,steel,(x-9,y-42,18,11))
            pygame.draw.rect(s,(244,148,66),(x-6,y-36,12,2))
        elif key=='wisp':
            y-=3+int(math.sin(self.clock*3)*3)
            pygame.draw.polygon(s,outline,[(x,y-35),(x+12,y-17),(x+5,y-3),(x-8,y-5),(x-13,y-18)])
            pygame.draw.polygon(s,(70,132,167),[(x,y-33),(x+9,y-17),(x+3,y-6),(x-7,y-7),(x-10,y-18)])
            pygame.draw.polygon(s,CYAN,[(x,y-27),(x+6,y-16),(x,y-9),(x-6,y-17)])
            pygame.draw.rect(s,WHITE,(x-3,y-20,6,7))
            pygame.draw.ellipse(s,(145,154,186),(x-15,y-18,30,8),1)
        elif key=='serpent':
            points=[(x-16,y-2),(x-7,y-7),(x+8,y-4),(x+13,y-11),(x+5,y-16),(x+6,y-26)]
            pygame.draw.lines(s,outline,False,points,9)
            pygame.draw.lines(s,(69,117,106),False,points,6)
            pygame.draw.lines(s,(122,176,132),False,points,2)
            pygame.draw.rect(s,outline,(x+1,y-31,15,10))
            pygame.draw.rect(s,(96,147,121),(x+2,y-30,14,7))
            pygame.draw.rect(s,GOLD,(x+11,y-29,2,2))
            pygame.draw.line(s,RED,(x+15,y-24),(x+19,y-23))
        elif key=='dragon':
            wing=(76,51,99);membrane=(125,70,128);armor=(143,132,159)
            pygame.draw.polygon(s,outline,[(x-8,y-16),(x-36,y-61),(x-37,y-25),(x-23,y-33),(x-22,y-12)])
            pygame.draw.polygon(s,wing,[(x-9,y-19),(x-33,y-57),(x-34,y-30),(x-23,y-37),(x-20,y-15)])
            pygame.draw.polygon(s,outline,[(x+2,y-17),(x+31,y-64),(x+36,y-26),(x+21,y-34),(x+17,y-8)])
            pygame.draw.polygon(s,membrane,[(x+4,y-22),(x+30,y-59),(x+32,y-31),(x+20,y-39),(x+14,y-14)])
            pygame.draw.lines(s,wing,False,[(x-3,y-16),(x-14,y-4),(x-29,y-3),(x-34,y-9)],8)
            pygame.draw.polygon(s,outline,[(x-17,y-23),(x-8,y-41),(x+8,y-33),(x+18,y-16),(x+10,y-3),(x-10,y-3)])
            pygame.draw.polygon(s,(101,81,125),[(x-14,y-23),(x-7,y-37),(x+7,y-30),(x+14,y-14),(x+7,y-5),(x-9,y-5)])
            pygame.draw.polygon(s,armor,[(x-4,y-32),(x+5,y-30),(x+10,y-12),(x-1,y-10)])
            pygame.draw.rect(s,outline,(x+5,y-46,20,13))
            pygame.draw.rect(s,(134,107,147),(x+6,y-44,19,9))
            pygame.draw.polygon(s,GOLD,[(x+8,y-44),(x+5,y-53),(x+12,y-44)])
            pygame.draw.rect(s,(255,157,92),(x+20,y-42,3,2))
            pygame.draw.rect(s,WHITE,(x+21,y-36,3,2))
            for dx in (-13,8):
                pygame.draw.rect(s,wing,(x+dx,y-13,7,11))
                pygame.draw.line(s,armor,(x+dx-1,y-2),(x+dx+8,y-2),3)
            pygame.draw.line(s,CYAN,(x-5,y-26),(x-1,y-13),2)
        if flip:s=pygame.transform.flip(s,True,False)
        return s

    def combat_body_source_rect(self,p):
        """Combat torso/legs stay on one source rect while arm state changes."""
        p.body_source_rect=self.combat_rig.body_rect(p.hero)
        return p.body_source_rect

    def combat_arm_source_rect(self,p,layer):
        cached={'rear':p.rear_arm_source_rect,
                'front':p.front_arm_source_rect,
                'weapon':p.weapon_source_rect}[layer]
        return cached or self.combat_rig.arm_rect(p.hero,p.animation_state,layer)

    def draw_combat_arm(self,p,layer,x,y):
        self.combat_rig.draw_arm(
            self.g.canvas,p.hero,p.animation_state,layer,x,y,p.direction==1)

    def draw_combat_body(self,p,x,y):
        self.combat_rig.draw_body(
            self.g.canvas,p.hero,x,y,p.direction==1)

    def draw_battle_ready(self,p,x,y):
        image=self.battle_ready_sheet.subsurface(
            self.g.battle_ready_source_rect(p.hero,p.direction))
        self.g.canvas.blit(image,(round(x-ACTOR_GROUND_ANCHOR[0]),
                                  round(y-ACTOR_GROUND_ANCHOR[1])))

    def draw_pawn(self, p, draw_shadow=True):
        g=self.g;s=g.canvas
        x,ground_y=int(p.x),int(p.y)
        y=ground_y-int(p.air)
        if draw_shadow:pygame.draw.ellipse(s,(16,24,28),(x-20,ground_y-5,40,10))
        if p.hero>=0:
            if (g.state=='battle' and p.hero==g.turn_actor and
                (not self.busy or self.enemy_action_active)):
                pygame.draw.ellipse(s,ELEMENT_COLORS[p.hero],(x-22,ground_y-6,44,12),2)
                pygame.draw.polygon(s,GOLD,[(x-5,y-92),(x+5,y-92),(x,y-86)])
            combat_rig=(g.state in ('battle','victory','gameover') and self.phase!='forming')
            full_frame=(combat_rig and self.battle_animation_atlas is not None and
                        p.hero==0 and
                        p.animation_clip in BATTLE_CLIPS)
            directional=self._directional_frame(p) if combat_rig else None
            if directional is not None:
                sheet, local_frame=directional
                src=sheet.subsurface(pygame.Rect(local_frame*64,0,64,64))
                s.blit(src,(round(x-32),round(y-64)))
            elif full_frame:
                self.battle_animation_atlas.draw(
                    s,p.animation_frame,x,y,p.direction==1)
            elif p.unit.alive():
                if combat_rig:
                    if p.animation_state==p.profile.idle_state:
                        self.draw_battle_ready(p,x,y)
                    else:
                        # Attack states retain the decoupled arm/body rig.
                        self.combat_rig.draw(
                            s,p.hero,p.animation_state,x,y,p.direction==1)
                else:g.draw_party_member(p.hero,x,y,p.direction,p.animation_frame)
            else:
                # A consistent prone pose, not an abruptly missing party member.
                src=g.party_sheet.subsurface(g.party_source_rect(p.hero,2,4)).copy()
                src.set_alpha(130)
                s.blit(src,(x-ACTOR_GROUND_ANCHOR[0],
                            ground_y-ACTOR_GROUND_ANCHOR[1]))

        elif p.unit.alive():
            s.blit(self.enemy_image(p),(x-40,y-69))
            if g.state=='battle':
                pygame.draw.rect(s,(19,26,31),(x-9,y+3,18,2))
                pygame.draw.rect(s,RED,(x-9,y+3,max(1,int(18*p.unit.hp/p.unit.maxhp)),2))
                pygame.draw.rect(s,(19,26,31),(x-9,y+7,18,2))
                if p.unit.atb:pygame.draw.rect(s,GOLD,(x-9,y+7,max(1,int(18*p.unit.atb/100)),2))
                if p.unit.status.get('poison',0):label(s,'P',x+12,y-15,GREEN)
                if p.unit.status.get('slow',0):label(s,'S',x+12,y-7,CYAN)
            if self.target is p.unit and self.targeting:
                pygame.draw.ellipse(s,RED,(x-14,y-4,28,8),1)
                pygame.draw.polygon(s,WHITE,[(x-3,y-39),(x+3,y-39),(x,y-35)])

    def _directional_frame(self,p):
        """Return an authored 64px directional strip frame when available."""
        if p.hero!=0 or p.animation_clip not in ('battle_idle','battle_dash','sword_basic','hurt','defeated'):
            return None
        prefix={'sword_basic':'sword_basic_','battle_idle':'battle_idle_',
                'hurt':'hurt_','defeated':'defeated_'}.get(p.animation_clip,'')
        if p.direction==0:
            sheet=self.battle_directional_sheets.get(prefix+'back_up')
        elif p.direction==2:
            sheet=self.battle_directional_sheets.get(prefix+'front_down')
        else:
            sheet=self.battle_directional_sheets.get(prefix+'profile_right')
        if sheet is None:return None
        clip=BATTLE_CLIPS[p.animation_clip]
        # Stationary battle idle is deliberately a held guard pose.  Motion is
        # reserved for battle_dash, whose four frames supply the guarded walk.
        local_frame=0 if p.animation_clip in ('battle_idle','defeated') else p.animation_frame-clip.start
        return sheet,local_frame

    def draw_scene(self, hud=True):
        self.draw_ground()
        layers=[(230,lambda:self.draw_machine(56)),(230,lambda:self.draw_machine(540))]
        for chest in self.g.treasure[self.g.room]:
            layers.append((chest.pos[1],lambda chest=chest:self.draw_chest(chest)))
        for patrol in self.patrols:
            for p in patrol.pawns:
                layers.append((p.y,lambda p=p:self.draw_pawn(p)))
        for p in self.heroes:layers.append((p.y,lambda p=p:self.draw_pawn(p)))
        for _,draw in sorted(layers,key=lambda item:item[0]):draw()
        self.draw_effects()
        if hud:
            draw=self.draw_battle_hud if self.g.state in ('battle','victory') else self.draw_field_hud
            self.g.draw_ui_overlay(draw)

    def draw_heroes_only(self):
        """Redraw only playable characters above the game-over fade."""
        for p in sorted(self.heroes,key=lambda pawn:pawn.y):
            self.draw_pawn(p,draw_shadow=False)

    def draw_chest(self, chest):
        s=self.g.canvas;x,y=chest.pos
        opened=chest.uid in self.g.opened_chests
        trim=MUTED if opened else CYAN if chest.tome else GOLD
        pygame.draw.ellipse(s,(16,24,28),(x-18,y-4,40,10))
        pygame.draw.rect(s,(14,22,29),(x-18,y-24,36,26))
        pygame.draw.rect(s,(80,61,49),(x-14,y-20,28,18))
        pygame.draw.rect(s,trim,(x-16,y-22,32,8),2)
        pygame.draw.line(s,trim,(x-12,y-12),(x+12,y-12),2)
        for dx in (-12,10):pygame.draw.line(s,trim,(x+dx,y-20),(x+dx,y-4),2)
        if opened:
            pygame.draw.rect(s,(12,18,24),(x-12,y-18,24,8))
            pygame.draw.rect(s,MUTED,(x-16,y-32,32,8),2)
        elif chest.tome:
            pygame.draw.rect(s,(225,221,185),(x-4,y-22,10,8))
            pygame.draw.line(s,(53,80,89),(x,y-22),(x,y-16),2)
        else:pygame.draw.rect(s,GOLD,(x-2,y-14,6,6))

    def draw_effects(self):
        s=self.g.canvas
        if self.action:
            a=self.action;t=a['elapsed']/a['duration']
            color=RED if a['enemy'] else ELEMENT_COLORS[a['actors'][0].hero]
            if a['link']:
                points=[(int(p.x),int(p.y-12)) for p in a['actors']]
                if len(points)>1:pygame.draw.lines(s,color,False,points,1)
                for p in a['actors']:pygame.draw.ellipse(s,color,(p.x-12,p.y-4,24,7),1)
            if .28<t<.46 and not a['melee'] and a['name'] not in SUPPORT:
                travel=(t-.28)/.18
                for source in a['actors']:
                    for target in a['targets']:
                        start=(source.x,source.y-source.air-18)
                        end=(target.x,target.y-target.air-15)
                        x=start[0]+(end[0]-start[0])*travel
                        y=start[1]+(end[1]-start[1])*travel
                        if source.hero==3 or a['name'] in ('Bomb','Plague Canister'):
                            y-=math.sin(travel*math.pi)*22
                            pygame.draw.rect(s,(23,27,31),(int(x)-2,int(y)-2,5,5))
                            pygame.draw.rect(s,GOLD,(int(x),int(y)-3,2,2))
                        else:
                            # A bright, fast slug for Marek; no continuous lightning beam.
                            dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy) or 1
                            tail=(x-dx/length*8,y-dy/length*8)
                            pygame.draw.line(s,color,tail,(x,y),1)
                            pygame.draw.rect(s,WHITE,(int(x)-1,int(y)-1,3,2))
            if .46<=t<.76:
                progress=(t-.46)/.30
                for target in a['targets']:
                    x,y=int(target.x),int(target.y)-15
                    if a['name'] in SUPPORT:
                        for n in range(3):
                            yy=y+12-int(progress*18)-n*8
                            pygame.draw.line(s,GREEN,(x-3,yy),(x+3,yy))
                            pygame.draw.line(s,GREEN,(x,yy-3),(x,yy+3))
                    elif a['melee']:
                        length=int(7+progress*13)
                        pygame.draw.line(s,WHITE,(x-length,y+length//2),(x+length,y-length//2),2)
                        pygame.draw.line(s,color,(x-length+2,y+length//2+3),(x+length,y-length//2+3))
                    else:
                        radius=int(4+progress*16)
                        pygame.draw.circle(s,color,(x,y),radius,2)
                        for n in range(6):
                            angle=n*math.pi/3+progress
                            px=x+int(math.cos(angle)*radius);py=y+int(math.sin(angle)*radius)
                            pygame.draw.rect(s,GOLD,(px,py,2,2))
        for f in self.floaters:
            x,y=f['pos'];age=1.05-f['ttl']
            value=f['value'];xx=int(x-len(value)*2);yy=int(y-32-age*15)
            label(s,value,xx+1,yy+1,(10,15,22))
            label(s,value,xx,yy,f['color'])

    def draw_field_hud(self):
        g=self.g;s=g.canvas
        pygame.draw.rect(s,(8,14,22),(0,0,320,20))
        label(s,self.rooms[g.room][0],5,2,GOLD,limit=31)
        label(s,f'K{g.keys} P{g.items["Potion"]} R{len(g.flags & {"relay_a","relay_b","relay_c"})}/3',232,2,CYAN)
        label(s,'DOMINION RESTORATION SITE',5,11,MUTED)
        near=next(((d,p) for d,p in self.exits() if distance((g.px,g.py),p)<30),None)
        chest=g.chest_in_reach()
        if chest:
            msg='A: OPEN '+('TOME CACHE' if chest.tome else 'SUPPLY CACHE')
        elif near:
            dest,p=near
            locked=tuple(sorted((g.room,dest))) in self.locks and tuple(sorted((g.room,dest))) not in g.open_locks
            msg=('LOCKED: ' if locked else 'TO: ')+self.rooms[dest][0]
        elif g.toast_t:msg=g.toast
        elif self.patrols:msg='VISIBLE PATROL - MAKE CONTACT TO ENGAGE'
        else:msg='AREA CLEAR - A: INTERACT   START: MENU'
        panel(s,(3,163,314,15))
        label(s,msg,8,167,WHITE,limit=50)

    def draw_battle_hud(self):
        g=self.g;s=g.canvas
        if self.targeting:
            message=f'TARGET {self.target.name}  {self.target.hp}/{self.target.maxhp}'
            message_color=RED
        else:
            message=g.log[-1] if g.log else 'CONTACT'
            message_color=WHITE
            if (g.state=='battle' and (not self.busy or self.enemy_action_active) and
                not g.submenu and g.cmd==1 and g.turn_actor>=0):
                h=g.party[g.turn_actor]
                message=h.skill+(' / FIND TOME' if not g.knows(h,h.skill) else ' / READY' if h.gauge>=100 else ' / RECHARGING')
        # Compact floating chips preserve the room behind them instead of
        # covering the entire top fifth with an opaque debug-style banner.
        panel(s,(3,3,236,14))
        label(s,message,7,7,message_color,limit=37)
        mode_color=GOLD if self.clocks_paused else CYAN
        panel(s,(263,3,54,14),mode_color)
        label(s,'WAIT' if g.battle_mode=='Wait' else 'ACTIVE',
              274 if g.battle_mode=='Wait' else 272,7,mode_color)

        # One continuous lower plate, divided only where commands and party
        # telemetry actually differ. Four tighter rows expose ten more pixels
        # of the shared battlefield than the previous double-window layout.
        panel(s,(2,132,316,46))
        pygame.draw.line(s,(67,84,95),(105,133),(105,177))
        for i,h in enumerate(g.party):
            y=136+i*10
            col=WHITE if h.alive() else MUTED
            if i==g.turn_actor and g.state=='battle':label(s,'>',109,y,GOLD)
            label(s,h.name,117,y,col,limit=5)
            label(s,f'H{h.hp}',150,y,col,limit=5)
            label(s,f'M{h.mp}',181,y,CYAN if h.alive() else MUTED,limit=4)
            pygame.draw.rect(s,(29,42,51),(207,y,105,7))
            pygame.draw.rect(s,(63,78,87),(208,y+1,103,5))
            fill=int(103*h.atb/100) if h.alive() else 0
            if fill:pygame.draw.rect(s,ELEMENT_COLORS[i],(208,y+1,fill,5))
            if h.atb>=100 and h.alive():
                pygame.draw.rect(s,WHITE,(207,y,105,7),1)
                if h.gauge>=100:pygame.draw.rect(s,GOLD,(307,y+2,3,3))
        if g.state=='victory':
            label(s,'VICTORY',8,137,GOLD)
            label(s,'A CONTINUE',8,158,WHITE)
            return
        if self.phase=='forming':
            label(s,'CONTACT',8,137,GOLD)
            label(s,'FORMING UP',8,152,WHITE)
            return
        if self.phase=='readying':
            label(s,'READY',8,137,GOLD)
            label(s,'DRAW WEAPONS',8,152,WHITE)
            return
        menu_owns_hud=bool(self.enemy_action_active and
                           (self.targeting or g.submenu or g.turn_actor>=0))
        if self.action and not menu_owns_hud:
            label(s,'ACTION',8,136,RED if self.action['enemy'] else GOLD)
            words=self.action['name'].split();lines=['']
            for word in words:
                if len(lines[-1])+len(word)+1>16:lines.append(word)
                else:lines[-1]=(lines[-1]+' '+word).strip()
            for n,line in enumerate(lines[:2]):label(s,line,8,150+n*10,WHITE,limit=16)
            return
        if self.pending_player:
            label(s,'QUEUED',8,136,GOLD)
            label(s,self.pending_player['command'],8,150,WHITE,limit=16)
            return
        if self.targeting:
            label(s,'TARGET',8,136,RED)
            label(s,'D-PAD CYCLE',8,150,WHITE)
            label(s,'A GO B BACK',8,161,WHITE)
            return
        if g.turn_actor<0:
            label(s,'ACTIVE TIME',8,137,CYAN)
            label(s,'TIME FLOWS',8,152,WHITE)
            return
        hero=g.party[g.turn_actor]
        if g.submenu:
            panel(s,(2,121,316,57))
            opts=g.get_submenu(hero)
            page=g.target//6
            label(s,f'{g.submenu} {page+1}/{max(1,(len(opts)+5)//6)}',8,125,GOLD)
            label(s,'A SELECT  B BACK',212,125,MUTED)
            for index,opt in enumerate(opts[page*6:page*6+6],page*6):
                local=index-page*6;col=local//3;row=local%3
                color=GOLD if index==g.target else WHITE
                if g.submenu=='Arts' and (opt.startswith('(') or int(opt.rsplit(' ',1)[1][:-2])>hero.mp):color=MUTED
                label(s,('>' if index==g.target else ' ')+opt,7+col*157,138+row*11,color,limit=25)
            return
        label(s,hero.name+' READY',8,136,GOLD)
        short=['ATTACK','SKILL','ARTS','LINK','ITEM','DEFEND']
        for i,name in enumerate(short):
            row=i%3;col=i//3
            disabled=(i==1 and (hero.gauge<100 or not g.knows(hero,hero.skill))) or (i==2 and not g.known_arts(hero)) or (i==3 and not g.ready_links())
            color=MUTED if disabled else GOLD if i==g.cmd else WHITE
            label(s,('>' if i==g.cmd else ' ')+name,6+col*49,149+row*9,color)
