"""Bake locked combat poses into true-size transparent PNG atlases.

This is an asset-authoring tool, not runtime rendering. It may rotate and reduce
the 64x80 source artwork, but the resulting 64x64 frames are checked in and are
always blitted 1:1 by the game.
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
from combat_poses import (ARM_LAYERS, ARM_SLICES, BAKED_SOURCE_SCALE,
    BODY_PROTECTED_FROM_Y,
    COMBAT_CELL_H, COMBAT_CELL_W, COMBAT_GROUND_ANCHOR, HERO_POSES,
    POSE_BLUEPRINTS, SOURCE_ARM_ANCHOR, SOURCE_ARM_CELL_H,
    SOURCE_ARM_CELL_W, SOURCE_ARM_OFFSET, SOURCE_CELL_H, SOURCE_CELL_W)


BODY_OUTPUT=ROOT/'assets/characters/party_combat_bodies_v2.png'
ARM_OUTPUT=ROOT/'assets/characters/party_combat_arms_v2.png'


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
            front=_is_layer_pixel(hero,'front',x,y,color)
            rear=_is_layer_pixel(hero,'rear',x,y,color) and not front
            if (layer=='front' and front) or (layer=='rear' and rear):
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


def _raw_body(source_sheet,motion_sheet,hero):
    """Build one permanent base body; runtime states never touch this layer."""
    source=source_sheet.subsurface(
        pygame.Rect(hero*SOURCE_CELL_W,0,SOURCE_CELL_W,SOURCE_CELL_H))
    body=pygame.Surface((SOURCE_CELL_W,SOURCE_CELL_H),pygame.SRCALPHA)
    for y in range(SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            color=source.get_at((x,y))
            if (color.a and not _is_layer_pixel(hero,'front',x,y,color) and
                    not _is_layer_pixel(hero,'rear',x,y,color)):
                body.set_at((x,y),color)

    # Fill only the torso pixels hidden behind the authored source arms. The
    # narrowed masks above never reach the lower body; this underpainting makes
    # the chest continuous beneath every transparent pre-baked arm overlay.
    under=motion_sheet.subsurface(pygame.Rect(8*32,hero*48,32,48)).copy()
    under=pygame.transform.scale(under,(43,65))
    for uy in range(under.get_height()):
        for ux in range(under.get_width()):
            x,y=10+ux,13+uy
            if 16<=x<=49 and 15<=y<=62 and body.get_at((x,y)).a==0:
                color=under.get_at((ux,uy))
                if color.a:body.set_at((x,y),color)
    # This is a build-stopping invariant, not a visual guess: lower-body source
    # pixels must survive byte-for-byte in the permanent body layer.
    for y in range(BODY_PROTECTED_FROM_Y[hero],SOURCE_CELL_H):
        for x in range(SOURCE_CELL_W):
            if source.get_at((x,y)).a and body.get_at((x,y))!=source.get_at((x,y)):
                raise RuntimeError(f'Combat mask consumed protected body pixel: hero={hero} ({x},{y})')
    return body


def _bake(source,source_anchor):
    """Reduce authored art once and align it to the shared combat ground point."""
    size=(round(source.get_width()*BAKED_SOURCE_SCALE),
          round(source.get_height()*BAKED_SOURCE_SCALE))
    image=pygame.transform.scale(source,size)
    anchor=(round(source_anchor[0]*BAKED_SOURCE_SCALE),
            round(source_anchor[1]*BAKED_SOURCE_SCALE))
    cell=pygame.Surface((COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    cell.blit(image,(COMBAT_GROUND_ANCHOR[0]-anchor[0],
                     COMBAT_GROUND_ANCHOR[1]-anchor[1]))
    return cell


def generate_atlases(root=ROOT):
    source=pygame.image.load(str(root/'assets/characters/party_battle_v6.png')).convert_alpha()
    motion=pygame.image.load(str(root/'assets/characters/party_motion_v1.png')).convert_alpha()
    bodies=pygame.Surface((4*COMBAT_CELL_W,COMBAT_CELL_H),pygame.SRCALPHA)
    columns=max(map(len,HERO_POSES.values()))
    arms=pygame.Surface((columns*COMBAT_CELL_W,8*COMBAT_CELL_H),pygame.SRCALPHA)
    for hero,states in HERO_POSES.items():
        body=_bake(_raw_body(source,motion,hero),(SOURCE_CELL_W//2,SOURCE_CELL_H-2))
        bodies.blit(body,(hero*COMBAT_CELL_W,0))
        source_layers={layer:_slice_arm(source,hero,layer) for layer in ARM_LAYERS}
        for column,state in enumerate(states):
            for layer in ARM_LAYERS:
                raw=_rotate_at(source_layers[layer],ARM_SLICES[hero][layer].pivot,
                               POSE_BLUEPRINTS[hero][state][layer])
                cell=_bake(raw,SOURCE_ARM_ANCHOR)
                row=hero*2+ARM_LAYERS.index(layer)
                arms.blit(cell,(column*COMBAT_CELL_W,row*COMBAT_CELL_H))
    return bodies,arms


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
    save_checked(bodies,BODY_OUTPUT)
    save_checked(arms,ARM_OUTPUT)
    print(BODY_OUTPUT)
    print(ARM_OUTPUT)
    pygame.quit()


if __name__=='__main__':main()
