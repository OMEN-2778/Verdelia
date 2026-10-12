"""Town buildings modelled in 3D and drawn with the oblique renderer (oblique.py), so they show
their depth from the usual front-and-45-degrees-above view: houses, the manor, the tower, the
barn, the windmill, shops, the smithy and the inn.

Each design builds a Scene of solids (walls, roofs, chimneys, steps, porches, awnings...), renders
it, then draws the 2D details (doors, windows, signs, lanterns...) from buildings.py onto the
walls they belong to. World units are pixels; x right, y back, z up; the base point is the middle
of the front wall at ground level."""
import math
import random

import materials as M
from buildings import (C, DARKWOOD, FIELDSTONE, IRON, LIT, PAINT, PLASTER, ROOFS, STONE, TRIM, WOOD, _result,
                       board_sign, door, flower_box, hanging_sign, item, lantern, sack, shop_window, window)
from landmarks import BARN_RED, CREAM, EMBER, HAY, SAIL_FRAMES, WHITE_TRIM, _sails
from oblique import K, Scene, box, frustum, gable_y, gambrel_y, gambrel_shell_y, hip_x, prism, pyramid, roof_shell_y, slab
from PIL import Image

STEEL = ["#2a2e38", "#4f5562", "#808897", "#b7bec9", "#e9edf2"]
COPPER = ["#3d1f10", "#6e3e20", "#9a5a2e", "#c97a3e", "#e8a066", "#f6c99a"]


# ================================================================ shared parts

def footing(S, x0, x1, y0, y1, seed=2):
    S.add(box(x0 - 1, x1 + 1, y0 - 1, y1 + 1, 0, 4, M.dressed_stone(STONE, seed=seed)))


def step(S, cx, w=18, depth=5, z=0, h=3):
    S.add(box(cx - w / 2, cx + w / 2, -depth, 0, z, z + h, M.dressed_stone(STONE, seed=4, bias=0.2)))


def chimney(S, cx, cy, z0, z1, w=8):
    S.add(box(cx - w / 2, cx + w / 2, cy - w / 2, cy + w / 2, z0, z1, M.chimney_stone()))
    return (cx, cy, z1)


def hip_roof(S, x0, x1, y0, y1, ze, pitch, hip, mat, th=3):
    zr = ze + (y1 - y0) / 2 * pitch
    S.add(hip_x(x0, x1, y0, y1, ze - th, ze, zr, hip, mat))
    return zr


def gable_front(S, wx0, wx1, y_wall, y_back, zw, pitch, roof_mat, wall_mat, over=4, th=3):
    """A roof with its gable to the street over walls wx0..wx1 topped at zw: the gable wall (a
    triangle of wall_mat) and two roof boards over it, overhanging by `over`."""
    xc = (wx0 + wx1) / 2
    zr_wall = zw + (xc - wx0) * pitch
    S.add(gable_y(wx0, wx1, y_wall, y_back, zw - 1, zw, zr_wall, wall_mat))
    ze = zw - pitch * over + th
    zr = ze + (xc - wx0 + over) * pitch
    for s in roof_shell_y(wx0 - over, wx1 + over, y_wall - over, y_back + over, ze, zr, th, roof_mat):
        S.add(s)
    return zr_wall, zr


def corner_posts(S, x0, x1, y0, y1, z0, z1):
    for px in (x0 - 1, x1 - 3):
        S.add(box(px, px + 4, y0 - 1, y1 + 1, z0, z1, M.wood(TRIM, bias=0.0)))


def chims_screen(S, pts):
    return [S.s(x, y, z) for x, y, z in pts]


def done(S, cv, kind, footprint, door_x=None, door_w=14, chims=(), extra=None):
    S.finish(cv)
    out = _result(cv, kind, (S.ox, S.base), footprint, S.sx(door_x) if door_x is not None else None, door_w,
                  chims_screen(S, chims))
    return out if extra is None else (*out, extra)


def fp(x0, x1, d):
    fd = round(K * d)
    return [round(x0), -fd, round(x1 - x0), fd]


# ================================================================ houses

