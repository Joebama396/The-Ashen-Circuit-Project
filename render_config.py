"""Native pixel geometry shared by exploration and seamless combat.

The room is still a compact placeholder map, but every actor now lives on one
64-pixel world grid.  Character atlases use 96x96 transparent cells so a
64x80 source sprite can carry an extended weapon without clipping.  No runtime
character rendering code is allowed to resize either kind of cell.
"""

VIEW_W=640
VIEW_H=360
DISPLAY_SCALE=2
UI_W=320
UI_H=180
WORLD_GRID=64
HALF_GRID=WORLD_GRID//2

ACTOR_CELL_W=96
ACTOR_CELL_H=96
ACTOR_GROUND_ANCHOR=(48,88)
SOURCE_CHARACTER_W=64
SOURCE_CHARACTER_H=80
SOURCE_IN_ACTOR_CELL=(16,10)

# Offline-only nearest-neighbour shrink ratios for battle artwork. Each ratio
# maps the tallest authored battle silhouette to the tallest visible overworld
# silhouette for that hero (Rian, Merek, Tess, Brann). The generated atlases
# keep their 96x96 cells and the runtime still blits every pixel at 1:1.
BATTLE_SPRITE_SCALE_RATIOS=((47,71),(46,78),(47,65),(47,78))

# Grid-derived feet anchors shared by patrol placement and combat formation.
GRID_X=tuple(range(HALF_GRID,VIEW_W, WORLD_GRID))
GRID_Y=(WORLD_GRID*2,WORLD_GRID*3,WORLD_GRID*4)
# Combatants may use half-cell tactical lanes while collisions, doors, chests,
# and map construction remain on the 64-pixel grid.
FORMATION_X=tuple(range(HALF_GRID,VIEW_W,HALF_GRID))
FORMATION_Y=GRID_Y

# The top door's foot trigger is the third half-grid line (y=96).  Keeping the
# walking boundary on that line lets the party actually enter north exits while
# the 96x96 actor cell and its visible authored pixels remain on-screen.
WALK_BOUNDS=(HALF_GRID,VIEW_W-HALF_GRID,WORLD_GRID+HALF_GRID,
             VIEW_H-HALF_GRID)
