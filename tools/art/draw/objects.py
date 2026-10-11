"""Props, crops and plants. Organic shapes are built from shaded ellipses and tapered leaves,
lit from the top-left, then given a coloured outline (the darkest step of each pixel's ramp)."""
import math
import random

from common import C, COLOURS, TILE, new, stamp

LIGHT = (-0.55, -0.75, 0.37)  # top-left, slightly toward the viewer
_RAMP_OF = {}
for _name, _rgb in COLOURS.items():
    if "-" in _name:
        _RAMP_OF.setdefault(_rgb, _name.rsplit("-", 1)[0])


def _shade(ramp, nx, ny, nz, levels):
    d = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])
    idx = min(len(levels) - 1, int(d * len(levels) * 0.999))
    return C(f"{ramp}-{levels[idx]}")


def ellipse(img, cx, cy, rx, ry, ramp, levels=(1, 2, 3, 4)):
    px = img.load()
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            r2 = dx * dx + dy * dy
            if r2 <= 1 and 0 <= x < img.width and 0 <= y < img.height:
                px[x, y] = _shade(ramp, dx, dy, math.sqrt(max(0.0, 1 - r2)), levels)


def leaf(img, x0, y0, x1, y1, width, ramp, levels=(1, 2, 3)):
    """Tapered leaf from (x0,y0) base to (x1,y1) tip, lit side lighter, with a darker midrib."""
    px = img.load()
    lx, ly = x1 - x0, y1 - y0
    length = math.hypot(lx, ly) or 1
    ux, uy = lx / length, ly / length
    side_light = 1 if (-uy * LIGHT[0] + ux * LIGHT[1]) > 0 else -1
    for y in range(img.height):
        for x in range(img.width):
            qx, qy = x + 0.5 - x0, y + 0.5 - y0
            t = (qx * ux + qy * uy) / length
            if not 0 <= t <= 1:
                continue
            s = -qx * uy + qy * ux  # signed distance from the midrib
            half = width * math.sin(math.pi * min(1.0, t * 1.15)) * (1 - 0.35 * t)
            if abs(s) <= half:
                if abs(s) < 0.5 and 0.15 < t < 0.85:
                    level = levels[0]
                elif s * side_light > 0:
                    level = levels[-1]
                else:
                    level = levels[1]
                px[x, y] = C(f"{ramp}-{level}")


def auto_outline(img):
    """1px outline around the sprite in the darkest step of the neighbouring pixel's ramp."""
    src = img.load()
    out = img.copy()
    px = out.load()
    for y in range(img.height):
        for x in range(img.width):
            if src[x, y][3]:
                continue
            for nx, ny in ((x, y + 1), (x + 1, y), (x - 1, y), (x, y - 1)):
                if 0 <= nx < img.width and 0 <= ny < img.height and src[nx, ny][3] == 255:
                    ramp = _RAMP_OF.get(src[nx, ny][:3])
                    px[x, y] = C(f"{ramp}-0") if ramp else C("ink")
                    break
    return out


def glow(img, cx, cy, radius, ramp="sun", step=5, strength=110):
    """Soft translucent halo behind everything already drawn (used for magic plants)."""
    halo = new(img.width, img.height)
    px = halo.load()
    r, g, b, _ = C(f"{ramp}-{step}")
    for y in range(img.height):
        for x in range(img.width):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / radius
            if d < 1:
                a = int(strength * (1 - d) ** 1.5 / 24) * 24  # banded falloff stays pixel-art friendly
                if a:
                    px[x, y] = (r, g, b, a)
    halo.alpha_composite(img)
    return halo


# ---------------------------------------------------------------- crops


