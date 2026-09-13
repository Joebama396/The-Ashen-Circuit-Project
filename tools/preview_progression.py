"""Capture the game's real treasure and progression UI using an isolated save."""
import os
from pathlib import Path
import sys
import tempfile

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import game


def main():
    out = Path(__file__).resolve().parents[1]/'previews'
    out.mkdir(exist_ok=True)
    original = game.SAVE
    with tempfile.TemporaryDirectory(prefix='ashen-preview-') as folder:
        try:
            game.SAVE = Path(folder)/'save.json'
            g = game.Game()
            g.state = 'field'
            g.px, g.py = 112, 120
            g.world.arrive()

            def snap(name):
                g.draw()
                temporary = out/(name+'.tmp.png')
                pygame.image.save(g.screen, str(temporary))
                pygame.image.load(str(temporary))
                temporary.replace(out/name)
                print(out/name)

            snap('42_treasure_entrance.png')
            for slot in range(4):
                chest = g.treasure['gate'][slot]
                g.state = 'field'
                g.px, g.py = chest.pos
                g.open_chest(chest)
            g.dindex = 0
            snap('43_tome_discovery.png')
            g.state = 'bag'
            g.bag_index = g.bag_options().index('Strength +1')
            g.bag_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
            g.bag_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
            snap('44_growth_assignment.png')
            g.bag_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
            g.state = 'manual'
            g.manual_type = 'party'
            snap('45_party_stats_and_tomes.png')
        finally:
            game.SAVE = original
            pygame.quit()


if __name__ == '__main__':
    main()
