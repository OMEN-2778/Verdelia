"""Things by the water, modelled in 3D for the oblique renderer (see town3d.py): a watermill whose
wheel turns (an animated part), a wooden dock running out into a lake, a rowboat, a lighthouse
with its keeper's hut, stone arch bridges both ways across a stream, and wooden footbridges.

Water itself belongs to the map (water_body.gd paints it flat into the terrain), so these sprites
never paint water of their own except where it is part of the thing (the flume's channel, the
dark water under an arch). Where a part stands in water it stops at the waterline and gets a
ring of ripples; a deck or a hull throws a soft, see-through shadow onto the water beside it
(a "shadow catcher": a sheet at the waterline that only keeps the pixels other solids shade).

Decks (dock, bridges, footbridges) are drawn with the walking surface where the player's feet go:
the deck's footprint is the walkable rectangle relative to the base point, the deck lies at
ground level (or a couple of px above it), and what is under it (posts, the arch face) hangs
below the base line over the water in front."""
import math
import random

import numpy as np
from PIL import Image

import materials as M
from buildings import (C, DARKWOOD, FIELDSTONE, GLASS, IRON, LIT, PLASTER, ROOFS, STONE, TRIM, WOOD, _result, door,
                       lantern, sack, tone, window)
from oblique import K, Mat, Scene, Solid, box, frustum, gable_x, hsh, prism, slab
from town3d import chimney, chims_screen, footing, gable_front, step

GROUP = "水边"

DOCKWOOD = ["#201a16", "#3a2f27", "#55463a", "#6e5c4b", "#87735d", "#a08b70", "#bba687"]
WATER = ["#14283c", "#1c3b58", "#285577", "#356f96", "#4f8db4", "#80b8d6", "#c9e9f5"]
FOAM = (226, 244, 250)
RIPPLE = (168, 214, 236)
ROPE = ["#4a3826", "#6e5639", "#94774f", "#b89a6c", "#d6bd8e"]
MOSS = ["#1f3322", "#2f4a2c", "#3f6236"]
WHITEWASH = ["#3e3a36", "#8f8a80", "#c8c2b5", "#e0dbcf", "#efebe1", "#f8f5ee", "#fffdf8"]
RED = ["#3a1214", "#621c1f", "#8c2a2a", "#ad3a35", "#c8534a", "#de7a6c", "#efa596"]
SHADOW = (14, 28, 48)


def _t(ramp, v):
    return ramp[tone(ramp, v)]


def _st(ramp, v, k):
    return ramp[max(1, min(len(ramp) - 1, tone(ramp, v) + k))]


# ================================================================ solids

def convex(poly, axis, a0, a1, mat, **kw):
    """A convex polygon extruded along an axis: axis "y" takes (x, z) points, "x" takes (y, z),
    "z" takes (x, y). Paddles, spokes, wedges, sloping parapet stones..."""
    i, j, k = {"x": (1, 2, 0), "y": (0, 2, 1), "z": (0, 1, 2)}[axis]
    n = len(poly)
    cu = sum(p[0] for p in poly) / n
    cw = sum(p[1] for p in poly) / n
    planes = []
    nk = [0.0, 0.0, 0.0]
    nk[k] = -1.0
    planes.append((tuple(nk), -a0))
    nk = [0.0, 0.0, 0.0]
    nk[k] = 1.0
    planes.append((tuple(nk), a1))
    for m in range(n):
        p, q = poly[m], poly[(m + 1) % n]
        eu, ew = q[0] - p[0], q[1] - p[1]
        nu, nw = ew, -eu
        if nu * (cu - p[0]) + nw * (cw - p[1]) > 0:
            nu, nw = -nu, -nw
        if abs(nu) + abs(nw) < 1e-9:
            continue
        v = [0.0, 0.0, 0.0]
        v[i], v[j] = nu, nw
        planes.append((tuple(v), nu * p[0] + nw * p[1]))
    lo = [0.0] * 3
    hi = [0.0] * 3
    lo[i], hi[i] = min(p[0] for p in poly), max(p[0] for p in poly)
    lo[j], hi[j] = min(p[1] for p in poly), max(p[1] for p in poly)
    lo[k], hi[k] = a0, a1
    return Solid(planes, mat, (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), **kw)


def rod(p0, p1, w, axis, a0, a1, mat, **kw):
    """A straight board of width w between two points in the plane across `axis` (see convex)."""
    du, dw = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(du, dw) or 1.0
    nu, nw = -dw / ln * w / 2, du / ln * w / 2
    poly = [(p0[0] + nu, p0[1] + nw), (p1[0] + nu, p1[1] + nw), (p1[0] - nu, p1[1] - nw), (p0[0] - nu, p0[1] - nw)]
    return convex(poly, axis, a0, a1, mat, **kw)


def ngon(cu, cw, r, n, rot=0.0):
    return [(cu + r * math.cos(rot + (m + 0.5) * 2 * math.pi / n), cw + r * math.sin(rot + (m + 0.5) * 2 * math.pi / n))
            for m in range(n)]


def hull(points, mat, **kw):
    """The convex hull of a few points (brute force over triples: fine for a dozen points)."""
    pts = [tuple(float(c) for c in p) for p in points]
    planes = []
    seen = set()
    n = len(pts)
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                pa, pb, pc = (np.array(pts[i]) for i in (a, b, c))
                nn = np.cross(pb - pa, pc - pa)
                ln = np.linalg.norm(nn)
                if ln < 1e-6:
                    continue
                nn = nn / ln
                d = float(nn @ pa)
                side = [float(nn @ np.array(p)) - d for p in pts]
                if all(v <= 1e-6 for v in side):
                    pl = (tuple(nn), d)
                elif all(v >= -1e-6 for v in side):
                    pl = (tuple(-nn), -d)
                else:
                    continue
                key = tuple(round(v, 4) for v in (*pl[0], pl[1]))
                if key not in seen:
                    seen.add(key)
                    planes.append(pl)
    xs, ys, zs = zip(*pts)
    return Solid(planes, mat, (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)), **kw)


CATCH = Mat(lambda u, v, kind, light, P, s: "#000000")


def catcher(S, x0, x1, y0, y1, z):
    """A sheet at the waterline that only keeps the shadows falling on it (see catch())."""
    return S.add(box(x0, x1, y0, y1, z - 0.5, z, CATCH, no_shadow=True, catcher=True))


def catch(S, cv):
    """Clear the shadow catchers' pixels; return the ones in shadow, to draw after the outline."""
    out = []
    for si, sol in enumerate(S.solids):
        if not sol.params.get("catcher"):
            continue
        ys, xs = np.nonzero(S.sid == si)
        for y, x in zip(ys, xs):
            if cv.shadow[y, x]:
                out.append((int(x), int(y)))
            cv.px[int(x), int(y)] = (0, 0, 0, 0)
    return out


def put_shadow(cv, pts, alpha=88):
    for x, y in pts:
        if cv.px[x, y][3] == 0:
            cv.px[x, y] = (*SHADOW, alpha)


def blend(cv, x, y, rgb, a):
    """Put a see-through pixel on an empty spot (ripples, spray, reflections)."""
    x, y = int(x), int(y)
    if cv.inb(x, y) and cv.px[x, y][3] == 0:
        cv.px[x, y] = (*rgb, a)


def ripple(cv, x0, x1, y, rnd=None, wide=2):
    """Rings round a post standing in water: a bright line either side and a dark streak under."""
    for x in range(x0 - wide, x1 + wide):
        if x0 - 1 <= x < x1 + 1:
            blend(cv, x, y + 1, SHADOW, 70)
            continue
        if (x - x0) % 3 != 2:
            blend(cv, x, y, RIPPLE, 210)
    for x in range(x0 - wide - 1, x1 + wide + 1):
        if x < x0 - wide or x >= x1 + wide:
            blend(cv, x, y + 1, RIPPLE, 120)
    blend(cv, x0 - wide - 2, y + 2, RIPPLE, 90)
    blend(cv, x1 + wide + 1, y + 2, RIPPLE, 90)


# ================================================================ materials

def deck_boards(ramp=DOCKWOOD, w=3.75, seed=1, run=23, along="x", nails=(), worn=0.12):
    """Deck planks. along="x": boards run across (left-right), one every w px going back (a dock
    or a bridge running back); along="y": boards run back, one every w px across (a bridge
    crossing left-right). Gaps between boards, staggered butt joints, nail heads over the
    stringers, a few weathered grey boards. On the front face: the fascia or the board ends."""
    def f(u, v, kind, light, P, s):
        if along == "x":
            a, c = P[0], P[1]
        else:
            a, c = P[1], P[0]
        row = math.floor(c / w)
        k = c - row * w
        if kind in ("wall", "side"):
            if along == "y":  # board ends
                if k < 0.9:
                    return ramp[1]
                return _t(ramp, light - 0.05 + (hsh(row, seed) - 0.5) * 0.2)
            zz = P[2] - s.bbox[4]
            if zz > s.bbox[5] - s.bbox[4] - 0.9:
                return _st(ramp, light + 0.1, 1)
            return _t(ramp, light - 0.1)
        off = hsh(row, seed) * run
        seg = math.floor((a + off) / run)
        aa = a + off - seg * run
        t0 = hsh(row, seg, seed + 3)
        lv = light + 0.08 + (t0 - 0.5) * 0.22
        grey = t0 < worn
        r = DRIFT if grey else ramp
        if k < w * 0.3 if along == "x" else k < 0.9:
            return ramp[1] if along == "x" else ramp[2]
        if aa < 1.0:
            return ramp[2]
        for nx in nails:
            if abs(a - nx) < 0.6 and w * 0.3 <= k < w * 0.66:
                return r[1]
        if k > w * 0.66:
            return _st(r, lv, 1)
        if hsh(math.floor(a / 2), row, seed + 7) < 0.1:
            return _st(r, lv, -1)
        return _t(r, lv)
    return Mat(f)


