"""Data-driven full-frame battle animation clips.

The authored source is a 29-frame, 64x64-per-frame Rian master strip.  An
offline builder pads those cells into the engine's existing 96x96 actor-cell
contract.  Runtime playback selects and blits source rectangles at 1:1; it
never scales, rotates, or synthesizes character pixels.
"""
from dataclasses import dataclass

from render_config import ACTOR_CELL_H, ACTOR_CELL_W, ACTOR_GROUND_ANCHOR


MASTER_FRAME_W = 64
MASTER_FRAME_H = 64
MASTER_FRAME_COUNT = 29
RUNTIME_FRAME_COUNT = MASTER_FRAME_COUNT

# The four strips below were exported with Rian at roughly 5/9 of the body
# scale used by party_overworld_hd_v2.png.  Scale only after extracting a
# 64x64 frame: this retains the complete sword/cape silhouette instead of
# clipping enlarged pixels back into the source cell.
DIRECTIONAL_FRAME_W = 64
DIRECTIONAL_FRAME_H = 64
RIAN_PARTY_REFERENCE_SCALE = 1.8
RIAN_UNDERSIZED_DIRECTIONAL_KEYS = frozenset({
    'profile_right',
    'sword_basic_front_down',
    'sword_basic_back_up',
    'sword_basic_profile_right',
})


def rian_directional_scale(key):
    """Return the display correction for an authored directional strip."""
    return (RIAN_PARTY_REFERENCE_SCALE
            if key in RIAN_UNDERSIZED_DIRECTIONAL_KEYS else 1.0)


def scaled_directional_frame(sheet, frame, key):
    """Extract a frame, then apply Rian's measured pixel-perfect correction."""
    import pygame
    if sheet.get_height() != DIRECTIONAL_FRAME_H or sheet.get_width() % DIRECTIONAL_FRAME_W:
        raise ValueError(f'Directional strip must contain 64x64 cells, got {sheet.get_size()}')
    frame_count = sheet.get_width() // DIRECTIONAL_FRAME_W
    if not 0 <= frame < frame_count:
        raise IndexError(f'Directional frame {frame} is outside 0..{frame_count - 1}')
    image = sheet.subsurface(pygame.Rect(frame * DIRECTIONAL_FRAME_W, 0,
                                         DIRECTIONAL_FRAME_W, DIRECTIONAL_FRAME_H))
    scale = rian_directional_scale(key)
    if scale == 1.0:
        return image
    size = (round(DIRECTIONAL_FRAME_W * scale),
            round(DIRECTIONAL_FRAME_H * scale))
    # pygame.transform.scale is nearest-neighbour; smoothscale is intentionally
    # avoided so the corrected sprite keeps hard 1:1-style pixel clusters.
    return pygame.transform.scale(image, size)


@dataclass(frozen=True)
class AnimationClip:
    """A contiguous animation range with deterministic delta-time sampling."""

    name: str
    start: int
    count: int
    frame_seconds: float
    loop: bool = False
    priority: int = 0
    next_clip: str = ''
    hold_last: bool = False
    impact_frame: int = -1

    @property
    def frames(self):
        return tuple(range(self.start, self.start + self.count))

    @property
    def duration(self):
        return self.count * self.frame_seconds

    def sample(self, elapsed):
        """Return ``(global_frame, finished)`` for non-negative elapsed time."""
        index = int(max(0., elapsed) / self.frame_seconds)
        if self.loop:
            return self.start + index % self.count, False
        finished = index >= self.count
        return self.start + min(index, self.count - 1), finished


# The ranges intentionally mirror the master-strip contract documented in the
# character asset README.  Keeping all timing here makes animation changes data
# edits instead of another rewrite of WorldCombat.update_action.
BATTLE_CLIPS = {
    'overworld_idle': AnimationClip('overworld_idle', 0, 4, .18, loop=True),
    'overworld_walk': AnimationClip('overworld_walk', 4, 4, .10, loop=True),
    'battle_idle': AnimationClip('battle_idle', 8, 4, .16, loop=True),
    'battle_dash': AnimationClip('battle_dash', 12, 4, .075, loop=True, priority=1),
    'sword_basic': AnimationClip('sword_basic', 16, 4, .095, priority=2,
                                 next_clip='battle_idle', impact_frame=1),
    'sword_skill': AnimationClip('sword_skill', 20, 4, .11, priority=3,
                                 next_clip='battle_idle', impact_frame=1),
    'hurt': AnimationClip('hurt', 24, 3, .09, priority=4,
                          next_clip='battle_idle'),
    'defeated': AnimationClip('defeated', 27, 2, .16, priority=5,
                              hold_last=True),
}


def validate_clip_contract(clips=BATTLE_CLIPS):
    """Fail loudly if a clip overlaps, leaves a hole, or exceeds the strip."""
    frames = [frame for clip in clips.values() for frame in clip.frames]
    if frames != list(range(MASTER_FRAME_COUNT)):
        raise ValueError('Battle animation clips must cover frames 0..28 exactly once')
    for clip in clips.values():
        if clip.count <= 0 or clip.frame_seconds <= 0:
            raise ValueError(f'Invalid timing for clip {clip.name}')
        if clip.next_clip and clip.next_clip not in clips:
            raise ValueError(f'Unknown next clip {clip.next_clip!r}')
        if clip.impact_frame >= clip.count:
            raise ValueError(f'Impact frame lies outside clip {clip.name}')
    return True


validate_clip_contract()


class BattleAnimationAtlas:
    """Lossless 1:1 renderer for the padded 29-frame runtime atlas."""

    def __init__(self, sheet, source_facing_right=True):
        required = (RUNTIME_FRAME_COUNT * ACTOR_CELL_W, ACTOR_CELL_H)
        if sheet.get_size() != required:
            raise ValueError(f'Battle animation atlas must be {required}, got {sheet.get_size()}')
        self.sheet = sheet
        self.source_facing_right = source_facing_right

    def frame_rect(self, frame):
        import pygame
        if not 0 <= frame < RUNTIME_FRAME_COUNT:
            raise IndexError(f'Battle animation frame {frame} is outside 0..28')
        return pygame.Rect(frame * ACTOR_CELL_W, 0, ACTOR_CELL_W, ACTOR_CELL_H)

    def draw(self, target, frame, x, y, facing_right):
        import pygame
        image = self.sheet.subsurface(self.frame_rect(frame))
        if facing_right != self.source_facing_right:
            image = pygame.transform.flip(image, True, False)
        target.blit(image, (round(x - ACTOR_GROUND_ANCHOR[0]),
                            round(y - ACTOR_GROUND_ANCHOR[1])))
