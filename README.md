# The Ashen Circuit

An original 16-bit-style dungeon RPG for Linux x86_64. Four characters infiltrate
an ancient magitek complex being restored by the Dominion. The dungeon contains
24 rooms, Commander Vael, and the dragon weapon Vharos. The facility fires before
the final dragon fight.

## Play on Ubuntu

Download `The_Ashen_Circuit-1.1-x86_64.AppImage` and `Play-The-Ashen-Circuit.sh`
into the same folder. Open a terminal in that folder and run:

```sh
sh ./Play-The-Ashen-Circuit.sh
```

This launcher runs the AppImage without FUSE. It also records startup errors.
No Python installation, administrator permissions, or package installation is
needed. You can also mark the launcher executable and choose **Run as a program**
in your file manager, if that option is available.

The AppImage can be run directly without FUSE too:

```sh
chmod +x ./The_Ashen_Circuit-1.1-x86_64.AppImage
./The_Ashen_Circuit-1.1-x86_64.AppImage --appimage-extract-and-run
```

An alternative download, `The_Ashen_Circuit-1.1-Linux-Portable.tar.gz`, contains the
same game already unpacked. Extract it, open the `The-Ashen-Circuit` folder, and
run `AppRun` (or `sh ./AppRun` in a terminal). Keep its files together.

### Why the previous AppImage could fail

The previous build's normal startup was reproduced failing with
`dlopen(): error loading libfuse.so.2` before the game launched. Making it
executable does not supply this missing library. This is a likely cause of a
silent double-click failure; your machine's error output is needed to confirm.
The launcher and portable archive avoid FUSE entirely.

