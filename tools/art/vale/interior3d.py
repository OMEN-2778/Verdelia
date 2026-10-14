"""Room walls and furniture for interior maps, modelled in 3D for the oblique renderer
(oblique.py) in the game's front-on, 45-degrees-from-above view.

An interior is drawn in the map editor like the town: the floor is a ground type (planks or
flags), and the room is put together from these pieces.

- Back-wall segments, 32 px wide and 40 px high, stand in a row along the back of a room and tile
  seamlessly end to end (patterns repeat every 32 px, no outline at the ends): wallpaper above a
  panelled wainscot and a skirting board, a cornice, and the wall's cut top edge. Variants carry
  a window (daylight through the glass, deep reveal and sill, curtains), a framed picture or
  shelves of jars.
- Side-wall segments run 32 px back on the map and stack down the sides of a room: mostly their
  top edge, plus a sliver of the inner face (the room side: right for a left wall, left for a
  right wall). Corner posts hide the joins at the corners.
- Furniture stands in front of them: beds, a kitchen range, a fireplace (its fire is an animated
  sprite in lamplight colours, so it glows at night), a table with chairs, a chair, a kitchen
  dresser, a wardrobe, a bookshelf, a shop counter, a chest, a potted plant, a floor lamp, rugs.

Footprints are what blocks walking. The map editor keeps 2 px between footprints, so the
segments' footprints stop 1 px short of their tiling ends (rows of them can still be placed
32 px apart).
"""
import math
import random

from PIL import Image

import materials as M
from buildings import BRASS, C, DARKWOOD, FIELDSTONE, IRON, LEAF, LIT, STONE, TRIM, WOOD, Canvas, _result, item, tone
from market import CLOTH, GOLD, WHITE, candle, jug
from oblique import K, Mat, Scene, box, frustum, hsh, prism, prism_x

GROUP = "室内"
WALL_H = 40  # room wall height
WALL_T = 6  # back wall thickness (world y)
SEG = 32  # segment length; every wall pattern repeats with this period
SIDE_D = 40  # side wall segment depth in world y: 32 px on the map

IRONK = ["#0e0d11", "#19171d", "#25232a", "#34313b", "#46424f", "#5d5967", "#7d7988"]  # blackened iron
BRASSR = ["#3a2608", "#5e3f0e", "#8f6418", "#bb8a2c", "#ddb04a", "#f1d27a", "#fff0b8"]
COPPERR = ["#2e170c", "#5a2e16", "#8a4a26", "#b4683a", "#d68a52", "#eeb07c", "#f8d3ac"]
CLAY = ["#3a1a10", "#6a2e1a", "#94442a", "#b85e3a", "#d07c50", "#e49c70", "#f0c09a"]
LINEN = ["#6e665c", "#a39a8c", "#cfc7b8", "#e6dfd2", "#f3eee4", "#fbf8f2", "#ffffff"]
SOOT = ["#120e0d", "#1d1716", "#2a2220", "#382e2a", "#463a35", "#574a43", "#6a5b52"]
BARK = ["#24170f", "#3b261a", "#553723", "#6f4a2e", "#8a5f3b", "#a6794f", "#c49a6c"]
HONEY = ["#2c1a0c", "#4f2f16", "#7a4a22", "#9c6430", "#bb8044", "#d39f62", "#e8c08a"]  # pale polished wood
LEAVES = ["#1a3320", "#24482a", "#2f5f33", "#3f7a3b", "#57974a", "#78b35c", "#a3d07a"]
PAPERS = {  # wallpaper ramp, (flower, leaf) of its sprig
    "sage": (["#22302a", "#34473c", "#4b6252", "#5f7a66", "#759079", "#8fa98f", "#b3c8ad"], ("#efe3bd", "#3d5544")),
    "rose": (["#3a2226", "#5c3639", "#7e4f50", "#9a6865", "#b4837d", "#cca29a", "#e3c6bd"], ("#f6ead6", "#6f8a5e")),
    "cream": (["#4a3b2c", "#7d6a52", "#a99475", "#c4b08e", "#d8c7a6", "#e8dbc0", "#f4ecd9"], ("#b0503a", "#6f8a5a")),
    "blue": (["#1c2636", "#2e3d55", "#435673", "#5a6f8f", "#7489a8", "#94a8c2", "#bccbdc"], ("#f1e8d0", "#d9b45a")),
}
PATCH = [["#5e2426", "#9c4040", "#c4635c"], ["#7a5c26", "#bf9a4c", "#dfc07c"], ["#8f8674", "#ddd3bd", "#f3ecdc"],
         ["#344c62", "#56789a", "#86a6c0"], ["#43573a", "#6b8656", "#97b082"], ["#8f8674", "#ddd3bd", "#f3ecdc"]]
JARS = {  # contents of a preserving jar: dark, mid, light
    "jam": ("#4a1020", "#9e2a3a", "#d0505a"), "honey": ("#6a3a08", "#c98a1e", "#f0c050"),
    "pickle": ("#24401a", "#5a8a2e", "#9ac060"), "plum": ("#2c1a3a", "#5a3a72", "#8a6aa8"),
    "flour": ("#8a7a5a", "#c4b48a", "#ece2c4"), "peach": ("#8a3e14", "#e08a3a", "#f6c27a"),
}


def _t(ramp, v):
    return ramp[tone(ramp, v)]


def _st(ramp, v, k):
    return ramp[max(1, min(len(ramp) - 1, tone(ramp, v) + k))]


def _r7(r):
    """A 5-tone cloth ramp padded to 7 for tone()."""
    return [r[0], r[0], r[1], r[2], r[3], r[4], r[4]]


def done(S, cv, kind, footprint, extra=None, **flags):
    S.finish(cv)
    im, night, info = _result(cv, kind, (S.ox, S.base), footprint)
    info.update(flags)
    return (im, night, info) if extra is None else (im, night, info, extra)


def fp(x0, x1, d, back=0.0):
    """Footprint of ground x0..x1 from the front (y=0) back to y=d (world), relative to the base point."""
    y0, y1 = round(K * back), round(K * d)
    return [round(x0), -y1, round(x1 - x0), y1 - y0]


# ================================================================ walls

def _cap(along, across, depth, light):
    """The cut top edge of a wall: a dark beam, its grain running along the wall."""
    if across > depth - 1.1:
        return DARKWOOD[2]
    if hsh(math.floor(along / 5), math.floor(across * 0.8), 11) < 0.2:
        return _st(DARKWOOD, light, -1)
    return _t(DARKWOOD, light + 0.02)


