"""Ruins, camps and other things out in the wild, modelled in 3D for the oblique renderer
(oblique.py, see town3d.py): marble temple columns (whole, ivy-grown, broken, fallen drums), a
crumbling wall with a broken arched window, a stone archway, an obelisk with a glowing rune, a
forest shrine, a mine entrance cut into a rock mound, a camp tent, a camp fire with animated
flames, and a wooden watchtower.

Besides the renderer's boxes, prisms and roofs this module builds general convex solids from
planes (`poly`): turned boxes (`obox`) for fallen and tilted blocks, cylinders along any axis
(`cyl`) for logs, drums and slanting posts, wedges of a column (`sector`) for a broken shaft's
jagged top, and faceted rocks (`rock`). Marble is fluted round the shaft and shows rough, fresh
stone where it broke; blocks get mortar joints, chipped edges, moss and rain streaks. Ivy, moss,
flowers, grass, ropes, glyphs and small tools are 2D parts drawn on afterwards."""
import itertools
import math
import random

import numpy as np
from PIL import Image

from buildings import C, DARKWOOD, IRON, LIT, ROOFS, TRIM, WOOD, _result, item, lantern
from landmarks import EMBER
from market import CLOTH, GOLD, pennant
from oblique import K, Mat, Scene, Solid, _shade, box, frustum, gable_y, hip_x, hsh, prism, roof_shell_y
import materials as M

GROUP = "野外"

# ---------------------------------------------------------------- palettes (dark -> light)
MARBLE = ["#27232f", "#4a4555", "#6f6b7b", "#98949f", "#bebbc0", "#dedbd5", "#f6f2e8"]
GRANITE = ["#1d1f27", "#33363f", "#4b4f5c", "#646a78", "#808797", "#a0a7b4", "#c5cad2"]
RUIN = ["#26221f", "#433c36", "#625950", "#81776b", "#a09584", "#bdb29e", "#d9cfbb"]  # weathered sandstone
ROCK = ["#1f1c1d", "#37312f", "#514843", "#6d625a", "#8a7d72", "#a8998b", "#c7b9a9"]
MOSS = ["#1b2c1b", "#2a4426", "#3d6032", "#567f3f", "#74a04d", "#97bf63"]
IVY = ["#14281a", "#1f3d22", "#2d5a2c", "#3f7a37", "#5fa047", "#86c25a"]
GRASS = ["#2a5a2a", "#3d7a34", "#58a043", "#7cbf55", "#a3d873"]
BARK = ["#21160f", "#382518", "#523722", "#6c4a2d", "#87603b", "#a27a4f"]
ENDGRAIN = ["#5a3f24", "#8a6239", "#b38654", "#d4a872", "#ebc994"]
TENT = ["#2f281e", "#5b4e39", "#857455", "#a8966f", "#c4b38a", "#dccfaa", "#eee6cc"]
TENT_GREEN = ["#1d2617", "#344229", "#4c5d3a", "#64784a", "#80935f", "#a0b07d", "#c3cfa2"]
TENT_RED = ["#2c1514", "#552524", "#7a3632", "#9a4a42", "#b5645a", "#cd877b", "#e4ada2"]
FIELDSTONE_ = ["#2a2622", "#4a433b", "#6a6156", "#887e70", "#a59a8a", "#c0b6a5", "#d9d1c1"]
BRASS_ = "#e8c15a"
FLAME = ["#b82a03", "#e85d03", "#f59a03", "#ffcf03", "#fff3a3"]  # blue 3: lamplight; last is a day-only core
GLOW = [LIT[0], LIT[1], LIT[2], LIT[3], LIT[4]]
BLOOM = [("#ffffff", "#ffe066"), ("#ff9ec4", "#ffe066"), ("#ffe066", "#ffffff"), ("#c9b3ff", "#ffe066"),
         ("#ff8a7a", "#ffe066"), ("#9cc8ff", "#ffffff")]


def _clamp(i, lo, hi):
    return lo if i < lo else hi if i > hi else i


def _ix(lv, n=7):
    """Light 0..1 -> a ramp index (2 .. n-2), spread wider than buildings.tone so a round shaft
    runs from lit to shaded."""
    return _clamp(round(2 + lv * (n - 3) * 1.05), 2, n - 2)


def vnoise(x, y, s, seed):
    """Smooth value noise in [0, 1) with cells s px wide."""
    gx, gy = x / s, y / s
    ix, iy = math.floor(gx), math.floor(gy)
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hsh(ix, iy, seed), hsh(ix + 1, iy, seed)
    c, d = hsh(ix, iy + 1, seed), hsh(ix + 1, iy + 1, seed)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


# ================================================================ solids

def _vertices(planes):
    N = np.array([n for n, d in planes])
    D = np.array([d for n, d in planes])
    tri = np.array(list(itertools.combinations(range(len(planes)), 3)))
    A = N[tri]
    b = D[tri]
    det = np.linalg.det(A)
    ok = np.abs(det) > 1e-9
    P = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]
    inside = np.all(P @ N.T <= D + 1e-6, axis=1)
    return P[inside]


def poly(planes, mat, **kw):
    """A convex solid from planes n.P <= d; its bounding box from its corners."""
    s = Solid(planes, mat, (0, 0, 0, 0, 0, 0), **kw)
    v = _vertices(s.planes)
    s.bbox = (v[:, 0].min(), v[:, 0].max(), v[:, 1].min(), v[:, 1].max(), v[:, 2].min(), v[:, 2].max())
    return s


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotation: roll about x, then pitch about y, then yaw about z (radians)."""
    cz, sz = math.cos(yaw), math.sin(yaw)
    cy, sy = math.cos(pitch), math.sin(pitch)
    cx, sx = math.cos(roll), math.sin(roll)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    return Rz @ Ry @ Rx


def obox(c, h, R, mat, **kw):
    """A box of half-sizes h centred on c, turned by R (fallen blocks, tilted boards)."""
    c = np.asarray(c, float)
    planes = []
    for i in range(3):
        a = R[:, i]
        planes.append((a, float(a @ c) + h[i]))
        planes.append((-a, -float(a @ c) + h[i]))
    return poly(planes, mat, obox=(c, np.asarray(h, float), R), **kw)


def cyl(p0, p1, r, mat, sides=14, phase=0.0, floor=None, **kw):
    """A many-sided cylinder from p0 to p1 (logs, drums lying down, slanting posts and poles);
    floor=z clips it flat where it lies on the ground."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = p1 - p0
    L = float(np.linalg.norm(a))
    a = a / L
    e1 = np.cross(a, (0, 0, 1)) if abs(a[2]) < 0.9 else np.cross(a, (1, 0, 0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    planes = [(-a, -float(a @ p0)), (a, float(a @ p1))]
    for k in range(sides):
        t = (k + 0.5) * 2 * math.pi / sides + phase
        n = math.cos(t) * e1 + math.sin(t) * e2
        planes.append((n, float(n @ p0) + r))
    if floor is not None:
        planes.append(((0, 0, -1), -floor))
    return poly(planes, mat, axis=(p0, a, e1, e2, r, L), **kw)


def sector(cx, cy, r, a0, a1, z0, ztop, mat, tilt=(0.0, 0.0), sides=32, **kw):
    """A wedge of an upright round shaft between angles a0..a1 (< 180 degrees) with a tilted top
    through (cx, cy, ztop): several of them make a broken column's jagged top."""
    tx, ty = tilt
    planes = [((0, 0, -1), -z0), ((tx, ty, 1), tx * cx + ty * cy + ztop),
              ((math.sin(a0), -math.cos(a0), 0), math.sin(a0) * cx - math.cos(a0) * cy),
              ((-math.sin(a1), math.cos(a1), 0), -math.sin(a1) * cx + math.cos(a1) * cy)]
    for k in range(sides):
        a = (k + 0.5) * 2 * math.pi / sides
        n = (math.cos(a), math.sin(a), 0)
        planes.append((n, r + n[0] * cx + n[1] * cy))
    return poly(planes, mat, cx=cx, cy=cy, r=r, **kw)


def rock(cx, cy, z0, rx, ry, rz, mat, seed=1, n=14, jag=0.18, lift=0.55, top=None, **kw):
    """A faceted rock: an ellipsoid cut by n jittered planes, sitting flat on z0 (and cut flat
    at z=top if given: a slab, an offering stone)."""
    rnd = random.Random(seed)
    cz = z0 + rz * lift
    planes = [((0, 0, -1), -z0)]
    if top is not None:
        planes.append(((0, 0, 1), top))
    off = rnd.random() * math.pi
    for k in range(n):
        zz = 1 - 2 * (k + 0.5) / n
        rr = math.sqrt(max(0.0, 1 - zz * zz))
        t = k * 2.39996 + off
        d = np.array([math.cos(t) * rr, math.sin(t) * rr, zz])
        d += np.array([rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.15, 0.15)])
        d /= np.linalg.norm(d)
        h = math.sqrt((rx * d[0]) ** 2 + (ry * d[1]) ** 2 + (rz * d[2]) ** 2)
        planes.append((d, float(d @ (cx, cy, cz)) + h * (1 - jag * rnd.random())))
    return poly(planes, mat, rock=(cx, cy, cz), **kw)


def tub(x0, x1, y0, y1, z0, z1, flare, mat, **kw):
    """A box whose four sides lean out by `flare` at the top (a mine cart, a trough)."""
    f = flare / (z1 - z0)
    planes = [((0, 0, -1), -z0), ((0, 0, 1), z1),
              ((-1, 0, -f), -x0 - f * z0), ((1, 0, -f), x1 - f * z0),
              ((0, -1, -f), -y0 - f * z0), ((0, 1, -f), y1 - f * z0)]
    return poly(planes, mat, **kw)


def spire(cx, cy, r, z0, z1, mat, sides=4, rot_=math.pi / 4, **kw):
    """A pyramid with its faces turned by rot_ (4 sides square to the axes by default)."""
    h = z1 - z0
    planes = [((0, 0, -1), -z0)]
    for k in range(sides):
        a = (k + 0.5) * 2 * math.pi / sides + rot_
        n = (math.cos(a), math.sin(a), r / h)
        planes.append((n, n[0] * cx + n[1] * cy + r / h * z1))
    return poly(planes, mat, cx=cx, cy=cy, r=r, ze=z0, zr=z1, cone=True, **kw)


def chamfered(x0, x1, y0, y1, z0, z1, mat, cuts=(), **kw):
    """A box with some edges worn off: cuts = [(edge, px)], edge one of 'tf' (top front),
    'tl', 'tr', 'tb', 'fl', 'fr' (front vertical edges)."""
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0), ((0, 0, 1), z1)]
    E = {"tf": ((0, -1, 1), -y0 + z1), "tb": ((0, 1, 1), y1 + z1), "tl": ((-1, 0, 1), -x0 + z1),
         "tr": ((1, 0, 1), x1 + z1), "fl": ((-1, -1, 0), -x0 - y0), "fr": ((1, -1, 0), x1 - y0)}
    for e, c in cuts:
        n, d = E[e]
        planes.append((n, d - c))
    return poly(planes, mat, blk=(x0, x1, y0, y1, z0, z1), **kw)


def voussoir(cx, cz, y0, y1, ri, ta, tb, mat, ro=None, rect=None, front=0.0, **kw):
    """One wedge stone of an arch round (cx, cz) between angles ta < tb (0 = right, pi = left),
    y0..y1 deep: its underside a chord at ri, its back a chord at ro or the rectangle
    rect=(x0, x1, ztop) when it is bonded into a wall's courses. front pulls it forward."""
    tm, half = (ta + tb) / 2, (tb - ta) / 2
    planes = [((0, -1, 0), -(y0 - front)), ((0, 1, 0), y1),
              ((-math.cos(tm), 0, -math.sin(tm)), -math.cos(tm) * cx - math.sin(tm) * cz - ri * math.cos(half)),
              ((math.sin(ta), 0, -math.cos(ta)), math.sin(ta) * cx - math.cos(ta) * cz),
              ((-math.sin(tb), 0, math.cos(tb)), -math.sin(tb) * cx + math.cos(tb) * cz)]
    if ro is not None:
        planes.append(((math.cos(tm), 0, math.sin(tm)), math.cos(tm) * cx + math.sin(tm) * cz + ro))
    if rect is not None:
        x0, x1, ztop = rect
        planes += [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, 0, 1), ztop)]
    return poly(planes, mat, vous=(cx, cz, ta, tb, ri), **kw)


