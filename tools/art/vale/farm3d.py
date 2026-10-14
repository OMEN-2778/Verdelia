"""Farm buildings and props modelled in 3D for the oblique renderer (see town3d.py): a hen house
with its wire run, an open-fronted livestock shed, a glasshouse you can see into, a silo, the
shipping bin, a tool shed, beehives, a compost bin, a scarecrow, a grape arbour and fences.

Each design builds a Scene of solids, renders it and then draws the small 2D things (hens, bees,
tools, straw, grapes, wire mesh...) onto the tops and walls they belong to. World units are
pixels; x right, y back, z up; the base point is the middle of the front wall (a prop: of its
front edge) at ground level.

Fences are segments meant to be placed end to end: fence_x is 32 px wide with a post centred on
each end, fence_y runs 32 px back (40 world units, 32 on screen) with a post at each end. Two
neighbours share the post at their joint: both draw it identically, and the rails stop one pixel
short of every post, so the outline round a post is the same in both pictures and whichever is
drawn on top, the join is seamless.
"""
import math
import random

import numpy as np
from PIL import Image

import materials as M
from buildings import (DARKWOOD, FIELDSTONE, GLASS, IRON, LEAF, LIT, PAINT, ROOFS, STONE, TRIM, WOOD, _result, door,
                       lantern, sack, window)
from landmarks import BARN_RED, CREAM, HAY, WHITE_TRIM, x_door
from market import CLOTH, GOLD, STEEL
from materials import _step, _t
from oblique import K, Mat, Scene, Solid, box, frustum, gable_x, gable_y, hsh, prism, roof_shell_y, slab
from town3d import footing, gable_front, step

FARM = "农场"

# ---------------------------------------------------------------- palettes (dark -> light)
WHITE7 = ["#4f4c49", "#8e8a84", "#b9b4ab", "#d6d1c7", "#e9e5dc", "#f6f3ec", "#fdfbf6"]
HAY7 = ["#4a3510", "#6b4f17", "#a8822a", "#d4b043", "#efd679", "#f7e49c", "#fbf0b5"]
EARTH = ["#3b2f22", "#5c4a35", "#7a6548", "#93805e", "#a99673", "#bfae8a", "#d4c6a4"]  # packed, sandy
COMPOST = ["#160f0a", "#261a11", "#3a2818", "#4d3520", "#60442a", "#755536", "#8a6844"]
TERRACOTTA = ["#3d1f10", "#6e3524", "#9a4a32", "#b9623f", "#cf7d52", "#e09a6c", "#efbb90"]
METAL = ["#22262d", "#3a404a", "#56606c", "#74808d", "#94a0ac", "#b6c0ca", "#d8dfe6"]
LEAF7 = ["#122a17", "#1c4021", "#2a5a2b", "#3b7735", "#559844", "#7cba57", "#a9d877"]
GRAPE = ["#1e0f2e", "#3b2160", "#5c3a8c", "#8463b8", "#b29be0"]
YELLOW7 = ["#4a3a10", "#7a6118", "#a8882a", "#cdab40", "#e2c65c", "#f0dc86", "#faf0b8"]
MINT7 = ["#1f3a30", "#2f5a48", "#447a62", "#5f9a7e", "#82b89c", "#a8d2b8", "#d0ead8"]
SKY7 = PAINT["blue"]
PAINTS = {"red": BARN_RED, "cream": CREAM, "sage": PAINT["sage"], "blue": PAINT["blue"], "rose": PAINT["rose"],
          "wood": WOOD, "dark": DARKWOOD, "white": WHITE7, "yellow": YELLOW7, "mint": MINT7}


# ================================================================ shared helpers

def fpr(x0, x1, y0, y1):
    """Footprint of the ground x0..x1, y0..y1 (world units, y back) relative to the base point."""
    top, bot = -round(K * y1), -round(K * y0)
    if bot - top < 2:
        top = bot - 2
    return [round(x0), top, round(x1 - x0), bot - top]


def done(S, cv, kind, footprint, door_x=None, door_w=14, after=None, extra=None, **flags):
    """Outline, then draw what must stay unoutlined (wire mesh, bees), then the info dict."""
    S.finish(cv)
    if after:
        cv.free()
        after(cv)
    im, night, info = _result(cv, kind, (S.ox, S.base), footprint, S.sx(door_x) if door_x is not None else None, door_w)
    info.update(flags)
    return (im, night, info) if extra is None else (im, night, info, extra)


def lean_x(xa, xb, y0, y1, za, zb, th, mat, **kw):
    """A board sloping along x from (xa, za) to (xb, zb): a lean-to roof against a side wall."""
    s = (zb - za) / (xb - xa)
    lo, hi = min(xa, xb), max(xa, xb)
    planes = [((-1, 0, 0), -lo), ((1, 0, 0), hi), ((0, -1, 0), -y0), ((0, 1, 0), y1),
              ((-s, 0, 1), za - s * xa), ((s, 0, -1), -(za - th) + s * xa)]
    return Solid(planes, mat, (lo, hi, y0, y1, min(za, zb) - th, max(za, zb)), ze=min(za, zb), zr=max(za, zb), **kw)


def obox(c, axes, half, mat, **kw):
    """An oriented box: centre c, three axes (normalised here), half sizes along them."""
    c = np.asarray(c, dtype=float)
    ax = [np.asarray(a, dtype=float) / np.linalg.norm(a) for a in axes]
    planes = []
    for a, h in zip(ax, half):
        d = float(a @ c)
        planes.append((a, d + h))
        planes.append((-a, -d + h))
    pts = [c + s0 * half[0] * ax[0] + s1 * half[1] * ax[1] + s2 * half[2] * ax[2]
           for s0 in (-1, 1) for s1 in (-1, 1) for s2 in (-1, 1)]
    pts = np.array(pts)
    bb = (pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max(), pts[:, 2].min(), pts[:, 2].max())
    return Solid(planes, mat, bb, **kw)


def rbox(x, y, ang, s0, s1, w0, w1, z0, z1, mat, **kw):
    """A box turned about z: from s0 to s1 along direction ang (radians, from +x towards +y) out of
    (x, y), w0..w1 across it, z0..z1 high (a gate leaf's rails and stiles)."""
    d = np.array([math.cos(ang), math.sin(ang), 0.0])
    n = np.array([-math.sin(ang), math.cos(ang), 0.0])
    c = np.array([x, y, 0.0]) + d * (s0 + s1) / 2 + n * (w0 + w1) / 2
    c[2] = (z0 + z1) / 2
    return obox(c, (d, n, (0, 0, 1)), ((s1 - s0) / 2, (w1 - w0) / 2, (z1 - z0) / 2), mat, **kw)


# ---------------------------------------------------------------- materials

def lwood(ramp=WOOD, seed=1, bias=0.1, grain=0.12, edge=False):
    """Wood whose grain is painted from coordinates local to the solid, so the same part looks
    the same wherever it stands (fence posts shared by two segments)."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1, z0, z1 = s.bbox
        lx, ly, lz = P[0] - x0, P[1] - y0, P[2] - z0
        if kind == "top":
            a, b = lx, ly
        elif kind == "side":
            a, b = ly, lz
        else:
            a, b = lx, lz
        g = -0.13 if hsh(math.floor(a), math.floor(b / 3), seed) < grain else 0.0
        if edge and kind == "wall":
            if lx < 1:
                g += 0.18
            elif x1 - P[0] < 1:
                g -= 0.15
        return _t(ramp, light + bias + g)
    return Mat(f)


def slats(ramp, inside, h=3, gap=1, seed=1, bias=0.1):
    """Horizontal boards with gaps between them through which `inside` (a colour) shows."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + bias + 0.1)
        z = P[2] - s.bbox[4]
        k = z % (h + gap)
        row = math.floor(z / (h + gap))
        if k >= h:
            return inside
        lv = light + bias + (hsh(row, seed) - 0.5) * 0.16
        if k >= h - 1:
            return _step(ramp, lv, 1)
        if hsh(math.floor(u / 3), row, seed + 3) < 0.1:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def ground(ramp, seed=1, specks=(), bias=0.0):
    """Earth, compost or straw on a top face, with scattered specks [(colour, chance), ...]."""
    def f(u, v, kind, light, P, s):
        if kind != "top":
            return _t(ramp, light - 0.1)
        hv = hsh(math.floor(P[0]), math.floor(P[1] * 1.25), seed)
        acc = 0.0
        for c, p in specks:
            acc += p
            if hv < acc:
                return c
        lv = light + bias + (hsh(math.floor(P[0] / 2), math.floor(P[1] / 2), seed + 7) - 0.5) * 0.3
        return _t(ramp, lv)
    return Mat(f)


def hay_mat(seed=1):
    """Loose hay: streaky strands on top and down the sides."""
    def f(u, v, kind, light, P, s):
        lv = light + 0.1 + (hsh(math.floor(u), math.floor(v / 3), seed) - 0.5) * 0.35
        if hsh(math.floor(u * 1.5), math.floor(v), seed + 2) < 0.12:
            return HAY7[2]
        return _t(HAY7, lv)
    return Mat(f)


