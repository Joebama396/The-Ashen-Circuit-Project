"""Locked, 1:1 sprite-sheet combat rendering.

The checked-in combat atlases are generated from the authored character art by
``tools/build_combat_layers.py``. Runtime code only selects transparent source
rectangles and blits rear arm -> fixed body -> front arm -> weapon. It never paints a
weapon, rotates a limb, or rescales a character during play.
"""
from dataclasses import dataclass

import pygame
from render_config import (ACTOR_CELL_H, ACTOR_CELL_W, ACTOR_GROUND_ANCHOR,
                           SOURCE_CHARACTER_H, SOURCE_CHARACTER_W,
                           SOURCE_IN_ACTOR_CELL)


COMBAT_CELL_W=ACTOR_CELL_W
COMBAT_CELL_H=ACTOR_CELL_H
COMBAT_GROUND_ANCHOR=ACTOR_GROUND_ANCHOR
ARM_LAYERS=('rear','front','weapon')

# Source-layout constants are consumed by the offline atlas builder. They stay
# here beside the state map so pose coordinates cannot silently drift apart.
SOURCE_CELL_W=SOURCE_CHARACTER_W
SOURCE_CELL_H=SOURCE_CHARACTER_H
SOURCE_ARM_CELL_W=96
SOURCE_ARM_CELL_H=96
SOURCE_ARM_OFFSET=(16,8)
SOURCE_ARM_ANCHOR=(48,86)
BODY_CELL_OFFSET=SOURCE_IN_ACTOR_CELL
# No arm mask is permitted to consume these rows or anything below them. This
# protects every coat panel, hip and leg pixel from future stance edits.
BODY_PROTECTED_FROM_Y=(38,36,47,41)


@dataclass(frozen=True)
class CombatPoseProfile:
    name: str
    idle_state: str
    firing_state: str = ''
    recoil_state: str = ''
    jump_sequence: tuple = ()


@dataclass(frozen=True)
class LayerSlice:
    """Authored source regions and shoulder attachment in a 64x80 cell."""
    regions: tuple
    pivot: tuple


@dataclass(frozen=True)
class LayerTransform:
    """Official pose blueprint baked into a transparent atlas frame."""
    angle: float = 0.
    offset: tuple = (0,0)


RIAN_PROFILE=CombatPoseProfile(
    'swordsman','low_sword_ready',
    jump_sequence=('jump_start','overhead_raise','downward_landing_strike'))
MAREK_PROFILE=CombatPoseProfile(
    'pistol','high_ready','extended_isosceles','recoil')
TESS_PROFILE=CombatPoseProfile(
    'dual_daggers','split-arm',jump_sequence=RIAN_PROFILE.jump_sequence)
BRANN_PROFILE=CombatPoseProfile(
    'grenadier','low_ready','shouldered_firing','heavy_recoil')
HERO_COMBAT_PROFILES=(RIAN_PROFILE,MAREK_PROFILE,TESS_PROFILE,BRANN_PROFILE)


HERO_POSES={
    0:('low_sword_ready','jump_start','overhead_raise','downward_landing_strike'),
    1:('high_ready','extended_isosceles','recoil'),
    2:('split-arm','jump_start','overhead_raise','downward_landing_strike'),
    3:('low_ready','shouldered_firing','heavy_recoil'),
}


LOCKED_STANCE_BLUEPRINTS={
    'Rian':{'idle':'low_sword_ready','jump':RIAN_PROFILE.jump_sequence},
    'Merek':{'idle':'high_ready','fire':'extended_isosceles','recoil':'recoil'},
    'Tess':{'idle':'split-arm','legacy_alias':'split_arm_profile'},
    'Brann':{'idle':'low_ready','fire':'shouldered_firing','recoil':'heavy_recoil'},
}


# Polygons assign existing source pixels to layers; they are never rendered.
# The coordinates and pivots are part of the locked blueprint.
ARM_SLICES={
    0:{
        # Sword, gauntlets and sleeves only. The previous broad polygons reached
        # into the coat panels and forward leg, which made them appear to vanish
        # when the arm layer rotated during a jump attack.
        'rear':LayerSlice((((18,24),(25,23),(34,27),(36,32),(31,37),(24,36),(18,31)),),(34,29)),
        'front':LayerSlice((((0,8),(5,9),(22,24),(27,24),(31,28),(29,34),(23,34),(18,30),(13,27),(0,17)),),(29,29)),
        'weapon':LayerSlice((((0,8),(5,9),(25,25),(22,29),(16,27),(0,17)),),(29,29)),
    },
    1:{
        # Merek's head, collar and chest remain in the fixed 3/4 body. Only the
        # forearms/hands are articulated, around a shoulder point moved three
        # pixels rearward and down so high_ready grows out of his chest rather
        # than reading as a flat side-profile appendage.
        'rear':LayerSlice((((14,22),(22,21),(30,24),(33,29),(30,34),(22,34),(15,29)),),(34,30)),
        'front':LayerSlice((((10,18),(22,17),(30,21),(33,26),(31,32),(25,35),(18,31),(12,27)),),(34,28)),
        'weapon':LayerSlice((((0,11),(22,11),(24,14),(24,21),(21,24),(9,24),(0,22)),),(34,28)),
    },
    2:{
        # Each dagger arm is isolated without the purple cape or either leg.
        'rear':LayerSlice((((0,31),(10,28),(20,27),(27,29),(27,35),(20,38),(10,43),(0,43)),),(27,29)),
        'front':LayerSlice((((27,25),(34,24),(40,28),(47,31),(54,34),(63,37),(63,46),(57,46),(51,41),(44,38),(36,35),(29,33)),),(32,28)),
        'weapon':LayerSlice((
            ((0,37),(8,36),(13,40),(10,49),(5,53),(0,52)),
            ((45,39),(54,42),(63,47),(63,56),(57,55),(49,49))),
            (32,28)),
    },
    3:{
        # Trigger arm stays behind the chassis; the support hand, forearm and
        # complete launcher form the front layer. Nothing below the waist is
        # classified as an arm, preserving Brann's coat and both legs.
        'rear':LayerSlice((((27,23),(34,21),(43,24),(46,31),(41,38),(33,37),(27,31)),),(41,27)),
        'front':LayerSlice((
            ((13,24),(22,22),(31,27),(32,34),(25,40),(17,35)),
            ((29,22),(36,21),(42,26),(41,33),(36,36),(31,32))),
            (38,27)),
        # The launcher slice ends before Brann's x=31..43 head cluster. This
        # keeps every face pixel in the permanent body frame in both facings.
        'weapon':LayerSlice((((0,8),(30,8),(31,12),(30,19),(37,23),(40,26),(35,31),(23,29),(14,27),(0,27)),),(38,27)),
    },
}


