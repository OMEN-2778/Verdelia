"""Street furniture modelled in 3D for the oblique renderer (see town3d.py and market3d.py):
street lamps whose glass glows at night, a slatted bench and a stone one, a notice board under
its own little roof, a signpost, flower beds, dry-stone wall pieces that join end to end, a
pillar post box, a barrel planter, stacked hay bales and a roofed woodpile.

Every piece has real tops and sides (seats, soil you look down into, wall copings, roofs); the
small things (flowers, papers, lettering, scrollwork, an axe in the chopping block) are drawn
in 2D afterwards at the depth they belong to. World units are pixels; x right, y back, z up; the
base point is the middle of the prop's front edge on the ground."""
import bisect
import math
import random

import numpy as np

import materials as M
from buildings import DARKWOOD, FIELDSTONE, IRON, LIT, ROOFS, STONE, TRIM, WOOD, _result, lantern, tone
from market import GOLD
from oblique import K, Mat, Scene, Solid, box, frustum, gable_x, hsh, prism, pyramid, slab

GROUP = "街道"


# ================================================================ palettes

LAMP_IRON = ["#111015", "#1a191f", "#24232b", "#302f39", "#413f4c", "#575463", "#77748a"]
BENCH_IRON = ["#101512", "#18201b", "#212c25", "#2c3a31", "#3a4b40", "#4f6455", "#6d8473"]
GLASS_DAY = ["#5a4418", "#8f6e2c", "#c9a75a", "#e6cd8a", "#f5e6b6", "#fff8e2"]
POST_RED = ["#240a0c", "#43110f", "#6e1a18", "#9a2622", "#bd372e", "#d9543f", "#ee8466"]
HAY7 = ["#3e2c0e", "#6b4f17", "#a8822a", "#c49b36", "#d9b54b", "#ecd174", "#f9ecb0"]
SOIL = ["#1a110a", "#2a1b10", "#3a2617", "#4a3220", "#5c3f29", "#6f4f35"]
STEMS = ["#173f22", "#215230", "#2c6a35", "#3d8240", "#5aa04a", "#7cbd5a"]
MOSS = ["#2f4a2a", "#46683a", "#62874a", "#7fa35a"]
TWINE = ["#4a2e14", "#7a4e22", "#a8743a"]
PAINTED = {  # sign boards: dark .. light
    "oak": ["#2a1a10", "#4a3020", "#6e4a2e", "#8e653e", "#a97d50", "#c49866", "#dcb787"],
    "cream": ["#4a3e2e", "#8a7a62", "#c2b294", "#dccdb0", "#ece2ca", "#f6f0e1", "#fdfaf2"],
    "green": ["#16261d", "#22392b", "#2f4f3b", "#3f664c", "#527e5f", "#6e9a78", "#93b89a"],
    "blue": ["#1b2433", "#2c3c55", "#405677", "#567196", "#738db0", "#97adc8", "#bfcfe0"],
}
BLOOMS = {  # dark, mid, light
    "red": ("#7a1622", "#cf3a44", "#ff7f7a"),
    "pink": ("#8a3a5e", "#e0709c", "#ffb2cc"),
    "yellow": ("#9a6e0e", "#efbd2a", "#fff07a"),
    "white": ("#8f8c9c", "#e4e2ec", "#ffffff"),
    "blue": ("#24347e", "#4c6cd8", "#9ab8ff"),
    "purple": ("#45236e", "#8650c0", "#c6a0f0"),
    "orange": ("#933a0c", "#ec7a22", "#ffbe6a"),
}


def _t(ramp, v):
    return ramp[tone(ramp, v)]


def _step(ramp, v, k):
    return ramp[max(1, min(len(ramp) - 1, tone(ramp, v) + k))]


# ================================================================ solids

def rotz(sol, ang, cx, cy):
    """The solid turned by ang (radians, anticlockwise seen from above) about the upright axis
    through (cx, cy): a board that points off at an angle."""
    ca, sa = math.cos(ang), math.sin(ang)
    planes = []
    for n, d in sol.planes:
        rn = np.array([n[0] * ca - n[1] * sa, n[0] * sa + n[1] * ca, n[2]])
        planes.append((rn, d - (n[0] * cx + n[1] * cy) + (rn[0] * cx + rn[1] * cy)))
    x0, x1, y0, y1, z0, z1 = sol.bbox
    xs, ys = [], []
    for x in (x0, x1):
        for y in (y0, y1):
            xs.append(cx + (x - cx) * ca - (y - cy) * sa)
            ys.append(cy + (x - cx) * sa + (y - cy) * ca)
    return Solid(planes, sol.mat, (min(xs), max(xs), min(ys), max(ys), z0, z1), **sol.params)


def arrow_board(xa, xb, y0, y1, z0, z1, tip, mat, **kw):
    """A plank from its square end xa to xb, where it comes to a point `tip` px long (pointing
    right when xb > xa, else left): a fingerpost arm."""
    hh = (z1 - z0) / 2
    s = 1 if xb > xa else -1
    planes = [((-s, 0, 0), -s * xa), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0), ((0, 0, 1), z1),
              ((s * hh, 0, tip), s * hh * xb + tip * z1), ((s * hh, 0, -tip), s * hh * xb - tip * z0)]
    lo, hi = (xa, xb + tip) if s > 0 else (xb - tip, xa)
    return Solid(planes, mat, (lo, hi, y0, y1, z0, z1), **kw)


def prism_y(cx, y0, y1, cz, r, mat, sides=12, **kw):
    """A cylinder lying along y, end on to the viewer (a log waiting to be split)."""
    planes = [((0, -1, 0), -y0), ((0, 1, 0), y1)]
    for i in range(sides):
        a = (i + 0.5) * 2 * math.pi / sides
        n = (math.cos(a), 0, math.sin(a))
        planes.append((n, r + n[0] * cx + n[2] * cz))
    return Solid(planes, mat, (cx - r, cx + r, y0, y1, cz - r, cz + r), **kw)


def battered(x0, x1, y0, y1, z0, z1, bx, by, mat, **kw):
    """A box whose sides lean in as they rise (bx px on each side across x, by along y): a
    dry-stone wall's batter, so the sides show as thin sloping faces."""
    h = z1 - z0
    ax, ay = bx / h, by / h
    planes = [((-1, 0, ax), -x0 + ax * z0), ((1, 0, ax), x1 + ax * z0), ((0, -1, ay), -y0 + ay * z0),
              ((0, 1, ay), y1 + ay * z0), ((0, 0, -1), -z0), ((0, 0, 1), z1)]
    return Solid(planes, mat, (x0, x1, y0, y1, z0, z1), **kw)


def pixels_of(S, sol, plane=None):
    """Screen pixels where a solid (one plane of it, if given) is the nearest surface."""
    si = S.solids.index(sol)
    m = S.sid == si
    if plane is not None:
        m &= S.pid == plane
    ys, xs = np.nonzero(m)
    return list(zip(xs.tolist(), ys.tolist()))


# ================================================================ materials

