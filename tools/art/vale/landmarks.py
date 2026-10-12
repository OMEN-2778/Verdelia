"""Palettes and 2D parts for the bigger buildings (town3d.py): the barn's red boards and white
trim, cross-braced barn doors, hay, the windmill's cream clapboard and its sails, drawn afresh
for every frame of their turn, and the forge's embers."""
import math

from buildings import DARKWOOD, IRON, Canvas

BARN_RED = ["#2e1212", "#5a1f1c", "#842d26", "#a8403a", "#c45a4e", "#db7f6f", "#ecaa98"]
WHITE_TRIM = ["#6d6a66", "#a9a49c", "#d6d1c7", "#efebe3", "#fdfbf6"]
HAY = ["#6b4f17", "#a8822a", "#d4b043", "#efd679", "#fbf0b5"]
CREAM = ["#3d3730", "#8e8474", "#bdb29e", "#d8cfbb", "#e9e2d1", "#f5f0e4", "#fdfbf5"]
EMBER = ["#5a1a08", "#b8400e", "#f07a1e", "#ffc24a", "#fff0a0"]
SAIL = ["#7d7871", "#bcb6ac", "#e4dfd5", "#fbf8f2"]


def x_door(cv, x0, x1, y0, y1, wall, trim=WHITE_TRIM):
    """A barn door leaf: boards with a white frame and cross braces."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            k = (x - x0) % 4
            cv.set(x, y, wall[3] if k == 0 else wall[1] if k == 3 else wall[2])
    w, h = x1 - x0, y1 - y0
    for i in range(max(w, h)):
        for (xa, ya) in ((x0 + round(i * (w - 1) / max(1, h - 1)), y0 + i), (x1 - 1 - round(i * (w - 1) / max(1, h - 1)), y0 + i)):
            if y0 <= ya < y1:
                cv.set(xa, ya, trim[3])
                cv.set(xa + 1 if xa + 1 < x1 else xa, ya, trim[2])
    for y in range(y0, y1):
        cv.set(x0, y, trim[3])
        cv.set(x0 + 1, y, trim[2])
        cv.set(x1 - 2, y, trim[2])
        cv.set(x1 - 1, y, trim[1])
    for x in range(x0, x1):
        for y in (y0, y0 + 1, y1 - 2, y1 - 1):
            cv.set(x, y, trim[3] if y < y0 + 2 else trim[2])


# ================================================================ designs


SAIL_FRAMES = 12


def _sails(sail_len, S, turn):
    sails = Canvas(S, S)
    c0 = S // 2
    for k in range(4):
        a = turn + k * math.pi / 2 + math.pi / 4
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx  # each blade lies on one side of its stock
        for s in range(3, sail_len):
            x, y = c0 + dx * s, c0 + dy * s
            if s > 9:
                for o in range(2, 9):
                    for sub in (0.0, 0.5):
                        px, py = round(x + nx * (o + sub)), round(y + ny * (o + sub))
                        grid = s % 5 == 0 or o in (2, 8)
                        sails.set(px, py, DARKWOOD[3] if grid else SAIL[3] if o < 5 else SAIL[2])
        for s in range(3, sail_len):
            x, y = c0 + dx * s, c0 + dy * s
            sails.set(round(x), round(y), DARKWOOD[4])
    for y in range(c0 - 2, c0 + 3):
        for x in range(c0 - 2, c0 + 3):
            if (x - c0) ** 2 + (y - c0) ** 2 <= 5:
                sails.set(x, y, IRON[2])
    sails.outline()
    return sails.im


