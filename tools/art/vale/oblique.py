"""A tiny renderer for pixel-art buildings seen from the front and 45 degrees above.

Buildings are put together from convex solids (boxes, roofs with the ridge across or going back,
gambrel roofs, many-sided prisms and pyramids for towers and cones, sloping slabs for awnings) in
a world where x runs right, y runs back (away from the viewer) and z runs up. A point projects to
the screen as
    sx = ox + x,    sy = base - z - K * y
so a front wall keeps its full height, top faces show their depth (foreshortened by K), the ridge
of a roof sits in the middle of it with a strip of the back slope showing behind, and a roof whose
gable faces the street runs back as two long planes.

For every pixel the nearest surface is found by clipping the view ray against each solid's planes
(numpy, all pixels at once). Faces are lit from the upper left and a little in front, solids cast
shadows on one another, each solid's material paints its own pixel pattern (planks, shingles,
stone...) from surface coordinates, and edges between faces and between near and far solids get
the crisp light and dark lines of hand-made pixel art. Doors, windows and signs are then drawn on
top with the 2D parts from buildings.py, which only land where the wall they belong to is visible.
"""
import math

import numpy as np

from buildings import C, Canvas, tone

K = 0.8  # how much depth shows on screen (1 = as much as height)
_L = np.array([-0.45, -0.5, 0.74])
LIGHT = _L / np.linalg.norm(_L)
SHADOW_TINT = np.array([22.0, 18.0, 34.0])


def hsh(*a):
    """Stable hash of a few numbers -> [0, 1)."""
    h = 2166136261
    for v in a:
        h = (h ^ (int(math.floor(v)) & 0xFFFFFFFF)) * 16777619 & 0xFFFFFFFF
        h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0x1000000)


# ================================================================ solids

class Solid:
    """A convex solid: planes n.P <= d (n normalised), a material and its parameters."""

    def __init__(self, planes, mat, bbox, **params):
        self.planes = []
        for n, d in planes:
            n = np.asarray(n, dtype=float)
            ln = np.linalg.norm(n)
            self.planes.append((n / ln, d / ln))
        self.mat = mat
        self.bbox = bbox  # x0, x1, y0, y1, z0, z1
        self.params = params


def box(x0, x1, y0, y1, z0, z1, mat, **kw):
    return Solid([((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0), ((0, 0, 1), z1)],
                 mat, (x0, x1, y0, y1, z0, z1), **kw)


def gable_x(x0, x1, y0, y1, z0, ze, zr, mat, **kw):
    """Roof with the ridge running across (left to right) halfway back; eaves at ze, ridge zr."""
    h = (y1 - y0) / 2
    p = (zr - ze) / h
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0),
              ((0, -p, 1), ze - p * y0), ((0, p, 1), ze + p * y1)]
    return Solid(planes, mat, (x0, x1, y0, y1, z0, zr), ze=ze, zr=zr, ridge="x", y0=y0, y1=y1, **kw)


def hip_x(x0, x1, y0, y1, z0, ze, zr, hip, mat, **kw):
    """Roof with the ridge across, its ends hipped: they slope up from the side eaves too, so
    the roof shows a lit end on the left and a shaded one on the right."""
    h = (y1 - y0) / 2
    p = (zr - ze) / h
    q = (zr - ze) / hip
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0),
              ((0, -p, 1), ze - p * y0), ((0, p, 1), ze + p * y1), ((-q, 0, 1), ze - q * x0), ((q, 0, 1), ze + q * x1)]
    return Solid(planes, mat, (x0, x1, y0, y1, z0, zr), ze=ze, zr=zr, ridge="x", y0=y0, y1=y1, **kw)


def gable_y(x0, x1, y0, y1, z0, ze, zr, mat, **kw):
    """Roof with the gable to the front and the ridge running back."""
    h = (x1 - x0) / 2
    p = (zr - ze) / h
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0),
              ((-p, 0, 1), ze - p * x0), ((p, 0, 1), ze + p * x1)]
    return Solid(planes, mat, (x0, x1, y0, y1, z0, zr), ze=ze, zr=zr, ridge="y", x0=x0, x1=x1, **kw)


