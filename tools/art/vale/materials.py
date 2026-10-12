"""Pixel materials for the oblique renderer: each paints a solid from its surface coordinates
(see oblique.Mat): planks, boards, plaster, dressed stone, fieldstone, shingles, thatch, cloth
stripes, plain wood and metal. light is 0..1 from the face's angle to the sun (and shadow)."""
import math

from buildings import DARKWOOD, FIELDSTONE, PLASTER, STONE, TRIM, WOOD, tone
from oblique import Mat, flat, hsh  # flat is re-exported for the designs (M.flat)


def _t(ramp, v):
    return ramp[tone(ramp, v)]


def _step(ramp, v, k):
    i = max(1, min(len(ramp) - 1, tone(ramp, v) + k))
    return ramp[i]


def planks(ramp=WOOD, h=5, seed=1, bias=0.1):
    """Horizontal boards on walls (and on top faces, running across)."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            u, v = v, u
        row = math.floor(v / h)
        k = v - row * h
        off = hsh(row, seed) * 26
        seg = math.floor((u + off) / 26)
        uu = (u + off) - seg * 26
        lv = light + bias + (hsh(row, seg, seed + 3) - 0.5) * 0.14
        if k < 1:
            return ramp[1]
        if uu < 1:
            return ramp[1]
        if k >= h - 1:
            return _step(ramp, lv, 1)
        if uu < 2:
            return _step(ramp, lv, 1)
        if hsh(math.floor(u / 3), row, seed + 9) < 0.12 and 1 < k < h - 1:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def boards(ramp, w=5, seed=1, bias=0.1):
    """Vertical boards (barns, painted shops, sheds)."""
    def f(u, v, kind, light, P, s):
        col = math.floor(u / w)
        k = u - col * w
        lv = light + bias + (hsh(col, seed) - 0.5) * 0.1
        if k < 1:
            return _step(ramp, lv, 1)
        if k >= w - 1:
            return ramp[1]
        if hsh(col, math.floor(v / 4), seed) < 0.08:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def plaster(ramp=PLASTER, seed=1, bias=0.15, frame=None):
    """Plaster; with frame=(xs, zs) a dark timber frame of posts at xs and rails at zs."""
    def f(u, v, kind, light, P, s):
        if frame:
            xs, zs = frame
            for fx in xs:
                if fx <= u < fx + 3:
                    return DARKWOOD[4] if u < fx + 1 else DARKWOOD[3] if u < fx + 2 else DARKWOOD[1]
            for fz in zs:
                if fz <= v < fz + 3:
                    return DARKWOOD[4] if v >= fz + 2 else DARKWOOD[3] if v >= fz + 1 else DARKWOOD[1]
        lv = light + bias
        hv = hsh(math.floor(u), math.floor(v), seed)
        if hv < 0.05:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def dressed_stone(ramp=STONE, h=4, seed=1, bias=0.1):
    def f(u, v, kind, light, P, s):
        if kind == "top":
            u, v = u, v * 1.0
        row = math.floor(v / h)
        k = v - row * h
        off = hsh(row, seed) * 9
        seg = math.floor((u + off) / 7)
        uu = (u + off) - seg * 7
        lv = light + bias + (hsh(row, seg, seed) - 0.5) * 0.22
        if k < 1 or uu < 1:
            return ramp[1]
        if k >= h - 1 or uu < 2:
            return _step(ramp, lv, 1)
        return _t(ramp, lv)
    return Mat(f)


def fieldstone(ramp=FIELDSTONE, seed=1, bias=0.1):
    """Rounded stones of different sizes in rough courses."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + bias)
        row = math.floor(v / 5)
        hrow = 4 + math.floor(hsh(row, seed) * 3)
        k = v - row * 5
        off = hsh(row, seed + 1) * 11
        w = 6 + math.floor(hsh(row, math.floor((u + off) / 8), seed) * 4)
        seg = math.floor((u + off) / w)
        uu = (u + off) - seg * w
        lv = light + bias + (hsh(row, seg, seed + 2) - 0.5) * 0.3
        corner = (uu < 1.5 or uu > w - 1.5) and (k < 1 or k > 3.5)
        if k < 1 or uu < 1 or corner or k > hrow:
            return ramp[1]
        if k > 3 or uu < 2:
            return _step(ramp, lv, 1)
        if uu > w - 2 or k < 2:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def shingles(ramp, seed=1, row_h=4, trim=TRIM, moss=None):
    """Wooden shingles on slopes: rows up from the eaves, staggered, lit butt edges; the roof's
    vertical faces (fascia, gable ends) in trim wood; a ridge cap at the top."""
    def f(u, v, kind, light, P, s):
        if kind in ("wall", "side"):
            z = P[2]
            if z > s.params.get("ze", 0) - 1:
                return trim[2]
            return trim[3] if z > s.params.get("ze", 0) - 2.2 else trim[1]
        if kind == "top":
            return _t(ramp, light)
        if P[2] > s.params.get("zr", 1e9) - 1.6:
            return _step(ramp, light + 0.15, 1)  # ridge cap
        row = math.floor(v / row_h)
        k = v - row * row_h
        off = hsh(row, seed) * 7
        w = 4 + math.floor(hsh(row, math.floor((u + off) / 6), seed) * 3)
        seg = math.floor((u + off) / w)
        uu = (u + off) - seg * w
        lv = light + (hsh(row, seg, seed + 5) - 0.5) * 0.16
        if moss and hsh(row, seg, seed + 11) < moss and row < 4 and hsh(math.floor(u), math.floor(v * 2), seed) < 0.55:
            return ["#2f4a2a", "#46683a", "#62874a"][1 if light > 0.5 else 0]
        if k < 1:
            return _step(ramp, lv, 1)  # butt edge
        if k >= row_h - 1:
            return _step(ramp, lv, -2)  # shadow of the row above
        if uu < 1:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def thatch(ramp, seed=1):
    def f(u, v, kind, light, P, s):
        if kind in ("wall", "side"):
            return _t(ramp, light - 0.15 + (hsh(math.floor(u), seed) - 0.5) * 0.2)
        if P[2] > s.params.get("zr", 1e9) - 3:
            zig = (math.floor(u) + math.floor(P[2] * 2)) % 6 == 0
            return ramp[2] if zig else _t(ramp, light + 0.05)
        course = 6
        row = math.floor(v / course)
        k = v - row * course
        edge = 2 - abs((math.floor(u) + row * 2) % 5 - 2)
        strand = -0.12 if hsh(math.floor(u), math.floor(v / 2), seed) < 0.18 else 0.0
        lv = light + (hsh(math.floor(u), seed + 3) - 0.5) * 0.18 + strand
        if k <= edge * 0.6:
            return _step(ramp, lv + 0.12, 1)
        if k < edge * 0.6 + 1.2:
            return _step(ramp, lv, -2)
        return _t(ramp, lv)
    return Mat(f)


