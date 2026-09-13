#!/usr/bin/env python3
import os, sys, json, math, random
from pathlib import Path
import pygame
from seamless import WorldCombat
from pixel_ui import label, panel
from progression import (ProgressionMixin, ARTS, LINKS_TECH, COSTS, CONSUMABLES,
                         ALL_TOMES, STATS, make_treasure)

W,H,SCALE=320,180,4
TILE=16
FPS=60
SAVE=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'ashen-circuit/save.json'
def resource_path(rel):
 base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent));return base/rel

INK=(14,16,27); WHITE=(234,230,211); BLUE=(43,76,112); STEEL=(57,67,79)
CYAN=(75,211,214); GOLD=(232,175,66); RED=(201,66,73); GREEN=(76,177,101); PURPLE=(135,91,170)
# One source pixel is always one native-canvas pixel. Character size belongs to
# the authored sheet, never to a runtime scale multiplier.
CHARACTER_SCALE=(1.0,1.0,1.0,1.0)
FOLLOWER_DX,FOLLOWER_DY=22,10

def clamp(v,a,b): return max(a,min(b,v))
def text(s,font,color=WHITE): return font.render(str(s),False,color)

ROOMS={
'gate':('Broken Processional',0,'The outer avenue of a civilization that expected to last forever.'),
'intake':('Occupation Intake',0,'Fresh bootprints cross dust older than the kingdom.'),
'lift':('Freight Lift',0,'A cargo platform groans back to life.'),
'barracks':('Makeshift Barracks',1,'The enemy slept here. They left in a hurry.'),
'nexus':('Central Dynamo',1,'Five wings orbit a turbine like spokes around a dead sun.'),
'west_hall':('West Conduit',1,'Copper veins twitch behind cracked glass.'),
'archive':('Mnemonic Archive',2,'Crystal cylinders whisper the names of forgotten operators.'),
'vault':('Armament Vault',3,'Sealed racks wait for soldiers who became dust.'),
'relay_a':('Aether Relay',3,'A restored coil tears blue fire from the air.'),
'north_hall':('Foundry Approach',2,'Heat shimmers above rails worn silver by war machines.'),
'foundry':('Automaton Foundry',3,'Half-built soldiers hang from hooks, learning to move.'),
'furnace':('Cinder Furnace',4,'The enemy has fed the old heart fresh coal.'),
'relay_b':('Thermal Relay',4,'A red sun turns inside a cage of black iron.'),
'east_hall':('East Conduit',2,'Coolant races beneath the grating.'),
'pumps':('Flooded Pumps',3,'Waist-deep water hides the lower machinery.'),
'reservoir':('Glass Reservoir',4,'A suspended lake presses against ancient crystal.'),
'relay_c':('Cryonic Relay',4,'Frost coats a machine burning with pale light.'),
'lower':('Lower Junction',3,'Every passage leads deeper than the builders intended.'),
'brig':('Excavation Brig',3,'Empty cells. One still has a warm lamp.'),
'workshop':('Field Workshop',2,'Tools and stolen parts cover every surface.'),
'bridge':('Command Bridge',5,'The occupation command post overlooks the dragon cradle.'),
'shaft':('Maintenance Shaft',4,'A ladder descends beside the main aether feed.'),
'ante':('Cradle Antechamber',5,'The walls pulse in time with something vast.'),
'cradle':('Dragon Cradle',6,'Vharos dreams beneath a crown of cables.'),
}

LINKS={
'gate':['intake'],'intake':['gate','lift','barracks'],'lift':['intake','nexus'],'barracks':['intake','workshop'],
'nexus':['lift','west_hall','north_hall','east_hall','lower'],'west_hall':['nexus','archive'],'archive':['west_hall','vault','relay_a'],
'vault':['archive','bridge'],'relay_a':['archive'],'north_hall':['nexus','foundry'],'foundry':['north_hall','furnace','workshop'],
'furnace':['foundry','relay_b'],'relay_b':['furnace'],'east_hall':['nexus','pumps'],'pumps':['east_hall','reservoir','brig'],
'reservoir':['pumps','relay_c'],'relay_c':['reservoir'],'lower':['nexus','brig','shaft'],'brig':['lower','pumps'],
'workshop':['barracks','foundry','shaft'],'bridge':['vault','ante'],'shaft':['lower','workshop','ante'],'ante':['shaft','bridge','cradle'],'cradle':['ante']}

# doors require scarce brass keys; unlocking is permanent
LOCKS={tuple(sorted(x)) for x in [('barracks','workshop'),('lower','shaft'),('foundry','workshop'),('pumps','brig'),('workshop','shaft')]}
RELAY_ROOM={'relay_a':'Aether','relay_b':'Thermal','relay_c':'Cryonic'}

STORY={
'gate':[("RIAN","There it is. The Caelus Engine."),("TESS","A mountain pretending to be a machine."),("MAREK","And the Dominion has scaffolding on it. Subtle."),("BRANN","We stop the awakening, retrieve the survey team, and leave."),("MAREK","You brought enough grenades to leave?"),("BRANN","I brought enough to redefine the entrance."),("RIAN","Then we'd better get started.")],
'intake':[("TESS","These lamps were dead in the reconnaissance sketches."),("MAREK","They're restoring systems from the outside inward."),("RIAN","Look for training tomes in the caches. A Link tome teaches us a combined technique."),("BRANN","Meaning I should not detonate anything alone?"),("MAREK","It means wait until I can make it electrically irresponsible." )],
'nexus':[("MAREK","Three restoration relays. Aether, thermal, cryonic."),("TESS","Break all three and the cradle loses its restraints."),("BRANN","Loses? I thought we wanted it restrained."),("MAREK","The restraints are also feeding it. Ancient engineers enjoyed irony."),("RIAN","Three wings. We choose the order. Save your Link charges for hard fights.")],
'archive':[("TESS","The crystals are memories."),("VOICE","Operator... return... Vharos awaits a command."),("MAREK","Do not answer the haunted filing cabinet."),("TESS","I wasn't going to."),("BRANN","You leaned toward it."),("TESS","Academically.")],
'foundry':[("BRANN","Those unfinished machines are watching us."),("MAREK","They have no heads."),("BRANN","Then they will not see where I place the charge."),("RIAN","Move before he improves the architecture.")],
'reservoir':[("TESS","All this water, held above a furnace."),("MAREK","Emergency quench system—and enough conductivity to power my med-coil."),("BRANN","Can we use it?"),("MAREK","Certainly. If you want to turn the complex into a pressure bomb."),("BRANN","Finally, a medical opinion I understand.")],
'lower':[("RIAN","Dominion cables. Recent."),("MAREK","They bypassed the original controls. Crude, effective, insulting."),("TESS","You sound personally offended."),("MAREK","I contain multitudes. Most are offended.")],
'brig':[("PRISONER","They moved the survey team to the command bridge. Commander Vael needs their translations."),("RIAN","Can you walk?"),("PRISONER","Away from here? Magnificently."),("BRANN","Take the marked service route. We cleared it." )],
'ante':[("TESS","The heartbeat is inside my teeth."),("BRANN","Good. I was worried only I could feel that."),("MAREK","All three relays are down. Whatever happens now—"),("RIAN","We finish it together.")],
}