def _t(rear=(0,(0,0)),front=(0,(0,0)),weapon=None):
    # Weapon and supporting hands share the front-arm attachment transform by
    # default, but occupy an independent atlas row/source rectangle.
    if weapon is None:weapon=front
    return {'rear':LayerTransform(*rear),'front':LayerTransform(*front),
            'weapon':LayerTransform(*weapon)}


POSE_BLUEPRINTS={
    0:{
        'low_sword_ready':_t(),
        'jump_start':_t((8,(0,2)),(8,(0,2))),
        'overhead_raise':_t((-38,(-1,-1)),(-42,(-1,-2))),
        'downward_landing_strike':_t((42,(1,2)),(48,(2,3))),
    },
    1:{
        'high_ready':_t((-66,(-3,2)),(-72,(-3,1))),
        'extended_isosceles':_t(),
        'recoil':_t((-18,(1,-1)),(-28,(2,-2))),
    },
    2:{
        'split-arm':_t(),
        'jump_start':_t((-8,(0,2)),(8,(0,2))),
        'overhead_raise':_t((-42,(0,-1)),(42,(0,-2))),
        'downward_landing_strike':_t((30,(1,2)),(-30,(2,2))),
    },
    3:{
        'low_ready':_t((20,(0,2)),(20,(0,3))),
        'shouldered_firing':_t(),
        'heavy_recoil':_t((-13,(2,-2)),(-18,(3,-3))),
    },
}


def normalized_pose(hero,state):
    if hero==2 and state=='split_arm_profile':state='split-arm'
    poses=HERO_POSES[hero]
    return state if state in poses else HERO_COMBAT_PROFILES[hero].idle_state


def arm_source_rect(hero,state,layer):
    """Return a distinct, true-size transparent arm-frame rectangle."""
    if layer not in ARM_LAYERS:raise ValueError(f'Unknown arm layer: {layer}')
    pose=normalized_pose(hero,state)
    column=HERO_POSES[hero].index(pose)
    row=hero*len(ARM_LAYERS)+ARM_LAYERS.index(layer)
    return pygame.Rect(column*COMBAT_CELL_W,row*COMBAT_CELL_H,
                       COMBAT_CELL_W,COMBAT_CELL_H)


def body_source_rect(hero):
    return pygame.Rect(hero*COMBAT_CELL_W,0,COMBAT_CELL_W,COMBAT_CELL_H)


class CombatSpriteRig:
    """Draw a modular character rig without altering any source pixels."""
    def __init__(self,body_sheet,arm_sheet):
        required_body=(4*COMBAT_CELL_W,COMBAT_CELL_H)
        required_arms=(max(map(len,HERO_POSES.values()))*COMBAT_CELL_W,
                       len(HERO_POSES)*len(ARM_LAYERS)*COMBAT_CELL_H)
        if body_sheet.get_size()!=required_body:
            raise ValueError(f'Combat body atlas must be {required_body}')
        if arm_sheet.get_size()!=required_arms:
            raise ValueError(f'Combat arm atlas must be {required_arms}')
        self.body_sheet=body_sheet
        self.arm_sheet=arm_sheet

    def body_rect(self,hero):
        return body_source_rect(hero)

    def arm_rect(self,hero,state,layer):
        return arm_source_rect(hero,state,layer)

    def _oriented(self,image,facing_right):
        # Mirroring is lossless: one atlas pixel remains one canvas pixel.
        return pygame.transform.flip(image,True,False) if facing_right else image

    def draw_arm(self,target,hero,state,layer,x,y,facing_right):
        image=self.arm_sheet.subsurface(self.arm_rect(hero,state,layer))
        image=self._oriented(image,facing_right)
        target.blit(image,(round(x-COMBAT_GROUND_ANCHOR[0]),
                           round(y-COMBAT_GROUND_ANCHOR[1])))

    def draw_body(self,target,hero,x,y,facing_right):
        image=self.body_sheet.subsurface(self.body_rect(hero))
        image=self._oriented(image,facing_right)
        target.blit(image,(round(x-COMBAT_GROUND_ANCHOR[0]),
                           round(y-COMBAT_GROUND_ANCHOR[1])))

    def draw(self,target,hero,state,x,y,facing_right):
        self.draw_arm(target,hero,state,'rear',x,y,facing_right)
        self.draw_body(target,hero,x,y,facing_right)
        self.draw_arm(target,hero,state,'front',x,y,facing_right)
        self.draw_arm(target,hero,state,'weapon',x,y,facing_right)