def cabin(spec):
    """Plain log cabin: plank walls on a stone footing, a hipped shingle roof, a stone chimney,
    a door with a step, shuttered windows."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = spec.get("width", 76), spec.get("depth", 44), spec.get("wall", 32)
    h2 = ww / 2
    S = Scene()
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, wall_h, M.planks(WOOD, seed=spec.get("seed", 1))))
    corner_posts(S, -h2, h2, 0, d, 4, wall_h)
    over = 5
    rm = M.shingles(ROOFS[spec.get("roof_colour", "rust")], seed=spec.get("seed", 1), moss=0.06 if spec.get("moss") else None)
    zr = hip_roof(S, -h2 - over, h2 + over, -over, d + over, wall_h, spec.get("pitch", 0.58), spec.get("hip", 16), rm)
    chims = []
    if spec.get("chimney", 0.7) is not None:
        chims.append(chimney(S, -h2 + ww * spec.get("chimney", 0.7), d * 0.55, wall_h, zr + 9))
    dcx = -h2 + ww * spec.get("door_at", 0.5)
    step(S, dcx)
    cv = S.render()
    cv.on_wall(0)
    door(cv, rnd, S.sx(dcx), S.sy(0, 4), step=False, style=spec.get("door", "plank"))
    for wf in spec.get("windows", (0.2, 0.8)):
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(0, 22), shutters=spec.get("shutters"), box=spec.get("flowers"))
    return done(S, cv, "house", fp(-h2, h2, d), dcx, chims=chims)


def cottage(spec):
    """Low fieldstone cottage under a thick, round-hipped thatch, an arched door, a small window
    with a flower box, a chimney and a climbing rose."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = 60, 38, 24
    h2 = ww / 2
    S = Scene()
    S.add(box(-h2, h2, 0, d, 0, wall_h, M.fieldstone(FIELDSTONE, seed=spec.get("seed", 1))))
    over = 6
    zr = wall_h + (d / 2 + over) * 0.8
    S.add(hip_x(-h2 - over, h2 + over, -over, d + over, wall_h - 5, wall_h, zr, 17, M.thatch(ROOFS["thatch"], seed=3)))
    ch = chimney(S, -h2 + 13, d * 0.45, wall_h, zr + 6)
    dcx = h2 - 20
    step(S, dcx, w=16, depth=4)
    cv = S.render()
    cv.on_wall(0)
    door(cv, rnd, S.sx(dcx), S.sy(0, 0), w=13, h=19, style="arched", wood=DARKWOOD, step=False)
    window(cv, rnd, S.sx(-h2 + 15), S.sy(0, 17), w=10, h=9, box=True)
    for z in range(1, 18):  # a climbing rose up the right corner
        x = S.sx(h2 - 3) + round(math.sin(z * 0.6))
        y = S.sy(0, z)
        cv.set(x, y, ("#2d5a2c", "#3f7a37", "#5fa047")[rnd.randint(0, 2)])
        if rnd.random() < 0.3:
            cv.set(x - 1, y, "#ff9ec4")
    return done(S, cv, "house", fp(-h2, h2, d), dcx, door_w=13, chims=[ch])