def gambrel_y(x0, x1, y0, y1, z0, ze, knee, zk, zr, mat, **kw):
    """A barn roof, gable to the front: steep lower slopes up to the knee (knee px in from the
    eaves, height zk), then flatter up to the ridge zr."""
    h = (x1 - x0) / 2
    p1 = (zk - ze) / knee
    p2 = (zr - zk) / (h - knee)
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0),
              ((-p1, 0, 1), ze - p1 * x0), ((p1, 0, 1), ze + p1 * x1),
              ((-p2, 0, 1), zk - p2 * (x0 + knee)), ((p2, 0, 1), zk + p2 * (x1 - knee))]
    return Solid(planes, mat, (x0, x1, y0, y1, z0, zr), ze=ze, zr=zr, ridge="y", x0=x0, x1=x1, **kw)


def roof_shell_y(x0, x1, y0, y1, ze, zr, th, mat, **kw):
    """A roof with its gable to the front as two boards (th thick) meeting at the ridge, so the
    gable wall under it shows and the boards' ends read as barge boards."""
    xc = (x0 + x1) / 2
    p = (zr - ze) / (xc - x0)
    left = Solid([((-1, 0, 0), -x0), ((1, 0, 0), xc), ((0, -1, 0), -y0), ((0, 1, 0), y1),
                  ((-p, 0, 1), ze - p * x0), ((p, 0, -1), -(ze - th) + p * x0)],
                 mat, (x0, xc, y0, y1, ze - th, zr), ze=ze, zr=zr, ridge="y", **kw)
    right = Solid([((-1, 0, 0), -xc), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1),
                   ((p, 0, 1), ze + p * x1), ((-p, 0, -1), -(ze - th) - p * x1)],
                  mat, (xc, x1, y0, y1, ze - th, zr), ze=ze, zr=zr, ridge="y", **kw)
    return [left, right]


def gambrel_shell_y(x0, x1, y0, y1, ze, knee, zk, zr, th, mat, **kw):
    """A barn's gambrel roof as four boards: steep up to the knee, then flatter to the ridge."""
    out = []
    xc = (x0 + x1) / 2
    for side in (-1, 1):
        ex = x0 if side < 0 else x1  # eave edge
        kx = ex - side * knee  # knee
        p1 = (zk - ze) / knee
        p2 = (zr - zk) / abs(xc - kx)
        for (xa, xb, z_at, p, x_from) in ((ex, kx, ze, p1, ex), (kx, xc, zk, p2, kx)):
            lo, hi = min(xa, xb), max(xa, xb)
            # z rises going inward from x_from: z = z_at + p * side * (x_from - x)
            n_top = (side * p, 0, 1)
            d_top = z_at + side * p * x_from
            out.append(Solid([((-1, 0, 0), -lo), ((1, 0, 0), hi), ((0, -1, 0), -y0), ((0, 1, 0), y1),
                              (n_top, d_top), ((-side * p, 0, -1), -(d_top - th))],
                             mat, (lo, hi, y0, y1, z_at - th, zr), ze=ze, zr=zr, ridge="y", **kw))
    return out


def frustum(cx, cy, r0, r1, z0, z1, mat, sides=8, rot=0.0, **kw):
    """An upright many-sided frustum, radius r0 at z0 narrowing to r1 at z1 (a smock mill)."""
    h = z1 - z0
    k = (r0 - r1) / h
    planes = [((0, 0, -1), -z0), ((0, 0, 1), z1)]
    for i in range(sides):
        a = (i + 0.5) * 2 * math.pi / sides + rot
        n = (math.cos(a), math.sin(a), k)
        planes.append((n, n[0] * cx + n[1] * cy + r0 + k * z0))
    return Solid(planes, mat, (cx - r0, cx + r0, cy - r0, cy + r0, z0, z1), cx=cx, cy=cy, r=r0, **kw)