def drystone(ramp=FIELDSTONE, period=64, seed=1, bias=0.05):
    """Dry-stone walling: long flat stones laid in rough courses with deep dark joints (no
    mortar), each stone its own tone, a lit top edge, rounded corners. The pattern repeats every
    `period` px along u, so wall pieces join end to end."""
    rnd = random.Random(seed)
    rows, z = [], 0
    while z < 80:
        h = rnd.choice((3, 3, 4, 4, 5))
        off = rnd.uniform(0, period)
        joints, x = [0.0], 0.0
        while True:
            w = rnd.choice((3, 4, 5, 5, 6, 7, 8))
            if x + w > period - 3:
                break
            x += w
            joints.append(x)
        rows.append((z, h, off, joints, [rnd.uniform(-0.2, 0.2) for _ in joints]))
        z += h
    starts = [r[0] for r in rows]

    def f(u, v, kind, light, P, s):
        if kind == "top":  # the hearting seen from above: rubble in a coarse grid
            g = hsh(math.floor(u / 3), math.floor(v / 2.5), seed)
            if g < 0.18:
                return ramp[1]
            return _t(ramp, light + bias - 0.05 + (g - 0.5) * 0.3)
        r = rows[max(0, bisect.bisect_right(starts, v) - 1)]
        z0, h, off, joints, tones = r
        k = v - z0
        uu = (u - off) % period
        i = bisect.bisect_right(joints, uu) - 1
        loc = uu - joints[i]
        w = (joints[i + 1] if i + 1 < len(joints) else period) - joints[i]
        lv = light + bias + tones[i]
        if k < 1 or loc < 1:
            return ramp[0] if (k < 1 and loc < 1) else ramp[1]
        if (loc < 1.8 and k < 1.8) or (loc > w - 1 and k >= h - 1):
            return ramp[1]  # rounded corners leave dark gaps
        if k >= h - 1:
            return _step(ramp, lv, 1)
        if loc > w - 1.2:
            return _step(ramp, lv, -1)
        if hsh(math.floor(u), math.floor(v), seed + 5) < 0.05:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def coping(ramp=FIELDSTONE, seed=1):
    """Coping stones set on edge along a wall's top: each its own tone, a dark joint down one
    side, a lit top edge; a lichen spot here and there."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1, z0, z1 = s.bbox
        t = (hsh(round(x0 * 4), round(y0 * 4), seed) - 0.5) * 0.36
        lich = hsh(round(x0 * 4), round(y0 * 4), seed + 7) < 0.22
        if kind == "top":
            if lich and hsh(math.floor(P[0]), math.floor(P[1]), seed) < 0.4:
                return MOSS[2] if light > 0.5 else MOSS[1]
            return _t(ramp, light + 0.02 + t)
        if kind == "wall":
            if P[0] - x0 < 0.9:
                return ramp[1]
            if z1 - P[2] < 1:
                return _step(ramp, light + t, 1)
        else:
            if P[1] - y0 < 0.9 and y1 - y0 > 2:
                return ramp[1]
        if lich and hsh(math.floor(u), math.floor(v), seed + 2) < 0.3:
            return MOSS[1]
        return _t(ramp, light + 0.05 + t)
    return Mat(f)


def ashlar(ramp=STONE, seed=1, bias=0.15, top_bias=0.1):
    """Smooth dressed stone: plain faces with a faint speckle, a lit top edge on the fronts."""
    def f(u, v, kind, light, P, s):
        hv = hsh(math.floor(P[0]), math.floor(P[1] * 1.25), math.floor(P[2]), seed)
        lv = light + bias + (top_bias if kind == "top" else 0)
        if kind == "wall" and s.bbox[5] - P[2] < 0.9:
            return _step(ramp, lv, 1)
        if hv < 0.07:
            return _step(ramp, lv, -1)
        if hv > 0.95:
            return _step(ramp, lv, 1)
        return _t(ramp, lv)
    return Mat(f)


def lamp_glass():
    """Lamp glass by day: pale amber panes, brighter where they face the light, with a glint."""
    def f(u, v, kind, light, P, s):
        z0, z1 = s.bbox[4], s.bbox[5]
        k = (P[2] - z0) / max(1e-6, z1 - z0)
        if kind == "top":
            return GLASS_DAY[2]
        lv = 0.25 + light * 0.8 + 0.15 * k
        return _t(GLASS_DAY, lv)
    return Mat(f)


def slats(ramp=WOOD, pitch=2.5, seed=1, bias=0.1):
    """Slats running across (along x) with dark gaps between them going back: a bench seat."""
    def f(u, v, kind, light, P, s):
        lv = light + bias
        if kind == "top":
            y0 = s.bbox[2]
            row = math.floor((P[1] - y0) / pitch)
            k = (P[1] - y0) - row * pitch
            g = (hsh(math.floor(P[0] / 5), row, seed) - 0.5) * 0.12
            if k > pitch - 0.9:
                return ramp[1]
            if k < 1.0:
                return _step(ramp, lv + g, 1)
            if hsh(math.floor(P[0] / 2), row, seed + 4) < 0.1:
                return _step(ramp, lv + g, -1)
            return _t(ramp, lv + g)
        if kind == "wall" and s.bbox[5] - P[2] < 0.9:
            return _step(ramp, lv, 1)
        g = -0.1 if hsh(math.floor(u / 3), math.floor(v), seed) < 0.12 else 0.0
        return _t(ramp, lv + g)
    return Mat(f)


def board_mat(ramp, seed=1, bias=0.12):
    """A painted, weathered sign arm: a light top edge, a dark lower one, grain and wear."""
    def f(u, v, kind, light, P, s):
        lv = light + bias
        if kind != "wall":
            return _step(ramp, lv + 0.1, 1)
        z0, z1 = s.bbox[4], s.bbox[5]
        if z1 - P[2] < 1:
            return _step(ramp, lv, 1)
        if P[2] - z0 < 1:
            return _step(ramp, lv, -1)
        if hsh(math.floor(u / 3), math.floor(P[2]), seed) < 0.1:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def straw(ramp=HAY7, seed=1):
    """A bale of hay: straws streaking along its length, two bands of twine round it; the cut
    end (a bale turned end-on) bristles with straw ends."""
    def f(u, v, kind, light, P, s):
        x0, x1, y0, y1, z0, z1 = s.bbox
        along_x = (x1 - x0) >= (y1 - y0)
        L = (x1 - x0) if along_x else (y1 - y0)
        a = (P[0] - x0) if along_x else (P[1] - y0)
        lv = light + 0.12
        end_face = (kind == "wall" and not along_x)
        if not end_face:
            for tw in (0.26, 0.74):
                if abs(a - L * tw) < 0.7:
                    return TWINE[2] if light > 0.45 else TWINE[1]
        if end_face:  # straw ends: speckles
            hv = hsh(math.floor(P[0]), math.floor(P[2]), seed)
            if hv < 0.2:
                return _step(ramp, lv, -2)
            if hv > 0.85:
                return _step(ramp, lv, 1)
            return _t(ramp, lv + (hv - 0.5) * 0.25)
        b = P[2] if kind != "top" else P[1] if along_x else P[0]
        row = math.floor(b)
        seg = math.floor((a + hsh(row, seed) * 6) / 4)
        hv = hsh(row, seg, seed + 3)
        if hv < 0.16:
            return _step(ramp, lv, -1)
        if hv > 0.84:
            return _step(ramp, lv, 1)
        return _t(ramp, lv + (hv - 0.5) * 0.12)
    return Mat(f)


def split_logs(seed=1):
    """A stack of split firewood seen end on: rounds and halves in staggered rows, pale end grain
    lit at the top left, bark rims, dark gaps; bark along the top."""
    bark = ["#24170e", "#3a2618", "#523722", "#6b4a2e", "#83603c", "#9c774c"]
    grain = [["#7a5230", "#b4844e", "#d4a56a", "#ecc68e"], ["#6e4a2c", "#a87a48", "#c99a62", "#e2bb82"],
             ["#80603a", "#bc955e", "#d9b47c", "#f0d3a0"]]

    def f(u, v, kind, light, P, s):
        if kind != "wall":
            return _t(bark, light + (0.1 if math.floor(P[0] / 3) % 2 else -0.05))
        row = math.floor(v / 4)
        cw = 5
        uu = u + (2.5 if row % 2 else 0) + hsh(row, seed) * 3
        col = math.floor(uu / cw)
        cu = (uu - col * cw) - cw / 2 + 0.5
        cv = (v - row * 4) - 2
        e = (cu / 2.6) ** 2 + (cv / 2.1) ** 2
        g = grain[int(hsh(row, col, seed) * 3)]
        half = hsh(row, col, seed + 1) < 0.35  # a split half: flat side down
        if half and cv < -0.6:
            return bark[0]
        if e > 1.0:
            return bark[0] if e > 1.35 else bark[2]
        if e > 0.62:
            return bark[3] if cu + cv < 0 else bark[2]
        if e < 0.12 and not half:
            return g[0]
        return g[3] if cu + cv < -1 else g[2] if cu + cv < 1 else g[1]
    return Mat(f)


def ring_top(side, rim, inner, rim_w=1.6):
    """A round thing whose top shows a rim and something inside (soil): sides from `side`."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            dd = math.hypot(P[0] - s.params["cx"], P[1] - s.params["cy"])
            r = s.params["r"]
            if dd > r - rim_w:
                a = math.atan2(P[1] - s.params["cy"], P[0] - s.params["cx"])
                k = math.floor(a * r / 2.2) % 2
                return rim[4] if k else rim[3]
            if dd > r - rim_w - 0.9:
                return rim[1]
            back = P[1] > s.params["cy"]
            hv = hsh(math.floor(P[0]), math.floor(P[1]), 3)
            return inner[3] if (hv < 0.15 and not back) else inner[2] if not back else inner[1]
        return side.fn(u, v, kind, light, P, s)
    return Mat(f)


