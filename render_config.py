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

# Grid-derived feet anchors shared by patrol placement and combat formation.
GRID_X=tuple(range(HALF_GRID,VIEW_W, WORLD_GRID))
GRID_Y=(WORLD_GRID*2,WORLD_GRID*3,WORLD_GRID*4)
# Combatants may use half-cell tactical lanes while collisions, doors, chests,
# and map construction remain on the 64-pixel grid.
FORMATION_X=tuple(range(HALF_GRID,VIEW_W,HALF_GRID))
FORMATION_Y=GRID_Y

# A full 64x80 character remains inside the room at every valid foot point.
WALK_BOUNDS=(HALF_GRID,VIEW_W-HALF_GRID,WORLD_GRID*2-16,VIEW_H-HALF_GRID)
