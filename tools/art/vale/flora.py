"""Detailed procedural trees, bushes, rocks and the cliff face for the Stardust-Vale-style scene.

Everything is lit from the upper left. Shapes are built from many small shaded clusters
(foliage) or blocks (rock) and quantised onto short ramps with 4x4 Bayer dithering, so tone
changes read as soft pixel-art gradients rather than flat bands. Every call takes a seed, so
each tree or bush in a scene can be different.
"""
import math
import random

from PIL import Image

BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
_L = (-0.55, -0.68, 0.48)
_LN = math.sqrt(sum(v * v for v in _L))
LIGHT = tuple(v / _LN for v in _L)


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


RAMPS = {
    # dark -> light; index 0 doubles as the outline
    "oak": ["#132a1b", "#1f4427", "#2d6232", "#3f803b", "#5ba044", "#86c25a", "#b8e07e"],
    "birch": ["#22381c", "#335222", "#4a7229", "#649331", "#86b33f", "#b0d35f", "#dcef9a"],
    "pine": ["#0d211b", "#163327", "#204833", "#2c5f3f", "#3d784c", "#58955e", "#86b77e"],
    "blossom": ["#5a2f45", "#83465f", "#ad6684", "#d18aa6", "#e9adc3", "#f7d2de", "#fff3f6"],
    "bush": ["#122a1a", "#1d4325", "#2a5f2f", "#3b7c37", "#579b45", "#7fbd58", "#aedb7a"],
    "bark": ["#25170e", "#3d281a", "#5a3d26", "#7a5636", "#9a7249", "#b8916a"],
    "birchbark": ["#2b2724", "#6d6760", "#a7a198", "#d2cdc3", "#ebe7de", "#fbf9f3"],
    "stone": ["#2b2726", "#47413e", "#655d57", "#837a71", "#a1978b", "#bdb4a6", "#d8d0c2"],
    "rock": ["#3b2a24", "#5e4232", "#82603f", "#a47e52", "#c19c69", "#d9b884", "#ecd2a2", "#f8e8c4"],
    "moss": ["#1f3d22", "#2f5a2c", "#457a36", "#62994a"],
    "flowers": ["#ffffff", "#ffe066", "#ffc4e1", "#c9b3ff"],
}


class Img:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.im.load()

    def inb(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, c):
        x, y = int(x), int(y)
        if self.inb(x, y):
            self.px[x, y] = c

    def get(self, x, y):
        x, y = int(x), int(y)
        return self.px[x, y] if self.inb(x, y) else (0, 0, 0, 0)

    def blend(self, x, y, c):
        x, y = int(x), int(y)
        if not self.inb(x, y):
            return
        r, g, b, a = c
        br, bg, bb, ba = self.px[x, y]
        k = a / 255
        oa = a + ba * (1 - k)
        if oa <= 0:
            return
        m = lambda s, d: round((s * a + d * ba * (1 - k)) / oa)
        self.px[x, y] = (m(r, br), m(g, bg), m(b, bb), round(oa))


def quant(v, x, y, n, lo=1, spread=0.9):
    """Map v in [0,1] to an index lo..n-1 with ordered dithering between steps."""
    t = (BAYER[(y & 3) * 4 + (x & 3)] / 16 - 0.5) * spread
    idx = int(v * (n - lo) + lo - 0.5 + t + 0.5)
    return max(lo, min(n - 1, idx))


def value_noise(seed, cell):
    rnd = random.Random(seed)
    cache = {}

    def lat(ix, iy):
        k = (ix, iy)
        if k not in cache:
            cache[k] = random.Random(hash((seed, ix, iy))).random()
        return cache[k]

    def f(x, y):
        fx, fy = x / cell, y / cell
        ix, iy = math.floor(fx), math.floor(fy)
        tx, ty = fx - ix, fy - iy
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a, b, c, d = lat(ix, iy), lat(ix + 1, iy), lat(ix, iy + 1), lat(ix + 1, iy + 1)
        return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy

    _ = rnd
    return f


def sphere_light(nx, ny):
    d2 = nx * nx + ny * ny
    nz = math.sqrt(max(0.0, 1 - d2))
    return max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])


def silhouette_outline(img, ramp, union):
    """Outline only where this layer meets empty space (not where it overlaps other layers)."""
    src = img.im.copy().load()
    dark, soft = hexc(ramp[0]), hexc(ramp[1])
    for y in range(img.h):
        for x in range(img.w):
            if src[x, y][3] or union[y][x]:
                continue
            if (x > 0 and src[x - 1, y][3]) or (y > 0 and src[x, y - 1][3]):
                img.px[x, y] = dark
            elif (x + 1 < img.w and src[x + 1, y][3]) or (y + 1 < img.h and src[x, y + 1][3]):
                img.px[x, y] = soft


