"""Cross-platform, ordered Pygame application shutdown."""

import sys

import pygame


def _safe_call(function, *args, **kwargs):
    """Keep teardown moving if one optional subsystem is already unavailable."""
    try:
        return function(*args, **kwargs)
    except Exception:
        return None


def graceful_exit(exit_code=0, fade_ms=350):
    """Fade active audio, uninitialize Pygame, and terminate the process.

    The explicit subsystem order matters on desktop builds: audio finishes
    first, controller handles are released next, the mixer device is closed,
    and finally Pygame tears down its display and remaining modules.
    """
    fade_ms = max(0, int(fade_ms))
    mixer_ready = bool(_safe_call(pygame.mixer.get_init))
    music_busy = bool(_safe_call(pygame.mixer.music.get_busy)) if mixer_ready else False
    channels_busy = bool(_safe_call(pygame.mixer.get_busy)) if mixer_ready else False

    if mixer_ready and (music_busy or channels_busy):
        if music_busy:
            _safe_call(pygame.mixer.music.fadeout, fade_ms)
        if channels_busy:
            _safe_call(pygame.mixer.fadeout, fade_ms)
        if fade_ms:
            _safe_call(pygame.time.wait, fade_ms)

    if mixer_ready:
        _safe_call(pygame.mixer.music.stop)
        _safe_call(pygame.mixer.stop)

    _safe_call(pygame.joystick.quit)
    _safe_call(pygame.mixer.quit)
    _safe_call(pygame.quit)
    sys.exit(exit_code)