def log_end(cx, cz, r):
    """A log lying end on: rings of pale end grain on the face towards you, bark round it."""
    bark = ["#24170e", "#3a2618", "#523722", "#6b4a2e", "#83603c", "#9c774c"]

    def f(u, v, kind, light, P, s):
        if kind == "wall" and abs(P[1] - s.bbox[2]) < 0.6:
            dd = math.hypot(P[0] - cx, P[2] - cz)
            if dd > r - 0.7:
                return bark[2]
            if dd < 0.6:
                return "#8a6038"
            return "#e2bb82" if math.floor(dd * 1.3) % 2 else "#c99a62"
        return _t(bark, light + 0.15 + (0.1 if math.floor(P[1] / 2) % 2 else 0))
    return Mat(f)


def soil():
    def f(u, v, kind, light, P, s):
        hv = hsh(math.floor(P[0]), math.floor(P[1]), 11)
        return SOIL[4] if hv < 0.1 else SOIL[3] if hv < 0.45 else SOIL[2]
    return Mat(f)


def stave_tub(ramp=DARKWOOD, seed=1):
    """A half barrel: staves round the sides, iron hoops near the top and bottom."""
    def f(u, v, kind, light, P, s):
        zz = P[2] - s.bbox[4]
        h = s.bbox[5] - s.bbox[4]
        if abs(zz - 1.6) < 0.8 or abs(zz - (h - 1.8)) < 0.8:
            return ["#2a2830", "#44424c", "#66636f", "#8a8794"][min(3, max(0, round(light * 3)))]
        lv = light + 0.18 + (hsh(math.floor(u / 2.2), seed) - 0.5) * 0.14
        if (u % 2.2) < 0.7:
            return _step(ramp, lv, -1)
        return _t(ramp, lv)
    return Mat(f)


def stump_mat():
    """A chopping block: bark round the sides, pale rings on the cut top."""
    bark = ["#24170e", "#3a2618", "#523722", "#6b4a2e", "#83603c", "#9c774c"]
    ring = ["#6e4a2c", "#a87a48", "#c99a62", "#e2bb82", "#f0d3a0"]

    def f(u, v, kind, light, P, s):
        if kind == "top":
            dd = math.hypot(P[0] - s.params["cx"], (P[1] - s.params["cy"]))
            if dd > s.params["r"] - 0.9:
                return bark[3]
            return ring[2] if math.floor(dd * 1.1) % 2 else ring[3]
        g = 0.12 if (u % 3) < 1 else 0
        return _t(bark, light + g)
    return Mat(f)


# ================================================================ 2D parts

def blossom(cv, x, y, kind, col):
    """One bloom with its lowest pixel at (x, y): cup (tulip), star (daisy, with a gold eye),
    spike (lavender, lupin) or ball (marigold, geranium)."""
    d, m, l = col
    if kind == "cup":
        cv.set(x, y, m)
        cv.set(x + 1, y, d)
        cv.set(x, y - 1, l)
        cv.set(x + 1, y - 1, m)
    elif kind == "star":
        cv.set(x, y - 1, "#e8a92a")
        cv.set(x - 1, y - 1, l)
        cv.set(x + 1, y - 1, m)
        cv.set(x, y - 2, l)
        cv.set(x, y, m)
    elif kind == "spike":
        cv.set(x, y, d)
        cv.set(x, y - 1, m)
        cv.set(x, y - 2, l)
    else:  # ball
        cv.set(x, y, m)
        cv.set(x + 1, y, d)
        cv.set(x, y - 1, l)
        cv.set(x + 1, y - 1, l if kind == "ball" else m)
        cv.set(x - 1, y, d)