def stripes(a, b, w=4, seed=1, bias=0.1):
    """Canvas or cloth in stripes along u."""
    def f(u, v, kind, light, P, s):
        r = a if math.floor(u / w) % 2 == 0 else b
        lv = light + bias
        if (u % w) < 1:
            return _step(r, lv, 1)
        return _t(r, lv)
    return Mat(f)


def barrel(ramp=DARKWOOD, seed=1):
    """Staves round the sides with two iron hoops; a lid on top with its rim."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            cx, cy, r = s.params["cx"], s.params["cy"], s.params["r"]
            dd = math.hypot(P[0] - cx, (P[1] - cy))
            return ramp[5] if dd > r - 1.2 else _t(ramp, light + 0.05 + (0.1 if (math.floor(P[0]) % 3) else 0))
        z0 = s.bbox[4]
        h = s.bbox[5] - z0
        zz = P[2] - z0
        if abs(zz - h * 0.25) < 0.8 or abs(zz - h * 0.75) < 0.8:
            return ["#33313a", "#55525e", "#7a7784", "#9a97a3"][min(3, max(0, round(light * 3)))]
        lv = light + 0.15 + (hsh(math.floor(u / 2), seed) - 0.5) * 0.12
        if (u % 2) < 0.6:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def wood(ramp=WOOD, seed=1, bias=0.1):
    def f(u, v, kind, light, P, s):
        g = -0.1 if hsh(math.floor(u / 2), math.floor(v), seed) < 0.1 else 0.0
        return _t(ramp, light + bias + g)
    return Mat(f)


def chimney_stone(ramp=STONE, seed=1):
    """Stone courses on the sides, a dark flue in the top."""
    inner = dressed_stone(ramp, seed=seed)

    def f(u, v, kind, light, P, s):
        if kind == "top":
            x0, x1, y0, y1 = s.bbox[:4]
            if x0 + 1.5 < P[0] < x1 - 1.5 and y0 + 1.5 < P[1] < y1 - 1.5:
                return "#1b1716"
            return ramp[5]
        return inner.fn(u, v, kind, light, P, s)
    return Mat(f)


def crate(ramp=WOOD, seed=1):
    """A crate: boards inside a dark frame on every face."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1, z0, z1 = s.bbox
        if kind == "top":
            a, b, lo_a, hi_a, lo_b, hi_b = P[0], P[1], x0, x1, y0, y1
        else:
            a, b, lo_a, hi_a, lo_b, hi_b = P[0], P[2], x0, x1, z0, z1
        if a - lo_a < 1 or hi_a - a < 1 or b - lo_b < 1 or hi_b - b < 1:
            return _step(ramp, light, -2)
        if (b - lo_b) % 3 < 1:
            return _step(ramp, light, -1)
        return _t(ramp, light + 0.15)
    return Mat(f)