AppImage's official guide describes
[the extraction fallback and Ubuntu FUSE package names](https://docs.appimage.org/user-guide/troubleshooting/fuse.html).
The updated binaries are built/tested on Ubuntu 24.04 x86_64 without FUSE. A
physical Ubuntu 26.04 desktop has not been available for testing. If startup
still fails, share `~/.local/state/ashen-circuit/launcher.log` and
`~/.local/state/ashen-circuit/game.log` (if present).

## Seamless combat

Enemies patrol the dungeon visibly. Touch one and the same room enters combat:
the party runs to spread-out positions, then commands appear. There is no
separate arena, camera cut, or sprite swap. Sword and dagger attacks approach
the enemy; Marek fires a rail-pistol projectile; Brann lobs grenades. Allies and
enemies move during their attacks. Combat remains turn based: movement is
command-driven, rather than free movement while selecting commands.

Normal patrols return when you leave and re-enter their rooms. Repair Drones
always drop a Potion, allowing supply farming. Bosses and treasure do not respawn.
Enemy strength increases by region to account for permanent character growth.

The approved overworld character artwork is unchanged. Relative scales remain
Rian 105%, Marek 100%, Tess 98%, Brann 110%. Enemy art is still a simple code-drawn
baseline. All gameplay screenshots are PNGs.

## Treasure replaces leveling

There are **27 technique tomes, 73 visible chests, and 97 permanent stat items**.
No XP, character levels, stat gains from victories, or automatic story-based
technique unlocks. Victories award salvage and supplies.

Approach a chest and press A / Z. Cyan-trimmed chests hold tomes. Each tome
immediately teaches its designated character or unlocks a party Link. The four
safe entrance caches teach an initial technique to each character. All personal
commands, spells, and Links require their own tome; Attack, Defend, and ordinary
item use are available from the start.

Stat items stay in your inventory until assigned. Open **Items & Growth**,
select an item and a character, review the before-and-after values, then confirm.
B cancels without consuming the item. Supplies can also be used here between
battles. HP/MP upgrades increase both the maximum and current value by the bonus;
HP upgrades do not revive a fallen character.

| Attribute | Three tiers | Effect |
| --- | --- | --- |
| Strength | +1 / +3 / +5 | Physical damage |
| Magic | +1 / +3 / +5 | Spell damage and scaling heals |
| Defense | +1 / +3 / +5 | Reduces physical damage received |
| Resistance | +1 / +3 / +5 | Reduces magical damage received |
| Speed | +1 / +3 / +5 | Faster hidden personal/Link recharge |
| HP | +10 / +30 / +50 | Maximum health |
| MP | +3 / +8 / +15 | Maximum magic points |

Stronger regions contain stronger stat items. Every cache is finite, saved
immediately, and cannot be rerolled by re-entering the room. Potions and Ethers
are mixed into the chests; no scarce access key is needed to obtain any tome.

## Party and Links

- Rian, Frostguard: sword, ice, attack/defense buffs.
- Marek, Arc Medic: male army doctor, projectile rail-pistol, lightning, healing.
- Tess, Venomist: daggers, bio/poison, debuffs.
- Brann, Bombardier: launcher, fire/non-elemental damage.

Learned personal commands grey out while their hidden charge refills. Spell
commands require MP. A learned Link requires every participant alive and fully
charged, and consumes all participants' charges. Dual, triple, and four-person
Links are obtained from chests, independently of story flags.

Three relay keys serve five service locks. Unlocks are permanent. The route to
the relays, command bridge, and dragon remains accessible regardless of how you
spend them. The workshop is optional and requires opening one of its keyed
entrances. Gear can also be upgraded at the vault and after the midpoint boss.

## Controls

| Action | Keyboard | Xbox |
| --- | --- | --- |
| Move / select | Arrows or WASD | Left stick / D-pad |
| Confirm / interact | Z / Enter | A |
| Cancel / field menu | X / Escape | B / Start |
| New game at title | N | Y |
| Quick-save outside combat | F5 | Field menu: Save |
| Toggle fullscreen | F11 | — |

Single-target attacks open a target picker. Directional input cycles visible
enemies, A/Z confirms, and B/X cancels. Menus pause exploration and patrols.

## Files and saves

The AppImage contains code, Python, libraries, music generation, and sprite data.
It writes these files in your home folder:

- `~/.local/share/ashen-circuit/save.json`: progress, learned tomes, chest state,
  consumed stat items, upgraded stats, and encounters.
- `~/.local/share/ashen-circuit/save-before-tomes.json`: one-time backup when
  loading a save from an earlier build.
- `~/.local/state/ashen-circuit/`: launch logs.
- `~/.cache/ashen-circuit/runtime/`: temporary extraction files, normally removed
  when the game exits; the empty cache directory can remain.

Standard `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `XDG_CACHE_HOME` overrides are
respected. Old saves keep their location, story, equipment, and supplies. The
new chests start unopened and techniques must now be found in tomes. Saves are
written atomically. An unreadable save is reported rather than silently reset.

## Build and verification

Python 3.12 and the pinned dependencies in `requirements.txt` are used for the
build. The runtime only needs pygame; the other requirements support packaging
and the existing optional sprite tools.

```sh
python3 -m pip install -r requirements.txt
# Put appimagetool-x86_64.AppImage in the project root and make it executable.
./build.sh
python3 -m unittest discover -s tests -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy sh dist/Play-The-Ashen-Circuit.sh --smoke-test
```

If dependencies are installed in the local `vendor` folder, prepend
`PYTHONPATH=./vendor` to Python commands. Builds preserve other downloads in
`dist/`. The build produces an AppImage, a FUSE-bypass launcher, and an extracted
portable archive. Tests use temporary saves and SDL dummy devices. They cover
seamless rendering, contact, targeting, movement, all Arts/Links, every room,
controller inputs, finite treasure, stat effects, save migration, and bosses.

Run `python3 tools/preview_seamless.py --video` for staged gameplay PNGs and an
optional MP4. Run `python3 tools/preview_progression.py` for treasure and growth
menu PNGs. Neither preview touches a player's save.

Full-playthrough balance and the requested roughly 90-minute pacing remain
unverified. This is a playable prototype for testing the mechanics and art.
