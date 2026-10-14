"""Public buildings of the town modelled in 3D for the oblique renderer (oblique.py), in the idiom
of town3d.py: a stone chapel with its steeple and bell, a clinic, a library, a small museum
behind a portico, the town hall with its clock and flag, a stable, a harbour warehouse, a clock
tower and a fountain in the square (its falling water an animated part).

Each design builds a Scene of solids, renders it, then draws the 2D details (doors, stained
glass, clock faces, signs, books, a horse looking out...) onto the walls and tops they belong
to. World units are pixels; x right, y back, z up; the base point is the middle of the front
wall at ground level (the fountain: the middle of its basin's front edge)."""
import math
import random

import materials as M
from buildings import (C, DARKWOOD, FIELDSTONE, IRON, LEAF, LIT, PAINT, ROOFS, STONE, TRIM, WOOD, door, flower_box,
                       lantern, sack, window)
from landmarks import HAY, WHITE_TRIM
from market import CLOTH, GOLD, rope
from oblique import Mat, Scene, box, frustum, gable_x, gable_y, hsh, prism, pyramid, roof_shell_y, slab
from PIL import Image
from town3d import chimney, done, fp, footing, gable_front, hip_roof, step

GROUP = "公共建筑"

# ================================================================ palettes (dark -> light)

SANDSTONE = ["#2e2620", "#4f4236", "#71604e", "#8f7c66", "#ab9880", "#c6b49a", "#ddd0b8"]
MARBLE = ["#3a3632", "#76706a", "#a19b92", "#c3beb3", "#dad6cc", "#ebe8e0", "#f8f6f1"]
WHITEWASH = ["#3a3633", "#8a857c", "#bab4a8", "#d9d4c9", "#ebe7de", "#f6f3ec", "#fdfcf8"]
BRICK = ["#2a1512", "#4a231c", "#6c3326", "#874230", "#a0553d", "#b86c50", "#cf8c6c"]
VERDIGRIS = ["#16302c", "#22493f", "#2f6455", "#40806b", "#5a9c84", "#7fb9a0", "#aad4bf"]
STABLE_WOOD = ["#24170f", "#3b2618", "#553722", "#6d482c", "#865b38", "#a07248", "#b98d60"]
WATER = ["#1b4561", "#2a6587", "#3f86aa", "#62a9c8", "#93cfe2", "#c9eef6", "#ffffff"]
TERRACOTTA = ["#3d1f10", "#6e3e24", "#9a5a36", "#b9774a", "#d0956a"]
BRONZE = ["#3a2510", "#6b4a1e", "#9c7030", "#c99a4a", "#ecc778"]
LEAD = "#2a2430"
GLASS_DAY = {"r": ["#5a1a24", "#9a2a34", "#d0504a"], "b": ["#1a2a5a", "#2c4a9a", "#5a7ad0"],
             "g": ["#7a5a10", "#c09a2a", "#f0d060"], "e": ["#1a4a2a", "#2e7a44", "#5aae6a"]}
GLASS_NIGHT = {"r": ["#a02403", "#e84a03", "#ff8a03"], "b": None,
               "g": ["#c08a03", "#ffc803", "#fff003"], "e": ["#6a9a03", "#9ad003", "#d0f003"]}


def _t(ramp, v):
    from buildings import tone
    return ramp[tone(ramp, v)]


def _step(ramp, v, k):
    from buildings import tone
    return ramp[max(1, min(len(ramp) - 1, tone(ramp, v) + k))]


# ================================================================ materials