def cloth(ramp, seed=1, fold=5):
    """A cloth over a table: a smooth lit top, folds hanging down the sides to a wavy hem."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return _t(ramp, light + 0.12)
        k = u % fold
        lv = light + 0.1 + (0.12 if k < 1.5 else -0.12 if k > fold - 1.5 else 0)
        if P[2] - s.bbox[4] < 1 and (u % fold) > 1:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def swirl(a, b, w=6, seed=1):
    """Cloth in swirling diagonal bands of two colours."""
    def f(u, v, kind, light, P, s):
        band = math.floor((u + v * 1.3 + 4 * math.sin(u * 0.09)) / w) % 2
        r = a if band == 0 else b
        return _t(r, light + 0.12)
    return Mat(f)


def rug(ramp, gold=("#5e3f0e", "#9a6c18", "#d19f2c", "#f1cf5e", "#fff0a8")):
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        bx, by = min(P[0] - x0, x1 - P[0]), min(P[1] - y0, y1 - P[1])
        b = min(bx, by)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        diamond = abs(P[0] - cx) / max(1, (x1 - x0) / 2 - 3) + abs(P[1] - cy) / max(1, (y1 - y0) / 2 - 2) < 0.75
        if b < 1:
            return ramp[1]
        if b < 2:
            return gold[2]
        return ramp[3] if diamond else ramp[2]
    return Mat(f)


def well_stone(ramp=FIELDSTONE, seed=1):
    """A well's ring of stones; on top, the rim and the dark water inside."""
    side = fieldstone(ramp, seed=seed)

    def f(u, v, kind, light, P, s):
        if kind == "top":
            dd = math.hypot(P[0] - s.params["cx"], P[1] - s.params["cy"])
            if dd < s.params["r"] - 3:
                return "#1f2b33" if dd < s.params["r"] - 4 else "#2e3e48"
            return ramp[5] if (math.floor(math.atan2(P[1] - s.params["cy"], P[0] - s.params["cx"]) * 4) % 2) else ramp[4]
        return side.fn(u, v, kind, light, P, s)
    return Mat(f)


def canvas(ramp, rib=10):
    """A wagon's canvas cover with ribs showing through every `rib` px."""
    def f(u, v, kind, light, P, s):
        if kind in ("side", "wall"):
            return _t(ramp, light - 0.1)
        if (P[0] - s.bbox[0]) % rib < 1:
            return _step(ramp, light + 0.12, -1)
        return _t(ramp, light + 0.12)
    return Mat(f)