def prism_x(x0, x1, cy, cz, r, mat, sides=16, upper=True, **kw):
    """A cylinder lying along x (a wagon's canvas cover); upper=True keeps the half above cz."""
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1)]
    if upper:
        planes.append(((0, 0, -1), -cz))
    for i in range(sides):
        a = (i + 0.5) * 2 * math.pi / sides
        n = (0, math.cos(a), math.sin(a))
        planes.append((n, r + n[1] * cy + n[2] * cz))
    return Solid(planes, mat, (x0, x1, cy - r, cy + r, cz if upper else cz - r, cz + r), cyl_x=(cy, cz, r), **kw)


def prism(cx, cy, r, z0, z1, mat, sides=20, **kw):
    """An upright many-sided prism (a round tower)."""
    planes = [((0, 0, -1), -z0), ((0, 0, 1), z1)]
    for k in range(sides):
        a = (k + 0.5) * 2 * math.pi / sides
        n = (math.cos(a), math.sin(a), 0)
        planes.append((n, r + n[0] * cx + n[1] * cy))
    return Solid(planes, mat, (cx - r, cx + r, cy - r, cy + r, z0, z1), cx=cx, cy=cy, r=r, **kw)


def pyramid(cx, cy, r, z0, z1, mat, sides=20, **kw):
    """A cone (many-sided pyramid) from radius r at z0 to a point at z1."""
    h = z1 - z0
    planes = [((0, 0, -1), -z0)]
    for k in range(sides):
        a = (k + 0.5) * 2 * math.pi / sides
        n = (math.cos(a), math.sin(a), r / h)
        planes.append((n, n[0] * cx + n[1] * cy + r / h * z1))
    return Solid(planes, mat, (cx - r, cx + r, cy - r, cy + r, z0, z1), cx=cx, cy=cy, r=r, ze=z0, zr=z1, cone=True, **kw)


def slab(x0, x1, y_front, y_back, z_front, z_back, thick, mat, **kw):
    """A board sloping from the back edge (y_back, z_back) down to the front (y_front, z_front):
    awnings, porch roofs, lean-tos."""
    s = (z_back - z_front) / (y_back - y_front)
    planes = [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y_front), ((0, 1, 0), y_back),
              ((0, -s, 1), z_front - s * y_front), ((0, s, -1), -(z_front - thick) + s * y_front)]
    return Solid(planes, mat, (x0, x1, y_front, y_back, z_front - thick, max(z_front, z_back)),
                 ze=z_front, zr=z_back, ridge="x", y0=y_front, y1=2 * y_back - y_front, **kw)


# ================================================================ materials

class Mat:
    """Paints a solid's pixels: fn(u, v, kind, light, P, solid) -> colour, where u, v are surface
    coordinates in px (walls: x and height; tops: x and depth; slopes: along the ridge and up the
    slope from the eaves), kind is 'wall', 'top', 'slope' or 'side', light is 0..1."""

    def __init__(self, fn, outline=None):
        self.fn = fn
        self.outline = outline


def flat(ramp, offset=0.0):
    return Mat(lambda u, v, kind, light, P, s: ramp[tone(ramp, light + offset)])


# ================================================================ scene

class DCanvas(Canvas):
    """A Canvas that remembers depth, shadow and what lies where, so 2D parts drawn on it can be
    kept to one wall (on_wall) or placed as small upright sprites at a depth (at_depth)."""

    def __init__(self, w, h):
        super().__init__(w, h)
        self.t = np.full((h, w), np.inf)
        self.shadow = np.zeros((h, w), dtype=bool)
        self.mode = None

    def _ok(self, x, y):
        if not self.inb(x, y):
            return False
        if self.mode is None:
            return True
        kind, depth, tol = self.mode
        if kind == "wall":
            return abs(self.t[y, x] - depth) < tol
        return self.t[y, x] >= depth - tol  # sprite: in front of what is there

    def set(self, x, y, c):
        x, y = int(x), int(y)
        if not self._ok(x, y):
            return
        c = C(c)
        if self.mode is not None and self.shadow[y, x] and c[3]:
            c = _shade(c, 0.38)
        self.px[x, y] = c
        if self.mode is not None and self.mode[0] == "sprite":
            self.t[y, x] = self.mode[1]

    def lit(self, x, y, c):
        x, y = int(x), int(y)
        if self.inb(x, y) and (self.mode is None or self.px[x, y][3]):
            self.npx[x, y] = C(c)

    def darken(self, x, y, k):
        x, y = int(x), int(y)
        if self._ok(x, y):
            super().darken(x, y, k)

    def on_wall(self, depth, tol=1.5):
        self.mode = ("wall", depth, tol)
        return self

    def at_depth(self, depth, tol=0.6):
        self.mode = ("sprite", depth, tol)
        return self

    def free(self):
        self.mode = None
        return self


