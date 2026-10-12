"""Market stalls and street props modelled in 3D for the oblique renderer (see town3d.py): the
counters, canopies, tables, tents and the wagon have real tops and depth; the goods, weapons,
lettering and other small things are the 2D parts from buildings.py and market.py, set on those
tops at the right depth."""
import math
import random

import materials as M
from buildings import CANVAS, DARKWOOD, IRON, ROOFS, WOOD, _result, item, lantern, sack
from market import CLOTH, GOLD, STEEL, WHITE, armour_stand, basket, blade, candle, crystal_ball, heap, jug, pennant, rope, shield
from oblique import K, Scene, box, gable_x, prism, prism_x, pyramid, slab


def _pad(r):
    return [r[0], r[0], r[1], r[2], r[3], r[3]]


def _canvas_ramps(colour):
    a, b = CANVAS[colour]
    return _pad(a), _pad(b)


def _cloth(name):
    r = CLOTH[name]
    return [r[0], r[0], r[1], r[2], r[3], r[4], r[4]]


WHITE6 = [WHITE[0], WHITE[0], WHITE[1], WHITE[2], WHITE[3], WHITE[4], WHITE[4]]


def post(S, x, y, z1, w=2, z0=0):
    S.add(box(x, x + w, y, y + w, z0, z1, M.wood(DARKWOOD, bias=0.15)))


def done(S, cv, kind, footprint):
    S.finish(cv)
    return _result(cv, kind, (S.ox, S.base), footprint)


def fp(x0, x1, d):
    fd = max(2, round(K * d))
    return [round(x0), -fd, round(x1 - x0), fd]


