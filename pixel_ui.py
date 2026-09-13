"""Small, deterministic bitmap lettering for the native-resolution game HUD."""
import pygame

ROWS = {
    'A': (2,5,7,5,5), 'B': (6,5,6,5,6), 'C': (3,4,4,4,3),
    'D': (6,5,5,5,6), 'E': (7,4,6,4,7), 'F': (7,4,6,4,4),
    'G': (3,4,5,5,3), 'H': (5,5,7,5,5), 'I': (7,2,2,2,7),
    'J': (1,1,1,5,2), 'K': (5,5,6,5,5), 'L': (4,4,4,4,7),
    'M': (5,7,7,5,5), 'N': (5,7,7,7,5), 'O': (2,5,5,5,2),
    'P': (6,5,6,4,4), 'Q': (2,5,5,3,1), 'R': (6,5,6,5,5),
    'S': (3,4,2,1,6), 'T': (7,2,2,2,2), 'U': (5,5,5,5,7),
    'V': (5,5,5,5,2), 'W': (5,5,7,7,5), 'X': (5,5,2,5,5),
    'Y': (5,5,2,2,2), 'Z': (7,1,2,4,7),
    '0': (7,5,5,5,7), '1': (2,6,2,2,7), '2': (6,1,2,4,7),
    '3': (6,1,2,1,6), '4': (5,5,7,1,1), '5': (7,4,6,1,6),
    '6': (3,4,6,5,2), '7': (7,1,2,2,2), '8': (2,5,2,5,2),
    '9': (2,5,3,1,6), ' ': (0,0,0,0,0), '.': (0,0,0,0,2),
    ',': (0,0,0,2,4), ':': (0,2,0,2,0), ';': (0,2,0,2,4),
    '!': (2,2,2,0,2), '?': (6,1,2,0,2), '-': (0,0,7,0,0),
    '+': (0,2,7,2,0), '/': (1,1,2,4,4), '%': (5,1,2,4,5),
    '>': (4,2,1,2,4), '<': (1,2,4,2,1), '=': (0,7,0,7,0),
    '[': (6,4,4,4,6), ']': (3,1,1,1,3), '(': (2,4,4,4,2),
    ')': (2,1,1,1,2), "'": (2,2,0,0,0), '&': (2,5,2,5,3),
}


def label(surface, value, x, y, color=(235,231,218), scale=1, limit=None):
    value = str(value).upper().replace('\u2014', '-').replace('\u2019', "'")
    if limit and len(value) > limit:
        value = value[:limit-2] + '..'
    for index, letter in enumerate(value):
        for row, bits in enumerate(ROWS.get(letter, ROWS['?'])):
            for col in range(3):
                if bits & (4 >> col):
                    pygame.draw.rect(surface, color,
                                     (x+(index*4+col)*scale, y+row*scale, scale, scale))


def panel(surface, rect, accent=(73,148,150)):
    pygame.draw.rect(surface, (11,18,27), rect)
    pygame.draw.rect(surface, (53,68,78), rect, 1)
    pygame.draw.line(surface, accent, (rect[0]+1, rect[1]),
                     (rect[0]+rect[2]-2, rect[1]))