def outline(img, ramp, lit_soft=True):
    """Coloured outline: darkest tone on the shadow side, a softer tone on the lit top-left."""
    src = img.im.copy().load()
    dark, soft = hexc(ramp[0]), hexc(ramp[1])
    for y in range(img.h):
        for x in range(img.w):
            if src[x, y][3]:
                continue
            right = x > 0 and src[x - 1, y][3] == 255
            below = y > 0 and src[x, y - 1][3] == 255
            left = x + 1 < img.w and src[x + 1, y][3] == 255
            above = y + 1 < img.h and src[x, y + 1][3] == 255
            if right or below:
                img.px[x, y] = dark
            elif left or above:
                img.px[x, y] = soft if lit_soft else dark


# ------------------------------------------------------------------ foliage


def foliage(img, ellipses, ramp, seed, cluster_r=(4.0, 6.8), density=1.0, flowers=None, berries=False, bounds=None):
    """Fill a crown silhouette (union of ellipses) with many individually lit leaf clusters.

    bounds=(cx, cy, rx, ry) lights the clusters as part of a larger crown (for layered trees)."""
    rnd = random.Random(seed)
    n = len(ramp)
    x0 = min(cx - rx for cx, cy, rx, ry in ellipses)
    x1 = max(cx + rx for cx, cy, rx, ry in ellipses)
    y0 = min(cy - ry for cx, cy, rx, ry in ellipses)
    y1 = max(cy + ry for cx, cy, rx, ry in ellipses)
    gcx, gcy = (x0 + x1) / 2, (y0 + y1) / 2
    grx, gry = (x1 - x0) / 2, (y1 - y0) / 2
    if bounds:
        gcx, gcy, grx, gry = bounds

    def inside(x, y):
        return any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1 for cx, cy, rx, ry in ellipses)

    # deep interior: the dark heart of the crown that shows between clusters
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            if inside(x + 0.5, y + 0.5):
                g = sphere_light((x - gcx) / grx * 0.9, (y - gcy) / gry * 0.9)
                img.set(x, y, hexc(ramp[1 if g < 0.55 else 2]))

    area = sum(math.pi * rx * ry for _, _, rx, ry in ellipses)
    count = int(area / 26 * density)
    clusters = []
    tries = 0
    while len(clusters) < count and tries < count * 20:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if inside(x, y):
            clusters.append((x, y, rnd.uniform(*cluster_r)))
    clusters.sort(key=lambda c: c[1] + rnd.uniform(-2, 2))  # upper clusters first, lower ones overlap
    leaf_noise = value_noise(seed + 7, 2)
    for cx, cy, r in clusters:
        g = sphere_light((cx - gcx) / grx * 0.95, (cy - gcy) / gry * 0.95)
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx, dy = (x + 0.5 - cx) / r, (y + 0.5 - cy) / (r * 0.85)
                d2 = dx * dx + dy * dy
                if d2 > 1 or not inside(x + 0.5, y + 0.5):
                    continue
                local = sphere_light(dx, dy)
                v = 0.55 * local + 0.55 * g + (leaf_noise(x, y) - 0.5) * 0.14 - 0.1
                if d2 > 0.7 and dx + dy > 0.25:  # shadowed rim separates the clusters
                    v -= 0.3
                img.set(x, y, hexc(ramp[quant(v, x, y, n, lo=1, spread=0.55)]))
    # sparkles of sunlight on the lit side
    for _ in range(int(area / 30)):
        x, y = rnd.uniform(x0, gcx + grx * 0.2), rnd.uniform(y0, gcy)
        if inside(x, y) and img.get(x, y)[3]:
            img.set(x, y, hexc(ramp[-1]))
    # ragged edge: single leaves poking out of the silhouette
    for _ in range(int((grx + gry) * 1.2)):
        a = rnd.uniform(0, math.tau)
        ex, ey = gcx + math.cos(a) * grx * 1.02, gcy + math.sin(a) * gry * 1.02
        for step in range(8):
            px, py = gcx + (ex - gcx) * (1 - step * 0.04), gcy + (ey - gcy) * (1 - step * 0.04)
            if img.get(px, py)[3]:
                ox, oy = round(math.cos(a)), round(math.sin(a))
                tone = 4 if -math.pi * 0.9 < a < -math.pi * 0.1 or a > math.pi * 1.1 else 2
                img.set(px + ox, py + oy, hexc(ramp[min(tone, n - 1)]))
                break
    if flowers:
        for _ in range(int(area / 26)):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if inside(x, y) and img.get(x, y)[3]:
                c = hexc(rnd.choice(flowers))
                img.set(x, y, c)
                if rnd.random() < 0.5:
                    img.set(x + 1, y, c)
    if berries:
        for _ in range(int(area / 40)):
            x, y = rnd.uniform(x0, x1), rnd.uniform(gcy - gry * 0.3, y1)
            if inside(x, y) and img.get(x + 1, y + 1)[3]:
                img.set(x, y, hexc("#e8524a"))
                img.set(x + 1, y, hexc("#b8323a"))
                img.set(x, y + 1, hexc("#b8323a"))
                img.set(x - 1, y - 1, hexc("#ffd0c0"))


