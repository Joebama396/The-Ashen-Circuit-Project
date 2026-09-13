# Character Sprite Kit

The seamless-combat build swaps between `party_motion_v1.png` for exploration
and the two `party_combat_*_v1.png` layer atlases for battle. All runtime party
frames are drawn at 1:1 native-canvas scale.

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

This is the authored source for the runtime combat layer atlases. It is processed
offline and is not resized by the running game.

## `party_combat_bodies_v2.png` and `party_combat_arms_v2.png`

- Runtime frame: 64×64 transparent pixels
- Body atlas: four fixed torso/body frames
- Arm atlas: separate rear/front rows and one column per named state
- Shared ground anchor: `(32, 58)` in every frame
- Rendering: direct 1:1 source-rectangle blits only

`tools/build_combat_layers.py` regenerates both atlases from the authored battle
sheet using the locked blueprints in `combat_poses.py`.

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