def corrugated(ramp=METAL, band=12, seed=1):
    """Galvanised sheet: vertical ribs, a seam with rivets every `band` px."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + 0.1)
        z = P[2] - s.bbox[4]
        k = z % band
        rib = (u % 3)
        lv = light + 0.12 + (0.12 if rib < 1 else -0.08 if rib >= 2 else 0) + (hsh(math.floor(z / band), seed) - 0.5) * 0.08
        if k < 1:
            return _step(ramp, light + 0.1, -2)
        if k < 2:
            return _step(ramp, light + 0.2, 1) if (math.floor(u) % 4 == 0) else _t(ramp, light + 0.2)
        return _t(ramp, lv)
    return Mat(f)


def leafy(ramp=LEAF7, seed=1, fruit=None):
    """A mat of vine leaves: rounded clusters, dark gaps, now and then a bunch of fruit."""
    def f(u, v, kind, light, P, s):
        cx, cy = math.floor(P[0] / 3), math.floor(P[1] / 3 + (0.5 if math.floor(P[0] / 3) % 2 else 0))
        hv = hsh(cx, cy, seed)
        lx = P[0] / 3 - cx
        ly = P[1] / 3 - math.floor(P[1] / 3 + (0.5 if cx % 2 else 0))
        if fruit and hv < 0.05:
            return fruit[3] if lx < 0.5 else fruit[2]
        if hv < 0.12:
            return ramp[1]
        lv = light + 0.05 + (hv - 0.5) * 0.4 + (0.12 if lx + ly < 0.7 else -0.1 if lx + ly > 1.4 else 0)
        if kind != "top":
            lv -= 0.15
        return _t(ramp, lv)
    return Mat(f)


# ---------------------------------------------------------------- 2D parts

HENS = {"white": ("#6d6a66", "#d6d1c7", "#fbf8f2"), "brown": ("#4a2610", "#9a5a2e", "#cf8f55"),
        "black": ("#16141a", "#34303a", "#5a5562")}
# h highlight, w body, s shade, r comb, y beak, k eye, o legs
HEN_STAND = ["..r....",
             ".rhh..h",
             "yhkh.hw",
             ".hwwhws",
             "..swws.",
             "...o.o."]
HEN_PECK = ["......h",
            "....hhw",
            "..hhwws",
            ".rhwwss",
            "ykhsws.",
            "...o.o."]


def hen(cv, x, bottom, colour="white", pose="stand", right=False):
    """A hen about 7 px long standing on `bottom`, x its left edge."""
    d, m, l = HENS[colour]
    rows = HEN_PECK if pose == "peck" else HEN_STAND
    cols = {"h": l, "w": m, "s": d, "r": "#d8333a", "y": "#f0b030", "k": "#1c1a1f", "o": "#e0902a"}
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == ".":
                continue
            cv.set(x + (len(row) - 1 - i if right else i), bottom - len(rows) + j, cols[ch])


SHEEP = ["....hhhhh..",
         "...hhwhwwh.",
         "kk.hwwwwwwh",
         "kek.wwwwwws",
         "kkk.wwwwwss",
         ".k..swwwss.",
         "....k.k.k.."]


def sheep(cv, x, bottom, right=False):
    """A sheep about 11 px long, black face, fleece in three tones, x its left edge."""
    cols = {"h": "#fbf8f2", "w": "#e2dccf", "s": "#b4ab9a", "k": "#2a2428", "e": "#d8d0c2"}
    for j, row in enumerate(SHEEP):
        for i, ch in enumerate(row):
            if ch in cols:
                cv.set(x + (len(row) - 1 - i if right else i), bottom - len(SHEEP) + j, cols[ch])


def egg_basket(cv, x, bottom, w=8):
    for y in range(bottom - 4, bottom):
        for i in range(w):
            c = "#c9a061" if (i + y) % 2 == 0 else "#9b7642"
            if i in (0, w - 1) or y == bottom - 1:
                c = "#6b4e2a"
            cv.set(x + i, y, c)
    for i in range(w):
        cv.set(x + i, bottom - 4, "#e2c084")
    for k, ex in enumerate(range(x + 1, x + w - 2, 2)):
        c = ("#fbf6ea", "#e8c9a0", "#fbf6ea")[k % 3]
        cv.set(ex, bottom - 5, c)
        cv.set(ex + 1, bottom - 5, "#d8cfbf" if c == "#fbf6ea" else "#c9a57a")
        cv.set(ex, bottom - 6, c)
    for i in range(1, w - 1):  # the handle
        y = bottom - 6 - round(3 * math.sin(math.pi * i / (w - 1)))
        cv.set(x + i, y, "#8b6a3e")


def wire_mesh(cv, x0, x1, y_top, y_bot, colour=("#e3e7ec", "#a7aeb6"), every=6, keep=None):
    """Chicken wire: a fine diamond lattice, blended over what is behind it (or half see-through
    where nothing is). Drawn after the outline so the thin wires stay one pixel wide."""
    for y in range(y_top, y_bot):
        for x in range(x0, x1):
            a, b = (x + y) % every, (x - y) % every
            if a and b:
                continue
            if keep and not keep(x, y):
                continue
            c = colour[0] if a == 0 else colour[1]
            r, g, bl = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            under = cv.get(x, y)
            if under[3]:
                k = 0.5 if a == 0 else 0.35
                cv.px[x, y] = (round(under[0] * (1 - k) + r * k), round(under[1] * (1 - k) + g * k),
                               round(under[2] * (1 - k) + bl * k), 255)
            else:
                cv.px[x, y] = (r, g, bl, 150 if a == 0 else 110)


def tool(cv, x, bottom, kind, h=20, lean=0):
    """A long-handled tool standing on its head or handle: rake, hoe, shovel, pitchfork, broom.
    lean shifts the top by that many px."""
    top = bottom - h

    def hx(y):
        return x + round(lean * (bottom - y) / h)
    if kind in ("rake", "hoe", "pitchfork"):  # head up
        for y in range(top + 2, bottom):
            cv.set(hx(y), y, WOOD[5] if y % 4 else WOOD[4])
        cx = hx(top + 2)
        if kind == "rake":
            for i in range(-3, 4):
                cv.set(cx + i, top + 1, IRON[2])
                if i % 2 != 0 or i == 0:
                    cv.set(cx + i, top, IRON[2] if i < 0 else IRON[1])
        elif kind == "hoe":
            for i in range(0, 4):
                cv.set(cx + i, top + 1, STEEL[3] if i < 3 else STEEL[2])
            cv.set(cx + 3, top + 2, STEEL[2])
            cv.set(cx + 3, top + 3, STEEL[1])
        else:
            for i in (-2, 0, 2):
                cv.set(cx + i, top, STEEL[3])
                cv.set(cx + i, top - 1, STEEL[4])
            for i in range(-2, 3):
                cv.set(cx + i, top + 1, STEEL[2])
    elif kind == "shovel":  # blade down, handle up with a grip
        for y in range(top + 2, bottom - 5):
            cv.set(hx(y), y, WOOD[5] if y % 4 else WOOD[4])
        gx = hx(top + 1)
        for i in (-1, 0, 1):
            cv.set(gx + i, top + 1, WOOD[3])
        cv.set(gx - 1, top + 2, WOOD[3])
        cv.set(gx + 1, top + 2, WOOD[3])
        bx = hx(bottom - 3)
        for j in range(5):
            for i in range(-1 if j < 4 else 0, 2 if j < 4 else 1):
                cv.set(bx + i, bottom - 5 + j, STEEL[3] if i < 0 else STEEL[2] if i == 0 else STEEL[1])
    elif kind == "broom":
        for y in range(top, bottom - 5):
            cv.set(hx(y), y, WOOD[5] if y % 4 else WOOD[4])
        bx = hx(bottom - 3)
        for j in range(5):
            for i in range(-1 - j // 2, 2 + j // 2):
                cv.set(bx + i, bottom - 5 + j, HAY[3] if (i + j) % 2 else HAY[2])


def straw(cv, rnd, x0, x1, y, n=8, colours=HAY):
    """Loose wisps of straw lying on the ground around y."""
    for _ in range(n):
        x = rnd.randint(x0, x1)
        yy = y + rnd.randint(-1, 1)
        ln = rnd.randint(2, 3)
        d = rnd.choice((-1, 1))
        for i in range(ln):
            cv.set(x + i * d, yy - (i if rnd.random() < 0.3 else 0), colours[rnd.randint(2, 4)])


def flower_tuft(cv, rnd, x, bottom, colour=None):
    for k in range(rnd.randint(2, 3)):
        bx = x + k * 2 - 1
        for j in range(rnd.randint(2, 4)):
            cv.set(bx, bottom - 1 - j, LEAF[min(2, j)])
    if colour:
        fx, fy = x + rnd.randint(-1, 1), bottom - 5
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1)):
            cv.set(fx + dx, fy + dy, colour[0])
        cv.set(fx, fy, colour[1])


# ================================================================ fences

FENCE_H = 15


def _post(S, x0, y0, style):
    """One fence post at x0 (left side), y0..y0+3 deep; identical everywhere it is used."""
    if style == "picket":
        pm = lwood(WHITE7, seed=3, bias=0.18, grain=0.06, edge=True)
        S.add(box(x0, x0 + 3, y0, y0 + 3, 0, FENCE_H - 1, pm))
        S.add(box(x0 - 1, x0 + 4, y0 - 1, y0 + 4, FENCE_H - 1, FENCE_H, lwood(WHITE7, seed=4, bias=0.25, grain=0)))
        S.add(frustum(x0 + 1.5, y0 + 1.5, 1.5, 0.25, FENCE_H, FENCE_H + 2.5, lwood(WHITE7, seed=5, bias=0.2, grain=0),
                      sides=4, rot=-math.pi / 4))
    else:
        S.add(box(x0, x0 + 4, y0, y0 + 3, 0, FENCE_H, lwood(DARKWOOD, seed=3, bias=0.22, edge=True)))


def _rails_x(S, x0, x1, style):
    """Rails (and pickets) between the posts of a run along x, from x0 to x1 (1 px short of the
    posts on either side)."""
    if style == "picket":
        rm = lwood(WHITE7, seed=6, bias=0.05, grain=0)
        for z in (3.5, 9.5):
            S.add(box(x0, x1, 1.5, 2.5, z, z + 1.5, rm))
        x = x0 + 1
        k = 0
        while x + 3 <= x1:
            pm = lwood(WHITE7, seed=7 + k % 3, bias=0.16, grain=0.05)
            S.add(box(x, x + 3, 0.5, 1.5, 0.5, 11, pm))
            S.add(gable_y(x, x + 3, 0.5, 1.5, 10.5, 11, 12.5, pm))
            x += 4
            k += 1
    else:
        rm = lwood(WOOD, seed=8, bias=0.12)
        S.add(box(x0, x1, 0.75, 2.25, 3, 5, rm))
        S.add(box(x0, x1, 0.75, 2.25, 10, 12, lwood(WOOD, seed=9, bias=0.12)))


def _rails_y(S, y0, y1, style):
    if style == "picket":
        rm = lwood(WHITE7, seed=6, bias=0.05, grain=0)
        for z in (3.5, 9.5):
            S.add(box(-1, 0, y0, y1, z, z + 1.5, rm))
        y = y0
        while y + 3 <= y1 + 0.01:
            pm = lwood(WHITE7, seed=7, bias=0.16, grain=0.05)
            S.add(box(-2, 1, y, y + 3, 0.5, 11, pm))
            S.add(gable_x(-2, 1, y, y + 3, 10.5, 11, 12.5, pm))
            y += 4
    else:
        S.add(box(-1, 1, y0, y1, 3, 5, lwood(WOOD, seed=8, bias=0.12)))
        S.add(box(-1, 1, y0, y1, 10, 12, lwood(WOOD, seed=9, bias=0.2)))


def _fence_scene():
    return Scene(pad=4, pad_top=3, pad_bottom=3)


def fence_x(spec):
    """A 32 px run of fence along x: a post centred on each end, rails (or pickets) between."""
    style = spec.get("style", "rustic")
    S = _fence_scene()
    pw = 3 if style == "picket" else 4
    lx = -16 - pw // 2 - (1 if style == "picket" else 0)  # picket posts are 3 wide: -18..-15, 14..17
    rx = lx + 32
    _post(S, lx, 0, style)
    _post(S, rx, 0, style)
    _rails_x(S, lx + pw + 1, rx - 1, style)
    cv = S.render()
    if style != "picket":
        _rustic_marks(cv, S, lx + pw + 1, rx - 1)
    return done(S, cv, "fence", fpr(-16, 16, 0, 3))


def _rustic_marks(cv, S, x0, x1):
    """Knots and a split here and there on the rails."""
    cv.at_depth(0.5)
    for z, seed in ((5, 1), (12, 2)):
        for x in range(round(x0) + 3, round(x1) - 2, 7):
            if hsh(x, seed) < 0.5:
                sx, sy = S.s(x, 0.5, z - 1)
                cv.set(sx, sy, WOOD[2])
    cv.free()


def fence_y(spec):
    """A run of fence going back into the scene: posts at the front and 40 units back (32 px on
    screen, so segments placed every 32 px join), rails (or pickets) between."""
    style = spec.get("style", "rustic")
    S = _fence_scene()
    lx = -2
    _post(S, lx if style != "picket" else -2, 0, style)
    _post(S, lx if style != "picket" else -2, 40, style)
    _rails_y(S, 4, 39, style)
    cv = S.render()
    return done(S, cv, "fence", fpr(-2, 2, 0, 40))


def fence_gate(spec):
    """A gate between two posts, 32 px wide like fence_x. Open (default) it stands swung back on
    its right-hand hinge, so the gap is free to walk through and only the leaf blocks; closed
    ({"open": false}) it fills the gap and blocks like a fence."""
    style = spec.get("style", "rustic")
    is_open = spec.get("open", True)
    S = _fence_scene()
    pw = 3 if style == "picket" else 4
    lx = -16 - pw // 2 - (1 if style == "picket" else 0)
    rx = lx + 32
    _post(S, lx, 0, style)
    _post(S, rx, 0, style)
    hx, hy = rx - 0.5, 1.5  # the hinge, on the right post's inner face
    length = rx - 1.5 - (lx + pw + 1)
    ang = math.radians(180 - spec.get("angle", 50)) if is_open else math.pi
    white = style == "picket"
    wm = lwood(WHITE7 if white else WOOD, seed=11, bias=0.16 if white else 0.12, grain=0.05 if white else 0.12)
    w0, w1 = -0.75, 0.75
    if white:
        for z0, z1 in ((2.5, 4), (8.5, 10)):
            S.add(rbox(hx, hy, ang, 0.5, length, w0 + 0.75, w1 + 0.75, z0, z1, wm))
        n = 6
        for k in range(n):
            s0 = 0.5 + k * (length - 0.5) / n + 0.6
            s1 = s0 + (length - 0.5) / n - 1.2
            mid = (s0 + s1) / 2 / length
            top = 11.5 + 2.5 * math.sin(math.pi * mid)
            S.add(rbox(hx, hy, ang, s0, s1, w0, w1, 1, top, lwood(WHITE7, seed=12 + k, bias=0.18, grain=0.05)))
    else:
        for z0, z1 in ((2.5, 4), (7.5, 9), (12, 13.5)):
            S.add(rbox(hx, hy, ang, 2.5, length - 2, w0, w1, z0, z1, wm))
        for s0 in (0.5, length - 2):
            S.add(rbox(hx, hy, ang, s0, s0 + 2, w0 - 0.25, w1 + 0.25, 1.5, 14, lwood(WOOD, seed=13, bias=0.05)))
        # the diagonal brace in front, from the bottom at the hinge up to the top at the latch
        d = np.array([math.cos(ang), math.sin(ang), 0.0])
        nrm = np.array([-math.sin(ang), math.cos(ang), 0.0])
        p0 = np.array([hx, hy, 0]) + d * 3 + nrm * 1.4 + np.array([0, 0, 3.5])
        p1 = np.array([hx, hy, 0]) + d * (length - 2.5) + nrm * 1.4 + np.array([0, 0, 12.5])
        a_ = p1 - p0
        S.add(obox((p0 + p1) / 2, (a_, nrm, np.cross(a_, nrm)), (np.linalg.norm(a_) / 2, 0.6, 0.8),
                   lwood(WOOD, seed=14, bias=0.22)))
    cv = S.render()
    if is_open:
        ex, ey = hx + math.cos(ang) * length, hy + math.sin(ang) * length
        foot = fpr(min(ex, hx) - 1, hx + 0.5, 0, max(ey, 3) + 1)
    else:
        foot = fpr(-16, 16, 0, 3)
    # the latch on the free end, the hinges on the post
    cv.free()
    return done(S, cv, "fence", foot)


# ================================================================ coop

def coop(spec):
    """A small hen house raised on short legs: painted boards under a shingled gable, a ramp up to
    a little hatch, a nesting box with its own sloping lid on the side, a vent window; beside it
    a run of chicken wire on posts over scratched earth, with a feeder and hens pecking about."""
    rnd = random.Random(spec.get("seed", 1))
    paint = PAINTS[spec.get("paint", "red")]
    trim = spec.get("trim", "white")
    trim_ramp = WHITE_TRIM if trim == "white" else TRIM
    roof = M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=spec.get("seed", 1) + 3, moss=0.05)
    walls = M.boards(paint, w=4, seed=spec.get("seed", 1))
    S = Scene(pad_top=6)
    cw, d, z_floor, z_wall = 17, 22, 7, 25
    # legs and the box of the house
    for lx in (-cw + 1, cw - 4):
        for ly in (1, d - 4):
            S.add(box(lx, lx + 3, ly, ly + 3, 0, z_floor, lwood(DARKWOOD, seed=lx + ly, bias=0.1)))
    S.add(box(-cw - 0.5, cw + 0.5, -0.5, d + 0.5, z_floor - 1.5, z_floor, M.wood(DARKWOOD, bias=0.15)))  # sill beam
    S.add(box(-cw, cw, 0, d, z_floor, z_wall, walls))
    for px in (-cw - 1, cw - 2):
        S.add(box(px, px + 3, -1, d + 1, z_floor, z_wall, M.wood(trim_ramp + [trim_ramp[-1]] * 2, bias=0.15)))
    zr_w, zr = gable_front(S, -cw, cw, 0, d, z_wall, 0.58, roof, walls, over=4)
    # nesting box on the right with a sloping lid
    S.add(box(cw, cw + 7, 3, 17, z_floor + 4, z_floor + 13, M.boards(paint, w=4, seed=4)))
    S.add(lean_x(cw - 1, cw + 9, 1.5, 18.5, z_floor + 16, z_floor + 12.5, 1.5, M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=8)))
    # ramp up to the hatch
    hx0, hx1 = -11, -4
    S.add(slab(hx0, hx1, -12, 0, 0.5, z_floor, 1.2, _ramp_mat()))
    # the run: earth floor, posts, a kick board and top rail along the front, left and back
    rx0, rx1, ry0, ry1 = -48, -cw, -5, 24
    rz = 9.5  # height of the run's wire
    S.add(box(rx0, rx1, ry0, ry1, 0, 0.6, ground(EARTH, seed=5, specks=((HAY[3], 0.05), (HAY[4], 0.03), (EARTH[1], 0.04)))))
    pm = lwood(WOOD, seed=2, bias=0.15)
    for (px, py) in ((rx0, ry0), (rx1 - 3, ry0), (rx0, ry1 - 2), (rx0 + (rx1 - rx0) // 2 - 1, ry0)):
        S.add(box(px, px + 2.5, py, py + 2.5, 0, rz + 1.5, pm, no_shadow=True))
    rail = lwood(WOOD, seed=4, bias=0.2)
    for (a0, a1, b0, b1) in ((rx0, rx1, ry0, ry0 + 1.5), (rx0, rx0 + 1.5, ry0, ry1), (rx0, rx1, ry1 - 1.5, ry1)):
        S.add(box(a0, a1, b0, b1, rz, rz + 1.5, rail, no_shadow=True))
        S.add(box(a0, a1, b0, b1 - 0.5 if b1 - b0 < 2 else b1, 0.6, 2.5, lwood(WOOD, seed=5, bias=0.05), no_shadow=True))
    feeder = (-38, -30, 8, 11)
    S.add(box(feeder[0], feeder[1], feeder[2], feeder[3], 0, 2.5, M.planks(WOOD, h=3, seed=6)))
    cv = S.render()
    # the hatch with straw on its sill, its little door slid up above it
    cv.on_wall(0)
    hb = S.sy(0, z_floor)
    for y in range(hb - 9, hb):
        for x in range(S.sx(hx0), S.sx(hx1)):
            cv.set(x, y, "#1c1410" if y < hb - 3 else "#2a1d14")
    for x in range(S.sx(hx0), S.sx(hx1)):
        cv.set(x, hb - 1, HAY[3] if x % 2 else HAY[2])
        if x % 3 == 0:
            cv.set(x, hb - 2, HAY[3])
    for y in range(hb - 18, hb - 10):  # the hatch door, slid up in its runners
        for x in range(S.sx(hx0) - 1, S.sx(hx1) + 1):
            edge = x in (S.sx(hx0) - 1, S.sx(hx1))
            cv.set(x, y, trim_ramp[1] if edge else WOOD[4] if (x - S.sx(hx0)) % 3 else WOOD[3])
    for y in range(hb - 19, hb):
        cv.set(S.sx(hx0) - 2, y, trim_ramp[3])
        cv.set(S.sx(hx1) + 1, y, trim_ramp[2])
    # a vent window with mesh, upper right
    vx, vy = S.sx(7), S.sy(0, z_wall - 4)
    for y in range(vy, vy + 7):
        for x in range(vx - 4, vx + 4):
            edge = x in (vx - 4, vx + 3) or y in (vy, vy + 6)
            if edge:
                cv.set(x, y, trim_ramp[3] if (x == vx - 4 or y == vy) else trim_ramp[1])
            else:
                cv.set(x, y, "#9aa3ad" if (x + y) % 2 == 0 else "#241a14")
    cv.on_wall(0, tol=2.0)
    gx, gy = S.sx(0), S.sy(0, z_wall + (zr_w - z_wall) * 0.4)  # a painted egg on the gable
    for y in range(gy - 3, gy + 3):
        for x in range(gx - 2, gx + 3):
            if ((x - gx) / 2.4) ** 2 + ((y - gy + 0.3) / 3.0) ** 2 <= 1:
                cv.set(x, y, "#fbf6ea" if x < gx + 1 else "#e3d8c4")
    # nesting box lid hinge and catch
    cv.on_wall(5)
    nx, ny = S.sx(cw + 3), S.sy(5, z_floor + 11)
    cv.set(nx, ny, IRON[2])
    cv.set(nx + 1, ny, IRON[1])
    # feed in the feeder
    cv.at_depth(feeder[2] + 0.5)
    for x in range(S.sx(feeder[0] + 1), S.sx(feeder[1] - 1)):
        cv.set(x, S.sy(feeder[2] + 1, 2.5), HAY[3] if x % 2 else "#c9a24a")
    # hens: two pecking in the run, one walking up the ramp, one by the feeder
    for (x, y, col, pose, right) in ((-42, 4, "white", "peck", False), (-27, 13, "brown", "stand", True),
                                     (-34, 0, "white", "stand", True)):
        cv.at_depth(y)
        hen(cv, S.sx(x), S.sy(y, 0.6), col, pose, right)
    cv.at_depth(-7)
    hen(cv, S.sx(-10), S.sy(-7, 0.5 + (z_floor - 0.5) * (12 - 7) / 12) + 0, spec.get("ramp_hen", "brown"), "stand", True)
    cv.at_depth(-4)
    egg_basket(cv, S.sx(cw - 6), S.sy(-4, 0))
    straw(cv, rnd, S.sx(-12), S.sx(-2), S.sy(-9, 0), n=5)
    cv.free()

    def mesh(c):
        top_f, bot_f = S.sy(ry0, rz), S.sy(ry0, 2.5)
        wire_mesh(c, S.sx(rx0 + 2), S.sx(rx1), top_f, bot_f + 1,
                  keep=lambda x, y: c.get(x, y)[3] and not (S.sx(rx1 - 3) <= x < S.sx(rx1 - 0.5))
                  and not (S.sx(rx0 + (rx1 - rx0) // 2 - 1) <= x < S.sx(rx0 + (rx1 - rx0) // 2 + 1.5)))
        top_b, bot_b = S.sy(ry1, rz), S.sy(ry1, 2.5)
        wire_mesh(c, S.sx(rx0 + 2), S.sx(rx1), top_b, bot_b, colour=("#a9b0b9", "#7c838c"),
                  keep=lambda x, y: not c.get(x, y)[3] or c.get(x, y)[:3] in ())
    return done(S, cv, "farm", fpr(rx0, cw + 7, ry0, d), after=mesh)


def _ramp_mat():
    def f(u, v, kind, light, P, s):
        if kind != "slope":
            return _t(WOOD, light)
        if v % 2.6 < 0.9:
            return WOOD[2]  # cleats for little feet
        return _t(WOOD, light + 0.15 + (hsh(math.floor(u / 3), 3) - 0.5) * 0.1)
    return Mat(f)




# ================================================================ livestock shed

def animal_shed(spec):
    """A long, low livestock shed open along the front: plank back and end walls under a hipped
    shingle roof on posts, four stalls behind cross-braced half-doors (one standing open) with
    straw on the floor and hay heaped at the back, a water trough in front, a lantern on the
    middle post, hay bales and a pitchfork."""
    rnd = random.Random(spec.get("seed", 1))
    h2, d, wall = 50, 34, 25
    stalls = spec.get("stalls", 4)
    sw = 2 * h2 / stalls
    roof = ROOFS[spec.get("roof_colour", "rust")]
    planks = M.planks(DARKWOOD if spec.get("dark") else WOOD, seed=spec.get("seed", 1) + 2)
    S = Scene(pad_top=6)
    S.add(box(-h2, h2, 0, d, 0, 1, ground(HAY7, seed=4, specks=((HAY7[2], 0.12), (EARTH[2], 0.06)), bias=-0.05), inside=True))
    S.add(box(-h2, h2, d - 3, d, 0, wall, planks, inside=True))
    S.add(box(-h2, -h2 + 3, 0, d, 0, wall, planks))
    S.add(box(h2 - 3, h2, 0, d, 0, wall, planks))
    post_m = lwood(TRIM, seed=5, bias=0.05, edge=True)
    xs = [-h2 + sw * i for i in range(stalls + 1)]
    for i, px in enumerate(xs):
        x0 = px - (0 if i == 0 else 1.5 if i < stalls else 3)
        S.add(box(x0, x0 + 3, -1, 2, 0, wall - 3, post_m))
    S.add(box(-h2, h2, -1, 2, wall - 3, wall, lwood(TRIM, seed=6, bias=0.1)))  # header beam
    for px in xs[1:-1]:  # stall partitions
        S.add(box(px - 1, px + 1, 2, d - 3, 0, 13, M.planks(WOOD, h=4, seed=round(px)), inside=True))
    hip_x_roof = __import__("oblique").hip_x
    S.add(hip_x_roof(-h2 - 5, h2 + 5, -5, d + 5, wall - 3, wall, wall + (d / 2 + 5) * 0.62, 14,
                     M.shingles(roof, seed=spec.get("seed", 1) + 5, moss=0.05)))
    zr0 = wall + (d / 2 + 5) * 0.62  # a vented cupola on the ridge
    S.add(box(-6, 6, d / 2 - 5, d / 2 + 5, zr0 - 4, zr0 + 7, M.boards(WHITE7, w=3, seed=3)))
    S.add(__import__("oblique").hip_x(-8, 8, d / 2 - 7, d / 2 + 7, zr0 + 6, zr0 + 7, zr0 + 13, 5,
                                      M.shingles(roof, seed=12, row_h=3)))
    for i in range(stalls):  # hay heaped at the back of each stall
        x0, x1 = xs[i] + 3, xs[i + 1] - 3
        S.add(box(x0, x1, d - 12, d - 3, 1, 6, hay_mat(seed=i), inside=True))
        S.add(box(x0 + 2, x1 - 3, d - 10, d - 3, 6, 9, hay_mat(seed=i + 5), inside=True))
    open_stall = spec.get("open_stall", 1)
    doors = []
    for i in range(stalls):
        if i == open_stall:
            continue
        x0, x1 = xs[i] + (1.5 if i else 3), xs[i + 1] - (1.5 if i < stalls - 1 else 3)
        S.add(box(x0, x1, -1, 0.5, 0, 12, M.boards(WOOD, w=3, seed=10 + i)))
        doors.append((x0, x1))
    tx0, tx1 = xs[2] + 3, xs[2] + sw - 3  # water trough before the third stall
    S.add(box(tx0, tx1, -8, -3, 0, 5, _trough_mat()))
    bx = h2 + 2  # hay bales to the right
    hay = M.flat(HAY)
    S.add(box(bx, bx + 12, -4, 4, 0, 7, hay))
    S.add(box(bx + 1, bx + 13, 5, 13, 0, 7, hay))
    S.add(box(bx + 2, bx + 12, 1, 9, 7, 14, hay))
    cv = S.render()
    inside_ids = {i for i, so in enumerate(S.solids) if so.params.get("inside")}
    from oblique import _shade
    for y in range(cv.h):  # the inside of the shed lies in the roof's shade
        for x in range(cv.w):
            if S.sid[y, x] in inside_ids and cv.shadow[y, x]:
                cv.px[x, y] = _shade(cv.px[x, y], 0.4)
    cv.on_wall(0.5)
    vx, vy = S.sx(0), S.sy(d / 2 - 5, zr0 + 3)
    for x in range(vx - 4, vx + 4):  # louvres in the cupola
        for y in range(vy - 3, vy + 3):
            cv.set(x, y, "#2a1d16" if (y - vy) % 2 == 0 else WHITE7[3])
    cv.on_wall(-1)
    for (x0, x1) in doors:  # cross braces on the half-doors
        x_door(cv, S.sx(x0), S.sx(x1), S.sy(-1, 12), S.sy(-1, 0), WOOD, trim=TRIM)
    cv.on_wall(-1, tol=1.2)
    for i, px in enumerate(xs[1:-1]):  # hinges, latch
        for x0, x1 in doors:
            if abs(x1 - px) < 2:
                cv.set(S.sx(x1) - 2, S.sy(-1, 6), IRON[2])
    # straw on the floor of the open stall, spilling out
    cv.at_depth(1)
    straw(cv, rnd, S.sx(xs[open_stall] + 3), S.sx(xs[open_stall + 1] - 4), S.sy(-1, 0), n=10)
    cv.at_depth(4)
    if spec.get("sheep", True):
        sheep(cv, S.sx(xs[open_stall] + 7), S.sy(4, 1))
    straw(cv, rnd, S.sx(-h2 + 4), S.sx(h2 - 4), S.sy(-3, 0), n=10)
    cv.free()
    lantern(cv, S.sx(xs[2] + 2), S.sy(-1, wall - 8))
    cv.at_depth(-9)
    tool(cv, S.sx(xs[1] - 4), S.sy(-2, 0), "pitchfork", h=24, lean=2)
    return done(S, cv, "farm", fpr(-h2, h2 + 15, -8, d))


def _trough_mat():
    """A plank trough: water inside its rim on top."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        if kind == "top":
            if x0 + 1.2 < P[0] < x1 - 1.2 and y0 + 1.2 < P[1] < y1 - 1.2:
                return GLASS[3] if (math.floor(P[0]) + math.floor(P[1] * 2)) % 7 == 0 else GLASS[1] if P[1] > y0 + 2.5 else GLASS[2]
            return WOOD[5]
        return M.planks(WOOD, h=2.5, seed=3).fn(u, v, kind, light, P, s)
    return Mat(f)


