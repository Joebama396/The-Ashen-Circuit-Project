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
    g.room='foundry';g.state='field';g.px,g.py=160,264;g.facing=1
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
        snap('67_hd_overworld_placeholder.png')
        for _ in range(240):
            if g.state!='field':break
            target=g.world.patrols[0].pawns[0]
            dx,dy=target.x-g.px,target.y-g.py
            length=max(.01,(dx*dx+dy*dy)**.5)
            g.move(dx/length*1.7,dy/length*1.7)
            frame()
        if g.state!='battle':raise RuntimeError('Demo never made contact')
        while g.world.busy:frame()
        frame(4)
        snap('68_hd_seamless_combat.png')
        while g.turn_actor<0:frame()
        frame(12)
        snap('39_seamless_battle.png')
        confirm();frame(6);confirm()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.54:frame()
        snap('40_seamless_melee.png')
        while g.world.busy:frame()
        frame(10)
        # Force a long melee approach to demonstrate the distance-selected
        # arcing jump attack separately from the nearby ground rush above.
        rian=g.world.heroes[0]
        jump_target=next(p for p in g.world.active.pawns if p.unit.alive())
        rian.x,rian.y=160,256;rian.home=rian.pos
        jump_target.x,jump_target.y=448,192;jump_target.home=jump_target.pos
        g.party[0].atb=100;g.turn_actor=0
        g.execute(g.party[0],'Attack');confirm()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.17:frame()
        snap('48_jump_attack.png')
        while g.world.busy:frame()
        frame(10)
        # Use the real target picker, then the real queued rail-pistol action.
        g.party[1].atb=100;g.turn_actor=1
        g.execute(g.party[1],'Rail Shot')
        g.battle_input(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
        frame(5);confirm()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.36:frame()
        snap('41_seamless_rail_projectile.png')
        while g.world.busy:frame()
        frame(10)
        # Let a real enemy active-time gauge interrupt without player input.
        for h in g.party:h.atb=0
        enemy=next(p for p in g.world.active.pawns if p.unit.alive())
        enemy.unit.atb=99
        while not (g.world.action and g.world.action['enemy']):frame()
        while g.world.action and g.world.action['elapsed']/g.world.action['duration']<.48:frame()
        snap('46_active_enemy_attack.png')
        while g.world.busy:frame()
        frame(30)
    finally:
        if encoder:
            encoder.stdin.close()
            if encoder.wait()!=0:raise RuntimeError('Video encoding failed')
        pygame.quit()


if __name__=='__main__':main()