# ================================================================ materials

def _moss(lv, x, z, seed):
    i = _clamp(round(1 + lv * 3.6 + (hsh(math.floor(x), math.floor(z), seed) - 0.5) * 1.2), 1, 5)
    return MOSS[i]


def marble(ramp=MARBLE, seed=1, moss=0.3, bias=0.0, veins=True):
    """Marble: fluted round a shaft (solid param flutes=n), weathered, rain-streaked and mossy
    near the ground and on tops; where it broke (param broken, or the inside of a wedge) rough,
    paler fresh stone."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        p = s.params
        lv = light + bias
        n = len(ramp)
        fresh = bool(p.get("fresh"))
        if p.get("broken"):
            if kind in ("top", "slope"):
                fresh = True
            elif p.get("cx") is not None and math.hypot(x - p["cx"], y - p["cy"]) < p["r"] - 0.9:
                fresh = True
        if fresh:
            g = hsh(math.floor(x), math.floor(y * 1.25), math.floor(z), seed)
            i = _ix(lv + 0.12, n) + (1 if g > 0.9 else -1 if g < 0.1 else 0)
            if vnoise(x + y, z + y, 2.0, seed + 7) < 0.2:
                i -= 1
            return ramp[_clamp(i, 1, n - 1)]
        i = _ix(lv, n)
        fl = p.get("flutes")
        a = None
        if kind == "wall" and p.get("cx") is not None:
            a = math.atan2(y - p["cy"], x - p["cx"])
        elif "axis" in p and kind != "top":
            p0, ax, e1, e2, r, L = p["axis"]
            w = np.array(P) - p0
            al = float(w @ ax)
            rad = w - al * ax
            if 0.4 < al < L - 0.4 and np.linalg.norm(rad) > r - 0.8:
                a = math.atan2(float(rad @ e2), float(rad @ e1))
            elif al <= 0.4 or al >= L - 0.4:  # a drum's flat end: scalloped rim, smooth band, rough middle, dowel hole
                c1, c2 = float(rad @ e1), float(rad @ e2)
                dd = math.hypot(c1, c2)
                b = math.atan2(c2, c1)
                j = _ix(lv - 0.12, n)
                if dd > r - 1.0:
                    if fl and ((b / (2 * math.pi) * fl + 50.0) % 1.0) < 0.4:
                        return ramp[_clamp(j - 2, 1, n - 1)]
                    return ramp[_clamp(j - 1, 1, n - 1)]
                if abs(c1) < 1.0 and abs(c2) < 1.0:
                    return ramp[1]  # the dowel hole
                if dd > r - 2.4:
                    return ramp[_clamp(j + 1, 1, n - 1)]
                g = hsh(math.floor(x), math.floor(z), math.floor(y), seed)
                return ramp[_clamp(j + (1 if g > 0.8 else -1 if g < 0.25 else 0), 1, n - 1)]
        if a is not None:
            if fl:
                ph = (a / (2 * math.pi) * fl + 50.0) % 1.0
                if ph < (0.2 if "axis" in p else 0.28):
                    i -= 1
                elif ph > 0.8 and lv > 0.55 and "axis" not in p:
                    i += 1
            if "axis" not in p and math.cos(a) > 0.86 and math.sin(a) < 0:
                i += 1  # light bounced back onto the shaded edge
        if kind == "wall" and "axis" not in p:
            if vnoise(x + 0.7 * y, z, 4.0, seed) < 0.18:
                i -= 1
            if veins:
                vv = (x * 0.8 + z + 3.0 * math.sin(z * 0.25 + x * 0.15 + seed)) % 13.0
                if vv < 0.7 and hsh(math.floor(z / 3), seed) < 0.6:
                    i -= 1
        elif kind == "top":
            g = hsh(math.floor(x), math.floor(y * 1.25), seed + 17)
            if g < 0.09 or vnoise(x, y, 3.0, seed + 2) < 0.16:
                i -= 1
            elif g > 0.96:
                i += 1
        z0, z1 = s.bbox[4], s.bbox[5]
        if kind == "wall":
            col = math.floor(x + y * 0.3)
            if hsh(col, seed + 3) < 0.14 and z > z1 - (2 + hsh(col, seed + 4) * (z1 - z0) * 0.6):
                i -= 1  # rain streaks from the top
            if moss and z < 6 and z - z0 < moss * (0.5 + vnoise(x, y, 2.5, seed + 5) * 4.5):
                return _moss(lv, x, z, seed)
        elif kind == "top" and moss:
            if vnoise(x, y, 2.6, seed + 9) * (0.7 + 0.3 * hsh(math.floor(x / 5), seed)) > 1.0 - moss * 0.55:
                return _moss(lv, x, y, seed)
        return ramp[_clamp(i, 1, n - 1)]
    return Mat(f)


def ashlar(ramp=RUIN, seed=1, moss=0.25, bias=0.05, streaks=True):
    """Dressed stone blocks: each solid is one block (box, chamfered or turned), with mortar on
    its lower and right edges, a lit upper and left edge, pitting, rain streaks and moss."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        p = s.params
        n = len(ramp)
        if "obox" in p:
            c, hh, R = p["obox"]
            q = R.T @ (np.asarray(P) - c)
            x0, x1, y0, y1, z0, z1 = -hh[0], hh[0], -hh[1], hh[1], -hh[2], hh[2]
            lx, ly, lz = q
        else:
            x0, x1, y0, y1, z0, z1 = p.get("blk", s.bbox)
            lx, ly, lz = x, y, z
        key = hsh(x0 * 3, y0 * 5, z0 * 7, seed)
        lv = light + bias + (key - 0.5) * 0.28
        i = _ix(lv, n)
        if kind == "top":
            a, b, a0, a1, b0, b1 = lx, ly, x0, x1, y0, y1
        elif kind == "side":
            a, b, a0, a1, b0, b1 = ly, lz, y0, y1, z0, z1
        else:
            a, b, a0, a1, b0, b1 = lx, lz, x0, x1, z0, z1
        g = hsh(math.floor(a), math.floor(b), seed + (3 if kind == "top" else 0))
        if g < 0.08:
            i -= 1
        elif g > 0.94:
            i += 1
        if kind == "wall" and "vous" in p:
            vcx, vcz, ta, tb, ri = p["vous"]
            rr = math.hypot(x - vcx, z - vcz)
            ang = math.atan2(z - vcz, x - vcx)
            if (ang - ta) * rr < 1.0:
                return ramp[1]
            if (tb - ang) * rr < 1.0 or rr < ri + 1.0:
                i += 1
        elif kind == "wall":
            if a1 - a < 1 or b - b0 < 1:
                return ramp[1]
            if a - a0 < 1 or b1 - b < 1:
                i += 1
        elif kind == "top":
            if a1 - a < 1:
                i -= 1
            if b1 - b < 1:
                i -= 1
        if streaks and kind == "wall":
            col = math.floor(lx)
            if hsh(col, key * 100, seed) < 0.18 and lz > z1 - 1 - hsh(col, seed + 2) * (z1 - z0) * 0.8:
                i -= 1
        if moss:
            if kind in ("top", "slope") and vnoise(x, y, 3.0, seed + 9) > 1.0 - moss * 0.9:
                return _moss(lv, x, y, seed)
            if kind == "wall" and z < (0.8 + vnoise(x, 0, 3.0, seed + 5) * 4.0) * moss * 2.4:
                return _moss(lv, x, z, seed)
        return ramp[_clamp(i, 1, n - 1)]
    return Mat(f)


def rough(ramp=ROCK, seed=1, moss=0.2, bias=0.0, lichen=True):
    """Rock: blotchy, grainy, with cracks, lichen spots and moss on the upper faces."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        n = len(ramp)
        lv = light + bias + (vnoise(x + y, z + y * 0.5, 4.0, seed) - 0.5) * 0.16
        i = _ix(lv, n)
        g = hsh(math.floor(x), math.floor(y * 1.25), math.floor(z), seed)
        if g < 0.06:
            i -= 1
        elif g > 0.95:
            i += 1
        cr = (x * 0.6 - z + 2.0 * math.sin(x * 0.3 + y * 0.2 + seed)) % 17.0
        if cr < 0.6 and hsh(math.floor(x / 4), math.floor(z / 4), seed) < 0.5:
            i -= 2
        if moss and kind != "wall" and light > 0.55 and vnoise(x, y + z, 3.5, seed + 9) > 1.0 - moss * 0.8:
            return _moss(lv, x, y, seed)
        if moss and kind == "wall" and z < 2.5 * moss * 3 * vnoise(x, y, 2.0, seed + 4):
            return _moss(lv, x, z, seed)
        if lichen and hsh(math.floor(x / 2), math.floor(z / 2), math.floor(y / 2), seed + 21) < 0.012:
            return "#b9b07a" if lv > 0.3 else "#8a845c"
        return ramp[_clamp(i, 1, n - 1)]
    return Mat(f)


def log_mat(seed=1, bark=BARK, end=ENDGRAIN, moss=0.0):
    """A log along its axis (cyl): furrowed bark round it, rings on the sawn ends."""
    def f(u, v, kind, light, P, s):
        p0, ax, e1, e2, r, L = s.params["axis"]
        w = np.asarray(P) - p0
        al = float(w @ ax)
        rad = w - al * ax
        d = float(np.linalg.norm(rad))
        if (al < 0.35 or al > L - 0.35) and d < r - 0.3:
            ring = math.floor(d * 1.3 + 0.6 * hsh(math.floor(d * 2), seed))
            if d > r - 1.0:
                return bark[2]
            c = end[3] if ring % 2 == 0 else end[2]
            if d < 0.8:
                c = end[1]
            if light < 0.3:
                c = end[max(0, end.index(c) - 1)]
            return c
        a = math.atan2(float(rad @ e2), float(rad @ e1))
        lv = light + 0.05
        i = _clamp(round(1 + lv * 4.2), 1, len(bark) - 1)
        fur = (a * r * 1.4 + hsh(math.floor(al / 3), seed) * 2) % 3.0
        if fur < 0.9:
            i -= 1
        if hsh(math.floor(al), math.floor(a * r), seed) < 0.1:
            i -= 1
        if moss and vnoise(al, a * r, 2.5, seed + 3) > 1 - moss and float(rad @ np.array([0, 0, 1.0])) > 0:
            return _moss(lv, al, a * r, seed)
        return bark[_clamp(i, 0, len(bark) - 1)]
    return Mat(f)


def timber(ramp=WOOD, seed=1, bias=0.1, grain_along="z"):
    """Rough-sawn timber with grain lines running along the beam and a few knots."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        if grain_along == "x":
            across, along = (z if kind != "top" else y), x
        else:
            across, along = (x if kind != "top" else x), z
        lv = light + bias + (hsh(math.floor(across), seed) - 0.5) * 0.12
        i = tone_i(ramp, lv)
        if hsh(math.floor(across), math.floor(along / 4), seed + 1) < 0.15:
            i -= 1
        if hsh(math.floor(across / 3), math.floor(along / 9), seed + 2) < 0.04:
            i -= 2
        return ramp[_clamp(i, 1, len(ramp) - 1)]
    return Mat(f)


