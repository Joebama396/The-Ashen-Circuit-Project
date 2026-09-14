# Approved Directional Stances

These PNGs are the lossless authored sources for the current party animation
and battle-ready atlases. `tools/build_authored_stance_atlases.py` packs them
into native 96x96 runtime cells without resizing their pixels.

## Walk sheets

- One 256x64 strip per character and authored direction.
- Four 64x64 frames in order: idle, first stride, idle, opposite stride.
- `down`, `up`, and `right` are authored; `left` is mirrored from `right`.
- Runtime frames repeat the approved four-frame cycle twice to satisfy the
  existing eight-frame animation contract.

## Battle-ready sheets

- One 192x80 sheet per character.
- Three 64x80 cells in order: front/down, back/up, profile left.
- Profile right is mirrored from profile left at build time.

## Runtime outputs

- `party_overworld_hd_v2.png`: 3072x384, four character rows, directions in
  `down`, `left`, `right`, `up` order, eight 96x96 cells per direction.
- `party_battle_ready_hd_v1.png`: 384x384, four character rows, directions in
  `down`, `left`, `right`, `up` order, one 96x96 cell per direction.
- Every visible foot is aligned to the shared `(48, 88)` ground anchor.
