# The Ashen Circuit

An original 16-bit-style dungeon RPG for Linux x86_64. Four characters infiltrate
an ancient magitek complex being restored by the Dominion. The dungeon contains
24 rooms, Commander Vael, and the dragon weapon Vharos. The facility fires before
the final dragon fight.

## Play on Ubuntu

Download and extract `The_Ashen_Circuit-1.3-Ubuntu.zip`. It already contains the
matching AppImage and launcher. Open a terminal in the extracted folder and run:

```sh
sh ./Play-The-Ashen-Circuit.sh
```

This launcher runs the AppImage without FUSE. It also records startup errors.
No Python installation, administrator permissions, or package installation is
needed. You can also mark the launcher executable and choose **Run as a program**
in your file manager, if that option is available.

The AppImage can be run directly without FUSE too:

```sh
chmod +x ./The_Ashen_Circuit-1.3-x86_64.AppImage
./The_Ashen_Circuit-1.3-x86_64.AppImage --appimage-extract-and-run
```

An alternative download, `The_Ashen_Circuit-1.3-Linux-Portable.tar.gz`, contains the
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

## Active seamless combat

Enemies patrol the dungeon visibly. Touch one and the same room enters combat:
the party runs to spread-out positions, then the active-time clocks begin. There
is no separate arena or camera cut. At contact, each party pawn switches from its
96x96 large exploration array to its native 96x96 layered combat array. Both
contain raw 64x80 character art without changing its pixel ratio. Every party member has a visible colored
ATB bar in the lower-right panel. A white outline and selection arrow mean that
character is ready for input. LB/RB switches between ready characters.

After forming up, each character visibly draws their designated weapon and enters
an animated, wide-footed combat stance. Sword and dagger attacks choose their
approach from the live distance to the target: a nearby enemy gets a grounded
rush, while a distant enemy triggers an arcing jump attack with a separate ground
shadow. Both arrive at the same real impact frame and end in a new arena position.

Time remains active during command and target selection. Enemies fill their own
gauges, choose targets, and attack without waiting for the player. Sword and
dagger users draw their weapons and close the distance; Marek braces and fires a
visible rail-pistol projectile; Brann shoulders his launcher and arcs grenades.
Actors run to impact positions, then take new positions instead of snapping back
to a fixed formation. The rest of the party and the enemies keep shifting around
the shared room between attacks.

The field menu includes an **Active / Wait** battle-mode setting. Active retains
continuous gauges. Wait freezes every party ATB, enemy ATB, and hidden personal
recharge while an Arts or Link submenu is open. Enemy animations no longer take
ownership of the player's command interface: open menus remain visible and
navigable, and a command confirmed during an enemy animation is queued to begin
as soon as that animation finishes.

Every party pawn exposes a named animation state and frame. The engine now uses
a 640x360 native world canvas and one 64-pixel map/collision grid in exploration
and combat. Tactical lanes may use half-cell offsets, but every door, chest,
blocker, patrol home, and formation candidate derives from that shared grid.

Exploration sets `moving_up`, `moving_down`, `moving_left`, or `moving_right`
while selecting eight-frame arrays from
`party_overworld_hd_v2.png`. Its 96x96 transparent cells contain the approved
four-frame walk cycles repeated once for the existing eight-frame timing
contract, with every character aligned to the shared ground anchor.

Combat idle states use the front, rear, and left/right profiles in
`party_battle_ready_hd_v1.png`. Attacks swap to
`party_combat_bodies_hd_v1.png` and `party_combat_arms_hd_v1.png`. Each 96x96
cell contains the authored 64x80 battle art at its original size plus
transparent weapon clearance. The body, rear arm, front arm/hand, and weapon
remain independent source rectangles for attacks. Every character frame is
blitted 1:1 with no runtime magnification or procedural weapon geometry.

`tools/build_combat_layers.py` is an offline authoring tool. It preserves the
64x80 battle-source resolution, bakes locked shoulder pivots, angles, offsets,
hand attachments, and weapon placement into the transparent attack atlases.
`tools/build_authored_stance_atlases.py` packs the approved walk
and battle-ready sheets. Neither tool runs while packaging or playing the game.

Rian idles in `low_sword_ready`; a long-range jump chains `jump_start` into
`overhead_raise` and `downward_landing_strike`. Marek idles in `high_ready`, fires
from `extended_isosceles`, then briefly enters `recoil`. Tess uses a persistent
`split-arm` while sharing Rian's jump-state logic. Brann has a separate
grenadier profile with `low_ready`, `shouldered_firing`, and `heavy_recoil`.

The lower HUD is one compact plate instead of two bulky windows. It keeps all four
HP, MP, and active-time rows visible while returning ten native pixels to the
battlefield. Battle messages and the ACTIVE indicator now float in small chips
over the room rather than occupying a full-width top banner.

The supplied `Battle Theme 1` is the only music track in this build. It begins at
enemy contact, loops for the duration of combat, and stops immediately when the
last enemy is defeated. The victory screen is intentionally silent until a
separate fanfare exists.

Normal patrols return when you leave and re-enter their rooms. Repair Drones
always drop a Potion, allowing supply farming. Bosses and treasure do not respawn.
Enemy strength increases by region to account for permanent character growth.

The former small walk cycles remain as source/reference art, but the runtime now
uses large temporary overworld frames so future high-detail directional walks
can be installed without another engine refactor. Exploration and combat share
one native pixel scale: one character-atlas pixel equals one 640x360 world-canvas
pixel. Only the finished canvas and the established UI overlay are integer-scaled
for the 1280x720 window. Enemy art remains a code-drawn baseline. All gameplay
screenshots are PNGs.

Dialogue, field prompts, combat messages, commands, HP/MP values, and ATB panels
now use a high-contrast 5x7 pixel alphabet on an integer-scaled 320x180 UI layer.
The field menu layout is intentionally unchanged in this pass.

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
| Speed | +1 / +3 / +5 | Faster visible ATB and hidden personal recharge |
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

Learned personal commands grey out while their separate hidden charge refills;
a gold pip at the end of a ready character's ATB bar shows that charge is full.
Spell commands require MP. A learned Link requires every participant alive with
a full visible ATB bar, and consumes all participating ATB bars. Dual, triple,
and four-person Links are obtained from chests, independently of story flags.

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
| Switch ready character (battle) | Q / E | LB / RB |
| New game at title | N | Y |
| Quick-save outside combat | F5 | Field menu: Save |
| Toggle fullscreen | F11 | — |

Single-target attacks open a target picker. Directional input cycles visible
enemies, A/Z confirms, and B/X cancels. Menus pause exploration and patrols.

## Files and saves

The AppImage contains code, Python, libraries, the supplied battle theme, and
sprite data.
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
controller inputs, active enemy clocks, distance-selected run/jump attacks,
battle-music lifecycle, finite treasure, stat effects, save migration, and bosses.

Run `python3 tools/preview_seamless.py --video` for staged gameplay PNGs and an
optional MP4. Run `python3 tools/preview_progression.py` for treasure and growth
menu PNGs. Run `python3 tools/preview_combat_poses.py` for the layered arm/weapon
stance PNGs. None of the preview tools touches a player's save.

Full-playthrough balance and the requested roughly 90-minute pacing remain
unverified. This is a playable prototype for testing the mechanics and art.