def _face(X, Z, light, paper, panel=WOOD, stiles=True):
    """A room wall's face at x (mod 32) and height Z: skirting, panelled wainscot, chair rail,
    wallpaper with a stripe and staggered sprigs, a cornice under the top."""
    ramp, (m1, m2) = PAPERS[paper]
    lv = light
    if Z < 3:  # skirting board
        return DARKWOOD[5] if Z == 2 else DARKWOOD[3] if Z == 1 else DARKWOOD[2]
    if Z < 13:  # wainscot: rails and stiles round recessed fields
        if Z == 3:
            return _st(panel, lv, -1)
        if Z == 4:
            return _t(panel, lv)
        if Z == 11:
            return _t(panel, lv)
        if Z == 12:
            return _st(panel, lv, 1)
        g = X % 16 if stiles else 8
        if g == 0:
            return _st(panel, lv, 1)
        if g == 1:
            return _t(panel, lv)
        if g == 2 or Z == 10:
            return _st(panel, lv, -2)  # the frame's shadow in the recess
        if g == 15 or Z == 5:
            return _st(panel, lv, 1)  # the recess's lit lower and right edges
        if hsh(X % SEG // 2, Z // 3, 5) < 0.12:
            return _st(panel, lv, -1)
        return _t(panel, lv + 0.1)
    if Z < 16:  # chair rail
        return (DARKWOOD[2], _t(panel, lv + 0.1), _st(panel, lv, 2))[Z - 13]
    if Z >= 37:  # cornice
        return (_st(panel, lv, 1), _st(panel, lv, -1), _st(panel, lv, 1))[min(2, Z - 37)]
    if Z == 36:
        return _st(ramp, lv + 0.12, -2)  # shadow under the cornice
    if Z == 16:
        return _st(ramp, lv + 0.12, -1)
    g = X % 8
    if g == 0:
        return _st(ramp, lv + 0.12, -1)  # fine stripe
    zz = (Z - 17 + (4 if (X // 8) % 2 else 0)) % 8
    if g == 4 and zz == 2:
        return m1
    if (g in (3, 5) and zz == 3) or (g == 4 and zz == 4):
        return m2
    return _t(ramp, lv + 0.12)


def wall_mat(paper):
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _cap(math.floor(P[0]) % SEG, P[1] - s.bbox[2], s.bbox[3] - s.bbox[2], light)
        return _face(math.floor(u) % SEG, math.floor(v), light, paper)
    return Mat(f)


def _wall_scene(spec, opening=None):
    """A back wall segment from x=-16 to 16 (no side padding, so rows of them tile), optionally
    built round an opening (x0, x1, z0, z1)."""
    S = Scene(pad=0, pad_top=2, pad_bottom=2)
    wm = wall_mat(spec.get("paper", "sage"))
    h = SEG / 2
    if opening is None:
        S.add(box(-h, h, 0, WALL_T, 0, WALL_H, wm))
    else:
        x0, x1, z0, z1 = opening
        S.add(box(-h, x0, 0, WALL_T, 0, WALL_H, wm))
        S.add(box(x1, h, 0, WALL_T, 0, WALL_H, wm))
        S.add(box(x0, x1, 0, WALL_T, 0, z0, wm))
        S.add(box(x0, x1, 0, WALL_T, z1, WALL_H, wm))
    return S


def _wall_done(S, cv):
    return done(S, cv, "wall", fp(-SEG / 2 + 1, SEG / 2 - 1, WALL_T))


def wall_back(spec):
    """A plain back-wall segment."""
    S = _wall_scene(spec)
    cv = S.render()
    return _wall_done(S, cv)


def wall_window(spec):
    """A back-wall segment with a window: a deep reveal with a wooden sill, white glazing bars,
    daylight and a far hillside through the glass, curtains tied back on a rod, a pot of
    geraniums on the sill. The glass stays as it is at night (no lamp glow)."""
    rnd = random.Random(spec.get("seed", 1))
    ox0, ox1, oz0, oz1 = -6, 6, 18, 33
    S = _wall_scene(spec, (ox0, ox1, oz0, oz1))
    glass = S.add(box(ox0, ox1, 4, 5, oz0, oz1, M.flat(["#253447", "#253447", "#36597a", "#5b8fb0", "#93c6dd", "#d9f1f8"])))
    S.add(box(ox0 - 2, ox1 + 2, -2.5, 0.5, oz0 - 1.5, oz0, M.wood(DARKWOOD, bias=0.12)))  # sill board
    cv = S.render()
    gi = S.solids.index(glass)
    gx0, gy0 = S.sx(ox0), S.sy(4, oz1)
    gw, gh = ox1 - ox0, oz1 - oz0
    hill = [round(9 + 1.6 * math.sin(i * 0.55 + 1.0)) for i in range(gw)]
    near = [round(11.5 + 1.2 * math.sin(i * 0.8 + 2.5)) for i in range(gw)]
    for y in range(gy0, gy0 + gh):
        for x in range(gx0, gx0 + gw):
            if not cv.inb(x, y) or S.sid[y, x] != gi:
                continue
            lx, ly = x - gx0, y - gy0
            c = "#8fc3dc" if ly < 3 else "#a9d3e6" if ly < 6 else "#c6e4ef"
            if ly in (3, 4) and 2 <= lx <= 4 + (ly == 4):  # a small cloud
                c = "#f4fbfd"
            if ly >= hill[lx]:
                c = "#9fc4a4" if ly == hill[lx] else "#86b38e"
            if ly >= near[lx]:
                c = "#6fa35e" if ly == near[lx] else "#5a8d4c"
            if lx >= 8 and 6 <= ly <= 10 and (lx - 9.5) ** 2 + (ly - 8) ** 2 < 5:  # a tree on the hill
                c = "#3f7a37" if lx + ly < 18 else "#2f5f33"
            if lx in (5, 6) or ly == 7 or lx in (0, gw - 1) or ly == gh - 1:  # glazing bars and frame
                c = "#efe9dc" if lx != 6 and ly != gh - 1 else "#c9c0ad"
            elif ly < 7 and (lx + ly) % 8 == 3:
                c = "#eef9fc"  # glint
            cv.px[x, y] = C(c)
    # curtains on a rod, tied back either side
    curtain = CLOTH[spec.get("curtain", "red")]
    cv.free()
    rod = S.sy(0, 36)
    for x in range(S.sx(-13), S.sx(13)):
        cv.set(x, rod, DARKWOOD[4])
        cv.set(x, rod + 1, DARKWOOD[1])
    for x in (S.sx(-13) - 1, S.sx(13)):
        cv.set(x, rod, BRASS)
        cv.set(x, rod + 1, BRASSR[2])
        cv.set(x, rod - 1, BRASSR[4])
    top, tie, bot = rod + 1, S.sy(0, 25), S.sy(0, 16)
    for side in (-1, 1):
        xo = S.sx(-12) if side < 0 else S.sx(12) - 1  # outer edge
        for y in range(top, bot):
            if y < tie:
                w = round(6 - 3 * (y - top) / max(1, tie - top))
            else:
                w = round(3 + 2.4 * (y - tie) / max(1, bot - tie))
            for i in range(w):
                x = xo - side * i
                k = (i + (0 if y < tie else 1)) % 3
                c = curtain[3] if k == 0 else curtain[2] if k == 1 else curtain[1]
                if i == w - 1:
                    c = curtain[4] if side > 0 else curtain[1]
                if y == bot - 1:
                    c = curtain[1]
                cv.set(x, y, c)
            if y in (tie, tie + 1):
                for i in range(-1, w + 1):
                    cv.set(xo - side * i, y, GOLD[3] if y == tie else GOLD[2])
    # geraniums in a pot on the sill
    cv.at_depth(1.0)
    px, pb = S.sx(-3), S.sy(1, oz0)
    for j, (a, b) in enumerate(((0, 4), (0, 4), (1, 3))):
        for i in range(a, b):
            cv.set(px + i, pb - 3 + j, CLAY[5] if i == a and j == 0 else CLAY[4] if i < 2 else CLAY[3])
    for i in range(0, 4):
        cv.set(px + i, pb - 4, CLAY[5] if i < 3 else CLAY[4])
    for (dx, dy, c) in ((0, -5, LEAVES[4]), (1, -5, LEAVES[3]), (2, -5, LEAVES[4]), (3, -5, LEAVES[3]), (-1, -6, LEAVES[4]),
                        (1, -6, LEAVES[5]), (2, -6, LEAVES[3]), (4, -6, LEAVES[4]), (0, -7, "#d8333a"), (1, -7, "#f0605a"),
                        (2, -8, "#d8333a"), (3, -7, "#f0605a"), (1, -8, "#ff8a7a"), (3, -8, "#d8333a")):
        cv.set(px + dx, pb + dy, c)
    _ = rnd
    return _wall_done(S, cv)


def wall_picture(spec):
    """A back-wall segment with a gilt-framed landscape hung from a nail on a cord."""
    S = _wall_scene(spec)
    cv = S.render()
    cv.on_wall(0)
    fw, fh = 16, 12
    x0, y0 = S.sx(-fw / 2), S.sy(0, 33)
    nx, ny = S.sx(0), S.sy(0, 37)
    for xa in (x0 + 3, x0 + fw - 4):  # the cord, from the frame's top corners up to the nail
        n = max(1, abs(nx - xa))
        for i in range(n + 1):
            cv.set(round(xa + (nx - xa) * i / n), round(y0 - 1 + (ny + 1 - (y0 - 1)) * i / n), "#5c4632")
    cv.set(nx, ny, IRON[2])
    cv.set(nx, ny + 1, IRON[1])
    for y in range(y0 + 1, y0 + fh + 1):  # its shadow on the wall
        cv.darken(x0 + fw, y, 0.35)
    for x in range(x0 + 1, x0 + fw + 1):
        cv.darken(x, y0 + fh, 0.35)
    for y in range(y0, y0 + fh):
        for x in range(x0, x0 + fw):
            lx, ly = x - x0, y - y0
            if lx in (0, fw - 1) or ly in (0, fh - 1):
                c = GOLD[4] if (lx == 0 or ly == 0) and not (lx == fw - 1 or ly == fh - 1) else GOLD[1]
            elif lx in (1, fw - 2) or ly in (1, fh - 2):
                c = GOLD[2] if (lx == 1 or ly == 1) else GOLD[3]
            else:
                c = _painting(lx - 2, ly - 2)
            cv.set(x, y, c)
    return _wall_done(S, cv)


def _painting(x, y):
    """A tiny landscape in oils, 12 x 8: sky, a sun, blue hills, a cottage, a tree, a meadow."""
    if y <= 4 and (x - 9) ** 2 + (y - 1) ** 2 <= 1:
        return "#fbe7a0"
    if 4 <= x <= 5 and y in (4, 5):  # the cottage
        return "#a8383a" if y == 4 else "#efe3c8"
    if x == 2 and y in (3, 4, 5):  # the tree
        return "#2f5f33" if y < 5 else "#5a3a22"
    if x in (1, 3) and y == 4:
        return "#3f7a37"
    hz = 4 + (1 if x > 7 else 0) - (1 if 2 <= x <= 4 else 0)
    if y < hz - 1:
        return "#9cc6dd" if y < 2 else "#c7e0e8"
    if y < hz:
        return "#7f95b8"
    if y >= 6 and x % 3 == 1:
        return "#d9b45a"
    return "#6f9f50" if y < 6 else "#5a8a40"


def _jar(cv, x, bottom, kind, lid="cloth"):
    """A preserving jar, 4 px wide, 6 tall, on `bottom`: glass with its contents showing, a label,
    a cloth cover tied with string (or a tin lid)."""
    d, m, l = JARS[kind]
    for j in range(4):
        y = bottom - 1 - j
        for i in range(4):
            c = l if i == 0 else m if i < 3 else d
            if j == 0:
                c = d if i else m
            if j in (1, 2) and i in (1, 2):
                c = "#efe6cf" if j == 2 else "#d8ccb0"  # the label
            cv.set(x + i, y, c)
    cv.set(x, bottom - 4, "#e9f4f6")  # glint on the shoulder
    if lid in ("cloth", "blue"):
        cl = ("#7a2629", "#a8383a", "#cf5652") if lid == "cloth" else ("#2b4372", "#3d5f9c", "#5a82c0")
        for i in range(-1, 5):
            cv.set(x + i, bottom - 5, cl[1] if 0 <= i < 3 else cl[0])
        for i in range(0, 4):
            cv.set(x + i, bottom - 6, cl[2] if i < 3 else cl[1])
        cv.set(x - 1, bottom - 4, cl[0])
        cv.set(x + 4, bottom - 4, cl[0])
    else:
        for i in range(0, 4):
            cv.set(x + i, bottom - 5, IRON[2] if i < 3 else IRON[1])
        cv.set(x + 1, bottom - 6, IRON[2])


def wall_shelf(spec):
    """A back-wall segment with two shelves on brackets: preserving jars, a stoneware crock,
    a stack of bowls, bunches of herbs drying under the lower shelf."""
    rnd = random.Random(spec.get("seed", 1))
    S = _wall_scene(spec)
    shelves = (20, 29)
    for z in shelves:
        S.add(box(-14, 14, -5, 0, z, z + 1.5, M.wood(WOOD, bias=0.12)))
    cv = S.render()
    cv.on_wall(0)
    for z in shelves:  # iron brackets under the boards
        for bx in (S.sx(-11), S.sx(10)):
            y0 = S.sy(0, z) + 1
            for k in range(5):  # an L bracket with a diagonal brace
                cv.set(bx, y0 + k, IRON[2] if k < 4 else IRON[1])
            for k in range(4):
                cv.set(bx + 3 - k, y0 + k, IRON[1])
            for k in range(1, 4):
                cv.set(bx + k, y0, IRON[2])
    # herbs drying under the lower shelf
    cv.free()
    for hx, col in ((-6, LEAVES), (5, ["#3a3418", "#5e5424", "#7f7334", "#9c9048", "#b5aa62", "#cfc488", "#e2dcae"])):
        x, y = S.sx(hx), S.sy(-2, shelves[0])
        cv.set(x, y, "#8a6a42")
        cv.set(x, y + 1, "#8a6a42")
        for j, (a, b) in enumerate(((0, 1), (-1, 2), (-1, 2), (-2, 2), (-1, 2), (-1, 1), (0, 1))):
            for i in range(a, b + 1):
                c = col[5] if i < 0 else col[4] if i == 0 else col[3]
                if (i + j) % 3 == 0:
                    c = col[2]
                cv.set(x + i, y + 2 + j, c)
        cv.set(x, y + 2, "#c9a061")
    # jars and crocks on the boards
    lower = [("jam", "cloth"), ("honey", "tin"), ("pickle", "blue"), ("peach", "cloth")]
    rnd.shuffle(lower)
    cv.at_depth(-2.5)
    b = S.sy(-2.5, shelves[0] + 1.5) + 1
    x = S.sx(-12)
    for kind, lid in lower[:2]:
        _jar(cv, x, b, kind, lid)
        x += 6
    jug(cv, x, b, ("#6b5a48", "#a8927a", "#d8c8b0"))  # stoneware crock
    x += 7
    for kind, lid in lower[2:]:
        _jar(cv, x, b, kind, lid)
        x += 6
    b = S.sy(-2.5, shelves[1] + 1.5) + 1
    x = S.sx(-12)
    for j in range(3):  # a stack of bowls
        w = 7 - j
        for i in range(w):
            cv.set(x + j // 2 + i, b - 1 - j * 2, "#efe7d6" if i < w - 2 else "#c8bca6")
            cv.set(x + j // 2 + i, b - 2 - j * 2, "#3d5f9c" if i in (0, w - 1) else "#fbf6ec")
    x += 10
    for kind in ("plum", "flour", "jam"):
        _jar(cv, x, b, kind, {"plum": "blue", "flour": "tin"}.get(kind, "cloth"))
        x += 6
    return _wall_done(S, cv)


def _side_mat(paper, x0, x1, room_right):
    def f(u, v, kind, light, P, s):
        if kind == "top":
            across = (x1 - P[0]) if room_right else (P[0] - x0)
            return _cap(math.floor(P[1]) % SIDE_D, across, x1 - x0, light)
        return _face(6 + math.floor(u - x0), math.floor(v), light, paper, stiles=False)
    return Mat(f)


def wall_side(spec):
    """A side-wall segment running 32 px back on the map: its top edge and a sliver of its inner
    face (spec side: "left" wall, room on its right; "right" wall, room on its left). Stacked,
    the segments join into one continuous wall; the front one shows the wall's end."""
    left = spec.get("side", "left") == "left"
    paper = spec.get("paper", "sage")
    ramp = PAPERS[paper][0]
    x0, x1 = (-4, 2) if left else (-2, 4)
    S = Scene(pad=2, pad_top=1, pad_bottom=2)
    S.add(box(x0, x1, 0, SIDE_D, 0, WALL_H, _side_mat(paper, x0, x1, left)))
    cv = S.render()
    top = S.sy(SIDE_D, WALL_H)
    bot = S.sy(0, 0)
    # the inner face, seen nearly edge on: wallpaper next to the top edge, then the wainscot
    cols = (S.sx(x1), S.sx(x1) + 1) if left else (S.sx(x0) - 1, S.sx(x0) - 2)
    shade = ((ramp[3], WOOD[2]) if left else (ramp[5], WOOD[5]))
    for y in range(top, bot):
        for c, col in zip(cols, shade):
            cv.set(c, y, col)
    for c in cols:  # the skirting where the face meets the floor at the front end
        cv.set(c, bot - 1, DARKWOOD[3])
        cv.set(c, bot - 2, DARKWOOD[4])
    S.finish(cv)
    for x in range(cv.w):  # no outline across the far end, so stacked segments join seamlessly
        cv.clear(x, top - 1)
    xa, xb = min(x0, -4), max(x1, 4)
    return _result(cv, "wall", (S.ox, S.base), [xa, -round(K * SIDE_D) + 1, xb - xa, round(K * SIDE_D) - 2])


def _post_mat():
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        if kind == "top":
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d = max(abs(P[0] - cx), abs(P[1] - cy) * 1.0)
            if d > (x1 - x0) / 2 - 1:
                return DARKWOOD[3]
            ring = math.floor(math.hypot(P[0] - cx, (P[1] - cy)) * 0.9)
            return DARKWOOD[5] if ring % 2 else DARKWOOD[4]
        lu = u - x0
        if lu < 1:
            return _st(DARKWOOD, light, 2)
        if lu > x1 - x0 - 1:
            return _st(DARKWOOD, light, -1)
        if hsh(math.floor(lu), math.floor(v / 4), 3) < 0.15:
            return _st(DARKWOOD, light, -1)
        return _t(DARKWOOD, light + 0.1)
    return Mat(f)


def wall_corner(spec):
    """A square corner post a little taller than the walls, with a plinth and a capping block
    showing its end grain: it covers the joins where back and side walls meet."""
    S = Scene(pad=2, pad_top=2)
    pm = _post_mat()
    S.add(box(-5, 5, 0, 10, 0, 3, M.wood(DARKWOOD, bias=-0.05)))
    S.add(box(-4, 4, 1, 9, 3, WALL_H, pm))
    S.add(box(-5, 5, 0, 10, WALL_H, WALL_H + 3, pm))
    cv = S.render()
    return done(S, cv, "wall", fp(-5, 5, 10))


# ================================================================ beds

def _quilt_mat(style, seed=1):
    """Patchwork squares with stitched seams and a border (style "patch"), or a plain coverlet
    stitched in diamonds with a contrasting border (any colour name in CLOTH)."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1, z0, z1 = s.bbox
        if kind == "top":
            a, b = P[0] - x0, P[1] - y0
            if y1 - P[1] < 4:  # the turned-down top edge with the sheet showing
                if y1 - P[1] < 2.2:
                    return LINEN[5] if y1 - P[1] > 1 else LINEN[3]
                b = 0
        else:
            a, b = P[0] - x0, (z1 - P[2]) * 1.25
        lit = kind == "top"
        border = min(a, x1 - x0 - a) < 2.2
        if style == "patch":
            if border:
                r = PATCH[0]
                return r[2] if lit else r[1]
            i, j = math.floor((a - 2.2) / 4), math.floor(b / 5)
            r = PATCH[math.floor(hsh(i, j, seed) * len(PATCH))]
            if (a - 2.2) % 4 < 0.8 or b % 5 < 1.0:
                return r[0] if not lit else r[1]  # seams
            return r[2] if lit else r[1]
        r = CLOTH[style]
        if border:
            return WHITE[3] if lit else WHITE[2]
        dd = ((a + b) % 6 < 0.9) or ((a - b) % 6 < 0.9)
        if dd:
            return r[2] if lit else r[1]
        return r[3] if lit else r[2]
    return Mat(f)


def bed(spec):
    """A bed with its head to the back wall: a turned wooden frame with a panelled headboard and
    knobbed posts, a quilt over the mattress hanging down over the foot (or a footboard on the
    double bed), the sheet turned down, pillows."""
    double = spec.get("double", False)
    hw = 17 if double else 10
    L = 34
    frame = DARKWOOD if spec.get("dark") else WOOD
    fw = M.wood(frame, bias=0.12)
    S = Scene(pad_top=3)
    for x in (-hw, hw - 2):  # legs
        S.add(box(x, x + 2, 0, 2, 0, 3, fw))
    S.add(box(-hw, hw, 0, L - 3, 2.5, 6, M.planks(frame, h=4, seed=3)))  # rails
    S.add(box(-hw + 0.5, hw - 0.5, 1, L - 3, 6, 9, M.flat(LINEN)))  # mattress
    if double:
        S.add(box(-hw, hw, 0, 2, 0, 10.5, M.wood(frame, bias=0.08)))  # footboard
        for x in (-hw - 1, hw - 2):
            S.add(box(x, x + 3, -0.5, 2.5, 0, 12.5, fw))
            S.add(prism(x + 1.5, 1, 1.6, 12.5, 14.5, fw, sides=8))
        S.add(box(-hw + 0.5, hw - 0.5, 2, L - 9, 6, 10.5, _quilt_mat(spec.get("quilt", "blue"), spec.get("seed", 1))))
    else:
        S.add(box(-hw - 0.5, hw + 0.5, -0.5, L - 9, 4.5, 10.5, _quilt_mat(spec.get("quilt", "patch"), spec.get("seed", 1))))
    S.add(box(-hw + 1, hw - 1, L - 9, L - 3, 8.5, 9.6, M.flat(LINEN)))  # sheet over the pillow end
    pil = M.flat(["#8a8478", "#b8b0a2", "#ddd6c8", "#eeeae0", "#f8f6f0", "#ffffff"])
    if double:
        for x0 in (-hw + 2, 1.5):
            S.add(prism_x(x0, x0 + hw - 3.5, L - 6.5, 9.6, 2.6, pil, sides=12))
    else:
        S.add(prism_x(-hw + 2, hw - 2, L - 6.5, 9.6, 2.6, pil, sides=12))
    S.add(box(-hw, hw, L - 3, L, 0, 19, M.planks(frame, h=5, seed=5)))  # headboard
    for x in (-hw - 1, hw - 2):
        S.add(box(x, x + 3, L - 3.5, L + 0.5, 0, 22, fw))
        S.add(prism(x + 1.5, L - 1.5, 1.7, 22, 24.5, fw, sides=8))
    cv = S.render()
    cv.on_wall(L - 3)
    hx0, hx1, hz = S.sx(-hw + 2), S.sx(hw - 2), S.sy(L - 3, 17)
    for x in range(hx0, hx1):  # a top rail and a fielded panel on the headboard
        cv.set(x, hz, frame[5])
        cv.set(x, hz + 1, frame[2])
    if double:
        cv.on_wall(0)
        _panel(cv, S.sx(-hw + 2), S.sx(-1), S.sy(0, 9), S.sy(0, 2), frame)
        _panel(cv, S.sx(1), S.sx(hw - 2), S.sy(0, 9), S.sy(0, 2), frame)
        cv.free()
        for y in range(S.sy(L - 4, 12.2), S.sy(L - 9, 9.6)):  # the two pillows meet in the middle
            if cv.get(S.sx(0), y)[3]:
                cv.set(S.sx(0), y, LINEN[2])
    return done(S, cv, "prop", fp(-hw - 1, hw + 1, L + 0.5))


# ================================================================ kitchen

def _iron_mat(ramp=IRONK, bias=0.12):
    def f(u, v, kind, light, P, s):
        g = -0.12 if hsh(math.floor(u), math.floor(v), 17) < 0.08 else 0.0
        return _t(ramp, light + bias + g)
    return Mat(f)


def _enamel(ramp, rim):
    """Enamelled tin: a smooth body with a coloured rim band at the top."""
    def f(u, v, kind, light, P, s):
        if kind != "top" and P[2] > s.bbox[5] - 0.9:
            return rim[1] if light < 0.45 else rim[2]
        return _t(ramp, light + 0.15)
    return Mat(f)


ENAMEL = ["#6e6a62", "#a49e92", "#cfc9bc", "#e4dfd3", "#f2eee5", "#fbf9f4", "#ffffff"]


def stove(spec):
    """A black iron kitchen range on short legs: an oven door with a brass bar, the firebox door
    with its grate glowing, an ash drawer, a brass rail under the hob with a check cloth on it; an
    enamel pot and a copper kettle on the hob, a warming shelf with a tin and a jar, the stovepipe
    rising into the wall."""
    S = Scene(pad_top=2)
    iron = _iron_mat()
    for x in (-12, 10):
        S.add(box(x, x + 2, 2, 4, 0, 3, iron))
    S.add(box(-12, 12, 2, 14, 3, 16.5, iron))
    S.add(box(-13, 13, 1.5, 14.5, 16.5, 18, _iron_mat(IRONK, 0.22)))  # hob plate
    S.add(box(-13, 13, 12.5, 15, 18, 26, iron))  # upstand
    S.add(box(-13.5, 13.5, 10.5, 15.5, 26, 27.2, _iron_mat(IRONK, 0.2)))  # warming shelf
    S.add(prism(8, 13.5, 1.8, 27.2, 42, _iron_mat(IRONK, 0.18), sides=10))  # stovepipe
    S.add(prism(8, 13.5, 2.4, 39, 40.5, M.flat(BRASSR), sides=10))  # its collar where it meets the wall
    S.add(box(-12, 12, 0, 0.8, 14.6, 15.6, M.flat(BRASSR)))  # rail under the hob
    S.add(prism(-5.5, 7.5, 3.3, 18, 22.5, _enamel(ENAMEL, CLOTH["blue"]), sides=14))  # pot
    S.add(prism(-5.5, 7.5, 3.5, 22.5, 23.1, M.flat(ENAMEL, 0.1), sides=14))
    S.add(prism(-5.5, 7.5, 0.8, 23.1, 24.2, M.flat(IRONK, 0.3), sides=6))
    cop = M.flat(COPPERR, 0.05)
    S.add(prism(5.5, 7.5, 3, 18, 21, cop, sides=12))  # kettle
    S.add(frustum(5.5, 7.5, 3, 1.3, 21, 23.6, cop, sides=12))
    S.add(prism(5.5, 7.5, 0.7, 23.6, 24.6, M.flat(BRASSR, 0.2), sides=6))
    cv = S.render()
    cv.on_wall(2)
    # oven door
    ox0, ox1, oy0, oy1 = S.sx(-11), S.sx(-1), S.sy(2, 14.5), S.sy(2, 4.5)
    _iron_door(cv, ox0, ox1, oy0, oy1)
    for x in range(ox0 + 2, ox1 - 2):
        cv.set(x, oy0 + 2, BRASS)
        cv.set(x, oy0 + 3, BRASSR[1])
    for y in range(oy0 + 5, oy1 - 2):  # a cast pattern on the door
        for x in range(ox0 + 3, ox1 - 3):
            if (x + y) % 4 == 0 and (x - y) % 4 == 0:
                cv.set(x, y, IRONK[5])
    # firebox door with its grate, ash drawer below
    fx0, fx1, fy0, fy1 = S.sx(1), S.sx(11), S.sy(2, 14.5), S.sy(2, 8.5)
    _iron_door(cv, fx0, fx1, fy0, fy1)
    ember = ["#5a1a08", "#b8400e", "#f07a1e", "#ffc24a"]
    for x in range(fx0 + 2, fx1 - 2):
        for y in range(fy0 + 2, fy1 - 2):
            if (x - fx0) % 2 == 0:
                c = ember[3] if (x * 3 + y) % 4 == 0 else ember[2]
                if y == fy1 - 3:
                    c = ember[1]
                cv.set(x, y, c)
                cv.lit(x, y, LIT[3] if c == ember[3] else LIT[2] if c == ember[2] else LIT[1])
            else:
                cv.set(x, y, IRONK[1])
    dx0, dx1, dy0, dy1 = S.sx(1), S.sx(11), S.sy(2, 7.5), S.sy(2, 4)
    _iron_door(cv, dx0, dx1, dy0, dy1)
    cv.set((dx0 + dx1) // 2, (dy0 + dy1) // 2, BRASS)
    cv.set((dx0 + dx1) // 2, (dy0 + dy1) // 2 + 1, BRASSR[1])
    # check tea towel over the rail
    cv.at_depth(-0.3)
    tx0, ty = S.sx(-9), S.sy(0, 15.6)
    for y in range(ty, ty + 8):
        for x in range(tx0, tx0 + 5):
            check = ((x - tx0) // 2 + (y - ty) // 2) % 2
            c = "#c0392b" if check else "#f4ece0"
            if x == tx0 + 4:
                c = "#a83228" if check else "#d8cfc0"
            if y == ty + 7 and (x - tx0) % 2:
                continue
            cv.set(x, y, c)
    for x in range(tx0, tx0 + 5):
        cv.set(x, ty, "#e8ddcc" if x < tx0 + 4 else "#c9bca6")
    # the kettle's spout and handle, the pot's handles
    cv.free()
    kx, ky = S.s(8.5, 6, 20)
    for i in range(4):
        cv.set(kx + i, ky - i // 2, COPPERR[4] if i < 3 else COPPERR[5])
        cv.set(kx + i, ky - i // 2 + 1, COPPERR[2])
    hx, hy = S.s(5.5, 7.5, 24.6)
    for dx, dy in ((-3, 1), (-3, 0), (-2, -1), (-1, -2), (0, -2), (1, -2), (2, -1), (3, 0), (3, 1)):
        cv.set(hx + dx, hy + dy, IRONK[3] if dx < 1 else IRONK[2])
    px, py = S.s(-5.5, 6, 21.5)
    for dx in (-5, 4):
        cv.set(px + dx, py, IRONK[3])
        cv.set(px + dx + (1 if dx > 0 else 0), py - 1, IRONK[4])
    # a tin and a little jar on the warming shelf
    cv.at_depth(12.5)
    b = S.sy(12.5, 27.2) + 1
    tx = S.sx(-10)
    for y in range(b - 5, b):
        for x in range(tx, tx + 4):
            cv.set(x, y, ("#3d5f9c" if x < tx + 3 else "#2b4372") if y > b - 4 else "#c9a24a")
    cv.set(tx, b - 3, "#5a82c0")
    _jar(cv, S.sx(-4), b, "honey", "tin")
    return done(S, cv, "prop", fp(-13, 13, 14.5))


def _iron_door(cv, x0, x1, y0, y1):
    for y in range(y0, y1):
        for x in range(x0, x1):
            edge_tl = x == x0 or y == y0
            edge_br = x == x1 - 1 or y == y1 - 1
            c = IRONK[5] if edge_tl and not edge_br else IRONK[1] if edge_br else IRONK[3]
            if x == x0 + 1 and y0 < y < y1 - 1 or y == y0 + 1 and x0 < x < x1 - 1:
                c = IRONK[2]
            cv.set(x, y, c)


# ---------------------------------------------------------------- the fire

FIRE_FRAMES = 6
FIRE_W, FIRE_H = 18, 16


def _fire_frame(f, w=FIRE_W, h=FIRE_H, base=13):
    """One frame of flames in lamplight colours (blue 3) so they glow at night: tongues that rise
    and sway with a 6-frame period, white-hot at the root, orange at the tips, a spark or two."""
    cv = Canvas(w, h)
    ph = f * 2 * math.pi / FIRE_FRAMES
    cx = w / 2
    for x in range(w):
        dxn = (x + 0.5 - cx) / (w * 0.42)
        if abs(dxn) >= 1:
            continue
        env = 1 - dxn * dxn
        tongue = 0.5 + 0.5 * math.sin(x * 1.25 + ph + 0.6 * math.sin(ph * 2 + x))
        hgt = base * env * (0.45 + 0.6 * tongue)
        lean = 0
        for y in range(h):
            k = (h - 1 - y)  # rows up from the bottom
            if k > hgt:
                continue
            q = k / max(1.0, hgt)
            core = env > 0.55 and q < 0.45
            if q > 0.82:
                c = LIT[1]
            elif q > 0.55:
                c = LIT[2]
            elif core:
                c = LIT[4] if q < 0.25 and env > 0.75 else LIT[3]
            else:
                c = LIT[3] if q < 0.3 else LIT[2]
            if k < 1:
                c = LIT[1] if abs(dxn) > 0.6 else LIT[2]
            cv.set(x + lean, y, c)
    for i in range(2):  # sparks
        sx = round(cx + 5 * math.sin(ph * (1 + i) + i * 2.0))
        sy = round((h - base - 2) - 2 * ((f + 3 * i) % FIRE_FRAMES) / FIRE_FRAMES * 2) + 1
        if 0 <= sx < w and 0 <= sy < h and not cv.get(sx, sy)[3]:
            cv.set(sx, sy, LIT[3])
    for y in range(h):  # a darker orange rim round the flames
        for x in range(w):
            if cv.get(x, y)[3]:
                continue
            if any(cv.get(x + dx, y + dy)[3] and cv.get(x + dx, y + dy)[:3] != C(LIT[3])[:3] or
                   (cv.get(x + dx, y + dy)[3] and dy == 1)
                   for dx, dy in ((1, 0), (-1, 0), (0, 1))) and y > 2:
                if hsh(x, y, f) < 0.5:
                    cv.set(x, y, LIT[0])
    return cv.im


def fire_sheet():
    sheet = Image.new("RGBA", (FIRE_W * FIRE_FRAMES, FIRE_H), (0, 0, 0, 0))
    for f in range(FIRE_FRAMES):
        sheet.alpha_composite(_fire_frame(f), (f * FIRE_W, 0))
    return sheet


def fireplace(spec):
    """A stone fireplace against the back wall: a hearth slab, jambs and a lintel of dressed
    stone round a sooty firebox with logs on iron firedogs, a timber mantel with candlesticks,
    a clock and a vase, the chimney breast rising to the top of the wall (its flue showing in the
    cut), a log stack and fire irons on the hearth. The fire is an animated part ("fire", 6
    frames) in lamplight colours; the candles and the firelight inside glow at night."""
    S = Scene(pad_top=2)
    stone = M.dressed_stone(STONE if spec.get("stone", "grey") == "grey" else FIELDSTONE, seed=6, bias=0.12)
    S.add(box(-21, 21, 0, 16, 0, 2.5, M.dressed_stone(STONE, h=5, seed=4, bias=0.22)))  # hearth
    S.add(box(-18, -9, 6, 16, 2.5, 25, stone))
    S.add(box(9, 18, 6, 16, 2.5, 25, stone))
    S.add(box(-9, 9, 6, 16, 18.5, 25, M.dressed_stone(STONE, h=7, seed=9, bias=0.08)))  # lintel
    back = S.add(box(-9, 9, 13, 16, 2.5, 18.5, M.flat(SOOT)))
    S.add(box(-22, 22, 4.5, 16.5, 25, 28, M.planks(DARKWOOD, h=3, seed=7)))  # mantel
    S.add(box(-15, 15, 9, 16, 28, WALL_H, stone))  # chimney breast
    S.add(prism_x(-6.5, 6, 10.5, 4.3, 1.8, M.wood(BARK, bias=0.15), sides=10, upper=False))  # logs
    S.add(prism_x(-4.5, 7, 8.8, 4.1, 1.6, M.wood(BARK, bias=0.2), sides=10, upper=False))
    S.add(box(-20.5, -12.5, 0.5, 5.5, 2.5, 9, M.logs()))  # log stack on the hearth
    cv = S.render()
    # soot and flue in the cut top of the breast
    tx0, tx1 = S.sx(-12), S.sx(12)
    for y in range(S.sy(15, WALL_H) + 1, S.sy(10, WALL_H)):
        for x in range(tx0, tx1):
            cv.set(x, y, "#1b1716" if y > S.sy(15, WALL_H) + 1 else "#2a2220")
    # the firebox floor: ash and embers; firelight on the back at night
    bi = S.solids.index(back)
    for y in range(cv.h):
        for x in range(cv.w):
            if S.sid[y, x] == bi and y > S.sy(13, 11):  # firelight on the sooty back, low down
                cv.lit(x, y, LIT[0])
    cv.free()
    fy0, fy1 = S.sy(13, 2.5), S.sy(6, 2.5)
    for y in range(fy0, fy1):
        for x in range(S.sx(-9), S.sx(9)):
            if cv.get(x, y)[3] and S.sid[y, x] == 0:
                ember = hsh(x, y, 3) < 0.25
                cv.set(x, y, "#c2561a" if ember else "#3a302c" if (x + y) % 3 else "#4a3e38")
                cv.lit(x, y, LIT[1] if ember else LIT[0])
    # firedogs in front of the logs
    cv.at_depth(7)
    for x in (S.sx(-6), S.sx(5)):
        b = S.sy(7, 2.5)
        for y in range(b - 7, b):
            cv.set(x, y, IRONK[4])
            cv.set(x + 1, y, IRONK[2])
        cv.set(x, b - 8, IRONK[5])
        cv.set(x + 1, b - 8, IRONK[4])
        cv.set(x - 1, b - 1, IRONK[3])
        cv.set(x + 2, b - 1, IRONK[2])
    # things on the mantel
    cv.at_depth(9)
    mb = S.sy(9, 28) + 1
    for cxx, h in ((-19, 4), (18, 4)):  # brass candlesticks with candles
        x = S.sx(cxx)
        cv.set(x - 1, mb - 1, BRASSR[3])
        cv.set(x, mb - 1, BRASSR[4])
        cv.set(x + 1, mb - 1, BRASSR[2])
        cv.set(x, mb - 2, BRASSR[4])
        cv.set(x, mb - 3, BRASSR[3])
        candle(cv, x, mb - 3, h)
    x = S.sx(-6)  # a mantel clock
    for y in range(mb - 8, mb):
        for i in range(6):
            c = DARKWOOD[4] if i < 5 else DARKWOOD[2]
            if y == mb - 8 and i in (0, 5):
                continue
            cv.set(x + i, y, c)
    for (i, j) in ((1, 2), (2, 2), (3, 2), (1, 3), (3, 3), (1, 4), (2, 4), (3, 4), (2, 3)):
        cv.set(x + i, mb - 8 + j, "#f4ecd9")
    cv.set(x + 2, mb - 8 + 3, "#2a1a12")
    cv.set(x + 2, mb - 8 + 2, "#2a1a12")
    cv.set(x + 2, mb - 1, BRASS)
    jx = S.sx(6)  # a little vase of flowers
    jug(cv, jx, mb, ("#1e4a4a", "#2f7472", "#5aa6a0"))
    for dx, dy, c in ((0, -7, "#ffe066"), (2, -8, "#ffffff"), (3, -7, "#ff9ec4"), (1, -7, LEAF[1]), (2, -7, LEAF[0])):
        cv.set(jx + dx, mb + dy, c)
    # fire irons leaning on the right jamb
    cv.at_depth(4)
    b = S.sy(4, 2.5)
    x = S.sx(14)
    for k in range(15):
        cv.set(x + k // 7, b - 1 - k, IRONK[4] if k % 7 else IRONK[5])
    cv.set(x + 2, b - 16, BRASS)
    cv.set(x + 3, b - 16, BRASSR[3])
    for k in range(4):
        cv.set(x - 2 + k, b - 1, "#5c4632" if k % 2 else "#8a6a42")
        cv.set(x - 2 + k, b - 2, "#8a6a42")
    im, night, info = done(S, cv, "prop", fp(-21, 21, 16), extra=None)
    fx, fyy = S.s(0.5, 9.5, 2.5)
    info["fire"] = [fx - S.ox, fyy - FIRE_H // 2 - S.base + 1]
    info["fire_frames"] = FIRE_FRAMES
    info["fire_fps"] = 8
    return im, night, info, {"fire": fire_sheet()}


def dresser(spec):
    """A kitchen dresser: a cupboard of two drawers and two doors under a worktop, an open rack
    above with blue-and-white plates standing along its shelves, cups on hooks, a jug and a
    bread crock on the worktop, a cornice on top."""
    rnd = random.Random(spec.get("seed", 1))
    wd = DARKWOOD if spec.get("dark") else WOOD
    w = M.wood(wd, bias=0.1)
    S = Scene(pad_top=2)
    S.add(box(-15, 15, 0.5, 11, 0, 2.5, M.wood(wd, bias=-0.05)))  # plinth
    S.add(box(-15, 15, 1, 11, 2.5, 15, w))
    S.add(box(-16, 16, 0, 11.5, 15, 16.5, M.planks(HONEY, h=3, seed=2)))  # worktop
    S.add(box(-14, 14, 9, 11, 16.5, 36, M.boards(wd, w=6, seed=3, bias=-0.3)))  # back boards
    for x in (-15, 13):
        S.add(box(x, x + 2, 5, 11, 16.5, 36, w))
    for z in (24, 31):
        S.add(box(-13, 13, 6, 9, z, z + 1.2, w))
    S.add(box(-16, 16, 5, 11.5, 36, 38.5, M.planks(wd, h=3, seed=9, bias=0.15)))  # cornice
    cv = S.render()
    # drawers and doors on the cupboard
    cv.on_wall(1)
    for x0, x1 in ((-14, -0.5), (0.5, 14)):
        _panel(cv, S.sx(x0), S.sx(x1), S.sy(1, 14), S.sy(1, 11), wd)
        cv.set((S.sx(x0) + S.sx(x1)) // 2, S.sy(1, 12.5), BRASS)
        _panel(cv, S.sx(x0), S.sx(x1), S.sy(1, 10), S.sy(1, 3), wd)
        kx = S.sx(x1) - 2 if x0 < 0 else S.sx(x0) + 1
        cv.set(kx, S.sy(1, 7), BRASS)
        cv.set(kx, S.sy(1, 7) + 1, BRASSR[1])
    # plates standing along the shelves, leaning on the back boards
    cv.at_depth(8)
    for z, rows in ((25.2, 0), (32.2, 1)):
        b = S.sy(8, z) + 1
        x = S.sx(-12)
        while x < S.sx(10):
            _plate(cv, x, b, 3 if rows == 0 else 2)
            x += 7 if rows == 0 else 5
    # cups hanging from hooks under the top shelf
    cv.at_depth(6)
    for k, cxx in enumerate((-10, -4, 2, 8)):
        x, y = S.sx(cxx), S.sy(6, 31) + 1
        cv.set(x + 1, y, IRON[2])
        for j in range(3):
            for i in range(3):
                cv.set(x + i, y + 1 + j, "#3d5f9c" if j == 0 else "#fbf6ec" if i < 2 else "#c8bca6")
        cv.set(x + 3, y + 2, "#c8bca6")
    # a jug and a bread crock on the worktop
    cv.at_depth(5)
    b = S.sy(5, 16.5) + 1
    jug(cv, S.sx(-11), b, ("#6b5a48", "#a8927a", "#d8c8b0"))
    x = S.sx(3)
    for j, (a, bb) in enumerate(((1, 6), (0, 7), (0, 7), (0, 7), (0, 7), (1, 6))):
        for i in range(a, bb):
            c = "#efe3c8" if i < 4 else "#c9b896"
            if j == 0:
                c = "#8a6a42" if i < 5 else "#5c4632"
            if j == 2 and 1 <= i <= 5:
                c = "#3d5f9c"
            cv.set(x + i, b - 6 + j, c)
    item(cv, S.sx(-5), b, "bread")
    _ = rnd
    return done(S, cv, "prop", fp(-16, 16, 11.5))


def _plate(cv, x, bottom, r):
    """A blue-and-white plate standing on edge, radius r, its rim at x..x+2r."""
    cx, cy = x + r, bottom - r - 1
    for y in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d = math.hypot(xx - cx, y - cy)
            if d > r + 0.45:
                continue
            if d > r - 0.6:
                c = "#2d4777" if xx + y < cx + cy + r else "#1d2c4c"
            elif d > r - 1.6:
                c = "#fbf7ee" if xx + y < cx + cy else "#d8d0c2"
            else:
                c = "#5a82c0" if (xx + y) % 2 == 0 else "#efe9dc"
            cv.set(xx, y, c)


def _panel(cv, x0, x1, y0, y1, ramp):
    """A framed panel (a drawer front, a door) drawn on a face: a dark gap round it, a lit top
    and left edge, a shaded bottom and right edge, a recessed field."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            if x == x0 or y == y0:
                c = ramp[1]
            elif x == x1 - 1 or y == y1 - 1:
                c = ramp[2]
            elif x == x0 + 1 or y == y0 + 1:
                c = ramp[5]
            elif (x == x0 + 2 or y == y0 + 2) and x1 - x0 > 6 and y1 - y0 > 5:
                c = ramp[2]
            elif (x == x1 - 3 or y == y1 - 3) and x1 - x0 > 6 and y1 - y0 > 5:
                c = ramp[5]
            else:
                continue
            cv.set(x, y, c)


# ================================================================ tables and chairs

def _table_top(cloth=None):
    planks = M.planks(WOOD, h=4, seed=6, bias=0.12)

    def f(u, v, kind, light, P, s):
        if cloth and kind == "top" and cloth[0] <= P[1] <= cloth[1]:
            e = min(P[1] - cloth[0], cloth[1] - P[1])
            if e < 1:
                return "#a8383a"
            return LINEN[5] if (math.floor(P[0]) // 3 + math.floor(P[1])) % 2 else LINEN[4]
        return planks.fn(u, v, kind, light, P, s)
    return Mat(f)


def _chair(S, x, y, facing="front", wood=WOOD, cushion=None):
    """Chair solids: facing 'front' (back rest behind the seat), 'left' or 'right' (seen side on,
    back rest on the far side)."""
    w = M.wood(wood, bias=0.15)
    if facing == "front":
        for lx in (x - 5, x + 3.5):
            for ly in (y, y + 7):
                S.add(box(lx, lx + 1.5, ly, ly + 1.5, 0, 8, w))
        S.add(box(x - 5.5, x + 5.5, y - 0.5, y + 9, 8, 9.5, M.planks(wood, h=3, seed=2, bias=0.15)))
        for lx in (x - 5, x + 3.5):
            S.add(box(lx, lx + 1.5, y + 7, y + 8.5, 9.5, 23, w))
        S.add(box(x - 5.5, x + 5.5, y + 6.5, y + 9, 20, 23.5, w))
        S.add(box(x - 5, x + 5, y + 7, y + 8.5, 13.5, 15, w))
        if cushion:
            S.add(box(x - 4.5, x + 4.5, y + 0.5, y + 6.5, 9.5, 10.6, M.flat(_r7(CLOTH[cushion]), 0.05)))
        return
    sgn = -1 if facing == "right" else 1  # the back rest is on the far side from the table
    bx = x + sgn * 3.5
    for lx in (x - 3.5, x + 2):
        for ly in (y, y + 6.5):
            S.add(box(lx, lx + 1.5, ly, ly + 1.5, 0, 8, w))
    S.add(box(x - 4, x + 4, y - 0.5, y + 8.5, 8, 9.5, M.planks(wood, h=3, seed=2, bias=0.15)))
    S.add(box(bx - 0.75, bx + 0.75, y, y + 1.5, 9.5, 22, w))
    S.add(box(bx - 0.75, bx + 0.75, y + 6.5, y + 8, 9.5, 22, w))
    S.add(box(bx - 1, bx + 1, y - 0.5, y + 8.5, 19, 22.5, w))
    S.add(box(bx - 0.75, bx + 0.75, y, y + 8, 13.5, 15, w))


def _spindles(cv, S, x, y, z0=15, z1=20):
    cv.on_wall(y, tol=1.0)
    for dx in (-2.5, 0, 2.5):
        for zz in range(z0, z1):
            cv.set(S.sx(x + dx), S.sy(y, zz + 0.5), WOOD[4])
            cv.set(S.sx(x + dx) + 1, S.sy(y, zz + 0.5), WOOD[2])


def table_set(spec):
    """A plank table with a linen runner and supper laid: plates, a loaf, a bowl of apples, a jug,
    a candle in a brass stick (lit at night); a chair behind it and one at each end."""
    S = Scene(pad_top=2)
    tw = M.wood(WOOD, bias=0.1)
    for lx in (-15, 13):
        for ly in (1, 13):
            S.add(box(lx, lx + 2, ly, ly + 2, 0, 10, tw))
    S.add(box(-15, 15, 1, 15, 10, 12, M.planks(WOOD, h=2, seed=4)))
    S.add(box(-16, 16, 0, 16, 12, 14, _table_top((5.5, 10.5))))
    _chair(S, 0, 18, "front", cushion=spec.get("cushion"))
    _chair(S, -21, 4, "left")
    _chair(S, 21, 4, "right")
    cv = S.render()
    _spindles(cv, S, 0, 25)
    cv.at_depth(8)
    b = S.sy(8, 14) + 1
    for px in (-12, 7):  # plates
        x = S.sx(px)
        for i in range(6):
            cv.set(x + i, b - 1, "#d8d0c2")
            cv.set(x + i, b - 2, "#fbf7ee" if 0 < i < 5 else "#d8d0c2")
        cv.set(x + 1, b - 2, "#efe9dc")
    item(cv, S.sx(-9), b - 1, "bread")
    x = S.sx(-2)  # a bowl of apples
    for i in range(6):
        cv.set(x + i, b - 1, "#8a5d36" if i in (0, 5) else "#a87545")
        cv.set(x + i, b - 2, "#c38f5a")
    for i in (0, 2, 4):
        item(cv, x + i, b - 2, "apple")
    cv.at_depth(11)
    b2 = S.sy(11, 14) + 1
    jug(cv, S.sx(4), b2, ("#6b3c17", "#b9773a", "#e2b06c"))
    x = S.sx(-6)
    cv.set(x - 1, b2 - 1, BRASSR[3])
    cv.set(x, b2 - 1, BRASSR[4])
    cv.set(x + 1, b2 - 1, BRASSR[2])
    cv.set(x, b2 - 2, BRASSR[4])
    candle(cv, x, b2 - 2, 4)
    return done(S, cv, "prop", fp(-25, 25, 26))


def chair(spec):
    """A wooden chair facing the room, spindles in its back, a cushion on the seat."""
    S = Scene(pad_top=2)
    _chair(S, 0, 0, "front", DARKWOOD if spec.get("dark") else WOOD, cushion=spec.get("cushion", "red"))
    cv = S.render()
    _spindles(cv, S, 0, 7)
    return done(S, cv, "prop", fp(-5.5, 5.5, 9))


# ================================================================ cupboards and shelves

def wardrobe(spec):
    """A tall wardrobe: two panelled doors with brass knobs and a keyhole, a drawer under them,
    a plinth on bun feet, a moulded cornice, a hat box and a folded blanket on top."""
    wd = DARKWOOD if spec.get("dark", True) else WOOD
    S = Scene(pad_top=2)
    for x in (-11, 11):
        S.add(prism(x, 2.5, 1.6, 0, 1.6, M.wood(wd, bias=0.1), sides=8))
    S.add(box(-12.5, 12.5, 0.5, 12.5, 1.5, 4.5, M.wood(wd, bias=0.0)))
    S.add(box(-12, 12, 1, 12, 4.5, 37, M.wood(wd, bias=0.1)))
    S.add(box(-13, 13, 0, 13, 37, 40, M.wood(wd, bias=0.22)))
    S.add(box(-12, 12, 1, 12, 40, 40.8, M.wood(wd, bias=0.1)))
    a, b_ = _r7(CLOTH["teal"]), _r7(WHITE)
    S.add(prism(6, 7, 3.6, 40.8, 45, M.stripes(a, b_, w=2), sides=12))  # hat box
    S.add(prism(6, 7, 3.9, 45, 46, M.flat(a, 0.1), sides=12))
    S.add(box(-10, -1, 3, 10, 40.8, 43.5, _quilt_mat("patch", 3)))  # folded blanket
    cv = S.render()
    cv.on_wall(1)
    for x0, x1 in ((-11.5, -0.25), (0.25, 11.5)):
        _panel(cv, S.sx(x0), S.sx(x1), S.sy(1, 36), S.sy(1, 11), wd)
        _panel(cv, S.sx(x0) + 2, S.sx(x1) - 2, S.sy(1, 34), S.sy(1, 23), wd)
        _panel(cv, S.sx(x0) + 2, S.sx(x1) - 2, S.sy(1, 21), S.sy(1, 13), wd)
    _panel(cv, S.sx(-11.5), S.sx(11.5), S.sy(1, 10), S.sy(1, 5), wd)
    for x in (S.sx(-2), S.sx(1)):
        cv.set(x, S.sy(1, 22), BRASS)
        cv.set(x, S.sy(1, 22) + 1, BRASSR[1])
    for x in (S.sx(-6), S.sx(5)):
        cv.set(x, S.sy(1, 7.5), BRASS)
        cv.set(x, S.sy(1, 7.5) + 1, BRASSR[1])
    cv.set(S.sx(1), S.sy(1, 25), "#1d120d")
    cv.set(S.sx(1), S.sy(1, 24.5), BRASSR[4])
    return done(S, cv, "prop", fp(-12.5, 12.5, 12.5))


BOOKS = ["#7a2629", "#a8383a", "#2b4372", "#3d5f9c", "#2b5233", "#3f7447", "#7e5719", "#ad7d26", "#3d2862",
         "#5a3b8c", "#5a3d26", "#8a5f3b", "#1d4f53", "#e9e1cf"]


def _books(cv, rnd, x0, x1, bottom, hmax):
    """A shelf of books standing (a few leaning, a stack lying flat), spines toward the room."""
    x = x0
    while x < x1:
        r = rnd.random()
        if r < 0.1 and x + 6 <= x1:  # a little stack lying flat
            for j in range(rnd.randint(2, 3)):
                c = BOOKS[rnd.randrange(len(BOOKS))]
                w = rnd.randint(4, 6)
                for i in range(w):
                    cv.set(x + i + j % 2, bottom - 1 - j * 2, c)
                    cv.set(x + i + j % 2, bottom - 2 - j * 2, c if i else "#e9e1cf")
            x += 7
            continue
        if r < 0.18:
            x += rnd.randint(1, 2)  # a gap
            continue
        bw = 2 if rnd.random() < 0.7 else 1
        h = rnd.randint(hmax - 3, hmax)
        c = BOOKS[rnd.randrange(len(BOOKS))]
        dark = _darker(c)
        lean = r > 0.92 and x + bw + 2 <= x1
        for j in range(h):
            sh = (j * 2 // h) if lean else 0
            for i in range(bw):
                cc = c if i == 0 else dark
                if j in (2, 3) and h > 5:
                    cc = "#e8c15a" if j == 2 else cc  # title band
                cv.set(x + i + sh, bottom - 1 - j, cc)
        x += bw + (2 if lean else 0)


def _darker(c):
    r, g, b, a = C(c)
    return (round(r * 0.72), round(g * 0.72), round(b * 0.76), a)


def bookshelf(spec):
    """A tall bookcase: shelves of books in many colours, some leaning, one lying in a stack,
    a candle stub and a little plant among them, a moulded top."""
    rnd = random.Random(spec.get("seed", 1))
    wd = DARKWOOD if spec.get("dark") else WOOD
    w = M.wood(wd, bias=0.12)
    S = Scene(pad_top=2)
    S.add(box(-13, -11, 0, 9, 0, 38, w))
    S.add(box(11, 13, 0, 9, 0, 38, w))
    S.add(box(-11, 11, 7, 9, 0, 38, M.boards(wd, w=4, seed=5, bias=-0.15)))
    S.add(box(-11, 11, 0.5, 9, 0, 3, M.wood(wd, bias=0.0)))
    shelves = (11, 20, 29)
    for z in shelves:
        S.add(box(-11, 11, 0.5, 7, z, z + 1.5, w))
    S.add(box(-14, 14, -1, 10, 38, 40.5, M.planks(wd, h=4, seed=6, bias=0.12)))
    cv = S.render()
    cv.at_depth(3)
    for k, z in enumerate((3,) + tuple(z + 1.5 for z in shelves)):
        b = S.sy(3, z) + 1
        hmax = 7
        _books(cv, rnd, S.sx(-11), S.sx(11), b, hmax)
        if k == 2:  # a candle stub in a dish
            x = S.sx(7)
            for i in range(-1, 3):
                cv.set(x + i, b - 1, BRASSR[4] if i < 2 else BRASSR[2])
            candle(cv, x, b - 1, 2)
        if k == 3:  # a small plant in a pot
            x = S.sx(-9)
            for j in range(3):
                for i in range(3):
                    cv.set(x + i, b - 1 - j, CLAY[4] if i < 2 else CLAY[2])
            for dx, dy in ((0, -4), (1, -5), (2, -4), (-1, -5), (3, -5), (1, -4), (1, -6)):
                cv.set(x + dx, b + dy, LEAVES[4] if dy < -4 else LEAVES[3])
    return done(S, cv, "prop", fp(-13, 13, 9))


# ================================================================ shop

def counter(spec):
    """A shop counter: a panelled front, a polished top; on it a brass till with its keys and
    drawer, a big glass jar of sweets, a scale, parcels in brown paper tied with string, a bell
    and an oil lamp that is lit at night."""
    rnd = random.Random(spec.get("seed", 1))
    wd = DARKWOOD if spec.get("dark") else WOOD
    S = Scene(pad_top=2)
    S.add(box(-22, 22, 0, 12, 0, 2, M.wood(wd, bias=-0.05)))
    S.add(box(-22, 22, 0.5, 12, 2, 14, M.wood(wd, bias=0.08)))
    S.add(box(-23, 23, -1, 13, 14, 15.8, M.planks(HONEY, h=3, seed=3)))
    br = M.flat(BRASSR)
    S.add(box(6, 16, 4, 11, 15.8, 20, br))  # till
    S.add(box(7, 15, 8, 11, 20, 24, br))
    S.add(box(8, 14, 9, 10.5, 24, 26, M.flat(LINEN)))  # its little price window
    kr = M.flat(["#5a4a36", "#8a6e4a", "#b38f5e", "#c9a26a", "#dcb87c", "#ecd2a0"])  # parcels
    S.add(box(-3, 4, 5, 11, 15.8, 19.5, kr))
    S.add(box(-2, 3, 6, 10, 19.5, 22.5, kr))
    S.add(prism(-15, 7.5, 3.5, 15.8, 23, M.flat(["#3a5560", "#6f93a0", "#a8c9d2", "#cfe6ec", "#e9f6f8"]), sides=12))
    S.add(prism(-15, 7.5, 2.4, 23, 24.5, M.flat(BRASSR), sides=10))
    cv = S.render()
    cv.on_wall(0.5)
    for k in range(5):
        x0 = S.sx(-21 + k * 8.6)
        _panel(cv, x0, x0 + 8, S.sy(0.5, 12), S.sy(0.5, 3.5), wd)
    # till: keys on its sloping front, drawer, price tabs
    cv.on_wall(4)
    d0 = S.sy(4, 18.5)
    for x in range(S.sx(6) + 1, S.sx(16) - 1):
        cv.set(x, d0, BRASSR[1])
    cv.set(S.sx(11), d0 + 2, BRASSR[6])
    cv.free()
    ky = S.sy(5.5, 20)
    for kx in range(S.sx(7), S.sx(15), 2):
        for row in (0, 2):
            cv.set(kx, ky - row - 1, "#f4ecd9")
            cv.set(kx, ky - row, "#1d120d")
    cv.on_wall(9, tol=1.2)
    for x in range(S.sx(9), S.sx(13)):
        cv.set(x, S.sy(9, 25), "#2a1a12" if x % 2 else LINEN[3])
    # sweets in the jar
    cv.at_depth(4)
    jx, jb = S.sx(-15), S.sy(4, 15.8)
    for y in range(jb - 6, jb - 1):
        for x in range(jx - 2, jx + 3):
            if rnd.random() < 0.8:
                cv.set(x, y, ("#e74c3c", "#f1c40f", "#5a82c0", "#ff9ec4", "#86bd78")[rnd.randrange(5)])
    cv.set(jx - 3, jb - 6, "#f4fbfd")
    cv.set(jx - 3, jb - 5, "#f4fbfd")
    # string round the parcels
    cv.free()
    for z0, z1, y_ in ((15.8, 19.5, 5), (19.5, 22.5, 6)):
        x = S.sx(0.5)
        for y in range(S.sy(y_, z1), S.sy(y_, z0)):
            cv.set(x, y, "#f4ecd9")
    # a scale with its pans and a bell
    cv.at_depth(3)
    b = S.sy(3, 15.8) + 1
    x = S.sx(-9)
    for i in range(-3, 4):
        cv.set(x + i, b - 7, BRASSR[4] if i < 0 else BRASSR[3])
    for y in range(b - 7, b - 1):
        cv.set(x, y, BRASSR[3])
    for i in range(-2, 3):
        cv.set(x + i, b - 1, BRASSR[2])
    for side in (-1, 1):
        for i in range(3):
            cv.set(x + side * 3 - 1 + i, b - 4, BRASSR[5] if i == 0 else BRASSR[3])
        cv.set(x + side * 3, b - 6, BRASSR[2])
        cv.set(x + side * 3, b - 5, BRASSR[2])
    bx = S.sx(19)
    for dx, dy, c in ((0, -4, BRASSR[5]), (-1, -3, BRASSR[4]), (0, -3, BRASSR[4]), (1, -3, BRASSR[3]), (-1, -2, BRASSR[4]),
                      (0, -2, BRASSR[3]), (1, -2, BRASSR[2]), (-2, -1, BRASSR[3]), (-1, -1, BRASSR[3]), (0, -1, BRASSR[2]),
                      (1, -1, BRASSR[2]), (2, -1, BRASSR[1]), (0, -5, BRASSR[2])):
        cv.set(bx + dx, b + dy, c)
    # an oil lamp at the left end, lit at night
    cv.at_depth(6)
    b = S.sy(6, 15.8) + 1
    x = S.sx(-20)
    for i in range(-2, 3):
        cv.set(x + i, b - 1, BRASSR[4] if i < 1 else BRASSR[2])
        cv.set(x + i, b - 2, BRASSR[3] if i < 1 else BRASSR[2])
    for i in (-1, 0, 1):
        cv.set(x + i, b - 3, BRASSR[2])
    for y in range(b - 9, b - 3):
        for i in (-1, 0, 1):
            if y == b - 9 and i != 0:
                continue
            c = "#f6efd8" if i < 1 else "#d8cfb6"
            cv.set(x + i, y, c)
            cv.lit(x + i, y, LIT[4] if y < b - 5 else LIT[3])
    cv.set(x, b - 6, "#ffd27a")
    cv.lit(x, b - 6, LIT[4])
    return done(S, cv, "prop", fp(-22, 22, 12))


# ================================================================ odds and ends

def _chest_mat(wood=WOOD):
    planks = M.planks(wood, h=4, seed=4, bias=0.15)

    def f(u, v, kind, light, P, s):
        if 4.8 <= abs(P[0]) <= 6.4:  # iron bands over body and lid
            return _t(IRONK, light + 0.3)
        return planks.fn(u, v, kind, light, P, s)
    return Mat(f)


def chest(spec):
    """A wooden storage chest with a domed lid, two iron bands, iron corners, a brass lock plate."""
    wd = DARKWOOD if spec.get("dark") else WOOD
    S = Scene(pad_top=2)
    cm = _chest_mat(wd)
    S.add(box(-9, 9, 0, 11, 0, 8, cm))
    S.add(prism_x(-9, 9, 5.5, 8, 5.5, cm, sides=16))
    cv = S.render()
    cv.on_wall(0)
    for xx, d in ((S.sx(-9), 1), (S.sx(9) - 1, -1)):  # corner irons
        for k in range(3):
            cv.set(xx + d * k, S.sy(0, 0.5), IRONK[4] if k == 0 else IRONK[3])
            cv.set(xx, S.sy(0, 0.5) - k, IRONK[4])
            cv.set(xx + d * k, S.sy(0, 7.5), IRONK[4])
            cv.set(xx, S.sy(0, 7.5) + k, IRONK[4])
    cv.free()
    x, y = S.sx(0), S.sy(0, 8)
    for j in range(5):
        for i in range(-2, 2):
            c = BRASSR[5] if i < 0 and j < 2 else BRASSR[4] if i < 1 else BRASSR[2]
            if j == 4:
                c = BRASSR[1]
            cv.set(x + i, y - 2 + j, c)
    cv.set(x - 1, y, "#1d120d")
    cv.set(x - 1, y + 1, "#1d120d")
    return done(S, cv, "prop", fp(-9, 9, 11))


def pot_plant(spec):
    """A terracotta pot on a saucer, an aspidistra in it: a fan of long leaves rising and arching
    out, lit along their upper edges."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad=8, pad_top=20)
    S.add(prism(0, 4.5, 4.8, 0, 1, M.flat(CLAY, 0.05), sides=14))  # saucer
    S.add(frustum(0, 4.5, 3.4, 4.3, 1, 8, M.flat(CLAY, 0.0), sides=14))
    rim = S.add(prism(0, 4.5, 4.8, 8, 10, M.flat(CLAY, 0.12), sides=14))
    cv = S.render()
    ri = S.solids.index(rim)
    for y in range(cv.h):  # soil inside the rim
        for x in range(cv.w):
            if S.sid[y, x] == ri and S.pid[y, x] == 1:
                X = x + 0.5 - S.ox
                Y = (S.base - (y + 0.5) - 10) / K
                if math.hypot(X, Y - 4.5) < 3.6:
                    cv.px[x, y] = C("#3b2a1e" if (x + y) % 3 else "#4f3828")
    cv.free()
    rx, ry = S.s(0, 5, 10)
    n = spec.get("leaves", 11)
    order = sorted(range(n), key=lambda k: -abs(k - (n - 1) / 2))  # outer leaves first, the middle ones in front
    for k in order:
        off = (k - (n - 1) / 2) / ((n - 1) / 2)  # -1 .. 1
        a = -math.pi / 2 + off * 1.25 + rnd.uniform(-0.08, 0.08)
        L = rnd.uniform(13, 19) * (1 - 0.25 * abs(off))
        g = 0.035 * abs(off) + 0.004
        x0 = rx + round(off * 1.5)
        pts = []
        for i in range(int(L)):
            dx = math.cos(a) * i
            dy = math.sin(a) * i + g * i * i
            pts.append((x0 + dx, ry + dy, i / L, math.atan2(math.sin(a) + 2 * g * i, math.cos(a))))
        for (px, py, t, ang) in pts:
            wdt = 2.1 * math.sin(min(1.0, t * 1.1) * math.pi) + 0.2
            nx, ny = -math.sin(ang), math.cos(ang)
            for o in range(-math.ceil(wdt), math.ceil(wdt) + 1):
                if abs(o) > wdt:
                    continue
                xx, yy = round(px + nx * o), round(py + ny * o)
                upper = (ny * o) < 0  # the half facing up catches the light
                c = LEAVES[5] if upper and abs(o) >= 1 else LEAVES[4] if upper else LEAVES[3]
                if not upper and abs(o) >= 1:
                    c = LEAVES[3] if abs(off) < 0.5 else LEAVES[2]
                cv.set(xx, yy, c)
            if t > 0.2:
                cv.set(round(px), round(py), LEAVES[3])
            else:
                cv.set(round(px), round(py), LEAVES[2])
    S.finish(cv)
    return _result(cv, "prop", (S.ox, S.base), fp(-4.8, 4.8, 9.3))


def _pleats(ramp):
    def f(u, v, kind, light, P, s):
        if kind == "top":
            d = math.hypot(P[0] - s.params["cx"], P[1] - s.params["cy"])
            return ramp[2] if d > s.params["r1"] - 1.0 else LINEN[5] if d > 1.2 else BRASSR[4]
        zz = P[2] - s.bbox[4]
        if zz < 1 or zz > s.bbox[5] - s.bbox[4] - 1:
            return _st(ramp, light + 0.1, -1)  # bound edges
        return _t(ramp, light + 0.2) if math.floor(u / 1.6) % 2 else _st(ramp, light + 0.2, -1)
    return Mat(f)


def floor_lamp(spec):
    """A standing lamp: a weighted brass foot, a slender pole, a pleated drum shade bound at top
    and bottom with a fringe; at night the shade glows and light spills from under it."""
    shade = _r7(CLOTH[spec.get("shade", "ochre")])
    S = Scene(pad_top=2)
    br = M.flat(BRASSR, 0.1)
    S.add(prism(0, 3, 3.4, 0, 1.2, br, sides=12))
    S.add(frustum(0, 3, 1.7, 0.8, 1.2, 3.5, br, sides=10))
    S.add(box(-0.5, 0.5, 2.5, 3.5, 3.5, 29, M.flat(BRASSR, 0.2)))
    sh = S.add(frustum(0, 3, 6.5, 4.6, 27, 33.5, _pleats(shade), sides=18))
    sh.params["r1"] = 4.6
    cv = S.render()
    si = S.solids.index(sh)
    for y in range(cv.h):
        for x in range(cv.w):
            if S.sid[y, x] == si:
                top = S.pid[y, x] == 1
                cv.lit(x, y, LIT[4] if top else LIT[3] if (x + (y > S.sy(0, 30))) % 2 else LIT[2])
    cv.free()
    for x in range(S.sx(-6.5), S.sx(6.5)):  # the fringe along the lowest edge of the shade
        X = x + 0.5 - S.ox
        yf = 3 - math.sqrt(max(0.0, 42 - X * X))
        y = S.sy(yf, 27)
        cv.set(x, y, shade[2])
        if x % 2:
            cv.set(x, y + 1, shade[3])
        cv.lit(x, y, LIT[1])
        cv.lit(x, y - 1, LIT[4])
    return done(S, cv, "prop", fp(-3.4, 3.4, 6.4))


def _rag_mat(cols, R):
    """A braided rag rug: concentric braids in a few colours, chevrons along each braid."""
    def f(u, v, kind, light, P, s):
        cx, cy = s.params["cx"], s.params["cy"]
        dx, dy = P[0] - cx, P[1] - cy
        d = math.hypot(dx, dy)
        ring = math.floor(d / 2.2)
        r = cols[ring % len(cols)] if d < R - 1.6 else cols[0]
        ang = math.atan2(dy, dx) * max(d, 1)
        chev = (math.floor(ang / 1.6) + (1 if (d % 2.2) < 1.1 else 0)) % 2
        if (d % 2.2) < 0.55:
            return r[0]
        return r[2] if chev else r[1]
    return Mat(f)


def rug_round(spec):
    """A round braided rag rug lying flat (walked over)."""
    cols = [["#4a1619", "#8c2f30", "#b9443e"], ["#7e5719", "#ad7d26", "#d4a340"], ["#9a8c80", "#cfc3b4", "#ece4d6"],
            ["#1d2c4c", "#2d4777", "#3f63a0"], ["#2b5233", "#3f7447", "#5a965c"]]
    R = spec.get("radius", 16)
    S = Scene(pad=2, pad_top=2, pad_bottom=2, outline="#3a1418")
    S.add(prism(0, R, R, 0, 0.6, _rag_mat(cols, R), sides=36))
    cv = S.render()
    return done(S, cv, "rug", fp(-R, R, 2 * R), solid=False)


def _runner_mat(field, border):
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        bx, by = min(P[0] - x0, x1 - P[0]), min(P[1] - y0, y1 - P[1])
        b = min(bx, by)
        if b < 1:
            return border[0]
        if b < 3:
            return border[2] if (math.floor(P[0]) + math.floor(P[1] * 0.8)) % 4 else "#ece4d6"
        if b < 4:
            return border[1]
        cyy = (y0 + y1) / 2
        k = (P[0] - x0 - 4) % 12 - 6
        dm = abs(k) + abs(P[1] - cyy) * 1.4
        if dm < 1.2:
            return "#f1cf5e"
        if dm < 3:
            return "#ece4d6"
        if dm < 4.2:
            return border[1]
        return field[2] if (math.floor(P[0] / 2) + math.floor(P[1])) % 7 else field[1]
    return Mat(f)


def rug_runner(spec):
    """A long woven runner with a border, a row of diamonds down the middle and fringed ends."""
    field = CLOTH[spec.get("cloth", "red")]
    border = CLOTH[spec.get("border", "blue")]
    S = Scene(pad=4, pad_top=2, pad_bottom=2, outline="#2a1418")
    L = spec.get("length", 26)
    S.add(box(-L, L, 0, 14, 0, 0.6, _runner_mat(field, border)))
    cv = S.render()
    S.finish(cv)
    for x_end, d in ((S.sx(-L) - 1, -1), (S.sx(L), 1)):  # fringes
        for y in range(S.sy(14, 0.6) + 1, S.sy(0, 0.6)):
            if y % 2 == 0:
                cv.set(x_end, y, "#ece4d6")
                cv.set(x_end + d, y, "#cfc3b4")
                cv.set(x_end + 2 * d, y, "#cfc3b4" if (y // 2) % 2 else (0, 0, 0, 0))
            else:
                cv.set(x_end, y, "#9a8c80")
    im, night, info = _result(cv, "rug", (S.ox, S.base), fp(-L - 2, L + 2, 14))
    info["solid"] = False
    return im, night, info


DESIGNS = {
    "wall_back": wall_back, "wall_window": wall_window, "wall_picture": wall_picture, "wall_shelf": wall_shelf,
    "wall_side": wall_side, "wall_corner": wall_corner, "bed": bed, "stove": stove, "fireplace": fireplace,
    "table_set": table_set, "chair": chair, "dresser": dresser, "wardrobe": wardrobe, "bookshelf": bookshelf,
    "counter": counter, "chest": chest, "pot_plant": pot_plant, "floor_lamp": floor_lamp, "rug_round": rug_round,
    "rug_runner": rug_runner,
}

ENTRIES = [
    {"id": "wall_back", "name": "墙面", "group": GROUP, "type": "wall_back", "seed": 1, "paper": "sage"},
    {"id": "wall_window", "name": "窗户墙", "group": GROUP, "type": "wall_window", "seed": 1, "paper": "sage", "curtain": "red"},
    {"id": "wall_picture", "name": "挂画墙", "group": GROUP, "type": "wall_picture", "seed": 1, "paper": "sage"},
    {"id": "wall_shelf", "name": "壁架墙", "group": GROUP, "type": "wall_shelf", "seed": 2, "paper": "sage"},
    {"id": "wall_side", "name": "左侧墙", "group": GROUP, "type": "wall_side", "seed": 1, "paper": "sage", "side": "left"},
    {"id": "wall_side_r", "name": "右侧墙", "group": GROUP, "type": "wall_side", "seed": 1, "paper": "sage", "side": "right"},
    {"id": "wall_corner", "name": "墙角柱", "group": GROUP, "type": "wall_corner", "seed": 1},
    {"id": "bed", "name": "单人床", "group": GROUP, "type": "bed", "seed": 3, "quilt": "patch"},
    {"id": "bed_double", "name": "双人床", "group": GROUP, "type": "bed", "seed": 4, "double": True, "quilt": "blue", "dark": True},
    {"id": "stove", "name": "灶台", "group": GROUP, "type": "stove", "seed": 1},
    {"id": "fireplace", "name": "壁炉", "group": GROUP, "type": "fireplace", "seed": 1},
    {"id": "table_set", "name": "餐桌椅", "group": GROUP, "type": "table_set", "seed": 1},
    {"id": "chair", "name": "椅子", "group": GROUP, "type": "chair", "seed": 1, "cushion": "red"},
    {"id": "dresser", "name": "碗柜", "group": GROUP, "type": "dresser", "seed": 1},
    {"id": "wardrobe", "name": "衣柜", "group": GROUP, "type": "wardrobe", "seed": 1},
    {"id": "bookshelf", "name": "书架", "group": GROUP, "type": "bookshelf", "seed": 5},
    {"id": "counter", "name": "柜台", "group": GROUP, "type": "counter", "seed": 1},
    {"id": "chest", "name": "储物箱", "group": GROUP, "type": "chest", "seed": 1},
    {"id": "pot_plant", "name": "盆栽", "group": GROUP, "type": "pot_plant", "seed": 2},
    {"id": "floor_lamp", "name": "落地灯", "group": GROUP, "type": "floor_lamp", "seed": 1, "shade": "ochre"},
    {"id": "rug_round", "name": "圆地毯", "group": GROUP, "type": "rug_round", "seed": 1},
    {"id": "rug_runner", "name": "长条地毯", "group": GROUP, "type": "rug_runner", "seed": 1, "cloth": "red", "border": "blue"},
]
