#!/usr/bin/env python3
"""Derive eight connected walk poses from the approved four-direction sprites."""
from pathlib import Path
import math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'assets/characters/party_overworld_v4.png';OUTPUT=ROOT/'assets/characters/party_motion_v1.png';FRAMES=8

def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1);return t*t*(3-2*t)

def pose(cell,direction,phase,hero):
    source=np.asarray(cell,dtype=np.uint8);alpha=source[:,:,3];ys,xs=np.where(alpha>0)
    if not len(xs):return cell
    left,right,top,bottom=xs.min(),xs.max(),ys.min(),ys.max();yy,xx=np.mgrid[0:48,0:32].astype(float)
    u=(xx-(left+right)/2)/max(1,right-left);v=(yy-top)/max(1,bottom-top)
    stride=math.sin(phase*math.tau/FRAMES);sway=math.sin((phase-1)*math.tau/FRAMES);side=np.where(u<0,-1.,1.)
    lower=smooth(.63,.94,v);arms=smooth(.27,.40,v)*(1-smooth(.69,.79,v))*smooth(.12,.38,np.abs(u))
    coat=smooth(.52,.67,v)*(1-smooth(.91,1.0,v))*(1-smooth(.28,.48,np.abs(u)))
    hair=(1 if hero in (0,2) else 0)*smooth(.12,.28,v)*(1-smooth(.67,.78,v))*smooth(.20,.38,np.abs(u))
    dx=np.zeros_like(xx);dy=np.zeros_like(yy)
    if direction in (0,3):dy+=lower*side*stride*1.9;dx+=lower*side*abs(stride)*.55;dy-=arms*side*stride*1.45
    else:dx+=lower*side*stride*1.65;dy+=lower*np.where(side*stride>0,-.7,.7)*abs(stride);dx-=arms*side*stride*1.25
    dx+=coat*sway*1.05;dx-=hair*stride*.9;dy+=hair*abs(stride)*.35;dy-=smooth(.15,.85,v)*(.35 if phase in (2,6) else 0)
    coords=np.array([yy-dy,xx-dx]);result=np.stack([map_coordinates(source[:,:,c],coords,order=0,mode='constant',cval=0) for c in range(4)],axis=2).astype(np.uint8)
    result[result[:,:,3]<128]=0;result[:,:,3][result[:,:,3]>=128]=255
    return Image.fromarray(result,'RGBA')

def main():
    original=Image.open(SOURCE).convert('RGBA');sheet=Image.new('RGBA',(32*4*FRAMES,48*4),(0,0,0,0))
    for hero in range(4):
        for direction in range(4):
            base=original.crop(((direction*4+1)*32,hero*48,(direction*4+2)*32,(hero+1)*48))
            for phase in range(FRAMES):sheet.alpha_composite(pose(base,direction,phase,hero),((direction*FRAMES+phase)*32,hero*48))
    temporary=OUTPUT.with_suffix('.writing.png');sheet.save(temporary)
    with Image.open(temporary) as check:check.load();assert check.size==(1024,192) and check.mode=='RGBA'
    temporary.replace(OUTPUT);print(OUTPUT)

if __name__=='__main__':main()
