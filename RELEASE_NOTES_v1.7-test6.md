# The Ashen Circuit v1.7-test6

A playable 16-bit-style dungeon RPG prototype for 64-bit Ubuntu/Linux.

This release brings the complete title-screen suite, three objective-based save
slots, persistent audio and battle settings, an interactive Bestiary, corrected
directional walk art, consistent overworld and battle sprite sizing, and the
supplied `Sleep Deprivation` title theme.

## Recommended download

Download `The_Ashen_Circuit-1.7-test6-Ubuntu.zip`, extract it, and follow
`START_HERE.txt`. The standalone AppImage now carries a static runtime and can
also be launched directly after marking it executable.

The extracted portable archive is included as another fallback.
`SHA256SUMS-1.7-test6.txt` verifies every download.

## Fixes in test6

- Restored reliable north-door activation.
- Prevented side-door machinery from trapping the party after arrivals or
  shortcut unlocks.
- Added automatic recovery for older saves already written inside collision
  geometry, including the Excavation Brig to Flooded Pumps shortcut.
- Audited all 46 directed room transitions and all five keyed shortcuts from
  both directions.
- Reduced every battle-ready and attack sprite to its corresponding overworld
  character height without changing designs or poses.
- Corrected Rian's left/right profile mapping.

## Notes

- Platform: Linux x86_64; packaged and tested on Ubuntu.
- Keyboard and Xbox-compatible controller input are supported.
- There is no XP or player-level system; save cards show location, current
  objective, and playtime.
- Save data remains outside the AppImage under the standard XDG data folder.
- The verified local build passes 112 automated tests and its packaged smoke
  test.
