# The Ashen Circuit

An original, self-contained 16-bit-style turn-based RPG dungeon for Linux.

## Seamless room combat

Exploration and combat now use the same room, camera, scale, and directional
character sprites. Enemies visibly patrol the dungeon. Touch a patrol to engage:
the party runs to spread-out positions around those enemies, and a compact
command HUD appears without a battle-screen transition.

Sword/dagger users approach their targets and return after striking. Marek fires
a projectile rail-pistol; Brann lobs arcing grenades. Healing, status effects,
combined Link attacks, and enemy turns animate in place. Movement in battle is
command-driven, not free-running action combat. Single-target offensive commands
open a visible target picker: D-pad/arrows cycle, A/Z confirms, B/X cancels.

Defeated patrols disappear until you leave and re-enter the room; saving/loading
in that room preserves the cleared patrol. Repair Drones always drop a Potion,
so supply farming remains available. Bosses do not respawn. Vael and the dragon
are visible before contact; the facility-firing scene precedes the dragon fight.

Current character scales remain Rian 105%, Marek 100%, Tess 98%, Brann 110%.
The overworld PNG itself is unchanged. Old side-view poses remain in the art kit
as reference material, but are no longer used by the playable build.

## Controls

- Arrow keys / D-pad: move or select
- Z / Enter / controller A: confirm, interact, advance dialogue
- X / Escape / controller B: cancel or open the field menu
- F11: toggle fullscreen
- F5: quick-save outside battle

Xbox controller: left stick/D-pad moves and navigates, A confirms, B cancels,
and Start opens the field menu.

## Party

- Rian — Frostguard: sword, ice attacks, defensive/attack buffs, and a slightly larger frame
- Marek — Arc Medic: projectile rail-pistol attacks, lightning, healing, and revival
- Tess — Venomist: bio daggers, poison, powerful debuffs, and a deliberately smaller frame
- Brann — Bombardier: fire, non-elemental grenade damage, and the party's largest frame

Personal commands recharge independently. When every required participant has
a full charge, the Link menu enables combined dual, triple, or four-person
techniques. More combinations unlock as the party disables relays and defeats
the midpoint boss.

The game auto-saves on room transitions and after major encounters. Save data is stored in `~/.local/share/ashen-circuit/save.json`.
Existing saves are supported; the new encounter state is optional in old saves.

## Objective

The resistance party must cross the occupied Caelus Engine, disable three restoration relays, defeat the enemy commander at the midpoint, and stop the ancient dragon weapon Vharos from awakening. The central complex opens after a guided introduction and can be explored in several orders. Brass access keys are deliberately scarce: choose which shortcuts to unlock.

## Sprite regeneration and build

The combined art references should first be split by connected silhouette rather
than by equal-width columns. Run `python3 tools/extract_direction_sprites.py` and
`python3 tools/extract_battle_sprites.py` after changing a high-resolution
reference. Then run `python3 tools/build_character_sheets_v2.py` followed by
`./build.sh`. The build creates `dist/The_Ashen_Circuit-x86_64.AppImage`.

For this combat update, the source backup and previous playable build are in
`checkpoints/`. Builds preserve other downloads in `dist/`.

## Verification and previews

Run `PYTHONPATH=./vendor python3 -m unittest discover -s tests -v` for the
seamless-combat regression suite. Tests use temporary saves and dummy SDL devices.
They cover shared room rendering, contact triggers, all rooms/exits, targeting,
animation timing, Arts/Links, sequential enemy turns, farming, saves, and bosses.
The built AppImage also accepts `--smoke-test` to verify the packaged sprites,
contact, formation, targeting, attack resolution, and HUD without reading or
writing a save. For a headless test set `SDL_VIDEODRIVER=dummy` and
`SDL_AUDIODRIVER=dummy` before launching it.

Run `PYTHONPATH=./vendor python3 tools/preview_seamless.py --video` to capture
actual PNG gameplay frames and a short MP4 demonstration (`ffmpeg` is required
only for the optional video). The preview does not modify a player's save.

Full-playthrough pacing toward the requested 90-minute target has not been
verified. Enemy artwork is still a simple code-drawn baseline, independent of
the approved character sprite artwork.