def branch(img, x0, y0, x1, y1, w0, w1, ramp, seed):
    """Tapered limb, lit on its upper-left edge."""
    rnd = random.Random(seed)
    n = len(ramp)
    length = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    for i in range(int(length) + 1):
        t = i / length
        cx, cy = x0 + ux * i + math.sin(t * 5 + seed) * 0.6, y0 + uy * i
        w = w0 + (w1 - w0) * t
        for j in range(-int(w), int(w) + 1):
            s = j / max(w, 0.5)
            v = 0.62 - s * 0.45 + rnd.uniform(-0.05, 0.05)
            px, py = cx - uy * j, cy + ux * j
            img.set(px, py, hexc(ramp[quant(v, int(px), int(py), n, lo=1)]))


def trunk(img, base_x, base_y, top_y, width, ramp, seed, lean=0.0, roots=3, birch=False, moss=True):
    rnd = random.Random(seed)
    n = len(ramp)
    bark = value_noise(seed + 3, 3)
    height = base_y - top_y
    for y in range(int(top_y), int(base_y) + 1):
        t = (y - top_y) / max(height, 1)
        half = width / 2 * (0.82 + 0.18 * t) + (max(0, t - 0.85) / 0.15) ** 2 * width * 0.35
        cx = base_x + lean * (1 - t) * height * 0.15
        for x in range(int(cx - half), int(cx + half) + 1):
            s = (x + 0.5 - cx) / max(half, 1)
            if abs(s) > 1:
                continue
            v = 0.85 - (s + 1) * 0.38 + (bark(x * 3, y * 0.6) - 0.5) * 0.3
            if birch and rnd.random() < 0.02 and abs(s) < 0.8:
                for k in range(rnd.randint(2, 4)):
                    img.set(x + k, y, hexc(ramp[0]))
                continue
            img.set(x, y, hexc(ramp[quant(v, x, y, n, lo=1)]))
    if birch:
        for _ in range(int(height / 5)):  # dark lenticel bands across the white bark
            y = rnd.uniform(top_y, base_y - 2)
            cx = base_x + lean * (1 - (y - top_y) / height) * height * 0.15
            x = cx + rnd.uniform(-width / 2, width / 4)
            for k in range(rnd.randint(2, 4)):
                img.set(x + k, y, hexc(ramp[0 if k else 1]))
    for k in range(roots):  # root flares
        side = -1 if k % 2 == 0 else 1
        length = rnd.uniform(width * 0.5, width * 1.0)
        rx0 = base_x + side * width * 0.3
        branch(img, rx0, base_y - 3, rx0 + side * length, base_y + rnd.uniform(-0.5, 1.5), 1.6, 0.4, ramp, seed + 31 * k)
    if moss and not birch:
        mramp = RAMPS["moss"]
        for _ in range(int(width * 2)):
            x = base_x + rnd.uniform(-width / 2, width / 3)
            y = base_y - rnd.uniform(0, height * 0.3) ** 1.0
            if img.get(x, y)[3] and rnd.random() < 0.7:
                img.set(x, y, hexc(mramp[rnd.randint(1, 3)]))


# ------------------------------------------------------------------ trees


TREE_KINDS = {
    # canvas w, h, trunk height (fraction of h), trunk width, limb depth, branch spread (deg),
    # first limb length (fraction of h), length decay, clump radius range, ramp
    "oak": dict(w=86, h=106, trunk=0.36, tw=10, depth=3, spread=(18, 40), len0=0.2, decay=0.74, r=(9, 13), ramp="oak"),
    "birch": dict(w=56, h=104, trunk=0.3, tw=6, depth=3, spread=(8, 22), len0=0.25, decay=0.8, r=(6.5, 9), ramp="birch"),
    "blossom": dict(w=84, h=90, trunk=0.36, tw=8, depth=3, spread=(28, 54), len0=0.2, decay=0.72, r=(8.5, 12), ramp="blossom"),
    "sapling": dict(w=36, h=50, trunk=0.36, tw=4, depth=2, spread=(20, 40), len0=0.2, decay=0.72, r=(5.5, 7.5), ramp="oak"),
}