def turnip(stage):
    """Ordinary crop, 4 growth stages: seeds, sprout, leafy, ready to harvest."""
    img = new(TILE, TILE)
    if stage == 0:
        pal = {"s": C("wood-3"), "d": C("soil-0")}
        for x, y in ((5, 9), (9, 8), (7, 11), (10, 11)):
            stamp(img, x, y, ["s", "d"], pal)
        return img
    if stage == 1:
        leaf(img, 8, 14, 4, 9, 1.3, "grass", levels=(1, 2, 3))
        leaf(img, 8, 14, 12, 9, 1.3, "grass", levels=(1, 2, 3))
    elif stage == 2:
        leaf(img, 8, 14, 3, 6, 1.7, "grass", levels=(1, 2, 3))
        leaf(img, 8, 14, 13, 6, 1.7, "grass", levels=(1, 2, 3))
        leaf(img, 8, 14, 8, 3, 1.5, "grass", levels=(1, 2, 3))
    else:
        ellipse(img, 8, 11.5, 3.6, 3.2, "magic", levels=(2, 3, 4, 5))
        px = img.load()
        for y in range(12, 15):  # white lower half of the root
            for x in range(4, 12):
                if px[x, y][3]:
                    px[x, y] = C("stone-4") if x > 8 else C("paper")
        leaf(img, 8, 9, 3, 2, 1.8, "grass", levels=(1, 2, 3))
        leaf(img, 8, 9, 13, 2, 1.8, "grass", levels=(1, 2, 3))
        leaf(img, 8, 9, 8, 0, 1.6, "grass", levels=(1, 2, 3))
    return auto_outline(img)


def lumen_bloom(stage):
    """Magic crop that needs light to sprout (光种): pale stalk, glowing bud, then a lantern bloom."""
    img = new(TILE, TILE)
    if stage == 0:
        stamp(img, 7, 10, [".m.", "mhm", ".m."], {"m": C("magic-3"), "h": C("magic-5")})
        return glow(auto_outline(img), 8, 11, 5, "magic", 4, 80)
    px = img.load()
    top = 9 if stage == 1 else 6
    for y in range(top, 15):
        px[8, y] = C("leaf-3")
        px[7, y] = C("leaf-2")
    leaf(img, 8, 13, 4, 10, 1.6, "leaf")
    leaf(img, 8, 12, 12, 9, 1.6, "leaf")
    if stage == 1:
        ellipse(img, 8, 8, 2, 2.2, "magic", levels=(3, 4, 5, 5))
        return glow(auto_outline(img), 8, 8, 6, "magic", 4, 90)
    ellipse(img, 8, 5, 4, 3.6, "sun", levels=(2, 3, 4, 5))
    for x in range(5, 12, 2):  # petal ribs
        px[x, 7] = C("petal-2")
    px[7, 3], px[8, 3] = C("paper"), C("paper")
    return glow(auto_outline(img), 8, 5, 8, "sun", 5, 130)


def glow_flower():
    """The glowing forest flower from Rosa's errand (发光的花)."""
    img = new(TILE, TILE)
    px = img.load()
    for y in range(8, 15):
        px[8, y] = C("leaf-2")
    leaf(img, 8, 14, 4, 11, 1.4, "leaf")
    leaf(img, 8, 13, 12, 10, 1.4, "leaf")
    for cx, cy in ((6, 6), (10, 6), (8, 4), (8, 8)):
        ellipse(img, cx, cy, 2.1, 2.1, "sky", levels=(3, 4, 5, 5))
    ellipse(img, 8, 6, 1.4, 1.4, "sun", levels=(3, 4, 5, 5))
    return glow(auto_outline(img), 8, 6, 8, "sky", 5, 120)


# ---------------------------------------------------------------- props


def weed(seed=0):
    img = new(TILE, TILE)
    rnd = random.Random(seed)
    for _ in range(5):
        tip = (8 + rnd.uniform(-6, 6), rnd.uniform(3, 8))
        leaf(img, 8 + rnd.uniform(-2, 2), 14, *tip, rnd.uniform(1.2, 1.8), "grass", levels=(0, 1, 2))
    return auto_outline(img)


def rock(seed=0):
    img = new(TILE, TILE)
    ellipse(img, 8, 10, 6, 4.4, "stone", levels=(1, 2, 3, 4))
    ellipse(img, 6, 9, 3, 2.4, "stone", levels=(2, 3, 4, 4))
    px = img.load()
    rnd = random.Random(seed)
    x, y = 9, 8
    for _ in range(4):  # crack
        px[x, y] = C("stone-1")
        x, y = x + rnd.choice((0, 1)), y + 1
    return auto_outline(img)


