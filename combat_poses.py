"""Sprite-sheet driven combat rigs.

Combat poses are assembled from pixels already present in
``party_battle_v6.png``. The source pose is partitioned into a fixed body, a
rear arm and a front arm/weapon layer. Pose changes transform only the two arm
layers around their shoulder pivots; no procedural rectangles or lines are
painted over the torso.
"""
from dataclasses import dataclass

import pygame


SOURCE_CELL_W=64
SOURCE_CELL_H=80
BODY_CELL_W=64
BODY_CELL_H=80
ARM_CELL_W=96
ARM_CELL_H=96
ARM_SOURCE_OFFSET=(16,8)
ARM_CENTER=(ARM_SOURCE_OFFSET[0]+SOURCE_CELL_W//2,
            ARM_SOURCE_OFFSET[1]+SOURCE_CELL_H-2)
ARM_LAYERS=('rear','front')


@dataclass(frozen=True)
class CombatPoseProfile:
    name: str
    idle_state: str
    firing_state: str = ''
    recoil_state: str = ''
    jump_sequence: tuple = ()


@dataclass(frozen=True)
class LayerSlice:
    """Regions and shoulder pivot in one 64x80 battle-sheet cell."""
    regions: tuple
    pivot: tuple


@dataclass(frozen=True)
class LayerTransform:
    angle: float = 0.
    offset: tuple = (0,0)


RIAN_PROFILE=CombatPoseProfile(
    'swordsman','low_sword_ready',jump_sequence=('jump_start','overhead_raise','downward_landing_strike'))
MAREK_PROFILE=CombatPoseProfile(
    'pistol','high_ready','extended_isosceles','recoil')
TESS_PROFILE=CombatPoseProfile(
    'dual_daggers','split_arm_profile',jump_sequence=RIAN_PROFILE.jump_sequence)
BRANN_PROFILE=CombatPoseProfile(
    'grenadier','low_ready','shouldered_firing','heavy_recoil')
HERO_COMBAT_PROFILES=(RIAN_PROFILE,MAREK_PROFILE,TESS_PROFILE,BRANN_PROFILE)


HERO_POSES={
    0:('low_sword_ready','jump_start','overhead_raise','downward_landing_strike'),
    1:('high_ready','extended_isosceles','recoil'),
    2:('split_arm_profile','jump_start','overhead_raise','downward_landing_strike'),
    3:('low_ready','shouldered_firing','heavy_recoil'),
}


# These polygons are source-coordinate ownership maps, not rendered geometry.
# Every visible arm/weapon pixel is copied from the battle sheet. A small
# shoulder overlap is deliberate so rotations remain joined to the torso.
ARM_SLICES={
    0:{
        'rear':LayerSlice((((14,27),(25,24),(36,28),(38,35),(31,42),(18,39),(11,33)),),(34,30)),
        'front':LayerSlice((((0,5),(7,6),(31,29),(46,28),(49,35),(36,43),(26,39)),),(38,31)),
    },
    1:{
        'rear':LayerSlice((((14,31),(24,27),(34,31),(35,38),(28,46),(17,43)),),(30,31)),
        'front':LayerSlice((((0,27),(18,27),(31,30),(36,36),(31,44),(18,41),(0,36)),),(31,31)),
    },
    2:{
        'rear':LayerSlice((((0,31),(13,27),(24,25),(30,31),(26,43),(12,45),(0,42)),),(25,29)),
        'front':LayerSlice((((25,22),(39,20),(63,36),(63,48),(49,46),(34,39),(25,33)),),(32,29)),
    },
    3:{
        'rear':LayerSlice((((19,30),(29,26),(43,28),(45,39),(36,45),(23,42)),),(37,30)),
        'front':LayerSlice((((0,22),(34,22),(42,28),(42,39),(36,53),(23,54),(14,45),(16,35),(0,36)),),(38,30)),
    },
}


def _t(rear=(0,(0,0)),front=(0,(0,0))):
    return {'rear':LayerTransform(*rear),'front':LayerTransform(*front)}