def townhouse(spec):
    """Two storeys, gable to the street: stone (or planks) below, plaster in a timber frame
    above, jettied out a little, flower boxes; the roof runs back in two long planes."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d = spec.get("width", 52), 46
    h2 = ww / 2
    pal = PAINT[spec.get("plaster", "cream")]
    S = Scene()
    low = M.fieldstone(FIELDSTONE, seed=5) if spec.get("lower", "stone") == "stone" else M.planks(WOOD, seed=5)
    S.add(box(-h2, h2, 0, d, 0, 26, low))
    S.add(box(-h2 - 2, h2 + 2, -3, d, 25, 28, M.wood(DARKWOOD, bias=0.0)))  # jetty beam
    S.add(box(-h2 - 2, h2 + 2, -2, d, 28, 50, M.plaster(pal, frame=([-h2 - 2, -1.5, h2 - 1], [28, 47]))))
    zr_wall, zr = gable_front(S, -h2 - 2, h2 + 2, -2, d, 50, 0.78, M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=6),
                              M.plaster(pal, frame=([-1.5], [])))
    dcx = -h2 + ww * spec.get("door_at", 0.3)
    step(S, dcx, w=16)
    cv = S.render()
    cv.on_wall(-2)
    for wf in (0.25, 0.75):
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(-2, 44), w=10, h=10, box=spec.get("flowers", True))
    cv.on_wall(-2, tol=2.0)
    vx, vz = S.sx(0), S.sy(-2, 50 + (zr_wall - 50) * 0.45)
    for y in range(vz - 2, vz + 3):  # a round vent in the gable
        for x in range(vx - 3, vx + 4):
            dd = (x - vx) ** 2 + (y - vz) ** 2
            if dd <= 6:
                cv.set(x, y, "#2c2622" if dd <= 2 else DARKWOOD[3])
    cv.on_wall(0)
    door(cv, rnd, S.sx(dcx), S.sy(0, 0), style=spec.get("door", "plank"), wood=DARKWOOD, step=False)
    wf2 = 0.75 if spec.get("door_at", 0.3) < 0.5 else 0.25
    window(cv, rnd, S.sx(-h2 + ww * wf2), S.sy(0, 19), w=12, h=11, shutters=spec.get("shutters"))
    if spec.get("sign"):
        cv.free()
        side = 1 if wf2 < 0.5 else -1
        hanging_sign(cv, S.sx(h2 + 2 if side > 0 else -h2 - 2), S.sy(-3, 26), spec["sign"], side)
    return done(S, cv, "house", fp(-h2, h2, d), dcx)


def manor(spec):
    """A two-storey manor under a long hipped roof: stone below, plaster and timber above, a
    middle bay that steps forward with its own gable, a balcony and double doors up a flight of
    steps, dormers on the roof either side, two chimneys, potted bay trees."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d = 116, 54
    h2 = ww / 2
    pal = PAINT[spec.get("plaster", "cream")]
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=4, moss=0.03)
    S = Scene()
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, 27, M.dressed_stone(STONE, seed=3)))
    S.add(box(-h2, h2, 0, d, 27, 50, M.plaster(pal, frame=([-h2, -h2 + 24, h2 - 27, h2 - 3], [27, 47]))))
    over, pitch = 5, 0.6
    zr = hip_roof(S, -h2 - over, h2 + over, -over, d + over, 50, pitch, 24, rm)
    chims = [chimney(S, -h2 + 12, d * 0.5, 50, zr + 8), chimney(S, h2 - 12, d * 0.5, 50, zr + 8)]
    # dormers on the front slope
    dorm = []
    for dx in (-34, 34):
        yd = 8
        zb = 50 + (yd + over) * pitch
        S.add(box(dx - 7, dx + 7, yd, yd + 14, zb - 3, zb + 11, M.plaster(pal)))
        for s in roof_shell_y(dx - 9, dx + 9, yd - 2, yd + 14, zb + 9, zb + 17, 2, rm):
            S.add(s)
        S.add(gable_y(dx - 7, dx + 7, yd, yd + 14, zb + 10, zb + 11, zb + 16, M.plaster(pal)))
        dorm.append((dx, yd, zb))
    # the middle bay
    bw = 40
    S.add(box(-bw / 2, bw / 2, -8, 12, 0, 27, M.dressed_stone(FIELDSTONE, seed=9)))
    S.add(box(-bw / 2, bw / 2, -8, 12, 27, 52, M.plaster(pal, frame=([-bw / 2, bw / 2 - 3], [27, 49]))))
    zr_w, zr_b = gable_front(S, -bw / 2, bw / 2, -8, 26, 52, 0.75, rm, M.plaster(pal))
    # balcony, steps
    S.add(box(-bw / 2 - 2, bw / 2 + 2, -13, -8, 25, 27, M.wood(DARKWOOD, bias=0.1)))
    step(S, 0, w=24, depth=13, h=2)
    S.add(box(-10, 10, -11, -8, 2, 4, M.dressed_stone(STONE, seed=4, bias=0.25)))
    # potted bay trees
    for px in (-22, 22):
        S.add(prism(px, -12, 3, 0, 5, M.wood(["#3d1f10", "#6e3e24", "#9a5a36", "#b9774a", "#d0956a"], bias=0.1), sides=10))
        S.add(prism(px, -12, 4, 5, 13, M.flat(["#1d3b1e", "#2d5a2c", "#3f7a37", "#5fa047", "#86c25a"]), sides=10))
    cv = S.render()
    cv.on_wall(0)
    for wf in (0.08, 0.27, 0.73, 0.92):
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(0, 45), w=10, h=10, shutters=spec.get("shutters", "green"))
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(0, 22), w=10, h=12, shutters=spec.get("shutters", "green"),
               box=wf in (0.27, 0.73))
    for dx, yd, zb in dorm:
        cv.on_wall(yd)
        window(cv, rnd, S.sx(dx), S.sy(yd, zb + 9), w=8, h=7)
    cv.on_wall(-8)
    window(cv, rnd, S.sx(0), S.sy(-8, 47), w=14, h=13, arch=True)
    door(cv, rnd, S.sx(0), S.sy(-8, 4), w=18, h=22, style="double", wood=DARKWOOD, step=False)
    lantern(cv, S.sx(-14), S.sy(-8, 23))
    lantern(cv, S.sx(12), S.sy(-8, 23))
    cv.at_depth(-13)
    by = S.sy(-13, 27)
    for x in range(S.sx(-bw / 2 - 2), S.sx(bw / 2 + 2)):  # balcony rail
        cv.set(x, by - 7, DARKWOOD[5])
        if (x - S.sx(-bw / 2)) % 3 == 0:
            for y in range(by - 6, by):
                cv.set(x, y, DARKWOOD[4])
    flower_box(cv, rnd, S.sx(-bw / 2), S.sx(-bw / 2 + 12), by - 10)
    flower_box(cv, rnd, S.sx(bw / 2 - 12), S.sx(bw / 2), by - 10)
    return done(S, cv, "house", fp(-h2, h2, d), 0, door_w=18, chims=chims)


