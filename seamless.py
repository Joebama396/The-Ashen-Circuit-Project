"""Visible encounters and a single, shared exploration/combat stage.

No screenshots, alternate arenas, sprite resizing on contact, or battle wipes:
every actor retains its room coordinates when an encounter begins.
"""
from dataclasses import dataclass, field
import math
import pygame
from pixel_ui import label, panel

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

    def exits(self):
        destinations=self.links[self.g.room]
        points=[(160,49),(305,96),(160,147),(15,96)]
        if len(destinations)>4:
            points[0]=(108,49)
            points.append((220,49))
        return list(zip(destinations, points))

    def blockers(self):
        # Only the feet collide; the tall machinery is depth-sorted at its base.
        return [pygame.Rect(28,101,22,14), pygame.Rect(270,101,22,14)]

    def walkable(self, p):
        return 12<=p[0]<=308 and 49<=p[1]<=148 and not any(
            r.inflate(8,6).collidepoint(p) for r in self.blockers())

    def clamp_point(self, p):
        x,y=max(18,min(302,p[0])),max(57,min(144,p[1]))
        if not self.walkable((x,y)):
            x=62 if x<160 else 258
        return x,y

    def arrive(self, previous=None, repopulate=False):
        g=self.g
        self.action=None
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
            door=next((p for dest,p in self.exits() if dest==previous), (160,147))
            length=distance(door,(160,100)) or 1
            g.px,g.py=self.clamp_point((door[0]+(160-door[0])*19/length,
                                        door[1]+(100-door[1])*19/length))
            g.facing=facing(door,(160,100))
        # Preserve the familiar four-person trail, but keep everyone on-screen.
        self.heroes=[]
        trail_x=-1 if g.px>=130 else 1
        trail_y=-1 if g.py>110 else 1
        for i,h in enumerate(g.party):
            p=self.clamp_point((g.px+trail_x*i*22, g.py+trail_y*i*10))
            self.heroes.append(Pawn(h,*p,i,g.facing,home=p,goal=p))
        self.path=[p.pos for p in reversed(self.heroes)]
        uid=f'{g.room}:0'
        if repopulate:
            self.cleared.discard(uid)
        self.patrols=[]
        if g.room in ('gate','barracks','workshop') or uid in self.cleared:
            return
        if g.room=='bridge':
            if 'vael_down' not in g.flags:
                self.patrols=[Patrol(uid,[self.make_enemy('vael',(175,89))],'vael')]
            return
        if g.room=='cradle':
            if 'dragon_down' not in g.flags:
                self.patrols=[Patrol(uid,[self.make_enemy('dragon',(170,99))],'dragon')]
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
        layouts=[[(150,86),(205,111),(104,119)],
                 [(117,85),(197,109),(231,75)],
                 [(181,75),(127,111),(222,121)]]
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
            if distance((g.px,g.py),p)<7:
                # Retreat from a blocked/locked doorway before showing dialogue.
                norm=distance(p,(160,100)) or 1
                retreat=(p[0]+(160-p[0])*11/norm,p[1]+(100-p[1])*11/norm)
                g.px,g.py=retreat
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
                    if walked>=i*22:break
                p.step(self.clamp_point(goal),74*dt)
            else:p.moving=False
        if self.grace>0:self.grace=max(0,self.grace-dt)
        for patrol in self.patrols:
            for i,p in enumerate(patrol.pawns):
                old=p.pos
                if not patrol.boss:
                    phase=self.clock*.55+i*2+list(self.rooms).index(g.room)
                    p.x=p.home[0]+math.sin(phase)*7
                    p.y=p.home[1]+math.sin(phase*.8)*3
                    if distance(old,p.pos)>.01:p.direction=facing(old,p.pos)
                    p.moving=True
                radius=21 if patrol.boss=='dragon' else 13
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
            points=[(155,87),(211,110),(103,118),(230,72)]
            self.active=Patrol(f'{g.room}:0',[self.make_enemy(k,p) for k,p in zip(keys,points)],boss)
            self.patrols.append(self.active)
        self.pending_boss=None
        self.target=None
        self.targeting=None
        self.action=None
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
        # Candidate slots surround the actual contact point, not a fixed team row.
        candidates=[(x,y) for y in (62,89,116) for x in (72,105,138,171,204,237,274)]
        occupied=[pygame.Rect(24,61,31,55),pygame.Rect(266,61,31,55)]
        for p in enemies:
            bounds=self.enemy_image(p).get_bounding_rect()
            radius=max(40-bounds.left,bounds.right-40)
            height=69-bounds.top+4  # Includes the full hover/idle range.
            occupied.append(pygame.Rect(p.x-radius,p.y-height,2*radius,height+3))
        ideals=[(min(p.x for p in enemies)-45,cy+8),
                (max(p.x for p in enemies)+55,cy-18),(cx-8,cy-44),(cx+15,cy+47)]
        # Plan with everyone visible, including KO poses, and avoid machinery.
        for i,p in enumerate(self.heroes):
            def score(q):
                rect=pygame.Rect(q[0]-14,q[1]-44,28,44)
                overlap=sum(rect.clip(r.inflate(4,2)).w*rect.clip(r.inflate(4,2)).h for r in occupied)
                return overlap*100+distance(q,ideals[i])+distance(q,p.pos)*.12
            valid=[q for q in candidates if self.walkable(q)]
            goal=min(valid,key=score)
            candidates.remove(goal)
            p.goal=goal
            occupied.append(pygame.Rect(goal[0]-14,goal[1]-44,28,44))

    def request_action(self, hero, command, link=False):
        if self.busy or self.g.state!='battle':return
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
        actors=[self.heroes[i] for i in self.link_tech[command][0]] if link else [self.pawn_for(hero)]
        if any(p is None or p.unit.atb<100 for p in actors):return
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
        self.phase='action';g.log=[command];g.log_wait=0

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
        # Do not retarget the command interface midway through a player action.
        # Enemy actions may interrupt a menu, but preserve its selected ally.
        if not self.action:g.select_ready_actor()

    def battle_roam(self,dt):
        """Everyone keeps their footing and shifts around the shared arena."""
        if not self.active:return
        acting=self.action['actors'] if self.action else ()
        for index,p in enumerate(self.heroes+self.active.pawns):
            if any(p is actor for actor in acting) or not p.unit.alive():continue
            phase=self.clock*(.68+(index%3)*.08)+index*1.9
            radius=4 if p.hero>=0 else 6
            goal=self.clamp_point((p.home[0]+math.sin(phase)*radius,
                                    p.home[1]+math.sin(phase*.73+1.2)*3))
            p.step(goal,(12 if p.hero>=0 else 15)*dt)

    def update(self, dt):
        self.clock+=dt
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
                self.update_clocks(dt)
                self.battle_roam(dt)
                self.schedule_ready_enemy()
            if self.phase=='idle' and self.active:
                foes=[p for p in self.active.pawns if p.unit.alive()]
                if foes:
                    for p in self.heroes:
                        target=min(foes,key=lambda e:distance(e.pos,p.pos))
                        p.direction=1 if target.x>p.x else 3
                    for p in foes:
                        target=min(self.heroes,key=lambda h:distance(h.pos,p.pos))
                        p.direction=1 if target.x>p.x else 3

    def update_action(self, dt):
        a=self.action
        a['elapsed']+=dt
        t=min(1,a['elapsed']/a['duration'])
        for p,start,impact,end,motion in zip(a['actors'],a['starts'],a['destinations'],a['endings'],a['motions']):
            if t<.34:
                f=t/.34;source,destination=start,impact
            elif t<.64:
                f=1.;source,destination=impact,impact
            else:
                f=(t-.64)/.36;source,destination=impact,end
            f=f*f*(3-2*f)
            old=p.pos
            p.x=source[0]+(destination[0]-source[0])*f
            p.y=source[1]+(destination[1]-source[1])*f
            p.air=math.sin(f*math.pi)*20 if motion=='jump' and t<.34 else 0
            p.moving=distance(old,p.pos)>.1
            if p.moving:p.direction=facing(old,p.pos)
            elif a['targets']:p.direction=facing(p.pos,a['targets'][0].pos)
        if t>=.46 and not a['hit']:
            a['hit']=True
            everyone=self.heroes+self.active.pawns
            before=[(p,p.unit.hp,p.unit.mp if p.hero>=0 else 0) for p in everyone]
            a['resolve']()
            for p,hp,mp in before:
                delta=p.unit.hp-hp
                if delta:self.floaters.append({'pos':p.pos,'value':f'+{delta}' if delta>0 else str(-delta),
                                               'color':GREEN if delta>0 else WHITE,'ttl':1.05})
                elif p.hero>=0 and p.unit.mp>mp:
                    self.floaters.append({'pos':p.pos,'value':f'+{p.unit.mp-mp}MP','color':CYAN,'ttl':1.05})
        if t>=1:
            for p,end in zip(a['actors'],a['endings']):
                p.x,p.y=end;p.home=end;p.goal=end;p.moving=False;p.air=0
            self.action=None;self.phase='idle'
            if self.g.state=='battle':
                if a['enemy']:self.g.finish_enemy_action(a['actors'][0].unit)
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
        pygame.draw.rect(s,(15,22,29),(0,17,320,25))
        for x in range(0,320,32):
            pygame.draw.rect(s,tile,(x+1,21,30,13))
            pygame.draw.line(s,edge,(x+3,21),(x+27,21))
        pygame.draw.rect(s,(10,17,22),(0,36,320,5))
        pygame.draw.line(s,edge,(0,41),(320,41),2)
        for y in range(43,180,16):
            for x in range(0,320,16):
                c=tuple(v+((x//16+y//16)%2)*3 for v in tile)
                pygame.draw.rect(s,c,(x,y,15,15))
                pygame.draw.line(s,base,(x,y+14),(x+14,y+14))
                pygame.draw.rect(s,edge,(x+2,y+2,1,1))
        # Recessed cable channels: exactly the same room geometry in both modes.
        for x in (58,258):
            pygame.draw.rect(s,(20,28,33),(x,42,4,132))
            pygame.draw.line(s,edge,(x+1,42),(x+1,174))
        pygame.draw.rect(s,(19,27,32),(62,153,197,4))
        active=len(self.g.flags & {'relay_a','relay_b','relay_c'})<3
        pulse=glow if active else (77,123,112)
        for x in range(65,258,16):
            pygame.draw.rect(s,pulse,(x,154,6,1))
        # Room-specific insets remain visible throughout encounters.
        variant=list(self.rooms).index(self.g.room)
        if self.g.room in ('reservoir','pumps'):
            for x in range(74,252,12):
                y=159+int(math.sin(x*.1+self.clock)*2)
                pygame.draw.line(s,(60,115,127),(x,y),(x+7,y))
        elif self.g.room in ('foundry','furnace','north_hall'):
            for x in (87,233):
                pygame.draw.rect(s,(27,30,32),(x,45,3,94))
                for y in range(48,135,9):pygame.draw.line(s,edge,(x-3,y),(x+6,y))
        elif self.g.room in ('archive','vault'):
            for x in range(77,247,18):
                pygame.draw.rect(s,(25,25,37),(x,46,12,5))
                pygame.draw.rect(s,PURPLE,(x+3,47,5,1))
        if self.g.room.startswith('relay_') or self.g.room=='nexus':
            pygame.draw.ellipse(s,base,(123,72,76,40),3)
            pygame.draw.ellipse(s,edge,(128,76,66,31),1)
            pygame.draw.circle(s,pulse,(161,92),5,1)
        else:
            for n in range(3):
                x=81+(variant*23+n*61)%160
                y=56+(variant*11+n*37)%82
                pygame.draw.line(s,base,(x,y),(x+8,y+2))
                pygame.draw.line(s,edge,(x+3,y+3),(x+7,y+3))
        for dest,(x,y) in self.exits():
            locked=tuple(sorted((self.g.room,dest))) in self.locks and tuple(sorted((self.g.room,dest))) not in self.g.open_locks
            col=RED if locked else GOLD
            pygame.draw.rect(s,(13,21,27),(x-8,y-4,17,9))
            pygame.draw.line(s,col,(x-6,y+3),(x+6,y+3),2)
            if y==49:
                pygame.draw.polygon(s,col,[(x-3,y),(x,y-3),(x+3,y)])
            elif y==147:
                pygame.draw.polygon(s,col,[(x-3,y-2),(x,y+1),(x+3,y-2)])
            elif x<160:
                pygame.draw.polygon(s,col,[(x+2,y-3),(x-1,y),(x+2,y+3)])
            else:pygame.draw.polygon(s,col,[(x-2,y-3),(x+1,y),(x-2,y+3)])

    def draw_machine(self, x):
        s=self.g.canvas
        base,tile,edge,glow=self.palette()
        pygame.draw.ellipse(s,(17,22,27),(x-4,110,30,8))
        pygame.draw.rect(s,(20,28,36),(x,70,22,44))
        pygame.draw.rect(s,(75,86,92),(x,70,18,40))
        pygame.draw.rect(s,(45,57,64),(x+2,73,14,32))
        pygame.draw.polygon(s,(105,116,119),[(x,70),(x+5,64),(x+23,64),(x+18,70)])
        pygame.draw.polygon(s,(32,41,48),[(x+18,70),(x+23,64),(x+23,106),(x+18,110)])
        pygame.draw.rect(s,(15,26,33),(x+4,78,10,12))
        pygame.draw.rect(s,glow,(x+6,81,6,4))
        for y in (95,99,103):pygame.draw.line(s,(25,35,43),(x+4,y),(x+13,y))

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

    def draw_pawn(self, p):
        g=self.g;s=g.canvas
        x,ground_y=int(p.x),int(p.y)
        y=ground_y-int(p.air)
        pygame.draw.ellipse(s,(16,24,28),(x-11,ground_y-3,22,6))
        if p.hero>=0:
            if g.state=='battle' and p.hero==g.turn_actor and not self.busy:
                pygame.draw.ellipse(s,ELEMENT_COLORS[p.hero],(x-12,ground_y-4,24,7),1)
                pygame.draw.polygon(s,GOLD,[(x-3,y-44),(x+3,y-44),(x,y-41)])
            if p.air:
                frame=2 if p.hero in (0,3) else 6
            elif p.moving:
                frame=int(self.clock*10)%8
            elif g.state in ('battle','victory') and self.phase!='forming':
                # Wide alternating poses read as a weapon-ready stance rather
                # than the exploration sprite's feet-together idle.
                frame=(2,6)[(int(self.clock*2.5)+p.hero)%2]
                y-=1 if int(self.clock*5+p.hero)%2 else 0
            else:frame=0
            if p.unit.alive():
                g.draw_party_member(p.hero,x,y,p.direction,frame,.82)
                self.draw_weapon(p,y)
            else:
                # A consistent prone pose, not an abruptly missing party member.
                src=g.party_sheet.subsurface(pygame.Rect(4*32,p.hero*48,32,48))
                img=pygame.transform.rotate(pygame.transform.scale(src,(23,32)),90)
                img.set_alpha(130);s.blit(img,(x-16,ground_y-14))
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

    def draw_weapon(self,p,y=None):
        """Keep weapons visible in stance, then extend them through a strike."""
        if self.g.state not in ('battle','victory') or self.phase=='forming' or p.hero<0:return
        attacking=bool(self.action and p in self.action['actors'] and not self.action['enemy'])
        progress=self.action['elapsed']/self.action['duration'] if attacking else 0
        striking=attacking and .12<=progress<=.87
        s=self.g.canvas;x=int(p.x);y=int(p.y-p.air) if y is None else int(y)
        if attacking and self.action['targets']:
            sign=1 if self.action['targets'][0].x>=p.x else -1
        else:sign=1 if p.direction==1 else -1 if p.direction==3 else 1
        hand=(x+sign*(6 if striking else 4),y-(21 if striking else 19))
        outline=(12,18,25)
        if p.hero==0:  # Rian's ice sword
            tip=(hand[0]+sign*(18 if striking else 14),hand[1]-(10 if striking else 5))
            pygame.draw.line(s,outline,hand,tip,4);pygame.draw.line(s,(184,230,242),hand,tip,2)
            pygame.draw.line(s,CYAN,(hand[0]-sign*3,hand[1]-2),(hand[0]+sign*4,hand[1]+3),2)
        elif p.hero==1:  # Marek braces the rail-pistol with both hands
            length=17 if striking else 14;bx=hand[0] if sign>0 else hand[0]-length
            pygame.draw.rect(s,outline,(bx-1,hand[1]-3,length+2,7))
            pygame.draw.rect(s,(94,124,137),(bx,hand[1]-2,length,4))
            pygame.draw.line(s,CYAN,(bx+2,hand[1]-1),(bx+length-1,hand[1]-1))
            pygame.draw.rect(s,(64,84,91),(bx+5,hand[1]+2,4,5))
        elif p.hero==2:  # Tess draws both bio daggers
            for offset in (-3,5):
                h=(hand[0]-sign*2,hand[1]+offset)
                tip=(h[0]+sign*(11 if striking else 8),h[1]-(4 if striking else 2))
                pygame.draw.line(s,outline,h,tip,3);pygame.draw.line(s,(135,222,142),h,tip,1)
        else:  # Brann shoulders the heavy grenade launcher
            length=20 if striking else 17;bx=hand[0] if sign>0 else hand[0]-length
            pygame.draw.rect(s,outline,(bx-2,hand[1]-5,length+3,9))
            pygame.draw.rect(s,(125,90,61),(bx,hand[1]-4,length,6))
            pygame.draw.rect(s,(217,133,55),(bx+(length-4 if sign>0 else 1),hand[1]-3,5,4))
            pygame.draw.line(s,(67,55,47),(x,hand[1]+1),(bx+8,hand[1]+7),3)

    def draw_scene(self, hud=True):
        self.draw_ground()
        layers=[(115,lambda:self.draw_machine(28)),(115,lambda:self.draw_machine(270))]
        for chest in self.g.treasure[self.g.room]:
            layers.append((chest.pos[1],lambda chest=chest:self.draw_chest(chest)))
        for patrol in self.patrols:
            for p in patrol.pawns:
                layers.append((p.y,lambda p=p:self.draw_pawn(p)))
        for p in self.heroes:layers.append((p.y,lambda p=p:self.draw_pawn(p)))
        for _,draw in sorted(layers,key=lambda item:item[0]):draw()
        self.draw_effects()
        if hud:
            if self.g.state in ('battle','victory'):self.draw_battle_hud()
            else:self.draw_field_hud()

    def draw_chest(self, chest):
        s=self.g.canvas;x,y=chest.pos
        opened=chest.uid in self.g.opened_chests
        trim=MUTED if opened else CYAN if chest.tome else GOLD
        pygame.draw.ellipse(s,(16,24,28),(x-9,y-2,20,5))
        pygame.draw.rect(s,(14,22,29),(x-9,y-12,18,13))
        pygame.draw.rect(s,(80,61,49),(x-7,y-10,14,9))
        pygame.draw.rect(s,trim,(x-8,y-11,16,4),1)
        pygame.draw.line(s,trim,(x-6,y-6),(x+6,y-6))
        for dx in (-6,5):pygame.draw.line(s,trim,(x+dx,y-10),(x+dx,y-2))
        if opened:
            pygame.draw.rect(s,(12,18,24),(x-6,y-9,12,4))
            pygame.draw.rect(s,MUTED,(x-8,y-16,16,4),1)
        elif chest.tome:
            pygame.draw.rect(s,(225,221,185),(x-2,y-11,5,4))
            pygame.draw.line(s,(53,80,89),(x,y-11),(x,y-8))
        else:pygame.draw.rect(s,GOLD,(x-1,y-7,3,3))

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
            if g.state=='battle' and not self.busy and not g.submenu and g.cmd==1 and g.turn_actor>=0:
                h=g.party[g.turn_actor]
                message=h.skill+(' / FIND TOME' if not g.knows(h,h.skill) else ' / READY' if h.gauge>=100 else ' / RECHARGING')
        # Compact floating chips preserve the room behind them instead of
        # covering the entire top fifth with an opaque debug-style banner.
        panel(s,(3,3,236,14))
        label(s,message,7,7,message_color,limit=37)
        panel(s,(263,3,54,14),CYAN)
        label(s,'ACTIVE',272,7,CYAN)

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
        if self.action:
            label(s,'ACTION',8,136,RED if self.action['enemy'] else GOLD)
            words=self.action['name'].split();lines=['']
            for word in words:
                if len(lines[-1])+len(word)+1>16:lines.append(word)
                else:lines[-1]=(lines[-1]+' '+word).strip()
            for n,line in enumerate(lines[:2]):label(s,line,8,150+n*10,WHITE,limit=16)
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