# ================================================================ greenhouse

BRICK = ["#2e1a16", "#4d2a22", "#6e3a2c", "#8c4c38", "#a65f46", "#bf7759", "#d6957a"]
SOIL = ["#1e1510", "#2e2018", "#3f2c1f", "#503827", "#614530", "#73533a", "#856244"]


def _glass_mat(frame, xs, zs, roof=False, door=None, k=0.3):
    """A pane of glass in a painted frame: bars come back opaque, panes as a tint with alpha < 255
    (the greenhouse composites the inside under them); glints run across some panes."""
    def f(u, v, kind, light, P, s):
        if roof and kind != "slope":
            return _t(frame, light + 0.1)  # the boards' edges: barge boards and fascia
        if roof:
            a, b = P[1], v  # along the ridge, up the slope
            if b < 1.2 or a % 8 < 1.2 or b % 10 < 1.0:
                return _t(frame, light + 0.25)
        else:
            a, b = P[0], P[2]
            if door and door[0] <= a < door[1] and b < door[2]:
                if a < door[0] + 1.5 or a >= door[1] - 1.5 or b >= door[2] - 1.5 or abs(b - door[3]) < 0.8:
                    return _t(frame, light + 0.2)
            else:
                for x in xs:
                    if x <= a < x + 1.5:
                        return _t(frame, light + 0.2)
                for z in zs:
                    if z <= b < z + 1.5:
                        return _t(frame, light + 0.2)
        g = (math.floor(a) + math.floor(b) * (1 if roof else 1)) % 13
        if g in (0, 1) and hsh(math.floor(a / 8), math.floor(b / 9), 3) < 0.6:
            return (236, 248, 250, 200)  # a glint
        if g == 3 and hsh(math.floor(a / 8), math.floor(b / 9), 4) < 0.4:
            return (214, 238, 244, 130)
        tint = (196, 226, 228) if light > 0.4 else (160, 196, 204)
        return (*tint, round(255 * k))
    return Mat(f)