def tower(spec):
    """A round stone tower: a plinth, courses round the drum, arched windows climbing a spiral
    stair, a ring of corbels, a cone roof of slate with a flag on top, ivy up one side."""
    rnd = random.Random(spec.get("seed", 1))
    r, cy = 17, 18
    S = Scene(pad_top=14)
    S.add(prism(0, cy, r + 2, 0, 5, M.dressed_stone(STONE, seed=2, bias=0.15), sides=24))
    S.add(prism(0, cy, r, 5, 86, M.dressed_stone(STONE, seed=7), sides=24))
    S.add(prism(0, cy, r + 2, 84, 88, M.dressed_stone(STONE, seed=3, bias=0.25), sides=24))
    top = 128
    S.add(pyramid(0, cy, r + 7, 87, top, M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=8), sides=24))
    cv = S.render()
    front = cy - r
    cv.on_wall(front, tol=2.5)
    door(cv, rnd, S.sx(-1), S.sy(front, 5), w=12, h=19, style="arched", wood=DARKWOOD, step=False)
    for dx, z in ((7, 40), (-6, 58), (5, 77)):
        window(cv, rnd, S.sx(dx), S.sy(front, z), w=7, h=10, arch=True)
    for z in range(6, 46):  # ivy
        x = S.sx(-r + 4) + round(2.5 * math.sin(z * 0.22))
        for dxl in (-1, 0, 1):
            if rnd.random() < 0.55:
                cv.set(x + dxl, S.sy(front, z), ("#2d5a2c", "#3f7a37", "#5fa047")[rnd.randint(0, 2)])
    cv.free()
    ax, ay = S.s(0, cy, top)
    for y in range(ay - 10, ay + 1):
        cv.set(ax, y, IRON[2])
    from market import CLOTH, pennant
    pennant(cv, ax, ay - 9, CLOTH[spec.get("flag", "red")], right=True)
    return done(S, cv, "house", fp(-r, r, 2 * r), -1, door_w=12)