def tree(kind, seed, scale=1.0):
    """Returns (trunk_img, [(crown_layer_img, sway)], (anchor_x, anchor_y)).

    A branch skeleton is grown first; leaf clumps sit on the branch tips, so every crown has its
    own irregular silhouette with limbs showing between clumps. Each first-level limb's clumps
    are a separate layer so they can sway independently.
    """
    if kind == "pine":
        return pine(seed, scale)
    if kind == "blossom":
        return blossom_tree(seed, scale)
    rnd = random.Random(seed)
    k = TREE_KINDS[kind]
    w, h = int(k["w"] * scale), int(k["h"] * scale)
    ramp = RAMPS[k["ramp"]]
    bramp = RAMPS["birchbark" if kind == "birch" else "bark"]
    tr = Img(w, h)
    ax, ay = w // 2, h - 4
    tw = max(3, round(k["tw"] * scale))
    lean = rnd.uniform(-0.25, 0.25)
    top = (ax + lean * 8 * scale, ay - h * k["trunk"])
    trunk(tr, ax, ay, top[1], tw, bramp, seed, lean=lean, roots=0 if kind == "sapling" else 3, birch=kind == "birch")

    clumps = []  # (cx, cy, rx, ry, group)

    def grow(x, y, ang, length, width, depth, group):
        ex, ey = x + math.cos(ang) * length, y + math.sin(ang) * length
        branch(tr, x, y, ex, ey, width, max(0.6, width * 0.6), bramp, seed + len(clumps) * 13 + depth)
        if depth == 0:
            r = rnd.uniform(*k["r"]) * scale
            ry = r * (rnd.uniform(1.0, 1.25) if kind == "birch" else rnd.uniform(0.72, 0.9))
            droop = r * 0.3 if kind == "birch" else 0
            clumps.append((ex, ey + droop, r, ry, group))
            return
        if depth < k["depth"]:  # a smaller clump along the limb fills the crown interior
            clumps.append(((x + ex) / 2, (y + ey) / 2 - 2, k["r"][0] * scale * 0.8, k["r"][0] * scale * 0.65, group))
        children = 3 if rnd.random() < 0.3 else 2
        for c in range(children):
            off = math.radians(rnd.uniform(*k["spread"])) * (1 if c % 2 else -1)
            grow(ex, ey, ang + off * (0.6 if c == 2 else 1), length * k["decay"] * rnd.uniform(0.82, 1.12),
                 width * 0.62, depth - 1, group)

    limbs = 3 if kind in ("oak", "blossom") else 2
    for g in range(limbs):
        base_ang = -math.pi / 2 + (g - (limbs - 1) / 2) * math.radians(k["spread"][1] * 0.9) + rnd.uniform(-0.15, 0.15)
        grow(top[0], top[1] + rnd.uniform(0, 3), base_ang, h * k["len0"] * rnd.uniform(0.85, 1.1),
             tw * 0.42, k["depth"] - 1, g)
    # core mass in the middle of the canopy (behind the limb clumps) so the crown reads as one tree
    tips = [c for c in clumps if c[4] != -1]
    mcx = sum(c[0] for c in tips) / len(tips)
    mcy = sum(c[1] for c in tips) / len(tips)
    spanx = (max(c[0] for c in tips) - min(c[0] for c in tips)) / 2
    spany = (max(c[1] for c in tips) - min(c[1] for c in tips)) / 2
    clumps.append((mcx, mcy + spany * 0.15, max(spanx * 0.6, k["r"][1] * scale), max(spany * 0.65, k["r"][1] * scale * 0.8), -1))

    # keep every clump inside the canvas
    fixed = []
    for cx, cy, rx, ry, g in clumps:
        cx = min(max(cx, rx + 2), w - rx - 2)
        cy = max(cy, ry + 2)
        fixed.append((cx, cy, rx, ry, g))
    clumps = fixed
    x0 = min(c[0] - c[2] for c in clumps)
    x1 = max(c[0] + c[2] for c in clumps)
    y0 = min(c[1] - c[3] for c in clumps)
    y1 = max(c[1] + c[3] for c in clumps)
    bounds = ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2)

    groups = sorted({c[4] for c in clumps}, key=lambda g: (g != -1, sum(c[1] for c in clumps if c[4] == g)
                                                           / max(1, sum(1 for c in clumps if c[4] == g))))
    layers, imgs = [], []
    for g in groups:
        ell = [(cx, cy, rx, ry) for cx, cy, rx, ry, gg in clumps if gg == g]
        img = Img(w, h)
        foliage(img, ell, ramp, seed + 50 + g * 7, density=1.15, bounds=bounds)
        imgs.append((g, ell, img))
    union = [[any(im.px[x, y][3] for _, _, im in imgs) for x in range(w)] for y in range(h)]
    for g, ell, img in imgs:
        silhouette_outline(img, ramp, union)
        mean_y = sum(e[1] for e in ell) / len(ell)
        height = 1 - (mean_y - y0) / max(y1 - y0, 1)  # higher clumps sway more
        sway = 0.45 if g == -1 else 0.75 + height * 0.6
        layers.append((img.im, sway * (1.25 if kind == "sapling" else 1.0)))
    outline(tr, bramp, lit_soft=False)
    return tr.im, layers, (ax, ay)