# Transforms are intentionally restrained. They articulate existing painted
# sleeves/weapons around their shoulders instead of replacing them with blocks.
POSE_TRANSFORMS={
    0:{
        'low_sword_ready':_t(),
        'jump_start':_t((8,(0,2)),(8,(0,2))),
        'overhead_raise':_t((-38,(-1,-1)),(-42,(-1,-2))),
        'downward_landing_strike':_t((42,(1,2)),(48,(2,3))),
    },
    1:{
        'high_ready':_t((-58,(1,-1)),(-66,(1,-2))),
        'extended_isosceles':_t(),
        'recoil':_t((-18,(1,-1)),(-28,(2,-2))),
    },
    2:{
        'split_arm_profile':_t(),
        'jump_start':_t((-8,(0,2)),(8,(0,2))),
        'overhead_raise':_t((-42,(0,-1)),(42,(0,-2))),
        'downward_landing_strike':_t((30,(1,2)),(-30,(2,2))),
    },
    3:{
        'low_ready':_t((17,(0,2)),(17,(0,2))),
        'shouldered_firing':_t(),
        'heavy_recoil':_t((-13,(2,-2)),(-18,(3,-3))),
    },
}


def normalized_pose(hero,state):
    poses=HERO_POSES[hero]
    return state if state in poses else HERO_COMBAT_PROFILES[hero].idle_state


def arm_source_rect(hero,state,layer):
    """Return one independent arm layer's atlas rect."""
    if layer not in ARM_LAYERS:raise ValueError(f'Unknown arm layer: {layer}')
    pose=normalized_pose(hero,state)
    column=HERO_POSES[hero].index(pose)
    row=hero*2+ARM_LAYERS.index(layer)
    return pygame.Rect(column*ARM_CELL_W,row*ARM_CELL_H,ARM_CELL_W,ARM_CELL_H)


def body_source_rect(hero):
    return pygame.Rect(hero*BODY_CELL_W,0,BODY_CELL_W,BODY_CELL_H)


def _inside_polygon(point,polygon):
    """Integer ray-cast used only to assign source pixels to rig layers."""
    x,y=point;inside=False
    j=len(polygon)-1
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[j]
        if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
        j=i
    return inside


def _belongs(hero,layer,x,y):
    return any(_inside_polygon((x+.5,y+.5),polygon)
               for polygon in ARM_SLICES[hero][layer].regions)