def valance(cv, S, x0, x1, y, z, ramp_a, ramp_b, w=4, depth=None):
    """Points of cloth hanging from the front edge of a canopy at (y, z)."""
    cv.at_depth(y - 0.5 if depth is None else depth)
    sy = S.sy(y, z)
    for x in range(S.sx(x0), S.sx(x1)):
        k = (x - S.sx(x0)) % w
        r = ramp_a if ((x - S.sx(x0)) // w) % 2 == 0 else ramp_b
        n = 3 if 0 < k < w - 1 else 2
        for i in range(n):
            cv.set(x, sy + i, r[3] if i == 0 else r[2] if i < n - 1 else r[1])


# ================================================================ stalls

def stall(spec):
    """A small stall: a plank counter loaded with trays of goods, a striped canopy on four
    posts, an open back with goods hung on a rail, a crate in front."""
    rnd = random.Random(spec.get("seed", 1))
    a, b = _canvas_ramps(spec.get("canopy", "red"))
    S = Scene()
    S.add(box(-20, 20, 0, 9, 0, 10, M.boards(WOOD, w=4, seed=2)))
    S.add(box(-20, 20, 0, 9, 10, 11, M.planks(WOOD, h=3, seed=3, bias=0.15)))
    for x, y in ((-21, -1), (19, -1), (-21, 13), (19, 13)):
        post(S, x, y, 31 if y < 0 else 34)
    S.add(slab(-23, 23, -5, 15, 30, 34, 1.5, M.stripes(a, b, w=4)))
    S.add(box(-17, -17 + 10, -10, -3, 0, 6, M.crate(WOOD)))
    cv = S.render()
    goods = spec["goods"]
    for row, yy in enumerate((6.5, 2.5)):  # trays of goods on the counter
        cv.at_depth(yy)
        x = -17 + row
        k = row
        while x < 16:
            g = goods[k % len(goods)]
            sx, sy = S.s(x, yy, 11)
            for i in range(-1, 6):
                cv.set(sx + i, sy, "#7a5a32")
            for gx in range(sx, sx + 5, 2):
                item(cv, gx, sy, g)
            x += 8
            k += 1
    if spec.get("hang"):
        cv.at_depth(13.5)
        for x in range(-16, 17, 6):
            sx, sy = S.s(x, 13.5, 27)
            cv.set(sx, sy, "#cdb487")
            cv.set(sx, sy + 1, "#cdb487")
            item(cv, sx, sy + 5 + (x // 6) % 2, spec["hang"])
    cv.at_depth(-10.5)
    for gx in range(S.sx(-16), S.sx(-8), 2):
        item(cv, gx, S.sy(-6, 6), goods[-1] if not goods[-1].startswith("potion") else "apple")
    valance(cv, S, -23, 23, -5, 30, a, b)
    return done(S, cv, "stall", fp(-20, 20, 9))


def sail_stall(spec):
    """Cloth sagging between four tall poles with pennants, guy ropes out to pegs; under it a
    table and a rack of arms with armour stands, or lengths of cloth, or shelves of pottery."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = _cloth(spec.get("cloth", "blue"))
    S = Scene(pad=10)
    fx, bx_, by = 30, 24, 17
    for x in (-bx_, bx_ - 2):
        post(S, x, by, 38)
    for x in (-fx, fx - 2):
        post(S, x, -1, 32)
    n = 10
    for i in range(n):  # the sagging sheet, in strips
        x0 = -fx + 2 * fx * i / n
        x1 = -fx + 2 * fx * (i + 1) / n
        u = (i + 0.5) / n
        sag = 1 - (2 * u - 1) ** 2
        S.add(slab(x0, x1 + 0.01, -1, by + 1, 33 - 7 * sag, 38 - 2 * sag, 1.2, M.swirl(ramp, WHITE6)))
    goods = spec.get("goods", "weapons")
    if goods == "weapons":
        S.add(box(-15, 15, 1, 7, 0, 9, M.cloth(_cloth("red"))))
        for x in (-18, 16):
            post(S, x, 12, 15)
        S.add(box(-18, 18, 12, 13, 12, 13.5, M.wood(DARKWOOD, bias=0.2)))
        S.add(box(-18, 18, 12, 13, 4, 5.5, M.wood(DARKWOOD, bias=0.2)))
    elif goods == "cloth":
        S.add(box(-20, 20, 12, 13, 24, 25.5, M.wood(DARKWOOD, bias=0.2)))
        S.add(box(-17, 17, 1, 7, 0, 9, M.cloth(_cloth("green"))))
    else:
        for z in (8, 17):
            S.add(box(-20, 20, 9, 14, z, z + 1.5, M.wood(DARKWOOD, bias=0.15)))
        for x in (-20, 18):
            post(S, x, 12, 19)
    cv = S.render()
    if goods == "weapons":
        cv.at_depth(12.4)
        kinds = ["sword", "spear", "axe", "sword", "spear", "sword", "axe", "spear"]
        x = -15
        k = rnd.randint(0, 3)
        while x < 16:
            kind = kinds[k % len(kinds)]
            sx, sy = S.s(x, 12.5, 0)
            blade(cv, sx, sy - (21 if kind == "spear" else 16 if kind == "sword" else 15), sy - 1, kind)
            x += 4 if kind != "axe" else 6
            k += 1
        cv.at_depth(4)
        tx, ty = S.s(-4, 4, 9)
        for i in range(12):
            cv.set(tx + i, ty, STEEL[3] if i < 8 else "#6b3c17")
        cv.set(tx + 8, ty - 1, GOLD[3])
        cv.set(tx + 8, ty + 1, GOLD[2])
        shield(cv, S.sx(9), S.sy(4, 9) - 4, CLOTH["blue"])
        for x, plume in ((-25, CLOTH["red"]), (24, CLOTH["blue"])):
            cv.at_depth(4)
            armour_stand(cv, S.sx(x), S.sy(4, 0), plume=plume)
    elif goods == "cloth":
        cv.at_depth(12.4)
        for i, c in enumerate(("red", "ochre", "teal", "purple", "green")):
            r = CLOTH[c]
            sx0, sy0 = S.s(-17 + i * 7, 12.5, 24)
            length = 13 + (i * 5) % 7
            for y in range(sy0, sy0 + length):
                for kx in range(5):
                    fold = (kx + (y // 3)) % 5
                    cv.set(sx0 + kx, y, r[4] if kx == 0 else r[3] if fold < 2 else r[2] if kx < 4 else r[1])
        cv.at_depth(4)
        x = -14
        for c in ("blue", "red", "ochre", "teal", "purple", "red"):
            r = CLOTH[c]
            sx, sy = S.s(x, 4, 9)
            for j in range(4):
                for i in range(4):
                    if (i, j) in ((0, 0), (3, 0), (0, 3), (3, 3)):
                        continue
                    cv.set(sx + i, sy - 4 + j, r[3] if i + j < 3 else r[2] if (i, j) != (1, 1) else r[0])
            x += 5
        cv.at_depth(-4)
        sack(cv, S.sx(-27), S.sy(-3, 0))
    else:
        ramps = [("#5b3a22", "#8f5a33", "#c0814d"), ("#1e4a4a", "#2f7472", "#5aa6a0"), ("#5a2a20", "#9a4a36", "#cf7a5c")]
        for z in (9.5, 18.5):
            cv.at_depth(10)
            x = -18
            while x < 17:
                jug(cv, S.sx(x), S.sy(10, z), ramps[rnd.randrange(3)])
                x += 6
        for k in range(3):
            cv.at_depth(-2 - k)
            jug(cv, S.sx(-26 + k * 6), S.sy(-2 - k, 0), ramps[k % 2])
    cv.free()
    for x in (-bx_, bx_ - 2, -fx, fx - 2):
        y = by if abs(x) < 28 else -1
        top = 38 if y == by else 32
        px, py = S.s(x, y, top)
        pennant(cv, px, py, CLOTH["red"], right=x > 0)
    for x in range(S.sx(-fx), S.sx(fx)):  # a toothed hem along the front edge
        u = (x - S.sx(-fx)) / (2 * fx)
        sag = 1 - (2 * u - 1) ** 2
        y0 = S.sy(-1, 33 - 7 * sag - 1.2)
        k = (x - S.sx(-fx)) % 6
        for i in range(3 - abs(k - 3) // 2):
            cv.set(x, y0 + i, ramp[3] if ((x - S.sx(-fx)) // 6) % 2 == 0 else WHITE6[3])
    S.finish(cv)
    rope(cv, S.sx(-fx) - 1, S.sy(-1, 31), S.sx(-fx) - 9, S.sy(-1, 0), 1.0)
    rope(cv, S.sx(fx) + 1, S.sy(-1, 31), S.sx(fx) + 9, S.sy(-1, 0), 1.0)
    return _result(cv, "stall", (S.ox, S.base), fp(-fx, fx, 12))


def sign_stall(spec):
    """A produce stand: a long counter of bins heaped with fruit and vegetables, a big painted
    signboard up on two forked poles, crates of melons and pumpkins, a basket and a barrel."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=8)
    S.add(box(-32, 32, 0, 12, 0, 11, M.boards(DARKWOOD, w=5, seed=3)))
    S.add(box(-32, 32, 0, 12, 11, 12, M.wood(DARKWOOD, bias=0.25)))
    for x in (-34, 32):
        post(S, x, 12, 46, w=2)
    S.add(box(-37, 37, 12, 14, 34, 45, M.planks(["#4a3520", "#7a5a32", "#a8854f", "#c4a066", "#d8b77a", "#e9cf94"], h=5, seed=4)))
    S.add(box(-30, -18, -12, -3, 0, 7, M.crate(WOOD)))
    S.add(box(-16, -4, -12, -3, 0, 7, M.crate(WOOD)))
    S.add(prism(27, -7, 4, 0, 9, M.barrel(seed=2), sides=12))
    cv = S.render()
    kinds = spec.get("goods", ["apples", "grapes", "cabbage", "oranges", "carrots"])
    bw = 60 / len(kinds)
    for row, yy in enumerate((9, 5)):  # heaps in the bins, back row first
        cv.at_depth(yy)
        for i, kind in enumerate(kinds):
            x0 = -30 + i * bw
            heap(cv, rnd, S.sx(x0 + 1), S.sx(x0 + bw - 1), S.sy(yy, 12), kind, rows=2 if row == 0 else 1)
    cv.on_wall(12)
    ly = S.sy(12, 41)
    for x in range(S.sx(-28), S.sx(28)):  # painted lettering on the board
        if (x // 3) % 4 != 3 and (x * 7) % 5 != 0:
            cv.set(x, ly, "#5a2f1a")
            if x % 3 == 0:
                cv.set(x, ly + 1, "#5a2f1a")
    for x, z in ((-36, 43), (36, 43), (-36, 36), (36, 36)):
        cv.set(S.sx(x), S.sy(12, z), IRON[1])
    cv.free()
    for x in (-34, 32):  # forks at the pole tops
        px, py = S.s(x, 12, 46)
        for i in range(4):
            cv.set(px - i, py - i, DARKWOOD[4])
            cv.set(px + 1 + i, py - i, DARKWOOD[3])
    front = spec.get("front", ["melon", "pumpkin"])
    for x0, g in ((-29, front[0]), (-15, front[1])):
        cv.at_depth(-8)
        heap(cv, rnd, S.sx(x0), S.sx(x0 + 10), S.sy(-8, 7) + 1, g, rows=1)
    cv.at_depth(-9)
    basket(cv, rnd, S.sx(8), S.sy(-9, 0), 9, kinds[0])
    return done(S, cv, "stall", fp(-32, 32, 12))


def table_stall(spec):
    """Bakes on a long table under a cloth, a striped awning on four posts, baskets and a sack,
    a chalkboard on an easel."""
    rnd = random.Random(spec.get("seed", 1))
    a, b = _canvas_ramps(spec.get("awning", "red"))
    S = Scene()
    S.add(box(-26, 26, 0, 14, 0, 10, M.cloth(WHITE6)))
    for x, y in ((-28, -3), (26, -3), (-28, 17), (26, 17)):
        post(S, x, y, 29 if y < 0 else 32)
    S.add(slab(-30, 30, -6, 19, 28, 32, 1.5, M.stripes(a, b, w=4)))
    cv = S.render()
    goods = spec.get("goods", ["bread", "pie", "bun", "cake"])
    for row, yy in enumerate((10, 4)):
        cv.at_depth(yy)
        x = -22 + row * 3
        k = row
        while x < 21:
            g = goods[k % len(goods)]
            sx, sy = S.s(x, yy, 10)
            for i in range(-1, 5):
                cv.set(sx + i, sy, "#b98a52" if g == "bread" else WHITE[1])
            if g == "pie":
                for i in range(5):
                    cv.set(sx + i - 1, sy - 1, "#c9862e")
                    cv.set(sx + i - 1, sy - 2, "#e8b25e" if i < 3 else "#c9862e")
                cv.set(sx + 1, sy - 2, "#8a3a2a")
            elif g == "bun":
                for bxx in (0, 3):
                    cv.set(sx + bxx, sy - 1, "#c98a42")
                    cv.set(sx + bxx + 1, sy - 1, "#a86c30")
                    cv.set(sx + bxx, sy - 2, "#efc27a")
                    cv.set(sx + bxx + 1, sy - 2, "#c98a42")
            elif g == "cake":
                for j in range(4):
                    for i in range(5):
                        cv.set(sx + i - 1, sy - 1 - j, "#fbeee0" if j == 3 else "#f2a7b5" if j == 1 else "#e8d0b0")
                cv.set(sx + 1, sy - 5, "#d8333a")
            else:
                item(cv, sx, sy, "bread")
                item(cv, sx + 1, sy - 2, "bread")
            x += 8
            k += 1
    valance(cv, S, -30, 30, -6, 28, a, b)
    cv.at_depth(-6)
    basket(cv, rnd, S.sx(-27), S.sy(-6, 0), 8, spec.get("basket", "apples"))
    sack(cv, S.sx(-17), S.sy(-5, 0))
    bx, by = S.sx(18), S.sy(-6, 0)  # chalkboard on an easel
    for y in range(by - 10, by):
        for x in range(bx, bx + 8):
            edge = x in (bx, bx + 7) or y in (by - 10, by - 1)
            cv.set(x, y, WOOD[4] if edge else "#2f3a36")
    for x in range(bx + 2, bx + 6):
        cv.set(x, by - 7, WHITE[3])
        if x % 2:
            cv.set(x, by - 4, WHITE[2])
    return done(S, cv, "stall", fp(-26, 26, 14))


def pavilion(spec):
    """A fortune teller's tent: a drum of striped curtains under a striped cone with a gold finial,
    a moon and star on the front, the flaps tied back on a dim inside with a crystal ball and
    candles on a draped table, a rug in front and guy ropes."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = _cloth(spec.get("cloth", "purple"))
    r, cy = 24, 24
    S = Scene(pad=10, pad_top=12)
    S.add(prism(0, cy, r, 0, 28, M.stripes(ramp, WHITE6, w=6), sides=20))
    S.add(pyramid(0, cy, r + 4, 27, 62, M.stripes(ramp, WHITE6, w=6), sides=20))
    S.add(box(-12, 12, -14, -2, 0, 0.6, M.rug(_cloth("red"))))
    cv = S.render()
    front = cy - r
    cv.on_wall(front, tol=3.5)
    ey = S.sy(front, 0)
    for y in range(ey - 24, ey):  # the dim doorway between the tied-back flaps
        hw = round(3 + 9 * (y - (ey - 24)) / 24)
        for x in range(S.sx(-hw), S.sx(hw)):
            cv.set(x, y, "#2a1f33" if y < ey - 9 else "#3a2b40")
    for side in (-1, 1):
        for i in range(3):
            cv.set(S.sx(side * 11) + side * i, ey - 12 + i, GOLD[3])
    cv.free()
    cv.at_depth(front - 0.5)
    tb = ey - 2
    for y in range(tb - 7, tb):
        for x in range(S.sx(-9), S.sx(9)):
            cv.set(x, y, ramp[4] if y == tb - 7 else ramp[3] if (x % 4) else ramp[2])
    crystal_ball(cv, S.sx(0), tb - 7)
    candle(cv, S.sx(-6), tb - 7)
    candle(cv, S.sx(6), tb - 7, 4)
    item(cv, S.sx(-4), tb - 7, "potion_r")
    item(cv, S.sx(3), tb - 7, "potion_g")
    cv.free()
    # scalloped valance at the eave across the front, the emblem, the finial and pennant
    for x in range(S.sx(-r - 3), S.sx(r + 4)):
        xx = x - S.ox
        if abs(xx) > r + 3:
            continue
        yy = cy - math.sqrt(max(0.0, (r + 3) ** 2 - xx * xx))
        sy = S.sy(yy, 27)
        k = (x + 100) % 6
        rr = ramp if ((x + 100) // 6) % 2 == 0 else WHITE6
        cv.set(x, sy, GOLD[3] if xx < 0 else GOLD[2])
        for i in range(4 - abs(k - 3)):
            cv.set(x, sy + 1 + i, rr[3] if i == 0 else rr[2])
    mx, my = S.s(0, cy - 13, 44)
    for y in range(my - 4, my + 5):
        for x in range(mx - 4, mx + 5):
            d1 = (x - mx) ** 2 + (y - my) ** 2
            d2 = (x - mx - 2) ** 2 + (y - my + 1) ** 2
            if d1 <= 16 and d2 > 9:
                cv.set(x, y, GOLD[4] if x < mx - 1 else GOLD[3])
    for dx, dy in ((5, -4), (4, -4), (6, -4), (5, -5), (5, -3)):
        cv.set(mx + dx, my + dy, GOLD[4])
    ax, ay = S.s(0, cy, 62)
    for y in range(ay - 6, ay):
        cv.set(ax, y, GOLD[3])
    cv.set(ax, ay - 7, GOLD[4])
    pennant(cv, ax, ay - 5, CLOTH["ochre"], right=True)
    S.finish(cv)
    rope(cv, S.sx(-r - 2), S.sy(cy - 6, 26), S.sx(-r - 9), S.sy(-4, 0), 1.5)
    rope(cv, S.sx(r + 2), S.sy(cy - 6, 26), S.sx(r + 9), S.sy(-4, 0), 1.5)
    _ = rnd
    return _result(cv, "stall", (S.ox, S.base), fp(-r, r, 2 * r))


def wagon(spec):
    """A merchant's wagon side on: a plank bed on big spoked wheels, an arched canvas cover over
    ribs, a side flap let down as a shelf of wares, shafts out in front, a lantern, a barrel."""
    rnd = random.Random(spec.get("seed", 1))
    ramp = _cloth(spec.get("cloth", "green"))
    S = Scene(pad=8)
    S.add(box(-30, 30, 0, 20, 11, 22, M.planks(WOOD, h=4, seed=5)))
    S.add(prism_x(-28, 28, 11, 22, 12, M.canvas(ramp, rib=10), sides=18))
    S.add(box(-28, 28, -5, 0, 12, 13.5, M.wood(WOOD, bias=0.2)))  # the flap, let down as a shelf
    S.add(box(-46, -30, 3, 5, 13, 14.5, M.wood(WOOD, bias=0.15)))
    S.add(box(-46, -30, 15, 17, 13, 14.5, M.wood(WOOD, bias=0.15)))
    if spec.get("barrel"):
        S.add(prism(34, 10, 4, 11, 20, M.barrel(seed=2), sides=12))
    cv = S.render()
    kinds = spec.get("goods", ["potion_r", "potion_b", "potion_g"])
    for row, yy in enumerate((-1.5, -3.5)):  # wares on the shelf
        cv.at_depth(yy)
        x = -26 + row
        while x < 26:
            sx, sy = S.s(x, yy, 13.5)
            if (x // 3) % 3 == 2:
                jug(cv, sx, sy, (("#5b3a22", "#8f5a33", "#c0814d"), ("#1e4a4a", "#2f7472", "#5aa6a0"))[x % 2])
                x += 6
            else:
                item(cv, sx, sy, kinds[rnd.randrange(len(kinds))])
                x += 3
    cv.at_depth(20.5)
    for wx in (-18, 18):  # the far wheels peep out behind, the near ones stand in front
        cx, cyy = S.s(wx, 21, 10)
        _wheel(cv, cx, cyy, 10)
    cv.at_depth(-6)
    for wx in (-18, 18):
        cx, cyy = S.s(wx, -6, 10)
        _wheel(cv, cx, cyy, 10)
    cv.free()
    lantern(cv, S.sx(-32), S.sy(0, 28))
    return done(S, cv, "stall", fp(-30, 30, 20))


def _wheel(cv, cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x - cx, y - cy)
            if d > r + 0.4:
                continue
            if d > r - 1.6:
                cv.set(x, y, DARKWOOD[4] if (x - cx) + (y - cy) < 0 else DARKWOOD[2])
            elif d < 1.6:
                cv.set(x, y, IRON[2] if x <= cx else IRON[1])
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        for s in range(2, r - 1):
            cv.set(round(cx + math.cos(a) * s), round(cy + math.sin(a) * s), DARKWOOD[5] if k < 3 else DARKWOOD[3])


# ================================================================ props

def prop_weapon_rack(spec):
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=22)
    for x in (-13, 11):
        post(S, x, 0, 14)
    S.add(box(-13, 13, 0, 1, 11, 12.5, M.wood(DARKWOOD, bias=0.2)))
    S.add(box(-13, 13, 0, 1, 4, 5.5, M.wood(DARKWOOD, bias=0.2)))
    cv = S.render()
    cv.at_depth(1.5)
    kinds = ["sword", "spear", "axe", "sword", "spear"]
    x = -10
    k = rnd.randint(0, 4)
    while x < 9:
        kind = kinds[k % len(kinds)]
        sx, sy = S.s(x, 1.5, 0)
        blade(cv, sx, sy - (21 if kind == "spear" else 16 if kind == "sword" else 15), sy - 1, kind)
        x += 3 if kind != "axe" else 5
        k += 1
    cv.at_depth(-1)
    shield(cv, S.sx(12), S.sy(-1, 9), CLOTH[spec.get("cloth", "red")])
    return done(S, cv, "prop", fp(-13, 13, 3))


def prop_dining(spec):
    """A round table under a cloth with stools round it and a roast on it."""
    S = Scene()
    for x, y in ((-15, 6), (14, 6), (0, 18)):
        S.add(prism(x, y, 3, 0, 5, M.wood(WOOD, bias=0.15), sides=10))
    S.add(prism(0, 7, 10, 0, 10, M.cloth(WHITE6, fold=4), sides=18))
    S.add(prism(0, -9, 3, 0, 5, M.wood(WOOD, bias=0.15), sides=10))
    cv = S.render()
    cv.at_depth(6)
    sx, sy = S.s(-2, 6, 10)
    for i in range(7):
        cv.set(sx - 1 + i, sy, WHITE[1])
    for i, c in enumerate(("#a8522a", "#d27a3a", "#e89a52", "#d27a3a", "#a8522a")):
        cv.set(sx + i, sy - 1, c)
        cv.set(sx + i, sy - 2, c if i < 4 else "#a8522a")
    cv.set(sx + 1, sy - 3, "#f0c070")
    jug(cv, S.sx(5), S.sy(9, 10))
    return done(S, cv, "prop", fp(-10, 10, 14))


def prop_barrels(spec):
    S = Scene()
    S.add(prism(-5, 6, 4.5, 0, 10, M.barrel(seed=1), sides=12))
    S.add(prism(5, 6, 4.5, 0, 10, M.barrel(seed=2), sides=12))
    S.add(prism(0, 7, 4.5, 10, 20, M.barrel(seed=3), sides=12))
    cv = S.render()
    cv.at_depth(0)
    sack(cv, S.sx(10), S.sy(0, 0))
    return done(S, cv, "prop", fp(-10, 10, 10))


def prop_crates(spec):
    S = Scene()
    S.add(box(-13, -1, 0, 10, 0, 9, M.crate(WOOD)))
    S.add(box(0, 11, 2, 12, 0, 8, M.crate(WOOD)))
    S.add(box(-9, 1, 2, 11, 9, 17, M.crate(WOOD)))
    cv = S.render()
    cv.at_depth(-1)
    sack(cv, S.sx(11), S.sy(-1, 0))
    cv.at_depth(6)
    jug(cv, S.sx(3), S.sy(6, 8))
    return done(S, cv, "prop", fp(-13, 12, 12))


def prop_rug(spec):
    S = Scene(pad=2, pad_top=2, pad_bottom=2, outline="#3a1418")
    S.add(box(-13, 13, 0, 13, 0, 0.6, M.rug(_cloth(spec.get("cloth", "red")))))
    cv = S.render()
    return done(S, cv, "rug", fp(-13, 13, 13))


def prop_well(spec):
    """A stone well: a ring of fieldstones round dark water, a little shingle roof on two posts,
    a crank and a bucket on its rope."""
    S = Scene(pad_top=6)
    S.add(prism(0, 10, 12, 0, 9, M.well_stone(seed=2), sides=18))
    for x in (-13, 11):
        post(S, x, 9, 30, w=2)
    S.add(gable_x(-16, 16, 1, 19, 28, 30, 36, M.shingles(ROOFS["rust"], seed=5)))
    S.add(box(-12, 12, 9.5, 10.5, 21, 22, M.wood(DARKWOOD, bias=0.2)))
    cv = S.render()
    cv.at_depth(9)
    rx, ry = S.s(1, 9.5, 21)
    for y in range(ry, ry + 7):
        cv.set(rx, y, "#5c4632")
    for y in range(ry + 7, ry + 11):
        for x in range(rx - 2, rx + 3):
            cv.set(x, y, WOOD[4] if x < rx + 1 else WOOD[2])
    cv.set(rx - 2, ry + 7, IRON[2])
    cv.set(rx + 2, ry + 7, IRON[2])
    return done(S, cv, "prop", fp(-12, 12, 20))


DESIGNS = {
    "stall": stall, "sail_stall": sail_stall, "sign_stall": sign_stall, "table_stall": table_stall, "pavilion": pavilion,
    "wagon": wagon, "weapon_rack": prop_weapon_rack, "dining": prop_dining, "barrels": prop_barrels,
    "crates": prop_crates, "rug": prop_rug, "well": prop_well,
}
