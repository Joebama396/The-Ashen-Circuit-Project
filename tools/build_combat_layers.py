"""Bake locked combat poses into native-resolution transparent PNG atlases.

This is an asset-authoring tool, not runtime rendering. It may rotate source
arm pixels into the approved pose blueprints, then reduces every completed
layer with nearest-neighbour sampling to the matching overworld silhouette
height. The resulting 96x96 frames are checked in and always blitted 1:1 by
the game.
"""
import os
from pathlib import Path
import sys
import colorsys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pygame
from combat_poses import (ARM_LAYERS, ARM_SLICES, BODY_CELL_OFFSET,
    BODY_PROTECTED_FROM_Y,
    COMBAT_CELL_H, COMBAT_CELL_W, COMBAT_GROUND_ANCHOR, HERO_POSES,
    POSE_BLUEPRINTS, SOURCE_ARM_ANCHOR, SOURCE_ARM_CELL_H,
    SOURCE_ARM_CELL_W, SOURCE_ARM_OFFSET, SOURCE_CELL_H, SOURCE_CELL_W)
from render_config import BATTLE_SPRITE_SCALE_RATIOS


BODY_OUTPUT=ROOT/'assets/characters/party_combat_bodies_hd_v1.png'
ARM_OUTPUT=ROOT/'assets/characters/party_combat_arms_hd_v1.png'
OVERWORLD_OUTPUT=ROOT/'assets/characters/party_overworld_hd_placeholder_v1.png'


def _inside_polygon(point,polygon):
    x,y=point;inside=False;j=len(polygon)-1
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[j]
        if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
        j=i
    return inside


def _belongs(hero,layer,x,y):
    return any(_inside_polygon((x+.5,y+.5),polygon)
               for polygon in ARM_SLICES[hero][layer].regions)


def _layer_pixel_allowed(hero,color):
    # Tess's cape crosses the narrow dagger-arm paths. Keep genuinely purple
    # cloth in the permanent body atlas while retaining black outlines, brown
    # gloves, skin and green blades in the arm overlays.
    hue,saturation,value=colorsys.rgb_to_hsv(
        color.r/255,color.g/255,color.b/255)
    if hero==2 and .68<=hue<=.92 and saturation>.25 and value>.08:
        return False
    return True


def _is_layer_pixel(hero,layer,x,y,color):
    if y>=BODY_PROTECTED_FROM_Y[hero]:return False
    return _belongs(hero,layer,x,y) and _layer_pixel_allowed(hero,color)