def brick(ramp=BRICK, seed=1, bias=0.1, mortar=("#6e6258", "#9a8e80", "#b9ad9c")):
    """Brick in courses of three px (two of brick, one of mortar), bricks six long, staggered."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + bias - 0.05)
        row = math.floor(v / 3)
        k = v - row * 3
        off = 3 if row % 2 else 0
        seg = math.floor((u + off) / 6)
        uu = (u + off) - seg * 6
        if k < 1 or uu < 1:
            return mortar[min(2, max(0, round(light * 2.4)))]
        lv = light + bias + (hsh(row, seg, seed) - 0.5) * 0.22
        if k >= 2 and uu >= 5:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def ashlar(ramp=MARBLE, h=6, w=12, seed=1, bias=0.12):
    """Large smooth blocks of pale stone with thin joints."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            u, v = P[0], P[1]
        row = math.floor(v / h)
        k = v - row * h
        off = (w // 2) if row % 2 else 0
        seg = math.floor((u + off) / w)
        uu = (u + off) - seg * w
        lv = light + bias + (hsh(row, seg, seed) - 0.5) * 0.08
        if k < 1 or uu < 1:
            return _step(ramp, lv, -1)
        if k >= h - 1:
            return _step(ramp, lv, 1) if kind != "top" else _t(ramp, lv)
        return _t(ramp, lv)
    return Mat(f)


def fluted(ramp=MARBLE, bias=0.15):
    """A column's shaft: flutes every two px round it."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + bias)
        if (u % 2.2) < 0.8:
            return _step(ramp, light + bias, -1)
        return _t(ramp, light + bias)
    return Mat(f)


def basin(ramp=STONE, rim=3, seed=1, water_top=True):
    """A round basin: stone courses round the side; on top the rim stones and water inside with
    rings of ripples and a few sparkles."""
    side = M.dressed_stone(ramp, h=4, seed=seed, bias=0.12)

    def f(u, v, kind, light, P, s):
        if kind != "top":
            return side.fn(u, v, kind, light, P, s)
        cx, cy = s.params["cx"], s.params["cy"]
        r = s.params.get("rtop", s.params["r"])
        dd = math.hypot(P[0] - cx, P[1] - cy)
        if dd > r - rim or not water_top:
            seg = math.floor(math.atan2(P[1] - cy, P[0] - cx) * r / 5)
            if dd > r - 0.9:
                return ramp[5]
            return ramp[4] if seg % 2 else ramp[5]
        if dd > r - rim - 1:
            return WATER[1]  # the water's edge in the rim's shadow
        ring = (dd * 0.8 + hsh(math.floor(P[0] / 4), math.floor(P[1] / 4), seed) * 0.8) % 4.5
        sp = hsh(math.floor(P[0]), math.floor(P[1]), seed + 7)
        if sp < 0.018:
            return WATER[6]
        if ring < 0.8:
            return WATER[4]
        return WATER[3] if (P[0] - cx) + (P[1] - cy) * 0.6 < 0 else WATER[2]
    return Mat(f)


def hay_bale(seed=1):
    """A bale of hay: straw lines along it, twine bands, a lit top."""
    def f(u, v, kind, light, P, s):
        x0 = s.bbox[0]
        if kind != "top" and ((P[0] - x0) % 8) in (2, 2.5) or (kind != "top" and 2 <= (P[0] - x0) % 8 < 3):
            return "#7a5a2a"
        lv = light + 0.1 + (hsh(math.floor(u), math.floor(v / 2), seed) - 0.5) * 0.3
        return HAY[max(0, min(4, round(lv * 4)))]
    return Mat(f)


# ================================================================ 2D parts

def glow(cv, x, y, c):
    """Light a pixel at night only where its day pixel was drawn (it is not hidden)."""
    if cv._ok(int(x), int(y)):
        cv.lit(x, y, c)


def _pointed(x, y, x0, x1, ys):
    """Inside an equilateral pointed arch over x0..x1 springing at ys (and the jambs below)."""
    px, py = x + 0.5, y + 0.5
    if py >= ys:
        return x0 <= px <= x1
    w = x1 - x0
    return (px - x0) ** 2 + (py - ys) ** 2 <= w * w and (px - x1) ** 2 + (py - ys) ** 2 <= w * w


def _glass_pixel(cv, x, y, key, shade, lit=True):
    day = GLASS_DAY[key]
    cv.set(x, y, day[shade])
    if lit and GLASS_NIGHT[key]:
        glow(cv, x, y, GLASS_NIGHT[key][shade])


def lancet(cv, cx, top, w, h, frame=SANDSTONE, seed=1, keys="rbgbe"):
    """A tall pointed window of stained glass in a stone frame (top = the arch's apex)."""
    x0, x1 = cx - w / 2, cx + w / 2
    ys = top + w * 0.87
    bottom = top + h
    for y in range(top - 2, bottom + 2):
        for x in range(math.floor(x0) - 2, math.ceil(x1) + 2):
            if _pointed(x, y, x0 - 1.5, x1 + 1.5, ys) and not _pointed(x, y, x0, x1, ys) and y < bottom + 1:
                cv.set(x, y, frame[5] if x < cx else frame[3])
    for y in range(top, bottom):
        for x in range(math.floor(x0), math.ceil(x1)):
            if not _pointed(x, y, x0, x1, ys):
                continue
            lx, ly = x - math.floor(x0), y - top
            if (lx + ly) % 4 == 0 or (lx - ly) % 4 == 0 or x == math.floor(cx):
                cv.set(x, y, LEAD)
                continue
            cell = (math.floor((lx + ly) / 4), math.floor((lx - ly) / 4))
            key = keys[int(hsh(cell[0], cell[1], seed) * len(keys))]
            shade = 2 if ly < h * 0.35 else 1
            if (lx + ly) % 4 == 1 and ly < h * 0.6:
                shade = 2
            _glass_pixel(cv, x, y, key, shade)
    for x in range(math.floor(x0) - 2, math.ceil(x1) + 2):  # sill
        cv.set(x, bottom, frame[5] if x < x1 else frame[4])
        cv.set(x, bottom + 1, frame[1])


def rose_window(cv, cx, cy, R, frame=SANDSTONE, seed=1):
    """A round window of stained glass: a stone ring, tracery spokes, petals of coloured glass
    round a gold centre."""
    for y in range(cy - R - 2, cy + R + 3):
        for x in range(cx - R - 2, cx + R + 3):
            dx, dy = x + 0.5 - (cx + 0.5), y + 0.5 - (cy + 0.5)
            d = math.hypot(dx, dy)
            if d > R + 1.6:
                continue
            if d > R - 0.4:
                cv.set(x, y, frame[5] if dx + dy < 0 else frame[3])
                continue
            a = math.atan2(dy, dx)
            sector = (a + math.pi) / (2 * math.pi) * 8
            if d < 1.5:
                _glass_pixel(cv, x, y, "g", 2)
                continue
            if abs(sector - round(sector)) * (d * 2 * math.pi / 8) < 0.55 or abs(d - R * 0.48) < 0.6:
                cv.set(x, y, LEAD)
                continue
            if d < R * 0.48:
                key = "r" if int(sector) % 2 else "g"
            else:
                key = "b" if int(sector) % 2 else "r"
            shade = 2 if dy < -1 else 1
            if d > R - 1.6:
                shade = 0
            _glass_pixel(cv, x, y, key, shade)


def arched_double_door(cv, cx, bottom, w=18, h=24, wood=DARKWOOD, frame=SANDSTONE, pointed=False):
    """Two leaves under a round (or pointed) arch in a ring of stone voussoirs, iron strap hinges
    and ring handles."""
    x0, x1 = cx - w / 2, cx + w / 2
    top = bottom - h
    ys = top + (w * 0.87 if pointed else w / 2)

    def inside(x, y, grow=0.0):
        if pointed:
            return _pointed(x, y, x0 - grow, x1 + grow, ys)
        px, py = x + 0.5, y + 0.5
        if py >= ys:
            return x0 - grow <= px <= x1 + grow
        return (px - cx) ** 2 + (py - ys) ** 2 <= (w / 2 + grow) ** 2

    for y in range(top - 4, bottom):  # the stone ring round the arch, the jambs
        for x in range(math.floor(x0) - 3, math.ceil(x1) + 3):
            if inside(x, y, 2.6) and not inside(x, y):
                a = math.atan2(y + 0.5 - ys, x + 0.5 - cx)
                joint = y < ys and (int((a + math.pi) * 5) % 2 == 0) and inside(x, y, 1.4)
                c = frame[5] if x < cx - 2 else frame[4] if x < cx + 3 else frame[3]
                if joint or (y >= ys and (y - top) % 5 == 0):
                    c = frame[2]
                cv.set(x, y, c)
    for y in range(top, bottom):
        for x in range(math.floor(x0), math.ceil(x1)):
            if not inside(x, y):
                continue
            k = (x - math.floor(x0)) % 3
            c = wood[3] if k == 0 else wood[1] if k == 2 else wood[2]
            if x in (math.floor(cx) - 1, math.floor(cx)):
                c = wood[0] if x == math.floor(cx) else wood[1]
            cv.set(x, y, c)
    for hy in (top + h // 3, bottom - 5):  # strap hinges
        for x in range(math.floor(x0), math.ceil(x1)):
            if inside(x, hy) and abs(x + 0.5 - cx) > 1.5:
                cv.set(x, hy, IRON[1])
                if abs(x + 0.5 - cx) > w / 2 - 3:
                    cv.set(x, hy + 1, IRON[2])
    for hx in (math.floor(cx) - 3, math.floor(cx) + 2):
        cv.set(hx, bottom - h // 2 + 1, GOLD[3])
        cv.set(hx, bottom - h // 2 + 2, GOLD[1])
    for x in range(math.floor(x0), math.ceil(x1)):  # the arch shades the top of the leaves
        for y in range(top, bottom):
            if inside(x, y):
                cv.darken(x, y, 0.5)
                if inside(x, y - 1):
                    pass
                break
    for y in range(top, bottom):
        if inside(math.floor(x0), y):
            cv.darken(math.floor(x0), y, 0.35)


def bell(cv, cx, top, w=7, h=7, ramp=BRONZE):
    """A bronze bell hanging from a yoke at `top`."""
    for x in range(cx - w // 2 - 1, cx + w // 2 + 2):
        cv.set(x, top, DARKWOOD[3])
    cv.set(cx, top + 1, IRON[1])
    for j in range(h):
        t = j / max(1, h - 1)
        half = 1.2 + (w / 2 - 1.2) * (t ** 1.6) + (0.8 if j == h - 1 else 0)
        for x in range(cx - math.ceil(half), cx + math.ceil(half) + 1):
            dx = x - cx
            if abs(dx) > half + 0.3:
                continue
            c = ramp[4] if dx < -half * 0.3 and j < h - 1 else ramp[3] if dx < half * 0.35 else ramp[2]
            if j == h - 1:
                c = ramp[1] if dx > 0 else ramp[2]
            cv.set(x, top + 2 + j, c)
    cv.set(cx, top + h + 2, ramp[1])


def cross(cv, x, y, h=7, arm=2, c1=GOLD[3], c2=GOLD[1]):
    """A small cross standing on (x, y)."""
    for yy in range(y - h, y):
        cv.set(x, yy, c1)
        cv.set(x + 1, yy, c2)
    for xx in range(x - arm, x + arm + 2):
        cv.set(xx, y - h + 2, c1 if xx <= x else c2)


def clock_face(cv, cx, cy, R, hour=10, minute=2, lit=True, rim=GOLD, face="#f3ead2"):
    """A round clock face: a gold rim, twelve ticks, two hands; at night the face glows."""
    for y in range(cy - R - 1, cy + R + 2):
        for x in range(cx - R - 1, cx + R + 2):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d > R + 0.5:
                continue
            if d > R - 1.0:
                cv.set(x, y, rim[3] if dx + dy < 0 else rim[1])
                continue
            c = face if dx + dy < R * 0.6 else "#ddd0b0"
            cv.set(x, y, c)
            glow(cv, x, y, LIT[3] if d < R - 2.5 else LIT[2])
    for k in range(12):
        a = k * math.pi / 6
        rr = R - 1.8
        tx, ty = round(cx + math.sin(a) * rr), round(cy - math.cos(a) * rr)
        cv.set(tx, ty, "#2a2430")
        glow(cv, tx, ty, LIT[0])
    for frac, length, col in ((hour / 12, R * 0.5, "#1c1a1f"), (minute / 12, R * 0.78, "#2a2430")):
        a = frac * 2 * math.pi
        for i in range(1, int(length * 2) + 1):
            s = i / 2
            hx, hy = round(cx + math.sin(a) * s), round(cy - math.cos(a) * s)
            cv.set(hx, hy, col)
            glow(cv, hx, hy, LIT[0])
    cv.set(cx, cy, GOLD[3])
    glow(cv, cx, cy, LIT[1])


ICONS = {  # 7x7 icons for signs: . clear, d dark, m mid, l light, w white, g green
    "book": [".......", "dmmmmd.", "dlwwld.", "dlwwld.", "dlwwld.", "dmmmmd.", ".ddddd."],
    "cross": ["..ggg..", "..glg..", "ggglggg", "glllllg", "ggglggg", "..glg..", "..ggg.."],
    "leaf": ["....gg.", "...glg.", "..glgg.", ".glgg..", ".ggg...", ".g.....", "d......"],
}


def sign_icon(cv, x, y, name, ramp=None):
    d, m, l = ramp or ("#5a1a24", "#9a2a34", "#e8d8b8")
    for j, row in enumerate(ICONS[name]):
        for i, ch in enumerate(row):
            c = {"d": d, "m": m, "l": l, "w": "#fbf7ee", "g": "#3a9a4a"}.get(ch)
            if name == "cross" and ch == "l":
                c = "#7ad07a"
            if c:
                cv.set(x + i, y + j, c)


def plaque(cv, x0, x1, y, icon_name, ramp, board=TRIM, h=11, letters=True):
    """A signboard with a border, an icon on the left and painted lettering."""
    for yy in range(y, y + h):
        for xx in range(x0, x1):
            edge = xx in (x0, x1 - 1) or yy in (y, y + h - 1)
            cv.set(xx, yy, board[1] if edge else board[3] if yy == y + 1 else board[2])
    sign_icon(cv, x0 + 2, y + 2, icon_name, ramp)
    if letters:
        for xx in range(x0 + 11, x1 - 3):
            if (xx * 7) % 5 != 0:
                cv.set(xx, y + 4, board[0])
                if (xx * 3) % 4 == 0:
                    cv.set(xx, y + 6, board[0])
            if xx % 4 != 0 and xx < x1 - 6:
                cv.set(xx, y + 7, board[1])


def bookshelf_window(cv, rnd, cx, top, w, h, frame=TRIM, arch=True):
    """A tall window, arched at the top, with shelves of books seen through the glass."""
    x0, x1 = cx - w // 2, cx - w // 2 + w
    bottom = top + h

    def inside(x, y, grow=0):
        if not arch or y >= top + w // 2:
            return x0 - grow <= x < x1 + grow
        r = w / 2 + grow
        return (x + 0.5 - (x0 + w / 2)) ** 2 + (y + 0.5 - (top + w / 2)) ** 2 <= r * r

    for y in range(top - 1, bottom + 1):
        for x in range(x0 - 1, x1 + 1):
            if inside(x, y, 1) and not inside(x, y):
                cv.set(x, y, frame[3] if x < cx else frame[1])
    books = ["#8a2a2a", "#2a4a8a", "#2a6a3a", "#b08a2a", "#6a3a7a", "#a85a2a", "#d8c8a0"]
    shelf_ys = list(range(top + w // 2 + 1, bottom, 6))
    for y in range(top, bottom):
        for x in range(x0, x1):
            if not inside(x, y):
                continue
            c = "#2a2230"
            gl = LIT[1]
            under = [s for s in shelf_ys if s <= y]
            if under and y - under[-1] in (1, 2, 3, 4, 5) and y > top + w // 2:
                sb = under[-1]
                k = hsh(x, sb, 3)
                tall = 5 if k > 0.3 else 4
                if y - sb >= 6 - tall:
                    c = books[int(hsh(x, sb, 9) * len(books))]
                    if x % 3 == 0:
                        c = _dim(c)
                    gl = LIT[0] if x % 2 else LIT[1]
            if y in shelf_ys:
                c, gl = WOOD[4], LIT[1]
            cv.set(x, y, c)
            glow(cv, x, y, gl)
    for y in range(top, bottom):  # the glazing bars and glints over the books
        for x in range(x0, x1):
            if not inside(x, y):
                continue
            if x == cx or (y - top) == w // 2:
                cv.set(x, y, frame[2])
                glow(cv, x, y, LIT[0])
            elif (x - x0 + y - top) % 11 in (2,) and y < top + h * 0.6:
                cv.set(x, y, "#c9e6f0")
    for x in range(x0 - 2, x1 + 2):
        cv.set(x, bottom + 1, frame[4] if x < x1 else frame[3])
        cv.set(x, bottom + 2, frame[1])
    _ = rnd


def _dim(c):
    r, g, b, a = C(c)
    return (r * 3 // 4, g * 3 // 4, b * 3 // 4, a)


def tall_window(cv, rnd, cx, top, w, h, frame=TRIM, arch=True, panes=3, lit=True, sill=True):
    """A tall sash window, arched or square-headed, glazing bars in a grid."""
    x0, x1 = cx - w // 2, cx - w // 2 + w
    bottom = top + h
    from buildings import GLASS

    def inside(x, y, grow=0):
        if not arch or y >= top + w // 2:
            return x0 - grow <= x < x1 + grow
        r = w / 2 + grow
        return (x + 0.5 - (x0 + w / 2)) ** 2 + (y + 0.5 - (top + w / 2)) ** 2 <= r * r

    for y in range(top - 1, bottom + 1):
        for x in range(x0 - 1, x1 + 1):
            if inside(x, y, 1) and not inside(x, y):
                cv.set(x, y, frame[3] if (x < cx and y < bottom) else frame[1])
    rows = [top + (w // 2 if arch else 0) + (h - (w // 2 if arch else 0)) * i // panes for i in range(1, panes)]
    for y in range(top, bottom):
        for x in range(x0, x1):
            if not inside(x, y):
                continue
            lx, ly = x - x0, y - top
            if x == x0 + w // 2 or y in rows or (arch and y == top + w // 2):
                cv.set(x, y, frame[2])
                continue
            glint = (lx + ly) % 9 in (3, 4) and ly < h * 0.55
            v = 0.7 - 0.5 * ly / h
            c = GLASS[4] if glint else GLASS[max(1, min(3, round(1 + v * 2.4)))]
            if not inside(x, y - 1) or y - 1 in rows:
                c = GLASS[0]
            cv.set(x, y, c)
            if lit:
                glow(cv, x, y, LIT[3] if ly < h * 0.45 else LIT[2])
    if sill:
        for x in range(x0 - 2, x1 + 2):
            cv.set(x, bottom + 1, frame[4] if x < x1 else frame[3])
            cv.set(x, bottom + 2, frame[1])
    _ = rnd


def ivy(cv, rnd, x, y_bottom, height, spread=2.5):
    for k in range(height):
        xx = x + round(spread * math.sin(k * 0.23 + x))
        for dx in (-1, 0, 1):
            if rnd.random() < 0.55:
                cv.set(xx + dx, y_bottom - k, LEAF[rnd.randint(0, 2)])


BUSH = ["#132a19", "#1d3b1e", "#2d5a2c", "#3f7a37", "#5fa047", "#86c25a", "#b0dc7c"]


def leafy(ramp=BUSH, seed=1):
    """Foliage: clumps of leaves lit from the upper left, a few dark gaps between them."""
    def f(u, v, kind, light, P, s):
        cl = hsh(math.floor(P[0] / 2), math.floor(P[2] / 2 + P[1] * 0.3), seed)
        lv = light + 0.05 + (cl - 0.5) * 0.35
        if hsh(math.floor(P[0]), math.floor(P[2] + P[1] * 0.8), seed + 3) < 0.1:
            return ramp[1]
        return _t(ramp, lv)
    return Mat(f)


def bush(S, x, y, r=5, h=9, seed=1):
    """A round shrub: a short drum of leaves rounding off into a dome."""
    m = leafy(seed=seed)
    S.add(prism(x, y, r, 0, h * 0.45, m, sides=10))
    S.add(frustum(x, y, r, r * 0.7, h * 0.45, h * 0.8, m, sides=10))
    S.add(frustum(x, y, r * 0.7, r * 0.2, h * 0.8, h, m, sides=10))


def shrub2d(cv, cx, bottom, r, ramp=BUSH, seed=1, flowers=None):
    """A small round shrub drawn flat: leaf clumps lit from the upper left, an optional
    sprinkle of blooms."""
    cy = bottom - r
    for y in range(cy - r - 1, bottom):
        for x in range(cx - r - 2, cx + r + 2):
            dx, dy = (x + 0.5 - cx) / (r + 0.8), (y + 0.5 - cy) / (r + 0.3)
            if dx * dx + dy * dy > 1.0 - 0.25 * hsh(x // 2, y // 2, seed):
                continue
            n = hsh(x // 2, (y + x // 3) // 2, seed + 1)
            lv = 0.5 - dx * 0.45 - dy * 0.55 + (n - 0.5) * 0.5
            c = ramp[max(1, min(len(ramp) - 1, 2 + round(lv * 3.2)))]
            if flowers and hsh(x, y, seed + 9) < 0.09 and dy < 0.6:
                c = flowers
            cv.set(x, y, c)


def pot2d(cv, cx, bottom, w=7, h=5, ramp=TERRACOTTA):
    for j in range(h):
        half = w / 2 - (0 if j < 1 else 0.5 + j * 0.25)
        for x in range(round(cx - half), round(cx + half)):
            c = ramp[4] if j == 0 else ramp[3] if x < cx - 1 else ramp[2] if x < cx + 1 else ramp[1]
            cv.set(x, bottom - h + j, c)


def keep_lit(cv, fn, *a, **k):
    """Call a 2D part from buildings.py, then take back the night glow it put where its wall is
    hidden (behind a porch, a post...): those parts light every pixel they try to draw."""
    import numpy as np
    before = np.array(cv.night)
    fn(cv, *a, **k)
    after = np.array(cv.night)
    ys, xs = np.nonzero(np.any(after != before, axis=2))
    for y, x in zip(ys, xs):
        if not cv._ok(int(x), int(y)):
            cv.npx[int(x), int(y)] = tuple(int(v) for v in before[y, x])


def flowers_on(cv, rnd, x0, x1, y, pal=None):
    """A row of blooms (on a bush top or a bed) between x0 and x1 at screen row y."""
    from buildings import FLOWER
    pal = pal or FLOWER[rnd.randrange(len(FLOWER))]
    for _ in range(max(1, (x1 - x0) // 3)):
        fx, fy = rnd.randint(x0, x1 - 1), y + rnd.randint(-1, 2)
        cv.set(fx, fy, pal[0])
        if rnd.random() < 0.4:
            cv.set(fx, fy - 1, pal[1])


# ================================================================ designs

def chapel(spec):
    """A small stone chapel: a long nave under a steep slate roof with its gable to the street, a
    rose window in the gable over an arched double door up a flight of steps, lancet windows of
    stained glass, buttresses; beside it a square bell tower with an open belfry, its bell, corner
    pinnacles and a tall octagonal spire with a gold cross."""
    rnd = random.Random(spec.get("seed", 1))
    stone = SANDSTONE
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=31, moss=0.04)
    d, wall_h = 56, 30
    nx0, nx1 = -24, 24
    tx0, tx1, ty0, ty1 = -43, -26, -3, 14
    tcx, tcy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    S = Scene(pad_top=12)
    footing(S, nx0, nx1, 0, d)
    S.add(box(nx0, nx1, 0, d, 4, wall_h, M.dressed_stone(stone, seed=31)))
    zr_w, zr = gable_front(S, nx0, nx1, 0, d, wall_h, 1.15, rm, M.dressed_stone(stone, seed=32), over=3)
    for bx in (nx1 - 4,):  # buttress on the open corner, with a sloping cap
        S.add(box(bx, bx + 6, -5, 0, 0, 20, M.dressed_stone(stone, seed=33, bias=0.15)))
        S.add(slab(bx - 0.5, bx + 6.5, -5.5, 0, 19, 24, 2, M.dressed_stone(stone, seed=34, bias=0.2)))
    # the tower: a plinth, the shaft, a string course, the belfry between two cornices, the spire
    S.add(box(tx0 - 1, tx1 + 1, ty0 - 1, ty1 + 1, 0, 6, M.dressed_stone(stone, seed=35, bias=0.15)))
    S.add(box(tx0, tx1, ty0, ty1, 6, 66, M.dressed_stone(stone, seed=36)))
    S.add(box(tx0 - 1, tx1 + 1, ty0 - 1, ty1 + 1, 40, 42, M.dressed_stone(stone, seed=37, bias=0.25)))
    S.add(box(tx0 - 1.5, tx1 + 1.5, ty0 - 1.5, ty1 + 1.5, 64, 67, M.dressed_stone(stone, seed=38, bias=0.25)))
    S.add(box(tx0, tx1, ty0, ty1, 67, 82, M.dressed_stone(stone, seed=39)))
    S.add(box(tx0 - 1.5, tx1 + 1.5, ty0 - 1.5, ty1 + 1.5, 82, 85, M.dressed_stone(stone, seed=40, bias=0.25)))
    spire_top = 123
    S.add(frustum(tcx, tcy, 9.6, 0.3, 85, spire_top, M.shingles(roof, seed=41, row_h=3), sides=8, ze=85, zr=spire_top))
    for px in (tx0 + 0.5, tx1 - 0.5):  # pinnacles at the front corners
        S.add(pyramid(px, ty0 + 0.5, 1.8, 85, 93, M.flat(stone), sides=6))
    # steps up to the door
    step(S, 0, w=28, depth=9, h=2)
    step(S, 0, w=23, depth=5, z=2, h=2)
    cv = S.render((0, 0, 0, 0))
    # nave front: the door, lancets, the rose window
    cv.on_wall(0)
    arched_double_door(cv, S.sx(0), S.sy(0, 4), w=18, h=25, wood=DARKWOOD, frame=stone, pointed=True)
    for lx in (-15.5, 15.5):
        lancet(cv, S.sx(lx), S.sy(0, 27), 6, 17, frame=stone, seed=7 + int(lx))
    cv.on_wall(0, tol=2.0)
    rose_window(cv, S.sx(0), S.sy(0, wall_h + 13), 8, frame=stone, seed=3)
    # tower front: a lancet, a slit, the open belfry with the bell
    cv.on_wall(ty0)
    lancet(cv, S.sx(tcx), S.sy(ty0, 33), 5, 13, frame=stone, seed=11)
    for y in range(S.sy(ty0, 58), S.sy(ty0, 50)):
        cv.set(S.sx(tcx), y, "#1f1a1c")
        cv.set(S.sx(tcx) - 1, y, stone[5])
    bx0, bx1 = S.sx(tcx - 5), S.sx(tcx + 5)
    btop = S.sy(ty0, 80)
    bbot = S.sy(ty0, 67)
    for y in range(btop, bbot):
        for x in range(bx0, bx1):
            if _pointed(x, y, bx0, bx1, btop + 9):
                cv.set(x, y, "#231d22" if y > btop + 3 else "#2e262b")
    bell(cv, S.sx(tcx), btop + 3, w=7, h=6)
    for x in range(bx0 - 1, bx1 + 1):  # louvre sill
        cv.set(x, bbot, stone[5])
        cv.set(x, bbot + 1, stone[2])
    cv.free()
    # a gold cross on the spire, a stone cross on the gable
    sx_, sy_ = S.s(tcx, tcy, spire_top)
    cross(cv, sx_, sy_ + 1, h=9, arm=2)
    gx, gy = S.s(0, -3, zr)
    cross(cv, gx, gy + 1, h=6, arm=2, c1=stone[5], c2=stone[3])
    # ivy on the tower, flowers on the bushes
    ivy(cv, rnd, S.sx(tx1 - 3), S.sy(ty0 - 1, 6), 26)
    cv.at_depth(-9)
    shrub2d(cv, S.sx(-18), S.sy(-6, 0), 4, seed=4, flowers="#ff9ec4")
    shrub2d(cv, S.sx(19), S.sy(-9, 0), 4, seed=5, flowers="#ffffff")
    return done(S, cv, "house", fp(tx0, nx1, d), 0, door_w=18)


GREEN_TRIM = ["#14302a", "#1f4a3c", "#2d6650", "#3f8266", "#5a9e80", "#80bc9e", "#a6d6bc"]
WHITE_WOOD = ["#4a4640", "#8a857c", "#bdb7ab", "#dcd7cc", "#eeebe3", "#f8f6f0", "#ffffff"]


def _awning_ramps(colour):
    from buildings import CANVAS
    a, b = CANVAS[colour]
    pad = lambda r: [r[0], r[0], r[1], r[2], r[3], r[3]]
    return pad(a), pad(b)


def valance(cv, S, x0, x1, y, z, ramp_a, ramp_b, w=4):
    """Points of cloth hanging from the front edge of an awning at (y, z)."""
    cv.at_depth(y - 0.5)
    sy = S.sy(y, z)
    for x in range(S.sx(x0), S.sx(x1)):
        k = (x - S.sx(x0)) % w
        r = ramp_a if ((x - S.sx(x0)) // w) % 2 == 0 else ramp_b
        n = 3 if 0 < k < w - 1 else 2
        for i in range(n):
            cv.set(x, sy + i, r[3] if i == 0 else r[2] if i < n - 1 else r[1])


def round_sign(cv, cx, cy, R, icon_name, ramp, rim=GREEN_TRIM):
    """A round signboard: a painted rim round a white disc with an icon."""
    for y in range(cy - R, cy + R + 1):
        for x in range(cx - R, cx + R + 1):
            d = math.hypot(x - cx, y - cy)
            if d > R + 0.4:
                continue
            cv.set(x, y, (rim[4] if x + y < cx + cy else rim[2]) if d > R - 1.2 else "#f6f3ec" if x + y < cx + cy + 2 else "#ddd8cc")
    sign_icon(cv, cx - 3, cy - 3, icon_name, ramp)


def bracket_sign(cv, x_wall, y, icon_name, ramp, side=1, board=TRIM):
    """An iron bracket out from the wall with a board hanging under it showing an icon."""
    for i in range(12):
        cv.set(x_wall + side * i, y, IRON[1])
    cv.set(x_wall + side * 11, y - 1, IRON[2])
    for i in range(4):  # a little scroll under the bracket
        cv.set(x_wall + side * i, y + 3 - i, IRON[1])
    bx = x_wall + side * 2 if side > 0 else x_wall - 13
    for cx in (bx + 1, bx + 9):
        cv.set(cx, y + 1, IRON[2])
    for yy in range(y + 2, y + 13):
        for xx in range(bx, bx + 11):
            edge = xx in (bx, bx + 10) or yy in (y + 2, y + 12)
            cv.set(xx, yy, board[1] if edge else board[4] if yy == y + 3 else board[3])
    sign_icon(cv, bx + 2, y + 4, icon_name, ramp)


def herbs(cv, rnd, x0, x1, bottom, h=5):
    """A row of herbs: green sprigs with lavender and white flowers."""
    for x in range(x0, x1):
        top = bottom - rnd.randint(2, h)
        for y in range(top, bottom):
            cv.set(x, y, LEAF[2] if y == top else LEAF[rnd.randint(0, 1)])
        if rnd.random() < 0.35:
            cv.set(x, top - 1, "#a78ad8" if rnd.random() < 0.6 else "#f6f3ec")


def bench3d(S, x0, x1, y, z=0, wood=WOOD):
    """A slatted bench with a back, facing the street, its back at y."""
    S.add(box(x0, x1, y - 4, y - 1, z + 5, z + 6.5, M.planks(wood, h=2, seed=5, bias=0.2)))
    for lx in (x0 + 1, x1 - 2.5):
        S.add(box(lx, lx + 1.5, y - 4, y - 2.5, z, z + 5, M.wood(DARKWOOD, bias=0.1)))
        S.add(box(lx, lx + 1.5, y - 1, y, z, z + 11, M.wood(DARKWOOD, bias=0.1)))
    S.add(box(x0, x1, y - 1, y, z + 8, z + 11, M.planks(wood, h=2, seed=6, bias=0.2)))


# ---------------------------------------------------------------- clinic

def clinic(spec):
    """A tidy clinic: white plaster under a hipped roof, green corner boards, an entrance porch on
    white posts with a green cross in its pediment, a hanging sign, windows under green and white
    awnings with flower boxes, a bench and a bed of herbs, a lantern by the glazed door."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = 78, 42, 33
    h2 = ww / 2
    roof = ROOFS[spec.get("roof_colour", "teal")]
    rm = M.shingles(roof, seed=51, moss=0.02)
    wall = M.plaster(WHITEWASH, seed=51, bias=0.1)
    S = Scene()
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, wall_h, wall))
    for px in (-h2 - 1, h2 - 3):  # painted corner boards
        S.add(box(px, px + 4, -1, d + 1, 4, wall_h, M.wood(GREEN_TRIM, bias=0.05)))
    S.add(box(-h2 - 1, h2 + 1, -1, d + 1, wall_h - 2, wall_h, M.wood(GREEN_TRIM, bias=0.1)))  # eaves board
    zr = hip_roof(S, -h2 - 5, h2 + 5, -5, d + 5, wall_h, 0.58, 16, rm)
    chims = [chimney(S, h2 - 14, d * 0.6, wall_h, zr + 8)]
    # the porch: a stone floor, two white posts, a fascia board carrying the sign, a gabled roof
    S.add(box(-14, 14, -13, 0, 0, 3, M.dressed_stone(STONE, seed=52, bias=0.2)))
    for px in (-13, 10):
        S.add(box(px, px + 3, -12, -9, 3, 26, M.wood(WHITE_WOOD, bias=0.1)))
    S.add(box(-14, 14, -12.5, 0, 26, 34, M.wood(WHITE_WOOD, bias=0.1)))
    gable_front(S, -14, 14, -12.5, 0, 34, 0.75, rm, M.plaster(WHITEWASH, seed=53, bias=0.15), over=2, th=2)
    # awnings over the windows
    aw = spec.get("awning", "green")
    a, b = _awning_ramps(aw)
    for wx in (-25, 25):
        S.add(slab(wx - 9, wx + 9, -6, 0, 24, 29, 1.5, M.stripes(a, b, w=3)))
    # a bench under the right window, a bed of herbs under the left
    bench3d(S, 16, 34, -1.5)
    S.add(box(-35, -16, -6, -1, 0, 4, M.planks(WOOD, h=2, seed=54)))
    cv = S.render()
    cv.on_wall(0)
    keep_lit(cv, door, rnd, S.sx(0), S.sy(0, 3), style="glazed", wood=GREEN_TRIM, step=False)
    for wx in (-25, 25):
        window(cv, rnd, S.sx(wx), S.sy(0, 22), w=14, h=12, frame=WHITE_TRIM + ["#ffffff"], box=True)
    keep_lit(cv, lantern, S.sx(-10), S.sy(0, 22))
    cv.on_wall(-12.5)
    fy = S.sy(-12.5, 33)
    x0, x1 = S.sx(-12), S.sx(12)
    for y in range(fy, fy + 7):  # the sign on the fascia: a green cross on white, lettering
        for x in range(x0, x1):
            edge = y in (fy, fy + 6) or x in (x0, x1 - 1)
            cv.set(x, y, GREEN_TRIM[2] if edge else "#f6f3ec" if y < fy + 3 else "#e6e1d6")
    cx_, cy_ = x0 + 4, fy + 3
    for dx in range(-2, 3):
        for dy in range(-1, 2):
            cv.set(cx_ + dx, cy_ + dy, "#2f9a4a")
            cv.set(cx_ + dy, cy_ + dx, "#2f9a4a")
    cv.set(cx_ - 1, cy_ - 1, "#7ad07a")
    cv.set(cx_, cy_ - 2, "#7ad07a")
    for x in range(x0 + 9, x1 - 2):
        if (x * 7) % 5 != 0:
            cv.set(x, fy + 2, GREEN_TRIM[1])
        if (x * 3) % 4 != 0 and x < x1 - 5:
            cv.set(x, fy + 4, GREEN_TRIM[3])
    cv.on_wall(-12.5, tol=2.0)
    round_sign(cv, S.sx(0), S.sy(-12.5, 39), 3, "leaf", None)
    cv.free()
    for wx in (-25, 25):
        valance(cv, S, wx - 9, wx + 9, -6, 24, a, b, w=3)
    cv.free()
    bracket_sign(cv, S.sx(-h2 - 1), S.sy(-1, 29), "cross", None, side=-1, board=WHITE_TRIM + ["#ffffff"])
    cv.at_depth(-6.5)
    herbs(cv, rnd, S.sx(-34), S.sx(-17), S.sy(-6, 4) + 1)
    return done(S, cv, "house", fp(-h2, h2, d), 0, chims=chims)


# ---------------------------------------------------------------- library

def library(spec):
    """A two-storey library: a stone ground floor with tall arched windows, shelves of books
    behind two of them, brick above between stone quoins, a cornice and a hipped slate roof with
    a little copper-domed cupola; the door between pilasters under an entablature that carries
    the sign with a book on it, and a pediment; steps, lanterns, potted bays."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d = 96, 50
    h2 = ww / 2
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=61, moss=0.03)
    pale = M.dressed_stone(MARBLE, h=4, seed=64, bias=0.2)
    S = Scene(pad_top=10)
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, 31, M.dressed_stone(STONE, seed=61)))
    S.add(box(-h2 - 1, h2 + 1, -1.5, d + 1, 31, 33, M.dressed_stone(MARBLE, seed=62, bias=0.25)))  # string course
    S.add(box(-h2, h2, 0, d, 33, 56, brick(seed=63)))
    for px in (-h2 - 0.5, h2 - 3.5):  # quoins
        S.add(box(px, px + 4, -0.5, d + 0.5, 33, 56, pale))
    S.add(box(-h2 - 1.5, h2 + 1.5, -2, d + 1.5, 56, 59, M.dressed_stone(MARBLE, seed=65, bias=0.25)))  # cornice
    zr = hip_roof(S, -h2 - 4, h2 + 4, -4, d + 4, 59, 0.5, 20, rm)
    chims = [chimney(S, -h2 + 12, d * 0.6, 59, zr + 6), chimney(S, h2 - 12, d * 0.6, 59, zr + 6)]
    # the cupola on the ridge
    cy = d / 2
    S.add(box(-7, 7, cy - 7, cy + 7, zr - 6, zr + 2, M.wood(WHITE_WOOD, bias=0.1)))
    S.add(prism(0, cy, 5.5, zr + 2, zr + 10, M.plaster(WHITEWASH, seed=66), sides=8))
    S.add(frustum(0, cy, 7, 6.6, zr + 10, zr + 11.5, M.flat(VERDIGRIS, 0.1), sides=8))
    S.add(frustum(0, cy, 6.2, 4.6, zr + 11.5, zr + 14, M.flat(VERDIGRIS), sides=8))
    S.add(frustum(0, cy, 4.6, 0.8, zr + 14, zr + 17, M.flat(VERDIGRIS), sides=8))
    # the entrance: pilasters, the entablature, a pediment, steps
    for px in (-16.5, 12.5):
        S.add(box(px, px + 4, -2.5, 0, 4, 27, M.dressed_stone(MARBLE, h=5, seed=67, bias=0.2)))
        S.add(box(px - 0.5, px + 4.5, -3, 0, 4, 6.5, M.dressed_stone(MARBLE, seed=68, bias=0.25)))
        S.add(box(px - 0.5, px + 4.5, -3, 0, 25, 27.5, M.dressed_stone(MARBLE, seed=69, bias=0.3)))
    S.add(box(-18, 18, -3.5, 0, 27.5, 37, M.dressed_stone(MARBLE, h=10, seed=70, bias=0.2)))
    S.add(gable_y(-19, 19, -4, 0, 36.5, 37, 37 + 19 * 0.42, M.dressed_stone(MARBLE, seed=71, bias=0.2)))
    step(S, 0, w=32, depth=9, h=2)
    step(S, 0, w=26, depth=5, z=2, h=2)
    cv = S.render()
    cv.on_wall(cy - 5.5, tol=1.2)
    for wx in (-2.6, 2.4):  # the cupola's little arched windows
        for y in range(S.sy(cy - 5.5, zr + 8), S.sy(cy - 5.5, zr + 3)):
            for x in (S.sx(wx), S.sx(wx) + 1):
                cv.set(x, y, "#3f86aa" if y < S.sy(cy - 5.5, zr + 6) else "#2a4a6a")
                glow(cv, x, y, LIT[2])
    cv.free()
    fx_, fy_ = S.s(0, cy, zr + 17)
    for y in range(fy_ - 4, fy_ + 1):
        cv.set(fx_, y, GOLD[3] if y > fy_ - 3 else GOLD[4])
    cv.set(fx_ - 1, fy_ - 2, GOLD[2])
    cv.set(fx_ + 1, fy_ - 2, GOLD[1])
    cv.on_wall(0)
    arched_double_door(cv, S.sx(0), S.sy(0, 4), w=16, h=21, wood=WOOD, frame=MARBLE)
    for wx in (-27, 27):
        bookshelf_window(cv, rnd, S.sx(wx), S.sy(0, 29), 10, 20)
    for wx in (-40, 40):
        tall_window(cv, rnd, S.sx(wx), S.sy(0, 29), 10, 20, frame=TRIM)
    for wx in (-40, -27, 27, 40):
        (bookshelf_window if wx in (-40, 40) else tall_window)(cv, rnd, S.sx(wx), S.sy(0, 53), 9, 15, frame=TRIM)
    lantern(cv, S.sx(-20.5), S.sy(0, 20))
    lantern(cv, S.sx(19), S.sy(0, 20))
    cv.on_wall(0, tol=2.0)
    ox, oy = S.sx(0), S.sy(0, 50)  # a round window over the pediment
    for y in range(oy - 5, oy + 6):
        for x in range(ox - 5, ox + 6):
            dd = math.hypot(x - ox, y - oy)
            if dd <= 4.6:
                cv.set(x, y, MARBLE[5] if dd > 3.4 and x + y < ox + oy else MARBLE[3] if dd > 3.4 else "#36597a" if (x - ox) * (y - oy) else TRIM[2])
                if dd <= 3.4 and (x - ox) * (y - oy):
                    glow(cv, x, y, LIT[2])
    cv.on_wall(-3.5)
    ey = S.sy(-3.5, 37)
    for x in range(S.sx(-16), S.sx(16)):  # the sign along the frieze: a board, a book, lettering
        for y in range(ey + 1, ey + 9):
            edge = y in (ey + 1, ey + 8) or x in (S.sx(-16), S.sx(16) - 1)
            cv.set(x, y, TRIM[1] if edge else TRIM[3] if y == ey + 2 else TRIM[2])
    sign_icon(cv, S.sx(0) - 3, ey + 2, "book", ("#3a1418", "#8a2a2a", "#e8d8b8"))
    for x in list(range(S.sx(-13), S.sx(-5))) + list(range(S.sx(5), S.sx(13))):
        if (x * 7) % 5 != 0:
            cv.set(x, ey + 4, WOOD[1])
            if (x * 3) % 4 == 0:
                cv.set(x, ey + 6, WOOD[1])
    cv.at_depth(-7)
    for px in (-23, 23):  # potted bay trees by the steps
        pot2d(cv, S.sx(px), S.sy(-7, 0), 7, 6)
        shrub2d(cv, S.sx(px), S.sy(-7, 6), 4, seed=px + 50)
    return done(S, cv, "house", fp(-h2, h2, d), 0, door_w=16, chims=chims)




# ---------------------------------------------------------------- museum

def wall_banner(cv, x, top, ramp, w=9, h=22, emblem="star"):
    """A long cloth banner hanging from a gilt rod on a wall, a fringe and a swallowtail."""
    for i in range(-2, w + 2):
        cv.set(x + i, top, GOLD[3] if i < w // 2 else GOLD[2])
    cv.set(x - 2, top - 1, GOLD[4])
    cv.set(x + w + 1, top - 1, GOLD[2])
    for j in range(1, h):
        for i in range(w):
            tail = j - (h - 4)
            if tail > 0 and abs(i - (w - 1) / 2) < tail * 1.2:
                continue
            c = ramp[3] if i < 2 else ramp[2] if i < w - 2 else ramp[1]
            if i in (0, w - 1) or j == 1:
                c = GOLD[2] if i < w - 1 else GOLD[1]
            if j % 7 == 3 and i == w // 2:
                c = ramp[4]
            cv.set(x + i, top + j, c)
    cx, cy = x + w // 2, top + 7
    pts = ((0, -3), (0, -2), (-1, -1), (0, -1), (1, -1), (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0),
           (-1, 1), (0, 1), (1, 1), (-2, 2), (2, 2), (0, 2)) if emblem == "star" else \
        ((-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2), (-2, -1), (2, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
         (-2, 1), (2, 1), (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2))
    for dx, dy in pts:
        cv.set(cx + dx, cy + dy, GOLD[4] if dx + dy < 0 else GOLD[3])


def museum(spec):
    """A small museum with a neoclassical front: a row of six fluted columns on a podium up wide
    steps, under an entablature with an inscription and a triangular pediment with a gilt
    emblem; behind them tall doors and windows in the pale stone hall, long banners on its
    wings, urns at the corners, a low hipped roof of red tiles."""
    rnd = random.Random(spec.get("seed", 1))
    stone = MARBLE
    roof = ROOFS[spec.get("roof_colour", "rust")]
    rm = M.shingles(roof, seed=71, row_h=3)
    hx0, hx1, hy0, hy1 = -48, 48, 13, 60
    px0, px1 = -31, 31
    S = Scene(pad_top=6)
    S.add(box(hx0 - 1, hx1 + 1, hy0 - 1, hy1 + 1, 0, 6, ashlar(stone, h=3, w=9, seed=71, bias=0.05)))
    S.add(box(hx0, hx1, hy0, hy1, 6, 40, ashlar(stone, h=6, w=12, seed=72)))
    S.add(box(hx0 - 1.5, hx1 + 1.5, hy0 - 1.5, hy1 + 1.5, 40, 44, ashlar(stone, h=4, w=40, seed=73, bias=0.22)))
    hip_roof(S, hx0 - 3, hx1 + 3, hy0 - 3, hy1 + 3, 44, 0.42, 18, rm)
    for qx in (hx0, hx1 - 4):  # corner pilasters on the wings
        S.add(box(qx, qx + 4, hy0 - 1, hy1, 6, 40, ashlar(stone, h=40, w=40, seed=74, bias=0.2)))
    # the portico: podium, steps, columns, entablature, pediment
    S.add(box(px0 - 1, px1 + 1, 0, hy0, 0, 6, ashlar(stone, h=3, w=9, seed=75, bias=0.05)))
    for i in range(3):
        S.add(box(px0 + 2, px1 - 2, -3 * (3 - i), 0, 2 * i, 2 * i + 2, M.dressed_stone(stone, h=2, seed=76 + i, bias=0.25)))
    cols = [px0 + 4 + i * (px1 - px0 - 8) / 5 for i in range(6)]
    for cx in cols:
        S.add(box(cx - 3.2, cx + 3.2, 0.5, 6.9, 6, 8, M.flat(stone, 0.15)))
        S.add(prism(cx, 3.7, 2.4, 8, 33, fluted(stone), sides=12))
        S.add(box(cx - 3.4, cx + 3.4, 0.3, 7.1, 33, 35.5, M.flat(stone, 0.2)))
    S.add(box(px0, px1, 0, hy0 + 2, 35.5, 43, ashlar(stone, h=4, w=60, seed=77, bias=0.15)))
    zr_w, zr = gable_front(S, px0, px1, 0, hy0 + 12, 43, 0.4, rm, ashlar(stone, h=40, w=80, seed=78, bias=0.12), over=2)
    cv = S.render()
    # the hall front behind the columns: a tall double door and two windows; banners on the wings
    cv.on_wall(hy0)
    arched_double_door(cv, S.sx(0), S.sy(hy0, 6), w=16, h=26, wood=DARKWOOD, frame=stone)
    for wx in (-15.5, 15.5):
        keep_lit(cv, tall_window, rnd, S.sx(wx), S.sy(hy0, 32), 8, 18, frame=TRIM)
    keep_lit(cv, lantern, S.sx(-11), S.sy(hy0, 24))
    keep_lit(cv, lantern, S.sx(10), S.sy(hy0, 24))
    for bx, col in ((-41, spec.get("banner", "red")), (36, spec.get("banner2", "blue"))):
        wall_banner(cv, S.sx(bx) - 1, S.sy(hy0, 37), CLOTH[col], w=7, h=24, emblem="star" if bx < 0 else "frame")
    # an inscription along the frieze and an emblem in the pediment
    cv.on_wall(0)
    iy = S.sy(0, 41)
    glyphs = ["1101011", "1111001", "1110111", "1011101", "1111001", "1101011"]
    gx = S.sx(0) - len(glyphs) * 4 // 2 + 1
    for g in glyphs:
        for k, bit in enumerate(g):
            if bit == "1":
                cv.set(gx + k % 3, iy + k // 3 * 2 - 1, "#6a6258")
                cv.set(gx + k % 3, iy + k // 3 * 2, "#6a6258")
        gx += 4
    cv.on_wall(0, tol=2.0)
    ex, ey = S.sx(0), S.sy(0, 48)
    for y in range(ey - 3, ey + 4):  # a gilt wreath round a star
        for x in range(ex - 5, ex + 6):
            dd = math.hypot((x - ex) * 0.8, y - ey)
            if 2.6 < dd < 3.8 and y > ey - 3:
                cv.set(x, y, GOLD[3] if x < ex else GOLD[2])
    for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
        cv.set(ex + dx, ey + dy, GOLD[4])
    cv.free()
    cv.at_depth(-10)
    for bx in (px0 - 6, px1 + 6):  # cypress-like bushes by the steps
        pot2d(cv, S.sx(bx), S.sy(-4, 0), 7, 5, ramp=["#3a3632", "#76706a", "#a19b92", "#c3beb3", "#dad6cc"])
        for j in range(14):
            half = 3.2 * math.sin(math.pi * (j + 1) / 15) ** 0.7
            for x in range(round(S.sx(bx) - half), round(S.sx(bx) + half) + 1):
                n = hsh(x, j, 3)
                c = BUSH[4] if x < S.sx(bx) - 0.5 and n > 0.3 else BUSH[3] if x <= S.sx(bx) + 1 else BUSH[2]
                if n < 0.12:
                    c = BUSH[1]
                cv.set(x, S.sy(-4, 5) - 1 - j, c)
    return done(S, cv, "house", fp(hx0, hx1, hy1), 0, door_w=16)


# ---------------------------------------------------------------- town hall

def notice_board(S, x, y, w=14):
    """A notice board on two posts with a little shingled roof, its face at y."""
    for px in (x - w / 2 - 1.5, x + w / 2):
        S.add(box(px, px + 1.5, y, y + 1.5, 0, 21, M.wood(DARKWOOD, bias=0.15)))
    S.add(box(x - w / 2, x + w / 2, y + 0.3, y + 1.3, 8, 19, M.planks(WOOD, h=11, seed=3, bias=0.1)))
    S.add(slab(x - w / 2 - 3, x + w / 2 + 3, y - 2.5, y + 2.5, 20.5, 23, 1.2, M.shingles(ROOFS["bark"], seed=9, row_h=2)))


def notices(cv, rnd, x0, x1, y0, y1):
    """Papers pinned to a board: notes, a poster with a picture, a red seal."""
    papers = ["#f3ecd8", "#e9dfc2", "#f6f0e2", "#efe2b8"]
    x = x0 + 1
    while x < x1 - 3:
        w = rnd.randint(3, 4)
        h = rnd.randint(4, y1 - y0 - 2)
        top = y0 + rnd.randint(1, max(1, y1 - y0 - h - 1))
        p = papers[rnd.randrange(len(papers))]
        for yy in range(top, min(y1, top + h)):
            for xx in range(x, min(x1 - 1, x + w)):
                c = p if xx < x + w - 1 else "#c9bf a6".replace(" ", "")
                cv.set(xx, yy, c)
                if yy > top + 1 and (yy - top) % 2 == 0 and xx < x + w - 1 and rnd.random() < 0.7:
                    cv.set(xx, yy, "#8a8070")
        cv.set(x + w // 2, top, "#c0392b")
        x += w + 1


def town_hall(spec):
    """The town hall, grandest of all and symmetrical: two storeys of pale stone and plaster
    under a long hipped roof, a middle bay that steps forward and rises into a gable holding a
    clock, a cupola with an open lantern and a copper dome on the ridge flying the town flag,
    double doors with a fanlight up wide steps between lanterns, notice boards either side of the
    entrance, tall windows with flower boxes, two chimneys."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d = 124, 56
    h2 = ww / 2
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=81, moss=0.03)
    pal = PAINT[spec.get("plaster", "cream")]
    y0 = 8  # the wings' front wall; the middle bay comes forward to y = 0
    S = Scene(pad_top=12)
    footing(S, -h2, h2, y0, y0 + d)
    S.add(box(-h2, h2, y0, y0 + d, 4, 30, ashlar(STONE, h=5, w=11, seed=81, bias=0.15)))
    S.add(box(-h2 - 1, h2 + 1, y0 - 1.5, y0 + d + 1, 30, 32, M.dressed_stone(MARBLE, seed=82, bias=0.25)))
    S.add(box(-h2, h2, y0, y0 + d, 32, 56, M.plaster(pal, seed=83)))
    for qx in (-h2 - 0.5, -h2 + 31, h2 - 34, h2 - 3.5):  # pilasters on the upper storey
        S.add(box(qx, qx + 3.5, y0 - 1, y0 + d, 32, 56, ashlar(STONE, h=4, w=40, seed=84, bias=0.25)))
    S.add(box(-h2 - 1.5, h2 + 1.5, y0 - 2, y0 + d + 1.5, 56, 59, M.dressed_stone(MARBLE, seed=85, bias=0.25)))
    zr = hip_roof(S, -h2 - 4, h2 + 4, y0 - 4, y0 + d + 4, 59, 0.5, 26, rm)
    chims = [chimney(S, -h2 + 12, y0 + d * 0.6, 59, zr + 6), chimney(S, h2 - 12, y0 + d * 0.6, 59, zr + 6)]
    # the middle bay
    bw = 21
    S.add(box(-bw - 1, bw + 1, -1, y0 + 20, 0, 4, M.dressed_stone(STONE, seed=86)))
    S.add(box(-bw, bw, 0, y0 + 20, 4, 30, ashlar(STONE, h=5, w=11, seed=87, bias=0.15)))
    S.add(box(-bw - 1, bw + 1, -1.5, y0 + 20, 30, 32, M.dressed_stone(MARBLE, seed=88, bias=0.25)))
    S.add(box(-bw, bw, 0, y0 + 20, 32, 63, M.plaster(pal, seed=89)))
    for qx in (-bw - 0.5, bw - 3.5):
        S.add(box(qx, qx + 4, -1, y0 + 20, 4, 63, ashlar(STONE, h=4, w=40, seed=90, bias=0.25)))
    zr_w, zr_b = gable_front(S, -bw, bw, 0, y0 + 24, 63, 0.72, rm, M.plaster(pal, seed=91), over=3)
    # the cupola on the ridge behind: a square base, an open lantern of posts round a bell, a dome
    cy = y0 + d / 2
    white = M.wood(WHITE_WOOD, bias=0.12)
    S.add(box(-8, 8, cy - 8, cy + 8, zr - 6, zr + 4, white))
    S.add(prism(0, cy, 8.6, zr + 4, zr + 5.5, M.wood(WHITE_WOOD, bias=0.25), sides=8))
    S.add(prism(0, cy, 5, zr + 5.5, zr + 14, M.flat(["#1c1820", "#1c1820", "#262028", "#2e2630", "#3a3038", "#3a3038"]), sides=8))
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        S.add(prism(7.2 * math.cos(a), cy + 7.2 * math.sin(a), 1.1, zr + 5.5, zr + 14, white, sides=6))
    S.add(prism(0, cy, 8.6, zr + 14, zr + 15.5, M.wood(WHITE_WOOD, bias=0.25), sides=8))
    S.add(frustum(0, cy, 8.2, 6.6, zr + 15.5, zr + 18.5, M.flat(VERDIGRIS, 0.05), sides=8))
    S.add(frustum(0, cy, 6.6, 3.6, zr + 18.5, zr + 21.5, M.flat(VERDIGRIS), sides=8))
    S.add(frustum(0, cy, 3.6, 0.6, zr + 21.5, zr + 23.5, M.flat(VERDIGRIS), sides=8))
    # steps, notice boards either side of the entrance
    step(S, 0, w=36, depth=9, h=2)
    step(S, 0, w=30, depth=5, z=2, h=2)
    for nx in (-30, 30):
        notice_board(S, nx, -3)
    cv = S.render((0, 0, 4, 0))
    # the bay: double doors with a fanlight, lanterns, three tall windows, the clock in the gable
    cv.on_wall(0)
    dcy = S.sy(0, 28)
    for y in range(dcy - 6, dcy + 1):  # the fanlight over the door
        for x in range(S.sx(-10), S.sx(10)):
            dd = math.hypot(x + 0.5 - S.sx(0), (y + 0.5 - dcy) * 1.4)
            if dd <= 10:
                if dd > 8.6:
                    cv.set(x, y, MARBLE[5] if x < S.sx(0) else MARBLE[3])
                elif int(math.degrees(math.atan2(dcy - y - 0.5, x + 0.5 - S.sx(0))) / 30) % 2 and dd > 2:
                    cv.set(x, y, "#3f6a8a")
                    glow(cv, x, y, LIT[3])
                else:
                    cv.set(x, y, TRIM[2])
    keep_lit(cv, door, rnd, S.sx(0), S.sy(0, 4), w=20, h=22, style="double", wood=DARKWOOD, step=False)
    keep_lit(cv, lantern, S.sx(-14), S.sy(0, 22))
    keep_lit(cv, lantern, S.sx(12), S.sy(0, 22))
    for wx, ww_ in ((-12, 8), (0, 12), (12, 8)):
        keep_lit(cv, tall_window, rnd, S.sx(wx), S.sy(0, 55), ww_, 18, frame=TRIM, arch=wx == 0)
    for wx in (-12, 12):
        flower_box(cv, rnd, S.sx(wx) - 5, S.sx(wx) + 5, S.sy(0, 37) + 1)
    cv.on_wall(0, tol=2.0)
    clock_face(cv, S.sx(0), S.sy(0, 68), 7)
    # the wings: two tall windows a storey, flower boxes upstairs
    cv.on_wall(y0)
    for wx in (-48, -38, 38, 48):
        keep_lit(cv, tall_window, rnd, S.sx(wx), S.sy(y0, 26), 8, 16, frame=TRIM, arch=False)
        keep_lit(cv, tall_window, rnd, S.sx(wx), S.sy(y0, 53), 8, 15, frame=TRIM, arch=False)
        flower_box(cv, rnd, S.sx(wx) - 5, S.sx(wx) + 5, S.sy(y0, 38) + 1)
        for x in range(S.sx(wx) - 5, S.sx(wx) + 6):  # a little cornice over each window
            cv.set(x, S.sy(y0, 27) - 1, MARBLE[5])
            cv.set(x, S.sy(y0, 54) - 1, MARBLE[5])
    # papers on the notice boards
    for nx in (-30, 30):
        cv.on_wall(-3 + 0.3, tol=0.8)
        notices(cv, rnd, S.sx(nx - 7), S.sx(nx + 7), S.sy(-3, 19), S.sy(-3, 8))
    # the bell in the lantern, the flag on the dome
    cv.at_depth(cy - 5.5, tol=1.0)
    bell(cv, S.sx(0), S.sy(cy - 5, zr + 13.5), w=5, h=4)
    cv.free()
    fx_, fy_ = S.s(0, cy, zr + 23.5)
    for y in range(fy_ - 16, fy_ + 1):
        cv.set(fx_, y, IRON[2] if y > fy_ - 15 else GOLD[4])
    flag = CLOTH[spec.get("flag", "blue")]
    for j in range(7):
        for i in range(12):
            wave = round(math.sin(i * 0.55) * 1.0)
            c = flag[3] if j < 2 else flag[2] if j < 5 else flag[1]
            if 4 <= i <= 6 and 2 <= j <= 4:
                c = GOLD[3]
            cv.set(fx_ + 1 + i, fy_ - 14 + j + wave, c)
    return done(S, cv, "house", fp(-h2, h2, y0 + d), 0, door_w=20, chims=chims)


# ---------------------------------------------------------------- stable

CHESTNUT = ["#2a160c", "#5a2e16", "#8a4a22", "#b06a34", "#d08e52"]
GREY_HORSE = ["#3a3634", "#6a6460", "#9a948c", "#c4bfb6", "#e6e2da"]
HORSE = [  # a horse's head looking out over a stable half-door, muzzle to the right
    "...a.a.....",
    "..mhahh....",
    ".mmhhhhh...",
    ".mmhehhhh..",
    "mmmhhhhhhh.",
    "mmmhhhwhhhh",
    "mmhhhhhhhll",
    "mmhhh.hhhnd",
    ".mhhh..hddd",
    ".mhhh......",
    ".mhhhh.....",
]


def horse_head(cv, x, bottom, coat=CHESTNUT, mane="#2a160c", blaze=True, flip=False):
    """A horse looking out of a half-door: head, ears, mane and neck, its bottom at `bottom`."""
    rows = HORSE
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == ".":
                continue
            xx = x + (len(row) - 1 - i if flip else i)
            yy = bottom - len(rows) + j
            c = {"a": coat[1], "m": mane, "h": coat[3] if (i + j) % 5 else coat[2], "e": "#120a08",
                 "w": "#efe8dc" if blaze else coat[3], "l": coat[4], "n": "#120a08", "d": coat[1]}[ch]
            if ch == "h" and i < 5 and j < 4:
                c = coat[4] if not flip else coat[3]
            if ch == "h" and i > 7 and j > 5:
                c = coat[2]
            cv.set(xx, yy, c)


def saddle(cv, x, y):
    """A saddle on a striped blanket thrown over a rail at (x, y): the seat, the horn, a flap and
    a stirrup hanging down."""
    blanket = ["#5a1a1c", "#8c2f30", "#b9443e", "#e8d8b8"]
    leather = ["#3a1c0e", "#6e3a1e", "#9a5a2e", "#c07a44", "#dca06a"]
    for j in range(8):  # the blanket hangs either side of the rail
        for i in range(-1, 12):
            if j > 5 and i in (-1, 11):
                continue
            c = blanket[2] if i < 8 else blanket[1]
            if j in (2, 5):
                c = blanket[3]
            if j == 7:
                c = blanket[0]
            cv.set(x + i, y - 1 + j, c)
    rows = [(3, 8), (1, 10), (1, 10)]
    for j, (a, b) in enumerate(rows):  # the seat with its horn and cantle
        for i in range(a, b):
            c = leather[4] if j == 0 else leather[3] if i < 6 else leather[2]
            cv.set(x + i, y - 3 + j, c)
    cv.set(x + 1, y - 4, leather[3])
    cv.set(x + 1, y - 5, leather[4])
    cv.set(x + 9, y - 4, leather[2])
    for j in range(5):  # the flap
        for i in range(3, 7):
            cv.set(x + i, y + j, leather[2] if i < 6 else leather[1])
    for j in range(5, 9):  # the stirrup leather and iron
        cv.set(x + 5, y + j, leather[1])
    for dx in (4, 6):
        cv.set(x + dx, y + 9, IRON[2])
    for dx in range(4, 7):
        cv.set(x + dx, y + 10, IRON[2])


def trough(seed=1):
    """A wooden water trough: plank sides, water inside the rim on top."""
    sides = M.planks(DARKWOOD, h=3, seed=seed, bias=0.15)

    def f(u, v, kind, light, P, s):
        if kind != "top":
            return sides.fn(u, v, kind, light, P, s)
        x0, x1, y0, y1 = s.bbox[:4]
        if P[0] - x0 < 1.2 or x1 - P[0] < 1.2 or P[1] - y0 < 1.2 or y1 - P[1] < 1.2:
            return DARKWOOD[5]
        if hsh(math.floor(P[0]), math.floor(P[1]), seed) < 0.06:
            return WATER[5]
        return WATER[3] if P[1] - y0 < 2.5 else WATER[2]
    return Mat(f)


def stable(spec):
    """A long timber stable: dark boards on a fieldstone footing under a shingled roof with the
    ridge across, a cross gable in the middle with the hay loft door, hay showing and a hoist beam
    with a pulley and hook, big cross-braced doors under it; a row of half-doors with a horse
    looking out of each of two; hay bales, a water trough, a saddle on a rail, a lantern and a
    horseshoe over the door."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = 110, 40, 35
    h2 = ww / 2
    wood = STABLE_WOOD
    roof = ROOFS[spec.get("roof_colour", "thatch")]
    rm = M.thatch(roof, seed=101) if spec.get("roof_colour", "thatch") == "thatch" else M.shingles(roof, seed=101, moss=0.06)
    walls = M.boards(wood, w=5, seed=102)
    S = Scene(pad_top=8)
    S.add(box(-h2 - 1, h2 + 1, -1, d + 1, 0, 5, M.fieldstone(FIELDSTONE, seed=101)))
    S.add(box(-h2, h2, 0, d, 5, wall_h, walls))
    for px in (-h2 - 1, -29, 26, h2 - 3):
        S.add(box(px, px + 3, -1, d + 1, 5, wall_h, M.wood(TRIM, bias=0.0)))
    over = 5
    bw = 15
    for (rx0, rx1) in ((-h2 - over, -bw), (bw, h2 + over)):  # the roof either side of the loft bay
        S.add(gable_x(rx0, rx1, -over, d + over, wall_h - 4, wall_h, wall_h + (d / 2 + over) * 0.66, rm))
    # the loft bay in the middle, its gable to the street, the hoist beam out of its apex
    S.add(box(-bw - 1, bw + 1, -3, d - 6, 0, 5, M.fieldstone(FIELDSTONE, seed=103)))
    S.add(box(-bw, bw, -2, d - 6, 5, 47, M.boards(wood, w=5, seed=104)))
    for px in (-bw - 1, bw - 2):
        S.add(box(px, px + 3, -3, d - 6, 5, 47, M.wood(TRIM, bias=0.0)))
    zr_w, zr_b = gable_front(S, -bw, bw, -2, d - 6, 47, 0.8, rm, M.boards(wood, w=4, seed=105), over=4, th=4)
    S.add(box(-1.5, 1.5, -12, -2, zr_w - 6, zr_w - 3, M.wood(DARKWOOD, bias=0.15)))
    # hay bales, the trough, the saddle rail, a barrel
    hb = hay_bale(seed=3)
    S.add(box(-h2 - 10, -h2 + 4, -12, -4, 0, 7, hb))
    S.add(box(-h2 + 4, -h2 + 16, -13, -5, 0, 7, hay_bale(seed=4)))
    S.add(box(-h2 - 6, -h2 + 8, -10, -2, 7, 14, hay_bale(seed=5)))
    S.add(box(30, 46, -9, -3, 0, 6, trough(seed=6)))
    for px in (h2 + 4, h2 + 16):
        S.add(box(px, px + 2, -6, -4, 0, 12, M.wood(DARKWOOD, bias=0.15)))
    S.add(box(h2 + 3, h2 + 19, -6, -4.5, 10, 12, M.wood(WOOD, bias=0.2)))
    S.add(prism(-21, -6, 4, 0, 10, M.barrel(seed=8), sides=12))
    cv = S.render((0, 6, 0, 0))
    # big doors in the bay, the loft door above with hay, a horseshoe, a lantern
    cv.on_wall(-2)
    from landmarks import x_door
    base_y = S.sy(-2, 5)
    x_door(cv, S.sx(-11), S.sx(0), base_y - 24, base_y, wood, trim=TRIM)
    x_door(cv, S.sx(0), S.sx(11), base_y - 24, base_y, wood, trim=TRIM)
    for x in range(S.sx(-13), S.sx(13)):
        cv.set(x, base_y - 26, DARKWOOD[5])
        cv.set(x, base_y - 25, DARKWOOD[2])
    hx, hy = S.sx(0), base_y - 30
    for dx, dy in ((-2, 0), (-2, 1), (-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2), (2, 1), (2, 0)):
        cv.set(hx + dx, hy + dy, IRON[2] if dx < 0 else IRON[1])
    cv.on_wall(-2, tol=2.0)
    ly = S.sy(-2, 50)
    for y in range(ly, ly + 12):
        for x in range(S.sx(-6), S.sx(6)):
            edge = x in (S.sx(-6), S.sx(6) - 1) or y == ly
            cv.set(x, y, TRIM[2] if edge else "#21170f")
    for x in range(S.sx(-5), S.sx(5)):
        for i in range(2 + (x * 7) % 4):
            cv.set(x, ly + 11 - i, HAY[3] if i == 0 else HAY[2] if i < 2 else HAY[1])
        if (x * 5) % 3 == 0:
            cv.set(x, ly + 11 - 2 - (x * 7) % 4, HAY[4])
    for x in range(S.sx(-13), S.sx(13)):  # a beam over the big doors
        cv.set(x, S.sy(-2, 33), DARKWOOD[5])
        cv.set(x, S.sy(-2, 33) + 1, DARKWOOD[2])
    for y in range(ly, ly + 12):  # the loft door swung open against the wall
        for x in range(S.sx(6) + 1, S.sx(6) + 5):
            cv.set(x, y, wood[4] if x == S.sx(6) + 1 else wood[3] if (x - S.sx(6)) % 2 else wood[2])
    cv.free()
    px_, py_ = S.s(0, -12, zr_w - 6)
    cv.set(px_ - 1, py_ + 1, IRON[2])
    cv.set(px_, py_ + 1, IRON[1])
    cv.set(px_ + 1, py_ + 1, IRON[2])
    for y in range(py_ + 2, py_ + 14):
        cv.set(px_ + 1, y, "#5c4632")
    for dx, dy in ((1, 14), (0, 15), (0, 16), (1, 17), (2, 16)):
        cv.set(px_ + dx, py_ + dy, IRON[2])
    # the half-doors along the front: lower leaves shut, the tops open, two horses looking out
    cv.on_wall(0)
    for k, sx in enumerate((-48, -38, 37, 47)):
        x0 = S.sx(sx - 4)
        top = S.sy(0, 28)
        mid = S.sy(0, 16)
        bot = S.sy(0, 5)
        for y in range(top - 1, bot):
            for x in range(x0 - 1, x0 + 9):
                cv.set(x, y, TRIM[1] if x in (x0 - 1, x0 + 8) or y == top - 1 else "#1d140e")
        for y in range(mid, bot):
            for x in range(x0, x0 + 8):
                kk = (x - x0) % 3
                c = wood[4] if kk == 0 else wood[2] if kk == 2 else wood[3]
                if y in (mid, mid + 1):
                    c = TRIM[3] if y == mid else TRIM[1]
                cv.set(x, y, c)
        for i in range(8):  # a diagonal brace on the lower leaf
            yy = bot - 1 - round(i * (bot - mid - 3) / 7)
            cv.set(x0 + i, yy, TRIM[2])
        for y in range(top, mid):  # the open top leaf against the wall
            for x in range(x0 + 9, x0 + 12):
                cv.set(x, y, wood[4] if x == x0 + 9 else wood[2])
        cv.set(x0 + 6, mid + 4, IRON[2])
        if k == 1:
            horse_head(cv, x0 - 1, mid + 2, CHESTNUT, flip=False)
        if k == 2:
            horse_head(cv, x0 - 2, mid + 2, GREY_HORSE, mane="#4a4440", blaze=False, flip=True)
    keep_lit(cv, lantern, S.sx(-19.5), S.sy(0, 22))
    keep_lit(cv, lantern, S.sx(19), S.sy(0, 22))
    for wx in (-23, 23):  # small windows high in the wall
        keep_lit(cv, window, rnd, S.sx(wx), S.sy(0, 30), w=8, h=7)
    cv.free()
    saddle(cv, S.sx(h2 + 4), S.sy(-6, 12) + 1)
    for x in range(S.sx(h2 + 14), S.sx(h2 + 17)):  # a bridle hanging off the rail
        cv.set(x, S.sy(-6, 12) + 2, "#3a1c0e")
    for y in range(S.sy(-6, 12) + 2, S.sy(-6, 12) + 8):
        cv.set(S.sx(h2 + 14), y, "#3a1c0e")
        cv.set(S.sx(h2 + 16), y, "#6e3a1e")
    cv.at_depth(-14)
    fxp = S.sx(-h2 + 18)
    for y in range(S.sy(-14, 0) - 22, S.sy(-14, 0)):  # a pitchfork leaning on the hay
        cv.set(fxp, y, WOOD[4])
    for dx in (-1, 0, 1):
        for dy in (22, 23, 24):
            cv.set(fxp + dx, S.sy(-14, 0) - dy, IRON[2] if dy > 22 or dx == 0 else IRON[1])
    return done(S, cv, "house", fp(-h2, h2, d), 0, door_w=22)


# ---------------------------------------------------------------- harbour warehouse

def rope_coil(seed=1):
    """A coil of rope lying flat: rings on top, turns round the side."""
    rp = ["#4a3a22", "#7a6440", "#a88e5e", "#cdb487", "#e2cfa2"]

    def f(u, v, kind, light, P, s):
        if kind == "top":
            dd = math.hypot(P[0] - s.params["cx"], P[1] - s.params["cy"])
            if dd < 1.2:
                return rp[0]
            return rp[3] if (dd % 1.6) < 0.9 else rp[1]
        return rp[2] if (P[2] % 1.6) < 0.9 and (u % 2) < 1.4 else rp[1]
    return Mat(f)


WEATHERED = ["#2a2622", "#45403a", "#625b52", "#7e766a", "#998f80", "#b3a996", "#cbc2ae"]


def warehouse(spec):
    """A big harbour warehouse: brick walls between piers under a low gable of weathered boards
    and slate, a wide sliding door half open on its rail with crates in the dark inside, a loft
    door in the gable under a hoist beam with a pulley, a rope and a hook with a net of sacks,
    barred windows, a painted anchor sign; crates, barrels, coils of rope and a bollard."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = 100, 62, 38
    h2 = ww / 2
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=111, moss=0.05)
    S = Scene(pad_top=8)
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, wall_h, brick(seed=111)))
    for px in (-h2 - 1, -h2 + 26, h2 - 29, h2 - 3):
        S.add(box(px, px + 4, -1.5, d, 4, wall_h, brick(seed=112, bias=0.22)))
    zr_w, zr = gable_front(S, -h2 - 1, h2 + 1, -1.5, d, wall_h, 0.42, rm, M.planks(WEATHERED, h=4, seed=113), over=4)
    S.add(box(-h2 - 1, h2 + 1, -2, d, wall_h - 2, wall_h, M.wood(DARKWOOD, bias=0.1)))  # a beam under the gable
    S.add(box(-2, 2, -16, -1.5, zr_w - 9, zr_w - 6, M.wood(DARKWOOD, bias=0.15)))  # hoist beam
    vy = d * 0.55  # a louvred ventilator on the ridge
    S.add(box(-6, 6, vy - 7, vy + 7, zr - 6, zr + 5, M.planks(WEATHERED, h=2, seed=114, bias=0.1)))
    for sl in roof_shell_y(-8.5, 8.5, vy - 9, vy + 9, zr + 3, zr + 9.5, 2, rm):
        S.add(sl)
    S.add(gable_y(-6, 6, vy - 7, vy + 7, zr + 4, zr + 5, zr + 9, M.planks(WEATHERED, h=2, seed=115)))
    # goods out front
    cr = M.crate(WOOD)
    S.add(box(-h2 + 1, -h2 + 13, -14, -4, 0, 10, cr))
    S.add(box(-h2 + 13, -h2 + 23, -12, -3, 0, 8, M.crate(WOOD)))
    S.add(box(-h2 + 3, -h2 + 13, -12, -4, 10, 18, M.crate(DARKWOOD)))
    for (bx, by, z) in ((h2 - 14, -6, 0), (h2 - 5, -5, 0), (h2 - 9.5, -5.5, 10)):
        S.add(prism(bx, by, 4.5, z, z + 10, M.barrel(seed=int(bx)), sides=12))
    S.add(prism(22, -8, 5, 0, 3, rope_coil(), sides=14))
    S.add(prism(22, -8, 3.6, 3, 5, rope_coil(), sides=12))
    S.add(prism(h2 + 7, -10, 2.6, 0, 7, M.flat(IRON + [IRON[2], "#77748a"]), sides=10))  # bollard
    S.add(prism(h2 + 7, -10, 3.4, 7, 8.5, M.flat(IRON + [IRON[2], "#77748a"]), sides=10))
    cv = S.render((0, 0, 0, 0))
    # the sliding door: a rail, the opening, the leaf slid half across
    cv.on_wall(0)
    ox0, ox1, oz1 = -15, 15, 30
    for y in range(S.sy(0, oz1), S.sy(0, 4)):
        for x in range(S.sx(ox0), S.sx(ox1)):
            cv.set(x, y, "#1a1410" if y < S.sy(0, 16) else "#231a12")
    for (cx_, z0, w_, h_) in ((5, 4, 8, 7), (11, 4, 6, 6), (8, 11, 6, 5)):  # crates in the dark inside
        for y in range(S.sy(0, z0 + h_), S.sy(0, z0)):
            for x in range(S.sx(cx_ - w_ / 2), S.sx(cx_ + w_ / 2)):
                edge = y in (S.sy(0, z0 + h_), S.sy(0, z0) - 1) or x in (S.sx(cx_ - w_ / 2), S.sx(cx_ + w_ / 2) - 1)
                cv.set(x, y, "#4a3420" if edge else "#5e4228")
    for x in range(S.sx(-h2 + 30), S.sx(ox1 + 3)):  # the rail and its brackets
        cv.set(x, S.sy(0, oz1 + 3), IRON[2])
        cv.set(x, S.sy(0, oz1 + 2), IRON[1])
    lx0, lx1 = S.sx(-19), S.sx(1)
    for y in range(S.sy(0, oz1 + 1), S.sy(0, 4)):
        for x in range(lx0, lx1):
            k = (x - lx0) % 4
            c = WEATHERED[4] if k == 0 else WEATHERED[2] if k == 3 else WEATHERED[3]
            cv.set(x, y, c)
    ly0, ly1 = S.sy(0, oz1 + 1), S.sy(0, 4)
    for i in range(lx1 - lx0):  # a Z brace and frame on the leaf
        yy = ly1 - 3 - round(i * (ly1 - ly0 - 6) / (lx1 - lx0 - 1))
        cv.set(lx0 + i, yy, DARKWOOD[4])
        cv.set(lx0 + i, yy + 1, DARKWOOD[2])
        for yb in (ly0, ly0 + 1, ly1 - 2, ly1 - 1):
            cv.set(lx0 + i, yb, DARKWOOD[4] if yb in (ly0, ly1 - 2) else DARKWOOD[2])
    for y in range(ly0, ly1):
        cv.set(lx0, y, DARKWOOD[4])
        cv.set(lx1 - 1, y, DARKWOOD[1])
    for rx in (lx0 + 3, lx1 - 4):  # rollers
        cv.set(rx, ly0 - 1, IRON[2])
        cv.set(rx + 1, ly0 - 1, IRON[1])
    cv.set(lx1 - 3, (ly0 + ly1) // 2, IRON[2])
    cv.set(lx1 - 3, (ly0 + ly1) // 2 + 1, IRON[1])
    for wx in (-37, 37):  # barred windows high up
        x0, y0 = S.sx(wx - 5), S.sy(0, 32)
        for y in range(y0, y0 + 8):
            for x in range(x0, x0 + 10):
                edge = x in (x0, x0 + 9) or y in (y0, y0 + 7)
                c = MARBLE[4] if edge and y == y0 else MARBLE[3] if edge else "#2a3440" if (x - x0) % 3 else IRON[1]
                cv.set(x, y, c)
                if not edge and (x - x0) % 3 and wx > 0:
                    glow(cv, x, y, LIT[1] if y > y0 + 2 else LIT[2])
    # the anchor sign painted on the left pier... a board on the right pier
    keep_lit(cv, lantern, S.sx(h2 - 31), S.sy(0, 22))
    cv.on_wall(-1.5)
    ax0, ay0 = S.sx(h2 - 28.5), S.sy(-1.5, 26)
    anchor = ["..w..", ".w.w.", "..w..", "wwwww", "..w..", "..w..", "w.w.w", ".www."]
    for y in range(ay0 - 1, ay0 + 10):
        for x in range(ax0 - 1, ax0 + 6):
            cv.set(x, y, "#1d2c4c" if y in (ay0 - 1, ay0 + 9) or x in (ax0 - 1, ax0 + 5) else "#2d4777")
    for j, row in enumerate(anchor):
        for i, ch in enumerate(row):
            if ch == "w":
                cv.set(ax0 + i, ay0 + 1 + j, "#ece4d6")
    # the loft door, the pulley, rope and hook with a net of sacks
    cv.on_wall(-1.5, tol=2.0)
    fy0 = S.sy(-1.5, zr_w - 12)
    for y in range(fy0, fy0 + 12):
        for x in range(S.sx(-6), S.sx(6)):
            edge = x in (S.sx(-6), S.sx(6) - 1) or y == fy0
            cv.set(x, y, DARKWOOD[4] if edge else "#1d1611")
    for i in range(3):
        sack(cv, S.sx(-5) + i * 3, fy0 + 12)
    cv.free()
    px_, py_ = S.s(0, -16, zr_w - 9)
    for dx, dy in ((-1, 1), (0, 1), (1, 1), (0, 2)):
        cv.set(px_ + dx, py_ + dy, IRON[2])
    hook = py_ + 17
    for y in range(py_ + 3, hook):
        cv.set(px_ + 1, y, "#5c4632")
    for y in range(hook, hook + 9):  # a net of sacks on the hook
        for x in range(px_ - 3, px_ + 6):
            dd = ((x - px_ - 1) / 4.5) ** 2 + ((y - hook - 5) / 4.5) ** 2
            if dd <= 1:
                c = "#cdb487" if x < px_ + 1 else "#a98e60"
                if (x + y) % 3 == 0:
                    c = "#5c4632"
                cv.set(x, y, c)
    cv.set(px_ + 1, hook, IRON[2])
    S.finish(cv)
    rope(cv, S.sx(22) + 5, S.sy(-8, 1), S.sx(22) + 14, S.sy(-12, 0), 0.6)
    return done(S, cv, "house", fp(-h2, h2, d), 8, door_w=14)


# ---------------------------------------------------------------- clock tower

def weather_vane(cv, x, y):
    """An iron weather vane standing on (x, y): a rod, the cross of the four winds with a letter
    dot at each end, an arrow with a feathered tail and a cockerel on top."""
    for yy in range(y - 18, y):
        cv.set(x, yy, IRON[1])
    for i in range(-5, 6):  # the arms of the four winds
        cv.set(x + i, y - 7, IRON[2] if i < 0 else IRON[1])
    for i in (-6, 6):
        cv.set(x + i, y - 7, GOLD[3])
    cv.set(x, y - 9, GOLD[3])
    cv.set(x, y - 5, GOLD[2])
    ay = y - 12
    for i in range(-6, 7):  # the arrow
        cv.set(x + i, ay, IRON[1])
    for dx, dy in ((5, -1), (5, 1), (4, -2), (4, 2)):
        cv.set(x + dx, ay + dy, IRON[1])
    for dx in (-6, -5, -4):
        cv.set(x + dx, ay - 1, IRON[2])
        cv.set(x + dx - 1, ay + 1, IRON[2])
    cock = ["..bb..", ".bbbr.", "bbbbb.", ".bbbbb", "..bb..", "..b..."]
    for j, row in enumerate(cock):
        for i, ch in enumerate(row):
            if ch != ".":
                cv.set(x - 3 + i, y - 19 - len(cock) + j + 1, "#c0392b" if ch == "r" else GOLD[3] if i < 3 else GOLD[2])
    cv.set(x, y - 18, GOLD[4])


def clock_tower(spec):
    """A tall square clock tower: a plinth, a shaft of dressed stone with lighter quoins and string
    courses, small arched windows climbing it, a jettied clock stage on a corbel table with a big
    clock face (it glows at night), a cornice and a steep slate pyramid with a weather vane; an
    arched door at the foot with a lantern."""
    rnd = random.Random(spec.get("seed", 1))
    stone = STONE
    roof = ROOFS[spec.get("roof_colour", "slate")]
    hw, dep = 12, 24
    cy = dep / 2
    S = Scene(pad=8, pad_top=26)
    S.add(box(-hw - 2, hw + 2, -2, dep + 2, 0, 6, M.dressed_stone(stone, seed=121, bias=0.15)))
    S.add(box(-hw, hw, 0, dep, 6, 84, M.dressed_stone(stone, seed=122)))
    for qx in (-hw - 0.5, hw - 3.5):  # quoins
        S.add(box(qx, qx + 4, -0.5, dep + 0.5, 6, 84, M.dressed_stone(SANDSTONE, h=5, seed=123, bias=0.1)))
    for z in (32, 58):  # string courses
        S.add(box(-hw - 1, hw + 1, -1, dep + 1, z, z + 2, M.dressed_stone(MARBLE, seed=124, bias=0.25)))
    S.add(box(-hw - 1.5, hw + 1.5, -1.5, dep + 1.5, 82, 85, M.dressed_stone(MARBLE, seed=125, bias=0.2)))
    for k in range(5):  # corbels under the clock stage
        cx_ = -hw + 1 + k * (2 * hw - 3) / 4
        S.add(box(cx_, cx_ + 2.5, -3, 0, 85, 88, M.dressed_stone(MARBLE, seed=126, bias=0.2)))
    S.add(box(-hw - 2.5, hw + 2.5, -2.5, dep + 2.5, 88, 113, M.dressed_stone(SANDSTONE, seed=127)))
    S.add(box(-hw - 4, hw + 4, -4, dep + 4, 113, 116.5, M.dressed_stone(MARBLE, seed=128, bias=0.25)))
    top = 156
    S.add(frustum(0, cy, hw + 4, 0.3, 116.5, top, M.shingles(roof, seed=129, row_h=3), sides=4, rot=-math.pi / 4,
                  ze=116.5, zr=top))
    S.add(box(-6, 6, -1.6, 4, 120, 128, M.dressed_stone(MARBLE, seed=130, bias=0.1)))  # a lucarne in the roof
    for s_ in roof_shell_y(-7.5, 7.5, -3, 6, 126, 133, 1.5, M.shingles(roof, seed=131, row_h=3)):
        S.add(s_)
    S.add(gable_y(-6, 6, -1.6, 4, 127.5, 128, 132.5, M.dressed_stone(MARBLE, seed=132, bias=0.1)))
    S.add(box(-8, 8, -7, -2, 0, 3, M.dressed_stone(stone, seed=133, bias=0.25)))  # the doorstep
    cv = S.render()
    cv.on_wall(0)
    keep_lit(cv, door, rnd, S.sx(0), S.sy(0, 6), w=12, h=20, style="arched", wood=DARKWOOD, step=False)
    keep_lit(cv, lantern, S.sx(7.5), S.sy(0, 22))
    for z in (50, 76):
        keep_lit(cv, tall_window, rnd, S.sx(0), S.sy(0, z), 5, 11, frame=MARBLE, arch=True, panes=2)
    for x in range(S.sx(-3), S.sx(3)):  # a datestone over the door
        for y in range(S.sy(0, 31), S.sy(0, 28)):
            cv.set(x, y, MARBLE[5] if y == S.sy(0, 31) else MARBLE[4])
        if x % 2:
            cv.set(x, S.sy(0, 29) - 1, MARBLE[2])
    cv.on_wall(-2.5)
    clock_face(cv, S.sx(0), S.sy(-2.5, 100.5), 10)
    for x in range(S.sx(-hw - 2.5), S.sx(hw + 2.5)):  # a moulding under the cornice
        cv.set(x, S.sy(-2.5, 113), SANDSTONE[2])
    cv.on_wall(-1.6, tol=1.0)
    lx, ly = S.sx(0), S.sy(-1.6, 127)
    for y in range(ly, ly + 6):  # the lucarne's louvres
        for x in range(lx - 3, lx + 3):
            cv.set(x, y, "#231d22" if (y - ly) % 2 == 0 else MARBLE[3])
    cv.free()
    vx, vy = S.s(0, cy, top)
    weather_vane(cv, vx, vy + 1)
    ivy(cv, rnd, S.sx(-hw + 3), S.sy(-1, 6), 30, spread=2)
    return done(S, cv, "house", fp(-hw - 2, hw + 2, dep + 2), 0, door_w=12)


# ---------------------------------------------------------------- fountain

FOUNTAIN_FRAMES = 4


def _falling_water(cv, S, cy, r_bowl, z_bowl, r_basin, z_water, z_spout, phase):
    """One frame of the water: a jet from the spout falling into the bowl, a curtain of streams
    pouring from the bowl's rim into the basin, splashes and rings where it lands."""
    streams = []
    n = 17
    for i in range(n):
        a = math.pi + (i + 0.5) * math.pi / n  # the front half of the rim
        x = r_bowl * math.cos(a)
        y = cy + r_bowl * math.sin(a)
        streams.append((x, y))
    for k, (x, y) in enumerate(streams):
        out = 1.0 + 0.4 * abs(x) / r_bowl  # the water arcs out a little as it falls
        x0, y0 = S.s(x, y, z_bowl)
        x1, y1 = S.s(x * (1 + out / r_bowl), y - out * 0.6, z_water)
        length = y1 - y0
        for j in range(length + 1):
            t = j / max(1, length)
            px = round(x0 + (x1 - x0) * t * t)
            py = y0 + j
            beat = (j - phase * 3 + k * 2) % 8
            c = WATER[6] if beat < 1 else WATER[5] if beat < 4 else WATER[4]
            if k % 2:
                c = WATER[5] if beat < 3 else WATER[4] if beat < 6 else WATER[3]
            cv.set(px, py, c)
        for dx, dy in ((-1, -1 - (phase + k) % 2), (1, -1 - (phase + k + 1) % 2), (0, -2 - (phase + k) % 3)):
            if (k + phase) % 3 == 0:
                cv.set(x1 + dx, y1 + dy, WATER[6])
    sx, sy = S.s(0, cy, z_spout)
    for j in range(-3, 0):  # the jet out of the spout
        cv.set(sx, sy + j, WATER[5] if (j + phase) % 2 else WATER[4])
    for side in (-1, 1):
        for j in range(0, 7):
            px = sx + side * round(math.sqrt(j) * 1.6)
            beat = (j + phase * 2) % 4
            cv.set(px, sy - 3 + j + (1 if j > 3 else 0), WATER[5] if beat < 2 else WATER[4])
    for i in range(6):  # sparkles drifting on the basin
        a = (i * 1.7 + phase * 0.6) % (math.pi)
        rr = r_bowl + 2 + (i * 3 + phase * 2) % (r_basin - r_bowl - 4)
        px, py = S.s(rr * math.cos(math.pi + a), cy + rr * math.sin(math.pi + a) * 0.9, z_water)
        if (i + phase) % 2 == 0:
            cv.set(px, py, WATER[6])
        else:
            cv.set(px, py, WATER[5])
            cv.set(px + 1, py, WATER[5])


def fountain(spec):
    """A fountain for the square: a round stone basin full of water with ripples and sparkles,
    a pedestal rising from it to an upper bowl with a spout on top; the water spouts up, falls
    into the bowl and pours over its rim into the basin (an animated part, four frames)."""
    rnd = random.Random(spec.get("seed", 1))
    R = 19
    cy = R
    z_rim = 7
    S = Scene(pad=6, pad_top=10)
    S.add(prism(0, cy, R + 1.2, 0, 2.5, M.dressed_stone(STONE, seed=141, bias=0.2), sides=28))  # a plinth ring
    S.add(prism(0, cy, R, 2.5, z_rim, basin(STONE, rim=2.6, seed=142), sides=28))
    S.add(frustum(0, cy, 5.5, 3.2, z_rim, z_rim + 3, M.dressed_stone(STONE, seed=143, bias=0.2), sides=12))
    S.add(prism(0, cy, 2.6, z_rim + 3, 24, M.flat(STONE, 0.12), sides=12))
    S.add(prism(0, cy, 3.6, 15, 17, M.flat(STONE, 0.22), sides=12))  # a ring round the shaft
    S.add(frustum(0, cy, 2.8, 4.8, 21, 24, M.flat(STONE, 0.15), sides=12))
    S.add(frustum(0, cy, 4.8, 10, 24, 28, basin(STONE, rim=1.6, seed=146), sides=18, rtop=10))
    S.add(prism(0, cy, 1.6, 28, 32, M.flat(STONE, 0.2), sides=8))
    S.add(frustum(0, cy, 2.4, 0.8, 32, 34.5, M.flat(STONE, 0.15), sides=8))
    cv = S.render()
    cv.free()
    for (x, y) in ((-9, cy - 8), (6, cy - 11), (11, cy - 4), (-12, cy + 2)):  # coins under the water
        px, py = S.s(x, y, z_rim)
        cv.set(px, py, GOLD[3])
    _ = rnd
    out = done(S, cv, "prop", fp(-R - 1, R + 1, 2 * R + 2))
    im, night, info = out
    # the animated water: frames side by side, each covering the bowl down to the basin
    fx0, fx1 = S.sx(-R + 3), S.sx(R - 3) + 1
    fy0, fy1 = S.sy(cy, 34) - 5, S.sy(cy - R + 2, z_rim) + 2
    fw, fh = fx1 - fx0, fy1 - fy0
    sheet = Image.new("RGBA", (fw * FOUNTAIN_FRAMES, fh), (0, 0, 0, 0))
    from buildings import Canvas
    for f in range(FOUNTAIN_FRAMES):
        fc = Canvas(im.width, im.height)
        _falling_water(fc, S, cy, 9.6, 27.6, R - 2.6, z_rim, 34, f)
        sheet.alpha_composite(fc.im.crop((fx0, fy0, fx1, fy1)), (f * fw, 0))
    info["water"] = [(fx0 + fx1) / 2 - S.ox, (fy0 + fy1) / 2 - S.base]
    info["water_frames"] = FOUNTAIN_FRAMES
    info["water_fps"] = 8
    return im, night, info, {"water": sheet}


DESIGNS = {"chapel": chapel, "clinic": clinic, "library": library, "museum": museum, "town_hall": town_hall,
           "stable": stable, "warehouse": warehouse, "clock_tower": clock_tower, "fountain": fountain}

ENTRIES = [
    {"id": "chapel", "name": "小教堂", "group": GROUP, "type": "chapel", "seed": 1, "roof_colour": "slate"},
    {"id": "clinic", "name": "诊所", "group": GROUP, "type": "clinic", "seed": 2, "roof_colour": "teal", "awning": "green"},
    {"id": "library", "name": "图书馆", "group": GROUP, "type": "library", "seed": 3, "roof_colour": "slate"},
    {"id": "museum", "name": "博物馆", "group": GROUP, "type": "museum", "seed": 4, "roof_colour": "rust",
     "banner": "red", "banner2": "blue"},
    {"id": "town_hall", "name": "镇公所", "group": GROUP, "type": "town_hall", "seed": 5, "roof_colour": "slate",
     "plaster": "cream", "flag": "blue"},
    {"id": "stable", "name": "马厩", "group": GROUP, "type": "stable", "seed": 6, "roof_colour": "thatch"},
    {"id": "warehouse", "name": "港口仓库", "group": GROUP, "type": "warehouse", "seed": 7, "roof_colour": "slate"},
    {"id": "clock_tower", "name": "钟楼", "group": GROUP, "type": "clock_tower", "seed": 8, "roof_colour": "slate"},
    {"id": "fountain", "name": "喷泉", "group": GROUP, "type": "fountain", "seed": 9},
]
