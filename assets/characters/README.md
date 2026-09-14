# Character Sprite Kit

The seamless-combat build swaps between `party_overworld_hd_v2.png` for
exploration, `party_battle_ready_hd_v1.png` for directional battle idle poses,
and the two `party_combat_*_hd_v1.png` layer atlases for attack states. All
runtime party frames are drawn at 1:1 native-world-canvas scale.

## `party_overworld_v4.png`

- Canvas: 512×192 pixels
- Frame: 32×48 pixels
- Rows: Rian, Marek, Tess, Brann
- Direction groups: down, left, right, up
- Four frames per direction: left step, idle, right step, idle/sway

This is the best sheet to repaint first. Preserve the canvas size and frame
positions so the game can load the edited sheet without code changes.

Every directional pose is isolated before packing, preventing a coat, weapon,
or limb from leaking into an adjacent animation frame.

## `party_battle_v6.png`

- Canvas: 256×80 pixels
- Four 64×80 transparent cells
- Order: Rian, Marek, Tess, Brann
- Dedicated left-facing three-quarter profiles: half of each face and one near eye remain visible
- Rian's shoulder-length frost-white/ice-blue hair gives her a distinct silhouette from Marek
- Every character is isolated before packing, so no weapon, cape, or limb crosses into a neighboring cell

This is the authored source for the runtime combat layer atlases. It is reduced
offline with nearest-neighbour sampling to match each hero's overworld height;
it is never resized by the running game.

## `party_combat_bodies_hd_v1.png` and `party_combat_arms_hd_v1.png`

- Runtime frame: 96×96 transparent pixels
- Authored character inside each frame: battle silhouette reduced to its
  corresponding overworld height
- Body atlas: four fixed torso/body frames
- Part atlas: separate rear-arm, front-arm/hand, and weapon rows, with one
  column per named state
- Shared ground anchor: `(48, 88)` in every frame
- Rendering: direct 1:1 source-rectangle blits only

`tools/build_combat_layers.py` regenerates both atlases from the authored battle
sheet using the locked blueprints in `combat_poses.py`. Before the intentional
final nearest-neighbour reduction, it never synthesizes or underpaints body
pixels. The packaged runtime never slices, masks, or scales the result.

Brann's face/head cluster is permanently excluded from every movable part
slice, so horizontal mirroring cannot hand those pixels to the launcher layer.
Merek's high-ready forearms and weapon use a rearward, lowered 3/4 shoulder
pivot while his head, collar, and chest stay in the fixed body frame.

## `party_overworld_hd_v2.png`

- Runtime frame: 96×96 transparent pixels
- Rows: Rian, Merek, Tess, Brann
- Direction groups: down, left, right, up
- Eight frames per direction, repeating the approved four-frame cycle twice
- Source cycle: idle, first stride, idle, opposite stride

`tools/build_authored_stance_atlases.py` packs the approved directional walk
strips from `stances/` without resizing any authored pixels.

## `party_battle_ready_hd_v1.png`

- Runtime frame: 96×96 transparent pixels
- Rows: Rian, Merek, Tess, Brann
- Direction columns: down, left, right, up
- Shared ground anchor: `(48, 88)`

These complete directional sprites are used for battle-ready idle states. The
decoupled combat body/arm atlases remain active for attacks, recoil, and jump
sequences. Both sets are baked at the same character scale as the corresponding
overworld sprites.

## `rian_animation_master.png`

- Source canvas: 1856x64 pixels
- Frame: 64x64 pixels
- Total: 29 frames in one horizontal row
- Order: overworld idle (4), overworld walk (4), battle idle (4), battle dash
  (4), sword basic (4), sword skill (4), hurt (3), defeated (2)
- Chroma key: solid `#ff00ff`

`tools/build_battle_animation_atlas.py` validates the exact source geometry,
removes the magenta key, and pads every frame into a transparent 96x96 runtime
cell at the shared `(48, 88)` ground anchor. It never resizes authored pixels.
The generated `rian_battle_animations_hd_v1.png` is optional until the final
master art is checked in; the existing modular battle rig remains the fallback.
Clip timing, loops, impact frames, recovery transitions, and interrupt priorities
are defined in `battle_animations.py`.

## `battle/` directional Rian animations

Rian's approved battle art is stored as native 64-pixel cells on `#ff00ff`:

- Stationary battle idle: four-frame source strips held on frame one.
- Guarded battle movement/dash: four frames per direction.
- Upward sword slash: four frames per direction.
- Hurt/recoil: three frames per direction.
- Fainted/defeated: one held frame per direction.

Every set provides `front_down`, `back_up`, and `profile_right`; left profile is
the lossless horizontal mirror of the right-facing source. The runtime removes
the magenta key while loading and never rescales the authored cells.

## `party_battle_reference_v5.png`

The full-resolution battle reference establishing costume, weapon, palette,
silhouette, and Rian's revised ice-colored hair. It is not displayed directly
during gameplay.

## `rian_directions_v2.png`

Rian's front, left, right, and rear reference views with the same shoulder-length
frost-white/ice-blue hairstyle used in battle.

## Individual battle silhouettes

`rian_battle_v6.png`, `marek_battle_v6.png`, `tess_battle_v6.png`, and
`brann_battle_v6.png` are complete, transparent source sprites. These are safer
to repaint than cutting characters out of the combined reference.

## Regeneration

`tools/build_character_sheets_v2.py` regenerates both game sheets from individually
isolated direction and battle silhouettes. `tools/extract_direction_sprites.py`
and `tools/extract_battle_sprites.py` reconstruct those clean sources from the
combined high-resolution references. Crop positions, cell sizes, animation
phases, and transparency cleanup are kept as readable code.

The sheets use transparency, so preserve the alpha channel when exporting.