def log_top(seed=1):
    """A stump: bark round the sides, rings on the sawn top."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        if kind == "top":
            dd = math.hypot(x - s.params["cx"], y - s.params["cy"])
            if dd > s.params["r"] - 0.9:
                return BARK[3]
            return ENDGRAIN[3] if math.floor(dd * 1.2) % 2 == 0 else ENDGRAIN[2]
        i = _clamp(round(1 + light * 4.2), 1, len(BARK) - 1)
        if (u % 3) < 0.9:
            i -= 1
        return BARK[_clamp(i, 0, len(BARK) - 1)]
    return Mat(f)


def tone_i(ramp, lv):
    return _clamp(round(2 + lv * (len(ramp) - 4)), 2, len(ramp) - 2)


def dark(colour_lo="#120e12", colour_hi="#2a2228"):
    """The inside of a cave or a tent: near black, a little lighter at the rim."""
    def f(u, v, kind, light, P, s):
        return colour_hi if light > 0.6 else colour_lo
    return Mat(f)


def granite(ramp=GRANITE, seed=1, moss=0.2, bias=0.05):
    """A dressed monolith of speckled granite, weathered darker down from its edges, mossy at
    the foot."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        n = len(ramp)
        lv = light + bias
        i = _ix(lv, n)
        g = hsh(math.floor(x), math.floor(y * 1.25), math.floor(z), seed)
        if g < 0.12:
            i -= 1
        elif g > 0.92:
            i += 1
        if kind == "wall" and vnoise(x + y, z, 5.0, seed + 3) < 0.2:
            i -= 1
        if moss and kind == "wall" and z < moss * (1 + vnoise(x, y, 2.5, seed + 5) * 6):
            return _moss(lv, x, z, seed)
        if moss and kind == "top" and vnoise(x, y, 2.5, seed + 9) > 1 - moss * 0.7:
            return _moss(lv, x, y, seed)
        return ramp[_clamp(i, 1, n - 1)]
    return Mat(f)


def tent_canvas(ramp=TENT, seed=1, patch=True):
    """Tent canvas: panels sewn across the slope, a seam down each, a patch, darker at the hem
    where it is damp and muddy."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        n = len(ramp)
        if kind in ("wall", "side"):
            return ramp[2 if light < 0.4 else 3]
        lv = light + 0.12
        i = _ix(lv, n)
        if P[2] > s.params.get("zr", 1e9) - 1.2:
            return ramp[_clamp(i - 1, 1, n - 1)]  # the ridge seam
        if (v % 7.0) < 0.9:
            return ramp[_clamp(i - 1, 1, n - 1)]
        if z < 1.6:
            i -= 1
        if patch and 4 < y < 10 and 7 < z < 12 and x < 0:
            if abs(y - 4.5) < 0.6 or abs(y - 9.5) < 0.6 or abs(z - 7.5) < 0.6 or abs(z - 11.5) < 0.6:
                return ramp[_clamp(i - 1, 1, n - 1)] if (math.floor(y) + math.floor(z)) % 2 else ramp[_clamp(i, 1, n - 1)]
            return ["#5b4a32", "#7f6845", "#9c8459", "#b49c6c", "#c9b17e", "#d9c393", "#e8d7ac"][_clamp(i, 1, n - 1)]
        if hsh(math.floor(x), math.floor(v), seed) < 0.05:
            i -= 1
        return ramp[_clamp(i, 1, n - 1)]
    return Mat(f)


def embers(seed=1):
    """The fire bed: grey ash with charcoal and glowing coals (they glow at night)."""
    ash = ["#3a3534", "#5d5654", "#857c78", "#a89f99"]

    def f(u, v, kind, light, P, s):
        x, y, z = P
        g = vnoise(x, y, 1.7, seed)
        if g > 0.66:
            return EMBER[3] if g > 0.78 else EMBER[2]
        if g < 0.3:
            return "#1f1a1a"
        return ash[_clamp(round(light * 3 + (hsh(math.floor(x), math.floor(y), seed) - 0.5)), 0, 3)]
    return Mat(f)


def cart_mat(seed=1):
    """A mine cart: dark planks bound with riveted iron at the corners and the rim."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        x0, x1, y0, y1, z0, z1 = s.bbox
        if kind == "top":
            return "#2a2222"
        lv = light + 0.1
        near_edge = (x - x0 < 1.6 or x1 - x < 1.6 or z1 - z < 1.4 or z - z0 < 1.0)
        if near_edge:
            c = IRON[2] if lv > 0.45 else IRON[1]
            if (math.floor(x) % 3 == 0 and z1 - z < 1.4) or (math.floor(z) % 3 == 0 and (x - x0 < 1.6 or x1 - x < 1.6)):
                return "#8a8794"  # rivets
            return c
        if (x - x0) % 4 < 0.8:
            return DARKWOOD[2]
        return DARKWOOD[_clamp(round(3 + lv * 2), 3, 5)]
    return Mat(f)


def ore(seed=1):
    """Lumps of rock and ore heaped in a cart."""
    def f(u, v, kind, light, P, s):
        x, y, z = P
        g = hsh(math.floor(x), math.floor(y), math.floor(z), seed)
        if g > 0.93:
            return "#e6c35a"  # a fleck of gold
        if g < 0.05:
            return "#7ec6d8"  # a crystal
        return ROCK[_clamp(round(1.5 + light * 4.2 + (g - 0.5)), 1, 6)]
    return Mat(f)


# ================================================================ 2D helpers

