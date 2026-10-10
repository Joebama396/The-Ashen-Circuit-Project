"""Shared, failure-safe user-interface sound effects."""

from pathlib import Path

import pygame


class UISfx:
    """Load and play the three authored UI sounds through one volume control."""

    def __init__(self, paths, volume=0.8):
        self.sounds = {}
        for name, raw_path in paths.items():
            path = Path(raw_path)
            if not path.is_file():
                continue
            try:
                self.sounds[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                pass
        self.set_volume(volume)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, float(volume)))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is None:
            return False
        try:
            sound.play()
        except pygame.error:
            return False
        return True