def clampf_ang(a):
    """Keep a limb at least ~22 degrees above horizontal (angles measured with y down)."""
    lo, hi = -math.pi + 0.38, -0.38
    return min(max(a, lo), hi)


def blossom_tree(seed, scale=1.0):
    """A cherry in bloom: a short trunk forking into a few limbs that spread wide, carrying flat
    clouds of blossom in uneven tiers with gaps where the dark branches show through; fine petal
    texture, a mauve shaded underside with a few green leaves, airy edges and loose petals.
    Each limb's blossom is its own sway layer, like tree()."""
    rnd = random.Random(seed)
    w, h = int(100 * scale), int(86 * scale)
    ramp = RAMPS["blossom"]
    bramp = RAMPS["bark"]
    tr = Img(w, h)
    ax, ay = w // 2, h - 4
    tw = max(4, round(6.5 * scale))
    lean = rnd.uniform(-0.2, 0.2)
    fork_y = ay - h * rnd.uniform(0.24, 0.3)
    trunk(tr, ax, ay, fork_y, tw, bramp, seed, lean=lean, roots=3)
    fork = (ax + lean * 6 * scale, fork_y)
    clouds = []  # (cx, cy, rx, ry, group)

    def grow(x, y, ang, length, width, depth, group):
        ex, ey = x + math.cos(ang) * length, y + math.sin(ang) * length
        branch(tr, x, y, ex, ey, width, max(0.6, width * 0.6), bramp, seed + len(clouds) * 13 + depth)
        if depth == 0:
            r = rnd.uniform(9.0, 13.0) * scale
            clouds.append((ex, ey - r * 0.1, r, r * rnd.uniform(0.5, 0.62), group))
            if rnd.random() < 0.55:  # a smaller cluster drooping under the tip breaks the flat underside
                sr = r * rnd.uniform(0.45, 0.6)
                clouds.append((ex + rnd.uniform(-r, r) * 0.5, ey + r * 0.42, sr, sr * 0.75, group))
            return
        if depth == 1 and rnd.random() < 0.7:  # a smaller cloud on the limb ties the canopy together
            r = rnd.uniform(7.0, 9.5) * scale
            clouds.append((ex, ey - 2, r, r * 0.55, group))
        for c in range(2):
            off = math.radians(rnd.uniform(18, 34)) * (1 if c else -1)
            # limbs reach outwards more than up: an umbrella, not a ball
            nang = ang + off
            nang = -math.pi / 2 + (nang + math.pi / 2) * 1.12
            nang = clampf_ang(nang)
            grow(ex, ey, nang, length * rnd.uniform(0.62, 0.78), width * 0.6, depth - 1, group)

    limbs = rnd.choice([3, 3, 4])
    for g in range(limbs):
        spread = math.radians(rnd.uniform(62, 74))
        base_ang = -math.pi / 2 + (g - (limbs - 1) / 2) * spread / max(1, (limbs - 1) / 2) * 0.62 + rnd.uniform(-0.12, 0.12)
        grow(fork[0], fork[1] + rnd.uniform(0, 3), base_ang, h * rnd.uniform(0.2, 0.26), tw * 0.45, 2, g)
    # a few clouds high in the middle to round off the top, on their own sway layer
    tips = clouds[:]
    mx = sum(c[0] for c in tips) / len(tips)
    top = min(c[1] - c[3] for c in tips)
    for k in range(rnd.randint(2, 3)):
        r = rnd.uniform(9.0, 12.0) * scale
        clouds.append((mx + rnd.uniform(-14, 14) * scale, top + r * 0.55 + rnd.uniform(0, 5), r, r * 0.55, -1))
    fixed = []
    for cx, cy, rx, ry, g in clouds:
        fixed.append((min(max(cx, rx + 3), w - rx - 3), max(cy, ry + 3), rx, ry, g))
    clouds = fixed
    x0 = min(c[0] - c[2] for c in clouds)
    x1 = max(c[0] + c[2] for c in clouds)
    y0 = min(c[1] - c[3] for c in clouds)
    y1 = max(c[1] + c[3] for c in clouds)
    bounds = ((x0 + x1) / 2, (y0 + y1) / 2 - (y1 - y0) * 0.1, (x1 - x0) / 2, (y1 - y0) / 2)

    groups = sorted({c[4] for c in clouds}, key=lambda g: (g != -1, sum(c[1] for c in clouds if c[4] == g)
                                                           / max(1, sum(1 for c in clouds if c[4] == g))))
    imgs = []
    for g in groups:
        ell = [(cx, cy, rx, ry) for cx, cy, rx, ry, gg in clouds if gg == g]
        img = Img(w, h)
        foliage(img, ell, ramp, seed + 50 + g * 7, cluster_r=(2.4, 3.8), density=1.6, bounds=bounds)
        prnd = random.Random(seed + 90 + g)
        # each cloud: a mauve shaded underside with a few green leaves, a lit top
        for cx, cy, rx, ry in ell:
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    px = img.get(x, y)
                    if not px[3]:
                        continue
                    dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                    if dx * dx + dy * dy > 1.05:
                        continue
                    if dy > 0.4 and prnd.random() < 0.4:
                        img.set(x, y, hexc(ramp[2 if dy > 0.75 else 3]))
                        if prnd.random() < 0.08:
                            img.set(x, y, hexc("#6f9a4c" if prnd.random() < 0.6 else "#4f7a3c"))
                    elif dy < -0.45 and dx < 0.3 and prnd.random() < 0.18:
                        img.set(x, y, hexc(ramp[-1] if prnd.random() < 0.4 else ramp[-2]))
        # airy edge: loose petals just outside the silhouette
        for cx, cy, rx, ry in ell:
            for _ in range(int(rx * 1.4)):
                a = prnd.uniform(0, math.tau)
                d = prnd.uniform(1.0, 1.25)
                px, py = cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d
                if not img.get(px, py)[3]:
                    img.set(px, py, hexc(ramp[prnd.choice([3, 4, 5])]))
        imgs.append((g, ell, img))
    union = [[any(im.px[x, y][3] for _, _, im in imgs) for x in range(w)] for y in range(h)]
    layers = []
    for g, ell, img in imgs:
        silhouette_outline(img, ramp, union)
        mean_y = sum(e[1] for e in ell) / len(ell)
        height = 1 - (mean_y - y0) / max(y1 - y0, 1)
        layers.append((img.im, 0.45 if g == -1 else 0.7 + height * 0.5))
    outline(tr, bramp, lit_soft=False)
    return tr.im, layers, (ax, ay)


