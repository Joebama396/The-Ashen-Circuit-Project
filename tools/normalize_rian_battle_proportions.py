#!/usr/bin/env python3
"""Restore Rian's unique v1.8 poses at a consistent, reference-led scale.

The archived source strips retain every authored action frame.  Each strip uses
one uniform scale factor for both axes, is placed in the engine's established
96x96 actor cell, and is anchored to the same ground line.  This gives broad
sword actions room without flattening Rian to fit a 64px source cell.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from PIL import Image

from tools.fix_rian_battle_transparency import replace_idle_strip


ROOT = Path(__file__).resolve().parents[1]
BATTLE_DIR = ROOT / "assets" / "characters" / "battle"
SOURCE_DIR = ROOT / "tools" / "reference" / "rian_v1_8_action_sources"
SOURCE_CELL = 64
RUNTIME_CELL = 96

# A single isotropic factor is shared by every frame in a strip.  Front guard
# art was already at the approved 48px scale.  Back-facing upright art is
# reduced to the approved 44px scale.  Low-profile and slash actions get room
# to recover their character scale while retaining their deliberately crouched
# poses and every original animation silhouette.
SCALE_FACTORS = {
    ("guard", "front_down"): Fraction(1, 1),
    ("guard", "back_up"): Fraction(11, 12),
    ("guard", "profile_right"): Fraction(8, 5),
    ("hurt", "front_down"): Fraction(7, 6),
    ("hurt", "back_up"): Fraction(11, 12),
    ("hurt", "profile_right"): Fraction(7, 6),
    # The regenerated front/back slash sheets already use the approved combat
    # scale inside their 64px source cells.  Keep them 1:1 in the 96px runtime
    # cells; enlarging them again would make Rian jump in size during attacks.
    ("slash", "front_down"): Fraction(1, 1),
    ("slash", "back_up"): Fraction(1, 1),
    ("slash", "profile_right"): Fraction(8, 5),
}


def animation_key(path: Path) -> tuple[str, str]:
    name = path.name
    animation = (
        "guard" if "guard_walk" in name else
        "hurt" if "hurt_recoil" in name else
        "slash" if "sword_basic" in name else ""
    )
    direction = next(
        direction for direction in ("front_down", "back_up", "profile_right")
        if direction in name
    )
    if not animation:
        raise ValueError(f"Not a scalable Rian action strip: {path.name}")
    return animation, direction


def scaled_size(size: int, factor: Fraction) -> int:
    """Round a rational scale deterministically without floating-point drift."""
    return max(1, (size * factor.numerator + factor.denominator // 2)
               // factor.denominator)


def normalize_frame(frame: Image.Image, factor: Fraction) -> Image.Image:
    bounds = frame.getbbox()
    if bounds is None:
        raise ValueError("Rian action frame is empty")
    sprite = frame.crop(bounds)
    width = scaled_size(sprite.width, factor)
    height = scaled_size(sprite.height, factor)
    if width > RUNTIME_CELL or height > RUNTIME_CELL:
        raise ValueError(
            f"Scaled Rian frame {width}x{height} exceeds {RUNTIME_CELL}px cell"
        )
    sprite = sprite.resize((width, height), Image.Resampling.NEAREST)

    # Preserve the source frame's lateral choreography around its original
    # 32px center, scaled into the 48px runtime center.  Only a final integer
    # translation is allowed if an edge would otherwise leave the actor cell.
    source_center_x = (bounds[0] + bounds[2]) / 2
    target_center_x = RUNTIME_CELL / 2 + (source_center_x - SOURCE_CELL / 2) * float(factor)
    left = round(target_center_x - width / 2)
    left = min(max(0, left), RUNTIME_CELL - width)
    top = RUNTIME_CELL - height

    output = Image.new("RGBA", (RUNTIME_CELL, RUNTIME_CELL), (0, 0, 0, 0))
    output.alpha_composite(sprite, (left, top))
    return output


def normalize_strip(source_path: Path, output_path: Path) -> None:
    source = Image.open(source_path).convert("RGBA")
    if source.height != SOURCE_CELL or source.width % SOURCE_CELL:
        raise ValueError(f"Unexpected archived strip size: {source.size}")
    factor = SCALE_FACTORS[animation_key(source_path)]
    frames = [
        normalize_frame(source.crop((x, 0, x + SOURCE_CELL, SOURCE_CELL)), factor)
        for x in range(0, source.width, SOURCE_CELL)
    ]
    output = Image.new(
        "RGBA", (len(frames) * RUNTIME_CELL, RUNTIME_CELL), (0, 0, 0, 0)
    )
    for index, frame in enumerate(frames):
        output.alpha_composite(frame, (index * RUNTIME_CELL, 0))
    output.save(output_path, optimize=True)


def copy_fainted(source_path: Path, output_path: Path) -> None:
    image = Image.open(source_path).convert("RGBA")
    if image.size != (SOURCE_CELL, SOURCE_CELL):
        raise ValueError(f"Unexpected fainted frame size: {image.size}")
    image.save(output_path, optimize=True)


def main() -> None:
    required = sorted(SOURCE_DIR.glob("rian_*.png"))
    if len(required) != 15:
        raise SystemExit(f"Expected 15 archived Rian strips in {SOURCE_DIR}")

    for source_path in required:
        output_path = BATTLE_DIR / source_path.name
        if "battle_idle" in source_path.name:
            replace_idle_strip(output_path)
            print(f"{output_path.relative_to(ROOT)}: exact approved idle")
        elif "fainted" in source_path.name:
            copy_fainted(source_path, output_path)
            print(f"{output_path.relative_to(ROOT)}: restored unique prone pose")
        else:
            normalize_strip(source_path, output_path)
            animation, direction = animation_key(source_path)
            factor = SCALE_FACTORS[(animation, direction)]
            print(
                f"{output_path.relative_to(ROOT)}: restored unique frames at "
                f"{factor.numerator}/{factor.denominator} uniform scale"
            )


if __name__ == "__main__":
    main()
