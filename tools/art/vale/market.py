"""Market structures and street props for the town, in the same style and light as buildings.py:
a sail-cloth stall draped between poles with pennants (arms, cloth or pottery), a produce stand
under a big painted signboard on forked branches, a covered table of bakes, a pointed fortune
teller's pavilion, a covered merchant wagon, and props: weapon rack, armour stand, banner, a
table with stools, stacks of barrels and crates, a rug and a well.
"""
import math
import random

from buildings import DARKWOOD, IRON, LIT, STONE, WOOD, Canvas, _result, barrel, crate, item, lantern, sack, tone

WHITE = ["#7d7871", "#aaa49b", "#d4cec4", "#ece7de", "#fbf8f2"]
CLOTH = {
    "blue": ["#1b2945", "#2b4372", "#3d5f9c", "#5a82c0", "#8aaee0"],
    "red": ["#4a1619", "#7a2629", "#a8383a", "#cf5652", "#ec8a7c"],
    "purple": ["#24183a", "#3d2862", "#5a3b8c", "#7c58b4", "#a786d6"],
    "green": ["#1b3322", "#2b5233", "#3f7447", "#5a965c", "#88bd7f"],
    "ochre": ["#4f3510", "#7e5719", "#ad7d26", "#d4a340", "#f0cd78"],
    "teal": ["#123236", "#1d4f53", "#2b6e70", "#46928e", "#79bcb2"],
}
STEEL = ["#2a2e38", "#4f5562", "#808897", "#b7bec9", "#e9edf2"]
GOLD = ["#5e3f0e", "#9a6c18", "#d19f2c", "#f1cf5e", "#fff0a8"]
ROPE = "#3d2c1f"
BIG = {  # big produce: dark, mid, light, accent
    "melon": ["#1f4a22", "#3c7a32", "#7fb653", "#cfe39a"],
    "pumpkin": ["#7a3a10", "#c9661a", "#ef9d3e", "#4f6b22"],
    "cabbage": ["#24481f", "#4f8a36", "#90c25e", "#c9e8a0"],
    "grapes": ["#24123a", "#4f2e7c", "#8461b8", "#3f7a37"],
    "apples": ["#5e1a1a", "#b8332b", "#e66a4e", "#3f7a37"],
    "oranges": ["#7a3d0e", "#de7f1f", "#f6b14c", "#3f7a37"],
    "lemons": ["#7a6410", "#d9bd2a", "#f6e47a", "#3f7a37"],
    "carrots": ["#7a300e", "#d9661f", "#f6a050", "#4f8a36"],
}


# ================================================================ parts

def pole(cv, x, y0, y1, ramp=DARKWOOD):
    for y in range(y0, y1):
        cv.set(x, y, ramp[5])
        cv.set(x + 1, y, ramp[3])
    cv.set(x, y1 - 1, ramp[3])
    cv.set(x + 1, y1 - 1, ramp[2])


def forked_pole(cv, x, y0, y1):
    """A rough branch for a pole, forked at the top."""
    pole(cv, x, y0 + 3, y1)
    for i in range(4):
        cv.set(x - i, y0 + 3 - i, DARKWOOD[4])
        cv.set(x + 1 + i, y0 + 3 - i, DARKWOOD[3])
    for y in range(y0 + 8, y1, 7):  # knots
        cv.set(x, y, DARKWOOD[2])


def pennant(cv, x, y, ramp, right=True):
    """A small flag at the top of a pole at x (pole top at y)."""
    cv.set(x, y - 1, GOLD[3])
    cv.set(x + 1, y - 1, GOLD[2])
    cv.set(x, y - 2, GOLD[4])
    d = 1 if right else -1
    sx = x + 2 if right else x - 1
    for j, n in enumerate((7, 5, 3)):
        for i in range(n):
            wave = 1 if 2 <= i <= 4 else 0
            cv.set(sx + d * i, y + j - wave, ramp[3] if j == 0 else ramp[2] if j == 1 else ramp[1])


def rope(cv, x0, y0, x1, y1, sag=2.0):
    """A thin guy rope (draw it after the outline so it stays one pixel wide) and its peg."""
    n = max(abs(x1 - x0), abs(y1 - y0)) + 1
    for i in range(n + 1):
        t = i / n
        x, y = round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t + sag * 4 * t * (1 - t))
        if not cv.get(x, y)[3]:
            cv.set(x, y, "#5c4632")
    cv.set(x1, y1, DARKWOOD[1])
    cv.set(x1, y1 - 1, DARKWOOD[4])