DRIFT = ["#26231f", "#423d36", "#5f5850", "#7a7268", "#948c80", "#ada598", "#c6bfb2"]


def post_wood(ramp=DOCKWOOD, wet=None, seed=1):
    """A round post or piling: grain down the sides, a lighter cut top, dark and mossy where it
    stays wet (below z = wet)."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _st(ramp, light + 0.1, 1) if (math.floor(P[0]) + math.floor(P[1])) % 3 else _t(ramp, light + 0.1)
        if wet is not None and P[2] < wet:
            return MOSS[1] if P[2] < wet - 1.5 else MOSS[2] if hsh(math.floor(u), seed) < 0.5 else ramp[2]
        g = -0.12 if hsh(math.floor(u * 1.5), math.floor(P[2] / 3), seed) < 0.15 else 0.0
        return _t(ramp, light + 0.12 + g)
    return Mat(f)


def flat_m(ramp, bias=0.0):
    return Mat(lambda u, v, kind, light, P, s: _t(ramp, light + bias))


def water_top(ramp=WATER, seed=1):
    """Running water seen from above (the flume's channel): ripples streaming along x."""
    def f(u, v, kind, light, P, s):
        if kind != "top":
            return ramp[2]
        k = (math.floor(P[0] * 0.5) + math.floor(P[1] * 1.3) * 3) % 7
        if hsh(math.floor(P[0] / 3), math.floor(P[1]), seed) < 0.18:
            return ramp[6]
        return ramp[4] if k < 2 else ramp[3]
    return Mat(f)


# ================================================================ finishing

def done(S, cv, kind, footprint, door_x=None, door_w=14, chims=(), shadow=(), post=None):
    """Outline, then the see-through bits drawn outside it (shadows on the water, ripples, ropes)."""
    S.finish(cv)
    put_shadow(cv, shadow)
    if post:
        post(cv)
    return _result(cv, kind, (S.ox, S.base), footprint, S.sx(door_x) if door_x is not None else None, door_w,
                   chims_screen(S, chims))


def deck_fp(x0, x1, y0, y1, zd=0.0):
    """The walkable rectangle of a deck at height zd from y0 to y1 (screen px from the base point)."""
    top = round(zd + K * y1)
    bot = round(zd + K * y0)
    return [round(x0), -top, round(x1 - x0), top - bot]


def rope_line(cv, x0, y0, x1, y1, sag=2.0, col=ROPE[3], dark=ROPE[0], thick=False):
    """A rope between two points sagging in the middle; thick ropes get a lit top and a dark
    underside so they read over a deck too."""
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    last = None
    for i in range(n + 1):
        t = i / n
        x = round(x0 + (x1 - x0) * t)
        y = round(y0 + (y1 - y0) * t + sag * 4 * t * (1 - t))
        if (x, y) != last:
            cv.set(x, y, col)
            if thick:
                cv.set(x, y + 1, ROPE[1])
                if cv.inb(x, y + 2) and cv.px[x, y + 2][3] == 0:
                    cv.set(x, y + 2, dark)
            elif cv.inb(x, y + 1) and cv.px[x, y + 1][3] == 0:
                cv.set(x, y + 1, dark)
        last = (x, y)


def coil(cv, cx, cy, rx=4, ry=2):
    """A coil of rope lying flat."""
    for ring in range(3):
        a, b = rx - ring * 1.2, ry - ring * 0.6
        if a < 1:
            break
        for k in range(48):
            t = k / 48 * 2 * math.pi
            x, y = cx + a * math.cos(t), cy + b * math.sin(t)
            cv.set(round(x), round(y), ROPE[3] if math.sin(t) < 0 and math.cos(t) < 0.3 else ROPE[2] if math.sin(t) < 0.5 else ROPE[1])
    cv.set(cx, cy, ROPE[0])
    cv.set(cx + 1, cy, ROPE[1])


# ================================================================ dock

def dock(spec):
    """A wooden pier running back from the shore into a lake: planks laid across on a frame,
    square pilings along both sides standing in the water, a lantern on a tall post at the far
    end, an iron bollard with a coil of rope and a mooring line, a crate, a bucket with a fish
    in it and a fishing rod."""
    rnd = random.Random(spec.get("seed", 1))
    L = spec.get("length", 64)
    hw = spec.get("width", 24) / 2
    zd, zw = 2.0, -7.0  # deck top, waterline
    shore = spec.get("shore", 10)  # px back from the front edge where the water starts
    S = Scene(pad=6, pad_top=6)
    S.add(box(-hw, hw, 0, L, 0, zd, deck_boards(DOCKWOOD, seed=spec.get("seed", 1), nails=(-hw + 2, 0, hw - 2))))
    posts = []
    ys = [1.5] + [y for y in range(shore + 12, int(L) - 8, 16)] + [L - 1.5]
    for y in ys:
        for side in (-1, 1):
            if side < 0 and y == ys[-1]:
                continue  # the lantern post stands there
            z0 = 0.0 if y < shore else zw
            x = side * (hw + 1.1)
            top = zd + (5 if y == ys[-1] else 2.5)
            S.add(box(x - 1.2, x + 1.2, y - 1.2, y + 1.2, z0, top, post_wood(wet=zw + 2.5, seed=int(y) + side)))
            if y >= shore:
                posts.append((x, y))
    lx, ly = -hw - 1.1, L - 1.5
    S.add(box(lx - 1.2, lx + 1.2, ly - 1.2, ly + 1.2, zw, zd + 21, post_wood(DARKWOOD, wet=zw + 2.5, seed=9)))
    posts.append((lx, ly))
    S.add(box(lx - 1.8, lx + 1.8, ly - 1.8, ly + 1.8, zd + 21, zd + 22.5, flat_m(DARKWOOD, 0.2)))
    # bollard: a squat iron post with a flared cap
    bx, by = hw - 4, L - 5
    iron = IRON + ["#6f6c78", "#8d8a96", "#a9a6b2"]
    S.add(prism(bx, by, 1.8, zd, zd + 4, flat_m(iron, 0.1), sides=10))
    S.add(prism(bx, by, 2.6, zd + 4, zd + 5.2, flat_m(iron, 0.25), sides=10))
    # a crate and a bucket by the lantern post
    S.add(box(-hw + 2, -hw + 9, L - 8, L - 2, zd, zd + 6, M.crate(WOOD)))
    S.add(frustum(-hw + 12.5, L - 4, 2.1, 2.5, zd, zd + 4, M.barrel(DARKWOOD, seed=3), sides=10))
    wy = shore - zw / K  # where the map's water is, seen at this waterline
    catcher(S, hw - 1, hw + 12, wy, L + 6, zw)
    catcher(S, -hw - 4, -hw + 1, wy, L + 6, zw)
    cv = S.render(extra=(0, 6, 0, 0))
    shadow = catch(S, cv)
    # lantern hung from an arm off the post's top, over the deck
    cv.free()
    px, py = S.s(lx, ly, zd + 20)
    for x in range(px + 1, px + 6):
        cv.set(x, py, IRON[1])
    cv.set(px + 2, py + 1, IRON[1])
    hang_lantern(cv, px + 5, py + 1)
    # bucket: dark water and a fish tail
    cv.at_depth(L - 6.5)
    qx, qy = S.s(-hw + 12.5, L - 4, zd + 4)
    for x in range(qx - 1, qx + 2):
        cv.set(x, qy, WATER[1])
    cv.set(qx, qy - 1, "#9fb3c4")
    cv.set(qx + 1, qy - 2, "#c9d8e4")
    cv.set(qx - 1, qy - 2, "#7f97ad")
    # coil of rope on the deck
    cv.at_depth(L - 12)
    cx, cy = S.s(bx - 6, L - 8, zd)
    coil(cv, cx, cy, 4, 2)
    # a fishing rod leaning on the crate, its line trailing
    cv.at_depth(L - 9)
    fx, fy = S.s(-hw + 8, L - 8.5, zd)
    for i in range(18):
        cv.set(fx - i // 3, fy - i, WOOD[3] if i < 5 else WOOD[5] if i < 12 else "#cdb98f")
    cv.set(fx - 1, fy - 4, IRON[2])
    cv.set(fx - 2, fy - 4, IRON[1])

    def post(cv):
        for x, y in posts:  # rings where the posts meet the water
            sx, sy = S.s(x, y, zw)
            ripple(cv, sx - 1, sx + 1, sy, wide=2)
        bxs, bys = S.s(bx + 2.5, by, zd + 5)  # mooring line off the bollard into the water
        ex, ey = S.s(hw + 9, L - 14, zw)
        rope_line(cv, bxs, bys, ex, ey, sag=1.5)
        ripple(cv, ex - 1, ex + 1, ey, wide=1)
        tx, ty = S.s(-hw + 8 - 6, L - 8.5, zd + 18)  # fishing line from the rod tip
        for i in range(1, 12):
            if cv.inb(tx - 1, ty + i) and cv.px[tx - 1, ty + i][3] == 0:
                cv.px[tx - 1, ty + i] = (230, 230, 220, 150)
    info = done(S, cv, "prop", deck_fp(-hw, hw, 0, L, zd), shadow=shadow, post=post)
    info[2]["place"] = "deck"
    info[2]["solid"] = False
    return info


def hang_lantern(cv, x, y):
    """A hanging ship's lantern (5 wide): a ring, a cap, glass panes that glow at night."""
    cv.set(x + 2, y, IRON[2])
    for i in range(1, 4):
        cv.set(x + i, y + 1, IRON[1])
    for i in range(5):
        cv.set(x + i, y + 2, IRON[2] if i < 3 else IRON[1])
    for yy in range(y + 3, y + 8):
        for i in range(5):
            frame = i in (0, 4) or i == 2 and yy in (y + 3,)
            if frame:
                cv.set(x + i, yy, IRON[1])
            else:
                c = "#fff3c4" if yy < y + 5 and i == 1 else "#f6d98a" if yy < y + 6 else "#d9a94e"
                cv.set(x + i, yy, c)
                cv.lit(x + i, yy, LIT[4] if yy < y + 6 and i < 3 else LIT[3])
    for i in range(5):
        cv.set(x + i, y + 8, IRON[1])
    cv.set(x + 2, y + 9, IRON[2])


# ================================================================ rowboat

HULL_PAINT = {
    "teal": ["#132a2c", "#1f4446", "#2d5f5e", "#3f7b76", "#5a9a90", "#80b8aa", "#acd4c4"],
    "red": RED,
    "white": WHITEWASH,
    "blue": ["#141f33", "#22344f", "#334c70", "#486693", "#6684b0", "#8ea7cb", "#bccbe2"],
}


def hull_mat(paint, wood=WOOD, stripe=None, seed=1):
    """A clinker-built hull: overlapping strakes. The outside painted, the inside bare wood; the
    gunwale capped in a darker rail; an optional stripe under it."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _st(DARKWOOD, light + 0.2, 1)
        inside = s.params.get("inside")
        r = wood if inside else paint
        zz = P[2]
        k = zz % 1.9
        lv = light + (-0.3 if inside else 0.05)
        if inside and P[0] % 4.5 < 1.0 and zz < s.params.get("ztop", 5) - 0.8:
            return _st(wood, lv, -1)  # ribs
        if not inside and stripe and zz > s.params.get("ztop", 5) - 1.6:
            return _t(stripe, lv)
        if k < 0.55:
            return _st(r, lv, -1)  # the lower edge of the strake above
        if k > 1.45:
            return _st(r, lv, 1)
        return _t(r, lv)
    return Mat(f)


def rowboat(spec):
    """A small clinker rowboat floating side on: you see the painted outside of the near side and
    down into the hull: the bare-wood inside of the far side, floor boards with a little bilge
    water, three thwarts, a pointed bow with a stem post, a flat transom; the oars shipped in
    their rowlocks with the blades resting on the water, a coil of painter rope on the bow."""
    rnd = random.Random(spec.get("seed", 1))
    paint = HULL_PAINT[spec.get("paint", "teal")]
    stripe = HULL_PAINT[spec.get("stripe", "white")] if spec.get("stripe", "white") else None
    hm = hull_mat(paint, stripe=stripe)
    hi = hull_mat(paint)
    # stations along the boat: x, half-beam at the gunwale, gunwale height
    st = [(-16.5, 4.3, 6.0), (-12.0, 6.6, 5.0), (-4.0, 7.6, 4.3), (4.0, 7.2, 4.4), (10.0, 5.4, 5.2), (14.0, 3.0, 6.4),
          (17.5, 0.5, 7.8)]
    flare, th = 1.8, 1.0
    yc = 7.6 - flare
    rake = {st[0][0]: 1.3, st[-1][0]: -3.4}  # the transom and the stem lean out at the top
    S = Scene(pad=8, pad_top=6, pad_bottom=6)
    for side in (-1, 1):
        for a, b in zip(st, st[1:]):
            pts = []
            for (x, hb, zt) in (a, b):
                for z, w, xx in ((zt, hb, x), (0.0, max(0.5, hb * (1 - flare / 7.6)), x + rake.get(x, 0))):
                    pts.append((xx, yc + side * w, z))
                    pts.append((xx, yc + side * max(0.0, w - th), z))
            S.add(hull(pts, hm if side < 0 else hi, inside=side > 0, ztop=min(a[2], b[2])))
    x0, hb0, z0 = st[0]
    tr = []
    for dx in (0.0, 1.2):
        tr += [(x0 + dx, yc - hb0, z0), (x0 + dx, yc + hb0, z0),
               (x0 + 1.3 + dx, yc - hb0 * 0.76, 0.0), (x0 + 1.3 + dx, yc + hb0 * 0.76, 0.0)]
    S.add(hull(tr, hm, ztop=z0))
    S.add(convex([(13.6, 0.0), (15.2, 0.0), (18.8, 8.6), (17.2, 8.6)], "y", yc - 0.7, yc + 0.7, flat_m(DARKWOOD, 0.15)))
    fl = [(x + rake.get(x, 0) * 0.8, max(0.3, hb * (1 - flare / 7.6) - th - 0.3)) for x, hb, _ in st]
    floor = [(x, yc - w) for x, w in fl] + [(x, yc + w) for x, w in reversed(fl)]
    S.add(convex(floor, "z", -1.0, -0.4, deck_boards(DRIFT, w=2.5, along="y", seed=4)))
    for x, wd, hb in ((-12.5, 3.0, 6.5), (-0.5, 2.4, 7.6), (9.0, 2.4, 5.8)):
        S.add(box(x - wd / 2, x + wd / 2, yc - hb + 1.2, yc + hb - 1.2, 2.4, 3.2, M.wood(WOOD, bias=0.25)))
    # oars: from the handle inside, over the rowlock, down to the blade on the water
    oars = []
    for side in (-1, 1):
        lock = (2.5, yc + side * 7.6, 4.8)
        hand = (6.0, yc - side * 2.5, 3.9)
        tip = (-8.0, yc + side * 19.0, 0.5)
        ux, uy = tip[0] - hand[0], tip[1] - hand[1]
        ln = math.hypot(ux, uy)
        nx, ny = -uy / ln * 0.45, ux / ln * 0.45
        loom = [(hand[0] + nx, hand[1] + ny, hand[2] + 0.5), (hand[0] - nx, hand[1] - ny, hand[2] + 0.5),
                (hand[0] + nx, hand[1] + ny, hand[2] - 0.5), (hand[0] - nx, hand[1] - ny, hand[2] - 0.5)]
        bstart = (hand[0] + ux * 0.72, hand[1] + uy * 0.72, 1.4)
        shaft = loom + [(bstart[0] + nx, bstart[1] + ny, bstart[2] + 0.5), (bstart[0] - nx, bstart[1] - ny, bstart[2] + 0.5),
                        (bstart[0] + nx, bstart[1] + ny, bstart[2] - 0.5), (bstart[0] - nx, bstart[1] - ny, bstart[2] - 0.5)]
        S.add(hull(shaft, flat_m(TRIM + ["#f0dcb4"], 0.15)))
        bx2, by2 = nx * 2.4, ny * 2.4
        blade = [(bstart[0] + bx2, bstart[1] + by2, bstart[2] + 0.4), (bstart[0] - bx2, bstart[1] - by2, bstart[2] + 0.4),
                 (tip[0] + bx2, tip[1] + by2, tip[2] + 0.4), (tip[0] - bx2, tip[1] - by2, tip[2] + 0.4),
                 (bstart[0] + bx2, bstart[1] + by2, bstart[2] - 0.1), (bstart[0] - bx2, bstart[1] - by2, bstart[2] - 0.1),
                 (tip[0] + bx2, tip[1] + by2, tip[2] - 0.1), (tip[0] - bx2, tip[1] - by2, tip[2] - 0.1)]
        S.add(hull(blade, flat_m(TRIM + ["#f0dcb4"], 0.0)))
        oars.append((lock, tip))
        S.add(box(lock[0] - 0.6, lock[0] + 0.6, lock[1] - 0.6, lock[1] + 0.6, lock[2] - 0.6, lock[2] + 0.8, flat_m(IRON + ["#6f6c78"], 0.2)))
    catcher(S, -18, 24, -2, 2 * yc + 12, 0.0)
    cv = S.render(extra=(0, 0, 0, 0))
    shadow = catch(S, cv)
    # a little bilge water and a coil of rope on the bow
    cv.at_depth(yc - 3)
    for x in range(S.sx(-9), S.sx(-4)):
        for dy in (0, 1):
            cv.set(x, S.sy(yc + 2.5, -0.4) + dy, WATER[3] if dy else WATER[4] if x % 3 else WATER[5])
    cv.at_depth(yc - 2)
    cx, cy = S.s(13.0, yc, 1.0)
    coil(cv, cx, cy - 1, 2, 1)

    def post(cv):
        # where the hull meets the water: a bright rim and a dark reflection under the near side
        for x in range(S.sx(-17), S.sx(18) + 1):
            ys = [y for y in range(cv.h) if cv.px[x, y][3] == 255]
            if not ys:
                continue
            yb = max(ys)
            blend(cv, x, yb + 1, RIPPLE, 200 if x % 4 else 120)
            blend(cv, x, yb + 2, SHADOW, 60)
        for (lock, tip) in oars:
            sx, sy = S.s(tip[0], tip[1], 0)
            for dx in range(-3, 4):
                blend(cv, sx + dx, sy + 2 + (abs(dx) > 2), RIPPLE, 150)
    info = done(S, cv, "prop", deck_fp(-17, 17.5, 0, 2 * yc + 2 * flare, 0), shadow=shadow, post=post)
    info[2]["place"] = "water"
    return info


# ================================================================ stone bridges

BRIDGE_STONE = ["#29252a", "#453e40", "#625856", "#7f7369", "#9a8d7e", "#b5a893", "#cfc4ae"]
PAVE = ["#24211f", "#3d3733", "#58504a", "#71675e", "#8a7f73", "#a39787", "#bdb19e"]


class Arch:
    """A segmental arch in a face: the opening runs from a to b (along the face) above the water
    at zw; it rises straight for `jamb` px, then curves up to the crown."""

    def __init__(self, a, b, zw, crown, jamb=2.0, ring=3.5):
        self.a, self.b, self.zw, self.crown, self.ring = a, b, zw, crown, ring
        self.zs = zw + jamb
        s = (b - a) / 2
        self.m = (a + b) / 2
        self.zc = (crown * crown - s * s - self.zs * self.zs) / (2 * (crown - self.zs))
        self.R = crown - self.zc

    def top(self, u):
        d = self.R * self.R - (u - self.m) ** 2
        return self.zc + math.sqrt(d) if d > 0 else -1e9

    def inside(self, u, z, grow=0.0):
        if not (self.a - grow <= u <= self.b + grow) or z < self.zw - 0.01:
            return False
        if z <= self.zs:
            return True
        return math.hypot(u - self.m, z - self.zc) <= self.R + grow


def stone_face(ramp=BRIDGE_STONE, arches=(), axis="x", zw=None, seed=1, h=4):
    """Dressed stone courses; arches cut through it (dark water and shadow inside, a ring of
    voussoirs with a keystone round each); a dark, mossy band where the stone stays wet."""
    stone = M.dressed_stone(ramp, h=h, seed=seed)

    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + 0.15)
        uu = P[0] if axis == "x" else P[1]
        z = P[2]
        for ar in arches:
            if ar.inside(uu, z):
                depth = (z - ar.zw) / max(1.0, ar.crown - ar.zw)
                if z < ar.zw + 1.6:
                    k = (math.floor(uu * 0.7) + math.floor(z * 3)) % 5
                    return WATER[3] if k == 0 else WATER[2] if k < 3 else WATER[1]
                return "#141922" if depth > 0.45 else "#19212c" if depth > 0.2 else "#1c2a38"
            if z > ar.zs - 0.5 and ar.inside(uu, z, ar.ring):
                ang = math.atan2(z - ar.zc, uu - ar.m)
                seg = math.floor(ang / 0.21)
                frac = ang / 0.21 - seg
                lv = light + 0.12 + (hsh(seg, seed + 5) - 0.5) * 0.18
                if abs(uu - ar.m) < 1.6 and z > ar.crown - 0.5:
                    return _st(ramp, light + 0.25, 1)  # keystone
                if frac < 0.18:
                    return ramp[1]
                rr = math.hypot(uu - ar.m, z - ar.zc)
                if rr > ar.R + ar.ring - 0.9:
                    return _st(ramp, lv, -1)
                return _t(ramp, lv)
        if zw is not None and z < zw + 2.2:
            return MOSS[0] if z < zw + 0.9 else MOSS[1] if hsh(math.floor(uu), seed) < 0.6 else ramp[2]
        return stone.fn(uu, z, kind, light, P, s)
    return Mat(f)


def paving(ramp=PAVE, seed=1, path=None):
    """Cobbles on a deck: rounded setts in staggered rows (3 screen rows each), lit on the upper
    left, dark joints; path=(axis, lo, hi) wears a lighter, smoother track along the deck, and
    weeds grow in the joints by the edges."""
    def f(u, v, kind, light, P, s):
        if kind in ("wall", "side"):
            return _t(ramp, light)
        row = math.floor(P[1] / 3.75)
        k = (P[1] - row * 3.75) / 3.75  # 0 at the front of the row, 1 at the back
        off = 2.0 if row % 2 else 0.0
        w = 4.0
        seg = math.floor((P[0] + off) / w)
        aa = (P[0] + off - seg * w) / w
        worn = False
        if path:
            q = P[0] if path[0] == "x" else P[1]
            worn = path[1] < q < path[2]
            if (q < path[1] - 4 or q > path[2] + 4) and hsh(math.floor(P[0]), math.floor(P[1] * 1.25), seed + 9) < 0.06:
                return MOSS[2] if hsh(math.floor(P[0]), seed) < 0.5 else "#5f8a3e"
        lv = light + 0.02 + (hsh(row, seg, seed + 2) - 0.5) * 0.3 + (0.1 if worn else 0)
        if k < 0.3 or aa < 0.22:
            return ramp[2] if not worn else _st(ramp, lv, -1)
        if k > 0.62 and aa < 0.6:
            return _st(ramp, lv, 1)
        if aa > 0.8 and k < 0.6:
            return _st(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def coping(ramp=BRIDGE_STONE, seed=1, axis="x"):
    """Capstones on a parapet: long slabs, lit tops, joints every few px."""
    def f(u, v, kind, light, P, s):
        a = P[0] if axis == "x" else P[1]
        lv = light + 0.2 + (hsh(math.floor(a / 7), seed) - 0.5) * 0.15
        if (a % 7) < 0.8:
            return ramp[2]
        if kind in ("top", "slope"):
            return _st(ramp, lv, 1)
        return _t(ramp, lv - 0.1)
    return Mat(f)


def lamp_post(cv, x, y, h=14):
    """A short iron lamp on a stone post: a pole, a bracket, a glass head that glows."""
    for yy in range(y - h, y):
        cv.set(x, yy, IRON[2])
        cv.set(x + 1, yy, IRON[1])
    top = y - h
    for i in range(-2, 4):
        cv.set(x + i, top - 1, IRON[1])
    for yy in range(top - 6, top - 1):
        for i in range(-1, 3):
            edge = i in (-1, 2)
            cv.set(x + i, yy, IRON[1] if edge else "#f6e3a0" if yy < top - 3 else "#e3b35a")
            if not edge:
                cv.lit(x + i, yy, LIT[4] if yy < top - 3 else LIT[3])
    for i in range(-2, 4):
        cv.set(x + i, top - 7, IRON[1])
    cv.set(x, top - 8, IRON[2])
    cv.set(x + 1, top - 8, IRON[1])


def pier(S, x0, x1, y0, y1, z0, z1):
    """An end pier on a parapet: a square stone post, a projecting cap and a stone ball."""
    S.add(box(x0, x1, y0, y1, z0, z1, M.dressed_stone(BRIDGE_STONE, h=3, seed=11, bias=0.15)))
    S.add(box(x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6, z1, z1 + 1.3, coping(seed=12)))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for za, zb, ra, rb in ((0, 0.8, 1.2, 2.0), (0.8, 2.2, 2.0, 2.0), (2.2, 3.0, 2.0, 1.1)):
        S.add(frustum(cx, cy, ra, rb, z1 + 1.3 + za, z1 + 1.3 + zb, coping(seed=13), sides=10))


def ivy(cv, rnd, x, y, n, down=True):
    """A trail of ivy leaves hanging from (x, y)."""
    for i in range(n):
        xx = x + round(1.4 * math.sin(i * 0.8 + x))
        yy = y + i if down else y - i
        for dx in (-1, 0, 1):
            if rnd.random() < (0.7 if dx == 0 else 0.35):
                cv.set(xx + dx, yy, ("#2d5a2c", "#3f7a37", "#5fa047")[rnd.randint(0, 2)])


def bridge_x(spec):
    """A stone arch bridge crossing left to right over a stream that flows towards the viewer:
    a paved deck between low parapets with capstones and end piers, and below the deck's front
    edge the arch face: an arch ring of voussoirs with a keystone over the dark opening the
    stream runs out of, stone courses, a projecting string course, wet moss at the waterline
    and wing walls into the banks. A lamp on one end pier."""
    rnd = random.Random(spec.get("seed", 1))
    span = spec.get("span", 28)
    half = spec.get("length", 76) / 2
    D = spec.get("depth", 30)
    drop = spec.get("drop", 16)
    hp = 4.0  # parapet height over the deck
    pt = 3.5  # parapet thickness
    a = span / 2 + 7  # abutments
    zw = -drop
    S = Scene(pad=6, pad_top=10, pad_bottom=4)
    arch = Arch(-span / 2, span / 2, zw, -3.4, jamb=3.0, ring=3.2)
    S.add(box(-a, a, 0, D, zw, -1, stone_face(arches=[arch], zw=zw, seed=3)))
    for side in (-1, 1):  # wing walls running into the banks
        x0 = side * a
        S.add(convex([(x0, zw), (x0, -1), (x0 + side * 9, -1)], "y", 0.5, D - 0.5, stone_face(zw=zw, seed=4)))
    S.add(box(-a - 1, a + 1, -1, 1, -2.4, -0.6, coping(seed=6)))  # string course
    for y0, y1 in ((0, pt), (D - pt, D)):
        S.add(box(-half + 4, half - 4, y0, y1, 0, hp, M.dressed_stone(BRIDGE_STONE, h=3, seed=7 if y0 else 8, bias=0.15)))
        S.add(box(-half + 4, half - 4, y0 - 0.5, y1 + 0.5, hp, hp + 1.3, coping(seed=9 if y0 else 10)))
        for x in (-half, half - 5):  # end piers with a cap and a stone ball
            pier(S, x, x + 5, y0 - 0.5, y1 + 0.5, 0, hp + 3.5)
    S.add(box(-half, half, 0, D, -1, 0, paving(seed=spec.get("seed", 1), path=("y", 11, D - 8))))
    cv = S.render()
    cv.on_wall(0, tol=1.2)
    for x, n in ((-a + 3, 7), (-a + 5, 4), (a - 6, 6)):  # ivy down the face from the string course
        ivy(cv, rnd, S.sx(x), S.sy(0, -2.5), n)
    if spec.get("lamp", True):
        cv.free()
        lx, ly = S.s(half - 3, D - pt / 2, hp + 8)
        lamp_post(cv, lx, ly, h=9)

    def post(cv):
        # the waterline along the face, and the stream running out from under the arch
        y = S.sy(0, zw)
        for x in range(S.sx(-a - 8), S.sx(a + 8) + 1):
            if cv.px[x, y - 1][3] == 255 or cv.px[x, y][3] == 255:
                blend(cv, x, y + 1, RIPPLE, 200 if x % 5 else 110)
                blend(cv, x, y + 2, SHADOW, 50)
        r = random.Random(spec.get("seed", 1))
        for k in range(4):
            yy = y + 3 + k * 2
            w = span / 2 - 2 - k
            for x in range(S.sx(-w), S.sx(w)):
                if r.random() < 0.45 - k * 0.08:
                    blend(cv, x, yy, FOAM if k == 0 else RIPPLE, 200 - k * 35)
    out = done(S, cv, "prop", deck_fp(-half, half, 9, D - pt, 0), post=post)
    info = out[2]
    info["place"] = "deck"
    info["solid"] = False
    info["span"] = [round(-span / 2), round(span / 2)]  # the stream must pass between these x (screen px)
    return out


def bridge_y(spec):
    """A stone arch bridge running back over a stream that flows left to right: a paved deck
    humped over the arch between parapet walls on both sides, end piers front and back, the
    sides battered so their stone and the dark mouth of the arch show over the water, wet moss at
    the waterline, and the bridge's shadow on the water to the right."""
    span = spec.get("span", 26)
    Lb = spec.get("length", 84)
    hw = spec.get("width", 30) / 2
    H = spec.get("hump", 9.0)
    zw = -3.0
    pt = 3.5
    hp = 4.0
    ys0 = (Lb - span) / 2
    ys1 = ys0 + span
    ym = Lb / 2
    bat = 0.6

    def zt(y):
        t = (y - ym) / (Lb / 2)
        return H * (1 - t * t)

    S = Scene(pad=6, pad_top=10, pad_bottom=4)
    arch = Arch(ys0, ys1, zw, H - 3.8, jamb=1.0, ring=3.0)
    side = stone_face(arches=[arch], axis="y", zw=zw, seed=3)
    n = 12
    for i in range(n):
        ya, yb = Lb * i / n, Lb * (i + 1) / n
        za, zb = zt(ya), zt(yb)
        sl = (zb - za) / (yb - ya)
        # z <= za + sl (y - ya);  |x| <= hw + bat (top(y) - z)
        planes = [((0, -1, 0), -ya), ((0, 1, 0), yb), ((0, 0, -1), -zw),
                  ((0, -sl, 1), za - sl * ya - 1.0)]
        for sx in (-1, 1):
            # sx*x <= hw + bat*(za - 1 + sl*(y - ya) - z)  ->  sx*x - bat*sl*y + bat*z <= hw + bat*(za - 1 - sl*ya)
            planes.append(((sx, -bat * sl, bat), hw + bat * (za - 1 - sl * ya)))
        ztop = max(za, zb)
        S.add(Solid(planes, side, (-hw - bat * (ztop - zw), hw + bat * (ztop - zw), ya, yb, zw, ztop)))
        dk = [((0, -1, 0), -ya), ((0, 1, 0), yb), ((-1, 0, 0), hw), ((1, 0, 0), hw),
              ((0, -sl, 1), za - sl * ya), ((0, sl, -1), -(za - 1.0 - sl * ya))]
        S.add(Solid(dk, paving(seed=5, path=("x", -4, 4)), (-hw, hw, ya, yb, min(za, zb) - 1, ztop)))
        for sx in (-1, 1):  # parapets and their capstones, following the hump
            x0, x1 = (-hw, -hw + pt) if sx < 0 else (hw - pt, hw)
            if i == 0 or i == n - 1:
                continue
            for z0, z1, xa, xb, m in ((0, hp, x0, x1, M.dressed_stone(BRIDGE_STONE, h=3, seed=7)),
                                      (hp, hp + 1.3, x0 - 0.5, x1 + 0.5, coping(seed=9, axis="y"))):
                pl = [((0, -1, 0), -ya), ((0, 1, 0), yb), ((-1, 0, 0), -xa), ((1, 0, 0), xb),
                      ((0, -sl, 1), za + z1 - sl * ya), ((0, sl, -1), -(za + z0 - 0.5 - sl * ya))]
                S.add(Solid(pl, m, (xa, xb, ya, yb, min(za, zb) + z0 - 0.5, ztop + z1)))
    for yy in (0.0, Lb - 7):  # end piers
        for sx in (-1, 1):
            x0, x1 = (-hw - 0.5, -hw + pt + 0.5) if sx < 0 else (hw - pt - 0.5, hw + 0.5)
            zb = zt(yy + 3.5)
            pier(S, x0, x1, yy, yy + 6, zb - 1, zb + hp + 3.5)
    catcher(S, hw - 2, hw + 16, ys0 - zw / K, ys1 + 8, zw)
    cv = S.render()
    shadow = catch(S, cv)
    if spec.get("lamp", False):
        cv.free()
        lx, ly = S.s(hw - pt / 2, Lb - 3.5, zt(Lb - 3.5) + hp + 8)
        lamp_post(cv, lx, ly, h=9)

    def post(cv):
        for sx in (-1, 1):  # ripples where the battered sides meet the water
            for y in range(int(ys0 + 4), int(ys1) + 1):
                x = sx * (hw + bat * (zt(y) - 1 - zw))
                px, py = S.s(x, y, zw)
                for dx in range(-1, 3):
                    blend(cv, px + sx * dx, py + 1, RIPPLE, 170 if (y + dx) % 3 else 90)
    out = done(S, cv, "prop", deck_fp(-hw + pt, hw - pt, 0, Lb, 0), shadow=shadow, post=post)
    info = out[2]
    info["place"] = "deck"
    info["solid"] = False
    info["span"] = [-round(K * ys1), -round(K * ys0)]  # the stream's rows (screen px from the base point)
    return out


# ================================================================ wooden footbridge

def footbridge(spec):
    """A wooden footbridge. dir="x" (default): it crosses left to right over a stream flowing
    towards the viewer; planks laid across on two stringers, the front stringer and a trestle of
    legs with cross bracing showing below the deck's front edge, log sills on the banks, rope
    rails on squared posts front and back. dir="y": it runs back over a stream flowing left to
    right, gently humped, its rail posts running down beside the deck into the water."""
    rnd = random.Random(spec.get("seed", 1))
    wood = DOCKWOOD if spec.get("weathered", True) else WOOD
    rope_pts = []
    if spec.get("dir", "x") == "x":
        span = spec.get("span", 28)
        half = spec.get("length", 60) / 2
        D = spec.get("depth", 22)
        drop = spec.get("drop", 12)
        zw = -drop
        S = Scene(pad=6, pad_top=8, pad_bottom=4)
        S.add(box(-half, half, 0, D, -1.5, 0, deck_boards(wood, w=4.0, along="y", seed=spec.get("seed", 1), worn=0.15)))
        S.add(box(-half + 1, half - 1, 0.3, 2.3, -4.0, -1.5, M.wood(DARKWOOD, bias=0.15)))  # front stringer
        legs = [-span / 2 - 1.5, 0.0, span / 2 + 1.5]
        for x in legs:
            S.add(box(x - 1.2, x + 1.2, 0.6, 3.0, zw, -4.0, post_wood(wood, wet=zw + 2.5, seed=int(x) + 7)))
        posts = []
        n = max(2, round(2 * half / 15))
        for i in range(n + 1):
            x = -half + 1.5 + (2 * half - 3) * i / n
            for y in (0.4, D - 2.4):
                S.add(box(x - 1.0, x + 1.0, y, y + 2.0, 0, 8.5, post_wood(wood, seed=i * 3 + int(y))))
                posts.append((x, y + 1.0))
        cv = S.render()
        shadow = []
        cv.at_depth(3.2)
        for xa, xb in zip(legs, legs[1:]):  # cross bracing between the legs
            for (x0, z0, x1, z1) in ((xa + 1.2, -4.5, xb - 1.2, zw + 2.5), (xa + 1.2, zw + 2.5, xb - 1.2, -4.5)):
                p0, p1 = S.s(x0, 3.2, z0), S.s(x1, 3.2, z1)
                nn = max(1, abs(p1[0] - p0[0]))
                for i in range(nn + 1):
                    x = round(p0[0] + (p1[0] - p0[0]) * i / nn)
                    y = round(p0[1] + (p1[1] - p0[1]) * i / nn)
                    cv.set(x, y, wood[4])
                    cv.set(x, y + 1, wood[2])
        for y in (1.4, D - 1.4):
            row = [p for p in posts if abs(p[1] - y) < 0.1]
            for (xa, ya), (xb, yb) in zip(row, row[1:]):
                rope_pts.append((S.s(xa + 1, ya, 7.5), S.s(xb - 1, yb, 7.5)))
        foot = deck_fp(-half, half, 8, D - 2.5, 0)

        def water(cv):
            for x in legs:
                sx, sy = S.s(x, 0.6, zw)
                ripple(cv, sx - 1, sx + 1, sy, wide=2)
    else:
        span = spec.get("span", 26)
        Lb = spec.get("length", 72)
        hw = spec.get("width", 22) / 2
        H = spec.get("hump", 5.0)
        zw = -3.0
        ys0 = (Lb - span) / 2
        ys1 = ys0 + span

        def zt(y):
            t = (y - Lb / 2) / (Lb / 2)
            return H * (1 - t * t)

        S = Scene(pad=6, pad_top=8, pad_bottom=4)
        n = 10
        deck = deck_boards(wood, w=3.75, along="x", seed=spec.get("seed", 1), nails=(-hw + 2, hw - 2), worn=0.18)
        for i in range(n):
            ya, yb = Lb * i / n, Lb * (i + 1) / n
            za, zb = zt(ya), zt(yb)
            sl = (zb - za) / (yb - ya)
            dk = [((0, -1, 0), -ya), ((0, 1, 0), yb), ((-1, 0, 0), hw), ((1, 0, 0), hw),
                  ((0, -sl, 1), za - sl * ya), ((0, sl, -1), -(za - 1.6 - sl * ya))]
            S.add(Solid(dk, deck, (-hw, hw, ya, yb, min(za, zb) - 1.6, max(za, zb))))
        posts = []
        m = max(2, round(Lb / 14))
        for i in range(m + 1):
            y = 1.0 + (Lb - 2) * i / m
            for sx in (-1, 1):
                x = sx * (hw + 0.9)
                z0 = zw if ys0 - 2 < y < ys1 + 2 else 0.0
                S.add(box(x - 1.0, x + 1.0, y - 1.0, y + 1.0, z0, zt(y) + 8.5,
                          post_wood(wood, wet=zw + 2.5 if z0 < 0 else None, seed=i * 5 + sx)))
                posts.append((x, y, z0))
        catcher(S, hw - 1, hw + 12, ys0 - zw / K, ys1 + 6, zw)
        cv = S.render()
        shadow = catch(S, cv)
        for sx in (-1, 1):
            row = [p for p in posts if p[0] * sx > 0]
            for (xa, ya, _), (xb, yb, _) in zip(row, row[1:]):
                rope_pts.append((S.s(xa, ya + 1, zt(ya) + 7.5), S.s(xb, yb - 1, zt(yb) + 7.5)))
        foot = deck_fp(-hw, hw, 0, Lb, 0)

        def water(cv):
            for x, y, z0 in posts:
                if z0 < 0 and y > ys0 + 3:
                    sx, sy = S.s(x, y, zw)
                    ripple(cv, sx - 1, sx + 1, sy, wide=2)

    def post(cv):
        water(cv)
        for (a, b) in rope_pts:
            rope_line(cv, a[0], a[1], b[0], b[1], sag=1.6 if a[1] == b[1] else 0.8, thick=True)
    out = done(S, cv, "prop", foot, shadow=shadow, post=post)
    out[2]["place"] = "deck"
    out[2]["solid"] = False
    if spec.get("dir", "x") == "x":
        out[2]["span"] = [round(-span / 2), round(span / 2)]
    else:
        out[2]["span"] = [-round(K * ys1), -round(K * ys0)]
    return out


# ================================================================ lighthouse

def banded(white=WHITEWASH, red=RED, bands=(), seed=1):
    """A whitewashed round tower with red bands: faint courses, a weathered streak or two."""
    def f(u, v, kind, light, P, s):
        z = P[2]
        r = white
        for z0, z1 in bands:
            if z0 <= z < z1:
                r = red
        lv = light + 0.18
        if kind == "top":
            return _t(r, lv)
        if z % 4 < 0.6:
            return _st(r, lv, -1) if hsh(math.floor(u / 5), math.floor(z / 4), seed) < 0.6 else _t(r, lv)
        if hsh(math.floor(u / 2), seed) < 0.06 and r is white:
            return _st(r, lv, -1)  # rain streaks
        return _t(r, lv)
    return Mat(f)


GLASS_DAY = [C(GLASS[1]), C(GLASS[2]), C(GLASS[3]), C(GLASS[4])]


def lantern_glass(frame=IRON, seed=1, panes=8):
    """The lantern room: glass panes between iron glazing bars, a rail at the foot and the top."""
    def f(u, v, kind, light, P, s):
        z = P[2]
        z0, z1 = s.bbox[4], s.bbox[5]
        if kind == "top":
            return frame[2]
        if z < z0 + 1.5 or z > z1 - 1.2:
            return RED[3] if z < z0 + 1.5 and light > 0.4 else RED[2]
        ang = math.atan2(P[1] - s.params["cy"], P[0] - s.params["cx"])
        seg = (ang / (2 * math.pi) * panes) % 1.0
        if seg < 0.12 or seg > 0.94 or abs(z - (z0 + z1) / 2) < 0.5:
            return frame[1]
        return GLASS[4] if (math.floor(z) + math.floor(seg * 8)) % 7 == 0 else GLASS[3] if light > 0.5 else GLASS[2]
    return Mat(f)


def lighthouse(spec):
    """A lighthouse on the shore: a tall round tower, whitewashed with red bands (or bare stone),
    on a stone plinth; little windows climbing it; a corbelled gallery with an iron railing; the
    lantern room's glass round a great lens that shines at night; a red dome with a vent ball and
    a lightning rod. Against it the keeper's whitewashed hut with a door, a lit window, a chimney,
    a lifebuoy on the wall, rope and a barrel; rocks at the foot."""
    rnd = random.Random(spec.get("seed", 1))
    cy, r0, r1 = 13.5, 12.5, 9.0
    zt = 88.0
    S = Scene(pad=8, pad_top=8)
    S.add(prism(0, cy, r0 + 2.5, 0, 6, M.dressed_stone(STONE, seed=3, bias=0.12), sides=20))
    if spec.get("stone"):
        body = M.dressed_stone(STONE, seed=5)
    else:
        body = banded(bands=((20, 32), (46, 58), (72, 82)), seed=spec.get("seed", 1))
    S.add(frustum(0, cy, r0, r1, 6, zt, body, sides=20))
    S.add(frustum(0, cy, r1, r1 + 4, zt - 4, zt, M.dressed_stone(STONE, seed=7, bias=0.1), sides=20))  # corbels
    S.add(prism(0, cy, r1 + 4.5, zt, zt + 1.8, flat_m(IRON + ["#6f6c78", "#8d8a96"], 0.15), sides=20))  # gallery deck
    rl = 6.5
    lant = S.add(prism(0, cy, rl, zt + 1.8, zt + 14, lantern_glass(), sides=8))
    roof = flat_m(RED, 0.1)
    for za, zb, ra, rb in ((0, 1.2, rl + 1.6, rl + 1.6), (1.2, 3.5, rl + 1.2, rl - 0.5), (3.5, 5.5, rl - 0.5, rl - 3),
                           (5.5, 6.8, rl - 3, 1.5)):
        S.add(frustum(0, cy, ra, rb, zt + 14 + za, zt + 14 + zb, roof, sides=16))
    S.add(prism(0, cy, 1.6, zt + 20.8, zt + 23, flat_m(IRON + ["#6f6c78", "#8d8a96"], 0.3), sides=8))
    # the keeper's hut against the tower's left side
    hx0, hx1, hy0, hy1, hz = -42.0, -9.0, 0.0, 24.0, 30.0
    footing(S, hx0, hx1, hy0, hy1)
    S.add(box(hx0, hx1, hy0, hy1, 4, hz, M.plaster(WHITEWASH, seed=4, bias=0.12)))
    over = 3.0
    zr = hz + ((hy1 - hy0) / 2 + over) * 0.8
    S.add(gable_x(hx0 - over, hx1 + over - 2, hy0 - over, hy1 + over, hz - 3, hz, zr,
                  M.shingles(ROOFS[spec.get("roof_colour", "slate")], seed=6)))
    ch = chimney(S, hx0 + 7, (hy0 + hy1) / 2 + 2, hz, zr + 6, w=6)
    dcx = hx0 + 21
    step(S, dcx, w=16, depth=4)
    # rocks at the foot, a barrel and a coil of rope by the hut
    for (x, y, w, h) in ((15, 4, 7, 5), (11, -1, 5, 3.5), (-6, -2, 4, 3)):
        pts = [(x + w * math.cos(a) * (0.8 + 0.4 * hsh(k, x)), y + w * 0.7 * math.sin(a), 0) for k, a in enumerate(np.linspace(0, 2 * math.pi, 7)[:-1])]
        pts += [(x + w * 0.5 * math.cos(a + 0.4), y + w * 0.4 * math.sin(a + 0.4), h) for a in np.linspace(0, 2 * math.pi, 5)[:-1]]
        S.add(hull(pts, M.fieldstone(FIELDSTONE, seed=int(x) + 3)))
    S.add(prism(hx0 + 1, -4.5, 3.6, 0, 9, M.barrel(seed=2), sides=12))
    cv = S.render()
    front = cy - r0
    # little windows up the tower, a door's worth of shadow at the foot
    cv.on_wall(front + 0.5, tol=3.2)
    for dx, z in ((3, 40), (-3, 64), (2, 79)):
        tower_window(cv, S.sx(dx), S.sy(front + 1.2, z))
    # the lens inside the lantern room, glowing at night
    li = S.solids.index(lant)
    glass = {C(c) for c in (GLASS[2], GLASS[3], GLASS[4])}
    for y in range(cv.h):
        for x in range(cv.w):
            if S.sid[y, x] == li and cv.px[x, y] in glass:
                cv.lit(x, y, LIT[3] if (x + y) % 3 else LIT[4])
    lx, ly = S.s(0, cy - rl + 1, zt + 8)
    for yy in range(ly - 4, ly + 4):
        for xx in range(lx - 2, lx + 3):
            if S.sid[yy, xx] != li or abs(xx - lx) + abs(yy - ly) * 0.6 > 3:
                continue
            c = "#fff7d0" if abs(xx - lx) < 1 else BRASS_HI if xx < lx else "#d9a640"
            cv.px[xx, yy] = C(c)
            cv.lit(xx, yy, LIT[4])
    # gallery railing: the back half, then the front
    rr = r1 + 4.2
    for half in (1, -1):
        for k in range(48):
            a = k / 48 * 2 * math.pi
            if (math.sin(a) > 0) != (half > 0):
                continue
            px, py = S.s(rr * math.cos(a), cy + rr * math.sin(a), zt + 1.8)
            depth = cy + rr * math.sin(a)
            cv.at_depth(depth - 0.3)
            cv.set(px, py - 5, IRON[2] if half < 0 else IRON[1])
            if k % 3 == 0:
                for y in range(py - 4, py):
                    cv.set(px, y, IRON[1])
            elif half < 0:
                cv.set(px, py - 2, IRON[1])
    cv.free()
    tx, ty = S.s(0, cy, zt + 23)  # lightning rod
    for y in range(ty - 6, ty):
        cv.set(tx, y, IRON[2])
    # the hut: door, window, lifebuoy
    cv.on_wall(hy0)
    door(cv, rnd, S.sx(dcx), S.sy(hy0, 4), w=12, h=18, style="plank", wood=DARKWOOD, step=False)
    window(cv, rnd, S.sx(hx0 + 9), S.sy(hy0, 21), w=9, h=9, shutters="blue", box=True)
    buoy(cv, S.sx(hx1 - 5), S.sy(hy0, 17))
    cv.at_depth(-3)
    coil(cv, S.sx(hx1 - 5), S.sy(-3, 0), 3, 2)
    return done(S, cv, "house", fp_rect(hx0, r0, 0, cy + r0), dcx, door_w=12, chims=[ch])


BRASS_HI = "#f6dc8a"


def fp_rect(x0, x1, y0, y1):
    return [round(x0), -round(K * y1), round(x1 - x0), round(K * y1) - round(K * y0)]


def tower_window(cv, cx, cy):
    """A small deep-set window on a round tower: a dark reveal, glass that glows at night."""
    for y in range(cy - 4, cy + 3):
        for x in range(cx - 2, cx + 2):
            edge = y == cy - 4 or x in (cx - 2, cx + 1)
            cv.set(x, y, "#3b3a40" if edge else GLASS[1] if y < cy - 1 else GLASS[0])
            if not edge:
                cv.lit(x, y, LIT[3] if y < cy - 1 else LIT[2])
    for x in range(cx - 3, cx + 3):
        cv.set(x, cy + 3, WHITEWASH[6] if x < cx + 2 else WHITEWASH[4])


def buoy(cv, cx, cy, r=4):
    """A red and white lifebuoy hanging on a peg."""
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            d = math.hypot(x - cx, y - cy)
            if r - 1.9 <= d <= r + 0.4:
                a = math.atan2(y - cy, x - cx)
                red = math.floor((a + math.pi) / (math.pi / 2) + 0.5) % 2 == 0
                lit = x + y < cx + cy
                c = (RED[4] if lit else RED[3]) if red else (WHITEWASH[6] if lit else WHITEWASH[4])
                cv.set(x, y, c)
    cv.set(cx, cy - r - 2, IRON[1])


# ================================================================ watermill

WHEEL_FRAMES = 8
WHEEL_SPOKES = 8
WHEEL_PADDLES = 16


def trough(along, rim=DARKWOOD, wood=WOOD, seed=1):
    """A flume: plank sides and running water in the channel between its rims."""
    water = water_top(seed=seed)

    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        if kind == "top":
            e = min(P[1] - y0, y1 - P[1]) if along == "x" else min(P[0] - x0, x1 - P[0])
            if e < 1.1:
                return _st(rim, light + 0.25, 1)
            return water.fn(u, v, kind, light, P, s)
        k = P[2] % 2.2
        return wood[1] if k < 0.6 else _t(wood, light + 0.05)
    return Mat(f)


def wheel_solids(S, cx, cz, y0, y1, turn, R=16.5):
    """The water wheel at angle `turn`: two rims of 16 segments, 16 paddles between them, eight
    spokes on each side, a hub and the axle running back."""
    rim_m = M.wood(WOOD, bias=0.15)
    pad_m = M.wood(DARKWOOD, bias=0.2)
    spoke_m = M.wood(WOOD, bias=0.2)
    n = WHEEL_PADDLES
    for ya, yb in ((y0, y0 + 1.4), (y1 - 1.4, y1)):
        for k in range(n):
            a0, a1 = turn + k * 2 * math.pi / n, turn + (k + 1) * 2 * math.pi / n
            pts = [(cx + r * math.cos(a), cz + r * math.sin(a)) for r, a in ((R - 2.2, a0), (R, a0), (R, a1), (R - 2.2, a1))]
            S.add(convex(pts, "y", ya, yb, rim_m))
    for k in range(n):
        a = turn + (k + 0.5) * 2 * math.pi / n
        p0 = (cx + (R - 4.8) * math.cos(a), cz + (R - 4.8) * math.sin(a))
        p1 = (cx + (R + 1.7) * math.cos(a), cz + (R + 1.7) * math.sin(a))
        S.add(rod(p0, p1, 1.4, "y", y0 + 0.3, y1 - 0.3, pad_m))
    for ya, yb in ((y0 + 0.2, y0 + 1.2), (y1 - 1.2, y1 - 0.2)):
        for k in range(WHEEL_SPOKES):
            a = turn + k * 2 * math.pi / WHEEL_SPOKES + (0.2 if ya > y0 + 1 else 0.0)
            p0 = (cx + 2.0 * math.cos(a), cz + 2.0 * math.sin(a))
            p1 = (cx + (R - 2.2) * math.cos(a), cz + (R - 2.2) * math.sin(a))
            S.add(rod(p0, p1, 1.6, "y", ya, yb, spoke_m))
    S.add(convex(ngon(cx, cz, 3.0, 8, turn), "y", y0 - 0.6, y1 + 0.6, M.wood(DARKWOOD, bias=0.3)))
    S.add(convex(ngon(cx, cz, 1.4, 8, turn), "y", y0 - 1.4, y0 - 0.6, flat_m(IRON + ["#6f6c78", "#8d8a96"], 0.3)))
    S.add(convex(ngon(cx, cz, 1.5, 8), "y", y1 + 0.6, 2.0, flat_m(IRON + ["#6f6c78", "#8d8a96"], 0.1)))


def wheel_sheet(cx, cz, y0, y1, zw, spout, ref, size=(50, 50), R=16.5, seed=1):
    """Render the wheel turning through one spoke's worth (WHEEL_FRAMES frames) side by side,
    each cut off at the waterline with foam and spray, and the water pouring onto it from the
    flume. ref = (x, y, z) of the point that lands at the middle of every frame."""
    fw, fh = size
    sheet = Image.new("RGBA", (fw * WHEEL_FRAMES, fh), (0, 0, 0, 0))
    step_a = 2 * math.pi / WHEEL_SPOKES / WHEEL_FRAMES
    for f in range(WHEEL_FRAMES):
        rnd = random.Random(seed * 100 + f)
        W = Scene(pad=4, pad_top=4, pad_bottom=4)
        wheel_solids(W, cx, cz, y0, y1, -f * step_a, R)
        cv = W.render(extra=(4, 4, 12, 8))
        H, Wd = W.t.shape
        rows = (W.base - (np.arange(H) + 0.5))[:, None] - K * W.t
        cut = (W.sid >= 0) & (rows < zw)
        for yy, xx in zip(*np.nonzero(cut)):
            cv.px[int(xx), int(yy)] = (0, 0, 0, 0)
            W.sid[yy, xx] = -1
        W.finish(cv)
        # foam where the paddles cut the water, a few drops of spray
        wl = W.sy((y0 + y1) / 2, zw)
        for x in range(W.sx(cx - R - 2), W.sx(cx + R + 3)):
            if any(cv.px[x, yy][3] for yy in range(wl - 3, wl + 1)):
                if rnd.random() < 0.8:
                    blend(cv, x, wl + 1, FOAM, 230)
                if rnd.random() < 0.5:
                    blend(cv, x, wl + 2, RIPPLE, 170)
        for k in range(7):
            x = W.sx(cx - R * 0.8 + rnd.random() * R * 1.6)
            blend(cv, x, wl - rnd.randint(1, 4), FOAM, 200)
        # the water pouring from the spout onto the top of the wheel, streaks moving down
        sx0, sx1 = W.sx(spout[0] - 2.0), W.sx(spout[0] + 2.0)
        top = W.sy(spout[1], spout[2])
        for x in range(sx0, sx1 + 1):
            y = top
            over = 0
            while y < cv.h and y - top < 16:
                if cv.px[x, y][3] == 255:
                    over += 1  # the water runs on over the paddles a little way
                    if over > 3:
                        break
                ph = (y - f + x * 2) % 4
                c = (226, 244, 250) if ph == 0 else (170, 214, 236) if ph < 3 else (110, 168, 205)
                cv.px[x, y] = (*c, 240)
                y += 1
            blend(cv, x - 2, y, FOAM, 200)
            blend(cv, x + 2, y - 1, FOAM, 160)
        # water carried down the descending side
        for k in range(5):
            a = -0.2 - k * 0.32 - f * step_a * 2
            r = R + 1.0
            x, y = W.s(cx + r * math.cos(a) + 1, y0, cz + r * math.sin(a))
            blend(cv, x + 1, y, (170, 214, 236), 210)
            blend(cv, x + 1, y + 1, FOAM, 160)
        rx, ry = W.s(*ref)
        frame = cv.im.crop((rx - fw // 2, ry - fh // 2, rx - fw // 2 + fw, ry - fh // 2 + fh))
        sheet.alpha_composite(frame, (f * fw, 0))
    return sheet


def watermill(spec):
    """A watermill: a fieldstone mill house with a timber-framed upper storey under a gable to
    the front, a loft door with a hoist beam and a sack on its rope, a door with a step, windows
    lit at night, a chimney, a millstone leaning by the door and flour sacks; on its right a low
    stone wheelhouse, and in front of it, in the stream, a big overshot water wheel (an animated
    part, "wheel") fed by a wooden flume on trestles that brings the water from behind."""
    rnd = random.Random(spec.get("seed", 1))
    d = 44
    h2 = 28
    roof = ROOFS[spec.get("roof_colour", "slate")]
    rm = M.shingles(roof, seed=7, moss=0.05)
    zw = -2.0
    wcx, wcz, wy0, wy1, R = 45.0, 11.0, -11.0, -5.0, 17.0
    fz0, fz1 = 34.0, 37.5  # flume bottom and rim
    S = Scene(pad=6, pad_top=8, pad_bottom=6)
    footing(S, -h2, h2, 0, d)
    S.add(box(-h2, h2, 0, d, 4, 24, M.fieldstone(FIELDSTONE, seed=3)))
    S.add(box(-h2 - 1, h2 + 1, -2, d, 23, 26, M.wood(DARKWOOD, bias=0.05)))  # jetty beam
    pal = PLASTER
    S.add(box(-h2 - 1, h2 + 1, -1, d, 26, 44, M.plaster(pal, frame=([-h2 - 1, -11, 8, h2 - 2], [26, 41]))))
    zr_w, zr = gable_front(S, -h2 - 1, h2 + 1, -1, d, 44, 0.72, rm, M.plaster(pal, frame=([-1.5], [])), over=4)
    ch = chimney(S, -14, 30, 44, zr - 2, w=7)
    dcx = -8
    step(S, dcx, w=16)
    # the wheelhouse: a low stone block with a lean-to roof
    S.add(box(h2, h2 + 30, 2, 36, 0, 24, M.dressed_stone(STONE, seed=5)))
    S.add(slab(h2 - 1, h2 + 32, 0, 38, 23, 30, 2, M.shingles(roof, seed=9)))
    # millstone leaning on the wall by the door, sacks
    S.add(convex(ngon(-20.0, 6.5, 6.5, 16), "y", -4.5, -1.5, millstone()))
    # the flume: from behind (along y) to the front, then left (along x) to its spout over the wheel
    fx0, fx1 = 66.0, 72.0
    S.add(box(fx0, fx1, wy0, 40, fz0, fz1, trough("y", seed=2)))
    S.add(box(wcx + 1.5, fx0, wy0, wy1, fz0, fz1, trough("x", seed=3)))
    S.add(box(wcx - 0.5, wcx + 1.5, wy0 + 0.5, wy1 - 0.5, fz0 - 0.3, fz1 - 1.2, M.wood(DARKWOOD, bias=0.1)))  # spout lip
    for ty, z0 in ((-8.0, zw), (14.0, 0.0), (34.0, 0.0)):  # trestles
        for tx in (fx0 + 0.5, fx1 - 2.5):
            S.add(box(tx, tx + 2, ty - 1, ty + 1, z0, fz0, post_wood(DARKWOOD, wet=zw + 2 if z0 < 0 else None, seed=int(ty + tx))))
        S.add(box(fx0 - 0.5, fx1 + 0.5, ty - 1, ty + 1, fz0 - 2.5, fz0, M.wood(DARKWOOD, bias=0.15)))
    # the sluice gate at the back of the flume
    S.add(box(fx0 - 1, fx1 + 1, 36, 37.5, fz0, fz1 + 6, M.planks(DARKWOOD, h=3, seed=4)))
    cv = S.render(extra=(0, 0, 0, 6))
    # walls: the door, windows, a lantern
    cv.on_wall(0)
    door(cv, rnd, S.sx(dcx), S.sy(0, 4), style="plank", wood=DARKWOOD, step=False)
    window(cv, rnd, S.sx(13), S.sy(0, 19), w=12, h=10, shutters="green")
    lantern(cv, S.sx(dcx + 10), S.sy(0, 20))
    cv.on_wall(-1)
    for wx in (-17, 15):
        window(cv, rnd, S.sx(wx), S.sy(-1, 38), w=10, h=9, box=wx < 0)
    # the loft door in the gable, a hoist beam and a sack on its rope
    cv.on_wall(-1, tol=2.0)
    ly = S.sy(-1, 53)
    for y in range(ly, ly + 9):
        for x in range(S.sx(-4), S.sx(4)):
            edge = x in (S.sx(-4), S.sx(4) - 1) or y == ly
            cv.set(x, y, TRIM[1] if edge else DARKWOOD[3] if (x - S.sx(-4)) % 3 else DARKWOOD[2])
    cv.free()
    hx, hy = S.s(0, -6, 66)
    for x in range(hx - 1, hx + 2):
        cv.set(x, hy, DARKWOOD[5])
        cv.set(x, hy + 1, DARKWOOD[2])
    for y in range(hy + 2, hy + 12):
        cv.set(hx, y, "#5c4632")
    sack(cv, hx - 3, hy + 17)
    # sacks by the door, the millstone's eye
    cv.at_depth(-4)
    sack(cv, S.sx(dcx + 9), S.sy(-4, 0))
    sack(cv, S.sx(dcx + 13), S.sy(-6, 0))
    mx, my = S.s(-20, -4.5, 6.5)
    for x in range(mx - 1, mx + 2):
        for y in range(my - 1, my + 2):
            cv.set(x, y, "#2a2523" if (x, y) != (mx - 1, my - 1) else "#4e4844")
    # the sluice gate's handwheel
    gx, gy = S.s((fx0 + fx1) / 2, 36, fz1 + 9)
    cv.at_depth(35.5)
    for k in range(12):
        a = k * math.pi / 6
        cv.set(round(gx + 2.5 * math.cos(a)), round(gy + 2.5 * math.sin(a)), IRON[2])
    cv.set(gx, gy, IRON[1])
    for y in range(gy + 1, gy + 6):
        cv.set(gx, y, IRON[1])
    sheet_ref = (wcx, -10.0, 13.0)  # projects to whole pixels: (45, -5) from the base point
    sheet = wheel_sheet(wcx, wcz, wy0, wy1, zw, (wcx + 1.5, (wy0 + wy1) / 2, fz0), sheet_ref, size=(50, 52), R=R,
                        seed=spec.get("seed", 1))

    def post(cv):
        sx, sy = S.s(fx0 + 1.5, -8, zw)
        ripple(cv, sx - 1, sx + 1, sy)
        sx, sy = S.s(fx1 - 1.5, -8, zw)
        ripple(cv, sx - 1, sx + 1, sy)
    im, night, info = done(S, cv, "house", fp(-h2, h2 + 30, d), dcx, chims=[ch], post=post)
    info["wheel"] = [round(sheet_ref[0]), round(-sheet_ref[2] - K * sheet_ref[1])]
    info["wheel_frames"] = WHEEL_FRAMES
    info["wheel_fps"] = 6
    info["wheel_water"] = [round(wcx - R - 2), round(fx1), round(-zw - K * wy0)]  # the stream under the wheel
    return im, night, info, {"wheel": sheet}


def millstone():
    """A millstone's face: dressed grey stone with grooves fanning out from the eye, a dark rim."""
    ramp = ["#26232a", "#403b40", "#5a5458", "#746c6c", "#8e8580", "#a89e95", "#c2b8ac"]

    def f(u, v, kind, light, P, s):
        dx, dz = P[0] - (s.bbox[0] + s.bbox[1]) / 2, P[2] - (s.bbox[4] + s.bbox[5]) / 2
        rr = math.hypot(dx, dz)
        if kind != "wall" or rr > 5.6:
            return _t(ramp, light - 0.05)
        a = math.atan2(dz, dx)
        if (a * 6 / math.pi) % 1.0 < 0.22 and rr > 1.8:
            return ramp[2]
        return _t(ramp, light + 0.1)
    return Mat(f)


def fp(x0, x1, dd):
    fd = round(K * dd)
    return [round(x0), -fd, round(x1 - x0), fd]


DESIGNS = {"watermill": watermill, "dock": dock, "rowboat": rowboat, "lighthouse": lighthouse, "bridge_x": bridge_x,
           "bridge_y": bridge_y, "footbridge": footbridge}

ENTRIES = [
    {"id": "watermill", "name": "水车磨坊", "group": GROUP, "type": "watermill", "seed": 1},
    {"id": "dock", "name": "码头", "group": GROUP, "type": "dock", "seed": 2},
    {"id": "rowboat", "name": "小船", "group": GROUP, "type": "rowboat", "seed": 3, "paint": "teal"},
    {"id": "rowboat_red", "name": "红色小船", "group": GROUP, "type": "rowboat", "seed": 4, "paint": "red", "stripe": None},
    {"id": "lighthouse", "name": "灯塔", "group": GROUP, "type": "lighthouse", "seed": 5},
    {"id": "bridge_x", "name": "石拱桥（横）", "group": GROUP, "type": "bridge_x", "seed": 6},
    {"id": "bridge_y", "name": "石拱桥（纵）", "group": GROUP, "type": "bridge_y", "seed": 7},
    {"id": "footbridge", "name": "木桥", "group": GROUP, "type": "footbridge", "seed": 8},
    {"id": "footbridge_y", "name": "木桥（纵）", "group": GROUP, "type": "footbridge", "seed": 9, "dir": "y"},
]