class Hero:
 def __init__(self,name,job,weapon,element,hp,mp,powr,mag,spd,skill,rate):
  self.name,self.job,self.weapon,self.element=name,job,weapon,element; self.maxhp,self.hp=hp,hp; self.maxmp,self.mp=mp,mp
  self.pow,self.mag,self.spd=powr,mag,spd;self.base_spd=spd;self.defense=0;self.resist=0;self.skill,self.rate=skill,rate
  self.gauge=random.randint(25,65);self.atb=0.;self.ready_stamp=0.;self.guard=False;self.buffs={}
 def alive(self): return self.hp>0
 def recharge(self): return self.rate + max(0,self.spd-self.base_spd)*.6
 def atb_rate(self): return 16+self.spd*.45

def new_party(): return [
 Hero('Rian','Frostguard','Sword','Ice',440,58,43,27,22,"Winter's Standard",31),
 Hero('Marek','Arc Medic','Rail-pistol','Lightning',330,82,29,40,28,'Second Spark',38),
 Hero('Tess','Venomist','Daggers','Bio',295,67,35,36,31,'Toxic Bloom',34),
 Hero('Brann','Bombardier','Launcher','Fire / None',390,55,46,27,18,'Grand Payload',27)]

ENEMIES={
'scout':('Dominion Scout',115,24,18,14,GOLD),'drone':('Repair Drone',90,21,21,16,CYAN),'mite':('Wire Mite',72,18,14,24,PURPLE),
'guard':('Iron Guard',185,32,27,13,STEEL),'wisp':('Aether Wisp',130,21,36,26,CYAN),'soldier':('Dominion Lancer',210,38,25,19,RED),
'golem':('Furnace Golem',330,45,35,10,GOLD),'serpent':('Coolant Serpent',240,39,34,23,GREEN),
'vael':('Commander Vael',1900,48,42,26,RED),'dragon':('Vharos, Ashen Dragon',4600,61,55,24,PURPLE)}

class Enemy:
 def __init__(self,key,scale=1):
  n,h,p,m,s,c=ENEMIES[key]; self.key=key; self.name=n; self.maxhp=int(h*scale); self.hp=self.maxhp
  self.pow=int(p*scale);self.mag=int(m*scale);self.spd=s;self.color=c;self.status={};self.turn=0;self.atb=0.;self.ready_stamp=0.
 def alive(self):return self.hp>0
 def atb_rate(self):return 14+self.spd*.42

FORMATIONS=[['scout','drone'],['mite','mite','drone'],['guard','scout'],['wisp','mite'],['soldier','drone'],['guard','wisp'],['serpent','mite'],['golem'],['soldier','guard']]