def pine(seed, scale=1.0):
    rnd = random.Random(seed)
    w, h = int(44 * scale), int(92 * scale)
    tr, cr = Img(w, h), Img(w, h)
    ax, ay = w // 2, h - 4
    ramp = RAMPS["pine"]
    n = len(ramp)
    trunk(tr, ax, ay, ay - 22, 5, RAMPS["bark"], seed, roots=2)
    tiers = 6
    top = 4
    bottom = ay - 12
    needle = value_noise(seed + 9, 2)
    for i in range(tiers):  # from the top tier down, each tier a drooping skirt
        t0 = i / tiers
        ty0 = top + (bottom - top) * t0 * 0.92
        ty1 = top + (bottom - top) * (i + 1.35) / tiers
        maxhalf = 3 + (w / 2 - 3) * ((i + 1) / tiers) ** 0.9
        for y in range(int(ty0), int(ty1) + 1):
            f = max(0.0, (y - ty0) / max(ty1 - ty0, 1))
            half = maxhalf * (0.25 + 0.75 * f ** 0.8)
            for x in range(int(ax - half - 1), int(ax + half + 2)):
                s = (x + 0.5 - ax) / max(half, 1)
                # jagged lower edge: needles hanging in points
                edge = ty1 - (abs(math.sin((x + seed) * 1.3)) * 3 + rnd.random() * 1.5) * (abs(s) ** 0.5)
                if abs(s) > 1 or y > edge:
                    continue
                v = 0.78 - (s + 1) * 0.3 + (0.25 - f * 0.45) + (needle(x, y * 0.5) - 0.5) * 0.35
                cr.set(x, y, hexc(ramp[quant(v, x, y, n, lo=1)]))
    for _ in range(30):  # snow-bright needle tips on the lit side
        x, y = rnd.uniform(ax - w / 2, ax), rnd.uniform(top, bottom)
        if cr.get(x, y)[3] and not cr.get(x - 1, y - 1)[3]:
            cr.set(x, y, hexc(ramp[-1]))
    outline(cr, ramp)
    outline(tr, RAMPS["bark"], lit_soft=False)
    return tr.im, [(cr.im, 0.4)], (ax, ay)