def slice_arm_layer(battle_sheet,hero,layer):
    """Copy a textured arm layer directly from sprite-sheet coordinates."""
    if layer not in ARM_LAYERS:raise ValueError(f'Unknown arm layer: {layer}')
    source=battle_sheet.subsurface(
        pygame.Rect(hero*SOURCE_CELL_W,0,SOURCE_CELL_W,SOURCE_CELL_H))
    result=pygame.Surface((SOURCE_CELL_W,SOURCE_CELL_H),pygame.SRCALPHA)
    # Front owns overlaps. This prevents a shared hand pixel from ghosting
    # when the two independently transformed layers diverge.
    for y in range(SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            if source.get_at((x,y)).a==0:continue
            front=_belongs(hero,'front',x,y)
            rear=_belongs(hero,'rear',x,y) and not front
            if (layer=='front' and front) or (layer=='rear' and rear):
                result.set_at((x,y),source.get_at((x,y)))
    return result


def _rotated_at(source,pivot,transform):
    """Rotate a source-pixel limb while keeping its shoulder attached."""
    bounds=source.get_bounding_rect()
    if not bounds.width:return pygame.Surface((ARM_CELL_W,ARM_CELL_H),pygame.SRCALPHA)
    crop=source.subsurface(bounds).copy()
    rotated=pygame.transform.rotate(crop,transform.angle)
    crop_center=pygame.Vector2(bounds.width/2,bounds.height/2)
    old_pivot=pygame.Vector2(pivot)-pygame.Vector2(bounds.topleft)
    pivot_from_center=(old_pivot-crop_center).rotate(-transform.angle)
    rotated_pivot=pygame.Vector2(rotated.get_width()/2,rotated.get_height()/2)+pivot_from_center
    target=(pygame.Vector2(ARM_SOURCE_OFFSET)+pygame.Vector2(pivot)+
            pygame.Vector2(transform.offset))
    top_left=target-rotated_pivot
    cell=pygame.Surface((ARM_CELL_W,ARM_CELL_H),pygame.SRCALPHA)
    cell.blit(rotated,(round(top_left.x),round(top_left.y)))
    return cell


def build_arm_atlas(battle_sheet):
    """Slice, articulate, and cache every named arm pose from source pixels."""
    columns=max(len(poses) for poses in HERO_POSES.values())
    atlas=pygame.Surface((columns*ARM_CELL_W,8*ARM_CELL_H),pygame.SRCALPHA)
    for hero,poses in HERO_POSES.items():
        layers={layer:slice_arm_layer(battle_sheet,hero,layer) for layer in ARM_LAYERS}
        for column,state in enumerate(poses):
            for layer in ARM_LAYERS:
                spec=ARM_SLICES[hero][layer]
                cell=_rotated_at(layers[layer],spec.pivot,POSE_TRANSFORMS[hero][state][layer])
                row=hero*2+ARM_LAYERS.index(layer)
                atlas.blit(cell,(column*ARM_CELL_W,row*ARM_CELL_H))
    return atlas


def build_combat_body_atlas(battle_sheet,motion_sheet):
    """Build fixed torsos after assigning source arm pixels to their layers.

    A small matching motion-sheet underlay fills the torso hidden behind the
    source arms. It is never translated when the pose changes.
    """
    atlas=pygame.Surface((4*BODY_CELL_W,BODY_CELL_H),pygame.SRCALPHA)
    for hero in range(4):
        source=battle_sheet.subsurface(
            pygame.Rect(hero*SOURCE_CELL_W,0,SOURCE_CELL_W,SOURCE_CELL_H))
        body=pygame.Surface((BODY_CELL_W,BODY_CELL_H),pygame.SRCALPHA)
        for y in range(SOURCE_CELL_H):
            for x in range(SOURCE_CELL_W):
                color=source.get_at((x,y))
                if color.a and not _belongs(hero,'front',x,y) and not _belongs(hero,'rear',x,y):
                    body.set_at((x,y),color)

        # Left-facing frame zero matches the battle sheet's source direction.
        under=motion_sheet.subsurface(pygame.Rect(8*32,hero*48,32,48)).copy()
        under=pygame.transform.scale(under,(43,65))
        under_pos=(10,13)
        for uy in range(under.get_height()):
            for ux in range(under.get_width()):
                x,y=under_pos[0]+ux,under_pos[1]+uy
                if 16<=x<=49 and 15<=y<=62 and body.get_at((x,y)).a==0:
                    color=under.get_at((ux,uy))
                    if color.a:body.set_at((x,y),color)
        atlas.blit(body,(hero*BODY_CELL_W,0))
    return atlas


class CombatSpriteRig:
    """Owns sprite slicing, pose lookup, and ordered rig rendering."""
    def __init__(self,motion_sheet,battle_sheet):
        self.arm_sheet=build_arm_atlas(battle_sheet)
        self.body_sheet=build_combat_body_atlas(battle_sheet,motion_sheet)

    def body_rect(self,hero):
        return body_source_rect(hero)

    def arm_rect(self,hero,state,layer):
        return arm_source_rect(hero,state,layer)

    def _oriented(self,image,facing_right):
        # The authored battle sheet faces left.
        return pygame.transform.flip(image,True,False) if facing_right else image

    def draw_arm(self,target,hero,state,layer,x,y,scale,facing_right):
        image=self.arm_sheet.subsurface(self.arm_rect(hero,state,layer))
        image=self._oriented(image,facing_right)
        if scale!=1:
            image=pygame.transform.scale(
                image,(round(ARM_CELL_W*scale),round(ARM_CELL_H*scale)))
        target.blit(image,(round(x-ARM_CENTER[0]*scale),round(y-ARM_CENTER[1]*scale)))

    def draw_body(self,target,hero,x,y,scale,facing_right):
        image=self.body_sheet.subsurface(self.body_rect(hero))
        image=self._oriented(image,facing_right)
        if scale!=1:
            image=pygame.transform.scale(
                image,(round(BODY_CELL_W*scale),round(BODY_CELL_H*scale)))
        target.blit(image,(round(x-image.get_width()/2),round(y-(BODY_CELL_H-2)*scale)))

    def draw(self,target,hero,state,x,y,scale,facing_right):
        self.draw_arm(target,hero,state,'rear',x,y,scale,facing_right)
        self.draw_body(target,hero,x,y,scale,facing_right)
        self.draw_arm(target,hero,state,'front',x,y,scale,facing_right)
