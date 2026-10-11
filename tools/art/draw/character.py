"""Protagonist base sprite, 16x32, front view. Drawn as a left half that is mirrored, then
asymmetric details and right-side shading are added, then a coloured outline."""
from common import C, new
from objects import auto_outline

PAL = {
    "a": "soil-0",  # hair shadow
    "b": "soil-1",  # hair
    "c": "soil-2",  # hair highlight
    "s": "skin-3",
    "S": "skin-2",
    "e": "slate-0",  # eyes
    "p": "blossom-3",  # cheeks
    "m": "skin-2",  # mouth
    "j": "magic-2",  # academy jacket
    "J": "magic-1",
    "i": "magic-3",
    "w": "paper",  # shirt
    "W": "stone-4",
    "t": "slate-2",  # trousers
    "T": "slate-1",
    "u": "wood-1",  # boots
    "U": "wood-0",
    "g": "wood-2",  # bag strap
    "y": "sun-3",  # buttons
}

LEFT = [
    "........",  # 0
    ".....abb",  # 1
    "...abbcc",  # 2
    "..abbccc",  # 3
    "..abbbbc",  # 4
    ".abbbbbb",  # 5
    ".abbsbbs",  # 6
    ".abbssss",  # 7
    ".abssess",  # 8
    ".abssess",  # 9
    ".abspsss",  # 10
    ".aasssss",  # 11
    "..aSssss",  # 12
    "....Ssss",  # 13
    "......Ss",  # 14
    "...jjjjw",  # 15
    "..ijjjjw",  # 16
    ".ijJjjjw",  # 17
    ".ijJjjjw",  # 18
    ".ijJjjjw",  # 19
    ".ijJjjjj",  # 20
    ".ijJjjjj",  # 21
    ".jjJJJJJ",  # 22
    ".s.ttttt",  # 23
    ".S.ttttt",  # 24
    "...tttt.",  # 25
    "...tttt.",  # 26
    "...tttt.",  # 27
    "...tttt.",  # 28
    "...uuuu.",  # 29
    "..uuuuu.",  # 30
    "........",  # 31
]

# (x, y, char) details that break the symmetry
DETAILS = [
    (7, 12, "m"), (8, 12, "m"),  # mouth
    (6, 3, "c"), (5, 4, "c"), (4, 5, "c"),  # hair shine on the lit side
    (9, 6, "b"), (10, 6, "b"),  # fringe swept to one side
    (7, 17, "y"), (7, 20, "y"),  # buttons
    (4, 15, "g"), (5, 16, "g"), (6, 17, "g"), (7, 18, "g"), (8, 19, "g"), (9, 20, "g"), (10, 21, "g"),  # strap
]

DARKEN = {"j": "J", "i": "j", "t": "T", "u": "U", "s": "S", "w": "W", "b": "a", "c": "b"}


def front():
    rows = [half + half[::-1] for half in LEFT]
    grid = [list(r) for r in rows]
    for x, y, ch in DETAILS:
        grid[y][x] = ch
    for y, row in enumerate(grid):  # light comes from the left: shade the right edge
        for x in range(9, 16):
            ch = row[x]
            if ch in DARKEN and (x >= 11 or y >= 15) and row[min(15, x + 1)] in ".":
                row[x] = DARKEN[ch]
            elif ch in ("j", "t") and x >= 10:
                row[x] = DARKEN[ch]
    img = new(16, 32)
    px = img.load()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ".":
                px[x, y] = C(PAL[ch])
    return auto_outline(img)