# ------------------------------------------------------------------ bushes and rocks


def bush(seed, kind="green", size=1.0):
    rnd = random.Random(seed)
    w, h = int(34 * size) + 4, int(26 * size) + 4
    img = Img(w, h)
    cx, by = w / 2, h - 3
    rx, ry = w / 2 - 3, h * 0.42
    ellipses = [(cx, by - ry, rx * 0.8, ry)]
    for k in range(rnd.randint(2, 4)):
        ellipses.append((cx + rnd.uniform(-rx * 0.55, rx * 0.55), by - ry * rnd.uniform(0.6, 1.2),
                         rx * rnd.uniform(0.4, 0.6), ry * rnd.uniform(0.6, 0.85)))
    fl = {"flower": ["#ffffff", "#ffe066"], "pink": ["#ffc4e1", "#ffffff"], "violet": ["#c9b3ff", "#ffffff"]}.get(kind)
    foliage(img, ellipses, RAMPS["bush"], seed, cluster_r=(2.6, 4.2), density=1.2, flowers=fl, berries=kind == "berry")
    outline(img, RAMPS["bush"])
    return img.im


def rock(seed, w=22, h=16, mossy=True):
    rnd = random.Random(seed)
    img = Img(w + 2, h + 2)
    ramp = RAMPS["stone"]
    n = len(ramp)
    cx, cy = w / 2 + 1, h / 2 + 2
    pts = []
    for k in range(9):
        a = k / 9 * math.tau
        pts.append((cx + math.cos(a) * w / 2 * rnd.uniform(0.75, 1.0), cy + math.sin(a) * h / 2 * rnd.uniform(0.7, 1.0)))
    tex = value_noise(seed, 3)

    def inside(x, y):
        c = False
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    for y in range(img.h):
        for x in range(img.w):
            if not inside(x + 0.5, y + 0.5):
                continue
            nx, ny = (x - cx) / (w / 2), (y - cy) / (h / 2)
            # faceted: flatten the normal so the top reads as a plane
            v = sphere_light(nx * 0.9, ny * 0.9 - 0.25) * 0.85 - 0.04 + (tex(x, y) - 0.5) * 0.3
            img.set(x, y, hexc(ramp[quant(v, x, y, n, lo=1)]))
    for _ in range(2):  # cracks
        x, y = rnd.uniform(cx - w / 4, cx + w / 4), cy - h / 4
        for _ in range(int(h / 2)):
            if img.get(x, y)[3]:
                img.set(x, y, hexc(ramp[1]))
                img.set(x - 1, y, hexc(ramp[4]))
            x += rnd.choice((-1, 0, 0, 1))
            y += 1
    if mossy:
        mramp = RAMPS["moss"]
        for y in range(img.h):
            for x in range(img.w):
                if img.get(x, y)[3] and not img.get(x, y - 2)[3] and rnd.random() < 0.75:
                    img.set(x, y, hexc(mramp[3 if x < cx else 2]))
                    if rnd.random() < 0.4:
                        img.set(x, y + 1, hexc(mramp[1]))
    outline(img, ramp)
    return img.im


# ------------------------------------------------------------------ cliff