def _slice_arm(source_sheet,hero,layer):
    source=source_sheet.subsurface(
        pygame.Rect(hero*SOURCE_CELL_W,0,SOURCE_CELL_W,SOURCE_CELL_H))
    result=pygame.Surface((SOURCE_CELL_W,SOURCE_CELL_H),pygame.SRCALPHA)
    for y in range(SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            color=source.get_at((x,y))
            if not color.a:continue
            weapon=_is_layer_pixel(hero,'weapon',x,y,color)
            front=_is_layer_pixel(hero,'front',x,y,color) and not weapon
            rear=(_is_layer_pixel(hero,'rear',x,y,color) and
                  not front and not weapon)
            if ((layer=='weapon' and weapon) or
                    (layer=='front' and front) or (layer=='rear' and rear)):
                result.set_at((x,y),color)
    return result


def _rotate_at(source,pivot,transform):
    bounds=source.get_bounding_rect()
    cell=pygame.Surface((SOURCE_ARM_CELL_W,SOURCE_ARM_CELL_H),pygame.SRCALPHA)
    if not bounds.width:return cell
    # An explicit SRCALPHA target prevents pygame from filling the expanded
    # corners of rotated sub-surfaces with an opaque matte color.
    crop=pygame.Surface(bounds.size,pygame.SRCALPHA)
    crop.blit(source,(0,0),bounds)
    rotated=pygame.transform.rotate(crop,transform.angle)
    crop_center=pygame.Vector2(bounds.width/2,bounds.height/2)
    old_pivot=pygame.Vector2(pivot)-pygame.Vector2(bounds.topleft)
    pivot_from_center=(old_pivot-crop_center).rotate(-transform.angle)
    rotated_pivot=pygame.Vector2(rotated.get_width()/2,rotated.get_height()/2)+pivot_from_center
    target=(pygame.Vector2(SOURCE_ARM_OFFSET)+pygame.Vector2(pivot)+
            pygame.Vector2(transform.offset))
    top_left=target-rotated_pivot
    cell.blit(rotated,(round(top_left.x),round(top_left.y)))
    return cell


def _raw_body(source_sheet,hero):
    """Build one permanent base body; runtime states never touch this layer."""
    source=source_sheet.subsurface(
        pygame.Rect(hero*SOURCE_CELL_W,0,SOURCE_CELL_W,SOURCE_CELL_H))
    body=pygame.Surface((SOURCE_CELL_W,SOURCE_CELL_H),pygame.SRCALPHA)
    for y in range(SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            color=source.get_at((x,y))
            if (color.a and not any(_is_layer_pixel(hero,layer,x,y,color)
                                   for layer in ARM_LAYERS)):
                body.set_at((x,y),color)

    # Do not synthesize, underpaint, or grow any body pixels. The base contains
    # every authored pixel outside the explicit part slices, byte-for-byte.
    # This prevents the flat geometric torso patches seen in earlier builds.
    # This is a build-stopping invariant, not a visual guess: lower-body source
    # pixels must survive byte-for-byte in the permanent body layer.
    for y in range(BODY_PROTECTED_FROM_Y[hero],SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            if source.get_at((x,y)).a and body.get_at((x,y))!=source.get_at((x,y)):
                raise RuntimeError(f'Combat mask consumed protected body pixel: hero={hero} ({x},{y})')
    return body


def _place_native(source,source_anchor):
    """Place unscaled source pixels on the shared transparent actor cell."""
    cell=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    cell.blit(source,(COMBAT_GROUND_ANCHOR[0]-source_anchor[0],
                      COMBAT_GROUND_ANCHOR[1]-source_anchor[1]))
    return cell


def _shrink_actor_cell(cell,hero):
    """Scale a complete layer around the shared feet anchor, offline only."""
    numerator,denominator=BATTLE_SPRITE_SCALE_RATIOS[hero]
    width=(cell.get_width()*numerator+denominator//2)//denominator
    height=(cell.get_height()*numerator+denominator//2)//denominator
    scaled=pygame.transform.scale(cell,(width,height))
    anchor_x=(COMBAT_GROUND_ANCHOR[0]*numerator+denominator//2)//denominator
    anchor_y=(COMBAT_GROUND_ANCHOR[1]*numerator+denominator//2)//denominator
    result=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    result.blit(scaled,(COMBAT_GROUND_ANCHOR[0]-anchor_x,
                        COMBAT_GROUND_ANCHOR[1]-anchor_y))
    return result


def generate_atlases(root=ROOT):
    source=pygame.image.load(str(root/'assets/characters/party_battle_v6.png')).convert_alpha()
    bodies=pygame.Surface((4*COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    columns=max(map(len,HERO_POSES.values()))
    arms=pygame.Surface((columns*COMBAT_CELL_W,
                         len(HERO_POSES)*len(ARM_LAYERS)*COMBAT_CELL_H),
                        pygame.SRCALPHA)
    for hero,states in HERO_POSES.items():
        body=_shrink_actor_cell(
            _place_native(_raw_body(source,hero),(SOURCE_CELL_W//2,SOURCE_CELL_H-2)),
            hero)
        bodies.blit(body,(hero*COMBAT_CELL_W,0))
        source_layers={layer:_slice_arm(source,hero,layer) for layer in ARM_LAYERS}
        for column,state in enumerate(states):
            for layer in ARM_LAYERS:
                raw=_rotate_at(source_layers[layer],ARM_SLICES[hero][layer].pivot,
                               POSE_BLUEPRINTS[hero][state][layer])
                cell=_shrink_actor_cell(_place_native(raw,SOURCE_ARM_ANCHOR),hero)
                row=hero*len(ARM_LAYERS)+ARM_LAYERS.index(layer)
                arms.blit(cell,(column*COMBAT_CELL_W,row*COMBAT_CELL_H))
    return bodies,arms


def generate_overworld_placeholder(bodies,arms):
    """Provide replaceable 96x96 exploration arrays at the combat-art scale."""
    from combat_poses import CombatSpriteRig, HERO_COMBAT_PROFILES
    rig=CombatSpriteRig(bodies,arms)
    atlas=pygame.Surface((32*COMBAT_CELL_W,4*COMBAT_CELL_H),pygame.SRCALPHA)
    # Runtime direction order: down, left, right, up. These temporary cells use
    # the approved idle silhouette until bespoke large walking art is supplied.
    for hero,profile in enumerate(HERO_COMBAT_PROFILES):
        for direction in range(4):
            facing_right=direction==2
            for frame in range(8):
                cell=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
                rig.draw(cell,hero,profile.idle_state,*COMBAT_GROUND_ANCHOR,
                         facing_right)
                atlas.blit(cell,((direction*8+frame)*COMBAT_CELL_W,
                                 hero*COMBAT_CELL_H))
    return atlas


def save_checked(surface,path):
    temporary=path.with_suffix('.writing.png')
    pygame.image.save(surface,str(temporary))
    loaded=pygame.image.load(str(temporary))
    if loaded.get_size()!=surface.get_size():
        raise RuntimeError(f'Invalid generated atlas: {path}')
    temporary.replace(path)


def main():
    pygame.init();pygame.display.set_mode((1,1))
    bodies,arms=generate_atlases()
    overworld=generate_overworld_placeholder(bodies,arms)
    save_checked(bodies,BODY_OUTPUT)
    save_checked(arms,ARM_OUTPUT)
    save_checked(overworld,OVERWORLD_OUTPUT)
    print(BODY_OUTPUT)
    print(ARM_OUTPUT)
    print(OVERWORLD_OUTPUT)
    pygame.quit()


if __name__=='__main__':main()
