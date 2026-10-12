"""Palettes and small 2D parts for the market (market3d.py): pennants, guy ropes, heaps of
produce, baskets, swords, spears and axes, shields, armour stands, banners, a crystal ball,
candles and jugs; and the two props that stay flat, an armour stand and a banner."""

from buildings import DARKWOOD, LIT, WOOD, Canvas, _result

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


def jug(cv, x, bottom, ramp=("#5b3a22", "#8f5a33", "#c0814d")):
    rows = [(1, 3), (0, 4), (0, 4), (0, 4), (1, 3)]
    for j, (a, b) in enumerate(rows):
        for i in range(a, b):
            cv.set(x + i, bottom - len(rows) + j, ramp[2] if i == a and j < 3 else ramp[1] if i < b - 1 else ramp[0])
    cv.set(x + 1, bottom - 6, ramp[1])
    cv.set(x + 2, bottom - 6, ramp[0])
    cv.set(x + 4, bottom - 4, ramp[0])


# ================================================================ market designs


# ================================================================ props


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