def paint_cliff(cv, top_y, face, seed, cave_x=None):
    """Layered sandstone cliff across the full width of `cv` (an Img or compatible canvas).

    The top edge undulates, the face is split into strata with irregular blocks, cracks and
    sunlit ledges; moss, hanging vines and small flowers sit on it; rubble at the foot.
    Returns per-column (top, bottom) y so callers can place things along it.
    """
    rnd = random.Random(seed)
    ramp = RAMPS["rock"]
    n = len(ramp)
    W = cv.w
    edge = value_noise(seed, 18)
    base = value_noise(seed + 1, 14)
    tex = value_noise(seed + 2, 3)
    weather = value_noise(seed + 4, 11)  # large lighter/darker weathering patches
    cols = []
    for x in range(W):
        t = int(top_y + (edge(x, 0) - 0.5) * 10)
        b = int(top_y + face + (base(x, 0) - 0.5) * 7)
        cols.append((t, b))
    # strata boundaries (wavy) and vertical cracks per stratum
    strata = 3
    weights = [rnd.uniform(0.7, 1.4) for _ in range(strata)]
    cum = [sum(weights[: k + 1]) / sum(weights) for k in range(strata)]
    bnoise = [value_noise(seed + 10 + k, 16) for k in range(strata)]
    cracks = []
    for k in range(strata):
        xs, x = [], rnd.uniform(0, 12)
        while x < W:
            xs.append(x)
            x += rnd.uniform(14, 36)
        cracks.append(xs)
    for x in range(W):
        t, b = cols[x]
        hgt = b - t
        bounds = [t] + [t + hgt * cum[k] + (bnoise[k](x, 0) - 0.5) * 8 for k in range(strata - 1)] + [b]
        for y in range(t, b):
            k = next(i for i in range(strata) if bounds[i] <= y < bounds[i + 1] or i == strata - 1)
            s0, s1 = bounds[k], bounds[k + 1]
            f = (y - s0) / max(s1 - s0, 1)  # 0 at the ledge top, 1 at the underside
            # distance to the nearest crack in this stratum (slanted a little)
            dxs = [x - (cx + (y - s0) * 0.25) for cx in cracks[k]]
            dc = min(dxs, key=abs) if dxs else 99
            v = 0.74 - f * 0.42 + (tex(x, y) - 0.5) * 0.26 + (weather(x, y) - 0.5) * 0.3
            v -= 0.12 * (y - t) / max(hgt, 1)  # ambient occlusion toward the foot
            if f < 0.12:
                v += 0.28  # sunlit ledge top
            if 0 <= dc < 1.6:
                v -= 0.45  # crack shadow
            elif -1.6 < dc < 0:
                v += 0.12  # lit edge of the next block
            col = hexc(ramp[quant(v, x, y, n, lo=1)])
            if f > 0.9 and rnd.random() < 0.6:
                col = hexc(ramp[1])  # undercut shadow line
            cv.set(x, y, col)
            if f < 0.08 and k > 0 and rnd.random() < 0.35:
                cv.set(x, y, hexc(RAMPS["moss"][rnd.randint(1, 3)]))  # moss on ledges
    # grass lip along the top with overhanging tufts and a shadow under it
    for x in range(W):
        t, _b = cols[x]
        lip = rnd.randint(2, 4)
        for j in range(lip):
            cv.set(x, t - j, hexc(RAMPS["bush"][3 if j == lip - 1 else 2]))
        if rnd.random() < 0.4:
            cv.set(x, t - lip, hexc(RAMPS["bush"][5]))
        cv.blend(x, t + 1, (20, 30, 15, 120))
        cv.blend(x, t + 2, (20, 30, 15, 60))
    # hanging vines with leaves and the odd flower
    x = rnd.uniform(4, 20)
    while x < W:
        if cave_x is not None and abs(x - cave_x) < 18:
            x += 20
            continue
        t, b = cols[int(x)]
        length = rnd.uniform(6, (b - t) * 0.8)
        vx = x
        for j in range(int(length)):
            vy = t + 1 + j
            vx += math.sin(j * 0.6 + x) * 0.25
            cv.set(vx, vy, hexc(RAMPS["bush"][2]))
            if j % 3 == 0:
                side = 1 if (j // 3) % 2 else -1
                cv.set(vx + side, vy, hexc(RAMPS["bush"][4]))
                cv.set(vx + side, vy - 1, hexc(RAMPS["bush"][5]))
            if rnd.random() < 0.05:
                cv.set(vx, vy, hexc(rnd.choice(RAMPS["flowers"])))
        x += rnd.uniform(6, 26)
    # rubble at the foot
    for _ in range(W // 14):
        x = rnd.uniform(0, W)
        _t, b = cols[int(min(x, W - 1))]
        r = rnd.uniform(1.5, 3.5)
        for y in range(int(b - r), int(b + 2)):
            for xx in range(int(x - r - 1), int(x + r + 2)):
                dx, dy = (xx - x) / r, (y - b) / (r * 0.8)
                if dx * dx + dy * dy <= 1:
                    v = sphere_light(dx, dy) + 0.1
                    cv.set(xx, y, hexc(ramp[quant(v, xx, y, n, lo=2)]))
        cv.blend(int(x + r), b + 1, (15, 40, 20, 90))
    return cols