def draped_canopy(cv, x0, x1, back_y, front_y, sag_back, sag_front, ramp, white=WHITE, swirl=True):
    """A cloth sheet tied to four poles: the back edge sags a little, the front a lot; swirling
    bands of colour and white, hanging folds, a lit back edge and a toothed valance in front."""
    w = x1 - x0
    for x in range(x0, x1):
        u = (x - x0) / max(1, w - 1)
        yb = round(back_y + sag_back * 4 * u * (1 - u))
        yf = round(front_y + sag_front * 4 * u * (1 - u))
        for y in range(yb, yf + 1):
            t = (y - yb) / max(1, yf - yb)
            if swirl:
                band = math.floor((x - x0 + (y - yb) * 1.3 + 5 * math.sin(u * 7.0 + t * 2.0)) / 7) % 2
            else:
                band = ((x - x0) // 5) % 2
            r = ramp if band == 0 else white
            v = 0.66 - 0.32 * t + 0.1 * math.sin(u * math.pi * 4) * t - 0.12 * u
            for px in (x0, x1 - 1):  # pulled taut and lit near the poles
                v += 0.18 * math.exp(-((x - px) ** 2) / 30.0) * (1 - t)
            if y == yb:
                v += 0.3
            cv.set(x, y, r[tone(r, v)])
        # valance: a row of points hanging off the front edge
        k = (x - x0) % 6
        depth = 4 - abs(k - 3)
        band = ((x - x0) // 6) % 2
        r = ramp if band == 0 else white
        for i in range(depth):
            cv.set(x, yf + 1 + i, r[2] if i < depth - 1 else r[1])
        cv.set(x, yf + 1, r[3])


def big_item(cv, x, bottom, kind):
    """A big round thing (melon, pumpkin, cabbage, bunch of grapes...) sitting on `bottom`."""
    d, m, l, a = BIG[kind]
    if kind in ("melon", "pumpkin", "cabbage"):
        w, h = (7, 5) if kind != "cabbage" else (6, 5)
        for j in range(h):
            for i in range(w):
                dx, dy = (i + 0.5 - w / 2) / (w / 2), (j + 0.5 - h / 2) / (h / 2)
                if dx * dx + dy * dy > 1.05:
                    continue
                c = l if dx + dy < -0.6 else m if dx + dy < 0.5 else d
                if kind == "melon" and i % 2 == 1:
                    c = d if c != d else BIG["melon"][0]
                if kind == "pumpkin" and i in (2, 4):
                    c = d
                if kind == "cabbage" and (i + j) % 3 == 0 and c != d:
                    c = a
                cv.set(x + i, bottom - h + j, c)
        if kind == "pumpkin":
            cv.set(x + 3, bottom - h - 1, a)
        return w
    if kind == "grapes":
        for j, (a0, a1) in enumerate(((0, 4), (0, 4), (1, 4), (1, 3))):
            for i in range(a0, a1):
                cv.set(x + i, bottom - 5 + j, l if (i + j) % 2 == 0 and j < 2 else m if (i + j) % 2 == 0 else d)
        cv.set(x + 2, bottom - 6, a)
        cv.set(x + 3, bottom - 6, a)
        return 4
    if kind == "carrots":
        for i in range(0, 5, 2):
            for j in range(4):
                cv.set(x + i, bottom - 1 - j, l if j == 3 else m)
            cv.set(x + i, bottom - 5, a)
            cv.set(x + i + 1, bottom - 6, a)
        return 5
    # small round fruit as a little heap
    for i in range(3):
        cv.set(x + i, bottom - 1, m if i < 2 else d)
        cv.set(x + i, bottom - 2, l if i == 0 else m)
    cv.set(x + 1, bottom - 3, l)
    return 3


def heap(cv, rnd, x0, x1, bottom, kind, rows=3):
    """A mound of produce filling a bin from x0 to x1."""
    for r in range(rows):
        x = x0 + r * 2 + rnd.randint(0, 1)
        y = bottom - r * 3
        while x < x1 - 2 - r * 2:
            if kind in BIG and kind not in ("apples", "oranges", "lemons"):
                x += big_item(cv, x, y, kind) - 2
            else:
                big_item(cv, x, y, kind)
                x += 3


def basket(cv, rnd, x, bottom, w, kind):
    for y in range(bottom - 5, bottom):
        for i in range(w):
            weave = (i + y) % 2 == 0
            c = "#c9a061" if weave else "#9b7642"
            if i in (0, w - 1) or y == bottom - 1:
                c = "#6b4e2a"
            cv.set(x + i, y, c)
    for i in range(w):
        cv.set(x + i, bottom - 5, "#e2c084")
    heap(cv, rnd, x, x + w, bottom - 4, kind, rows=2)


def blade(cv, x, top, base, kind):
    """A weapon standing on `base` (sword, spear or axe), 1-3 px wide."""
    if kind == "spear":
        for y in range(top + 4, base):
            cv.set(x, y, WOOD[4] if y % 5 else WOOD[2])
        cv.set(x, top, STEEL[4])
        for y in range(top + 1, top + 4):
            cv.set(x, y, STEEL[3])
            cv.set(x - 1 if y > top + 1 else x, y, STEEL[4])
            cv.set(x + 1 if y > top + 1 else x, y, STEEL[2])
        cv.set(x - 1, top + 4, CLOTH["red"][3])
        cv.set(x + 1, top + 4, CLOTH["red"][2])
    elif kind == "axe":
        for y in range(top + 1, base):
            cv.set(x, y, WOOD[4] if y % 4 else WOOD[2])
        for j, (a, b) in enumerate(((1, 3), (1, 4), (1, 4), (1, 3))):
            for i in range(a, b + 1):
                cv.set(x + i, top + j, STEEL[4] if i == b else STEEL[3] if j < 2 else STEEL[2])
    else:  # sword, point up
        cv.set(x, top, STEEL[4])
        for y in range(top + 1, base - 5):
            cv.set(x, y, STEEL[4] if y < top + 4 else STEEL[3])
            cv.set(x + 1, y, STEEL[2])
        for i in range(-1, 3):
            cv.set(x + i, base - 5, GOLD[3] if i < 1 else GOLD[2])
        for y in range(base - 4, base - 1):
            cv.set(x, y, "#6b3c17")
            cv.set(x + 1, y, "#4a2a12")
        cv.set(x, base - 1, GOLD[3])


def shield(cv, cx, cy, ramp, r=4):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d > r * r + 1:
                continue
            if d > (r - 1) ** 2:
                c = STEEL[3] if x + y < cx + cy else STEEL[1]
            else:
                c = ramp[3] if x < cx - 1 else ramp[2] if x < cx + 1 else ramp[1]
                if abs(x - cx) <= 0 or abs(y - cy) <= 0:
                    c = GOLD[3] if x + y < cx + cy else GOLD[2]
            cv.set(x, y, c)
    cv.set(cx, cy, GOLD[4])


def weapon_rack(cv, rnd, x0, x1, base):
    pole(cv, x0, base - 13, base)
    pole(cv, x1 - 2, base - 13, base)
    kinds = ["sword", "spear", "axe", "sword", "spear"]
    x = x0 + 3
    k = rnd.randint(0, 4)
    while x < x1 - 3:
        kind = kinds[k % len(kinds)]
        top = base - (21 if kind == "spear" else 16 if kind == "sword" else 15)
        blade(cv, x, top, base - 1, kind)
        x += 3 if kind != "axe" else 5
        k += 1
    for y in (base - 12, base - 5):  # rails in front of the weapons
        for x in range(x0, x1):
            cv.set(x, y, DARKWOOD[5])
            cv.set(x, y + 1, DARKWOOD[2])


def armour_stand(cv, cx, base, plume=CLOTH["red"]):
    pole(cv, cx, base - 10, base)
    for x in range(cx - 3, cx + 5):  # cross foot
        cv.set(x, base - 1, DARKWOOD[3])
    # breastplate
    for j in range(8):
        half = 4 if j < 5 else 3
        for i in range(-half, half + 1):
            x, y = cx + i, base - 18 + j
            c = STEEL[4] if i < -1 and j < 4 else STEEL[3] if i < 1 else STEEL[2] if i < 3 else STEEL[1]
            if j == 7 or abs(i) == half:
                c = STEEL[1]
            cv.set(x, y, c)
    for i in (-5, 5):  # pauldrons
        cv.set(cx + i, base - 18, STEEL[3])
        cv.set(cx + i, base - 17, STEEL[2])
    # helmet with a slit visor and a plume
    for j in range(6):
        for i in range(-3, 4):
            if j == 0 and abs(i) == 3:
                continue
            c = STEEL[4] if i < -1 else STEEL[3] if i < 1 else STEEL[2]
            if j == 3 and -2 <= i <= 2:
                c = STEEL[0]
            cv.set(cx + i, base - 25 + j, c)
    for j in range(4):
        cv.set(cx + 1 + j // 2, base - 26 - j, plume[3] if j % 2 else plume[2])
        cv.set(cx + 2 + j // 2, base - 26 - j, plume[1])


def banner(cv, x, base, ramp, h=30, emblem="sun"):
    """A tall pole with a cross bar and a hanging banner with a pointed tail."""
    pole(cv, x, base - h, base)
    cv.set(x, base - h - 1, GOLD[4])
    cv.set(x + 1, base - h - 1, GOLD[2])
    top = base - h + 2
    for i in range(-5, 7):
        cv.set(x + i, top, DARKWOOD[4])
    for j in range(16):
        for i in range(-4, 6):
            tail = j - 12
            if tail > 0 and abs(i - 0.5) < tail * 1.4:
                continue  # V cut at the bottom
            c = ramp[3] if i < -1 else ramp[2] if i < 3 else ramp[1]
            if i in (-4, 5):
                c = GOLD[2]
            cv.set(x + i, top + 1 + j, c)
    cy = top + 7
    for i, j in ((0, -2), (1, -2), (-1, -1), (2, -1), (-2, 0), (3, 0), (-1, 1), (2, 1), (0, 2), (1, 2), (0, 0), (1, 0), (0, -1), (1, 1)):
        cv.set(x + i, cy + j, GOLD[3] if (i + j) < 1 else GOLD[2])


def table_cloth(cv, x0, x1, top, h, cloth=WHITE, hem=True):
    """A table under a cloth: the lit top, then folds hanging down the front to a wavy hem."""
    for y in range(top, top + 3):
        for x in range(x0, x1):
            cv.set(x, y, cloth[4] if y == top else cloth[3])
    for y in range(top + 3, top + h):
        for x in range(x0, x1):
            k = (x - x0) % 5
            c = cloth[3] if k == 0 else cloth[1] if k == 4 else cloth[2]
            if y == top + 3:
                c = cloth[1]
            cv.set(x, y, c)
    if hem:
        for x in range(x0, x1):
            if (x - x0) % 5 in (1, 2, 3):
                cv.set(x, top + h, cloth[1])


def wheel(cv, cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x - cx, y - cy)
            if d > r + 0.4:
                continue
            if d > r - 1.4:
                c = DARKWOOD[4] if (x - cx) + (y - cy) < 0 else DARKWOOD[2]
                cv.set(x, y, c)
            elif d < 1.6:
                cv.set(x, y, IRON[2] if x <= cx else IRON[1])
    for k in range(6):  # spokes
        a = k * math.pi / 3 + 0.3
        for s in range(2, r - 1):
            cv.set(round(cx + math.cos(a) * s), round(cy + math.sin(a) * s), DARKWOOD[5] if k < 3 else DARKWOOD[3])


def crystal_ball(cv, cx, bottom):
    for x in range(cx - 3, cx + 4):
        cv.set(x, bottom - 1, GOLD[2])
        cv.set(x, bottom - 2, GOLD[3] if x < cx else GOLD[2])
    orb = ["#3a1650", "#6b2d8f", "#a35cc8", "#e2b4f2"]
    for y in range(bottom - 9, bottom - 2):
        for x in range(cx - 3, cx + 4):
            d = (x - cx) ** 2 + (y - (bottom - 6)) ** 2
            if d <= 10:
                c = orb[3] if d <= 2 and x < cx and y < bottom - 6 else orb[2] if x + y < cx + bottom - 6 else orb[1]
                cv.set(x, y, c)
                cv.lit(x, y, LIT[2] if d > 4 else LIT[4])


def candle(cv, x, bottom, h=3):
    for y in range(bottom - h, bottom):
        cv.set(x, y, "#f1ead8")
    cv.set(x, bottom - h - 1, "#ffd27a")
    cv.lit(x, bottom - h - 1, LIT[4])
    cv.set(x, bottom - h - 2, "#fff3c0")
    cv.lit(x, bottom - h - 2, LIT[3])


def rug(cv, x0, x1, y0, y1, ramp):
    for y in range(y0, y1):
        for x in range(x0, x1):
            bx = min(x - x0, x1 - 1 - x)
            by = min(y - y0, y1 - 1 - y)
            b = min(bx, by)
            cx, cy = (x0 + x1 - 1) / 2, (y0 + y1 - 1) / 2
            diamond = abs(x - cx) / max(1, (x1 - x0) / 2 - 3) + abs(y - cy) / max(1, (y1 - y0) / 2 - 1.5) < 0.75
            c = ramp[1] if b == 0 else GOLD[2] if b == 1 else ramp[3] if diamond else ramp[2]
            if diamond and (abs(x - cx) + abs(y - cy)) < 1.5:
                c = GOLD[3]
            cv.set(x, y, c)
    for y in range(y0 + 1, y1 - 1, 2):  # fringe at the ends
        cv.set(x0 - 1, y, WHITE[3])
        cv.set(x1, y, WHITE[3])


def stool(cv, x, bottom):
    for i in range(5):
        cv.set(x + i, bottom - 5, WOOD[5] if i < 3 else WOOD[4])
        cv.set(x + i, bottom - 4, WOOD[3] if i < 4 else WOOD[2])
    for y in range(bottom - 3, bottom):
        cv.set(x, y, WOOD[3])
        cv.set(x + 4, y, WOOD[1])


def jug(cv, x, bottom, ramp=("#5b3a22", "#8f5a33", "#c0814d")):
    rows = [(1, 3), (0, 4), (0, 4), (0, 4), (1, 3)]
    for j, (a, b) in enumerate(rows):
        for i in range(a, b):
            cv.set(x + i, bottom - len(rows) + j, ramp[2] if i == a and j < 3 else ramp[1] if i < b - 1 else ramp[0])
    cv.set(x + 1, bottom - 6, ramp[1])
    cv.set(x + 2, bottom - 6, ramp[0])
    cv.set(x + 4, bottom - 4, ramp[0])


# ================================================================ market designs

def sail_stall(spec):
    """A cloth sheet tied between four poles with pennants, guy ropes out to the sides; under it
    a weapon rack and armour stands, or bolts of cloth, or pottery."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = CLOTH[spec.get("cloth", "blue")]
    pad = 8
    w = spec.get("width", 64)
    W, H = w + pad * 2, 74
    base = H - 6
    x0, x1 = pad, pad + w
    cv = Canvas(W, H)
    bx0, bx1 = x0 + 8, x1 - 10  # back poles
    for px in (bx0, bx1):
        pole(cv, px, 10, base - 14)
        pennant(cv, px, 10, CLOTH["red"], right=px > W // 2)
    goods = spec.get("goods", "weapons")
    if goods == "weapons":
        weapon_rack(cv, rnd, bx0 + 4, bx1 - 2, base - 9)
        table_cloth(cv, x0 + 14, x1 - 14, base - 10, 9, CLOTH["red"])
        blade(cv, x0 + 20, base - 22, base - 9, "sword")
        shield(cv, x1 - 22, base - 14, CLOTH["blue"])
        for x in range(x0 + 26, x0 + 38):  # a sword laid on the table
            cv.set(x, base - 9, STEEL[3] if x < x0 + 34 else "#6b3c17")
        cv.set(x0 + 33, base - 10, GOLD[3])
        cv.set(x0 + 33, base - 8, GOLD[2])
        armour_stand(cv, x0 + 6, base)
        armour_stand(cv, x1 - 7, base, plume=CLOTH["blue"])
    elif goods == "cloth":
        for i, c in enumerate(("red", "ochre", "teal", "purple", "green")):  # hanging lengths of cloth
            r = CLOTH[c]
            length = 13 + (i * 5) % 7
            for y in range(base - 30, base - 30 + length):
                for k in range(5):
                    fold = (k + (y - base) // 3) % 5
                    cv.set(bx0 + 3 + i * 7 + k, y, r[4] if k == 0 else r[3] if fold < 2 else r[2] if k < 4 else r[1])
            for k in range(0, 5, 2):  # fringe
                cv.set(bx0 + 3 + i * 7 + k, base - 30 + length, r[3])
        for x in range(bx0 + 2, bx1):
            cv.set(x, base - 31, DARKWOOD[4])
        table_cloth(cv, x0 + 8, x1 - 8, base - 10, 9, CLOTH["green"])
        x = x0 + 10
        for c in ("blue", "red", "ochre", "teal", "purple", "red", "green"):  # rolls seen end on
            r = CLOTH[c]
            if x > x1 - 14:
                break
            for j in range(4):
                for i in range(4):
                    if (i, j) in ((0, 0), (3, 0), (0, 3), (3, 3)):
                        continue
                    cv.set(x + i, base - 14 + j, r[3] if i + j < 3 else r[2] if (i, j) != (1, 1) else r[0])
            x += 5
        sack(cv, x0 + 1, base)
    else:  # pottery
        for sy in (base - 22, base - 12):
            for x in range(bx0 + 1, bx1 + 1):
                cv.set(x, sy, DARKWOOD[5])
                cv.set(x, sy + 1, DARKWOOD[2])
            x = bx0 + 3
            while x < bx1 - 4:
                ramps = [("#5b3a22", "#8f5a33", "#c0814d"), ("#1e4a4a", "#2f7472", "#5aa6a0"), ("#5a2a20", "#9a4a36", "#cf7a5c")]
                jug(cv, x, sy, ramps[rnd.randrange(3)])
                x += 6
        pole(cv, bx0 + 1, base - 22, base - 8)
        pole(cv, bx1 - 1, base - 22, base - 8)
        for k in range(3):
            jug(cv, x0 + 4 + k * 6, base, [("#5b3a22", "#8f5a33", "#c0814d"), ("#1e4a4a", "#2f7472", "#5aa6a0")][k % 2])
    draped_canopy(cv, x0 + 1, x1 - 1, 10, 19, 3, 12, ramp)
    for px in (x0, x1 - 2):  # front poles
        pole(cv, px, 18, base)
        pennant(cv, px, 18, CLOTH["red"], right=px > W // 2)
    cv.outline()
    rope(cv, x0 - 1, 20, 1, base - 1, 1.0)  # guy ropes out to pegs
    rope(cv, x1, 20, W - 2, base - 1, 1.0)
    return _result(cv, "stall", (W // 2, base), [x0 - W // 2, -12, w, 12])


def sign_stall(spec):
    """A produce stand: a long counter of bins heaped with fruit and vegetables under a big painted
    signboard held up on forked branches, with crates and baskets set out in front."""
    rnd = random.Random(spec.get("seed", 1))
    w = spec.get("width", 70)
    W, H = w + 8, 62
    base = H - 5
    x0, x1 = 4, 4 + w
    cv = Canvas(W, H)
    for px in (x0 + 1, x1 - 3):
        forked_pole(cv, px, 4, base)
    # the signboard: two planks with ragged ends, painted lettering, nails
    sy = 8
    for y in range(sy, sy + 10):
        for x in range(x0 - 2, x1 + 2):
            ragged = (x < x0 + 1 and (y - sy) % 5 in (0, 4)) or (x > x1 - 1 and (y - sy) % 5 in (0, 4))
            if ragged:
                continue
            k = (y - sy) % 5
            c = "#e9cf94" if k == 0 else "#7a5a32" if k == 4 else "#d8b77a" if (x * 3 + y) % 11 else "#c4a066"
            cv.set(x, y, c)
    for x in range(x0 + 6, x1 - 6):  # lettering
        if (x // 3) % 4 != 3 and ((x * 7) % 5) != 0:
            cv.set(x, sy + 3, "#5a2f1a")
            if (x % 3) == 0:
                cv.set(x, sy + 4, "#5a2f1a")
    for x, y in ((x0, sy + 2), (x1 - 1, sy + 2), (x0, sy + 7), (x1 - 1, sy + 7)):
        cv.set(x, y, IRON[1])
    # counter with produce bins
    ct = base - 13
    kinds = spec.get("goods", ["apples", "grapes", "cabbage", "oranges", "carrots"])
    bins = len(kinds)
    bw = (w - 8) // bins
    for b, kind in enumerate(kinds):
        bx = x0 + 4 + b * bw
        heap(cv, rnd, bx + 1, bx + bw, ct, kind, rows=3)
    for y in range(ct, base):
        for x in range(x0 + 2, x1 - 2):
            k = (x - x0) % 6
            c = DARKWOOD[5] if y == ct else DARKWOOD[4] if y == ct + 1 else (DARKWOOD[1] if k == 5 else DARKWOOD[3] if k == 0 else DARKWOOD[2])
            if y == base - 1:
                c = DARKWOOD[1]
            cv.set(x, y, c)
    for b in range(1, bins):  # dividers between the bins
        bx = x0 + 4 + b * bw
        for y in range(ct - 3, ct + 1):
            cv.set(bx, y, DARKWOOD[4])
    # out in front: a crate of melons, a crate of pumpkins, a basket, a little barrel
    front = spec.get("front", ["melon", "pumpkin"])
    crate(cv, rnd, x0 + 2, base + 3, w=12, h=7)
    heap(cv, rnd, x0 + 3, x0 + 14, base - 3, front[0], rows=1)
    crate(cv, rnd, x0 + 16, base + 3, w=12, h=7)
    heap(cv, rnd, x0 + 17, x0 + 28, base - 3, front[1], rows=1)
    basket(cv, rnd, x1 - 22, base + 3, 9, kinds[0])
    barrel(cv, x1 - 10, base + 3, w=7, h=9)
    cv.outline()
    return _result(cv, "stall", (W // 2, base), [x0 - W // 2 + 2, -11, w - 4, 11])


def table_stall(spec):
    """Bakes on a long table under a white cloth, a striped awning on four thin posts above,
    baskets and sacks around and a little chalkboard."""
    from buildings import awning
    rnd = random.Random(spec.get("seed", 1))
    w = spec.get("width", 60)
    W, H = w + 8, 54
    base = H - 5
    x0, x1 = 4, 4 + w
    cv = Canvas(W, H)
    for px in (x0 + 3, x1 - 5):  # back posts
        pole(cv, px, 10, base - 12)
    tt = base - 12
    table_cloth(cv, x0 + 2, x1 - 2, tt, 11, spec.get("cloth") and CLOTH[spec["cloth"]] or WHITE)
    goods = spec.get("goods", ["bread", "pie", "bun"])
    x = x0 + 5
    k = 0
    while x < x1 - 7:
        g = goods[k % len(goods)]
        # a wooden board or plate under each
        for i in range(-1, 5):
            cv.set(x + i, tt + 1, "#b98a52" if g == "bread" else WHITE[1])
        if g == "pie":
            for i in range(5):
                cv.set(x + i - 1, tt, "#c9862e")
                cv.set(x + i - 1, tt - 1, "#e8b25e" if i < 3 else "#c9862e")
            cv.set(x + 1, tt - 1, "#8a3a2a")
            cv.set(x + 2, tt - 2, "#e8b25e")
        elif g == "bun":
            for bx in (0, 3):
                cv.set(x + bx, tt, "#c98a42")
                cv.set(x + bx + 1, tt, "#a86c30")
                cv.set(x + bx, tt - 1, "#efc27a")
                cv.set(x + bx + 1, tt - 1, "#c98a42")
            cv.set(x + 1, tt - 2, "#efc27a")
            cv.set(x + 2, tt - 2, "#c98a42")
        elif g == "cake":
            for j in range(4):
                for i in range(5):
                    cv.set(x + i - 1, tt - j, "#fbeee0" if j == 3 else "#f2a7b5" if j == 1 else "#e8d0b0")
            cv.set(x + 1, tt - 4, "#d8333a")
        else:
            item(cv, x, tt + 1, "bread")
            item(cv, x + 1, tt - 1, "bread")
        x += 7
        k += 1
    awning(cv, x0, x1, 6, 9, spec.get("awning", "red"))
    for px in (x0, x1 - 2):  # front posts
        pole(cv, px, 18, base)
    basket(cv, rnd, x0 + 1, base + 3, 8, spec.get("basket", "apples"))
    sack(cv, x0 + 10, base + 3)
    # chalkboard on an easel
    bx = x1 - 10
    for y in range(base - 7, base + 3):
        for x in range(bx, bx + 8):
            edge = x in (bx, bx + 7) or y in (base - 7, base + 2)
            cv.set(x, y, WOOD[4] if edge else "#2f3a36")
    for x in range(bx + 2, bx + 6):
        cv.set(x, base - 4, WHITE[3])
        if x % 2:
            cv.set(x, base - 2, WHITE[2])
    cv.outline()
    return _result(cv, "stall", (W // 2, base), [x0 - W // 2 + 2, -10, w - 4, 10])


def pavilion(spec):
    """A fortune teller's pointed tent: striped cloth sweeping down from a gold finial, a moon
    and star on the front, the flaps tied back on a dim inside with a crystal ball, candles and
    potions on a draped table, and a patterned rug laid out in front."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = CLOTH[spec.get("cloth", "purple")]
    W, H = 72, 86
    base = H - 9
    cx = W // 2
    cv = Canvas(W, H)
    apex = 8
    eave = 36
    half = 30
    # roof: a cone of stripes radiating from the finial, lit on the left
    for y in range(apex, eave + 1):
        t = (y - apex) / (eave - apex)
        hw = 3 + (half - 3) * (t ** 0.85)
        for x in range(round(cx - hw), round(cx + hw) + 1):
            s = (x - cx) / max(1.0, hw)
            band = math.floor((s + 1) * 5.0) % 2
            r = ramp if band == 0 else WHITE
            v = 0.62 - 0.38 * s - 0.08 * t
            if abs(((s + 1) * 5.0) % 1.0 - 0.5) > 0.42:
                v -= 0.2  # seams
            cv.set(x, y, r[tone(r, v)])
    # scalloped valance with gold trim
    for x in range(cx - half - 1, cx + half + 2):
        k = (x - cx + 100) % 6
        depth = 4 - abs(k - 3) // 1
        r = ramp if ((x - cx + 100) // 6) % 2 == 0 else WHITE
        cv.set(x, eave + 1, GOLD[3] if x < cx else GOLD[2])
        for i in range(depth):
            cv.set(x, eave + 2 + i, r[2] if i < depth - 1 else r[1])
    # walls: curtains down to the ground, tied back to open a doorway in the middle
    wall_l, wall_r = cx - half + 2, cx + half - 2
    for y in range(eave + 2, base):
        t = (y - eave) / (base - eave)
        open_hw = 4 + 10 * min(1.0, t * 1.6)  # the doorway widens toward the ground
        for x in range(wall_l, wall_r + 1):
            if abs(x - cx) < open_hw:
                continue
            k = (x - wall_l) % 6
            band = ((x - wall_l) // 6) % 2
            r = ramp if band == 0 else WHITE
            v = 0.55 - 0.3 * (x - wall_l) / (wall_r - wall_l) + (0.12 if k < 2 else -0.1 if k > 4 else 0)
            near = abs(abs(x - cx) - open_hw)
            if near < 2:
                v -= 0.15  # folds bunched at the tie-back
            cv.set(x, y, r[tone(r, v)])
    # the dim inside, a draped table with a crystal ball, candles, potions
    for y in range(eave + 6, base):
        t = (y - eave) / (base - eave)
        open_hw = 4 + 10 * min(1.0, t * 1.6)
        for x in range(round(cx - open_hw), round(cx + open_hw)):
            if not cv.get(x, y)[3]:
                cv.set(x, y, "#2a1f33" if y < base - 10 else "#3a2b40")
    for side in (-1, 1):  # gold tie-backs
        tx = cx + side * 13
        for i in range(3):
            cv.set(tx + side * i, eave + 22 + i, GOLD[3])
    table_cloth(cv, cx - 10, cx + 10, base - 9, 8, ramp)
    crystal_ball(cv, cx, base - 9)
    candle(cv, cx - 7, base - 9, 3)
    candle(cv, cx + 7, base - 9, 4)
    for i, k in enumerate(("potion_r", "potion_g")):
        item(cv, cx - 5 + i * 9, base - 9, k)
    # emblem: a moon and a star on the front of the roof
    my = eave - 12
    for y in range(my - 4, my + 5):
        for x in range(cx - 4, cx + 5):
            d1 = (x - cx) ** 2 + (y - my) ** 2
            d2 = (x - cx - 2) ** 2 + (y - my + 1) ** 2
            if d1 <= 16 and d2 > 9:
                cv.set(x, y, GOLD[4] if x < cx - 1 else GOLD[3])
    for dx, dy in ((5, -4), (4, -4), (6, -4), (5, -5), (5, -3)):
        cv.set(cx + dx, my + dy, GOLD[4])
    # finial and pennant
    for y in range(apex - 6, apex):
        cv.set(cx, y, GOLD[3] if y > apex - 4 else GOLD[2])
    cv.set(cx, apex - 7, GOLD[4])
    pennant(cv, cx, apex - 5, CLOTH["ochre"], right=True)
    # a rug laid out in front of the doorway
    rug(cv, cx - 12, cx + 12, base, base + 7, CLOTH["red"])
    # tent pegs and ropes
    _ = rnd
    cv.outline()
    rope(cv, cx - half, eave + 3, 2, base + 2, 1.5)
    rope(cv, cx + half, eave + 3, W - 3, base + 2, 1.5)
    return _result(cv, "stall", (W // 2, base), [wall_l - W // 2, -14, wall_r - wall_l, 14])


def wagon(spec):
    """A merchant's covered wagon side on: big spoked wheels, a plank bed, an arched canvas cover
    on ribs with its side rolled up over shelves of wares, shafts out in front, a lantern."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = CLOTH[spec.get("cloth", "green")] if spec.get("cloth") else WHITE
    W, H = 86, 58
    base = H - 2
    cv = Canvas(W, H)
    bed_x0, bed_x1 = 20, W - 6
    bed_top, bed_bot = base - 22, base - 12
    # shafts to the front (left)
    for x in range(2, bed_x0 + 2):
        y = bed_bot - 3 + (bed_x0 - x) // 6
        cv.set(x, y, WOOD[5])
        cv.set(x, y + 1, WOOD[2])
    # cover: arched canvas over ribs
    ctop = 6
    for x in range(bed_x0 - 1, bed_x1 + 1):
        u = (x - bed_x0 + 1) / (bed_x1 - bed_x0 + 1)
        arch = ctop + round(9 * (1 - math.sin(u * math.pi)) ** 1.5)
        for y in range(arch, bed_top - 9):
            t = (y - arch) / max(1, bed_top - 9 - arch)
            v = 0.72 - 0.25 * t - 0.2 * u
            if (x - bed_x0) % 11 == 0:
                v -= 0.25  # ribs under the canvas
            cv.set(x, y, ramp[tone(ramp, v)])
        cv.set(x, arch, ramp[4])
    # the rolled-up side of the cover and the shelves of wares below it
    roll = bed_top - 9
    for x in range(bed_x0, bed_x1):
        cv.set(x, roll, ramp[3])
        cv.set(x, roll + 1, ramp[2])
        cv.set(x, roll + 2, ramp[1])
    for y in range(roll + 3, bed_top):
        for x in range(bed_x0 + 1, bed_x1 - 1):
            cv.set(x, y, "#2e2420")
    for x in range(bed_x0 + 2, bed_x1 - 2):  # shelf
        cv.set(x, bed_top - 3, WOOD[4])
    x = bed_x0 + 3
    kinds = spec.get("goods", ["potion_r", "potion_b", "potion_g"])
    while x < bed_x1 - 4:
        item(cv, x, bed_top - 3, kinds[rnd.randrange(len(kinds))])
        x += 3
    x = bed_x0 + 3
    while x < bed_x1 - 6:
        jug(cv, x, bed_top, [("#5b3a22", "#8f5a33", "#c0814d"), ("#1e4a4a", "#2f7472", "#5aa6a0")][(x // 7) % 2])
        x += 7
    for y in range(roll + 3, bed_top):  # corner posts of the bed
        cv.set(bed_x0, y, WOOD[4])
        cv.set(bed_x1 - 1, y, WOOD[2])
    # the bed: planks with iron straps
    for y in range(bed_top, bed_bot):
        for x in range(bed_x0, bed_x1):
            k = (y - bed_top) % 4
            c = WOOD[5] if k == 0 else WOOD[1] if k == 3 else WOOD[3] if x < (bed_x0 + bed_x1) // 2 + 8 else WOOD[2]
            if (x - bed_x0) % 16 in (0, 1):
                c = IRON[2] if k < 2 else IRON[1]
            cv.set(x, y, c)
    # wheels
    r = 8
    for wx in (bed_x0 + 11, bed_x1 - 11):
        wheel(cv, wx, base - r - 1, r)
    # lantern hanging at the front, a barrel strapped at the back
    lantern(cv, bed_x0 - 3, roll - 4)
    if spec.get("barrel"):
        barrel(cv, bed_x1 - 2, bed_top + 2, w=7, h=9)
    cv.outline()
    return _result(cv, "stall", (W // 2, base), [bed_x0 - W // 2, -12, bed_x1 - bed_x0, 12])


# ================================================================ props

def prop_weapon_rack(spec):
    rnd = random.Random(spec.get("seed", 1))
    cv = Canvas(30, 30)
    base = 27
    weapon_rack(cv, rnd, 3, 27, base)
    shield(cv, 25, base - 12, CLOTH[spec.get("cloth", "red")])
    cv.outline()
    return _result(cv, "prop", (15, base), [-12, -4, 24, 4])


def prop_armour(spec):
    cv = Canvas(16, 34)
    base = 32
    armour_stand(cv, 7, base, plume=CLOTH[spec.get("cloth", "red")])
    cv.outline()
    return _result(cv, "prop", (8, base), [-4, -3, 8, 3])


def prop_banner(spec):
    cv = Canvas(18, 40)
    base = 38
    banner(cv, 7, base, CLOTH[spec.get("cloth", "red")], h=34)
    cv.outline()
    return _result(cv, "prop", (8, base), [-2, -2, 4, 2])


def prop_dining(spec):
    """A round table under a cloth, stools round it and a meal on it."""
    cv = Canvas(40, 28)
    base = 24
    cxm = 20
    stool(cv, cxm - 17, base - 4)  # stools behind and at the sides
    stool(cv, cxm + 13, base - 4)
    stool(cv, cxm - 2, base - 13)
    for y in range(base - 13, base - 1):  # the round table: a lit top and the cloth falling in folds
        t = y - (base - 13)
        hw = 9 if t > 1 else 8
        for x in range(cxm - hw, cxm + hw + 1):
            if t < 5:
                d = ((x - cxm) / 9.0) ** 2 + ((t - 2.5) / 2.6) ** 2
                if d > 1.0:
                    continue
                c = WHITE[4] if x < cxm and t < 3 else WHITE[3]
            else:
                c = WHITE[3] if (x - cxm) % 4 == 0 else WHITE[1] if (x - cxm) % 4 == 3 else WHITE[2]
                if abs(x - cxm) == hw:
                    c = WHITE[1]
            cv.set(x, y, c)
    for x in range(cxm - 8, cxm + 9):
        if (x - cxm) % 4 in (1, 2):
            cv.set(x, base - 1, WHITE[1])
    for i in range(6):  # a roast on a plate, and a mug
        cv.set(cxm - 4 + i, base - 10, WHITE[1])
    for i, c in enumerate(("#a8522a", "#d27a3a", "#e89a52", "#d27a3a")):
        cv.set(cxm - 3 + i, base - 11, c)
        cv.set(cxm - 3 + i, base - 12, c if i < 3 else "#a8522a")
    cv.set(cxm - 2, base - 13, "#f0c070")
    cv.set(cxm + 4, base - 12, "#c9862e")
    cv.set(cxm + 5, base - 12, "#8a5a1e")
    cv.set(cxm + 4, base - 13, WHITE[4])
    stool(cv, cxm - 2, base + 3)  # and one in front
    cv.outline()
    return _result(cv, "prop", (cxm, base), [-10, -7, 20, 7])


def prop_barrels(spec):
    cv = Canvas(30, 26)
    base = 23
    barrel(cv, 3, base, w=8, h=10)
    barrel(cv, 13, base, w=8, h=10)
    barrel(cv, 8, base - 10, w=8, h=10)
    sack(cv, 22, base)
    cv.outline()
    return _result(cv, "prop", (15, base), [-12, -5, 24, 5])


def prop_crates(spec):
    rnd = random.Random(spec.get("seed", 1))
    cv = Canvas(32, 28)
    base = 25
    crate(cv, rnd, 2, base, w=12, h=9)
    crate(cv, rnd, 14, base, w=11, h=8)
    crate(cv, rnd, 5, base - 9, w=10, h=8)
    sack(cv, 25, base)
    jug(cv, 18, base - 8)
    cv.outline()
    return _result(cv, "prop", (16, base), [-13, -5, 26, 5])


def prop_rug(spec):
    cv = Canvas(30, 14)
    rug(cv, 2, 28, 2, 12, CLOTH[spec.get("cloth", "red")])
    return _result(cv, "rug", (15, 12), [-13, -10, 26, 10])


def prop_well(spec):
    """A stone well: a ring of stones, a little shingle roof on two posts, a crank and a bucket."""
    from buildings import roof_shingles, ROOFS
    cv = Canvas(34, 46)
    base = 42
    cxm = 17
    # posts
    for px in (cxm - 12, cxm + 10):
        pole(cv, px, 12, base - 6)
    # the stone ring: front face with courses curving round, the dark water opening on top
    for y in range(base - 16, base):
        for x in range(cxm - 12, cxm + 13):
            u = (x - cxm) / 12.5
            curve = round(2.5 * math.sqrt(max(0.0, 1 - u * u)))
            if y < base - 12 + curve - 3:
                continue
            k = (y - curve) % 4
            sx = (x + ((y - curve) // 4) * 3) % 6
            c = STONE[1] if k == 3 or sx == 5 else STONE[tone(STONE, 0.7 - 0.45 * (u + 1) / 2)]
            cv.set(x, y, c)
    for y in range(base - 18, base - 12):  # rim and opening, seen from above
        for x in range(cxm - 12, cxm + 13):
            dx, dy = (x - cxm) / 12.5, (y - (base - 15)) / 3.2
            if dx * dx + dy * dy <= 1.0:
                inner = (x - cxm) ** 2 / 90 + (y - (base - 15)) ** 2 / 4.0 <= 1.0
                cv.set(x, y, "#1f2b33" if inner else STONE[5] if y < base - 15 else STONE[4])
    # crank axle and bucket
    for x in range(cxm - 11, cxm + 11):
        cv.set(x, 17, DARKWOOD[4])
    for y in range(18, base - 18):
        cv.set(cxm + 2, y, ROPE)
    for y in range(base - 24, base - 19):
        for x in range(cxm, cxm + 5):
            cv.set(x, y, WOOD[4] if x < cxm + 3 else WOOD[2])
    cv.set(cxm, base - 24, IRON[2])
    cv.set(cxm + 4, base - 24, IRON[2])
    cv.set(cxm + 12, 17, DARKWOOD[5])
    cv.set(cxm + 13, 18, DARKWOOD[4])
    roof_shingles(cv, 41, 2, 32, 6, 16, ROOFS["rust"])
    cv.outline()
    return _result(cv, "prop", (cxm, base), [-12, -10, 25, 10])


DESIGNS = {
    "sail_stall": sail_stall, "sign_stall": sign_stall, "table_stall": table_stall, "pavilion": pavilion,
    "wagon": wagon, "weapon_rack": prop_weapon_rack, "armour": prop_armour, "banner": prop_banner,
    "dining": prop_dining, "barrels": prop_barrels, "crates": prop_crates, "rug": prop_rug, "well": prop_well,
}
