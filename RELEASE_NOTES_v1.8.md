# The Ashen Circuit v1.8

This release completes Rian's first directional battle-animation set and adds
the full defeat presentation.

## New in v1.8

- Added Rian's approved directional battle-idle, guarded movement/dash,
  upward sword slash, hurt/recoil, and fainted sprites.
- Added Front/Down, Back/Up, and Profile Right selection for every completed
  battle animation.
- Added a slow battlefield fade on party defeat while keeping playable
  characters visible above the darkness.
- Added the centered, fully opaque `You Died` title in exact `#8A0000` red.
- Added the supplied `Game Over` music, which begins when the party falls.
- Packaged the new directional sprites and defeat music in every Linux build.

## Notes

- Platform: Linux x86_64; packaged and tested through GitHub Actions on Ubuntu.
- Keyboard and Xbox-compatible controller input remain supported.
- After the fade completes, any key restores the active save slot or starts a
  new game when no save exists.