def on_solids(S, cv, sids):
    """A setter that only paints pixels of the given solids (keeps shadow tint)."""
    sids = set(sids)

    def put(x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < cv.w and 0 <= y < cv.h and S.sid[y, x] in sids:
            c = C(c)
            if cv.shadow[y, x]:
                c = _shade(c, 0.38)
            cv.px[x, y] = c
    return put


def sid_of(S, solid):
    return S.solids.index(solid)


def leaf(cv, x, y, lv, rnd, ramp=IVY, put=None):
    """A small leaf cluster (3-5 px): a lit top-left, a shaded bottom-right."""
    put = put or cv.set
    n = len(ramp)
    i = _clamp(round(2 + lv * 3), 2, n - 2)
    hi, mid, lo = ramp[i + 1], ramp[i], ramp[i - 1]
    shape = rnd.randrange(4)
    if shape == 0:
        pts = ((0, 0, hi), (1, 0, mid), (0, 1, mid), (1, 1, lo))
    elif shape == 1:
        pts = ((0, 0, hi), (-1, 0, mid), (0, 1, lo), (-1, 1, lo))
    elif shape == 2:
        pts = ((0, 0, mid), (1, 0, hi), (1, 1, mid), (0, 1, lo), (2, 1, lo))
    else:
        pts = ((0, -1, hi), (0, 0, mid), (1, 0, lo), (-1, 0, mid))
    for dx, dy, c in pts:
        put(x + dx, y + dy, c)


def ivy_spiral(cv, S, cx, cy, r, z0, z1, rnd, a0=-2.6, turns=0.9, density=0.75, flowers=0.0):
    """Ivy winding up a round shaft: the stem only shows on the near half, leaves cluster
    along it, lighter on the lit left."""
    steps = int((z1 - z0) * 3)
    last = None
    for k in range(steps):
        t = k / steps
        z = z0 + (z1 - z0) * t
        wob = 0.25 * math.sin(t * 17 + a0)
        a = a0 + turns * 2 * math.pi * t + wob
        if math.sin(a) > 0.12:
            last = None
            continue
        x, y = cx + (r + 0.3) * math.cos(a), cy + (r + 0.3) * math.sin(a)
        sx, sy = S.s(x, y, z)
        cv.set(sx, sy, IVY[2])
        lv = 0.85 - 0.6 * (math.cos(a) + 1) / 2
        if last is None or abs(z - last) > 1.3:
            if rnd.random() < density:
                leaf(cv, sx + rnd.choice((-1, 1)), sy + rnd.randint(-1, 1), lv, rnd)
                if flowers and rnd.random() < flowers:
                    pal = rnd.choice(BLOOM)
                    cv.set(sx + rnd.randint(-1, 1), sy - 1, pal[0])
            last = z


def ivy_hang(cv, x, y, length, rnd, lv=0.6, put=None):
    """A strand of ivy hanging down from (x, y), leaves to either side."""
    put = put or cv.set
    xx = x
    for j in range(length):
        if rnd.random() < 0.2:
            xx += rnd.choice((-1, 1)) if abs(xx - x) < 2 else (1 if xx < x else -1)
        put(xx, y + j, IVY[2] if j % 3 else IVY[1])
        if j % 2 == 0 and rnd.random() < 0.85:
            leaf(cv, xx + rnd.choice((-1, 1)), y + j, lv - j * 0.01, rnd, put=put)


def ivy_climb(cv, x, y0, y1, rnd, lv=0.6, spread=2, put=None):
    """Ivy climbing up a flat wall from y0 (bottom, screen) to y1 (top)."""
    put = put or cv.set
    xx = x
    for y in range(y0, y1, -1):
        if rnd.random() < 0.3:
            xx += rnd.choice((-1, 1))
            xx = max(x - spread, min(x + spread, xx))
        put(xx, y, IVY[1])
        if rnd.random() < 0.6:
            leaf(cv, xx + rnd.choice((-1, 0, 1)), y, lv, rnd, put=put)


def tuft(cv, x, y, rnd, h=4, ramp=GRASS):
    """A tuft of grass blades standing on screen row y."""
    for b in range(rnd.randint(3, 5)):
        bx = x + rnd.randint(-2, 2)
        bh = rnd.randint(max(1, h - 2), h)
        lean = rnd.choice((-1, 0, 0, 1))
        for j in range(bh):
            xx = bx + (lean if j > bh // 2 else 0)
            c = ramp[_clamp(1 + j * 3 // max(1, bh), 0, len(ramp) - 1)]
            cv.set(xx, y - j, c)


def flowers(cv, x, y, rnd, n=4, spread=4, pal=None):
    """A little clump of wild flowers on screen row y."""
    pal = pal or rnd.choice(BLOOM)
    for _ in range(n):
        fx, fh = x + rnd.randint(-spread, spread), rnd.randint(2, 4)
        for j in range(fh):
            cv.set(fx, y - j, GRASS[1] if j < fh - 1 else GRASS[2])
        cv.set(fx, y - fh, pal[0])
        if rnd.random() < 0.5:
            cv.set(fx + 1, y - fh, pal[0])
            cv.set(fx, y - fh - 1, pal[0])
        if rnd.random() < 0.4:
            cv.set(fx, y - fh, pal[1])


def crack(put, x, y, length, rnd, dark, light=None, dx=0):
    """A crack wandering down from (x, y)."""
    for j in range(length):
        put(x, y + j, dark)
        if light is not None:
            put(x + 1, y + j, light)
        if rnd.random() < 0.45:
            x += rnd.choice((-1, 1)) if dx == 0 else dx * rnd.choice((0, 1))


def plant(cv, S, rnd, plants):
    """Grass tufts and flower clumps standing on the ground in front of things: plants =
    [("tuft" | "flowers", x, y, size)], drawn without an outline, behind whatever is nearer."""
    for kind, x, y, n in plants:
        cv.at_depth(y - 0.5)
        if kind == "tuft":
            tuft(cv, S.sx(x), S.sy(y, 0), rnd, h=n)
        else:
            flowers(cv, S.sx(x), S.sy(y, 0), rnd, n=n, spread=max(2, n - 1))
    cv.free()


def finish(S, cv, kind, footprint, door_x=None, door_w=14, chims=(), extra=None, late=None, plants=(), rnd=None):
    """Outline, then draw the thin late parts (ropes, grass), then pack the result."""
    S.finish(cv)
    if plants:
        plant(cv, S, rnd or random.Random(7), plants)
    if late:
        late(cv)
    out = _result(cv, kind, (S.ox, S.base), footprint, S.sx(door_x) if door_x is not None else None, door_w,
                  [S.s(x, y, z) for x, y, z in chims])
    return out if extra is None else (*out, extra)


def fp(x0, x1, d, y0=0.0):
    """Footprint from x0..x1, from the base line back to depth d."""
    fd = max(2, round(K * d))
    return [round(x0), -fd, round(x1 - x0), fd]


# ================================================================ ruins: columns

def column(spec):
    """A marble temple column: a stepped plinth, a moulded base, a fluted shaft with real
    shading round it, a Doric capital with its abacus. Variants: vines (ivy winding up, hanging
    from the capital), broken (a short stump with a jagged, freshly broken top and rubble at its
    foot)."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    broken = spec.get("broken", False)
    vines = spec.get("vines", False)
    mos = spec.get("moss", 0.3)
    mar = marble(seed=seed, moss=mos)
    blk = marble(seed=seed + 1, moss=mos, veins=False)
    cy = 10
    h = spec.get("height", 38)
    S = Scene(pad_top=3, outline="#25212b")
    S.add(chamfered(-11, 11, 0, 20, 0, 3, blk, cuts=[("tf", 0.8)]))
    S.add(chamfered(-8.5, 8.5, 1.5, 18.5, 3, 7, blk, cuts=[("tf", 1.0)]))
    S.add(prism(0, cy, 7.8, 7, 8.6, mar, sides=32))
    S.add(prism(0, cy, 7.0, 8.6, 9.4, mar, sides=32))
    S.add(prism(0, cy, 6.6, 9.4, 10.5, mar, sides=32))
    shaft_ids = []
    z0s = 10.5
    if not broken:
        zt = z0s + h
        shaft_ids.append(S.add(frustum(0, cy, 6.1, 5.3, z0s, zt, mar, sides=32, flutes=12)))
        S.add(prism(0, cy, 5.8, zt, zt + 1.4, mar, sides=32))
        S.add(frustum(0, cy, 5.5, 7.6, zt + 1.4, zt + 4.4, mar, sides=32))
        S.add(chamfered(-7.8, 7.8, cy - 7.8, cy + 7.8, zt + 4.4, zt + 7.2, blk, cuts=[("tf", 0.7)]))
        top = zt + 7.2
        foot = fp(-11, 11, 20)
    else:
        r = 6.0
        n = 7
        ph = rnd.uniform(0, 1)
        hts = [h * 0.42 + rnd.uniform(-4, 4) for _ in range(n)]
        hts[rnd.randrange(n)] += 9
        for k in range(n):
            a0 = (k + ph) * 2 * math.pi / n
            a1 = (k + 1 + ph) * 2 * math.pi / n
            am = (a0 + a1) / 2
            tilt = (math.cos(am) * rnd.uniform(0.25, 0.6), math.sin(am) * rnd.uniform(0.25, 0.6))
            shaft_ids.append(S.add(sector(0, cy, r, a0, a1, z0s, z0s + hts[k], mar, tilt=tilt, flutes=12, broken=True)))
        top = z0s + max(hts)
        # rubble at its foot: chunks of marble (a fresh break on one or two), a fallen drum
        for k, (x, y, rx, ry, rz) in enumerate(((-13.5, 1, 2.6, 2.2, 2.0), (-10.5, -2.5, 1.3, 1.2, 1.0), (-15, 8, 1.8, 1.6, 1.5),
                                                (8, -2.5, 1.4, 1.3, 1.1), (-5, 21, 1.6, 1.4, 1.3))):
            S.add(rock(x, y, 0, rx, ry, rz, marble(seed=seed + 5 + k, moss=0.35, veins=False), seed=rnd.randint(1, 999), n=11,
                       fresh=k == 1))
        S.add(cyl((11, 5, 4.2), (21, 6, 4.2), 4.6, marble(seed=seed + 4, moss=0.3), sides=24, floor=0, flutes=12, broken=True))
        foot = fp(-15, 21, 20)
    cv = S.render()
    put = on_solids(S, cv, [sid_of(S, s) for s in shaft_ids])
    for k in range(rnd.randint(1, 2)):  # hairline cracks in the shaft
        x = S.sx(rnd.uniform(-3.5, 2.5))
        crack(put, x, S.sy(cy - 6, top - 6 - rnd.uniform(0, 8)), rnd.randint(5, 10), rnd, MARBLE[2])
    cv.free()
    if vines:
        ivy_spiral(cv, S, 0, cy, 6.0, 8, top - 6, rnd, a0=-2.9, turns=1.15, density=1.0, flowers=0.12)
        ivy_spiral(cv, S, 0, cy, 6.0, 9, top * 0.6, rnd, a0=-0.9, turns=0.6, density=0.9)
        ivy_spiral(cv, S, 0, cy, 6.0, 6, top * 0.35, rnd, a0=-2.0, turns=-0.5, density=1.0, flowers=0.2)
        put = on_solids(S, cv, range(len(S.solids)))
        for k in range(14):  # a mat of ivy over the plinth
            x = rnd.uniform(-8, 8)
            leaf(cv, S.sx(x), S.sy(1.5, rnd.uniform(3.5, 7.5)), 0.7 - (x + 8) / 40, rnd, put=put)
        for x in range(-7, 8, 2):
            if rnd.random() < 0.6:
                ivy_hang(cv, S.sx(x), S.sy(cy - 7.8, top - 2.8), rnd.randint(2, 9), rnd, lv=0.75 - (x + 8) / 30)
        for x in range(-7, 7, 2):  # ivy sprawling over the abacus
            if rnd.random() < 0.6:
                leaf(cv, S.sx(x), S.sy(cy + rnd.uniform(-7, 2), top), 0.85, rnd)
    # grass and a few flowers round the plinth
    plants = [("tuft", x + rnd.uniform(-1, 1), -0.5, rnd.randint(3, 5)) for x in range(-12, 13, 3) if rnd.random() < 0.6]
    if rnd.random() < 0.8 or vines:
        plants.append(("flowers", rnd.choice((-10, 9)), -1, 3))
    return finish(S, cv, "prop", foot, plants=plants, rnd=rnd)


def fallen_column(spec):
    """A fallen column in the grass: its shaft lies in two drums that came apart, a third drum
    rolled toward us showing its worn end (scalloped rim, smooth band, dowel hole), the capital
    tipped over at the far end, chips of marble, ivy, grass and flowers."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    S = Scene(pad_top=3, outline="#25212b")
    r = 5.2
    yaw = math.radians(spec.get("yaw", 5))
    d = np.array([math.cos(yaw), math.sin(yaw), 0.0])
    p = np.array([-15.0, 9.0, r - 0.5])
    shaft = []
    for k, ln in enumerate((10.5, 11.0)):
        shaft.append(S.add(cyl(p, p + d * ln, r, marble(seed=seed + k, moss=0.3), sides=28, floor=0, flutes=12)))
        p = p + d * (ln + 2.2)
    # the capital beyond, toppled upside down: abacus on the grass, echinus and a stub of shaft
    cx, cy = p[0] + 9.5, p[1] + 1.5
    cm = marble(seed=seed + 5, moss=0.45, veins=False)
    S.add(chamfered(cx - 7.4, cx + 7.4, cy - 7.4, cy + 7.4, 0, 2.8, cm, cuts=[("tf", 0.7)]))
    S.add(frustum(cx, cy, 7.4, 5.4, 2.8, 5.8, marble(seed=seed + 6, moss=0.2), sides=28))
    S.add(prism(cx, cy, 5.6, 5.8, 7.0, marble(seed=seed + 6, moss=0.0), sides=28))
    S.add(frustum(cx, cy, 5.3, 5.2, 7.0, 10.5, marble(seed=seed + 6, moss=0.0), sides=28, flutes=12, broken=True))
    # a drum that rolled toward us, its end facing front
    roll = S.add(cyl((-21, -1, r - 0.5), (-20.2, 7, r - 0.5), r, marble(seed=seed + 3, moss=0.3), sides=28, floor=0, flutes=12))
    for k, (x, y, rx, ry, rz) in enumerate(((-9, 1, 1.6, 1.4, 1.3), (-12, -2, 1.1, 1.0, 0.9), (2, 2.5, 1.4, 1.3, 1.1),
                                            (21, 3, 1.5, 1.3, 1.2), (-3, 18, 1.4, 1.2, 1.1))):
        S.add(rock(x, y, 0, rx, ry, rz, marble(seed=seed + 7 + k, moss=0.2, veins=False), seed=rnd.randint(1, 999), n=11,
                   fresh=k in (1, 2)))
    cv = S.render()
    cv.free()
    for k in range(6):  # ivy creeping over the shaft
        q = np.array([-15.0, 9.0, 0]) + d * rnd.uniform(2, 22)
        sx, sy = S.s(q[0], q[1] + rnd.uniform(-1, 3), 2 * r - 0.6)
        leaf(cv, sx, sy, 0.8, rnd)
    plants = [("tuft", x + rnd.uniform(-1, 1), y, rnd.randint(3, 6))
              for x, y in ((-16, -2.5), (-6, 1.5), (5, 2.5), (12, 3.5), (25, 6), (-27, 4), (-1, 17))]
    plants += [("flowers", -4, 1, 4), ("flowers", 17, 3, 3)]
    return finish(S, cv, "prop", fp(-26, 26, 18), plants=plants, rnd=rnd)


# ================================================================ ruins: walls, an archway, an obelisk

def _profile(pts, x):
    for (xa, ha), (xb, hb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ha + (hb - ha) * (x - xa) / (xb - xa)
    return pts[0][1] if x < pts[0][0] else pts[-1][1]


def ruin_wall(spec):
    """A crumbling stretch of dressed-stone wall: courses of blocks with a ragged, stepped top
    (each block a solid, so the broken top shows its depth), a window whose round arch still
    stands on the left while the right side has fallen, fallen blocks and rubble in front, moss
    on the tops, ivy climbing and hanging, grass and flowers along its foot."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    W = spec.get("width", 64)
    ramp = spec.get("ramp", RUIN)
    X0, X1 = -W / 2, W / 2
    y0, y1 = 4.0, 12.0
    ch = 6.0
    wx0, wx1 = -11.0, 1.0
    wxc, ri, ro = (wx0 + wx1) / 2, (wx1 - wx0) / 2, (wx1 - wx0) / 2 + 4
    spring = 4 * ch
    prof = spec.get("profile", [(X0, 5.6), (X0 + 6, 6.0), (wxc + ro + 0.5, 6.0), (wxc + ro + 1, 4.6), (12, 3.6), (20, 2.4),
                                (X1, 1.3)])
    S = Scene(pad=6, pad_top=4, outline="#221d1a")
    blocks = []
    for c in range(6):
        z0 = c * ch
        x = X0 - (0 if c % 2 == 0 else rnd.uniform(3, 6))
        while x < X1:
            ln = rnd.uniform(7, 12)
            bx0, bx1 = max(X0, x), min(X1, x + ln)
            x += ln
            pieces = [(bx0, bx1)]
            if 1 <= c < 4:
                cut = (wx0, wx1)
            elif c >= 4:
                cut = (wxc - ro, wxc + ro)
            else:
                cut = None
            if cut:
                pieces = [(a, min(b, cut[0])) for a, b in pieces if a < cut[0]] + [(max(a, cut[1]), b) for a, b in pieces if b > cut[1]]
            for a, b in pieces:
                if b - a < 1.5:
                    continue
                h = _profile(prof, (a + b) / 2) + rnd.uniform(-0.25, 0.25)
                if c + 1 <= h:
                    cuts = [("tf", rnd.uniform(0.4, 1.0))] if rnd.random() < 0.5 else []
                    zt = z0 + ch
                elif c < h:
                    frac = h - c
                    zt = z0 + ch * max(0.45, frac)
                    cuts = [(rnd.choice(("tl", "tr")), rnd.uniform(1.5, 3.0)), ("tf", rnd.uniform(0.8, 1.6))]
                else:
                    continue
                jy = rnd.uniform(-0.35, 0.35)
                blocks.append(S.add(chamfered(a, b, y0 + jy, y1, z0, zt, ashlar(ramp, seed=seed, moss=0.28), cuts=cuts)))
    # the sill, and the window's arch: three wedge stones left, the rest fallen
    S.add(chamfered(wx0 - 1.5, wx1 + 1.5, y0 - 1.2, y1, 4.8, 6.4, ashlar(ramp, seed=seed + 2, moss=0.3, bias=0.12),
                    cuts=[("tf", 0.6)]))
    nv = 7  # the arch: wedge stones bonded into the courses; the two on its right shoulder have fallen
    tops = {2: 33.5, 3: 36, 4: 36, 5: 36, 6: 36}
    for k in range(2, nv):
        ta, tb = k * math.pi / nv, (k + 1) * math.pi / nv
        S.add(voussoir(wxc, spring, y0, y1, ri, ta, tb, ashlar(ramp, seed=seed + 3 + k, moss=0.25, bias=0.1 if k == 3 else 0.04),
                       rect=(wxc - ro, wxc + ro, tops[k]), front=0.6 if k == 3 else 0.3))
    # fallen blocks and rubble in front, under the broken end
    fb = ashlar(ramp, seed=seed + 5, moss=0.35)
    S.add(obox((12, 1.5, 2.2), (4.5, 2.8, 2.5), rot(yaw=0.35, roll=0.12), fb))
    S.add(obox((22, 0.5, 2.0), (3.6, 3.2, 2.4), rot(yaw=-0.5, pitch=0.25), fb))
    S.add(obox((27, 15, 2.6), (4.0, 3.0, 2.6), rot(yaw=0.2, roll=-0.2), fb))
    for k, (x, y, r_) in enumerate(((6.5, 1.0, 1.4), (17, -1.5, 1.2), (30, 3, 1.5), (-1, 2.0, 1.0), (16.5, 4.0, 1.3))):
        S.add(rock(x, y, 0, r_ * 1.2, r_, r_, rough(ramp, seed=seed + 11 + k, moss=0.3), seed=rnd.randint(1, 999), n=10))
    cv = S.render()
    cv.free()
    # ivy: climbing the tall left end, spilling over its top, hanging from the sill
    ivy_climb(cv, S.sx(X0 + 5), S.sy(y0, 1), S.sy(y0, 33), rnd, lv=0.75, spread=3)
    ivy_climb(cv, S.sx(X0 + 11), S.sy(y0, 1), S.sy(y0, 18), rnd, lv=0.65, spread=2)
    for x in range(int(X0) + 1, -17, 2):
        if rnd.random() < 0.75:
            ivy_hang(cv, S.sx(x), S.sy(y0, 36), rnd.randint(2, 9), rnd, lv=0.7)
            leaf(cv, S.sx(x), S.sy(y0 + rnd.uniform(1, 7), 36), 0.85, rnd)
    for x in (wx0 + 1, wx0 + 4, wx1 - 2):
        if rnd.random() < 0.8:
            ivy_hang(cv, S.sx(x), S.sy(y0 - 1.2, 4.8), rnd.randint(2, 4), rnd, lv=0.6)
    plants = [("tuft", x + rnd.uniform(-1, 1), y0 - 0.6, rnd.randint(3, 6)) for x in range(int(X0), int(X1), 4) if rnd.random() < 0.7]
    plants += [("flowers", X0 + 8, y0 - 1, 4), ("flowers", -3, y0 - 1, 3), ("tuft", 9, -1.5, 4), ("tuft", 25, -2.5, 5),
               ("flowers", 19, -3, 3)]
    return finish(S, cv, "prop", fp(X0, X1, y1), plants=plants, rnd=rnd)


def ruin_arch(spec):
    """A ruined stone archway you can walk through: two piers of coursed blocks, moulded
    imposts, an arch of nine wedge stones with a projecting keystone, the stumps of the wall it
    once carried on its haunches, a fallen stone, cracks, moss, ivy climbing one pier and
    trailing from the arch."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    ramp = spec.get("ramp", RUIN)
    y0, y1 = 2.0, 12.0
    px0, px1 = 12.0, 23.0  # pier from the opening's edge to the outside
    ch = 6.0
    S = Scene(pad=6, pad_top=4, outline="#221d1a")
    st = lambda k, b=0.05: ashlar(ramp, seed=seed + k, moss=0.25, bias=b)
    for side in (-1, 1):
        a, b = (-px1, -px0) if side < 0 else (px0, px1)
        for c in range(4):
            z0, z1 = c * ch, (c + 1) * ch
            if c % 2 == 0:
                parts = [(a, b)]
            else:
                m = (a + b) / 2 + rnd.uniform(-1.5, 1.5)
                parts = [(a, m), (m, b)]
            for pa, pb in parts:
                cuts = [("tf", rnd.uniform(0.4, 1.0))] if rnd.random() < 0.6 else []
                if side > 0 and c == 3 and pb == b:
                    cuts.append(("tr", 2.2))
                S.add(chamfered(pa, pb, y0 + rnd.uniform(-0.3, 0.3), y1, z0, z1, st(c + (5 if side > 0 else 0)), cuts=cuts))
        S.add(chamfered(a - 1.2, b + 1.2, y0 - 1.2, y1 + 1.2, 24, 26.5, st(20, 0.15), cuts=[("tf", 1.0)]))
    spring, ri, ro = 26.5, px0, px0 + 5.5
    n = 9
    for k in range(n):
        ta, tb = k * math.pi / n, (k + 1) * math.pi / n
        key = k == n // 2
        S.add(voussoir(0, spring, y0, y1, ri, ta, tb, st(30 + k, 0.08 if not key else 0.14), ro=ro + (2.2 if key else 0),
                       front=1.0 if key else 0.0))
    # the stumps of the wall over the haunches
    S.add(chamfered(-px1, -18.0, y0, y1, spring, spring + 6, st(40), cuts=[("tf", 0.8)]))
    S.add(chamfered(-px1, -17.2, y0 + 0.4, y1, spring + 6, spring + 10, st(41), cuts=[("tr", 2.5), ("tf", 1.2)]))
    S.add(chamfered(18.3, px1, y0, y1, spring, spring + 4.5, st(42), cuts=[("tl", 2.0), ("tf", 1.0)]))
    # a fallen stone and rubble
    S.add(obox((19, -3.2, 2.2), (3.6, 2.6, 2.2), rot(yaw=0.45, roll=0.15), st(50)))
    for k, (x, y, r_) in enumerate(((-17, -2, 1.3), (27, 2, 1.5), (14.5, -5, 0.9), (-27, 6, 1.2))):
        S.add(rock(x, y, 0, r_ * 1.2, r_, r_, rough(ramp, seed=seed + 60 + k, moss=0.3), seed=rnd.randint(1, 999), n=10))
    cv = S.render()
    cv.free()
    for k in range(2):  # cracks in the right pier
        put = on_solids(S, cv, range(len(S.solids)))
        crack(put, S.sx(rnd.uniform(14, 21)), S.sy(y0, rnd.uniform(14, 22)), rnd.randint(4, 8), rnd, ramp[1])
    ivy_climb(cv, S.sx(-19), S.sy(y0, 1), S.sy(y0, 30), rnd, lv=0.75, spread=3)
    ivy_climb(cv, S.sx(-14), S.sy(y0, 1), S.sy(y0, 14), rnd, lv=0.6, spread=2)
    for t in (0.62, 0.7, 0.78, 0.86, 0.52, 0.3):  # ivy trailing from the arch
        a = math.pi * t
        x, z = ri * math.cos(a), spring + ri * math.sin(a)
        ivy_hang(cv, S.sx(x), S.sy(y0, z), rnd.randint(3, 10 if t > 0.5 else 5), rnd, lv=0.65)
    for k in range(8):
        a = math.pi * rnd.uniform(0.45, 0.95)
        x, z = (ro + 0.5) * math.cos(a), spring + (ro + 0.5) * math.sin(a)
        leaf(cv, S.sx(x), S.sy(y0 + rnd.uniform(0, 6), z), 0.85, rnd)
    plants = [("tuft", x + rnd.uniform(-1, 1), y0 - 0.6, rnd.randint(3, 6)) for x in (-24, -21, -16, -13, 13, 16, 21, 24)]
    plants += [("tuft", -8, 6, 3), ("tuft", 7, 9, 3), ("flowers", -22, y0 - 1, 4), ("flowers", 23, y0 - 1, 3)]
    out = finish(S, cv, "prop", fp(-px1, px1, y1), plants=plants, rnd=rnd)
    out[2]["passage"] = [-round(px0), round(px0)]  # the opening between the piers (screen x from the base point)
    return out


GLYPHS = [["x.x", ".x.", "x.x", "..."], ["xxx", "x.x", "xxx", "..."], [".x.", "xxx", ".x.", ".x."], ["x..", "xxx", "..x", "..."],
          ["xx.", ".x.", ".xx", "..."], ["x.x", "xxx", "x.x", "..."], [".x.", "x.x", ".x.", "..."], ["xxx", ".x.", "xxx", "..."],
          ["x..", "x..", "xxx", "..."], ["..x", ".x.", "x..", "xxx"]]
RUNE = ["..x..", ".xxx.", "x.x.x", "..x..", ".x.x.", "x...x", "..x.."]
BRONZE = ["#16231f", "#24413a", "#336052", "#4a816c", "#6aa58a", "#97c9ab", "#cbe8d6"]


def obelisk(spec):
    """A tall granite obelisk on three steps, tapering to a verdigris bronze cap, carved with
    columns of glyphs; a rune inlaid with gold in the middle glows faintly at night. Moss on the
    steps, grass and flowers round them."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    ramp = spec.get("ramp", GRANITE)
    cy = 14.0
    S = Scene(pad=5, pad_top=6, outline="#1b1a22")
    for k, (hw, d0, d1, z0, z1) in enumerate(((15, 0, 28, 0, 3), (12, 2.5, 25.5, 3, 6), (9, 5, 23, 6, 9))):
        xs = [-hw, -hw / 3 + rnd.uniform(-2, 2), hw / 3 + rnd.uniform(-2, 2), hw]
        for a, b in zip(xs, xs[1:]):
            S.add(chamfered(a, b, d0, d1, z0, z1, ashlar(ramp, seed=seed + k, moss=0.3, bias=0.08),
                            cuts=[("tf", rnd.uniform(0.5, 1.0))]))
    zt = spec.get("height", 56)
    shaft = S.add(frustum(0, cy, 5.6, 3.6, 9, zt, granite(ramp, seed=seed, moss=0.25), sides=4, rot=math.pi / 4))
    S.add(spire(0, cy, 3.7, zt, zt + 7, M.flat(BRONZE, 0.05)))
    cv = S.render()
    put = on_solids(S, cv, [sid_of(S, shaft)])

    def front_y(z):
        return cy - (5.6 - (5.6 - 3.6) * (z - 9) / (zt - 9))

    def carve(x, z, pattern):
        for j, row in enumerate(pattern):
            for i, ch_ in enumerate(row):
                if ch_ == "x":
                    sx, sy = S.s(x + i, front_y(z - j), z - j)
                    put(sx, sy, ramp[1])
                    if j + 1 >= len(pattern) or pattern[j + 1][i] != "x":
                        put(sx, sy + 1, ramp[5])
    rz = (zt + 9) / 2 + 2
    for col in (-3.2, 0.6):
        z = zt - 4
        while z > 13:
            if abs(z - rz) > 5.5:
                carve(col, z, GLYPHS[rnd.randrange(len(GLYPHS))])
            z -= 5
    # the rune: gold inlay in a carved ring, glowing at night
    rx, ry = S.s(0, front_y(rz), rz)
    for y in range(ry - 5, ry + 6):
        for x in range(rx - 4, rx + 5):
            dd = (x - rx) ** 2 + (y - ry) ** 2
            if 16 <= dd <= 24:
                put(x, y, ramp[1] if (x - rx) + (y - ry) < 0 else ramp[2])
                cv.lit(x, y, LIT[0])
    for j, row in enumerate(RUNE):
        for i, ch_ in enumerate(row):
            if ch_ == "x":
                x, y = rx - 2 + i, ry - 3 + j
                put(x, y, GOLD[3] if (i + j) % 3 else GOLD[4])
                cv.lit(x, y, LIT[4] if j in (2, 3, 4) and i in (1, 2, 3) else LIT[3])
    for (x, y) in ((rx - 3, ry - 4), (rx + 3, ry - 4), (rx - 4, ry + 1), (rx + 4, ry + 1), (rx, ry + 5), (rx, ry - 5)):
        cv.lit(x, y, LIT[1])
    crack(on_solids(S, cv, range(len(S.solids))), S.sx(7), S.sy(2.5, 5.5), 4, rnd, ramp[1])
    cv.free()
    for x in (-14, -9, 11):  # moss and ivy spilling down the steps
        ivy_hang(cv, S.sx(x), S.sy(5, 9), rnd.randint(2, 6), rnd, lv=0.7)
    plants = [("tuft", x + rnd.uniform(-1, 1), -0.6, rnd.randint(3, 6)) for x in range(-15, 16, 3) if rnd.random() < 0.6]
    plants += [("flowers", -12, -1, 4), ("flowers", 13, -1, 3)]
    return finish(S, cv, "prop", fp(-15, 15, 28), plants=plants, rnd=rnd)


# ================================================================ a forest shrine

def _figure(cv, cx, bottom, put=None):
    """A small carved robed figure with a halo, hands holding a flower."""
    put = put or cv.set
    st = ["#5d5752", "#8f8780", "#bdb5aa", "#ddd5c8", "#f2ebdf"]
    rows = [(-1, 1), (-2, 2), (-2, 2), (-1, 1), (-2, 2), (-3, 2), (-3, 3), (-3, 3), (-3, 3), (-4, 3), (-4, 4), (-4, 4)]
    top = bottom - len(rows) - 1
    for j, (a, b) in enumerate(rows):
        for i in range(a, b + 1):
            c = st[4] if i <= a + 1 and j > 3 else st[3] if i < 0 else st[2] if i < b else st[1]
            if j < 4:  # the hooded head
                c = st[3] if i < 0 else st[2]
                if j == 2 and i in (-1, 0):
                    c = st[1]
            put(cx + i, top + j, c)
    put(cx, top + 6, BLOOM[1][0])
    put(cx - 1, top + 6, "#5fa047")
    for i in range(-3, 4):  # halo
        put(cx + i, top - 2, GOLD[3] if i < 1 else GOLD[2])
    put(cx - 3, top - 1, GOLD[2])
    put(cx + 3, top - 1, GOLD[1])
    for i in range(-5, 6):  # little pedestal
        put(cx + i, bottom, st[3] if i < 3 else st[1])
        put(cx + i, bottom + 1, st[1])


def _candle(cv, x, bottom, h=3, put=None):
    put = put or cv.set
    for y in range(bottom - h, bottom):
        put(x, y, "#f1ead8" if y > bottom - h else "#fff7e8")
    put(x, bottom - h - 1, "#ffcf6a")
    put(x, bottom - h - 2, "#fff2b8")
    cv.lit(x, bottom - h - 1, LIT[4])
    cv.lit(x, bottom - h - 2, LIT[3])
    cv.lit(x, bottom - h, LIT[2])


def shrine(spec):
    """A small stone wayside shrine in the woods: a niche under a mossy shingled gable roof with a
    carved figure, candles inside and on the rough offering stone in front (they glow at night),
    a bowl of fruit, a flower garland over the niche, wild flowers all round."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    ramp = spec.get("ramp", RUIN)
    st = lambda k, b=0.08: ashlar(ramp, seed=seed + k, moss=0.3, bias=b)
    S = Scene(pad=6, pad_top=4, outline="#221c19")
    S.add(chamfered(-10.5, 10.5, 8, 21, 0, 4, st(1), cuts=[("tf", 0.8)]))
    S.add(chamfered(-9, -5.5, 9, 19.5, 4, 21, st(2)))
    S.add(chamfered(5.5, 9, 9, 19.5, 4, 21, st(3)))
    back = S.add(box(-5.5, 5.5, 16.5, 19.5, 4, 21, st(4, -0.05)))
    S.add(chamfered(-9.6, 9.6, 8.4, 19.8, 21, 23.6, st(5, 0.15), cuts=[("tf", 0.7)]))
    from town3d import gable_front
    zr_w, zr = gable_front(S, -9.6, 9.6, 8.6, 19.8, 23.6, 0.72, M.shingles(ROOFS[spec.get("roof", "moss")], seed=seed, row_h=3, moss=0.15),
                           st(6), over=2.5, th=1.6)
    off = S.add(rock(0, 3.2, 0, 7.0, 3.4, 3.0, rough(ramp, seed=seed + 9, moss=0.25, lichen=True), seed=seed + 3, n=14, top=3.0))
    cv = S.render()
    # inside the niche: the figure on the back wall, candles on the niche floor
    bid = sid_of(S, back)
    fig = []

    def put_fig(x, y, c):
        if 0 <= x < cv.w and 0 <= y < cv.h and S.sid[y, x] == bid:
            cv.px[x, y] = C(c)
            fig.append((x, y))
    _figure(cv, S.sx(0), S.sy(16.5, 5.5), put=put_fig)
    cv.free()
    cands = []
    for x in (-3.8, 3.8):
        cv.at_depth(13)
        _candle(cv, S.sx(x), S.sy(13, 4), h=3 if x < 0 else 2)
        cands.append((S.sx(x), S.sy(13, 4) - 4))
    figs = set(fig)
    for y in range(cv.h):  # candlelight in the niche at night
        for x in range(cv.w):
            if S.sid[y, x] != bid or (x, y) in figs:
                continue
            dd = min(math.hypot(x - a, y - b) for a, b in cands)
            if dd < 4.5:
                cv.lit(x, y, LIT[0])
    for (x, y) in fig:
        r, g, b, a = cv.px[x, y]
        if (r, g, b) in (C(GOLD[3])[:3], C(GOLD[2])[:3]):
            cv.lit(x, y, LIT[2])
        elif r > 215 and (x + y) % 2 == 0:
            cv.lit(x, y, LIT[0])
    # the garland over the niche
    cv.free()
    gx0, gx1 = S.sx(-8.5), S.sx(8.5)
    gy = S.sy(8.3, 21.5)
    for x in range(gx0, gx1 + 1):
        t = (x - gx0) / (gx1 - gx0)
        y = gy + round(3 * math.sin(t * math.pi))
        cv.set(x, y, IVY[3] if x % 2 else IVY[4])
        if x % 3 == 0:
            cv.set(x, y + 1, BLOOM[(x // 3) % 4][0])
            cv.set(x, y, BLOOM[(x // 3) % 4][1] if x % 2 else BLOOM[(x // 3) % 4][0])
    # offerings on the stone: candles, a bowl of apples, a posy
    cv.at_depth(2)
    oy = S.sy(3.2, 3.0)
    _candle(cv, S.sx(-5), oy + 1, h=3)
    _candle(cv, S.sx(-3.5), oy, h=2)
    _candle(cv, S.sx(5.5), oy + 1, h=4)
    bx = S.sx(0)
    for i in range(-3, 4):
        cv.set(bx + i, oy, "#6b4a2a" if i > 1 else "#8a6239")
        cv.set(bx + i, oy - 1, "#a87a48" if i < 1 else "#8a6239")
    for gx in (-2, 0, 2):
        item(cv, bx + gx - 1, oy - 1, "apple")
    for k, x in enumerate((2, 3, 4)):
        cv.set(bx + x, oy - 1 - k % 2, BLOOM[3][0])
    put = on_solids(S, cv, range(len(S.solids)))
    for k in range(6):  # moss and ivy up the corners
        leaf(cv, S.sx(rnd.choice((-9, 8))), S.sy(9, rnd.uniform(4, 14)), 0.7, rnd, put=put)
    plants = [("flowers", -13, 9, 4), ("flowers", 12, 10, 4), ("flowers", -9, -0.5, 3), ("flowers", 9, -0.5, 3),
              ("tuft", -12, 5, 5), ("tuft", 12, 5, 4), ("tuft", -7, -1, 3), ("tuft", 7, -1.5, 4), ("tuft", 0, -1.5, 3)]
    return finish(S, cv, "prop", fp(-10.5, 10.5, 21), plants=plants, rnd=rnd)


# ================================================================ a mine entrance

def _pick(cv, x, y, flip=False):
    """A pickaxe leaning on something: handle from (x, y) up and to the left, iron head on top."""
    d = -1 if not flip else 1
    for j in range(13):
        cv.set(x + d * (j // 3), y - j, WOOD[4] if j % 4 else WOOD[2])
    hx, hy = x + d * 4, y - 13
    for i, (dx, dy) in enumerate(((-4, 2), (-3, 1), (-2, 0), (-1, 0), (0, -1), (1, 0), (2, 0), (3, 1), (4, 2))):
        cv.set(hx + dx, hy + dy, IRON[2] if dx < 1 else IRON[1])
        if dy <= 0:
            cv.set(hx + dx, hy + dy - 1, "#9a97a3" if dx < 0 else IRON[2])


def mine(spec):
    """A mine entrance cut into a mound of rock: a timber frame (posts, a heavy lintel, braces)
    round the dark opening with rails running into the gloom, a lamp glowing far inside and a
    lantern on the post at night, the rails curving out to a cart heaped with ore, a pickaxe
    against the frame, a sign over the door."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    rk = lambda k, m=0.25: rough(ROCK, seed=seed + k, moss=m)
    S = Scene(pad=5, pad_top=4, outline="#1a1615")
    S.add(rock(0, 34, 0, 38, 24, 26, rk(0, 0.3), seed=seed + 1, n=22, jag=0.12, lift=0.45))
    S.add(rock(-12, 36, 22, 14, 11, 9, rk(8, 0.35), seed=seed + 9, n=14))
    S.add(rock(13, 40, 20, 12, 10, 8, rk(9, 0.35), seed=seed + 10, n=14))
    S.add(rock(-28, 14, 0, 15, 13, 17, rk(1), seed=seed + 2, n=16))
    S.add(rock(29, 16, 0, 14, 12, 14, rk(2), seed=seed + 3, n=16))
    S.add(rock(-17, 8, 0, 8, 6, 9, rk(3), seed=seed + 4, n=14))
    S.add(rock(17, 8, 0, 8, 6, 8, rk(4), seed=seed + 5, n=14))
    S.add(rock(1, 10, 21, 17, 8, 7, rk(5, 0.35), seed=seed + 6, n=16, lift=0.4))
    S.add(rock(-36, 4, 0, 5, 4, 4, rk(6), seed=seed + 7, n=12))
    S.add(rock(38, 6, 0, 4, 3.5, 3.5, rk(7), seed=seed + 8, n=12))
    hole = S.add(box(-9, 9, 3, 30, 0, 21, dark()))
    tmv = timber(DARKWOOD, seed=seed, grain_along="z")
    S.add(box(-12, -9, 0, 3, 0, 22, tmv))
    S.add(box(9, 12, 0, 3, 0, 22, tmv))
    S.add(box(-14.5, 14.5, -0.5, 3.2, 21.5, 25, timber(DARKWOOD, seed=seed + 1, grain_along="x")))
    # the cart on the siding, heaped with ore
    S.add(tub(21, 34, -19, -12, 2.6, 9.4, 1.0, cart_mat(seed)))
    for k, (x, y, rr) in enumerate(((23.5, -15.5, 2.8), (27.5, -15, 3.2), (31.5, -15.5, 2.6), (25.5, -14, 2.2))):
        S.add(rock(x, y, 8.6, rr, 2.4, rr * 0.75, ore(seed + k), seed=seed + 20 + k, n=10))
    cv = S.render()
    # the dark inside: gloom deepening from the mouth, a set of timbers further in, rails into the dark
    hid = sid_of(S, hole)
    x0, x1 = S.sx(-9), S.sx(9)
    yb, yt = S.sy(3, 0), S.sy(3, 21)
    for y in range(yt, yb):
        for x in range(x0, x1):
            if S.sid[y, x] != hid:
                continue
            u = abs(x + 0.5 - (x0 + x1) / 2) / ((x1 - x0) / 2)
            v = (y - yt) / (yb - yt)
            dd = max(u, 1 - v * 1.3)
            cv.px[x, y] = C("#3a302c" if dd > 0.93 else "#251e1d" if dd > 0.78 else "#161112" if dd > 0.5 else "#0b0809")
    for y in range(yt + 5, yb - 2):  # inner frame
        for x in (x0 + 4, x1 - 5):
            cv.set(x, y, "#3b2a1f")
    for x in range(x0 + 4, x1 - 4):
        cv.set(x, yt + 5, "#3b2a1f")
    vx, vy = (x0 + x1) // 2, yt + 9
    for k, bx in enumerate((x0 + 3, x1 - 4)):
        for i in range(0, 40):
            t = i / 40
            x, y = round(bx + (vx + (k * 2 - 1) - bx) * t), round(yb - 1 + (vy - yb) * t)
            if y < vy + 1:
                break
            cv.set(x, y, "#6b6670" if t < 0.4 else "#3d3a42")
    for y in range(vy + 2, yb, 2):
        t = (yb - y) / (yb - vy)
        w = round(8 * (1 - t)) + 1
        for x in range(vx - w, vx + w + 1):
            if cv.px[x, y][:3] != C("#6b6670")[:3]:
                cv.set(x, y, "#2e2420")
    cv.set(vx - 1, vy - 1, "#ffcf6a")  # a lamp far inside
    cv.lit(vx - 1, vy - 1, LIT[3])
    for dx, dy in ((-1, 0), (0, -1), (-2, -1), (-1, -2)):
        cv.lit(vx - 1 + dx, vy - 1 + dy, LIT[0])
    # braces in the frame's corners, the sign over the door
    for i in range(4):
        cv.set(S.sx(-9) + i, S.sy(0, 21) + 3 - i, DARKWOOD[4])
        cv.set(S.sx(9) - 1 - i, S.sy(0, 21) + 3 - i, DARKWOOD[3])
    sx0, sy0 = S.sx(-6), S.sy(-0.5, 25) - 6
    for y in range(sy0, sy0 + 6):
        for x in range(sx0, sx0 + 12):
            edge = x in (sx0, sx0 + 11) or y in (sy0, sy0 + 5)
            cv.set(x, y, TRIM[1] if edge else TRIM[3] if y == sy0 + 1 else TRIM[2])
    for i in range(4):  # crossed picks
        cv.set(sx0 + 4 + i, sy0 + 1 + i, IRON[1])
        cv.set(sx0 + 7 - i, sy0 + 1 + i, IRON[1])
    cv.set(sx0 + 3, sy0 + 1, IRON[2])
    cv.set(sx0 + 8, sy0 + 1, IRON[2])
    lantern(cv, S.sx(12) + 2, S.sy(0, 15))
    # rails out of the mouth, curving onto the siding where the cart stands
    path = [(0.0, 3.0 - i * 0.5) for i in range(15)]
    for i in range(1, 25):
        th = math.pi + (math.pi / 2) * i / 24
        path.append((9 + 9 * math.cos(th), -4 + 9 * math.sin(th)))
    path += [(9 + i * 0.5, -13.0) for i in range(1, 60)]
    for k, (px_, py_) in enumerate(path):
        if k + 1 < len(path):
            dx, dy = path[k + 1][0] - px_, path[k + 1][1] - py_
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        cv.at_depth(py_ - 0.2)
        if k % 6 == 0:
            for s in range(-5, 6):
                q = S.s(px_ + nx * s * 0.75, py_ + ny * s * 0.75, 0)
                cv.set(q[0], q[1], DARKWOOD[3] if s < 3 else DARKWOOD[2])
        for side in (-3, 3):
            q = S.s(px_ + nx * side, py_ + ny * side, 0)
            cv.set(q[0], q[1], "#9a97a3")
            cv.set(q[0], q[1] + 1, IRON[1])
    cv.at_depth(-19.5)  # the cart's wheels
    for wx in (24, 31):
        cx_, cy_ = S.s(wx, -19.5, 2.4)
        for y in range(cy_ - 2, cy_ + 3):
            for x in range(cx_ - 2, cx_ + 3):
                dd = (x - cx_) ** 2 + (y - cy_) ** 2
                if dd <= 5:
                    cv.set(x, y, IRON[2] if dd <= 1 else IRON[0] if dd > 3 else IRON[1])
    cv.free()
    _pick(cv, S.sx(-13), S.sy(-1, 0))
    for k in range(9):  # grass and a bush or two clinging to the mound
        x = rnd.uniform(-30, 30)
        col = [y for y in range(cv.h) if S.sid[y, S.sx(x)] >= 0]
        if col:
            yy = col[0] + rnd.randint(2, 6)
            tuft(cv, S.sx(x), yy, rnd, h=rnd.randint(2, 4))
            if k % 3 == 0:
                for j in range(5):
                    leaf(cv, S.sx(x) + rnd.randint(-3, 3), yy - rnd.randint(0, 3), 0.75, rnd, ramp=GRASS + ["#c3e68f"])
    for (gx, gy) in ((-3, 3), (3, 2), (-6, 6)):  # flecks of ore spilt by the mouth
        q = S.s(gx, -2 - gy * 0.3, 0)
        cv.set(q[0], q[1], "#e6c35a" if gx > 0 else ROCK[4])
    plants = [("tuft", x, y, rnd.randint(3, 5)) for x, y in ((-30, -4), (-22, -1), (-40, 1), (20, -1), (36, -1), (42, 3), (-34, 6))]
    plants += [("flowers", -26, -3, 3)]
    out = finish(S, cv, "house", fp(-42, 42, 44), door_x=0, door_w=16, plants=plants, rnd=rnd)
    return out


# ================================================================ camp: tent, fire

def tent(spec):
    """An A-frame canvas tent: two canvas slopes from a ridge to the ground, the left door flap
    laced shut, the right one rolled and tied back on the dim inside with a bedroll and a lantern
    hanging from the ridge (it glows at night), crossed poles at the apex, guy ropes to pegs, a
    patched panel, a pack by the door."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    ramp = {"khaki": TENT, "green": TENT_GREEN, "red": TENT_RED}[spec.get("colour", "khaki")]
    hw, d, zr = 14.0, 24.0, 21.0
    ze, th = 1.4, 1.3
    S = Scene(pad=12, pad_top=6, outline="#221c15")
    floor_ = S.add(box(-hw + 1, hw - 1, 0, d, 0, 0.4, M.flat(["#1b1712", "#231e17", "#2f281f", "#3a3226", "#463c2d"])))
    back = S.add(gable_y(-hw + 1, hw - 1, d - 0.8, d, 0.3, 0.4, zr - 1.5, M.flat(["#1d1814", "#2a231b", "#352c22", "#3f3528", "#4a3f30"], -0.2)))
    for sl in roof_shell_y(-hw, hw, -1, d + 1, ze, zr, th, tent_canvas(ramp, seed)):
        S.add(sl)
    p = (zr - ze) / hw
    S.add(poly([((-1, 0, 0), hw - 0.3), ((1, 0, 0), -0.4), ((0, -1, 0), 0.4), ((0, 1, 0), 0.4), ((0, 0, -1), 0),
                ((-p, 0, 1), (ze - th) + p * hw)], tent_canvas(ramp, seed + 1, patch=False), panel=True))
    cv = S.render()
    put_in = on_solids(S, cv, [sid_of(S, floor_), sid_of(S, back)])
    # inside: a bedroll and a lantern, the glow at night
    cv.at_depth(10)
    for y in range(S.sy(10, 0.4) - 4, S.sy(10, 0.4)):
        for x in range(S.sx(2), S.sx(11)):
            put_in(x, y, CLOTH["red"][3] if y == S.sy(10, 0.4) - 4 else CLOTH["red"][2] if y < S.sy(10, 0.4) - 1 else CLOTH["red"][1])
    for y in range(S.sy(10, 0.4) - 4, S.sy(10, 0.4)):
        put_in(S.sx(2), y, "#d8cfb8")
        put_in(S.sx(3), y, "#b5a98f")
    ix, iy = S.s(2.5, 9, zr - 2)
    for y in range(iy, iy + 3):
        cv.set(ix, y, "#4a4038")
    for yy in range(iy + 3, iy + 7):
        for xx in range(ix - 1, ix + 2):
            frame = yy in (iy + 3, iy + 6) or xx != ix
            cv.set(xx, yy, IRON[1] if frame else "#f3dc9a")
            if not frame:
                cv.lit(xx, yy, LIT[4])
    for y in range(cv.h):
        for x in range(cv.w):
            if S.sid[y, x] in (sid_of(S, floor_), sid_of(S, back)) and cv.px[x, y][3]:
                dd = math.hypot(x - ix, (y - iy - 5) * 0.8)
                if dd < 4:
                    cv.lit(x, y, LIT[1])
                elif S.sid[y, x] == sid_of(S, back) or dd < 8:
                    cv.lit(x, y, LIT[0])
    cv.free()
    # the right flap rolled up along its edge and tied, the lacing on the closed left one
    ax_, ay_ = S.s(0, -1, zr)
    ex_, ey_ = S.s(hw, -1, ze)
    n = ex_ - ax_
    for y in range(ay_ + 1, ey_ + 1):
        t = (y - ay_) / max(1, ey_ - ay_)
        xe = round(ax_ + (ex_ - ax_) * t)
        w = 2 + round(2.4 * math.sin(t * math.pi))
        for k in range(w):
            cv.set(xe - k, y, ramp[5] if k == 0 else ramp[4] if k < w - 1 else ramp[2])
    tx, ty = ax_ + n // 2, round(ay_ + (ey_ - ay_) * 0.5)
    cv.set(tx - 2, ty + 3, "#5c4632")
    cv.set(tx - 3, ty + 4, "#5c4632")
    for k, y in enumerate(range(S.sy(-0.4, 3), S.sy(-0.4, zr - 3), -3)):
        cv.set(S.sx(-1.2), y, "#5c4632")
        cv.set(S.sx(-2), y - 1, "#5c4632")
    # crossed poles at the front and back apex
    for (px_, py_) in (S.s(0, -1, zr), S.s(0, d + 1, zr)):
        for i in range(1, 4):
            cv.set(px_ - i, py_ - i, WOOD[4])
            cv.set(px_ + i, py_ - i, WOOD[3])
    # a pack by the door
    cv.at_depth(-4)
    bx, by = S.sx(hw + 3), S.sy(-4, 0)
    for y in range(by - 7, by):
        for x in range(bx, bx + 6):
            if (x, y) in ((bx, by - 7), (bx + 5, by - 7)):
                continue
            cv.set(x, y, "#6b4a2a" if x > bx + 3 else "#8a6239" if y > by - 6 else "#a87a48")
    for x in range(bx + 1, bx + 5):
        cv.set(x, by - 4, "#4a2f1f")
    cv.set(bx + 2, by - 3, BRASS_)
    cv.free()

    def late(cv):
        from market import rope
        rope(cv, ax_ - 1, ay_ + 1, S.sx(-hw - 10), S.sy(-7, 0), 1.0)
        rope(cv, ax_ + 1, ay_ + 1, S.sx(hw + 10), S.sy(-7, 0), 1.0)
        bx_, by_ = S.s(0, d + 1, zr)
        rope(cv, bx_ - 1, by_, S.sx(-hw - 8), S.sy(d + 5, 0), 0.8)
        rope(cv, bx_ + 1, by_, S.sx(hw + 8), S.sy(d + 5, 0), 0.8)
        for (x, y) in ((-hw - 1.5, -1.5), (hw + 1.5, -1.5), (-hw - 1.5, d / 2), (hw + 1.5, d / 2)):
            q = S.s(x, y, 0)
            cv.set(q[0], q[1], DARKWOOD[1])
            cv.set(q[0], q[1] - 1, DARKWOOD[4])
    plants = [("tuft", x, y, rnd.randint(3, 5)) for x, y in ((-hw - 2, -1), (hw - 3, -2), (-6, -2), (hw + 9, 3), (-hw - 6, 8))]
    plants += [("flowers", -hw - 4, 2, 3)]
    return finish(S, cv, "prop", fp(-hw, hw, d + 1), plants=plants, rnd=rnd, late=late)


FIRE = ["#c84003", "#f07a03", "#f5b003", "#ffd403", "#fff003"]  # all blue 3: they glow at night


def flame_sheet(n=8, w=17, h=24, seed=1):
    """Frames of a camp fire's flames, tongues licking up and swaying, a few sparks rising."""
    rnd = random.Random(seed)
    tongues = [(rnd.uniform(-3.5, 3.5), rnd.uniform(9, 17), rnd.uniform(2.0, 3.4), rnd.choice((1, 2, 3)), rnd.uniform(0, 6.3))
               for _ in range(5)]
    tongues.append((0.0, 19.0, 4.0, 1, 0.0))
    sheet = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    px = sheet.load()
    for f in range(n):
        t = f / n * 2 * math.pi
        base = h - 2
        for j in range(h):
            for i in range(w):
                dx = i + 0.5 - w / 2
                hg = base - j + 0.5
                val = 0.0
                for ox, H, Wd, sp, ph in tongues:
                    Hk = H * (0.72 + 0.28 * math.sin(t * sp + ph))
                    if hg < 0 or hg > Hk:
                        continue
                    sway = 1.3 * math.sin(t * sp + ph + hg * 0.4) * (hg / Hk)
                    half = Wd * (1 - (hg / Hk) ** 1.4) + 0.3
                    dd = abs(dx - ox - sway)
                    if dd < half:
                        val = max(val, (1 - dd / half) * (1 - 0.6 * hg / Hk) + 0.15)
                if val <= 0.08:
                    continue
                c = FIRE[4] if val > 0.8 else FIRE[3] if val > 0.6 else FIRE[2] if val > 0.4 else FIRE[1] if val > 0.22 else FIRE[0]
                px[f * w + i, j] = C(c)
        for k in range(3):  # sparks
            sy = base - 14 - ((f * 2 + k * 5) % 9)
            sx = round(w / 2 + 3 * math.sin(k * 2.1 + f * 0.7))
            if 0 <= sy < h:
                px[f * w + sx, sy] = C(FIRE[3] if k % 2 else FIRE[2])
    return sheet


def campfire(spec):
    """A camp fire: a ring of stones round a bed of ash and coals, split logs leant together over
    it, animated flames (an 8-frame sprite in lamplight colours, so it glows at night), the coals
    and the inside of the ring glowing too, smoke from the game; a log to sit on and a stump."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    cy = 10.0
    S = Scene(pad=6, pad_top=6, outline="#1e1814")
    S.add(prism(0, cy, 7.5, 0, 0.6, embers(seed), sides=20))
    ring = []
    nst = 11
    for k in range(nst):
        a = k * 2 * math.pi / nst + 0.2
        x, y = 9.5 * math.cos(a), cy + 8.0 * math.sin(a)
        ring.append(S.add(rock(x, y, 0, rnd.uniform(2.4, 3.0), rnd.uniform(2.0, 2.5), rnd.uniform(2.2, 2.8),
                               rough(FIELDSTONE_, seed=seed + k, moss=0.15), seed=seed * 31 + k, n=12)))
    logs = []
    for k in range(4):
        a = k * math.pi / 2 + 0.6
        p0 = (6.0 * math.cos(a), cy + 5.0 * math.sin(a), 0.9)
        p1 = (1.0 * math.cos(a), cy + 0.8 * math.sin(a), 7.0)
        logs.append(S.add(cyl(p0, p1, 1.2, log_mat(seed + k), sides=8)))
    S.add(cyl((-31, 3, 3.0), (-16, 8.5, 3.0), 3.3, log_mat(seed + 9, moss=0.2), sides=14, floor=0))
    S.add(prism(18, 8, 3.4, 0, 5, log_top(seed), sides=14))
    cv = S.render()
    fx, fy = S.s(0, cy, 0)
    for y in range(cv.h):  # firelight: coals, the ring's inner faces, the logs
        for x in range(cv.w):
            si = S.sid[y, x]
            if si < 0 or not cv.px[x, y][3]:
                continue
            sol = S.solids[si]
            dd = math.hypot(x - fx, (y - fy) * 1.25)
            if si == 0:
                r, g, b, a = cv.px[x, y]
                cv.lit(x, y, LIT[3] if r > 200 else LIT[1] if r > 150 else LIT[0])
            elif sol in ring and sol.params["rock"][1] > cy + 1 and dd < 11:
                cv.lit(x, y, LIT[1] if dd < 8 else LIT[0])
            elif sol in ring and dd < 9.5 and y < fy + 1:
                cv.lit(x, y, LIT[0])
            elif sol in logs:
                cv.lit(x, y, LIT[1] if dd < 4 else LIT[0])
    sheet = flame_sheet(8, 17, 24, seed)
    fcx, fcy = S.s(0, cy, 0)
    out = finish(S, cv, "prop", fp(-32, 22, 19), chims=[(0, cy, 20)], extra={"flame": sheet},
                 plants=[("tuft", x, y, rnd.randint(3, 5)) for x, y in ((-13, -1), (13, 0), (-24, -1), (22, 3), (-6, 20))],
                 rnd=rnd)
    info = out[2]
    info["flame"] = [fcx - S.ox, fcy - 10 - S.base]
    info["flame_frames"] = 8
    info["flame_fps"] = 8
    return out


# ================================================================ a watchtower

def watchtower(spec):
    """A wooden watchtower: four splayed legs braced with crossed timbers, a ladder up the front
    to a plank platform with railings, a little hipped shingle roof on corner posts, a lantern
    hanging under the eave (it glows at night) and a pennant on top."""
    rnd = random.Random(spec.get("seed", 1))
    seed = spec.get("seed", 1)
    S = Scene(pad=8, pad_top=12, outline="#21160f")
    wd = lambda k, b=0.1: timber(WOOD, seed=seed + k, bias=b)
    plat = 42.0
    legs = []
    for sx_ in (-1, 1):
        for sy_ in (0, 1):
            yb = 1.5 if sy_ == 0 else 21.5
            yt = 4.0 if sy_ == 0 else 19.0
            legs.append(S.add(cyl((sx_ * 12.0, yb, 0), (sx_ * 9.5, yt, plat), 1.6, wd(len(legs)), sides=4, phase=math.pi / 4)))
    def leg_at(sx_, sy_, z):
        t = z / plat
        x = sx_ * (12.0 + (9.5 - 12.0) * t)
        y = (1.5 + (4.0 - 1.5) * t) if sy_ == 0 else (21.5 + (19.0 - 21.5) * t)
        return np.array([x, y, z])
    br = lambda k: timber(DARKWOOD, seed=seed + 10 + k, bias=0.15)
    k = 0
    for za, zb in ((3, 21), (21, 39)):
        for sy_ in (0, 1):  # crossed braces front and back
            S.add(cyl(leg_at(-1, sy_, za) + (0, -0.6 if sy_ == 0 else 0.6, 0), leg_at(1, sy_, zb) + (0, -0.6 if sy_ == 0 else 0.6, 0), 0.7, br(k), sides=4))
            S.add(cyl(leg_at(1, sy_, za) + (0, -0.6 if sy_ == 0 else 0.6, 0), leg_at(-1, sy_, zb) + (0, -0.6 if sy_ == 0 else 0.6, 0), 0.7, br(k + 1), sides=4))
            k += 2
        for sx_ in (-1, 1):  # and on the sides
            S.add(cyl(leg_at(sx_, 0, za) + (sx_ * 0.6, 0, 0), leg_at(sx_, 1, zb) + (sx_ * 0.6, 0, 0), 0.7, br(k), sides=4))
            k += 1
    for z in (21,):
        for sy_ in (0, 1):
            S.add(cyl(leg_at(-1, sy_, z) + (0, -0.8 if sy_ == 0 else 0.8, 0), leg_at(1, sy_, z) + (0, -0.8 if sy_ == 0 else 0.8, 0), 0.9, br(30 + sy_), sides=4))
    S.add(box(-13.5, 13.5, 1, 22, plat, plat + 2.5, M.planks(WOOD, h=3, seed=seed + 3)))
    for x in (-13.5, 12, -1):
        for y in (1, 20.5):
            S.add(box(x, x + 1.5, y, y + 1.5, plat + 2.5, plat + 18, wd(40 + int(x) + int(y), 0.15)) if x != -1 else
                  box(x, x + 1.5, y, y + 1.2, plat + 2.5, plat + 9, wd(41)))
    for z0_ in (plat + 7.5, plat + 4.8):
        S.add(box(-13.5, 13.5, 1, 2.2, z0_, z0_ + 1.3, wd(50, 0.2)))
        S.add(box(-13.5, 13.5, 20.3, 21.5, z0_, z0_ + 1.3, wd(51, 0.2)))
        S.add(box(-13.5, -12.3, 1, 21.5, z0_, z0_ + 1.3, wd(52, 0.2)))
        S.add(box(12.3, 13.5, 1, 21.5, z0_, z0_ + 1.3, wd(53, 0.2)))
    roof = M.shingles(ROOFS[spec.get("roof", "rust")], seed=seed, row_h=3, moss=0.06)
    S.add(hip_x(-16.5, 16.5, -3, 25, plat + 16.5, plat + 18, plat + 33, 13.5, roof))
    # the ladder: two rails leaning from the ground in front up to the platform's edge
    for lx in (-3.0, 3.0):
        S.add(cyl((lx, -7, 0), (lx, 1.2, plat + 3.5), 0.7, wd(60, 0.2), sides=4))
    cv = S.render()
    cv.free()
    for z in range(3, int(plat) + 2, 3):  # rungs
        t = z / (plat + 3.5)
        y = -7 + 8.2 * t
        cv.at_depth(y - 0.8)
        a, b = S.s(-3, y, z), S.s(3, y, z)
        for x in range(a[0] + 1, b[0]):
            cv.set(x, a[1], WOOD[5] if x < a[0] + 3 else WOOD[4])
            cv.set(x, a[1] + 1, WOOD[2])
    cv.free()
    lx_, ly_ = S.s(8, -3.5, plat + 16)  # a lantern hung under the eave
    for y in range(ly_, ly_ + 3):
        cv.set(lx_, y, IRON[1])
    for yy in range(ly_ + 3, ly_ + 8):
        for xx in range(lx_ - 1, lx_ + 2):
            frame = yy in (ly_ + 3, ly_ + 7) or xx != lx_
            cv.set(xx, yy, IRON[1] if frame else "#f3dc9a")
            if not frame:
                cv.lit(xx, yy, LIT[4] if yy < ly_ + 6 else LIT[3])
    cv.set(lx_ - 1, ly_ + 2, IRON[2])
    cv.set(lx_ + 1, ly_ + 2, IRON[2])
    tx, ty = S.s(0, 11, plat + 33)
    for y in range(ty - 8, ty):
        cv.set(tx, y, IRON[2])
    pennant(cv, tx, ty - 7, CLOTH[spec.get("flag", "red")], right=True)
    plants = [("tuft", x, y, rnd.randint(3, 6)) for x, y in ((-13, 0), (12, 0), (-9, 20), (10, 21), (-6, -6), (6, -5))]
    plants += [("flowers", -16, 3, 3)]
    return finish(S, cv, "prop", fp(-13.5, 13.5, 23), plants=plants, rnd=rnd)


DESIGNS = {"column": column, "fallen_column": fallen_column, "ruin_wall": ruin_wall, "ruin_arch": ruin_arch,
           "obelisk": obelisk, "shrine": shrine, "mine": mine, "tent": tent, "campfire": campfire, "watchtower": watchtower}

ENTRIES = [
    {"id": "column", "name": "石柱", "group": GROUP, "type": "column", "seed": 1},
    {"id": "column_vines", "name": "藤蔓石柱", "group": GROUP, "type": "column", "seed": 2, "vines": True},
    {"id": "column_broken", "name": "断柱", "group": GROUP, "type": "column", "seed": 3, "broken": True},
    {"id": "column_fallen", "name": "倒塌石柱", "group": GROUP, "type": "fallen_column", "seed": 1},
    {"id": "ruin_wall", "name": "断墙", "group": GROUP, "type": "ruin_wall", "seed": 1},
    {"id": "ruin_arch", "name": "石门", "group": GROUP, "type": "ruin_arch", "seed": 1},
    {"id": "obelisk", "name": "方尖碑", "group": GROUP, "type": "obelisk", "seed": 1},
    {"id": "shrine", "name": "林间神龛", "group": GROUP, "type": "shrine", "seed": 1},
    {"id": "mine", "name": "矿洞口", "group": GROUP, "type": "mine", "seed": 1},
    {"id": "tent", "name": "帐篷", "group": GROUP, "type": "tent", "seed": 1},
    {"id": "campfire", "name": "篝火", "group": GROUP, "type": "campfire", "seed": 1},
    {"id": "watchtower", "name": "瞭望塔", "group": GROUP, "type": "watchtower", "seed": 1},
]