def _shade(c, k):
    r, g, b, a = c
    return (round(r * (1 - k) + SHADOW_TINT[0] * k), round(g * (1 - k) + SHADOW_TINT[1] * k), round(b * (1 - k) + SHADOW_TINT[2] * k), a)


class Scene:
    def __init__(self, pad=6, pad_top=4, pad_bottom=6, outline="#2a1a12"):
        self.solids = []
        self.pad, self.pad_top, self.pad_bottom = pad, pad_top, pad_bottom
        self.outline_colour = outline

    def add(self, solid):
        self.solids.append(solid)
        return solid

    # screen mapping, valid after render()
    def s(self, x, y, z):
        return round(self.ox + x), round(self.base - z - K * y)

    def sx(self, x):
        return round(self.ox + x)

    def sy(self, y, z):
        return round(self.base - z - K * y)

    def render(self, extra=(0, 0, 0, 0)):
        """Rasterise into a new DCanvas. extra = (left, right, top, bottom) px of room for parts
        drawn later (signs, ropes, things set out in front)."""
        xs0 = min(s.bbox[0] for s in self.solids)
        xs1 = max(s.bbox[1] for s in self.solids)
        top = max(s.bbox[5] + K * s.bbox[3] for s in self.solids)
        bot = min(0.0, min(s.bbox[4] + K * s.bbox[2] for s in self.solids))  # always down to the ground line
        self.ox = math.ceil(-xs0) + self.pad + extra[0]
        W = math.ceil(xs1 - xs0) + 2 * self.pad + extra[0] + extra[1]
        self.base = math.ceil(top) + self.pad_top + extra[2]
        H = self.base + math.ceil(-bot) + self.pad_bottom + extra[3]
        cv = DCanvas(W, H)
        X = np.broadcast_to(np.arange(W) + 0.5 - self.ox, (H, W))
        Cz = np.broadcast_to(self.base - (np.arange(H) + 0.5)[:, None], (H, W))
        best_t = np.full((H, W), np.inf)
        best_s = np.full((H, W), -1)
        best_p = np.full((H, W), -1)
        for si, sol in enumerate(self.solids):
            tin = np.full((H, W), -np.inf)
            tout = np.full((H, W), np.inf)
            pin = np.full((H, W), -1)
            ok = np.ones((H, W), dtype=bool)
            for pi, (n, d) in enumerate(sol.planes):
                nb = n[1] - K * n[2]
                na = n[0] * X + n[2] * Cz
                if abs(nb) < 1e-9:
                    ok &= na <= d + 1e-9
                elif nb < 0:
                    tc = (d - na) / nb
                    upd = tc > tin
                    tin = np.where(upd, tc, tin)
                    pin = np.where(upd, pi, pin)
                else:
                    tout = np.minimum(tout, (d - na) / nb)
            hit = ok & (tin <= tout) & (tin < best_t) & np.isfinite(tin)
            best_t = np.where(hit, tin, best_t)
            best_s = np.where(hit, si, best_s)
            best_p = np.where(hit, pin, best_p)
        # hit points, normals, light and shadows
        Py = best_t
        Pz = Cz - K * best_t
        hitm = best_s >= 0
        N = np.zeros((H, W, 3))
        for si, sol in enumerate(self.solids):
            for pi, (n, d) in enumerate(sol.planes):
                m = (best_s == si) & (best_p == pi)
                N[m] = n
        lam = np.clip(N @ LIGHT, 0.0, 1.0)
        shadow = np.zeros((H, W), dtype=bool)
        hy, hx = np.nonzero(hitm)
        if len(hy):
            P = np.stack([X[hy, hx], Py[hy, hx], Pz[hy, hx]], axis=1) + N[hy, hx] * 0.35
            sh = np.zeros(len(hy), dtype=bool)
            for sol in self.solids:
                if sol.params.get("no_shadow"):
                    continue
                tin = np.zeros(len(hy))
                tout = np.full(len(hy), np.inf)
                ok = np.ones(len(hy), dtype=bool)
                for n, d in sol.planes:
                    nb = float(n @ LIGHT)
                    na = P @ n
                    if abs(nb) < 1e-9:
                        ok &= na <= d
                    elif nb < 0:
                        tin = np.maximum(tin, (d - na) / nb)
                    else:
                        tout = np.minimum(tout, (d - na) / nb)
                sh |= ok & (tin < tout)
            shadow[hy, hx] = sh
        light = np.where(shadow, np.minimum(lam, 0.32) * 0.75, lam)
        self.t, self.sid, self.pid, self.light = best_t, best_s, best_p, light
        cv.t = best_t.copy()
        cv.shadow = shadow
        # paint
        for y in range(H):
            for x in range(W):
                si = best_s[y, x]
                if si < 0:
                    continue
                sol = self.solids[si]
                n = N[y, x]
                P3 = (X[y, x], Py[y, x], Pz[y, x])
                u, v, kind = _uv(P3, n, sol)
                c = sol.mat.fn(u, v, kind, float(light[y, x]), P3, sol)
                if c is None:
                    continue
                cv.px[x, y] = C(c)
        self._edges(cv)
        return cv

    def _edges(self, cv):
        """Light the near edge where a face turns away below a brighter one, darken a far face
        where a nearer solid stands in front of it."""
        H, W = self.t.shape
        src = cv.im.copy().load()
        for y in range(H):
            for x in range(W):
                si = self.sid[y, x]
                if si < 0:
                    continue
                t0 = self.t[y, x]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if not (0 <= xx < W and 0 <= yy < H):
                        continue
                    sj = self.sid[yy, xx]
                    if sj < 0:
                        continue
                    if sj != si and self.t[yy, xx] < t0 - 1.5:
                        cv.px[x, y] = _shade(src[x, y], 0.42)  # a nearer solid in front of us
                        break
                    if sj == si and self.pid[yy, xx] != self.pid[y, x]:
                        if dy == 1 and self.light[y, x] > self.light[yy, xx] + 0.05:
                            r, g, b, a = src[x, y]  # a crease: the brighter face's edge catches the light
                            cv.px[x, y] = (min(255, r + 26), min(255, g + 22), min(255, b + 16), a)
                            break
                        if self.light[y, x] < self.light[yy, xx] - 0.12:
                            cv.px[x, y] = _shade(src[x, y], 0.22)  # and the darker one's edge dips
                            break

    def finish(self, cv):
        cv.free()
        cv.outline(self.outline_colour)
        return cv


def _uv(P, n, sol):
    x, y, z = P
    nz = n[2]
    if abs(nz) < 0.2:
        if abs(n[1]) >= abs(n[0]) or sol.params.get("cx") is not None:
            if sol.params.get("cx") is not None:  # round: arc length around the axis
                a = math.atan2(y - sol.params["cy"], x - sol.params["cx"])
                return a * sol.params["r"], z, "wall"
            return x, z, "wall"
        return y, z, "side"
    if sol.params.get("cyl_x") is not None:
        cy, cz, r = sol.params["cyl_x"]
        return x, math.atan2(z - cz, cy - y) * r, "slope"
    if nz > 0.995:
        return x, y, "top"
    # a slope: along the ridge, and up the slope from the eaves
    ze = sol.params.get("ze", 0.0)
    sinp = math.sqrt(max(1e-6, 1 - nz * nz))
    if sol.params.get("cone"):
        a = math.atan2(y - sol.params["cy"], x - sol.params["cx"])
        return a * sol.params["r"], (z - ze) / sinp, "slope"
    if abs(n[0]) > abs(n[1]):
        return y, (z - ze) / sinp, "slope"
    return x, (z - ze) / sinp, "slope"


