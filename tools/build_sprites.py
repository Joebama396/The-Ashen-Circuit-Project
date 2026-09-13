#!/usr/bin/env python3
"""Build the editable 24x32 character sprite sheet used by the game.

Layout: four character rows. Each row contains Down, Left, Right, Up groups;
each direction has three walk frames. Transparent magenta is never used.
"""
from pathlib import Path
from PIL import Image, ImageDraw

FW,FH=24,32
OUT=Path(__file__).resolve().parents[1]/'assets/characters/party_sprites.png'
BATTLE_OUT=Path(__file__).resolve().parents[1]/'assets/characters/party_battle_sprites.png'
CONCEPT=Path(__file__).resolve().parents[1]/'assets/characters/party_concept.png'

PALE=(224,177,139,255); DARK=(94,55,47,255); DEEP=(13,18,28,255)
CAST=[
 {'name':'Rian','skin':PALE,'hair':(139,46,42,255),'main':(31,59,91,255),'trim':(115,203,225,255),'metal':(200,218,224,255),'weapon':'sword'},
 {'name':'Mira','skin':(129,77,52,255),'hair':(25,22,29,255),'main':(33,114,111,255),'trim':(244,188,54,255),'metal':(63,214,225,255),'weapon':'pistol'},
 {'name':'Tess','skin':PALE,'hair':(201,197,211,255),'main':(91,53,125,255),'trim':(83,221,102,255),'metal':(125,239,97,255),'weapon':'dagger'},
 {'name':'Brann','skin':(205,146,105,255),'hair':(73,52,42,255),'main':(143,62,31,255),'trim':(237,142,40,255),'metal':(78,82,91,255),'weapon':'launcher'},
]

def px(d,xy,fill): d.rectangle(xy,fill=fill)

def sprite(cfg,direction,frame):
 im=Image.new('RGBA',(FW,FH),(0,0,0,0));d=ImageDraw.Draw(im)
 bob=1 if frame==1 else 0; leftstep=1 if frame==0 else -1 if frame==2 else 0
 skin,hair,main,trim,metal=[cfg[k] for k in ('skin','hair','main','trim','metal')]
 # cast shadow
 px(d,(6,29,18,31),(8,10,16,100))
 # legs and boots
 px(d,(8+leftstep,23+bob,11+leftstep,28+bob),DEEP);px(d,(14-leftstep,23+bob,17-leftstep,28+bob),DEEP)
 px(d,(7+leftstep,28+bob,11+leftstep,30+bob),(38,34,36,255));px(d,(14-leftstep,28+bob,18-leftstep,30+bob),(38,34,36,255))
 # coat/body silhouette
 if cfg['name']=='Brann':px(d,(6,11+bob,18,24+bob),main);px(d,(4,14+bob,20,21+bob),main)
 else:px(d,(7,11+bob,17,24+bob),main);px(d,(5,14+bob,19,21+bob),main)
 px(d,(8,17+bob,16,19+bob),trim);px(d,(11,11+bob,12,23+bob),trim)
 # neck and face
 px(d,(10,8+bob,14,12+bob),skin);px(d,(8,3+bob,16,10+bob),skin)
 # direction-specific face and hair
 if direction==3: # back
  px(d,(7,2+bob,17,10+bob),hair);px(d,(8,9+bob,16,12+bob),hair)
 elif direction in (1,2):
  flip=direction==2;px(d,(7,2+bob,16,6+bob),hair);px(d,((7 if flip else 14),5+bob,(9 if flip else 17),10+bob),hair)
  ex=14 if flip else 9;px(d,(ex,6+bob,ex,6+bob),(28,30,36,255))
 else:
  px(d,(7,2+bob,17,6+bob),hair);px(d,(7,5+bob,9,10+bob),hair);px(d,(15,5+bob,17,10+bob),hair)
  px(d,(9,7+bob,10,7+bob),(28,30,36,255));px(d,(14,7+bob,15,7+bob),(28,30,36,255))
 # distinct costume and equipment clusters
 if cfg['name']=='Rian':
  px(d,(6,19+bob,8,27+bob),(25,47,78,255));px(d,(16,19+bob,18,27+bob),(25,47,78,255))
  # diagonal sword and frozen edge
  px(d,(18,8+bob,20,25+bob),metal);px(d,(20,7+bob,21,23+bob),trim);px(d,(16,22+bob,21,24+bob),(105,77,44,255))
 elif cfg['name']=='Mira':
  px(d,(7,2+bob,9,4+bob),trim);px(d,(15,3+bob,17,5+bob),trim);px(d,(5,18+bob,8,23+bob),(108,72,37,255))
  px(d,(17,15+bob,22,18+bob),metal);px(d,(20,17+bob,23,19+bob),(184,137,43,255));px(d,(18,14+bob,19,15+bob),(250,213,61,255))
 elif cfg['name']=='Tess':
  # hood, scarf tails, twin green daggers and vials
  px(d,(6,1+bob,18,4+bob),main);px(d,(5,3+bob,8,12+bob),main);px(d,(16,3+bob,19,12+bob),main)
  px(d,(4,12+bob,7,23+bob),main);px(d,(17,11+bob,20,21+bob),main)
  px(d,(3,17+bob,5,24+bob),metal);px(d,(19,16+bob,21,23+bob),metal);px(d,(8,20+bob,10,23+bob),trim);px(d,(14,20+bob,16,23+bob),trim)
 elif cfg['name']=='Brann':
  px(d,(8,9+bob,16,11+bob),hair);px(d,(7,17+bob,17,20+bob),(76,53,39,255))
  # shell bandolier
  for i in range(4):px(d,(7+i*3,12+i*2+bob,8+i*3,14+i*2+bob),trim)
  # launcher
  px(d,(16,15+bob,23,20+bob),metal);px(d,(20,14+bob,23,21+bob),(33,36,43,255));px(d,(15,16+bob,18,18+bob),trim)
 return im

def main():
 OUT.parent.mkdir(parents=True,exist_ok=True)
 sheet=Image.new('RGBA',(FW*12,FH*4),(0,0,0,0))
 for row,cfg in enumerate(CAST):
  for direction in range(4):
   for frame in range(3):sheet.alpha_composite(sprite(cfg,direction,frame),((direction*3+frame)*FW,row*FH))
 sheet.save(OUT)
 # Derive higher-detail 48x72 battle poses from the approved concept lineup.
 # Crop coordinates are intentionally plain data so the poses can be replaced easily.
 if CONCEPT.exists():
  concept=Image.open(CONCEPT).convert('RGBA');crops=[(0,0,505,887),(455,0,900,887),(825,0,1320,887),(1260,0,1774,887)]
  battle=Image.new('RGBA',(48*4,72),(0,0,0,0))
  for i,box in enumerate(crops):
   ch=concept.crop(box);alpha=ch.getchannel('A');bbox=alpha.getbbox()
   if bbox:ch=ch.crop(bbox)
   ch.thumbnail((46,70),Image.Resampling.LANCZOS)
   battle.alpha_composite(ch,(i*48+(48-ch.width)//2,72-ch.height))
  battle.save(BATTLE_OUT)
 print(OUT);print(BATTLE_OUT)

if __name__=='__main__':main()
