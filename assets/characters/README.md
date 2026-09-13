# Character Sprite Kit

The seamless-combat build uses `party_overworld_v4.png` for both exploration and
combat. The old battle sheet and high-detail references remain available for
art editing; the approved character pixels have not been redrawn for this update.

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
- Gameplay scale: Rian 105%, Marek 100%, Tess 98%, Brann 110%
- Every character is isolated before packing, so no weapon, cape, or limb crosses into a neighboring cell

These are the higher-detail side-view combat poses from the previous battle
layout. They are retained as references and are not loaded by the current game.

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
