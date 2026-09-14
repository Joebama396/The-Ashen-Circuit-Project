#!/usr/bin/env python3
"""Pack Rian's 29x64x64 chroma-key master strip into 96x96 runtime cells."""
from pathlib import Path
import argparse

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / 'assets/characters/rian_animation_master.png'
DEFAULT_OUTPUT = ROOT / 'assets/characters/rian_battle_animations_hd_v1.png'
FRAME_W = 64
FRAME_H = 64
FRAME_COUNT = 29
ACTOR_W = 96
ACTOR_H = 96
CELL_OFFSET = (16, 24)


def chroma_to_alpha(cell):
    """Remove exact/near #ff00ff without touching Rian's red or blue palette."""
    cell = cell.convert('RGBA')
    pixels = cell.load()
    for y in range(cell.height):
        for x in range(cell.width):
            red, green, blue, alpha = pixels[x, y]
            if red >= 245 and green <= 12 and blue >= 245:
                pixels[x, y] = (0, 0, 0, 0)
            elif alpha:
                pixels[x, y] = (red, green, blue, 255)
    return cell


def build(source=DEFAULT_SOURCE, output=DEFAULT_OUTPUT):
    source = Path(source)
    output = Path(output)
    with Image.open(source) as opened:
        master = opened.convert('RGBA')
    required = (FRAME_W * FRAME_COUNT, FRAME_H)
    if master.size != required:
        raise ValueError(f'Rian master strip must be exactly {required}, got {master.size}')

    atlas = Image.new('RGBA', (ACTOR_W * FRAME_COUNT, ACTOR_H), (0, 0, 0, 0))
    for frame in range(FRAME_COUNT):
        cell = master.crop((frame * FRAME_W, 0, (frame + 1) * FRAME_W, FRAME_H))
        cell = chroma_to_alpha(cell)
        atlas.alpha_composite(cell, (frame * ACTOR_W + CELL_OFFSET[0], CELL_OFFSET[1]))

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.writing.png')
    atlas.save(temporary)
    with Image.open(temporary) as check:
        check.load()
        if check.size != (ACTOR_W * FRAME_COUNT, ACTOR_H) or check.mode != 'RGBA':
            raise RuntimeError('Written battle atlas failed validation')
    temporary.replace(output)
    return atlas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output)


if __name__ == '__main__':
    main()

