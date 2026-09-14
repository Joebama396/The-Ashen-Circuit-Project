"""Render PNG QA frames for the independently layered combat arm poses."""
import os
from pathlib import Path
import sys

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import pygame
import game
from combat_poses import COMBAT_CELL_H, COMBAT_CELL_W, COMBAT_GROUND_ANCHOR


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'previews'


def main():
    OUT.mkdir(exist_ok=True)
    g=game.Game();g.room='foundry';g.state='field';g.px,g.py=160,264
    g.world.arrive();patrol=g.world.patrols[0];g.world.contact=patrol
    g.start_battle([p.unit.key for p in patrol.pawns])
    for _ in range(300):
        g.world.update(1/60)
        if not g.world.busy:break
    for enemy in g.enemies:enemy.atb=0;enemy.hp=0
    for hero in g.party:hero.atb=0
    for pawn,pos in zip(g.world.heroes,((96,240),(224,240),(352,240),(480,240))):
        pawn.x,pawn.y=pos;pawn.home=pos;pawn.goal=pos;pawn.direction=1;pawn.moving=False
    for pawn,state in zip(g.world.heroes,
                          ('low_sword_ready','high_ready','split-arm','low_ready')):
        g.world.set_animation(pawn,state,0)

    def save(name):
        g.draw();path=OUT/name
        temporary=path.with_suffix('.tmp.png')
        pygame.image.save(g.screen,str(temporary));pygame.image.load(str(temporary))
        temporary.replace(path);print(path)

    save('62_hd_native_stances.png')

    rian=g.world.heroes[0]
    rian.x,rian.y=160,224;rian.home=rian.pos
    for state,name in (
        ('overhead_raise','63_hd_rian_overhead.png'),
        ('downward_landing_strike','64_hd_rian_landing.png')):
        g.world.set_animation(rian,state,0);save(name)

    marek,brann=g.world.heroes[1],g.world.heroes[3]
    g.world.set_animation(rian,'low_sword_ready',0)
    g.world.set_animation(marek,'extended_isosceles',0)
    g.world.set_animation(brann,'shouldered_firing',0)
    save('65_hd_ranged_stances.png')

    # Native-cell inspection strip: Rian idle/raise/land, Merek ready/fire,
    # Tess idle/raise/land, and Brann ready/fire. Scaling happens only in this
    # QA image so individual source pixels remain easy to inspect.
    states=((0,'low_sword_ready'),(0,'overhead_raise'),
            (0,'downward_landing_strike'),(1,'high_ready'),
            (1,'extended_isosceles'),(2,'split-arm'),
            (2,'overhead_raise'),(2,'downward_landing_strike'),
            (3,'low_ready'),(3,'shouldered_firing'))
    closeups=pygame.Surface((5*COMBAT_CELL_W,2*COMBAT_CELL_H));closeups.fill((24,30,38))
    for index,(hero,state) in enumerate(states):
        cell=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
        g.world.combat_rig.draw(cell,hero,state,*COMBAT_GROUND_ANCHOR,True)
        closeups.blit(cell,((index%5)*COMBAT_CELL_W,
                            (index//5)*COMBAT_CELL_H))
    closeups=pygame.transform.scale(closeups,(5*COMBAT_CELL_W*3,
                                              2*COMBAT_CELL_H*3))
    path=OUT/'66_hd_pose_layer_closeups.png'
    pygame.image.save(closeups,str(path));pygame.image.load(str(path));print(path)
    pygame.quit()


if __name__=='__main__':main()