def _far_glass_mat(frame):
    """The back of the glasshouse seen from inside: dim panes with the garden beyond."""
    def f(u, v, kind, light, P, s):
        a, b = P[0], P[2]
        if a % 8 < 1.2 or b % 9 < 1.0:
            return frame[2]
        hv = hsh(math.floor(a / 2), math.floor(b / 2), 9)
        return ["#4f6e5a", "#5a7d64", "#648a6c", "#6f9576"][min(3, int(hv * 4))]
    return Mat(f)


def _floor_mat(path_w):
    def f(u, v, kind, light, P, s):
        if kind != "top":
            return M.dressed_stone(BRICK, h=3, seed=2).fn(u, v, kind, light, P, s)
        if abs(P[0]) < path_w / 2:
            row = math.floor(P[1] / 2)
            k = (P[0] + (2 if row % 2 else 0)) % 4
            if P[1] % 2 < 0.6 or k < 0.6:
                return BRICK[2]
            return _t(BRICK, light + 0.05 + (hsh(math.floor((P[0] + (2 if row % 2 else 0)) / 4), row, 5) - 0.5) * 0.2)
        if hsh(math.floor(P[0]), math.floor(P[1]), 6) < 0.07:
            return LEAF[0]
        return _t(SOIL, light + (hsh(math.floor(P[0] / 2), math.floor(P[1] / 2), 7) - 0.5) * 0.3)
    return Mat(f)


