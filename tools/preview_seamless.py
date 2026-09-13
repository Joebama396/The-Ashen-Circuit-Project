"""Capture actual gameplay frames and an optional short, silent motion demo.

Run from the project root with PYTHONPATH=./vendor.
This never calls new_game/save/transition and never touches a player's save.
"""
import argparse
import os
from pathlib import Path
import random
import subprocess
import sys

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
import game


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--video',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    out=root/'previews'
    out.mkdir(exist_ok=True)
    random.seed(23)
    g=game.Game()
    # Stage a party that has already collected these tomes for animation QA.
    g.learned.update(('Rail Shot','Venom Cut','Incendiary'))
    g.room='foundry';g.state='field';g.px,g.py=77,137;g.facing=1
    g.world.arrive();g.world.clock=0
    encoder=None
    if args.video:
        encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
            '-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-',
            '-an','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(out/'ashen_circuit_seamless_demo.mp4')],stdin=subprocess.PIPE)

    def frame(count=1):
        for _ in range(count):
            g.world.update(1/30);g.draw()
            if encoder:encoder.stdin.write(pygame.image.tostring(g.screen,'RGB'))

    def snap(filename):
        g.draw()
        temporary=out/(filename+'.tmp.png')
        pygame.image.save(g.screen,str(temporary))
        pygame.image.load(str(temporary))  # Validate before replacing a good PNG.
        temporary.replace(out/filename)
        print(out/filename)

    def confirm():
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z))

    try:
        frame(24)
        snap('38_seamless_exploration.png')
        for _ in range(240):
            if g.state!='field':break
            target=g.world.patrols[0].pawns[0]
            dx,dy=target.x-g.px,target.y-g.py
            length=max(.01,(dx*dx+dy*dy)**.5)
            g.move(dx/length*1.7,dy/length*1.7)
            frame()
        if g.state!='battle':raise RuntimeError('Demo never made contact')
        while g.world.busy:frame()
        frame(24)
        snap('39_seamless_battle.png')
        confirm();frame(15);confirm()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.54:frame()
        snap('40_seamless_melee.png')
        while g.world.busy:frame()
        frame(18)
        # Use the real target picker, then the real queued rail-pistol action.
        g.execute(g.party[1],'Rail Shot')
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
        frame(15);confirm()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.36:frame()
        snap('41_seamless_rail_projectile.png')
        while g.world.busy:frame()
        frame(18)
        g.execute(g.party[2],'Venom Cut');frame(12);confirm()
        while g.world.busy:frame()
        frame(18)
        g.execute(g.party[3],'Incendiary')
        while g.world.busy:frame()
        frame(45)
    finally:
        if encoder:
            encoder.stdin.close()
            if encoder.wait()!=0:raise RuntimeError('Video encoding failed')
        pygame.quit()


if __name__=='__main__':main()
