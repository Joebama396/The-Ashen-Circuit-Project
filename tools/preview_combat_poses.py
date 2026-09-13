"""Render PNG QA frames for the independently layered combat arm poses."""
import os
from pathlib import Path
import sys

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import pygame
import game


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'previews'


def main():
    OUT.mkdir(exist_ok=True)
    g=game.Game();g.room='foundry';g.state='field';g.px,g.py=80,125
    g.world.arrive();patrol=g.world.patrols[0];g.world.contact=patrol
    g.start_battle([p.unit.key for p in patrol.pawns])
    for _ in range(300):
        g.world.update(1/60)
        if not g.world.busy:break
    for enemy in g.enemies:enemy.atb=0;enemy.hp=0
    for hero in g.party:hero.atb=0
    for pawn,pos in zip(g.world.heroes,((58,120),(128,120),(198,120),(266,120))):
        pawn.x,pawn.y=pos;pawn.home=pos;pawn.goal=pos;pawn.direction=1;pawn.moving=False
    for pawn,state in zip(g.world.heroes,
                          ('low_sword_ready','high_ready','split_arm_profile','low_ready')):
        g.world.set_animation(pawn,state,0)

    def save(name):
        g.draw();path=OUT/name
        temporary=path.with_suffix('.tmp.png')
        pygame.image.save(g.screen,str(temporary));pygame.image.load(str(temporary))
        temporary.replace(path);print(path)

    save('49_decoupled_combat_stances.png')

    rian=g.world.heroes[0]
    rian.x,rian.y=95,115;rian.home=rian.pos
    for state,name in (
        ('overhead_raise','50_rian_overhead_raise.png'),
        ('downward_landing_strike','51_rian_downward_landing_strike.png')):
        g.world.set_animation(rian,state,0);save(name)

    marek,brann=g.world.heroes[1],g.world.heroes[3]
    g.world.set_animation(rian,'low_sword_ready',0)
    g.world.set_animation(marek,'extended_isosceles',0)
    g.world.set_animation(brann,'shouldered_firing',0)
    save('52_ranged_firing_stances.png')
    pygame.quit()


if __name__=='__main__':main()