def greenhouse(spec):
    """A glasshouse, gable to the front: a brick base, white glazing bars, panes of glass on the
    walls and the long roof slopes. Inside (seen through the tinted, glinting glass) a brick
    path between benches of potted plants, a lemon tree at the back, a hanging basket and a
    lantern that glows at night. A glazed door with a step."""
    rnd = random.Random(spec.get("seed", 1))
    h2, d, zb, zw, pitch = 28, 50, 5, 27, 0.7
    frame = WHITE7 if spec.get("frame", "white") == "white" else TRIM + ["#efd6aa", "#f6e4c4"]
    fm = M.wood(frame, bias=0.2)
    xs = [-h2, -h2 + 7, -h2 + 14, 13.5, 20.5, h2 - 1.5]
    zs = [zb, 17, zw - 1.5]
    dw, dh = 12, 19
    door_spec = (-dw / 2, dw / 2, zb + dh, zb + 10)
    pots = []

    def build(glass):
        S = Scene(pad_top=6)
        S.add(box(-h2, h2, 0, d, 0, zb, _floor_mat(12)))
        S.add(box(-h2, h2, d - 1, d, zb, zw, _far_glass_mat(frame)))
        S.add(gable_y(-h2, h2, d - 1, d, zw - 1, zw, zw + h2 * pitch, _far_glass_mat(frame)))
        for x0 in (-h2 - 1, h2 - 1):
            S.add(box(x0, x0 + 2, -1, d + 1, zw - 1.5, zw, fm))  # eave beams
        for x0 in (-h2, h2 - 2):
            S.add(box(x0, x0 + 2, 0, 2, zb, zw, fm))  # front corner posts
        zr_roof = zw + 0.2 + (h2 + 1) * pitch
        S.add(box(-1, 1, -1.5, d + 1.5, zr_roof - 1, zr_roof + 1, fm))  # ridge
        S.add(box(-8, 8, -4, 0, 0, 2.5, M.dressed_stone(STONE, seed=4, bias=0.2)))  # step
        # benches with pots along both sides, a lemon tree in a tub at the back
        bm = M.planks(WOOD, h=3, seed=4)
        for bx0, bx1 in ((-h2 + 2, -9), (9, h2 - 2)):
            S.add(box(bx0, bx1, 4, d - 4, 13, 14.5, bm))
            for ly in (5, d - 7):
                for lx in (bx0 + 1, bx1 - 3):
                    S.add(box(lx, lx + 2, ly, ly + 2, zb, 13, lwood(WOOD, seed=2)))
            for k, py in enumerate(range(9, d - 8, 7)):
                for j, px in enumerate((bx0 + 4, bx1 - 5)):
                    r = 2.5 if (j + k) % 2 else 2.0
                    S.add(prism(px, py, r, 14.5, 14.5 + r * 1.6, M.wood(TERRACOTTA, bias=0.15), sides=10))
                    if not glass:
                        pots.append((px, py, 14.5 + r * 1.6, (j + k + bx0) % 4))
        S.add(prism(0, d - 8, 4, zb, zb + 6, M.barrel(DARKWOOD, seed=3), sides=12))
        if glass:
            gm = _glass_mat(frame, xs, zs, door=door_spec)
            S.add(box(-h2, h2, 0, 1, zb, zw, gm, glass=True))
            S.add(gable_y(-h2, h2, 0, 1, zw - 1, zw, zw + h2 * pitch, _glass_mat(frame, [-1, -8, 7], []), glass=True))
            for sl in roof_shell_y(-h2 - 1, h2 + 1, -1, d + 1, zw + 0.2, zr_roof, 1, _glass_mat(frame, [], [], roof=True, k=0.36)):
                sl.params["glass"] = True
                S.add(sl)
        return S

    SA, SB = build(True), build(False)
    A = SA.render()
    B = SB.render()
    assert (SA.ox, SA.base, A.w, A.h) == (SB.ox, SB.base, B.w, B.h)
    S = SB
    # the inside, drawn before the glass goes over it: plants in the pots, the lemon tree, a basket
    plants = [("#3f7a37", "#5fa047", "#86c25a"), ("#2d5a2c", "#3f7a37", "#5fa047")]
    for (px, py, top, kind) in sorted(pots, key=lambda p: -p[1]):
        B.at_depth(py)
        sx, sy = S.s(px, py, top)
        _pot_plant(B, rnd, sx, sy, kind, plants[kind % 2])
    B.at_depth(d - 9)
    tx, ty = S.s(0, d - 8, zb + 6)
    _lemon_tree(B, rnd, tx, ty)
    B.free()
    # glass over the inside
    pa, pb = A.px, B.px
    glass_ids = {i for i, so in enumerate(SA.solids) if so.params.get("glass")}
    for y in range(A.h):
        for x in range(A.w):
            if SA.sid[y, x] not in glass_ids:
                continue
            g = pa[x, y]
            B.t[y, x] = A.t[y, x]
            B.shadow[y, x] = A.shadow[y, x]
            if g[3] == 255:
                pb[x, y] = g
                continue
            under = pb[x, y] if pb[x, y][3] else (70, 98, 62, 255)
            k = g[3] / 255
            dark = 0.82  # the inside is in shade
            pb[x, y] = (round(under[0] * dark * (1 - k) + g[0] * k), round(under[1] * dark * (1 - k) + g[1] * k),
                        round(under[2] * dark * (1 - k) + g[2] * k), 255)
    cv = B
    # a lantern hanging inside from the ridge, glowing through the roof at night
    cv.free()
    lx, ly = S.s(0, 8, zw + 10)
    for yy in range(ly - 8, ly):
        cv.set(lx, yy, IRON[1])
    for yy in range(ly, ly + 4):
        for xx in range(lx - 1, lx + 2):
            edge = xx != lx or yy in (ly, ly + 3)
            cv.set(xx, yy, IRON[1] if edge else "#f3dc9a")
            if not edge:
                cv.lit(xx, yy, LIT[4])
    for yy in range(ly - 1, ly + 5):  # its glow on the glass round it
        for xx in range(lx - 3, lx + 4):
            if (xx - lx) ** 2 + ((yy - ly - 1.5) * 1.2) ** 2 <= 10 and not (abs(xx - lx) <= 1 and ly <= yy < ly + 4):
                if cv.get(xx, yy)[3]:
                    cv.lit(xx, yy, LIT[1])
    # door handle, a watering can and pots by the door
    cv.on_wall(0)
    cv.set(S.sx(dw / 2 - 3), S.sy(0, zb + 9), "#e8c15a")
    cv.at_depth(-5)
    _watering_can(cv, S.sx(-h2 + 2), S.sy(-5, 0))
    cv.at_depth(-4)
    for px in (h2 - 10, h2 - 5):
        _small_pot(cv, rnd, S.sx(px), S.sy(-4, 0))
    return done(S, cv, "house", fpr(-h2, h2, 0, d), door_x=0, door_w=dw)


