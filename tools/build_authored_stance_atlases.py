#!/usr/bin/env python3
"""Pack the approved directional walk and battle-ready sprites for runtime use.

The source sheets remain untouched. Runtime cells are 96x96 and are positioned
on the shared (48, 88) ground anchor. Battle art is reduced offline with
nearest-neighbour sampling to match each hero's visible overworld height;
runtime rendering never scales it.
"""
from pathlib import Path
import sys

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from render_config import BATTLE_SPRITE_SCALE_RATIOS

STANCES = ROOT / "assets/characters/stances"
CHARACTERS = ("rian", "merek", "tess", "brann")
DIRECTIONS = ("down", "left", "right", "up")

ACTOR_CELL = (96, 96)
GROUND_Y = 88
WALK_FRAME = (64, 64)
BATTLE_FRAME = (64, 80)
WALK_PHASES = (0, 1, 2, 3, 0, 1, 2, 3)

WALK_OUTPUT = ROOT / "assets/characters/party_overworld_hd_v2.png"
BATTLE_OUTPUT = ROOT / "assets/characters/party_battle_ready_hd_v1.png"


def load_rgba(path, expected_size):
    image = Image.open(path).convert("RGBA")
    if image.size != expected_size:
        raise ValueError(f"{path} must be {expected_size}, got {image.size}")
    return image


def place_on_actor_cell(source):
    """Center a native sprite and place its last visible row at y=87."""
    bounds = source.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Authored stance frame is empty")
    target = Image.new("RGBA", ACTOR_CELL, (0, 0, 0, 0))
    x = (ACTOR_CELL[0] - source.width) // 2
    y = GROUND_Y - bounds[3]
    if x + bounds[0] < 0 or x + bounds[2] > ACTOR_CELL[0]:
        raise ValueError("Authored stance exceeds the actor cell horizontally")
    if y + bounds[1] < 0 or y + bounds[3] > GROUND_Y:
        raise ValueError("Authored stance exceeds the actor cell vertically")
    target.alpha_composite(source, (x, y))
    return target


def shrink_actor_cell(cell, hero):
    """Bake one battle cell to the hero's overworld silhouette scale."""
    numerator, denominator = BATTLE_SPRITE_SCALE_RATIOS[hero]
    width = (cell.width * numerator + denominator // 2) // denominator
    height = (cell.height * numerator + denominator // 2) // denominator
    scaled = cell.resize((width, height), Image.Resampling.NEAREST)
    anchor_x = (ACTOR_CELL[0] // 2 * numerator + denominator // 2) // denominator
    anchor_y = (GROUND_Y * numerator + denominator // 2) // denominator
    result = Image.new("RGBA", ACTOR_CELL, (0, 0, 0, 0))
    result.alpha_composite(
        scaled, (ACTOR_CELL[0] // 2 - anchor_x, GROUND_Y - anchor_y)
    )
    return result


def walk_frames(character):
    strips = {
        direction: load_rgba(
            STANCES / f"{character}_walk_{direction}.png", (256, 64)
        )
        for direction in ("down", "right", "up")
    }
    frames = {}
    for direction, strip in strips.items():
        frames[direction] = [
            strip.crop((frame * 64, 0, (frame + 1) * 64, 64))
            for frame in range(4)
        ]
    # Rian's approved profile strip was authored facing left despite retaining
    # the historical ``rian_walk_right.png`` filename.  Treat that strip as
    # left-facing and derive his right-facing frames from it.  The other three
    # source strips are correctly right-facing.
    if character == "rian":
        left_frames = frames.pop("right")
        frames["left"] = left_frames
        frames["right"] = [ImageOps.mirror(frame) for frame in left_frames]
    else:
        frames["left"] = [ImageOps.mirror(frame) for frame in frames["right"]]
    return frames


def battle_frames(character):
    # Authored sheet order: front/down, back/up, profile left.
    sheet = load_rgba(STANCES / f"{character}_battle_ready.png", (192, 80))
    down, up, left = [
        sheet.crop((column * 64, 0, (column + 1) * 64, 80))
        for column in range(3)
    ]
    return {"down": down, "left": left, "right": ImageOps.mirror(left), "up": up}


def build_walk_atlas():
    atlas = Image.new("RGBA", (32 * ACTOR_CELL[0], 4 * ACTOR_CELL[1]), (0, 0, 0, 0))
    for hero, character in enumerate(CHARACTERS):
        source = walk_frames(character)
        for direction_index, direction in enumerate(DIRECTIONS):
            for runtime_frame, authored_frame in enumerate(WALK_PHASES):
                cell = place_on_actor_cell(source[direction][authored_frame])
                x = (direction_index * 8 + runtime_frame) * ACTOR_CELL[0]
                atlas.alpha_composite(cell, (x, hero * ACTOR_CELL[1]))
    return atlas


def build_battle_atlas():
    atlas = Image.new("RGBA", (4 * ACTOR_CELL[0], 4 * ACTOR_CELL[1]), (0, 0, 0, 0))
    for hero, character in enumerate(CHARACTERS):
        source = battle_frames(character)
        for direction_index, direction in enumerate(DIRECTIONS):
            cell = shrink_actor_cell(place_on_actor_cell(source[direction]), hero)
            atlas.alpha_composite(
                cell, (direction_index * ACTOR_CELL[0], hero * ACTOR_CELL[1])
            )
    return atlas


def save_checked(image, path):
    temporary = path.with_suffix(".writing.png")
    image.save(temporary)
    with Image.open(temporary) as check:
        check.load()
        if check.size != image.size or check.mode != "RGBA":
            raise RuntimeError(f"PNG verification failed for {path.name}")
    temporary.replace(path)


def main():
    save_checked(build_walk_atlas(), WALK_OUTPUT)
    save_checked(build_battle_atlas(), BATTLE_OUTPUT)
    print(WALK_OUTPUT)
    print(BATTLE_OUTPUT)


if __name__ == "__main__":
    main()