def barn(spec):
    """A big red barn, gable to the front under a gambrel roof: cross-braced double doors, a hay
    loft door with a hoist beam, small windows, hay bales, a barrel and a weathervane."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = 78, 62, 34
    h2 = ww / 2
    red = M.boards(BARN_RED, seed=3)
    roof = M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=5)
    S = Scene(pad_top=12)
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, wall_h, red))
    for px in (-h2 - 1, h2 - 3):
        S.add(box(px, px + 4, -1, d + 1, 4, wall_h, M.wood(WHITE_TRIM, bias=0.15)))
    knee, p1, p2 = 13, 1.45, 0.48
    zk = wall_h + knee * p1
    zr_w = zk + (h2 - knee) * p2
    S.add(gambrel_y(-h2, h2, 0, d, wall_h - 1, wall_h, knee, zk, zr_w, red))
    over, th = 4, 3
    ze = wall_h - p1 * over + th
    zk2 = ze + (knee + over) * p1
    zr = zk2 + (h2 - knee) * p2
    for s in gambrel_shell_y(-h2 - over, h2 + over, -over, d + over, ze, knee + over, zk2, zr, th, roof):
        S.add(s)
    # hay bales and a barrel in front
    hay = M.flat(HAY)
    S.add(box(-h2 - 14, -h2 - 2, -10, -2, 0, 7, hay))
    S.add(box(-h2 - 2, -h2 + 9, -12, -4, 0, 7, hay))
    S.add(box(-h2 - 10, -h2 + 1, -6, 2, 7, 13, hay))
    S.add(prism(h2 + 6, -5, 4, 0, 10, M.barrel(seed=2), sides=12))
    cv = S.render()
    cv.on_wall(0)
    from landmarks import x_door
    dw, dh = 30, 26
    base_y = S.sy(0, 4)
    x_door(cv, S.sx(-dw / 2), S.sx(0), base_y - dh, base_y, BARN_RED)
    x_door(cv, S.sx(0), S.sx(dw / 2), base_y - dh, base_y, BARN_RED)
    for x in range(S.sx(-dw / 2 - 4), S.sx(dw / 2 + 4)):
        cv.set(x, base_y - dh - 3, DARKWOOD[4])
        cv.set(x, base_y - dh - 2, DARKWOOD[2])
    for wx in (-h2 + 9, h2 - 9):
        window(cv, rnd, S.sx(wx), S.sy(0, wall_h - 4), w=8, h=7, frame=WHITE_TRIM + ["#ffffff"])
    cv.on_wall(0, tol=2.0)
    ly = S.sy(0, wall_h + 18)
    x_door(cv, S.sx(-7), S.sx(7), ly, ly + 13, BARN_RED)
    for y in range(ly + 2, ly + 12):
        for x in range(S.sx(-5), S.sx(5)):
            cv.set(x, y, "#2a1d16")
    for x in range(S.sx(-5), S.sx(5)):
        for i in range(1 + (x * 7) % 3):
            cv.set(x, ly + 11 - i, HAY[3] if i == 0 else HAY[2])
    cv.free()
    for x in range(S.sx(-2), S.sx(3)):  # hoist beam
        cv.set(x, ly - 4, DARKWOOD[5])
        cv.set(x, ly - 3, DARKWOOD[2])
    for y in range(ly - 2, ly + 3):
        cv.set(S.sx(0), y, "#5c4632")
    tx, ty = S.s(0, -over, zr)  # weathervane on the front of the ridge
    for y in range(ty - 9, ty):
        cv.set(tx, y, IRON[1])
    for ddx, ddy in ((0, -10), (1, -10), (2, -10), (-1, -11), (0, -11), (1, -11), (2, -11), (3, -12), (-2, -12), (-1, -12), (3, -11), (-1, -13)):
        cv.set(tx + ddx, ty + ddy, IRON[1])
    for x in range(tx - 4, tx + 5):
        cv.set(x, ty - 6, IRON[2])
    for y in range(S.sy(-3, 0) - 22, S.sy(-3, 0)):  # pitchfork leaning by the door
        cv.set(S.sx(h2 + 1), y, WOOD[4])
    for ddx in (-1, 0, 1):
        cv.set(S.sx(h2 + 1) + ddx, S.sy(-3, 0) - 23, IRON[2])
        cv.set(S.sx(h2 + 1) + ddx, S.sy(-3, 0) - 24, IRON[2])
    return done(S, cv, "house", fp(-h2, h2, d), 0, door_w=dw)


def windmill(spec):
    """A smock windmill: an eight-sided clapboard tower narrowing on a stone base, a gallery
    round its middle, a domed cap, and sails (a separate sprite, 12 frames of a quarter turn)."""
    rnd = random.Random(spec.get("seed", 1))
    cy = 20
    S = Scene(pad=8, pad_top=8)
    S.add(prism(0, cy, 23, 0, 10, M.fieldstone(FIELDSTONE, seed=4), sides=8, ))
    clap = M.planks(CREAM, h=4, seed=6, bias=0.15)
    S.add(frustum(0, cy, 20, 12, 10, 66, clap, sides=8))
    S.add(prism(0, cy, 19, 40, 42, M.wood(DARKWOOD, bias=0.1), sides=16))  # gallery
    cap = M.shingles(ROOFS[spec.get("roof_colour", "bark")], seed=9, row_h=3)
    for z0, z1, r0, r1 in ((66, 71, 15, 14), (71, 76, 14, 11), (76, 79, 11, 7), (79, 81, 7, 2)):
        S.add(frustum(0, cy, r0, r1, z0, z1, cap, sides=12))
    cv = S.render()
    front = cy - 20
    cv.on_wall(front + 1, tol=3.0)
    door(cv, rnd, S.sx(0), S.sy(front, 10), w=12, h=17, style="arched", wood=DARKWOOD, step=False)
    cv.on_wall(cy - 16, tol=3.0)
    window(cv, rnd, S.sx(-4), S.sy(cy - 16, 36), w=7, h=7)
    window(cv, rnd, S.sx(4), S.sy(cy - 13, 58), w=6, h=6)
    cv.at_depth(cy - 19.5)
    gy = S.sy(cy - 19, 42)
    for x in range(S.sx(-18), S.sx(19)):  # gallery rail
        cv.set(x, gy - 6, DARKWOOD[5])
        if x % 4 == 0:
            for y in range(gy - 5, gy):
                cv.set(x, y, DARKWOOD[4])
    cv.free()
    hub = S.s(0, cy - 15, 71)
    for y in range(hub[1] - 2, hub[1] + 3):
        for x in range(hub[0] - 2, hub[0] + 3):
            if (x - hub[0]) ** 2 + (y - hub[1]) ** 2 <= 5:
                cv.set(x, y, IRON[2] if x + y < sum(hub) else IRON[1])
    sack(cv, S.sx(18), S.sy(-6, 0))
    sack(cv, S.sx(23), S.sy(-4, 0))
    sail_len = 40
    Sz = sail_len * 2 + 5
    sheet = Image.new("RGBA", (Sz * SAIL_FRAMES, Sz), (0, 0, 0, 0))
    for f in range(SAIL_FRAMES):
        sheet.alpha_composite(_sails(sail_len, Sz, f * (math.pi / 2) / SAIL_FRAMES), (f * Sz, 0))
    im, night, info = done(S, cv, "house", fp(-22, 22, 2 * 20), 0, door_w=12)
    info["sails"] = [hub[0] - S.ox, hub[1] - S.base]
    info["sails_frames"] = SAIL_FRAMES
    return im, night, info, {"sails": sheet}


# ================================================================ shops and workshops

def shop(spec):
    """A shop: painted boards (or plaster and timber), a display window under a striped awning
    that juts out over the street, a glazed door with a signboard over it, goods out in front."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d, wall_h = spec.get("width", 82), 46, 36
    h2 = ww / 2
    paint = spec.get("paint", "sage")
    S = Scene()
    footing(S, -h2, h2, 0, d)
    if paint == "cream":
        wall = M.plaster(PLASTER, frame=([-h2, -1.5, h2 - 3], [4, wall_h - 3]))
    else:
        wall = M.boards(PAINT[paint], seed=spec.get("seed", 1))
    S.add(box(-h2, h2, 0, d, 4, wall_h, wall))
    corner_posts(S, -h2, h2, 0, d, 4, wall_h)
    roof = M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=spec.get("seed", 1), moss=0.03)
    chims = []
    if spec.get("gable"):
        zr_w, zr = gable_front(S, -h2, h2, 0, d, wall_h, 0.62, roof, M.plaster(PLASTER, frame=([-1.5], [])), over=5)
        top_z = zr
    else:
        top_z = hip_roof(S, -h2 - 5, h2 + 5, -5, d + 5, wall_h, 0.56, spec.get("hip", 14), roof)
    door_left = spec.get("door_at", 0.72) > 0.5
    chims.append(chimney(S, -h2 + ww * (0.2 if door_left else 0.8), d * 0.6, wall_h, top_z + 8))
    dcx = -h2 + ww * spec.get("door_at", 0.72)
    sx0, sx1 = (-h2 + 7, dcx - 12) if door_left else (dcx + 12, h2 - 7)
    S.add(slab(sx0 - 3, sx1 + 3, -10, 0, wall_h - 10, wall_h - 4, 1.5,
               M.stripes(*_awning(spec.get("awning", "red")), w=4), no_shadow=False))
    step(S, dcx, w=16)
    # goods out in front: a crate on the left, a barrel on the right
    S.add(box(sx0, sx0 + 12, -12, -4, 0, 7, M.planks(WOOD, h=3, seed=4)))
    if spec.get("barrel", True):
        S.add(prism(sx1 - 5, -7, 4, 0, 10, M.barrel(seed=2), sides=12))
    cv = S.render()
    cv.on_wall(0)
    shop_window(cv, rnd, S.sx(sx0), S.sx(sx1), S.sy(0, 27), S.sy(0, 10), spec["goods"])
    door(cv, rnd, S.sx(dcx), S.sy(0, 4), style="glazed", step=False)
    board_sign(cv, S.sx(dcx - 11), S.sx(dcx + 11), S.sy(0, wall_h - 2), spec["sign"])
    lantern(cv, S.sx(dcx + 10), S.sy(0, 25))
    # awning valance: points hanging from its front edge
    cv.at_depth(-10.5)
    col, white = _awning(spec.get("awning", "red"))
    vy = S.sy(-10, wall_h - 10)
    for x in range(S.sx(sx0 - 3), S.sx(sx1 + 3)):
        k = (x - S.sx(sx0 - 3)) % 4
        r = col if ((x - S.sx(sx0 - 3)) // 4) % 2 == 0 else white
        for i in range(3 if k in (1, 2) else 2):
            cv.set(x, vy + i, r[2] if i < 2 else r[1])
    # goods on the crate top
    g = spec["goods"][0]
    if not g.startswith("potion") and g != "bread":
        cv.at_depth(-9)
        for gx in range(S.sx(sx0 + 1), S.sx(sx0 + 11), 2):
            item(cv, gx, S.sy(-8, 7) + 1, g)
    elif g == "bread":
        cv.at_depth(-9)
        for gx in range(S.sx(sx0 + 1), S.sx(sx0 + 10), 3):
            item(cv, gx, S.sy(-8, 7) + 1, g)
    if spec.get("sack"):
        cv.at_depth(-12)
        sack(cv, S.sx(sx0 + 13), S.sy(-11, 0))
    return done(S, cv, "shop", fp(-h2, h2, d), dcx, chims=chims)


def _awning(colour):
    from buildings import CANVAS
    a, b = CANVAS[colour]
    pad = lambda r: [r[0], r[0], r[1], r[2], r[3], r[3]]
    return pad(a), pad(b)


def smithy(spec):
    """A smithy: a stone house with a hipped roof and, beside it, an open forge shed under a
    lean-to: the hearth with glowing coals under a copper hood, a tall chimney, an anvil on a
    stump, a quench barrel, tools hung on the back wall."""
    rnd = random.Random(spec.get("seed", 1))
    d = 40
    hx0, hx1 = -54, -8
    sx0, sx1 = -8, 46
    roof = ROOFS[spec.get("roof_colour", "slate")]
    S = Scene()
    footing(S, hx0, hx1, 0, d)
    S.add(box(hx0, hx1, 0, d, 4, 30, M.dressed_stone(STONE, seed=3)))
    zr = hip_roof(S, hx0 - 4, hx1 + 4, -4, d + 4, 30, 0.6, 12, M.shingles(roof, seed=3, moss=0.04))
    # the shed: back wall, lean-to roof on posts, the forge near the open front
    S.add(box(sx0, sx1, d - 6, d, 0, 34, M.dressed_stone(STONE, seed=5, bias=-0.05)))
    S.add(slab(sx0 - 1, sx1 + 3, -4, d + 2, 31, 36, 2, M.shingles(roof, seed=7)))
    for px in (sx0 + 1, sx1 - 3):
        S.add(box(px, px + 3, -2, 1, 0, 31, M.wood(TRIM, bias=0.0)))
    hearth = S.add(box(12, 32, 3, 14, 0, 11, M.dressed_stone(STONE, seed=8)))
    S.add(frustum(22, 8.5, 9, 4, 17, 31, M.flat(COPPER), sides=4, rot=math.pi / 4))
    ch = chimney(S, 22, 8.5, 31, zr + 14, w=10)
    S.add(prism(2, -6, 3, 0, 6, M.wood(WOOD, bias=0.05), sides=10))  # stump
    S.add(box(-3, 8, -7.5, -4.5, 6, 9, M.flat(STEEL)))  # anvil
    S.add(prism(40, -5, 4, 0, 9, M.barrel(seed=2), sides=12))  # quench barrel
    cv = S.render()
    hi = S.solids.index(hearth)
    for (x, y) in zip(*_pixels_where(S, hi, top=True)):  # glowing coals on top of the hearth
        if 1 < x - S.sx(12) < 19:
            c = EMBER[3] if (x + y) % 3 else EMBER[4]
            cv.px[x, y] = C(c)
            cv.lit(x, y, LIT[4] if c == EMBER[4] else LIT[3])
    cv.on_wall(d - 6)
    for x in range(S.sx(sx0 + 4), S.sx(sx0 + 18), 4):  # tools on the back wall
        for y in range(S.sy(d - 6, 22), S.sy(d - 6, 12)):
            cv.set(x, y, IRON[2] if x % 8 else WOOD[3])
    for k in range(3):
        hx = S.sx(sx0 + 4 + k * 5)
        for dx, dy in ((0, 0), (0, 1), (1, 2), (2, 2), (3, 1), (3, 0)):
            cv.set(hx + dx, S.sy(d - 6, 9) + dy, IRON[2])
    cv.on_wall(0)
    dcx = hx0 + 30
    door(cv, rnd, S.sx(dcx), S.sy(0, 4), style="plank", wood=DARKWOOD, step=False)
    window(cv, rnd, S.sx(hx0 + 11), S.sy(0, 24), w=12, h=11)
    cv.free()
    hanging_sign(cv, S.sx(sx0 + 2), S.sy(-1, 27), "hammer", 1)
    return done(S, cv, "house", fp(hx0, sx1, d), dcx, chims=[ch])


def _pixels_where(S, si, top=False):
    import numpy as np
    m = S.sid == si
    if top:
        m &= S.pid == 5  # a box's top plane
    ys, xs = np.nonzero(m)
    return xs, ys


def inn(spec):
    """The inn: two storeys of planks under a long hipped roof, a porch along the front on posts
    with a deck and a signboard on its roof, double doors, lanterns, barrels."""
    rnd = random.Random(spec.get("seed", 1))
    ww, d = 100, 54
    h2 = ww / 2
    roof = ROOFS[spec.get("roof_colour", "rust")]
    S = Scene()
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, 54, M.planks(DARKWOOD if spec.get("dark") else WOOD, seed=9)))
    corner_posts(S, -h2, h2, 0, d, 4, 54)
    zr = hip_roof(S, -h2 - 5, h2 + 5, -5, d + 5, 54, 0.56, 22, M.shingles(roof, seed=11, moss=0.04))
    chims = [chimney(S, -h2 + 20, d * 0.55, 54, zr + 8), chimney(S, h2 - 20, d * 0.55, 54, zr + 8)]
    S.add(box(-h2 - 2, h2 + 2, -13, 0, 0, 3, M.planks(WOOD, h=4, seed=3)))  # deck
    for px in (-h2, -17, 14, h2 - 3):
        S.add(box(px, px + 3, -12, -9, 3, 27, M.wood(TRIM, bias=0.0)))
    S.add(slab(-h2 - 3, h2 + 3, -14, 0, 27, 32, 2, M.shingles(roof, seed=12)))
    S.add(prism(-h2 + 6, -18, 4.5, 0, 10, M.barrel(seed=2), sides=12))
    S.add(prism(-h2 + 15, -17, 4, 0, 9, M.barrel(seed=3), sides=12))
    cv = S.render()
    cv.on_wall(0)
    for wf in (0.17, 0.39, 0.61, 0.83):
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(0, 47), w=10, h=10, shutters=spec.get("shutters", "green"),
               box=wf in (0.39, 0.61))
    door(cv, rnd, S.sx(0), S.sy(0, 3), w=18, h=22, style="double", wood=DARKWOOD, step=False)
    for wf in (0.2, 0.8):
        window(cv, rnd, S.sx(-h2 + ww * wf), S.sy(0, 22), w=14, h=12)
    lantern(cv, S.sx(-15), S.sy(0, 22))
    lantern(cv, S.sx(13), S.sy(0, 22))
    cv.at_depth(-14.5)
    board_sign(cv, S.sx(-15), S.sx(15), S.sy(-14, 27) - 4, spec.get("sign", "mug"))
    return done(S, cv, "house", fp(-h2, h2, d), 0, door_w=18, chims=chims)


DESIGNS = {"cabin": cabin, "cottage": cottage, "townhouse": townhouse, "manor": manor, "tower": tower,
           "barn": barn, "windmill": windmill, "shop": shop, "smithy": smithy, "inn": inn}