class Game(ProgressionMixin):
 def __init__(self):
  pygame.mixer.pre_init(48000,-16,2,512); pygame.init()
  self.full=False; self.screen=pygame.display.set_mode((W*SCALE,H*SCALE));pygame.display.set_caption('The Ashen Circuit')
  self.canvas=pygame.Surface((W,H)); self.clock=pygame.time.Clock()
  self.font=pygame.font.Font(None,12);self.small=pygame.font.Font(None,10);self.tiny=pygame.font.Font(None,9);self.big=pygame.font.Font(None,22)
  self.party_sheet=pygame.image.load(str(resource_path('assets/characters/party_motion_v1.png'))).convert_alpha()
  self.combat_body_sheet=pygame.image.load(str(resource_path('assets/characters/party_combat_bodies_v2.png'))).convert_alpha()
  self.combat_arm_sheet=pygame.image.load(str(resource_path('assets/characters/party_combat_arms_v2.png'))).convert_alpha()
  self.state='title';self.party=new_party();self.room='gate';self.prev=None;self.px,self.py=160,110;self.facing=0
  self.flags=set();self.open_locks=set();self.keys=0;self.gold=0;self.items={'Potion':5,'Ether':2,'Phoenix Gear':1,'Bomb':1}
  self.weapon=0;self.armor=0;self.steps=0;self.dialog=[];self.dindex=0;self.room_menu=0
  self.battle_mode='Active'
  self.enemies=[];self.turn_actor=-1;self.cmd=0;self.submenu=None;self.target=0;self.log=[];self.log_wait=0;self.boss=None
  self.manual_page=0;self.manual_type='party'
  self.treasure=make_treasure(ROOMS);self.init_progression()
  self.playtime=0;self.last_tick=pygame.time.get_ticks();self.toast='';self.toast_t=0;self.shake=0;self.moving=False
  self.stars=[(random.randrange(W),random.randrange(H),random.choice([1,1,2])) for _ in range(80)]
  self.joy=None;self.axis_latch=[0,0];self.pad_buttons=set()
  if pygame.joystick.get_count(): self.connect_controller(0)
  self.music_ready=False;self.battle_music_playing=False
  self.battle_music_path=resource_path('assets/audio/battle_theme_1.mp3')
  try:self.make_music()
  except (pygame.error,OSError):pass
  self.world=WorldCombat(self,ROOMS,LINKS,LOCKS,Enemy,LINKS_TECH)

 def connect_controller(self,index=0):
  try:
   self.joy=pygame.joystick.Joystick(index);self.joy.init();self.toast='Xbox controller connected';self.toast_t=120
  except pygame.error:self.joy=None

 def controller_direction(self,key):
  return self.event(pygame.event.Event(pygame.KEYDOWN,key=key))

 def make_music(self):
  pygame.mixer.music.load(str(self.battle_music_path))
  self.music_ready=True

 def start_battle_music(self):
  if not self.music_ready:return
  pygame.mixer.music.stop()
  pygame.mixer.music.play(-1)
  self.battle_music_playing=True

 def stop_battle_music(self):
  if not self.battle_music_playing:return
  pygame.mixer.music.stop()
  self.battle_music_playing=False

 def save(self):
  if self.state=='battle': return
  SAVE.parent.mkdir(parents=True,exist_ok=True)
  data={'room':self.room,'prev':self.prev,'px':self.px,'py':self.py,'flags':list(self.flags),'locks':[list(x) for x in self.open_locks],
   'keys':self.keys,'gold':self.gold,'items':self.items,'weapon':self.weapon,'armor':self.armor,'playtime':self.playtime,
   'battle_mode':self.battle_mode,
   'party':[{'hp':h.hp,'mp':h.mp,'gauge':h.gauge,'buffs':h.buffs,
             'stats':{stat:getattr(h,stat) for stat in STATS}} for h in self.party],
   'learned_tomes':sorted(self.learned),'opened_chests':sorted(self.opened_chests),
   'cleared_encounters':sorted(self.world.cleared),'save_version':3}
  temporary=SAVE.with_suffix('.tmp');temporary.write_text(json.dumps(data));temporary.replace(SAVE)
  self.toast='Game saved';self.toast_t=100

 def load(self):
  self.stop_battle_music()
  try:
   d=json.loads(SAVE.read_text());self.room=d['room'];self.prev=d.get('prev');self.px=d.get('px',160);self.py=d.get('py',110)
   self.flags=set(d['flags']);self.open_locks={tuple(x) for x in d['locks']};self.keys=d['keys'];self.gold=d['gold'];self.items=d['items'];self.weapon=d['weapon'];self.armor=d['armor'];self.playtime=d['playtime']
   self.battle_mode=d.get('battle_mode','Active') if d.get('battle_mode','Active') in ('Active','Wait') else 'Active'
   self.party=new_party();self.init_progression()
   for h,v in zip(self.party,d['party']):
    for stat,value in v.get('stats',{}).items():
     if stat in STATS:setattr(h,stat,int(value))
    h.hp=clamp(v['hp'],0,h.maxhp);h.mp=clamp(v['mp'],0,h.maxmp);h.gauge=v.get('gauge',0);h.atb=0;h.buffs=v.get('buffs',{})
   self.learned=set(d.get('learned_tomes',[])) & ALL_TOMES
   valid={c.uid for chests in self.treasure.values() for c in chests}
   self.opened_chests=set(d.get('opened_chests',[])) & valid
   if d.get('save_version',1)<3:
    backup=SAVE.with_name('save-before-tomes.json')
    if not backup.exists():backup.write_bytes(SAVE.read_bytes())
    self.open_locks &= LOCKS
    self.keys=min(self.keys,max(0,len(self.flags & set(RELAY_ROOM))-len(self.open_locks)))
   self.world.cleared=set(d.get('cleared_encounters',[]));self.world.arrive()
   self.state='field';self.toast='Save loaded';self.toast_t=120
  except (ValueError,KeyError,OSError,TypeError) as error:
   print(f'Could not load save: {error}',file=sys.stderr)
   self.state='title';self.toast='Save could not be read. N: new game.';self.toast_t=600

 def new_game(self):
  self.stop_battle_music()
  self.__dict__.update(room='gate',prev=None,px=160,py=110,flags=set(),open_locks=set(),keys=0,gold=0,items={'Potion':5,'Ether':2,'Phoenix Gear':1,'Bomb':1},weapon=0,armor=0,playtime=0,party=new_party(),state='field')
  self.init_progression();self.world.reset()
  self.start_dialog(STORY['gate']+[('RIAN','Four training caches by the entrance. Take the tomes before we meet the patrols.'),('SYSTEM','Approach a chest and press A / Z. Tomes teach techniques; stat items are assigned in Items & Growth.')]);self.flags.add('seen_gate')

 def start_dialog(self,lines):self.dialog=lines;self.dindex=0;self.state='dialog'
 def say(self,name,line):self.start_dialog([(name,line)])

 def transition(self,dest):
  if dest not in LINKS[self.room]:return
  edge=tuple(sorted((self.room,dest)))
  if edge in LOCKS and edge not in self.open_locks:
   if self.keys:
    self.keys-=1;self.open_locks.add(edge);self.say('SYSTEM','Brass key consumed. Shortcut permanently unlocked.');self.save();return
   self.say('SYSTEM','A brass access lock. No keys remain.');return
  if dest=='ante' and 'vael_down' not in self.flags:
   self.say('RIAN','The command bridge is still shielding the cradle. We need to take it.');return
  if dest=='cradle' and len(self.flags&{'relay_a','relay_b','relay_c'})<3:
   self.say('MAREK','The cradle seal has three live feeds. We need every relay down.');return
  old=self.room;self.prev=old;self.room=dest;self.steps=0
  self.world.arrive(previous=old,repopulate=True)
  flag='seen_'+dest
  if flag not in self.flags and dest in STORY:self.flags.add(flag);self.start_dialog(STORY[dest])
  if dest!='cradle':self.room_event(dest)
  self.save()

 def room_event(self,r):
  if r in RELAY_ROOM and r not in self.flags:
   self.flags.add(r);self.keys+=1;self.items['Potion']+=2
   self.start_dialog([('MAREK',f"{RELAY_ROOM[r]} relay exposed. Stand back."),('SYSTEM','RELAY SEVERED - one brass key and two Potions recovered.'),('TESS','The whole complex felt that.'),('RIAN','Good. Let it know we are coming.')])
  if r=='cradle' and 'dragon_down' not in self.flags:self.start_dialog([('VAEL','You are too late.'),('MAREK','Vael? You should be unconscious.'),('VAEL','The Engine requires no commander. Only a target.'),('SYSTEM','CAELUS LANCE: ACQUIRING'),('TESS','The dragon is the focusing array.'),('RIAN','Then we break it before—'),('SYSTEM','CAELUS LANCE: FIRED'),('BRANN','...The western horizon.'),('RIAN','We cannot undo that shot. We can make it the last.')]);self.flags.add('pre_dragon')

 def start_battle(self,keys,boss=None):
  self.world.begin(keys,boss)
  self.start_battle_music()

 def field_input(self,e):
  if e.type==pygame.KEYDOWN:
   if e.key in (pygame.K_ESCAPE,pygame.K_x):self.state='menu';self.room_menu=0
   if e.key==pygame.K_F5:self.save()
   if e.key in (pygame.K_RETURN,pygame.K_z,pygame.K_SPACE):self.interact()

 def interact(self):
  chest=self.chest_in_reach()
  if chest and self.open_chest(chest):return
  # Treasure requires proximity; consoles retain the room's interaction.
  if self.room=='nexus':
   n=len(self.flags&{'relay_a','relay_b','relay_c'});self.say('SYSTEM',f'RESTORATION FEEDS: {3-n} active. CRADLE SHIELD: '+('offline' if n==3 else 'engaged'))
  elif self.room=='workshop' and 'shop_used' not in self.flags:
   self.flags.add('shop_used');self.weapon=min(2,self.weapon+1);self.armor=min(2,self.armor+1);self.say('MAREK','Dominion supplies. I can tune everyone’s gear one grade. Try not to look grateful.')
  elif self.room=='vault' and 'vault_loot' not in self.flags:
   self.flags.add('vault_loot');self.weapon=2;self.items['Bomb']+=2;self.say('SYSTEM','Found: Arclight weapons and 2 Bombs. Weapon grade maximized.')
  elif self.room=='brig' and 'brig_loot' not in self.flags:
   self.flags.add('brig_loot');self.items['Phoenix Gear']+=1;self.say('PRISONER','Take this revival gear. The bridge is reached through the armament vault; its service route is open.')
  elif self.room=='barracks':self.shop()
  else:self.say('MAREK',random.choice(['Nothing useful. Remarkably decorative, though.','Dead conduit. Even the dust has dust.','If it starts humming, stop touching it.']))

 def shop(self):
  if self.gold>=35:
   self.gold-=35;self.items['Potion']+=2;self.say('MAREK','Two usable tonics from the abandoned medical kit. Cost us 35 gil in stabilizer parts.')
  else:self.say('MAREK','I can rebuild two Potions here for 35 gil worth of stabilizer parts.')

 def move(self,dx,dy):
  self.world.field_move(dx,dy)

 def battle_input(self,e):
  if self.world.pending_player:return
  if self.world.busy and not self.world.enemy_action_active:return
  if self.world.target_input(e):return
  alive=[h for h in self.party if h.alive()]
  if not alive:return
  if self.turn_actor<0 or self.party[self.turn_actor].atb<100:
   self.select_ready_actor()
  if self.turn_actor<0:return
  hero=self.party[self.turn_actor]
  if not hero.alive():self.select_ready_actor(force=True);return
  if e.type!=pygame.KEYDOWN:return
  if e.key in (pygame.K_q,pygame.K_e):
   self.cycle_ready_actor(-1 if e.key==pygame.K_q else 1);return
  if self.submenu:
   opts=self.get_submenu(hero)
   if e.key in (pygame.K_UP,pygame.K_w):self.target=(self.target-1)%len(opts)
   elif e.key in (pygame.K_DOWN,pygame.K_s):self.target=(self.target+1)%len(opts)
   elif e.key in (pygame.K_RIGHT,pygame.K_d):self.target=(self.target+3)%len(opts)
   elif e.key in (pygame.K_LEFT,pygame.K_a):self.target=(self.target-3)%len(opts)
   elif e.key in (pygame.K_ESCAPE,pygame.K_x):self.submenu=None;self.target=0
   elif e.key in (pygame.K_RETURN,pygame.K_z,pygame.K_SPACE):self.use_sub(hero,opts[self.target])
  else:
   commands=self.commands(hero)
   if e.key in (pygame.K_UP,pygame.K_w):self.cmd=(self.cmd-1)%len(commands)
   elif e.key in (pygame.K_DOWN,pygame.K_s):self.cmd=(self.cmd+1)%len(commands)
   elif e.key in (pygame.K_LEFT,pygame.K_a,pygame.K_RIGHT,pygame.K_d):self.cmd=(self.cmd+3)%len(commands)
   elif e.key in (pygame.K_RETURN,pygame.K_z,pygame.K_SPACE):
    c=commands[self.cmd]
    if c==hero.skill and not self.knows(hero,c):self.log=['Find the personal technique tome in a chest.'];self.log_wait=35
    elif c==hero.skill and hero.gauge<100:self.log=[f'{c} is still recharging.'];self.log_wait=35
    elif c=='Link' and not self.ready_links():self.log=['No Link technique is ready.'];self.log_wait=35
    elif c in ('Attack','Defend'):self.execute(hero,c)
    elif c==hero.skill:self.execute(hero,c)
    else:self.submenu=c;self.target=0

 def commands(self,h):return ['Attack',h.skill,'Arts','Link','Item','Defend']

 def ready_links(self):
  return [name for name,(people,_) in LINKS_TECH.items()
          if name in self.learned and all(self.party[i].alive() and self.party[i].atb>=100 for i in people)]

 def ready_party(self):
  return [i for i,h in enumerate(self.party) if h.alive() and h.atb>=100]

 def select_ready_actor(self,force=False):
  ready=self.ready_party()
  if not ready:self.turn_actor=-1;self.submenu=None;self.world.targeting=None;return
  if not force and self.turn_actor in ready:return
  self.turn_actor=min(ready,key=lambda i:self.party[i].ready_stamp)
  self.cmd=0;self.submenu=None;self.target=0;self.world.target=None;self.world.targeting=None

 def cycle_ready_actor(self,delta):
  ready=self.ready_party()
  if len(ready)<2:return
  current=ready.index(self.turn_actor) if self.turn_actor in ready else 0
  self.turn_actor=ready[(current+delta)%len(ready)]
  self.cmd=0;self.submenu=None;self.target=0;self.world.target=None;self.world.targeting=None

 def get_submenu(self,h):
  if self.submenu=='Arts':return [f'{n} {cost}MP' for n,cost in self.known_arts(h)] or ['(Find tomes in chests)']
  if self.submenu=='Link':return self.ready_links() or ['(No Link ready)']
  return [f'{k} x{self.items.get(k,0)}' for k in CONSUMABLES if self.items.get(k,0)>0] or ['(Empty)']

 def use_sub(self,h,opt):
  if opt.startswith('('):return
  if self.submenu=='Link':self.submenu=None;self.execute_link(opt);return
  if self.submenu=='Arts':
   name,cost=opt.rsplit(' ',1);cost=int(cost[:-2])
   if h.mp<cost:self.log=['Not enough MP.'];self.log_wait=35;return
   opt=name
  else:opt=opt.split(' x')[0]
  self.submenu=None;self.execute(h,opt)

 def damage(self,att,target,power,magic=False,element=None):
  stat=att.mag if magic else att.pow; base=stat*power/20+random.randint(-4,5)+self.weapon*5
  if att.buffs.get('attack',0):base*=1.25
  if target.status.get('frail',0):base*=1.3
  weak={'drone':'Lightning','guard':'Bio','wisp':'None','golem':'Ice','serpent':'Fire','vael':'Bio','dragon':'Ice'}.get(target.key)
  if element and element==weak:base*=1.35
  dmg=max(1,int(base));target.hp=max(0,target.hp-dmg);return dmg

 def heal(self,target,amount):
  if not target.alive():return 0
  amount=min(target.maxhp-target.hp,int(amount));target.hp+=amount;return amount

 def apply_enemy(self,e,**effects):
  duration=2 if e.key in ('vael','dragon') else 3
  for name,val in effects.items():e.status[name]=max(e.status.get(name,0),min(val,duration))

 def execute(self,h,c):
  self.world.request_action(h,c)

 def resolve_command(self,h,c):
  if not self.command_available(h,c):return
  foes=[e for e in self.enemies if e.alive()];lines=[]
  if not foes:return
  t=self.world.target if self.world.target in foes else min(foes,key=lambda x:x.hp)
  if c=='Attack':lines=[f'{h.name} attacks with {h.weapon} — {self.damage(h,t,31)} damage!']
  elif c=='Defend':h.guard=True;lines=[f'{h.name} braces for impact.']
  elif c==h.skill:
   h.gauge=0
   if c=="Winter's Standard":
    for x in self.party:
     if x.alive():x.buffs['attack']=3;x.buffs['defense']=3
    lines=["Winter's Standard! Party attack and defense surge!"]
   elif c=='Second Spark':
    total=0
    for x in self.party:
     if not x.alive():x.hp=max(1,x.maxhp//5)
     total+=self.heal(x,x.maxhp*.35);x.buffs['regen']=3
    lines=[f'Second Spark! The party revives and recovers {total} HP!']
   elif c=='Toxic Bloom':
    total=sum(self.damage(h,f,30,True,'Bio') for f in foes)
    for f in foes:self.apply_enemy(f,poison=3,frail=3,weak=3,slow=3)
    lines=[f'Toxic Bloom — {total} damage and four maladies!']
   elif c=='Grand Payload':
    total=sum(self.damage(h,f,120,False,'None') for f in foes);lines=[f'Grand Payload detonates — {total} total damage!']
  elif c=='Frost Edge':h.mp-=6;lines=[f'Frost Edge — {self.damage(h,t,48,True,"Ice")} ice damage!']
  elif c=='Crystal Guard':
   h.mp-=7;x=min([q for q in self.party if q.alive()],key=lambda q:q.hp/q.maxhp);x.buffs['defense']=4;lines=[f'Crystal armor forms around {x.name}.']
  elif c=='Glacial Formation':
   h.mp-=12
   for x in self.party:
    if x.alive():x.buffs['defense']=3
   lines=['The party enters Glacial Formation.']
  elif c=='Rail Shot':h.mp-=6;lines=[f'Rail Shot — {self.damage(h,t,48,True,"Lightning")} lightning damage!']
  elif c=='Galvanize':
   h.mp-=7;x=min([q for q in self.party if q.alive()],key=lambda q:q.hp/q.maxhp);a=self.heal(x,105+h.mag);lines=[f'Marek galvanizes {x.name} for {a} HP.']
  elif c=='Chain Mend':
   h.mp-=14;total=sum(self.heal(x,62+h.mag*.35) for x in self.party);lines=[f'Chain Mend restores {total} party HP.']
  elif c=='Defibrillate':
   h.mp-=18;dead=[x for x in self.party if not x.alive()]
   if dead:dead[0].hp=dead[0].maxhp//3;lines=[f'{dead[0].name} is electrically revived!']
   else:lines=['The restorative charge becomes a barrier.'];h.buffs['defense']=3
  elif c=='Venom Cut':
   h.mp-=5;d=self.damage(h,t,40,False,'Bio');self.apply_enemy(t,poison=3);lines=[f'Venom Cut — {d} damage and Poison!']
  elif c=='Corrode':h.mp-=7;self.apply_enemy(t,frail=3);lines=[f'{t.name}’s defenses corrode!']
  elif c=='Wither':h.mp-=7;self.apply_enemy(t,weak=3);lines=[f'{t.name}’s attack withers!']
  elif c=='Nerve Toxin':h.mp-=11;self.apply_enemy(t,slow=3,poison=3);lines=[f'{t.name} is poisoned and slowed!']
  elif c=='Frag Grenade':h.mp-=7;total=sum(self.damage(h,f,34,False,'None') for f in foes);lines=[f'Frag Grenade — {total} total damage!']
  elif c=='Incendiary':h.mp-=9;total=sum(self.damage(h,f,39,True,'Fire') for f in foes);lines=[f'Incendiary — {total} total fire damage!']
  elif c=='Shaped Charge':h.mp-=12;lines=[f'Shaped Charge — {self.damage(h,t,73,False,"None")} damage!']
  elif c=='Potion':
   self.items[c]-=1;x=min([q for q in self.party if q.alive()],key=lambda q:q.hp/q.maxhp);amt=min(x.maxhp-x.hp,140);x.hp+=amt;lines=[f'{x.name} recovers {amt} HP.']
  elif c=='Ether':self.items[c]-=1;x=min(self.party,key=lambda q:q.mp/q.maxmp);amt=min(x.maxmp-x.mp,30);x.mp+=amt;lines=[f'{x.name} recovers {amt} MP.']
  elif c=='Phoenix Gear':
   dead=[x for x in self.party if not x.alive()]
   if dead:self.items[c]-=1;dead[0].hp=dead[0].maxhp//3;lines=[f'{dead[0].name} returns to battle!']
   else:lines=['No one needs revival.']
  elif c=='Bomb':self.items[c]-=1;d=self.damage(h,t,100,True);lines=[f'The Bomb erupts — {d} damage!']
  self.log=lines;self.log_wait=0;self.check_battle()

 def execute_link(self,name):
  self.world.request_action(self.party[self.turn_actor],name,link=True)

 def resolve_link(self,name):
  if name not in self.learned:return
  foes=[e for e in self.enemies if e.alive()];people,_=LINKS_TECH[name]
  if not foes:return
  r,m,tess,b=self.party;target=self.world.target if self.world.target in foes else max(foes,key=lambda e:e.hp);lines=[]
  if name=='Aurora Circuit':
   total=sum(self.heal(x,x.maxhp*.48) for x in self.party)
   for x in self.party:
    if x.alive():x.buffs['defense']=3
   lines=[f'Aurora Circuit! {total} HP restored; barrier raised!']
  elif name=='Plague Canister':
   total=sum(self.damage(b,e,150,True,'Bio') for e in foes)
   for e in foes:self.apply_enemy(e,poison=3,frail=3)
   lines=[f'Plague Canister! {total} damage; enemies corroded!']
  elif name=='Cryotoxin':
   d=self.damage(tess,target,160,True,'Bio');self.apply_enemy(target,poison=3,slow=3,weak=3,frail=3);lines=[f'Cryotoxin! {d} damage and total debilitation!']
  elif name=='Thermal Fracture':lines=[f'Thermal Fracture! {self.damage(b,target,250,False,"None")} damage!']
  elif name=='Neuroshock':
   d=self.damage(m,target,190,True,'Lightning');self.apply_enemy(target,slow=3,weak=3,frail=3);lines=[f'Neuroshock! {d} damage; systems collapse!']
  elif name=='Thunderhead':
   total=sum(self.damage(b,e,250,True,'Fire') for e in foes);lines=[f'Thunderhead! {total} total stormfire damage!']
  elif name=='Permafrost Protocol':
   total=sum(self.heal(x,x.maxhp*.55) for x in self.party)
   for x in self.party:x.buffs.update(attack=4,defense=4,regen=4)
   for e in foes:self.apply_enemy(e,slow=3,weak=3)
   lines=[f'Permafrost Protocol! {total} HP; party fortified!']
  elif name=='Extinction Event':
   total=sum(self.damage(b,e,520,True,'Bio') for e in foes)
   for e in foes:self.apply_enemy(e,poison=3,frail=3,weak=3)
   lines=[f'Extinction Event! {total} damage; ruin persists!']
  else:
   total=sum(self.damage(b,e,450,False,'None') for e in foes)
   for x in self.party:
    if not x.alive():x.hp=x.maxhp//4
    self.heal(x,x.maxhp);x.buffs['defense']=2
   lines=[f'ZERO HOUR — {total} damage! The party is restored!']
  self.log=lines;self.log_wait=0;self.check_battle()

 def finish_hero_action(self,actors,command):
  if self.state!='battle':return
  for pawn in actors:
   h=pawn.unit
   if command!='Defend':h.guard=False
   if h.buffs.get('regen',0):self.heal(h,h.maxhp*.06)
   for key in list(h.buffs):h.buffs[key]=max(0,h.buffs[key]-1)
  self.cmd=0;self.submenu=None;self.target=0;self.world.target=None
  self.turn_actor=-1;self.select_ready_actor(force=True);self.check_battle()

 def finish_enemy_action(self,enemy):
  if self.state!='battle':return
  self.turn_actor=-1 if self.turn_actor>=0 and not self.party[self.turn_actor].alive() else self.turn_actor
  if self.turn_actor<0:self.select_ready_actor(force=True)
  self.check_battle()

 # Compatibility entry points for tools that stage combat directly.
 def next_actor(self):
  actors=self.world.action['actors'] if self.world.action else []
  command=self.world.action['name'] if self.world.action else ''
  self.finish_hero_action(actors,command)

 def enemy_phase(self):
  self.world.force_enemy_action()

 def resolve_enemy_turn(self,e,t):
  lines=[];e.turn+=1
  if e.status.get('poison',0):
   pd=max(4,e.maxhp//24);e.hp=max(0,e.hp-pd);lines.append(f'{e.name}: {pd} poison damage!')
  slowed=e.status.get('slow',0) and e.turn%2==0
  weak=e.status.get('weak',0)>0
  for k in list(e.status):e.status[k]=max(0,e.status[k]-1)
  if e.alive() and not slowed and t.alive():
   special=e.key in ('vael','dragon') and e.turn%3==0
   p=e.mag if special else e.pow
   d=max(1,int(p*(1.5 if special else 1)+random.randint(-5,7)-self.armor*5-(t.resist if special or e.key=='wisp' else t.defense)))
   if weak:d=int(d*.7)
   if t.guard:d//=2
   if t.buffs.get('defense',0):d=int(d*.7)
   d=max(1,d);t.hp=max(0,t.hp-d)
   lines.append(f'{e.name}: {d} damage to {t.name}!')
  elif slowed:lines.append(f'{e.name} is slowed!')
  self.log=lines;self.log_wait=0;self.check_battle()

 def check_battle(self):
  if self.state!='battle':return
  if not any(e.alive() for e in self.enemies):
   self.stop_battle_music()
   reward=sum(e.maxhp//5 for e in self.enemies);self.gold+=reward
   if any(e.key=='drone' for e in self.enemies) or random.random()<.42:self.items['Potion']+=1;drop=' Potion found.'
   else:drop=''
   self.log=[f'Victory! {reward} gil in usable parts.{drop}'];self.log_wait=100;self.state='victory';return
  if not any(h.alive() for h in self.party):self.stop_battle_music();self.state='gameover'

 def end_victory(self):
  if self.world.busy:return
  self.world.finish_victory()
  if self.boss=='vael':
   self.flags.add('vael_down');self.armor=max(2,self.armor)
   self.start_dialog([('VAEL','You think the relays were restraints? They were the ignition sequence.'),('TESS','He wanted us to sever them.'),('MAREK','No. He needed anyone to sever them. Their controls reject Dominion blood.'),('RIAN','Then we reach the cradle first.'),('SYSTEM','Commander defeated. Armor grade maximized. Search the wing caches for triple Link tomes.')])
  elif self.boss=='dragon':
   self.flags.add('dragon_down');self.state='ending';self.dindex=0
  else:self.state='field'
  self.boss=None
  self.save()

 def menu_input(self,e):
  if e.type!=pygame.KEYDOWN:return
  opts=self.menu_options()
  if e.key in (pygame.K_UP,pygame.K_w):self.room_menu=(self.room_menu-1)%len(opts)
  elif e.key in (pygame.K_DOWN,pygame.K_s):self.room_menu=(self.room_menu+1)%len(opts)
  elif e.key in (pygame.K_ESCAPE,pygame.K_x):self.state='field'
  elif e.key in (pygame.K_RETURN,pygame.K_z):
   c=opts[self.room_menu]
   if c=='Items & Growth':self.state='bag';self.bag_hero=None;self.bag_confirm=False;self.bag_message=''
   elif c=='Party & Arts':self.manual_type='party';self.manual_page=0;self.state='manual'
   elif c=='Link Manual':self.manual_type='links';self.manual_page=0;self.state='manual'
   elif c.startswith('Battle Mode:'):
    self.battle_mode='Wait' if self.battle_mode=='Active' else 'Active'
    self.toast=f'Battle mode: {self.battle_mode}';self.toast_t=120
   elif c=='Save':self.state='field';self.save()
   elif c=='Return to field':self.state='field'
   elif c=='Quit to title':self.state='title'

 def menu_options(self):
  return ['Items & Growth','Party & Arts','Link Manual',f'Battle Mode: {self.battle_mode}',
          'Save','Return to field','Quit to title']

 def event(self,e):
  if e.type==pygame.QUIT:return False
  if e.type==pygame.JOYDEVICEADDED:
   if self.joy is None:self.connect_controller(e.device_index)
   return True
  if e.type==pygame.JOYDEVICEREMOVED:
   if self.joy and e.instance_id==self.joy.get_instance_id():self.joy=None;self.toast='Controller disconnected';self.toast_t=120
   return True
  if e.type==pygame.JOYBUTTONDOWN:
   self.pad_buttons.add(e.button)
   key=pygame.K_n if e.button==3 and self.state=='title' else pygame.K_z if e.button==0 else pygame.K_x if e.button==1 else pygame.K_q if e.button==4 and self.state=='battle' else pygame.K_e if e.button==5 and self.state=='battle' else pygame.K_ESCAPE if e.button in (6,7) else pygame.K_UP if e.button==11 else pygame.K_DOWN if e.button==12 else pygame.K_LEFT if e.button==13 else pygame.K_RIGHT if e.button==14 else None
   if key is not None:return self.event(pygame.event.Event(pygame.KEYDOWN,key=key))
  if e.type==pygame.JOYBUTTONUP:
   self.pad_buttons.discard(e.button);return True
  if e.type==pygame.JOYAXISMOTION and e.axis in (0,1):
   old=self.axis_latch[e.axis];new=1 if e.value>.55 else -1 if e.value<-.55 else 0
   self.axis_latch[e.axis]=new
   if new and new!=old:
    key=(pygame.K_RIGHT if new>0 else pygame.K_LEFT) if e.axis==0 else (pygame.K_DOWN if new>0 else pygame.K_UP)
    return self.controller_direction(key)
   return True
  if e.type==pygame.JOYHATMOTION and e.value!=(0,0):
   key=pygame.K_RIGHT if e.value[0]>0 else pygame.K_LEFT if e.value[0]<0 else pygame.K_UP if e.value[1]>0 else pygame.K_DOWN
   return self.controller_direction(key)
  if e.type==pygame.KEYDOWN and e.key==pygame.K_F11:
   self.full=not self.full;self.screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN) if self.full else pygame.display.set_mode((W*SCALE,H*SCALE));return True
  if self.state=='title' and e.type==pygame.KEYDOWN:
   if e.key in (pygame.K_RETURN,pygame.K_z):self.load() if SAVE.exists() else self.new_game()
   elif e.key==pygame.K_n:self.new_game()
  elif self.state=='dialog' and e.type==pygame.KEYDOWN and e.key in (pygame.K_RETURN,pygame.K_z,pygame.K_SPACE):
   self.dindex+=1
   if self.dindex>=len(self.dialog):
    if self.world.pending_boss:self.start_battle(['dragon'],'dragon')
    else:self.state='field'
  elif self.state=='field':self.field_input(e)
  elif self.state=='battle':self.battle_input(e)
  elif self.state=='victory' and e.type==pygame.KEYDOWN and e.key in (pygame.K_z,pygame.K_RETURN,pygame.K_SPACE):self.end_victory()
  elif self.state=='menu':self.menu_input(e)
  elif self.state=='bag':self.bag_input(e)
  elif self.state=='manual' and e.type==pygame.KEYDOWN:
   if e.key in (pygame.K_ESCAPE,pygame.K_x):self.state='menu'
   elif e.key in (pygame.K_LEFT,pygame.K_UP,pygame.K_a,pygame.K_w):self.manual_page=max(0,self.manual_page-1)
   elif e.key in (pygame.K_RIGHT,pygame.K_DOWN,pygame.K_d,pygame.K_s,pygame.K_z,pygame.K_RETURN):self.manual_page+=1
  elif self.state=='gameover' and e.type==pygame.KEYDOWN:self.load() if SAVE.exists() else self.new_game()
  elif self.state=='ending' and e.type==pygame.KEYDOWN:self.dindex+=1
  return True

 def update(self):
  now=pygame.time.get_ticks();dt=now-self.last_tick;self.last_tick=now
  seconds=min(.05,max(0,dt/1000))
  if self.state not in ('title','gameover'):self.playtime+=dt/1000
  if self.log_wait:self.log_wait-=1
  if self.toast_t:self.toast_t-=1
  if self.state=='field':
   k=pygame.key.get_pressed();dx=(k[pygame.K_RIGHT] or k[pygame.K_d])-(k[pygame.K_LEFT] or k[pygame.K_a]);dy=(k[pygame.K_DOWN] or k[pygame.K_s])-(k[pygame.K_UP] or k[pygame.K_w])
   if self.joy:
    ax=self.joy.get_axis(0);ay=self.joy.get_axis(1);hat=self.joy.get_hat(0) if self.joy.get_numhats() else (0,0)
    dx=dx+(1 if ax>.35 else -1 if ax<-.35 else 0)+hat[0]+(1 if 14 in self.pad_buttons else -1 if 13 in self.pad_buttons else 0);dy=dy+(1 if ay>.35 else -1 if ay<-.35 else 0)-hat[1]+(1 if 12 in self.pad_buttons else -1 if 11 in self.pad_buttons else 0)
   self.moving=bool(dx or dy)
   if self.moving:
    length=math.hypot(dx,dy) or 1
    self.move(dx/length*60*seconds,dy/length*60*seconds)
  self.world.update(seconds)

 def box(self,x,y,w,h,fill=(21,27,46)):
  pygame.draw.rect(self.canvas,INK,(x-2,y-2,w+4,h+4));pygame.draw.rect(self.canvas,WHITE,(x-1,y-1,w+2,h+2),1);pygame.draw.rect(self.canvas,fill,(x,y,w,h))

 def draw_party_member(self,index,x,y,direction=0,frame=1):
  # Sheet directions are down, left, right, up; field facing uses up/right/down/left.
  img=self.party_sheet.subsurface(self.party_source_rect(index,direction,frame))
  self.canvas.blit(img,(int(x-16),int(y-48)))

 def party_source_rect(self,index,direction=0,frame=1):
  sheet_dir={0:3,1:2,2:0,3:1}.get(direction,direction)
  return pygame.Rect((sheet_dir*8+frame%8)*32,index*48,32,48)


 def draw_title(self):
  self.canvas.fill((8,9,18))
  for x,y,s in self.stars:pygame.draw.rect(self.canvas,(70+s*30,75+s*25,95+s*25),(x,y,s,s))
  # dragon silhouette
  pygame.draw.polygon(self.canvas,(42,30,58),[(35,92),(92,55),(145,81),(172,45),(196,82),(286,58),(244,105),(286,125),(193,112),(160,148),(127,111),(45,128),(77,105)])
  self.canvas.blit(text('THE ASHEN',self.big,GOLD),(92,28));self.canvas.blit(text('CIRCUIT',self.big,CYAN),(112,49))
  self.canvas.blit(text('An original 16-bit dungeon RPG',self.font),(79,74))
  blink=(pygame.time.get_ticks()//500)%2
  if blink:self.canvas.blit(text('ENTER  Continue / Begin',self.font),(91,143))
  if SAVE.exists():self.canvas.blit(text('N / Xbox Y  New Game',self.small),(113,158))
  if self.toast_t:label(self.canvas,self.toast,8,171,CYAN,limit=75)

 def draw_room(self):
  self.world.draw_scene()

 def wrap(self,s,maxchars=48):
  out=[];line=''
  for w in s.split():
   if len(line)+len(w)+1>maxchars:out.append(line);line=w
   else:line=(line+' '+w).strip()
  if line:out.append(line)
  return out

 def draw_dialog(self):
  self.draw_room();name,line=self.dialog[min(self.dindex,len(self.dialog)-1)]
  panel(self.canvas,(4,112,312,65))
  label(self.canvas,name,11,118,GOLD)
  for i,l in enumerate(self.wrap(line,49)):label(self.canvas,l,11,130+i*10,WHITE)
  label(self.canvas,'A: NEXT',265,167,CYAN)

 def draw_battle(self):
  self.world.draw_scene()

 def draw_menu(self):
  self.draw_room();panel(self.canvas,(8,25,304,148))
  label(self.canvas,'FIELD MENU',18,34,GOLD,scale=2)
  opts=self.menu_options()
  for i,o in enumerate(opts):label(self.canvas,('> ' if i==self.room_menu else '  ')+o,18,56+i*14,GOLD if i==self.room_menu else WHITE)
  label(self.canvas,f'WEAPON {self.weapon}/2',179,61,CYAN)
  label(self.canvas,f'ARMOR  {self.armor}/2',179,74,CYAN)
  label(self.canvas,f'TOMES  {len(self.learned)}/{len(ALL_TOMES)}',179,91,WHITE)
  label(self.canvas,f'CHESTS {len(self.opened_chests)}/73',179,104,WHITE)
  label(self.canvas,f'TIME   {int(self.playtime//60):02}:{int(self.playtime%60):02}',179,122,WHITE)
  label(self.canvas,'D-PAD: SELECT   A: CONFIRM   B: BACK',18,160,CYAN)

 def draw_manual(self):
  self.draw_progression_manual()

 def draw_ending(self):
  lines=[('TESS','The western sky is still burning.'),('BRANN','The villages had warning sirens. Some will have made it.'),('MAREK','Some.'),('RIAN','Vael wanted one shot to prove the old world could be owned.'),('TESS','And we proved it could bleed.'),('RIAN','Tomorrow we count the cost. Tonight, we make sure no one rebuilds this place.'),('SYSTEM','VHAROS TERMINATED — CAELUS ENGINE ENTERING FINAL DARK'),('MAREK','For once, a machine says exactly the right thing.')]
  if self.dindex<len(lines):self.dialog=lines;self.draw_dialog()
  else:
   self.canvas.fill((7,8,15));self.canvas.blit(text('THE ASHEN CIRCUIT',self.big,GOLD),(79,48));self.canvas.blit(text('The weapon fired. The dragon fell.',self.font),(84,79));self.canvas.blit(text('But this was only the first shot of the coming war.',self.small),(63,96));self.canvas.blit(text(f'Completion time  {int(self.playtime//60)}m {int(self.playtime%60)}s',self.font,CYAN),(92,122));self.canvas.blit(text('Thank you for playing.',self.font),(105,145))

 def draw(self):
  if self.state=='title':self.draw_title()
  elif self.state=='field':self.draw_room()
  elif self.state=='dialog':self.draw_dialog()
  elif self.state in ('battle','victory'):self.draw_battle()
  elif self.state=='menu':self.draw_menu()
  elif self.state=='manual':self.draw_manual()
  elif self.state=='bag':self.draw_bag()
  elif self.state=='gameover':self.canvas.fill(INK);self.canvas.blit(text('THE CIRCUIT CLAIMED YOU',self.big,RED),(55,69));self.canvas.blit(text('Press any key to restore the last save.',self.font),(71,104))
  elif self.state=='ending':self.draw_ending()
  size=self.screen.get_size();scaled=pygame.transform.scale(self.canvas,(min(size[0],size[1]*16//9),min(size[1],size[0]*9//16)));self.screen.fill((0,0,0));self.screen.blit(scaled,((size[0]-scaled.get_width())//2,(size[1]-scaled.get_height())//2));pygame.display.flip()

 def run(self):
  go=True
  while go:
   for e in pygame.event.get():
    if self.event(e) is False:go=False
   self.update();self.draw();self.clock.tick(FPS)
  pygame.quit()

def smoke_test(g):
 # Exercise the packaged modules and sprite asset without touching a save.
 g.state='field';g.room='foundry';g.world.arrive()
 enemy=g.world.patrols[0].pawns[0]
 g.px,g.py=enemy.pos;g.world.grace=0;g.world.update(1/60)
 assert g.state=='battle', 'Visible contact did not start combat'
 assert g.music_ready and g.battle_music_playing, 'Supplied battle theme did not start'
 for _ in range(600):
  g.world.update(1/60)
  if not g.world.busy:break
 assert not g.world.busy, 'Party formation did not finish'
 confirm=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z)
 for _ in range(600):
  g.world.update(1/60)
  if g.turn_actor>=0:break
 assert g.turn_actor>=0, 'No party ATB reached ready'
 g.battle_input(confirm)
 target=g.world.target;hp=target.hp
 g.battle_input(confirm)
 for _ in range(600):
  g.world.update(1/60)
  if not g.world.busy:break
 g.draw()
 assert target.hp<hp, 'Queued attack failed'
 before=sum(h.hp for h in g.party)
 enemy=next(e for e in g.world.active.pawns if e.unit.alive())
 enemy.unit.atb=100;enemy.unit.ready_stamp=0
 for _ in range(600):
  g.world.update(1/60)
  if sum(h.hp for h in g.party)<before:break
 assert sum(h.hp for h in g.party)<before, 'Enemy active-time attack did not fire'
 for foe in g.enemies:foe.hp=0
 g.check_battle()
 assert not g.battle_music_playing, 'Battle theme continued after the final enemy fell'
 # Exercise real treasure, controller menus, and persistence against a temporary
 # save, never against the player's data.
 import tempfile
 global SAVE
 original_save=SAVE
 with tempfile.TemporaryDirectory(prefix='ashen-smoke-') as folder:
  try:
   SAVE=Path(folder)/'save.json'
   g.new_game();g.state='field';g.px,g.py=g.treasure['gate'][0].pos
   g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
   assert g.knows(g.party[0],'Frost Edge'), 'Chest tome was not learned'
   g.state='field';g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=7))
   g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
   assert g.state=='bag', 'Controller could not open growth menu'
   g.bag_index=g.bag_options().index('Strength +1')
   old=g.party[0].pow
   for _ in range(3):g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
   g.load();assert g.party[0].pow==old+1, 'Permanent growth did not survive loading'
   g.state='bag';g.draw()
  finally:SAVE=original_save
 print('SMOKE OK: battle stances, active time, supplied music lifecycle, motion sprites, readable HUD, tomes, Xbox menus, saves')
 pygame.quit()

if __name__=='__main__':
 instance=Game()
 if '--smoke-test' in sys.argv:smoke_test(instance)
 else:instance.run()
