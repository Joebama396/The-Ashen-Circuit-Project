#!/usr/bin/env python3
"""Split the combined battle reference by connected silhouette, not columns."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from build_character_sheets_v2 import transparency


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/characters'
SOURCE = ASSETS / 'party_battle_reference_v5.png'
NAMES = ('rian', 'marek', 'tess', 'brann')


def main():
    reference = transparency(Image.open(SOURCE))
    pixels = np.asarray(reference).copy()
    foreground = pixels[:, :, 3] > 0
    labels, count = ndimage.label(foreground, np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0

    # The four largest connected silhouettes are the four party members.
    main_labels = list(np.argsort(sizes)[-4:])
    main_labels.sort(key=lambda label: np.where(labels == label)[1].mean())
    centers = [np.where(labels == label)[1].mean() for label in main_labels]
    owner = {label: index for index, label in enumerate(main_labels)}

    # Preserve small detached details (for example Tess's poison droplets) by
    # assigning them to the nearest main silhouette on the horizontal axis.
    for label in range(1, count + 1):
        if label in owner or sizes[label] < 4:
            continue
        xs = np.where(labels == label)[1]
        owner[label] = min(range(4), key=lambda i: abs(centers[i] - xs.mean()))

    for index, name in enumerate(NAMES):
        keep = np.zeros(foreground.shape, dtype=bool)
        for label, target in owner.items():
            if target == index:
                keep |= labels == label
        isolated = pixels.copy()
        isolated[~keep] = 0
        image = Image.fromarray(isolated.astype('uint8'), 'RGBA')
        image = image.crop(image.getchannel('A').getbbox())
        path = ASSETS / f'{name}_battle_v6.png'
        temporary = path.with_name(path.stem + '.writing.png')
        image.save(temporary)
        with Image.open(temporary) as check:
            check.load()
            if check.size != image.size or check.mode != 'RGBA':
                raise RuntimeError(f'PNG verification failed for {name}')
        temporary.replace(path)
        print(path)


if __name__ == '__main__':
    main()
