"""Render both facings for the Merek and Brann alignment regression."""
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
OUTPUT=ROOT/'previews/69_merek_brann_facing_alignment.png'


def main():
    pygame.init();pygame.display.set_mode((1,1))
    g=game.Game()
    canvas=pygame.Surface((4*COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    canvas.fill((24,30,38,255))
    entries=((1,'high_ready',False),(1,'high_ready',True),
             (3,'low_ready',False),(3,'low_ready',True))
    for index,(hero,state,facing_right) in enumerate(entries):
        cell=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
        g.world.combat_rig.draw(cell,hero,state,*COMBAT_GROUND_ANCHOR,
                                facing_right)
        canvas.blit(cell,(index*COMBAT_CELL_W,0))
    enlarged=pygame.transform.scale(
        canvas,(canvas.get_width()*3,canvas.get_height()*3))
    temporary=OUTPUT.with_suffix('.writing.png')
    pygame.image.save(enlarged,str(temporary))
    pygame.image.load(str(temporary))
    temporary.replace(OUTPUT)
    print(OUTPUT)
    pygame.quit()


if __name__=='__main__':main()