def plant(cv, S, rnd, z, rows, clumps, band=7, gap=(3, 4), stem=(1, 2), mound=None, spikes=()):
    """Plant a bed on soil at height z: rows = [(y, x0, x1), ...] from the back forwards.
    Each row gets a mat of leaves, then blooms on short stems; the flower changes every `band`
    px across, drifting a little row by row, so the bed reads as clumps of one flower each.
    mound = (cx, cy, r, extra) heaps the planting up towards the middle of a round tub; spikes =
    [(x, y, height, colour), ...] are tall flowers (lupins, foxgloves) set in among the rows."""
    spikes = sorted(spikes, key=lambda t: -t[1])
    for (y, x0, x1) in rows:
        while spikes and spikes[0][1] >= y:
            sx_, sy_, h, colour = spikes.pop(0)
            cv.at_depth(sy_)
            px, py = S.s(sx_, sy_, z)
            for k in range(h):
                cv.set(px, py - k, STEMS[3] if k % 2 else STEMS[2])
            d, m, l = BLOOMS[colour]
            for k, c in enumerate((d, m, d, m, l, l)):
                cv.set(px, py - h - k, c)
            cv.set(px + 1, py - h - 1, d)
            cv.set(px - 1, py - h - 2, m)
        cv.at_depth(y)
        sy = S.sy(y, z)
        a, b = S.sx(x0), S.sx(x1)
        for x in range(a, b):
            lift = 0
            if mound:
                mx, my, mr, extra = mound
                dd = ((x + 0.5 - S.sx(mx)) ** 2 + ((y - my) / 0.8) ** 2) / (mr * mr)
                lift = round(extra * max(0.0, 1 - dd))
            n = rnd.randint(1, 2) + lift
            for k in range(n):
                top = k == n - 1
                c = STEMS[4] if top and (x * 7 + round(y)) % 3 == 0 else STEMS[3] if top else STEMS[2]
                if k == 0 and not top:
                    c = STEMS[1]
                cv.set(x, sy - k, c)
        x = a + rnd.randint(0, 2)
        while x < b - 1:
            kind, colour = clumps[((x - S.ox + 64 + round(y * 0.6)) // band) % len(clumps)]
            lift = 0
            if mound:
                mx, my, mr, extra = mound
                dd = ((x + 0.5 - S.sx(mx)) ** 2 + ((y - my) / 0.8) ** 2) / (mr * mr)
                lift = round(extra * max(0.0, 1 - dd))
            h = rnd.randint(*stem) + lift
            for k in range(h):
                cv.set(x, sy - k, STEMS[3] if k else STEMS[2])
            blossom(cv, x, sy - h, kind, BLOOMS[colour])
            x += rnd.randint(*gap)


def scribble(cv, rnd, x0, x1, y, c, gap=0.25):
    """A line of tiny handwriting or painted lettering: words of dark pixels with gaps."""
    x = x0
    while x < x1:
        n = rnd.randint(2, 4)
        for i in range(n):
            if x + i < x1 and rnd.random() > gap * 0.4:
                cv.set(x + i, y, c)
        x += n + 1


def finial(cv, x, y, ramp=LAMP_IRON):
    """A little iron point with a ball on top of a cap at (x, y)."""
    cv.set(x, y - 1, ramp[4])
    cv.set(x, y - 2, ramp[5])
    cv.set(x - 1, y - 2, ramp[3])
    cv.set(x + 1, y - 2, ramp[2])
    cv.set(x, y - 3, ramp[6])
    cv.set(x, y - 4, ramp[4])


def glow(cv, S, glass, flame=True):
    """Iron glazing bars where the panes meet, a glint on the front pane, a little flame on its
    burner inside; at night the glass is lamplight, brightest round the flame, and the iron
    right above and below it catches some of the light."""
    px = pixels_of(S, glass)
    if not px:
        return
    gs = set(px)
    pid = S.pid
    xs = [p[0] for p in px]
    ys = [p[1] for p in px]
    cx = (min(xs) + max(xs) + 1) // 2
    top, bot = min(ys), max(ys)
    front = pid[(top + bot) // 2, cx]
    for x, y in px:
        if (x + 1, y) in gs and pid[y, x + 1] != pid[y, x]:
            cv.set(x, y, LAMP_IRON[3])  # glazing bar where two panes meet
        elif y == top:
            cv.set(x, y, GLASS_DAY[1])  # the cap's shadow along the top
        elif pid[y, x] == front and x == cx - 2 and y < bot - 1:
            cv.set(x, y, GLASS_DAY[5])  # a glint
    if flame:
        cv.set(cx, bot, LAMP_IRON[4])
        cv.set(cx - 1, bot, LAMP_IRON[3])
        cv.set(cx, bot - 1, "#fff3c0")
        cv.set(cx, bot - 2, "#f2c450")
    for x, y in px:  # night
        dy = (y - top) / max(1, bot - top)
        near = abs(x - cx) <= 1 and 0.3 < dy < 0.95
        c = LIT[4] if near else LIT[3] if (pid[y, x] == front or dy > 0.5) else LIT[2]
        if y == top:
            c = LIT[1]
        cv.lit(x, y, c)
    for x, y in px:  # the iron rim above and the cup below, warmed
        for q in ((x, y - 1), (x, y + 1)):
            if q not in gs and cv.get(*q)[3]:
                cv.lit(q[0], q[1], LIT[1] if q[1] > y else LIT[0])


# ================================================================ lamps

def street_lamp(spec):
    """A street lamp: an iron post on an octagonal stone foot, a collar, a ring and the
    lamplighter's ladder bar, and a six-sided lantern with a cap and a finial; its glass glows at
    night. arms=2: a taller post with a scrolled cross arm and two lanterns hanging from it."""
    arms = spec.get("arms", 1)
    S = Scene(pad_top=6)
    cy = 4
    iron = M.flat(LAMP_IRON, 0.05)
    cap = M.flat(LAMP_IRON, 0.12)
    S.add(prism(0, cy, 4.2, 0, 2.5, ashlar(STONE, seed=3, bias=0.0), sides=8))
    S.add(prism(0, cy, 3.3, 2.5, 4.5, ashlar(STONE, seed=5, bias=0.06), sides=8))
    S.add(frustum(0, cy, 2.3, 1.3, 4.5, 9, iron, sides=8))
    S.add(prism(0, cy, 1.7, 9, 10, cap, sides=8))
    glasses = []
    if arms == 1:
        top = 26
        S.add(prism(0, cy, 1.0, 10, top, iron, sides=8))
        S.add(prism(0, cy, 1.5, 16, 17, cap, sides=8))
        S.add(box(-4.5, 4.5, cy - 0.5, cy + 0.5, top - 4, top - 3, iron))  # ladder bar
        S.add(frustum(0, cy, 1.2, 3.0, top, top + 3, iron, sides=6))
        glasses.append(S.add(frustum(0, cy, 2.9, 3.7, top + 3, top + 11, lamp_glass(), sides=6)))
        S.add(prism(0, cy, 4.6, top + 11, top + 12, cap, sides=6))
        S.add(pyramid(0, cy, 4.4, top + 12, top + 16, cap, sides=6))
    else:
        top = 37
        S.add(prism(0, cy, 1.1, 10, top, iron, sides=8))
        S.add(prism(0, cy, 1.6, 19, 20, cap, sides=8))
        S.add(box(-12, 12, cy - 0.6, cy + 0.6, top - 2, top - 0.5, iron))  # the cross arm
        S.add(prism(0, cy, 1.9, top - 1, top + 1.5, cap, sides=8))
        S.add(prism(0, cy, 1.3, top + 1.5, top + 3, cap, sides=8))
        for lx in (-10.5, 10.5):
            zt = top - 4
            S.add(pyramid(lx, cy, 3.9, zt - 0.5, zt + 1.8, cap, sides=6))
            S.add(prism(lx, cy, 3.9, zt - 1.5, zt - 0.5, cap, sides=6))
            glasses.append(S.add(frustum(lx, cy, 2.4, 3.2, zt - 9.5, zt - 1.5, lamp_glass(), sides=6)))
            S.add(frustum(lx, cy, 0.8, 2.6, zt - 12, zt - 9.5, iron, sides=6))
    cv = S.render()
    for g in glasses:
        glow(cv, S, g)
    cv.free()
    if arms == 1:
        finial(cv, *S.s(0, cy, top + 16))
    else:
        finial(cv, *S.s(0, cy, top + 3))
        for side in (-1, 1):  # scrolls under the arm, hooks down to the lanterns
            ax, ay = S.s(side * 1.1, cy - 1, top - 2)
            for i, (dx, dy) in enumerate(((1, 2), (1, 3), (2, 4), (3, 4), (4, 3), (5, 2), (6, 1), (4, 2))):
                cv.set(ax + side * dx, ay + dy, LAMP_IRON[5] if i < 4 else LAMP_IRON[4])
            hx, hy = S.s(side * 10.5, cy, top - 2)
            cv.set(hx, hy, LAMP_IRON[5])
            cv.set(hx, hy + 1, LAMP_IRON[4])
            fx, fy = S.s(side * 10.5, cy, top - 16)
            cv.set(fx, fy, LAMP_IRON[4])
            cv.set(fx, fy + 1, LAMP_IRON[5])
    return done(S, cv, fp(-4.2, 4.2, 2 * cy))


# ================================================================ benches

def bench(spec):
    """A park bench: wooden slats on cast-iron ends, the seat top and a slatted back rest you can
    see the grass through, armrests with scrolled fronts."""
    wood = spec.get("wood", WOOD)
    S = Scene(pad_top=4)
    hw = 14
    seat_z = 7.5
    S.add(box(-hw + 1, hw - 1, 0.5, 8, seat_z - 1.5, seat_z, slats(wood, pitch=2.5, seed=2)))
    for z0, z1 in ((10.5, 13), (14, 16.5)):
        S.add(box(-hw + 1, hw - 1, 7.2, 8.2, z0, z1, slats(wood, seed=int(z0))))
    iron = M.flat(BENCH_IRON, 0.1)
    for x in (-hw, hw - 1.5):
        S.add(box(x, x + 1.5, 0.8, 2.3, 0, seat_z - 1.5, iron))  # front leg
        S.add(box(x, x + 1.5, 7.0, 8.6, 0, 17.5, iron))  # back leg up to the top of the back
        S.add(box(x - 0.3, x + 1.8, 0.2, 8.6, 11, 12.3, iron))  # armrest
        S.add(box(x, x + 1.5, 1.0, 2.2, seat_z, 11, iron))  # arm post
        S.add(box(x, x + 1.5, 1.5, 7.5, 1.5, 2.5, iron))  # stretcher
    cv = S.render()
    cv.free()
    for side, x in ((-1, -hw), (1, hw - 1.5)):  # scrolled armrest fronts and splayed feet
        fx, fy = S.s(x + 0.75, 0.2, 11)
        cv.set(fx - side, fy, BENCH_IRON[5])
        cv.set(fx - side, fy + 1, BENCH_IRON[4])
        lx, ly = S.s(x + 0.75, 0.8, 0)
        cv.set(lx - side, ly - 1, BENCH_IRON[3])
    return done(S, cv, fp(-hw - 0.3, hw + 0.3, 8.6))


def bench_stone(spec):
    """A stone bench: a smooth dressed slab with a moulded lip on two tapering pedestals with
    plinths, a little moss on the seat, grass at its feet."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=4)
    hw = 14
    S.add(box(-hw, hw, 0, 9, 7.5, 9.5, ashlar(STONE, seed=4, bias=0.12, top_bias=0.05)))
    S.add(box(-hw + 1, hw - 1, 1, 8, 6.5, 7.5, ashlar(STONE, seed=6, bias=-0.05)))
    for x in (-9, 9):
        S.add(frustum(x, 4.5, 3.2, 2.5, 1.2, 6.5, ashlar(STONE, seed=7 + x, bias=0.05), sides=4, rot=math.pi / 4))
        S.add(box(x - 4, x + 4, 0.5, 8.5, 0, 1.2, ashlar(STONE, seed=9, bias=0.1)))
    cv = S.render()
    cv.at_depth(3)
    for x in range(S.sx(-hw + 1), S.sx(-hw + 8)):  # moss creeping over the seat's back corner
        for k in range(rnd.randint(0, 3) if x < S.sx(-hw + 5) else rnd.randint(0, 1)):
            cv.set(x, S.sy(8.5, 9.5) + k, MOSS[rnd.randint(1, 3)])
    cv.at_depth(-0.1)
    for x in range(S.sx(-hw), S.sx(-hw + 4)):  # and down its front edge
        if rnd.random() < 0.6:
            cv.set(x, S.sy(0, 9.5) + rnd.randint(0, 1), MOSS[rnd.randint(0, 2)])
    S.finish(cv)
    for x in range(S.sx(-hw - 1), S.sx(hw + 1)):  # grass round the feet
        if hsh(x, 13) < 0.35:
            for k in range(1 + int(hsh(x, 14) * 2)):
                if not cv.get(x, S.sy(0, 0) - k)[3] or k == 0:
                    cv.set(x, S.sy(-0.5, 0) - k, STEMS[4] if k else STEMS[3])
    return _result(cv, "prop", (S.ox, S.base), fp(-hw, hw, 9))


# ================================================================ notice board and signpost

def notice_board(spec):
    """A notice board: a framed plank board on two posts under a little shingle roof, papers
    pinned all over it (notes, a wanted bill, a picture, a torn scrap), a lantern on one post."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=4)
    dw = M.wood(DARKWOOD, bias=0.12)
    for x in (-14, 11.5):
        S.add(box(x, x + 2.5, 0, 2.5, 0, 30, dw))
    S.add(box(-11.5, 11.5, 0.6, 2, 7.5, 25, M.boards(WOOD, w=4, seed=5, bias=0.05)))
    for z0, z1 in ((6, 7.5), (25, 26.5)):
        S.add(box(-12, 12, 0.3, 2.3, z0, z1, M.wood(DARKWOOD, bias=0.2)))
    S.add(gable_x(-16.5, 16.5, -3.5, 5.5, 28, 29.5, 35, M.shingles(ROOFS[spec.get("roof_colour", "rust")], seed=7, row_h=2.5)))
    cv = S.render()
    cv.on_wall(0.6, tol=0.5)
    papers = [  # x, z (top), w, h, paper, kind
        (-10, 24, 7, 8, "#efe6cf", "wanted"),
        (-2, 23, 6, 6, "#f6f1e4", "note"),
        (5, 24, 6, 7, "#e9dcb8", "map"),
        (-6, 15, 6, 6, "#f3e3a8", "note"),
        (2, 16, 8, 5, "#dfe8ef", "picture"),
        (-11, 13, 4, 4, "#f6f1e4", "scrap"),
        (6, 10, 4, 3, "#f0c8c0", "note"),
    ]
    pins = ["#d63a3a", "#3a6ad6", GOLD[3], "#3aa04a"]
    for i, (x, z, w, h, pc, kind) in enumerate(papers):
        sx, sy = S.sx(x), S.sy(0.6, z)
        for yy in range(sy, sy + h):
            for xx in range(sx, sx + w):
                c = pc
                if xx == sx + w - 1 or yy == sy + h - 1:
                    c = "#b8ac90"  # its shaded edge
                cv.set(xx, yy, c)
        if kind == "wanted":
            for xx in range(sx + 1, sx + w - 1):
                cv.set(xx, sy + 1, "#8a2a22")
            for yy in range(sy + 3, sy + 6):  # a little face
                for xx in range(sx + 2, sx + 5):
                    cv.set(xx, yy, "#c9a27a" if yy > sy + 3 else "#5a3a22")
            cv.set(sx + 2, sy + 4, "#3a2a1a")
            cv.set(sx + 4, sy + 4, "#3a2a1a")
            scribble(cv, rnd, sx + 1, sx + w - 1, sy + 7, "#6a5a4a")
        elif kind == "map":
            for yy in range(sy + 1, sy + h - 1):
                for xx in range(sx + 1, sx + w - 1):
                    if (xx * 3 + yy * 5) % 7 == 0:
                        cv.set(xx, yy, "#7a9a5a")
            cv.set(sx + 3, sy + 3, "#c0392b")
            cv.set(sx + 2, sy + 4, "#5a7ab0")
        elif kind == "picture":
            for xx in range(sx + 1, sx + 4):
                cv.set(xx, sy + 2, "#e07a2a")
                cv.set(xx, sy + 3, "#c05a1a")
            cv.set(sx + 2, sy + 1, "#5fa047")
            for k in range(3):
                scribble(cv, rnd, sx + 5, sx + w - 1, sy + 1 + k, "#5a5a6a")
        elif kind != "scrap":
            for k in range(1, h - 1, 2):
                scribble(cv, rnd, sx + 1, sx + w - 1, sy + k, "#6a6070")
        else:
            cv.set(sx + w - 1, sy, "#d8ccb0")  # a torn corner
        cv.set(sx + w // 2, sy, pins[i % len(pins)])
        if i % 3 == 1:  # a corner curling away from the board
            cv.set(sx + w - 1, sy + h - 1, "#fffaf0")
    cv.free()
    if spec.get("lantern", True):
        lantern(cv, S.sx(14.5) + 2, S.sy(0, 22))
    return done(S, cv, fp(-14, 14, 2.5))


def signpost(spec):
    """A fingerpost: an oak post on a cairn of stones with a pitched cap, painted arms pointing
    left and right at different heights, one of them angled off down a side road, lettering
    on each."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=4, pad=4)
    py0 = 1.2
    S.add(prism(0, 2.6, 4.6, 0, 2.2, M.fieldstone(FIELDSTONE, seed=3, bias=-0.05), sides=9))
    S.add(prism(-0.4, 2.8, 3.2, 2.2, 3.8, M.fieldstone(FIELDSTONE, seed=4, bias=0.0), sides=7))
    S.add(box(-1.4, 1.4, py0, py0 + 2.8, 0, 36, M.wood(PAINTED["oak"], bias=0.12)))
    S.add(gable_x(-2.2, 2.2, py0 - 0.8, py0 + 3.6, 35.5, 36.5, 38.5, M.wood(PAINTED["oak"], bias=0.2)))
    arms = spec.get("arms", [  # (pointing right?, z, length, paint, angle)
        (True, 30, 15, "cream", 0.0),
        (False, 25, 14, "green", 0.0),
        (True, 19.5, 11, "oak", 0.0),
    ])
    boards = []
    for right, z, length, paint, ang in arms:
        s = 1 if right else -1
        b = arrow_board(-s * 2.5, s * length, py0 - 1.2, py0, z, z + 4, 2.5, board_mat(PAINTED[paint], seed=int(z)))
        if ang:
            b = rotz(b, s * ang, 0, py0 + 1.4)
        boards.append((S.add(b), right, paint))
    cv = S.render()
    for b, right, paint in boards:
        px = pixels_of(S, b, 1)
        if not px:
            continue
        ys = sorted({p[1] for p in px})
        mid = ys[len(ys) // 2]
        row = sorted(p[0] for p in px if p[1] == mid)
        x0, x1 = row[0] + (2 if right else 4), row[-1] - (3 if right else 1)
        ink = "#3a2a1e" if paint == "cream" else "#f1e6cc"
        rowpx = {p for p in px}
        for x in range(x0, x1):
            if (x, mid) in rowpx and rnd.random() < 0.8 and (x - x0) % 4 != 3:
                cv.set(x, mid, ink)
                if rnd.random() < 0.4 and (x, mid - 1) in rowpx:
                    cv.set(x, mid - 1, ink)
    cv.free()
    cv.at_depth(-1)
    for x in range(S.sx(-5), S.sx(5)):  # grass round the cairn
        if rnd.random() < 0.45:
            for k in range(rnd.randint(1, 3)):
                cv.set(x, S.sy(-0.5, 0) - k, STEMS[3 + (k > 0)])
    return done(S, cv, fp(-4.6, 4.6, 5.2))


# ================================================================ flower beds and planters

def planter(spec):
    """A raised flower bed: low walls of dressed stone under a timber coping, soil a little way
    down inside, packed with clumps of tulips, daisies, lavender and marigolds, a few trailing
    over the front."""
    rnd = random.Random(spec.get("seed", 1))
    hw, d = spec.get("width", 32) / 2, 14
    S = Scene(pad_top=8)
    st = M.dressed_stone(STONE, h=3, seed=2, bias=0.12)
    S.add(box(-hw, hw, 0, 2, 0, 6, st))
    S.add(box(-hw, hw, d - 2, d, 0, 6, st))
    S.add(box(-hw, -hw + 2, 2, d - 2, 0, 6, st))
    S.add(box(hw - 2, hw, 2, d - 2, 0, 6, st))
    cap = M.wood(TRIM, bias=0.15)
    S.add(box(-hw - 0.5, hw + 0.5, -0.5, 2.3, 6, 7.5, cap))
    S.add(box(-hw - 0.5, hw + 0.5, d - 2.3, d + 0.5, 6, 7.5, cap))
    S.add(box(-hw - 0.5, -hw + 2.3, 2.3, d - 2.3, 6, 7.5, cap))
    S.add(box(hw - 2.3, hw + 0.5, 2.3, d - 2.3, 6, 7.5, cap))
    S.add(box(-hw + 2, hw - 2, 2, d - 2, 0, 5.5, soil()))
    cv = S.render()
    clumps = spec.get("clumps", [("cup", "red"), ("star", "white"), ("spike", "purple"), ("ball", "yellow"),
                                 ("cup", "pink"), ("star", "white"), ("spike", "blue"), ("ball", "orange")])
    rows = [(y, -hw + 2.3, hw - 2.3) for y in (11.2, 9.4, 7.6, 5.8, 4.0, 2.4)]
    plant(cv, S, rnd, 5.5, rows, clumps, band=6, stem=(1, 3))
    cv.at_depth(-0.6)
    for x in range(S.sx(-hw + 1), S.sx(hw - 1)):  # a few stems trailing over the front coping
        if hsh(x, 21) < 0.2:
            n = 1 + int(hsh(x, 22) * 3)
            for k in range(n):
                cv.set(x, S.sy(-0.5, 7.5) + k, STEMS[4] if k == 0 else STEMS[3])
    return done(S, cv, fp(-hw - 0.5, hw + 0.5, d + 0.5))


def planter_round(spec):
    """A round stone flower bed: a drum of dressed stone on a plinth with a lit rim, the bed
    heaped up into a dome of flowers with tall spikes of lupins in the middle, ivy trailing over
    the front."""
    rnd = random.Random(spec.get("seed", 1))
    r = 11
    cy = r
    S = Scene(pad_top=12)
    side = M.dressed_stone(STONE, h=3, seed=4, bias=0.1)
    S.add(prism(0, cy, r, 1, 7, ring_top(side, STONE, SOIL, rim_w=1.8), sides=22))
    S.add(prism(0, cy, r + 0.8, 0, 1.2, ashlar(STONE, seed=6, bias=0.0), sides=22))
    cv = S.render()
    clumps = spec.get("clumps", [("cup", "pink"), ("star", "white"), ("ball", "yellow"), ("cup", "red"),
                                 ("ball", "blue"), ("ball", "orange")])
    rows = []
    for dy in (7.2, 5.8, 4.4, 3, 1.6, 0.2, -1.2, -2.6, -4, -5.4, -6.8, -8):
        half = math.sqrt(max(0.0, (r - 2.1) ** 2 - dy * dy))
        if half > 1.5:
            rows.append((cy + dy, -half, half))
    centre = spec.get("centre", "purple")
    spikes = [(-3, cy + 2.4, 5, centre), (0, cy + 3.2, 6, centre), (3, cy + 1.6, 5, centre), (-1, cy + 0.4, 4, "blue")]
    plant(cv, S, rnd, 7, rows, clumps, band=5, stem=(1, 2), mound=(0, cy, r - 2, 3), spikes=spikes)
    cv.at_depth(cy - r - 0.6)
    for x0, n in ((-6, 3), (-5, 5), (-2, 2), (4, 4)):  # ivy trailing over the front
        x = S.sx(x0)
        for k in range(n):
            cv.set(x + (k >= 3) * (-1 if x0 < 0 else 1), S.sy(0, 7) + k, STEMS[4] if k % 2 == 0 else STEMS[3])
    return done(S, cv, fp(-r - 0.8, r + 0.8, 2 * r + 0.8))


def barrel_planter(spec):
    """Half a barrel full of flowers: staves and hoops, the rim of stave ends round the soil, a
    mound of blooms heaped up in the middle and greenery spilling over the front."""
    rnd = random.Random(spec.get("seed", 1))
    r = 7.5
    cy = r
    S = Scene(pad_top=10)
    rim = ["#2a1a10", "#4b3022", "#7b5236", "#946743", "#ad7f55", "#c49a6c"]
    S.add(prism(0, cy, r, 0, 8, ring_top(stave_tub(WOOD, seed=2), rim, SOIL, rim_w=1.2), sides=16))
    cv = S.render()
    clumps = spec.get("clumps", [("ball", "orange"), ("star", "white"), ("cup", "red"), ("ball", "yellow")])
    rows = []
    for dy in (4.8, 3.6, 2.4, 1.2, 0, -1.2, -2.4, -3.6, -4.8):
        half = math.sqrt(max(0.0, (r - 1.3) ** 2 - dy * dy))
        if half > 1:
            rows.append((cy + dy, -half, half))
    plant(cv, S, rnd, 8, rows, clumps, band=4, gap=(2, 3), stem=(1, 1), mound=(0, cy, r - 1, 4))
    cv.at_depth(cy - r - 0.6)
    for x0, n in ((-4, 4), (3, 3)):  # strands of ivy down the staves
        x = S.sx(x0)
        for k in range(n):
            cv.set(x + (k == n - 1) * (1 if x0 > 0 else -1), S.sy(0, 8) + k, STEMS[4] if k % 2 == 0 else STEMS[3])
    return done(S, cv, fp(-r, r, 2 * r))


# ================================================================ dry-stone walls

def _wall_finish(S, cv, keep):
    """Outline the wall, then take away the outline beyond the ends that join on (keep is a
    function (x, y) -> bool), so pieces placed end to end meet without a seam."""
    S.finish(cv)
    for y in range(cv.h):
        for x in range(cv.w):
            if not keep(x, y):
                cv.clear(x, y)


def stone_wall(spec):
    """A low dry-stone wall. run="x": a 32 px length running across, the stones repeating so
    pieces join end to end; run="y": a 32 px (on the map) length running back, its battered sides
    showing as thin sloping faces; run="post": a square pillar with a cap stone for corners and
    ends. Cock-and-hen coping stones set on edge along the top, lichen, grass at the foot."""
    run = spec.get("run", "x")
    seed = spec.get("seed", 1)
    rnd = random.Random(seed)
    ramp = FIELDSTONE
    H = 9
    if run == "x":
        L = 32
        S = Scene(pad_top=6)
        S.add(battered(-L / 2, L / 2, 0, 7.5, 0, H, 0, 1.0, drystone(ramp, period=L, seed=seed)))
        x = -L / 2
        k = 0
        widths = [3, 2, 3, 2.5, 3, 2, 3.5, 2, 3, 2.5, 3, 2.5]  # sums to 32
        for w in widths:
            hgt = (4.0, 2.5, 3.5, 2.5)[k % 4] + (0.5 if k in (2, 7) else 0)
            S.add(box(x, x + w, 1.1, 6.4, H, H + hgt, coping(ramp, seed=seed + k)))
            x += w
            k += 1
        cv = S.render()
        _grass(cv, rnd, S.sx(-L / 2), S.sx(L / 2), S.sy(-0.3, 0))
        x0, x1 = S.sx(-L / 2), S.sx(L / 2)
        _wall_finish(S, cv, lambda x, y: x0 <= x < x1)
        return _result(cv, "prop", (S.ox, S.base), fp(-L / 2, L / 2, 7.5))
    if run == "y":
        D = 40  # 40 px back = 32 px on the map
        S = Scene(pad_top=6, pad=4)
        S.add(battered(-5, 5, 0, D, 0, H, 2.4, 0, drystone(ramp, period=D, seed=seed + 1)))
        y = 0.0
        k = 0
        depths = [3, 2.5, 3.5, 2.5, 3, 3, 2.5, 3.5, 2.5, 3, 3.5, 2.5, 3.5]  # sums to 40
        for dpt in depths:
            hgt = (4.0, 2.5, 3.5, 2.5)[k % 4] + (0.5 if k in (3, 8) else 0)
            S.add(box(-2.5, 2.5, y, y + dpt, H, H + hgt, coping(ramp, seed=seed + 20 + k)))
            y += dpt
            k += 1
        cv = S.render()
        _grass(cv, rnd, S.sx(-5), S.sx(5), S.sy(-0.3, 0))
        S.finish(cv)
        # the far end joins the next piece back, whose front end fills in round it: take away
        # the outline drawn above and beside the far end so the two meet without a seam
        far = S.sy(D, 0)
        for x in range(S.sx(-5) - 1, S.sx(5) + 1):
            for yy in range(0, far):
                if not _wall_px(S, x, yy):
                    cv.clear(x, yy)
        return _result(cv, "prop", (S.ox, S.base), fp(-5, 5, D))
    # the post
    S = Scene(pad_top=6)
    S.add(battered(-5, 5, 0, 10, 0, 13, 0.6, 0.6, drystone(ramp, period=40, seed=seed + 2)))
    S.add(box(-6, 6, -1, 11, 13, 15, ashlar(STONE, seed=seed + 3, bias=0.12)))
    S.add(frustum(0, 5, 4.6, 2.6, 15, 17.5, ashlar(STONE, seed=seed + 4, bias=0.1), sides=4, rot=math.pi / 4))
    cv = S.render()
    cv.at_depth(-1.5)
    sy = S.sy(-1, 15)
    for x in range(S.sx(-6), S.sx(-1)):  # lichen on the cap's front edge
        if hsh(x, 51) < 0.5:
            cv.set(x, sy + (hsh(x, 52) < 0.3), MOSS[1 + int(hsh(x, 53) * 3)])
    _grass(cv, rnd, S.sx(-5), S.sx(5), S.sy(-0.3, 0))
    return done(S, cv, fp(-5, 5, 10))


def _wall_px(S, x, y):
    """Whether screen pixel (x, y) shows one of the wall's own solids."""
    return 0 <= y < S.sid.shape[0] and 0 <= x < S.sid.shape[1] and S.sid[y, x] >= 0


def _grass(cv, rnd, x0, x1, y):
    """Grass and a weed or two growing at the foot of a wall (repeating with the stones)."""
    cv.free()
    for x in range(x0, x1):
        h = 1 + int(hsh(x - x0, 3) * 3) if hsh(x - x0, 4) < 0.55 else 0
        for k in range(h):
            if not cv.get(x, y - k)[3] or k < 3:
                cv.set(x, y - k, STEMS[4] if k == h - 1 else STEMS[3])
        if hsh(x - x0, 9) < 0.06 and h:
            cv.set(x, y - h, BLOOMS["yellow"][1])


# ================================================================ post box

def postbox(spec):
    """A red pillar post box: a dark plinth, a drum with a door and keyhole, a posting slot under
    a little hood, a collection plate, a gold horn badge, a banded rim and a domed cap."""
    S = Scene(pad_top=6)
    r = 5
    cy = 5.8
    red = M.flat(POST_RED, 0.12)
    S.add(prism(0, cy, r + 0.8, 0, 1.6, M.flat(LAMP_IRON, 0.1), sides=16))
    S.add(prism(0, cy, r, 1.6, 14, red, sides=16))
    S.add(prism(0, cy, r + 0.6, 14, 15.2, M.flat(POST_RED, 0.22), sides=16))
    S.add(frustum(0, cy, r + 0.2, r - 1.4, 15.2, 16.6, M.flat(POST_RED, 0.18), sides=16))
    S.add(frustum(0, cy, r - 1.4, 1.6, 16.6, 17.8, M.flat(POST_RED, 0.2), sides=16))
    S.add(frustum(0, cy, 1.6, 0.5, 17.8, 18.4, M.flat(POST_RED, 0.25), sides=16))
    S.add(box(-2.8, 2.8, cy - r - 0.9, cy - r + 1.5, 11.4, 12.4, M.flat(POST_RED, 0.25)))  # hood over the slot
    cv = S.render()
    front = cy - r
    cv.on_wall(front, tol=1.2)
    sx, sy = S.sx(0), S.sy(front, 11)
    for x in range(sx - 2, sx + 3):  # the slot
        cv.set(x, sy, "#120608")
        cv.set(x, sy + 1, POST_RED[2])
    py = S.sy(front, 9)
    for y in range(py, py + 3):  # collection plate
        for x in range(sx - 2, sx + 2):
            cv.set(x, y, "#ece4cc" if (x + y) % 3 else "#b8ae98")
    cv.set(sx - 1, py + 1, "#5a5050")
    cv.set(sx + 1, py, "#5a5050")
    dy0, dy1 = S.sy(front, 6.5), S.sy(front, 2.5)
    for y in range(dy0, dy1):  # the door's edge
        cv.set(sx - 3, y, POST_RED[3])
        cv.set(sx + 3, y, POST_RED[2])
    for x in range(sx - 3, sx + 4):
        cv.set(x, dy0, POST_RED[3])
        cv.set(x, dy1, POST_RED[2])
    by = S.sy(front, 5)  # a little posthorn badge
    for dx, dy, c in ((-1, 0, GOLD[3]), (0, 0, GOLD[3]), (1, 0, GOLD[2]), (1, -1, GOLD[2]), (-1, 1, GOLD[2]),
                      (-2, 1, GOLD[3]), (0, 1, GOLD[1])):
        cv.set(sx + dx, by + dy, c)
    cv.set(sx + 2, S.sy(front, 3.5), GOLD[3])  # keyhole
    cv.free()
    for (x, y) in pixels_of(S, S.solids[2], None):  # a shadow line under the rim band
        if not (S.sid[y + 1, x] == 2) and S.sid[y + 1, x] == 1:
            cv.darken(x, y + 1, 0.35)
    return done(S, cv, fp(-r - 0.8, r + 0.8, 2 * cy))


# ================================================================ farmyard

def hay_bales(spec):
    """Square bales of hay: two on the ground and one on top, each with two bands of twine; a
    fourth turned end on beside them showing its bristling cut end; loose straw about."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=6)
    bales = [S.add(box(-15, -0.6, 0, 8, 0, 7, straw(seed=1))),
             S.add(box(0.6, 14.5, 0.6, 8.6, 0, 7, straw(seed=2))),
             S.add(box(-7.5, 6.5, 1.8, 9.8, 7, 14, straw(seed=3))),
             S.add(box(15.8, 22.6, -1.5, 11.5, 0, 7, straw(seed=4)))]
    cv = S.render()
    S.finish(cv)
    for b in bales:  # stray straws poking out of the top edges, through the outline
        x0, x1, y0, y1, z0, z1 = b.bbox
        for i in range(1, int(x1 - x0) - 1):
            if hsh(i, x0, 61) < 0.2:
                px, py = S.s(x0 + i + 0.5, y1 - 0.5, z1)
                for k in range(1, 3):
                    if S.sid[py - k, px] < 0 if 0 <= py - k < cv.h else False:
                        cv.set(px + (k == 2) * (1 if hsh(i, 63) < 0.5 else -1), py - k, HAY7[5] if k == 1 else HAY7[4])
                        break
    for _ in range(10):  # loose straw on the ground near the bales
        x = rnd.uniform(-16, 23)
        px, py = S.s(x, -rnd.uniform(0.3, 2.5), 0)
        if cv.get(px, py)[3]:
            continue
        cv.set(px, py, HAY7[5] if rnd.random() < 0.5 else HAY7[4])
    return _result(cv, "prop", (S.ox, S.base), fp(-15, 22.6, 12))


def woodpile(spec):
    """A woodpile: split logs stacked end on under a little shingle pent roof on four posts, a
    chopping block with an axe bitten into it, two logs waiting to be split, chips about."""
    rnd = random.Random(spec.get("seed", 1))
    S = Scene(pad_top=4)
    hw, d = 15, 12
    dw = M.wood(DARKWOOD, bias=0.12)
    for x in (-hw, hw - 2):
        S.add(box(x, x + 2, 0, 2, 0, 22, dw))
        S.add(box(x, x + 2, d - 2, d, 0, 19, dw))
    S.add(box(-hw + 1, hw - 1, 1, d - 1, 0, 1.5, M.planks(DARKWOOD, h=3, seed=4, bias=0.1)))
    S.add(box(-hw + 2, hw - 2, 2, d - 1, 1.5, 19, split_logs(seed=spec.get("seed", 1))))
    roof = S.add(slab(-hw - 2, hw + 2, -3, d + 2, 23.5, 19.5, 1.6,
                      M.shingles(ROOFS[spec.get("roof_colour", "bark")], seed=8, row_h=3)))
    roof.params["zr"] = 1e9  # it falls to the back: no ridge cap
    S.add(prism(hw + 6, -3, 3.4, 0, 5, stump_mat(), sides=12))
    for lx, ly, lr in ((-hw - 3.5, -6.5, 2.6), (-hw + 2, -5, 2.2)):  # rounds waiting to be split
        S.add(prism_y(lx, ly, ly + 3.5, lr, lr, log_end(lx, lr, lr), sides=12))
    cv = S.render()
    S.finish(cv)
    ax, ay = S.s(hw + 6.5, -3.5, 5)  # the axe bitten into the block, its haft up to the left
    for k in range(9):
        x, y = ax - 2 - k, ay - 2 - k // 2
        cv.set(x, y, WOOD[5] if k % 3 else WOOD[4])
        cv.set(x, y + 1, WOOD[1])
    for dx, dy, c in ((-1, -2, IRON[1]), (0, -2, "#b7bec9"), (1, -2, "#808897"), (-1, -1, IRON[1]), (0, -1, "#e9edf2"),
                      (1, -1, "#808897"), (0, -3, IRON[1]), (1, -3, IRON[1])):
        cv.set(ax + dx, ay + dy, c)
    for _ in range(14):  # chips
        px, py = S.s(rnd.uniform(hw - 2, hw + 13), rnd.uniform(-9, -1), 0)
        if not cv.get(px, py)[3]:
            cv.set(px, py, "#e2bb82" if rnd.random() < 0.5 else "#a87a48")
    return _result(cv, "prop", (S.ox, S.base), fp(-hw, hw, d))


# ================================================================ shared

def done(S, cv, footprint, kind="prop"):
    S.finish(cv)
    return _result(cv, kind, (S.ox, S.base), footprint)


def fp(x0, x1, d):
    fd = max(2, round(K * d))
    return [math.floor(x0), -fd, math.ceil(x1) - math.floor(x0), fd]


DESIGNS = {
    "street_lamp": street_lamp, "bench": bench, "bench_stone": bench_stone, "notice_board": notice_board,
    "signpost": signpost, "planter": planter, "planter_round": planter_round, "stone_wall": stone_wall,
    "postbox": postbox, "barrel_planter": barrel_planter, "hay_bales": hay_bales, "woodpile": woodpile,
}

ENTRIES = [
    {"id": "street_lamp", "name": "路灯", "group": GROUP, "type": "street_lamp", "seed": 1},
    {"id": "street_lamp_double", "name": "双臂路灯", "group": GROUP, "type": "street_lamp", "seed": 2, "arms": 2},
    {"id": "bench", "name": "长椅", "group": GROUP, "type": "bench", "seed": 1},
    {"id": "bench_stone", "name": "石长椅", "group": GROUP, "type": "bench_stone", "seed": 2},
    {"id": "notice_board", "name": "告示板", "group": GROUP, "type": "notice_board", "seed": 3},
    {"id": "signpost", "name": "路标", "group": GROUP, "type": "signpost", "seed": 4},
    {"id": "planter", "name": "花坛", "group": GROUP, "type": "planter", "seed": 5},
    {"id": "planter_round", "name": "圆花坛", "group": GROUP, "type": "planter_round", "seed": 6},
    {"id": "stone_wall_x", "name": "石墙(横)", "group": GROUP, "type": "stone_wall", "seed": 7, "run": "x"},
    {"id": "stone_wall_y", "name": "石墙(纵)", "group": GROUP, "type": "stone_wall", "seed": 7, "run": "y"},
    {"id": "stone_wall_post", "name": "石墙柱", "group": GROUP, "type": "stone_wall", "seed": 7, "run": "post"},
    {"id": "postbox", "name": "邮筒", "group": GROUP, "type": "postbox", "seed": 8},
    {"id": "barrel_planter", "name": "木桶花盆", "group": GROUP, "type": "barrel_planter", "seed": 9},
    {"id": "hay_bales", "name": "干草堆", "group": GROUP, "type": "hay_bales", "seed": 10},
    {"id": "woodpile", "name": "柴堆", "group": GROUP, "type": "woodpile", "seed": 11},
]