def fence():
    """Wooden fence: post + rails, 16x16, joins seamlessly left/right."""
    img = new(TILE, TILE)
    pal = {"o": C("wood-0"), "d": C("wood-1"), "m": C("wood-2"), "l": C("wood-3"), "h": C("wood-4")}
    rails = [
        "oooooooooooooooo",
        "llllllllllllllll",
        "mmmmmmmmmmmmmmmm",
        "dddddddddddddddd",
        "oooooooooooooooo",
    ]
    stamp(img, 0, 5, rails, pal)
    stamp(img, 0, 10, rails, pal)
    post = [
        ".oooo.",
        "ohllmo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "olmmdo",
        "omdddo",
        "oooooo",
    ]
    stamp(img, 5, 2, post, pal)
    return img


def bush(berries=True):
    img = new(TILE * 2, TILE * 2)
    for cx, cy, r in ((11, 20, 7), (21, 19, 7), (16, 13, 7), (9, 25, 5), (24, 25, 5), (16, 24, 7)):
        ellipse(img, cx, cy, r, r * 0.9, "grass", levels=(1, 1, 2, 3))
    if berries:
        rnd = random.Random(3)
        px = img.load()
        for _ in range(7):
            x, y = rnd.randrange(8, 25), rnd.randrange(12, 27)
            if px[x, y][3] and px[x + 1, y + 1][3]:
                px[x, y] = C("berry-3")
                px[x + 1, y] = C("berry-2")
                px[x, y + 1] = C("berry-2")
                px[x + 1, y + 1] = C("berry-1")
    return auto_outline(img)


def tree(seed=0):
    """Broadleaf tree, 48x64: a short sturdy trunk and a dense canopy of small leaf clumps."""
    w, h = 48, 64
    img = new(w, h)
    px = img.load()
    for y in range(36, 61):  # trunk, flaring into roots at the base
        spread = 4 + max(0, y - 56)
        for x in range(24 - spread, 24 + spread):
            t = (x - (24 - spread) + 0.5) / (2 * spread)
            px[x, y] = C("wood-3") if t < 0.3 else C("wood-2") if t < 0.7 else C("wood-1")
    for x, y in ((22, 44), (22, 45), (25, 50), (25, 51), (23, 55)):  # bark
        px[x, y] = C("wood-1")
    rnd = random.Random(seed)
    clumps = []
    for _ in range(26):  # dome-shaped cloud of clumps, back to front
        ang = rnd.uniform(math.pi, 2 * math.pi)
        rad = rnd.uniform(0, 1) ** 0.6
        cx = 24 + math.cos(ang) * rad * 15
        cy = 30 + math.sin(ang) * rad * 22
        clumps.append((cx, cy, rnd.uniform(4.5, 7)))
    clumps += [(13, 31, 6), (35, 31, 6), (24, 34, 7), (18, 34, 5), (30, 34, 5)]
    clumps.sort(key=lambda c: c[1])
    for cx, cy, r in clumps:
        ellipse(img, cx, cy, r, r * 0.8, "grass", levels=(1, 1, 2, 3))
    for _ in range(40):  # leaf texture: single bright tips over darker notches
        x, y = rnd.randrange(6, 42), rnd.randrange(4, 38)
        if px[x, y][3] == 255 and px[x, y][:3] == COLOURS["grass-2"] and y + 1 < h and px[x, y + 1][3]:
            px[x, y] = C("grass-3")
            px[x, y + 1] = C("grass-1")
    for x in range(15, 34):  # ground shadow
        for y in (60, 61):
            if not px[x, y][3] and (y == 60 or 18 <= x <= 30):
                px[x, y] = C("ink", 70)
    return auto_outline(img)


def sheet():
    """All 16x16 props in one row: turnip x4, lumen x3, glow flower, weeds x2, rock x2, fence."""
    items = [turnip(s) for s in range(4)] + [lumen_bloom(s) for s in range(3)]
    items += [glow_flower(), weed(0), weed(1), rock(0), rock(1), fence()]
    img = new(TILE * len(items), TILE)
    for i, it in enumerate(items):
        img.alpha_composite(it, (i * TILE, 0))
    return img
