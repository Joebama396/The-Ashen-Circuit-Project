#!/usr/bin/env python3
"""Build game-ready character sheets from the character art references.

Overworld layout: 4 character rows x 4 direction groups x 4 walk frames.
Directions are Down, Left, Right, Up. Each frame is 32x48 pixels, sourced from
an individually isolated silhouette rather than an equal-width crop.
Battle layout: four 64x80 left-facing three-quarter-profile cells. Each battle
character is sourced from a separately isolated silhouette to prevent clipping
or neighboring parts from crossing cell boundaries.
"""
from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/characters'
OW_OUT=ASSETS/'party_overworld_v4.png'
BATTLE_OUT=ASSETS/'party_battle_v6.png'
NAMES=('rian','marek','tess','brann')
DIRECTIONS=('down','left','right','up')
DIRECTION_REFS=[[ASSETS/f'{name}_{direction}_v7.png' for direction in DIRECTIONS] for name in NAMES]
BATTLE_REFS=[ASSETS/f'{name}_battle_v6.png' for name in NAMES]

def transparency(im):
 """Preserve real alpha or flood away an edge-connected gray checkerboard."""
 im=im.convert('RGBA');a=np.asarray(im).copy();rgb=a[:,:,:3].astype(np.int16)
 if a[:,:,3].min()==255:
  candidate=(rgb.max(2)-rgb.min(2)<18)&(rgb.mean(2)>105)
  background=np.zeros(candidate.shape,dtype=bool);queue=deque()
  for x in range(candidate.shape[1]):
   if candidate[0,x]: background[0,x]=True;queue.append((0,x))
   if candidate[-1,x] and not background[-1,x]: background[-1,x]=True;queue.append((candidate.shape[0]-1,x))
  for y in range(candidate.shape[0]):
   if candidate[y,0] and not background[y,0]: background[y,0]=True;queue.append((y,0))
   if candidate[y,-1] and not background[y,-1]: background[y,-1]=True;queue.append((y,candidate.shape[1]-1))
  while queue:
   y,x=queue.popleft()
   for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
    if 0<=ny<candidate.shape[0] and 0<=nx<candidate.shape[1] and candidate[ny,nx] and not background[ny,nx]:
     background[ny,nx]=True;queue.append((ny,nx))
  a[:,:,3][background]=0
 a[:,:,:3][a[:,:,3]==0]=0
 return Image.fromarray(a.astype('uint8'),'RGBA')

def fit_crisp(im,size,pad=1):
 """Downsample a silhouette, then snap its alpha to the pixel grid."""
 im=im.copy();im.thumbnail((size[0]-pad*2,size[1]-pad*2),Image.Resampling.LANCZOS)
 a=np.asarray(im).copy();keep=a[:,:,3]>=144;a[~keep]=0;a[:,:,3][keep]=255
 im=Image.fromarray(a.astype('uint8'),'RGBA')
 out=Image.new('RGBA',size,(0,0,0,0));out.alpha_composite(im,((size[0]-im.width)//2,size[1]-im.height-pad));return out

def walk_frame(base,phase):
 if phase in (1,3):return base.copy()
 out=Image.new('RGBA',base.size,(0,0,0,0));split=int(base.height*.72)
 top=base.crop((0,0,base.width,split));out.alpha_composite(top,(0,-1))
 left=base.crop((0,split,base.width//2,base.height));right=base.crop((base.width//2,split,base.width,base.height))
 step=-1 if phase==0 else 1
 out.alpha_composite(left,(step,split-1));out.alpha_composite(right,(base.width//2-step,split-1));return out

def build_overworld():
 sheet=Image.new('RGBA',(32*16,48*4),(0,0,0,0))
 for row,paths in enumerate(DIRECTION_REFS):
  for direction,path in enumerate(paths):
   base=fit_crisp(transparency(Image.open(path)),(32,48))
   for phase in range(4):
    frame=walk_frame(base,phase);x=(direction*4+phase)*32
    sheet.alpha_composite(frame,(x,row*48))
 sheet.save(OW_OUT)

def build_battle():
 sheet=Image.new('RGBA',(64*4,80),(0,0,0,0))
 for i,path in enumerate(BATTLE_REFS):
  sprite=transparency(Image.open(path))
  sheet.alpha_composite(fit_crisp(sprite,(64,80)),(i*64,0))
 sheet.save(BATTLE_OUT)

if __name__=='__main__':
 build_overworld();build_battle();print(OW_OUT);print(BATTLE_OUT)