def _pot_plant(cv, rnd, sx, sy, kind, leaf):
    """A plant growing out of a pot whose rim is at (sx, sy)."""
    if kind == 0:  # tomatoes on a cane
        for j in range(9):
            cv.set(sx, sy - j, leaf[0] if j % 3 else leaf[1])
            if j % 2 == 0:
                cv.set(sx - 1 + (j % 4 == 0) * 2, sy - j, leaf[2])
        for dx, dy in ((-1, 3), (1, 6), (-1, 7)):
            cv.set(sx + dx, sy - dy, "#d8333a")
    elif kind == 1:  # a leafy clump
        for dx in range(-2, 3):
            for j in range(3 - abs(dx) // 2 + rnd.randint(0, 1)):
                cv.set(sx + dx, sy - j, leaf[min(2, j)])
    elif kind == 2:  # flowers
        for dx in (-1, 0, 1):
            for j in range(3):
                cv.set(sx + dx, sy - j, leaf[1 if j else 0])
        col = rnd.choice((("#ff9ec4", "#ffe066"), ("#ffe066", "#ffffff"), ("#c9b3ff", "#ffe066")))
        for dx, dy in ((-1, 3), (1, 3), (0, 4)):
            cv.set(sx + dx, sy - dy, col[0])
        cv.set(sx, sy - 3, col[1])
    else:  # seedlings
        for dx in (-1, 1):
            cv.set(sx + dx, sy - 1, leaf[2])
            cv.set(sx + dx, sy - 2, leaf[1])


def _lemon_tree(cv, rnd, sx, sy):
    for j in range(8):
        cv.set(sx, sy - j, WOOD[3])
    for y in range(sy - 20, sy - 6):
        for x in range(sx - 7, sx + 8):
            dd = ((x - sx) / 7.5) ** 2 + ((y - (sy - 13)) / 7) ** 2
            if dd <= 1 and rnd.random() < 0.95:
                c = LEAF7[5] if (x - sx) + (y - sy + 13) < -4 else LEAF7[4] if dd < 0.5 else LEAF7[3]
                if rnd.random() < 0.08:
                    c = "#f6e05a"
                cv.set(x, y, c)


def _watering_can(cv, x, bottom):
    for y in range(bottom - 5, bottom):
        for i in range(6):
            cv.set(x + i, y, METAL[5] if i < 2 else METAL[4] if i < 4 else METAL[3])
    for i in range(4):  # spout
        cv.set(x + 6 + i, bottom - 3 - i, METAL[4])
    cv.set(x + 9, bottom - 7, METAL[5])
    for i in range(1, 5):  # handle
        cv.set(x + i, bottom - 7, METAL[3])
    cv.set(x, bottom - 6, METAL[3])
    cv.set(x + 5, bottom - 6, METAL[3])


def _small_pot(cv, rnd, x, bottom):
    for j, (a, b) in enumerate(((0, 5), (0, 5), (1, 4), (1, 4))):
        for i in range(a, b):
            cv.set(x + i, bottom - 4 + j, TERRACOTTA[5] if j == 0 else TERRACOTTA[4] if i < 2 else TERRACOTTA[3])
    flower_tuft(cv, rnd, x + 2, bottom - 4, rnd.choice([("#ff9ec4", "#ffe066"), ("#ffe066", "#ffffff")]))


# ================================================================ silo

def _hoop_stone():
    """Stone courses with iron hoops every 16 px."""
    inner = M.dressed_stone(FIELDSTONE, h=4, seed=6)

    def f(u, v, kind, light, P, s):
        z = P[2] - s.bbox[4]
        if kind != "top" and z % 16 < 1.5 and z > 4:
            return IRON[2] if light > 0.4 else IRON[1]
        return inner.fn(u, v, kind, light, P, s)
    return Mat(f)


def silo(spec):
    """A tall round silo of riveted galvanised sheet (or stone with iron hoops) on a stone ring,
    a domed cap with a vent and a rooster weathervane, a caged ladder up the front, and a small
    feed room built against its foot with a chute down from the silo."""
    rnd = random.Random(spec.get("seed", 1))
    r, H = 14, 74
    cy = r
    stone = spec.get("material", "metal") == "stone"
    S = Scene(pad=6, pad_top=16)
    S.add(prism(0, cy, r + 2, 0, 4, M.dressed_stone(STONE, seed=2, bias=0.15), sides=24))
    body = _hoop_stone() if stone else corrugated(METAL, band=12)
    S.add(prism(0, cy, r, 4, H, body, sides=24))
    capm = M.shingles(ROOFS["slate"], seed=7, row_h=3) if stone else corrugated(METAL, band=40)
    S.add(prism(0, cy, r + 1, H, H + 2, M.flat(METAL), sides=24))
    for z0, z1, r0, r1 in ((H + 2, H + 7, r + 1, r - 2), (H + 7, H + 11, r - 2, r - 7), (H + 11, H + 13, r - 7, 2.5)):
        S.add(frustum(0, cy, r0, r1, z0, z1, capm, sides=24))
    S.add(prism(0, cy, 2.5, H + 13, H + 16, M.flat(METAL), sides=10))  # vent
    S.add(frustum(0, cy, 3.5, 0.5, H + 16, H + 18, M.flat(METAL), sides=10))
    annex = spec.get("annex", True)
    ax0, ax1 = -r - 24, -r + 3
    if annex:
        footing(S, ax0, ax1, 3, 25, seed=3)
        S.add(box(ax0, ax1, 3, 25, 4, 22, M.planks(DARKWOOD, seed=4)))
        S.add(slab(ax0 - 3, ax1 + 1, -1, 28, 21, 28, 2, M.shingles(ROOFS[spec.get("roof_colour", "rust")], seed=6)))
        # the chute from the silo's side down onto the annex roof
        a = np.array([-11.0, 0.0, -14.0])
        c = np.array([-r - 4, cy - 6, 38.0])
        S.add(obox(c, (a, (0, 1, 0), np.cross(a, (0, 1, 0))), (np.linalg.norm(a) / 2, 1.5, 1.5), M.flat(METAL)))
    cv = S.render()
    front = cy - r
    # ladder with a safety cage, up the front a little right of the middle
    lx0, lx1 = 5, 9
    cv.at_depth(front + r - math.sqrt(r * r - lx1 * lx1) - 1.2, tol=0.8)
    yl0 = cy - math.sqrt(r * r - lx0 * lx0) - 1
    yl1 = cy - math.sqrt(r * r - lx1 * lx1) - 1
    cv.free()
    rail_top = H + 3
    for lx, yl, c in ((lx0, yl0, IRON[2]), (lx1, yl1, IRON[1])):
        for z in range(5, rail_top):
            x, y = S.s(lx, yl, z)
            cv.set(x, y, c)
    for z in range(8, rail_top, 3):
        xa, ya = S.s(lx0, yl0, z)
        xb, yb = S.s(lx1, yl1, z)
        for x in range(xa + 1, xb):
            cv.set(x, ya + round((yb - ya) * (x - xa) / max(1, xb - xa)), STEEL[3])
    for z in range(26, rail_top, 7):  # cage hoops
        for i in range(0, 13):
            t = math.pi * i / 12
            xx = (lx0 + lx1) / 2 + 3.5 * math.cos(t)
            yy = (yl0 + yl1) / 2 - 3.5 * math.sin(t)
            x, y = S.s(xx, yy, z)
            cv.set(x, y, IRON[2] if i > 6 else STEEL[2])
    for k in (0.25, 0.5, 0.75):  # cage uprights
        t = math.pi * k
        xx = (lx0 + lx1) / 2 + 3.5 * math.cos(t)
        yy = (yl0 + yl1) / 2 - 3.5 * math.sin(t)
        for z in range(26, rail_top - 2):
            x, y = S.s(xx, yy, z)
            cv.set(x, y, IRON[1])
    # an access hatch at the foot of the silo
    cv.on_wall(front, tol=2.5)
    hx, hy = S.sx(-3), S.sy(front, 5)
    for y in range(hy - 11, hy):
        for x in range(hx - 4, hx + 4):
            edge = x in (hx - 4, hx + 3) or y == hy - 11
            cv.set(x, y, IRON[1] if edge else METAL[3] if x < hx else METAL[2])
    cv.set(hx + 2, hy - 5, STEEL[4])
    if annex:
        cv.on_wall(3)
        door(cv, rnd, S.sx((ax0 + ax1) / 2 + 2), S.sy(3, 4), w=12, h=16, style="plank", wood=WOOD, step=False)
        lantern(cv, S.sx((ax0 + ax1) / 2 + 10), S.sy(3, 15))
        cv.free()
        sack(cv, S.sx(ax0 + 1), S.sy(1, 0))
        sack(cv, S.sx(ax0 + 6), S.sy(0, 0))
    cv.free()
    # a rooster weathervane on the vent
    vx, vy = S.s(0, cy, H + 18)
    for y in range(vy - 7, vy):
        cv.set(vx, y, IRON[1])
    for x in range(vx - 3, vx + 4):
        cv.set(x, vy - 4, IRON[2])
    for ddx, ddy in ((-2, -8), (-1, -8), (0, -8), (1, -8), (-1, -9), (0, -9), (1, -9), (2, -9), (2, -10), (3, -10),
                     (-2, -9), (-3, -10), (-2, -10), (-3, -11), (2, -11), (3, -11), (2, -12)):
        cv.set(vx + ddx, vy + ddy, IRON[1])
    x0 = ax0 if annex else -r - 2
    return done(S, cv, "farm", fpr(x0, r + 2, -2, 2 * r + 2))


# ================================================================ shipping bin

def shipping_bin(spec):
    """The shipping bin: a stout box of boards bound with iron at the corners, a slanted lid on
    hinges, a gold coin painted on the front, crates stacked beside it and a sack."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=8)
    wood = PAINTS[spec.get("wood", "wood")]
    S.add(box(-13, 13, 0, 13, 0, 11, M.boards(wood, w=4, seed=3)))
    for x0 in (-14, 12):
        S.add(box(x0, x0 + 2, -1, 14, 0, 12, lwood(DARKWOOD, seed=4, bias=0.15, edge=True)))
    S.add(slab(-14.5, 14.5, -1.5, 14, 12, 16.5, 1.8, _lid_mat(wood)))
    S.add(box(16, 27, 1, 12, 0, 9, M.crate(WOOD)))
    S.add(box(17, 25, 3, 11, 9, 16, M.crate(WOOD)))
    S.add(box(-24, -16, 2, 10, 0, 7, M.crate(WOOD)))
    cv = S.render()
    cv.on_wall(-1, tol=1.2)
    for x0 in (-14, 12):  # iron corner plates with rivets
        for z in (2, 9):
            for y in range(S.sy(-1, z + 2), S.sy(-1, z - 1)):
                for x in range(S.sx(x0), S.sx(x0 + 2)):
                    cv.set(x, y, IRON[2] if x == S.sx(x0) else IRON[1])
            cv.set(S.sx(x0) + 1, S.sy(-1, z), STEEL[3])
    cv.on_wall(0)
    cx, cyy = S.sx(0), S.sy(0, 6)
    for y in range(cyy - 4, cyy + 5):  # a gold coin painted on the front
        for x in range(cx - 4, cx + 5):
            dd = (x - cx) ** 2 + (y - cyy) ** 2
            if dd <= 17:
                c = GOLD[1] if dd > 11 else GOLD[3] if (x - cx) + (y - cyy) < 0 else GOLD[2]
                if dd <= 4 and abs(x - cx) <= 0:
                    c = GOLD[4]
                cv.set(x, y, c)
    for dy in (-2, -1, 0, 1, 2):
        cv.set(cx, cyy + dy, GOLD[4] if dy < 0 else GOLD[3])
    cv.set(cx - 1, cyy - 1, GOLD[4])
    cv.set(cx + 1, cyy + 1, GOLD[3])
    cv.free()
    hx, hy = S.s(0, -1.5, 12)  # the lid's handle and hasp
    for x in range(hx - 3, hx + 3):
        cv.set(x, hy + 1, IRON[2])
    cv.set(hx - 3, hy, IRON[1])
    cv.set(hx + 2, hy, IRON[1])
    for y in range(hy + 1, hy + 4):
        cv.set(hx, y, IRON[1])
    cv.at_depth(6)
    for gx in range(S.sx(18), S.sx(24), 3):  # produce in the top crate
        from buildings import item
        item(cv, gx, S.sy(7, 16) + 1, rnd.choice(("apple", "orange", "cabbage")))
    cv.at_depth(-2)
    sack(cv, S.sx(-23), S.sy(-1, 0))
    cv.at_depth(5)
    from market import big_item
    big_item(cv, S.sx(-23), S.sy(5, 7) + 1, "pumpkin")
    return done(S, cv, "prop", fpr(-24, 27, -1, 14))


def _lid_mat(ramp):
    """The bin's lid: boards running back to the hinges, two iron straps, a dark rim."""
    boards = M.boards(ramp, w=4, seed=6, bias=0.18)

    def f(u, v, kind, light, P, s):
        if kind != "slope":
            return _t(DARKWOOD, light + 0.1)
        if abs(abs(P[0]) - 8.5) < 1:
            return IRON[2] if light > 0.5 else IRON[1]
        if s.bbox[1] - P[0] < 1 or P[0] - s.bbox[0] < 1:
            return _t(DARKWOOD, light + 0.15)
        return boards.fn(u, v, kind, light, P, s)
    return Mat(f)


# ================================================================ tool shed

def tool_shed(spec):
    """A small board shed under a shingled gable: a plank door with a lantern beside it, a little
    window, a rake, a hoe and a shovel leaning by the door, a saw and a coil of rope on hooks, and a
    lean-to on the side sheltering a rain barrel, a stack of firewood and a wheelbarrow wheel."""
    rnd = random.Random(spec.get("seed", 1))
    h2, d, wall = 19, 28, 27
    paint = PAINTS[spec.get("paint", "sage")]
    roof = ROOFS[spec.get("roof_colour", "bark")]
    walls = M.boards(paint, w=4, seed=spec.get("seed", 1))
    S = Scene(pad_top=6)
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, wall, walls))
    for px in (-h2 - 1, h2 - 2):
        S.add(box(px, px + 3, -1, d + 1, 4, wall, lwood(TRIM, seed=2, bias=0.1, edge=True)))
    gable_front(S, -h2, h2, 0, d, wall, 0.66, M.shingles(roof, seed=spec.get("seed", 1) + 1, moss=0.05), walls, over=4)
    # the lean-to on the right
    lx1 = h2 + 15
    S.add(lean_x(h2 - 1, lx1 + 1, 0, d - 2, wall - 4, 15, 1.5, M.shingles(roof, seed=9)))
    for py in (1, d - 5):
        S.add(box(lx1 - 2.5, lx1, py, py + 2.5, 0, 15 - 1.5 * (lx1 - 2.5 - h2) / (lx1 + 2 - h2) * 0, lwood(TRIM, seed=3)))
    S.add(prism(h2 + 6, 7, 4.5, 0, 11, M.barrel(seed=4), sides=12))
    S.add(box(h2 + 2, lx1 - 3, 13, d - 4, 0, 10, M.logs()))
    dcx = -5
    step(S, dcx, w=16, depth=4, h=3)
    cv = S.render()
    cv.on_wall(0)
    door(cv, rnd, S.sx(dcx), S.sy(0, 4), w=13, h=20, style="plank", wood=DARKWOOD, step=False)
    window(cv, rnd, S.sx(11), S.sy(0, 22), w=8, h=7, frame=TRIM)
    for y in range(S.sy(0, 23), S.sy(0, 13)):  # nobody works in there at night: only the lantern glows
        for x in range(S.sx(6), S.sx(16)):
            cv.unlit(x, y)
    # hooks with a saw and a coil of rope on the wall right of the door
    sx0, sy0 = S.sx(6), S.sy(0, 13)
    for i in range(8):  # saw
        cv.set(sx0 + i, sy0 + i // 3, STEEL[3])
        cv.set(sx0 + i, sy0 + 1 + i // 3, STEEL[2] if i % 2 else STEEL[1])
    cv.set(sx0 - 1, sy0, WOOD[4])
    cv.set(sx0 - 2, sy0, WOOD[4])
    cv.set(sx0 - 2, sy0 + 1, WOOD[3])
    rx, ry = S.sx(14), S.sy(0, 12)
    for y in range(ry - 3, ry + 4):
        for x in range(rx - 3, rx + 4):
            dd = (x - rx) ** 2 + (y - ry) ** 2
            if 3 <= dd <= 11:
                cv.set(x, y, "#c9a46a" if (x + y) % 2 else "#9a7a48")
    cv.set(rx, ry - 4, IRON[1])
    cv.free()
    lantern(cv, S.sx(dcx + 9), S.sy(0, 21))
    # tools leaning by the door
    cv.at_depth(-2)
    gy = S.sy(-2, 0)
    tool(cv, S.sx(-h2 + 3), gy, "rake", h=22, lean=2)
    tool(cv, S.sx(-h2 + 7), gy, "hoe", h=21, lean=2)
    tool(cv, S.sx(-h2 + 10), gy, "shovel", h=19, lean=1)
    cv.at_depth(-3)
    _bucket(cv, S.sx(3), S.sy(-3, 0))
    cv.at_depth(-1)
    wx, wy = S.s(lx1 - 6, -1, 5)  # a wheelbarrow tipped up against the lean-to post
    from market3d import _wheel
    _wheel(cv, wx, wy, 4)
    return done(S, cv, "house", fpr(-h2, lx1, -1, d), door_x=dcx, door_w=13)


def _bucket(cv, x, bottom):
    for j in range(5):
        for i in range(-2 + (1 if j > 2 else 0), 3 - (1 if j > 2 else 0)):
            cv.set(x + i, bottom - 5 + j, METAL[5] if i < 0 else METAL[4] if i < 1 else METAL[3])
    for i in range(-2, 3):
        cv.set(x + i, bottom - 5, METAL[2])
    for i, dy in ((-2, -6), (-1, -7), (0, -7), (1, -7), (2, -6)):
        cv.set(x + i, bottom + dy, IRON[2])


# ================================================================ beehives

HIVE_PAINTS = [CREAM, YELLOW7, MINT7, SKY7, PAINT["rose"]]


def _hive_mat(ramp, seed=1):
    """A painted hive box: smooth boards, a dark seam under its top edge."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + 0.1)
        z1 = s.bbox[5]
        if z1 - P[2] < 0.8:
            return _step(ramp, light, -2)
        if z1 - P[2] < 1.6:
            return _step(ramp, light + 0.2, 1)
        g = -0.1 if hsh(math.floor(u / 3), math.floor(P[2] / 2), seed) < 0.08 else 0
        return _t(ramp, light + 0.15 + g)
    return Mat(f)


def beehives(spec):
    """Two or three stacked-box beehives in pastel paints on a plank stand over stone blocks,
    each with a lid (one a little peaked roof), an entrance slit over a landing board and hand
    holds on its boxes; lavender at their feet and bees about them (an animated sprite, 8
    frames: "bees", with a few drawn sitting on the landing boards)."""
    rnd = random.Random(spec.get("seed", 1))
    n = spec.get("hives", 3)
    gap = 16
    xs = [(i - (n - 1) / 2) * gap for i in range(n)]
    half = xs[-1] + 9
    S = Scene(pad_top=10)
    for bx in (-half + 1, -2, half - 5) if n > 2 else (-half + 1, half - 5):
        S.add(box(bx, bx + 4, 2, 12, 0, 4, M.dressed_stone(STONE, seed=3, bias=0.15)))
    S.add(box(-half, half, 1, 13, 4, 5.5, M.planks(WOOD, h=3, seed=4, bias=0.1)))
    stacks = spec.get("stacks", [[7, 6], [7, 6, 6], [7, 6]])
    paints = spec.get("paints", [1, 0, 2])
    tops = []
    for i, xc in enumerate(xs):
        z = 5.5
        ramp = HIVE_PAINTS[paints[i % len(paints)]]
        S.add(box(xc - 6, xc + 6, 2.5, 12, z, z + 1.5, lwood(DARKWOOD, seed=i, bias=0.15)))  # floor with the entrance
        z += 1.5
        for k, h in enumerate(stacks[i % len(stacks)]):
            S.add(box(xc - 6, xc + 6, 2.5, 12, z, z + h, _hive_mat(ramp if k % 2 == 0 else ramp, seed=i * 5 + k)))
            z += h
        S.add(box(xc - 6.5, xc + 6.5, 2, 12.5, z, z + 1, lwood(WHITE7, seed=i, bias=0.1, grain=0)))  # lid rim
        roofs = spec.get("roofs", ["bark", "moss", "slate"])
        S.add(gable_x(xc - 7.5, xc + 7.5, 0.5, 14, z + 0.5, z + 1, z + 5.5,
                      M.shingles(ROOFS[roofs[i % len(roofs)]], seed=3 + i, row_h=2)))
        z += 5.5
        tops.append(z)
        S.add(box(xc - 4, xc + 4, -0.5, 2.5, 5.5, 6.5, lwood(WOOD, seed=i + 3, bias=0.2)))  # landing board
    cv = S.render()
    for i, xc in enumerate(xs):
        cv.on_wall(2.5)
        ey = S.sy(2.5, 7)
        for x in range(S.sx(xc - 3), S.sx(xc + 3)):
            cv.set(x, ey, "#1a120c")
        z = 7
        for h in stacks[i % len(stacks)]:
            hy = S.sy(2.5, z + h * 0.6)
            for x in range(S.sx(xc - 2), S.sx(xc + 2)):
                cv.set(x, hy, _darker(cv.get(x, hy)))
            z += h
        cv.at_depth(0)
        for k in range(rnd.randint(1, 3)):  # bees on the landing board
            bx = S.sx(xc - 3) + rnd.randint(0, 6)
            by = S.sy(0.5, 6.5)
            cv.set(bx, by, "#f2c230")
            cv.set(bx + 1, by, "#2a1a12")
    cv.free()
    lav = [(S.sx(-half + 3 + k * (2 * half - 6) / 6) + rnd.randint(-1, 1), S.sy(-3, 0) + rnd.randint(0, 1))
           for k in range(7)]

    def lavender(c):
        for (x, y) in lav:  # drawn after the outline, so the stalks stay fine
            for k in range(rnd.randint(3, 4)):
                bx = x + k * 2 - 3 + rnd.randint(0, 1)
                h = rnd.randint(4, 6)
                for j in range(h):
                    c.set(bx + (1 if j > h - 3 and k % 2 else 0), y - j, LEAF[0] if j < 2 else LEAF[1])
                for j in range(h - 2, h + 1):
                    c.set(bx + (1 if k % 2 else 0), y - j, "#9a7ad6" if j % 2 else "#c9b3ff")
    # bees flying: a separate sprite of 8 frames
    F = 8
    bw, bh = round(2 * half + 12), 30
    sheet = Image.new("RGBA", (bw * F, bh), (0, 0, 0, 0))
    paths = []
    for k in range(spec.get("bees", 9)):
        cx = rnd.uniform(-half + 2, half - 2) + bw / 2
        cyb = rnd.uniform(8, 22)
        paths.append((cx, cyb, rnd.uniform(3, 7), rnd.uniform(2, 4), rnd.uniform(0, 6.28), rnd.choice((1, 2))))
    for f in range(F):
        px = sheet.load()
        for (cx, cyb, rx, ry, ph, sp) in paths:
            t = ph + 2 * math.pi * f * sp / F
            x = round(f * bw + cx + rx * math.sin(t))
            y = round(cyb + ry * math.sin(2 * t))
            if 0 <= y < bh - 1 and f * bw <= x < (f + 1) * bw - 1:
                px[x, y] = (242, 194, 48, 255)
                px[x + 1, y] = (42, 26, 18, 255)
                if f % 2 == 0:
                    px[x, y - 1] = (230, 240, 250, 220)
    mid_y = S.sy(7, (max(tops) + 5.5) / 2 + 4) - S.base
    im, night, info = done(S, cv, "prop", fpr(-half, half, -0.5, 13), after=lavender)
    info["bees"] = [0, mid_y]
    info["bees_frames"] = F
    info["bees_fps"] = 8
    return im, night, info, {"bees": sheet}


def _darker(c):
    r, g, b, a = c
    return (round(r * 0.55 + 22 * 0.45), round(g * 0.55 + 18 * 0.45), round(b * 0.55 + 34 * 0.45), a) if a else c


# ================================================================ compost bin

def compost_bin(spec):
    """A two-bay compost bin of slatted boards: the left bay full and heaped, the right bay's
    front boards partly lifted out to show the dark compost, fresh greens, peel and eggshell on
    top, a fork stuck in the heap and a pail of scraps beside it."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=8)
    inside = COMPOST[1]
    sl = slats(WOOD, inside, h=3, gap=1, seed=2)
    S.add(box(-22, 22, 15, 17, 0, 13, sl))  # back
    for x0 in (-22, -1, 20):
        S.add(box(x0, x0 + 2, 0, 17, 0, 13, slats(WOOD, inside, h=3, gap=1, seed=3)))
    for x0 in (-23, -2, 19):  # corner posts
        S.add(box(x0, x0 + 4 if x0 != -2 else x0 + 4, -0.5, 2, 0, 14, lwood(DARKWOOD, seed=x0, bias=0.15, edge=True)))
    S.add(box(-20, -1, 0, 2, 0, 12, sl))  # left front
    S.add(box(1, 20, 0, 2, 0, 4, slats(WOOD, inside, h=3, gap=1, seed=5)))  # right front, boards out
    cm = ground(COMPOST, seed=3, specks=(("#3f7a37", 0.04), ("#5fa047", 0.03), (COMPOST[5], 0.06), ("#c9662a", 0.01)))
    S.add(box(-20, -1, 2, 15, 0, 10, cm))
    S.add(frustum(-10.5, 8.5, 7, 3.5, 10, 14, cm, sides=12))
    S.add(box(1, 20, 2, 15, 0, 7, cm))
    cv = S.render()
    # fresh scraps on top of the right bay and the heap
    for (x0, x1, y0, y1, z) in ((2, 19, 3, 14, 7), (-17, -4, 5, 12, 13.5)):
        for _ in range(14 if z < 10 else 9):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            cv.at_depth(y)
            sx, sy = S.s(x, y, z)
            kind = rnd.random()
            if kind < 0.45:  # green leaves
                c = rnd.choice(LEAF)
                cv.set(sx, sy, c)
                cv.set(sx + 1, sy, LEAF[0])
                cv.set(sx, sy - 1, LEAF[2])
            elif kind < 0.65:  # orange peel, carrot tops
                cv.set(sx, sy, "#e0802a")
                cv.set(sx + 1, sy, "#b05a1a")
            elif kind < 0.8:  # eggshell
                cv.set(sx, sy, "#f6f0e1")
                cv.set(sx + 1, sy, "#d8cfbf")
            else:  # brown leaves
                cv.set(sx, sy, "#9a6a2e")
                cv.set(sx, sy - 1, "#b8823a")
    cv.at_depth(8)
    fx, fy = S.s(-7, 8, 13)
    tool(cv, fx, fy + 2, "pitchfork", h=20, lean=-3)
    cv.at_depth(-3)
    _bucket(cv, S.sx(25), S.sy(-2, 0))
    for dx, c in ((-2, LEAF[2]), (0, "#e0802a"), (1, LEAF[1])):
        cv.set(S.sx(25) + dx, S.sy(-2, 0) - 6, c)
    return done(S, cv, "prop", fpr(-23, 23, -0.5, 17))


# ================================================================ scarecrow

def _plaid(a, b, w=3):
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(a, light + 0.1)
        cu, cv_ = math.floor(u / w) % 2, math.floor(P[2] / w) % 2
        r = a if cu == cv_ else b
        lv = light + 0.12 + (0.1 if cu and cv_ else 0)
        return _t(r, lv)
    return Mat(f)


def _burlap(ramp):
    def f(u, v, kind, light, P, s):
        k = (math.floor(u) + math.floor(P[2])) % 2
        return _t(ramp, light + 0.15 + (0.06 if k else -0.04))
    return Mat(f)


SACK = ["#3a2a18", "#5c4528", "#80643c", "#a08250", "#bba06a", "#d2ba86", "#e6d4a8"]
DENIM = ["#141c2e", "#22304c", "#33476c", "#46608c", "#5f7caa", "#7f9cc4", "#a8c0dc"]


def scarecrow(spec):
    """A scarecrow on a post and cross-bar: a plaid shirt and patched trousers stuffed with straw
    poking out of the cuffs, a burlap head with a stitched face, a wide straw hat, and a crow
    perched on one arm."""
    rnd = random.Random(spec.get("seed", 1))
    shirt = _plaid(_cloth7(spec.get("shirt", "red")), _cloth7(spec.get("shirt2", "ochre")))
    S = Scene(pad=8, pad_top=10)
    S.add(frustum(0, 4, 4.5, 2, 0, 2, hay_mat(3), sides=10))
    S.add(box(-1, 1, 3, 5, 0, 31, lwood(WOOD, seed=2, bias=0.15)))  # the post
    S.add(box(-16, 16, 3.5, 5, 25, 26.5, lwood(WOOD, seed=3, bias=0.2)))  # the cross-bar
    S.add(box(-4.5, -0.5, 2.5, 5.5, 5, 15, _burlap(DENIM)))  # trouser legs
    S.add(box(0.5, 4.5, 2.5, 5.5, 5, 15, _burlap(DENIM)))
    S.add(box(-5, 5, 2, 6, 14, 27, shirt))
    S.add(box(-13.5, -5, 2.5, 5.5, 23, 27, shirt))  # sleeves
    S.add(box(5, 13.5, 2.5, 5.5, 23, 27, shirt))
    S.add(prism(0, 4, 4.5, 27, 36, _burlap(SACK), sides=12))  # head
    straw_hat = _burlap(HAY7)
    S.add(prism(0, 4.5, 6.5, 35.5, 36.5, straw_hat, sides=16))
    S.add(frustum(0, 5, 4.4, 3.4, 36.5, 41, straw_hat, sides=12))
    cv = S.render()
    # straw out of the cuffs, collar and trouser hems
    for (x, z, dirx) in ((-13.5, 25, -1), (13.5, 25, 1)):
        for k in range(5):
            sx, sy = S.s(x, 2, z - 1.5 + k * 0.8)
            for i in range(rnd.randint(1, 3)):
                cv.set(sx + dirx * (i + 1), sy + rnd.randint(-1, 1), HAY[2 + (k + i) % 3])
    for k in range(7):
        sx, sy = S.s(-4 + k * 1.3, 2, 5)
        for i in range(rnd.randint(1, 3)):
            cv.set(sx, sy + i, HAY[2 + (k + i) % 3])
    for k in range(6):
        sx, sy = S.s(-3 + k * 1.2, 2, 27)
        cv.set(sx, sy - 1, HAY[3 + k % 2])
    # face
    cv.on_wall(0, tol=1.5)
    fx, fy = S.s(0, -0.5, 31)
    for dx in (-2, 2):  # button eyes
        cv.set(fx + dx, fy - 1, "#1c1a1f")
    for dx in range(-2, 3):  # stitched grin
        cv.set(fx + dx, fy + 2 - (1 if abs(dx) == 2 else 0), "#3a2a18")
    cv.set(fx - 1, fy + 3, "#3a2a18")
    cv.set(fx + 1, fy + 3, "#3a2a18")
    # hat band, a patch on the trousers, a patch on the shirt
    cv.on_wall(1.1, tol=2.0)
    for x in range(S.sx(-4), S.sx(4)):
        cv.set(x, S.sy(1.1, 37.5), "#7a2629")
    cv.on_wall(2.5)
    for y in range(S.sy(2.5, 10), S.sy(2.5, 7)):
        for x in range(S.sx(1.5), S.sx(4)):
            cv.set(x, y, "#a8383a" if (x + y) % 2 else "#cf5652")
    cv.on_wall(2)
    for y in range(S.sy(2, 20), S.sy(2, 17)):
        for x in range(S.sx(-4), S.sx(-1)):
            cv.set(x, y, "#5a965c" if (x + y) % 2 else "#3f7447")
    cv.free()
    # the crow on the right arm
    if spec.get("crow", True):
        cx, cy = S.s(11, 4, 27)
        _crow(cv, cx, cy)
    return done(S, cv, "prop", fpr(-3, 3, 1, 7))


def _cloth7(name):
    r = CLOTH[name]
    return [r[0], r[0], r[1], r[2], r[3], r[4], r[4]]


def _crow(cv, x, bottom, right=True):
    """A crow 7 px long perched with its feet at (x, bottom), facing left."""
    rows = ["..kk...",
            ".kgkk..",
            "ykkkkkk",
            "..kkkkkk",
            "...o.o.."]
    cols = {"k": "#1c1a24", "g": "#4a4a5e", "y": "#d8a830", "o": "#3a3440"}
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in cols:
                cv.set(x - 3 + i, bottom - len(rows) + j + 1, cols[ch])
    cv.set(x - 1, bottom - 4, "#e8e8f0")  # eye glint


# ================================================================ grape arbour

def trellis(spec):
    """A grape arbour: six square posts carrying beams and cross-pieces, a mat of vine leaves over
    the top spilling down the front, bunches of grapes hanging under the front beam, the twisting
    old vines climbing the front posts, and a basket of picked grapes."""
    rnd = random.Random(spec.get("seed", 1))
    h2, d, zt = 28, 20, 28
    grapes = GRAPE if spec.get("grapes", "purple") == "purple" else ["#2a3a10", "#4f6a1a", "#7a9a2a", "#a8c84a", "#d6ec8a"]
    pm = lwood(WOOD, seed=3, bias=0.15, edge=True)
    S = Scene(pad=8, pad_top=8)
    for px in (-h2, -1.5, h2 - 3):
        for py in (0, d - 3):
            S.add(box(px, px + 3, py, py + 3, 0, zt, pm))
    for py in (0, d - 3):
        S.add(box(-h2 - 3, h2 + 3, py, py + 3, zt - 3, zt, lwood(WOOD, seed=4, bias=0.2)))
    for x in range(-h2 + 2, h2, 6):
        S.add(box(x, x + 1.5, -2.5, d + 2.5, zt, zt + 1.5, lwood(WOOD, seed=5 + x, bias=0.2)))
    cv = S.render()
    # the vine over the top: clusters of leaves drawn back to front over the beams
    clusters = []
    for _ in range(spec.get("leaves", 70)):
        clusters.append((rnd.uniform(-h2 - 1, h2 + 1), rnd.uniform(-1, d + 1), zt + 1.5 + rnd.uniform(0, 3),
                         rnd.uniform(2.5, 4.5)))
    for (x, y, z, r) in sorted(clusters, key=lambda c: -c[1]):
        cv.at_depth(y, tol=40)
        cx, cy = S.s(x, y, z)
        _leaf_blob(cv, rnd, cx, cy, r, grapes)
    # leaves spilling over the front beam
    cv.at_depth(-1.5)
    by = S.sy(-1, zt)
    for x in range(S.sx(-h2 - 2), S.sx(h2 + 2)):
        n = rnd.choice((0, 1, 2, 2, 3, 4)) if hsh(x, 2) > 0.25 else 0
        for j in range(n):
            cv.set(x, by - 2 + j, LEAF7[3 + (1 if (x + j) % 3 == 0 else 0) - (1 if j == n - 1 else 0)])
    # bunches of grapes under the front beam
    cv.at_depth(1.5)
    for x in (-23, -15, -8, 5, 12, 20) if spec.get("bunches", True) else ():
        bx = S.sx(x + rnd.uniform(-1.5, 1.5))
        _bunch(cv, bx, S.sy(1.5, zt - 3), grapes, rnd)
    # old vines up the front posts
    cv.at_depth(-0.5)
    for px in (-h2 + 1.5, h2 - 1.5, 0):
        x0 = S.sx(px)
        for z in range(0, zt):
            x = x0 + round(1.2 * math.sin(z * 0.45 + px))
            y = S.sy(-0.5, z)
            cv.set(x, y, "#5a3d26" if z % 3 else "#3d281a")
            cv.set(x + 1, y, "#3d281a")
            if z > 8 and rnd.random() < 0.18:
                cv.set(x - 1, y, LEAF7[4])
                cv.set(x - 2, y - 1, LEAF7[3])
    cv.at_depth(-6)
    bx, bb = S.sx(10), S.sy(-6, 0)
    for y in range(bb - 4, bb):
        for i in range(9):
            c = "#c9a061" if (i + y) % 2 == 0 else "#9b7642"
            if i in (0, 8) or y == bb - 1:
                c = "#6b4e2a"
            cv.set(bx + i, y, c)
    for i in range(1, 8, 3):
        _bunch(cv, bx + i, bb - 7, grapes, rnd, small=True)
    return done(S, cv, "prop", fpr(-h2, h2, 0, d))


def _leaf_blob(cv, rnd, cx, cy, r, fruit=None):
    """A round cluster of vine leaves lit from the upper left, darker at its rim."""
    ry = r * 0.8
    for y in range(round(cy - ry) - 1, round(cy + ry) + 2):
        for x in range(round(cx - r) - 1, round(cx + r) + 2):
            nx, ny = (x + 0.5 - cx) / r, (y + 0.5 - cy) / ry
            dd = nx * nx + ny * ny
            if dd > 1 or (dd > 0.75 and rnd.random() < 0.35):
                continue
            lv = 0.62 - 0.32 * nx - 0.32 * ny + rnd.uniform(-0.12, 0.12) - (0.25 if dd > 0.7 else 0)
            c = LEAF7[max(1, min(6, round(1 + lv * 5)))]
            if fruit and rnd.random() < 0.025:
                c = fruit[3]
            cv.set(x, y, c)


def _bunch(cv, x, top, ramp, rnd, small=False):
    """A bunch of grapes hanging from (x, top): rows narrowing to a point, a leaf at the stalk."""
    widths = (4, 4, 3, 2, 1) if not small else (3, 2, 1)
    cv.set(x + 1, top, "#5a3d26")
    for j, w in enumerate(widths):
        x0 = x + (4 - w) // 2 - (1 if small else 0)
        for i in range(w):
            k = (i + j) % 2
            c = ramp[3] if k == 0 and i == 0 else ramp[2] if k == 0 else ramp[1]
            if j == 0 and i == 0:
                c = ramp[4]
            cv.set(x0 + i, top + 1 + j, c)
    if not small:
        cv.set(x + 3, top, LEAF7[4])
        cv.set(x + 4, top, LEAF7[3])
        cv.set(x + 4, top - 1, LEAF7[5])


# ================================================================ catalogue

def picket_x(spec):
    return fence_x({**spec, "style": "picket"})


def picket_y(spec):
    return fence_y({**spec, "style": "picket"})


def picket_gate(spec):
    return fence_gate({**spec, "style": "picket"})


DESIGNS = {
    "coop": coop, "animal_shed": animal_shed, "greenhouse": greenhouse, "silo": silo, "shipping_bin": shipping_bin,
    "tool_shed": tool_shed, "beehives": beehives, "compost_bin": compost_bin, "scarecrow": scarecrow,
    "trellis": trellis, "fence_x": fence_x, "fence_y": fence_y, "fence_gate": fence_gate,
    "picket_x": picket_x, "picket_y": picket_y, "picket_gate": picket_gate,
}

ENTRIES = [
    {"id": "coop", "name": "鸡舍", "group": FARM, "type": "coop", "seed": 1, "roof_colour": "rust"},
    {"id": "animal_shed", "name": "畜棚", "group": FARM, "type": "animal_shed", "seed": 1},
    {"id": "greenhouse", "name": "温室", "group": FARM, "type": "greenhouse", "seed": 1},
    {"id": "silo", "name": "筒仓", "group": FARM, "type": "silo", "seed": 1},
    {"id": "shipping_bin", "name": "出货箱", "group": FARM, "type": "shipping_bin", "seed": 1},
    {"id": "tool_shed", "name": "工具棚", "group": FARM, "type": "tool_shed", "seed": 1},
    {"id": "beehives", "name": "蜂箱", "group": FARM, "type": "beehives", "seed": 1},
    {"id": "compost_bin", "name": "堆肥箱", "group": FARM, "type": "compost_bin", "seed": 1},
    {"id": "scarecrow", "name": "稻草人", "group": FARM, "type": "scarecrow", "seed": 1},
    {"id": "trellis", "name": "葡萄架", "group": FARM, "type": "trellis", "seed": 1},
    {"id": "fence_x", "name": "木栅栏(横)", "group": FARM, "type": "fence_x"},
    {"id": "fence_y", "name": "木栅栏(纵)", "group": FARM, "type": "fence_y"},
    {"id": "fence_gate", "name": "木栅栏门", "group": FARM, "type": "fence_gate"},
    {"id": "picket_x", "name": "白栅栏(横)", "group": FARM, "type": "picket_x"},
    {"id": "picket_y", "name": "白栅栏(纵)", "group": FARM, "type": "picket_y"},
    {"id": "picket_gate", "name": "白栅栏门", "group": FARM, "type": "picket_gate"},
]
