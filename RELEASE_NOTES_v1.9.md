# The Ashen Circuit v1.9

This release finalizes Rian's directional combat presentation and gives the
battlefield a calmer, more deliberate idle rhythm.

## New in v1.9

- Added the approved Front/Down, Back/Up, and Profile Right sword-slash
  sequences with consistent guards, visible hands, and directional poses.
- Added the approved Profile Right guarded movement cycle with Rian's sword
  held in a low rear guard.
- Rebuilt Rian's affected battle sheets as true transparent RGBA assets with
  consistent ground alignment and combat scale.
- Replaced constant battlefield pacing with short movements separated by
  three-to-five-second stationary pauses.
- Slowed Rian's guarded movement animation from roughly 13 FPS to roughly
  7 FPS while preserving attack, hurt, and recoil timing.
- Fixed Rian's transition from moving guard back to his held stationary guard.

## Notes

- Platform: Linux x86_64; packaged and tested through GitHub Actions on Ubuntu.
- Validation: all 136 automated tests and the packaged-game smoke test pass.
- Keyboard and Xbox-compatible controller input remain supported.
- Includes the v1.8 directional battle animations, defeat screen, and supplied
  Game Over music.
