#!/usr/bin/env python3
"""Split each four-direction reference into four clean character silhouettes."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from build_character_sheets_v2 import transparency


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/characters'
SOURCES = {
    'rian': ASSETS / 'rian_directions_v2.png',
    'marek': ASSETS / 'marek_directions.png',
    'tess': ASSETS / 'tess_directions.png',
    'brann': ASSETS / 'brann_directions.png',
}
DIRECTIONS = ('down', 'left', 'right', 'up')


def save_verified(image, path):
    temporary = path.with_name(path.stem + '.writing.png')
    image.save(temporary)
    with Image.open(temporary) as check:
        check.load()
        if check.size != image.size or check.mode != 'RGBA':
            raise RuntimeError(f'PNG verification failed for {path.name}')
    temporary.replace(path)


def main():
    for name, source in SOURCES.items():
        reference = transparency(Image.open(source))
        pixels = np.asarray(reference).copy()
        foreground = pixels[:, :, 3] > 0
        labels, _ = ndimage.label(foreground, np.ones((3, 3), dtype=np.uint8))
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        main_labels = list(np.argsort(sizes)[-4:])
        main_labels.sort(key=lambda label: np.where(labels == label)[1].mean())

        for direction, label in zip(DIRECTIONS, main_labels):
            isolated = pixels.copy()
            isolated[labels != label] = 0
            image = Image.fromarray(isolated.astype('uint8'), 'RGBA')
            image = image.crop(image.getchannel('A').getbbox())
            path = ASSETS / f'{name}_{direction}_v7.png'
            save_verified(image, path)
            print(path)


if __name__ == '__main__':
    main()
