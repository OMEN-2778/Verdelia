"""Bigger town buildings with their own silhouettes, in the style and light of buildings.py:
a red barn under a gambrel roof, a windmill whose sails turn (drawn as a separate sprite), an
open-fronted smithy with a glowing forge, a manor with a cross gable, balcony and dormers, and a
round stone tower under a cone roof.
"""
import math
import random

from PIL import Image

from buildings import (DARKWOOD, FIELDSTONE, IRON, LIT, PAINT, ROOFS, STONE, TRIM, WOOD, Canvas, _result, barrel,
                       chimney, door, eave_shadow, flower_box, footing, gable_fill, hanging_sign, lantern, plaster,
                       roof_gable, roof_moss, roof_shingles, sack, stones, timber, tone, window)
from market import CLOTH, pennant

BARN_RED = ["#2e1212", "#5a1f1c", "#842d26", "#a8403a", "#c45a4e", "#db7f6f", "#ecaa98"]
WHITE_TRIM = ["#6d6a66", "#a9a49c", "#d6d1c7", "#efebe3", "#fdfbf6"]
HAY = ["#6b4f17", "#a8822a", "#d4b043", "#efd679", "#fbf0b5"]
CREAM = ["#3d3730", "#8e8474", "#bdb29e", "#d8cfbb", "#e9e2d1", "#f5f0e4", "#fdfbf5"]
EMBER = ["#5a1a08", "#b8400e", "#f07a1e", "#ffc24a", "#fff0a0"]
SAIL = ["#7d7871", "#bcb6ac", "#e4dfd5", "#fbf8f2"]


def roof_profile(cv, seed, x0, x1, ey, depth, ramp, prof):
    """A roof with its gable to the viewer and any cross-section: prof(d) is the height above the
    eaves at d px in from the nearer eave (0..half). The planes run back `depth` px; shading
    follows the slope, so a gambrel's steep lower planes read differently from its flat tops."""
    half = (x1 - x0) / 2
    mid = (x0 + x1) / 2
    for x in range(x0, x1):
        d = half - abs(x + 0.5 - mid)
        h = prof(d)
        slope = prof(min(half, d + 1)) - prof(max(0, d - 1))
        left = x + 0.5 < mid
        steep = slope > 1.6
        for y in range(round(ey - h - depth), round(ey - h) + 1):
            t = (ey - h) - y
            ci = int(d / 4)
            pos = d % 4
            joint = int((t + (ci * 3) % 7) % 7) == 0
            base = (0.74 if left else 0.38) + (-0.06 if steep else 0.06)
            idx = tone(ramp, base - 0.1 * t / depth + ((ci * 37) % 5 - 2) * 0.02)
            if pos < 1:
                c = ramp[min(len(ramp) - 1, idx + 1)]
            elif pos >= 3:
                c = ramp[max(1, idx - 1)]
            elif joint:
                c = ramp[max(1, idx - 2)]
            else:
                c = ramp[idx]
            cv.set(x, y, c)
        yf = round(ey - h)  # barge board along the front, the back edge lit
        cv.set(x, yf, TRIM[3] if left else TRIM[2])
        cv.set(x, yf - 1, TRIM[4] if left else TRIM[3])
        cv.set(x, yf + 1, TRIM[1])
        cv.set(x, round(ey - h - depth), ramp[5] if left else ramp[4])
    cx = int(mid)
    top = round(ey - prof(half))
    for y in range(top - depth, top + 1):  # ridge
        cv.set(cx - 1, y, ramp[5])
        cv.set(cx, y, ramp[3])
    _ = seed


def under_profile(cv, x0, x1, ey, prof, fill, xmin, xmax):
    """Fill the gable wall under a roof_profile with fill(x, y)."""
    half = (x1 - x0) / 2
    mid = (x0 + x1) / 2
    for x in range(xmin, xmax):
        d = half - abs(x + 0.5 - mid)
        for y in range(round(ey - prof(d)) + 2, ey + 1):
            fill(x, y)


def x_door(cv, x0, x1, y0, y1, wall, trim=WHITE_TRIM):
    """A barn door leaf: boards with a white frame and cross braces."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            k = (x - x0) % 4
            cv.set(x, y, wall[3] if k == 0 else wall[1] if k == 3 else wall[2])
    w, h = x1 - x0, y1 - y0
    for i in range(max(w, h)):
        for (xa, ya) in ((x0 + round(i * (w - 1) / max(1, h - 1)), y0 + i), (x1 - 1 - round(i * (w - 1) / max(1, h - 1)), y0 + i)):
            if y0 <= ya < y1:
                cv.set(xa, ya, trim[3])
                cv.set(xa + 1 if xa + 1 < x1 else xa, ya, trim[2])
    for y in range(y0, y1):
        cv.set(x0, y, trim[3])
        cv.set(x0 + 1, y, trim[2])
        cv.set(x1 - 2, y, trim[2])
        cv.set(x1 - 1, y, trim[1])
    for x in range(x0, x1):
        for y in (y0, y0 + 1, y1 - 2, y1 - 1):
            cv.set(x, y, trim[3] if y < y0 + 2 else trim[2])


def hay_bale(cv, x, bottom, w=12, h=8):
    for y in range(bottom - h, bottom):
        for i in range(w):
            ly = y - (bottom - h)
            c = HAY[3] if ly < 2 else HAY[2] if (i + ly * 2) % 5 else HAY[1]
            if i in (0, w - 1) or y == bottom - 1:
                c = HAY[1]
            if i in (3, w - 4):
                c = "#7a5a24"  # twine
            cv.set(x + i, y, c)
    for i in range(1, w - 1, 2):
        cv.set(x + i, bottom - h - 1, HAY[4])


# ================================================================ designs

def barn(spec):
    """A big red barn with its gambrel roof to the front: cross-braced double doors, a hayloft
    door with a hoist beam above, hay bales and a weathervane."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, wall_h, foot_h, over, depth = 76, 32, 4, 4, 18
    wall = BARN_RED
    roof = ROOFS[spec.get("roof_colour", "slate")]
    half = wall_w / 2 + over
    knee = half * 0.36

    def prof(d):  # steep lower slopes, flatter top
        return d * 1.45 if d < knee else knee * 1.45 + (d - knee) * 0.5

    gable_h = math.ceil(prof(half))
    pad = 14
    W = wall_w + 2 * over + 2 * pad
    ey = 2 + 8 + depth + gable_h
    base = ey + wall_h + foot_h
    cv = Canvas(W, base + 6)
    wx0, wx1 = pad + over, pad + over + wall_w
    cxm = W // 2
    # walls: red boards, white corner trim
    for y in range(ey, base - foot_h):
        for x in range(wx0, wx1):
            k = (x - wx0) % 5
            u = (x - wx0) / wall_w
            idx = tone(wall, 0.62 - 0.2 * u)
            cv.set(x, y, wall[idx + 1] if k == 0 else wall[1] if k == 4 else wall[idx])
    for y in range(ey, base - foot_h):
        for i, c in enumerate((WHITE_TRIM[4], WHITE_TRIM[3], WHITE_TRIM[1])):
            cv.set(wx0 + i, y, c)
            cv.set(wx1 - 3 + i, y, (WHITE_TRIM[3], WHITE_TRIM[2], WHITE_TRIM[1])[i])
    footing(cv, rnd, wx0 - 1, wx1 + 1, base - foot_h, base)
    # the big doors
    dw, dh = 30, 26
    x_door(cv, cxm - dw // 2, cxm, base - foot_h - dh, base - foot_h, wall)
    x_door(cv, cxm, cxm + dw // 2, base - foot_h - dh, base - foot_h, wall)
    for y in range(base - foot_h - dh - 3, base - foot_h - dh):  # track beam over them
        for x in range(cxm - dw // 2 - 4, cxm + dw // 2 + 4):
            cv.set(x, y, DARKWOOD[4] if y == base - foot_h - dh - 3 else DARKWOOD[2])
    cv.set(cxm - 2, base - foot_h - dh // 2, IRON[2])
    cv.set(cxm + 1, base - foot_h - dh // 2, IRON[2])
    for wxp in (wx0 + 9, wx1 - 9):  # small high windows
        window(cv, rnd, wxp, ey + 4, w=8, h=7, frame=WHITE_TRIM + ["#ffffff"])
    # gable: boards, trimmed under the roof, a hayloft door with hay and a hoist beam
    gx0, gx1 = wx0 - over, wx1 + over

    def gfill(x, y):
        k = (x - wx0) % 5
        cv.set(x, y, wall[4] if k == 0 else wall[1] if k == 4 else wall[3] if x < cxm else wall[2])

    under_profile(cv, gx0, gx1, ey, prof, gfill, wx0, wx1)
    for x in range(wx0 - 1, wx1 + 1):  # a trim band where the gable meets the wall
        cv.set(x, ey - 1, WHITE_TRIM[3])
        cv.set(x, ey, WHITE_TRIM[2])
        cv.set(x, ey + 1, WHITE_TRIM[1])
    ly0 = ey - 16
    x_door(cv, cxm - 7, cxm + 7, ly0, ly0 + 13, wall)
    for y in range(ly0 + 2, ly0 + 12):
        for x in range(cxm - 5, cxm + 5):
            cv.set(x, y, "#2a1d16")
    for x in range(cxm - 5, cxm + 5):  # hay spilling over the sill
        for i in range(1 + (x * 7) % 3):
            cv.set(x, ly0 + 11 - i, HAY[3] if i == 0 else HAY[2])
    for x in range(cxm - 2, cxm + 3):  # hoist beam
        cv.set(x, ly0 - 4, DARKWOOD[5])
        cv.set(x, ly0 - 3, DARKWOOD[2])
    for y in range(ly0 - 2, ly0 + 3):
        cv.set(cxm, y, "#5c4632")
    cv.set(cxm, ly0 + 3, IRON[2])
    roof_profile(cv, spec.get("seed", 1), gx0, gx1, ey, depth, roof, prof)
    # weathervane: a little iron rooster on the front of the ridge
    top = round(ey - prof(half))
    for y in range(top - 9, top - 1):
        cv.set(cxm - 1, y, IRON[1])
    for dx, dy in ((0, -10), (1, -10), (2, -10), (-1, -11), (0, -11), (1, -11), (2, -11), (3, -12), (-2, -12), (-1, -12), (3, -11), (-1, -13)):
        cv.set(cxm - 1 + dx, top + dy, IRON[1])
    for x in range(cxm - 5, cxm + 4):
        cv.set(x, top - 6, IRON[2])
    eave_shadow(cv, wx0, wx1, ey + 2, rows=3, strength=0.5)
    # hay bales and a pitchfork
    hay_bale(cv, wx0 - 10, base + 1)
    hay_bale(cv, wx0 + 1, base + 2, w=11, h=7)
    hay_bale(cv, wx0 - 5, base - 7, w=11, h=7)
    for y in range(base - 22, base + 1):
        cv.set(wx1 + 4, y, WOOD[4])
    for i in (-1, 0, 1):
        cv.set(wx1 + 4 + i, base - 23, IRON[2])
        cv.set(wx1 + 4 + i, base - 24, IRON[2])
    barrel(cv, wx1 + 6, base + 1)
    cv.outline()
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -34, wall_w, 34], cxm, door_w=dw)


def windmill(spec):
    """A smock windmill: a tapering clapboard tower on a stone base, a domed cap, a door and small
    windows, and the hub for its sails, which come as a separate sprite so they can turn."""
    rnd = random.Random(spec.get("seed", 1))
    W = 64
    body_h, base_h, cap_h = 58, 12, 16
    bot_hw, top_hw = 22, 13
    cxm = W // 2
    sail_len = 40
    top = 6 + sail_len // 2  # leave room for the sails sweeping above the cap
    cap_top = top
    body_top = cap_top + cap_h - 4
    base = body_top + body_h + base_h
    cv = Canvas(W, base + 6)
    clap = CREAM if spec.get("paint", "cream") == "cream" else PAINT[spec["paint"]]
    # stone base
    stones(cv, rnd, cxm - bot_hw - 3, cxm + bot_hw + 3, base - base_h, base, FIELDSTONE, row_h=(3, 4))
    # the tapering body: three facets of clapboard, lit from the left
    for y in range(body_top, base - base_h):
        t = (y - body_top) / body_h
        hw = round(top_hw + (bot_hw - top_hw) * t)
        for x in range(cxm - hw, cxm + hw + 1):
            u = (x - (cxm - hw)) / (2 * hw)
            facet = 0 if u < 0.28 else 1 if u < 0.72 else 2
            v = (0.82, 0.6, 0.3)[facet]
            k = (y - body_top) % 4
            if k == 3:
                v -= 0.25  # clapboard shadow lines
            elif k == 0:
                v += 0.08
            idx = tone(clap, v)
            c = clap[idx]
            if abs(u - 0.28) < 0.02 or abs(u - 0.72) < 0.02:
                c = clap[2]  # facet corners
            cv.set(x, y, c)
    # door with a step, two windows climbing the tower, a little balcony rail
    door(cv, rnd, cxm, base - base_h + 4, w=12, h=18, style="arched", wood=DARKWOOD, step_at=base - 1)
    window(cv, rnd, cxm - 5, body_top + 30, w=8, h=8)
    window(cv, rnd, cxm + 4, body_top + 12, w=7, h=7)
    gy = body_top + 4
    for x in range(cxm - top_hw - 4, cxm + top_hw + 5):  # the stage (gallery) under the cap
        cv.set(x, gy, DARKWOOD[5])
        cv.set(x, gy + 1, DARKWOOD[2])
        if (x - cxm) % 4 == 0:
            for y in range(gy - 4, gy):
                cv.set(x, y, DARKWOOD[4])
    for x in range(cxm - top_hw - 4, cxm + top_hw + 5):
        cv.set(x, gy - 5, DARKWOOD[5])
    # the cap: a rounded, boat-shaped roof of shingles
    roof = ROOFS[spec.get("roof_colour", "bark")]
    cap_hw = top_hw + 5
    for y in range(cap_top, body_top + 2):
        t = (y - cap_top) / (body_top + 2 - cap_top)
        hw = round(cap_hw * math.sqrt(max(0.0, 1 - (1 - t) ** 2)))
        for x in range(cxm - hw, cxm + hw + 1):
            s = (x - cxm) / max(1, hw)
            v = 0.75 - 0.45 * (s + 1) / 2 - 0.1 * t
            if (y - cap_top) % 3 == 2:
                v -= 0.18
            cv.set(x, y, roof[tone(roof, v)])
    for x in range(cxm - cap_hw, cxm + cap_hw + 1):
        cv.set(x, body_top + 2, TRIM[2])
    cv.set(cxm, cap_top - 1, IRON[2])
    cv.set(cxm, cap_top - 2, IRON[2])
    hub = (cxm, cap_top + 8)
    for y in range(hub[1] - 2, hub[1] + 3):  # the windshaft hub
        for x in range(hub[0] - 2, hub[0] + 3):
            if (x - hub[0]) ** 2 + (y - hub[1]) ** 2 <= 5:
                cv.set(x, y, IRON[2] if x + y < sum(hub) else IRON[1])
    sack(cv, cxm + bot_hw - 2, base + 1)
    sack(cv, cxm + bot_hw + 3, base + 2)
    cv.outline()
    # the sails: four lattice blades on a cross, drawn afresh for each frame of a quarter turn
    # (the sails look the same every 90 degrees), so they stay crisp pixel art as they turn
    frames = SAIL_FRAMES
    S = sail_len * 2 + 5
    sheet = Image.new("RGBA", (S * frames, S), (0, 0, 0, 0))
    for f in range(frames):
        sheet.alpha_composite(_sails(sail_len, S, f * (math.pi / 2) / frames), (f * S, 0))
    im, night, info = _result(cv, "house", (W // 2, base), [-bot_hw - 2, -22, 2 * bot_hw + 4, 22], cxm, door_w=12)
    info["sails"] = [hub[0] - W // 2, hub[1] - base]
    info["sails_frames"] = frames
    return im, night, info, {"sails": sheet}


SAIL_FRAMES = 12


def _sails(sail_len, S, turn):
    sails = Canvas(S, S)
    c0 = S // 2
    for k in range(4):
        a = turn + k * math.pi / 2 + math.pi / 4
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx  # each blade lies on one side of its stock
        for s in range(3, sail_len):
            x, y = c0 + dx * s, c0 + dy * s
            if s > 9:
                for o in range(2, 9):
                    for sub in (0.0, 0.5):
                        px, py = round(x + nx * (o + sub)), round(y + ny * (o + sub))
                        grid = s % 5 == 0 or o in (2, 8)
                        sails.set(px, py, DARKWOOD[3] if grid else SAIL[3] if o < 5 else SAIL[2])
        for s in range(3, sail_len):
            x, y = c0 + dx * s, c0 + dy * s
            sails.set(round(x), round(y), DARKWOOD[4])
    for y in range(c0 - 2, c0 + 3):
        for x in range(c0 - 2, c0 + 3):
            if (x - c0) ** 2 + (y - c0) ** 2 <= 5:
                sails.set(x, y, IRON[2])
    sails.outline()
    return sails.im


def smithy(spec):
    """A smithy: a stone house with an open forge shed beside it under a lean-to roof, the hearth
    glowing under its hood and a big chimney, an anvil on a stump, a quench barrel, tools on the
    wall and a grindstone."""
    rnd = random.Random(spec.get("seed", 1))
    W = 108
    house_w, shed_w = 46, 50
    wall_h, foot_h, roof_h = 30, 4, 30
    roof = ROOFS[spec.get("roof_colour", "slate")]
    ridge_y = 2 + 14 + 4
    eave_y = ridge_y + roof_h
    wall_top = eave_y - 4
    base = eave_y + wall_h + foot_h
    cv = Canvas(W, base + 6)
    hx0 = 8
    hx1 = hx0 + house_w
    sx0, sx1 = hx1, hx1 + shed_w
    # the shed first (it is behind the house's corner): back wall, hearth, hood, tools
    shed_top = wall_top + 8
    for y in range(shed_top, base - foot_h):
        for x in range(sx0, sx1):
            cv.set(x, y, "#3a3330" if (x + y * 3) % 7 else "#2f2926")
    stones(cv, rnd, sx0 + 22, sx0 + 42, base - 18, base - foot_h, STONE, row_h=(3, 4))  # the hearth
    for y in range(base - 17, base - 14):  # bed of coals
        for x in range(sx0 + 24, sx0 + 40):
            e = EMBER[3] if (x + y) % 3 else EMBER[4]
            if y == base - 15:
                e = EMBER[2]
            cv.set(x, y, e)
            cv.lit(x, y, LIT[4] if e == EMBER[4] else LIT[3])
    for i in range(6):  # flames licking up
        fx = sx0 + 26 + i * 2 + rnd.randint(0, 1)
        for j in range(rnd.randint(1, 3)):
            cv.set(fx, base - 18 - j, EMBER[3] if j == 0 else EMBER[2])
            cv.lit(fx, base - 18 - j, LIT[3])
    hood_top = shed_top + 2
    for y in range(hood_top, base - 20):  # copper hood narrowing up into the chimney
        t = (y - hood_top) / max(1, base - 20 - hood_top)
        hw = round(4 + 8 * t)
        for x in range(sx0 + 32 - hw, sx0 + 32 + hw):
            u = (x - (sx0 + 32 - hw)) / (2 * hw)
            cv.set(x, y, "#c97a3e" if u < 0.3 else "#9a5a2e" if u < 0.7 else "#6e3e20")
    for x in range(sx0 + 3, sx0 + 19, 4):  # tools hanging on the back wall
        for y in range(shed_top + 6, shed_top + 15):
            cv.set(x, y, IRON[2] if x % 8 else WOOD[3])
        cv.set(x - 1, shed_top + 6, IRON[2])
        cv.set(x + 1, shed_top + 6, IRON[2])
    for x in range(sx0 + 3, sx0 + 19):
        cv.set(x, shed_top + 5, WOOD[3])
    for k in range(3):  # horseshoes
        hx = sx0 + 4 + k * 5
        for dx, dy in ((0, 0), (0, 1), (1, 2), (2, 2), (3, 1), (3, 0)):
            cv.set(hx + dx, shed_top + 18 + dy, IRON[2])
    # anvil on a stump, quench barrel, grindstone
    ax = sx0 + 8
    for y in range(base - 6, base):
        for x in range(ax, ax + 7):
            cv.set(x, y, WOOD[4] if x < ax + 3 else WOOD[2])
    for x in range(ax - 3, ax + 10):
        cv.set(x, base - 9, "#9aa3ad" if x < ax + 4 else "#6e7680")
        cv.set(x, base - 8, "#4f5562")
    for x in range(ax, ax + 7):
        cv.set(x, base - 7, "#4f5562")
    cv.set(ax - 4, base - 9, "#6e7680")
    barrel(cv, sx1 - 10, base + 1, w=8, h=9)
    for x in range(sx1 - 9, sx1 - 3):
        cv.set(x, base - 9, "#3e6f8f")
    # lean-to roof and posts
    for px in (sx0 + 1, sx1 - 3):
        for y in range(shed_top, base):
            cv.set(px, y, TRIM[3])
            cv.set(px + 1, y, TRIM[2])
            cv.set(px + 2, y, TRIM[1])
    roof_shingles(cv, spec.get("seed", 1) + 3, sx0 - 2, sx1 + 3, wall_top - 2, shed_top, roof, ridge=False)
    eave_shadow(cv, sx0 + 3, sx1 - 3, shed_top, rows=6, strength=0.8)
    # big chimney rising from the hood through the shed roof
    chim = chimney(cv, sx0 + 26, 4, wall_top + 2, cw=12)
    # the house part
    stones(cv, rnd, hx0, hx1, wall_top, base - foot_h, STONE)
    footing(cv, rnd, hx0 - 1, hx1 + 1, base - foot_h, base)
    dcx = hx0 + 30
    door(cv, rnd, dcx, base - foot_h, style="plank", wood=DARKWOOD, step_at=base - 1)
    window(cv, rnd, hx0 + 11, base - foot_h - 20, w=12, h=11, shutters=None)
    hanging_sign(cv, hx1, wall_top + 9, "hammer", 1)
    eave_shadow(cv, hx0, hx1, wall_top)
    roof_shingles(cv, spec.get("seed", 1), hx0 - 5, hx1 + 5, ridge_y, eave_y, roof)
    roof_moss(cv, rnd, hx0 - 5, hx1 + 5, eave_y - 4, 3)
    # grindstone in front of the house corner
    gx, gy = hx0 + 3, base + 1
    for y in range(gy - 8, gy - 1):
        for x in range(gx - 3, gx + 4):
            d = (x - gx) ** 2 + (y - (gy - 5)) ** 2
            if d <= 11:
                cv.set(x, y, STONE[4] if x < gx else STONE[3] if d > 2 else STONE[1])
    for y in range(gy - 3, gy):
        cv.set(gx - 4, y, WOOD[3])
        cv.set(gx + 4, y, WOOD[2])
    cv.outline()
    return _result(cv, "house", (W // 2, base), [hx0 - W // 2, -26, sx1 - hx0, 26], dcx, chimneys=[chim])


def manor(spec):
    """A two-storey manor: stone below, plaster and timber above under a long roof, a projecting
    middle bay with its own gable, a balcony and double doors, dormers either side, two chimneys
    and potted bay trees by the door."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, low_h, up_h, foot_h, roof_h, over = 120, 28, 24, 4, 32, 5
    roof = ROOFS[spec.get("roof_colour", "slate")]
    pal = PAINT[spec.get("plaster", "cream")]
    W = wall_w + over * 2 + 4
    ridge_y = 2 + 14 + 4
    eave_y = ridge_y + roof_h
    wall_top = eave_y - 4
    floor_y = wall_top + up_h
    base = floor_y + low_h + foot_h
    cv = Canvas(W, base + 6)
    wx0, wx1 = 2 + over, 2 + over + wall_w
    cxm = W // 2
    # main block
    plaster(cv, rnd, wx0, wx1, wall_top, floor_y, pal)
    timber(cv, wx0, wx1, wall_top, floor_y, studs=(wx0 + 26, wx1 - 29))
    stones(cv, rnd, wx0, wx1, floor_y, base - foot_h, STONE)
    footing(cv, rnd, wx0 - 1, wx1 + 1, base - foot_h, base)
    for frac in (0.1, 0.27, 0.73, 0.9):
        window(cv, rnd, wx0 + round(wall_w * frac), wall_top + 7, w=10, h=10, shutters=spec.get("shutters", "green"))
        window(cv, rnd, wx0 + round(wall_w * frac), floor_y + 6, w=10, h=12, shutters=spec.get("shutters", "green"),
               box=frac in (0.27, 0.73))
    eave_shadow(cv, wx0, wx1, wall_top)
    roof_shingles(cv, spec.get("seed", 1), 2, W - 2, ridge_y, eave_y, roof)
    roof_moss(cv, rnd, 2, W - 2, eave_y - 4, 5)
    chims = [chimney(cv, 10, 2, ridge_y + 8), chimney(cv, W - 20, 2, ridge_y + 8)]
    # dormers on the roof
    for dx in (wx0 + 22, wx1 - 22):
        dy0, dy1 = ridge_y + 14, ridge_y + 25
        plaster(cv, rnd, dx - 7, dx + 7, dy0, dy1, pal)
        window(cv, rnd, dx, dy0 + 2, w=8, h=7)
        for x in range(dx - 8, dx + 8):  # the dormer's sill on the shingles
            cv.set(x, dy1, TRIM[2])
            cv.set(x, dy1 + 1, TRIM[1])
        roof_gable(cv, spec.get("seed", 1) + dx, dx - 10, dx + 10, dy0, 6, roof, slope=0.6)
    # the middle bay, a little proud of the walls
    bw = 40
    bx0, bx1 = cxm - bw // 2, cxm + bw // 2
    bay_top = wall_top - 6
    plaster(cv, rnd, bx0, bx1, bay_top, floor_y, pal)
    timber(cv, bx0, bx1, bay_top, floor_y)
    stones(cv, rnd, bx0, bx1, floor_y, base - foot_h, FIELDSTONE)
    for y in range(bay_top, base - foot_h):  # the bay's shadow on the wall to its right
        for i, k in enumerate((0.45, 0.25, 0.1)):
            cv.darken(bx1 + i, y, k)
    window(cv, rnd, cxm, bay_top + 6, w=14, h=12, arch=True)
    # balcony on the bay
    by = floor_y - 2
    for x in range(bx0 - 2, bx1 + 2):
        cv.set(x, by, DARKWOOD[5])
        cv.set(x, by + 1, DARKWOOD[3])
        cv.set(x, by - 7, DARKWOOD[5])
        if (x - bx0) % 3 == 0:
            for y in range(by - 6, by):
                cv.set(x, y, DARKWOOD[4])
    flower_box(cv, rnd, bx0 + 2, bx0 + 14, by - 9)
    flower_box(cv, rnd, bx1 - 14, bx1 - 2, by - 9)
    for x in range(bx0 - 2, bx1 + 2):  # its shadow
        for i, k in enumerate((0.5, 0.3, 0.12)):
            cv.darken(x, by + 2 + i, k)
    door(cv, rnd, cxm, base - foot_h, w=18, h=22, style="double", wood=DARKWOOD, step_at=base - 1)
    lantern(cv, cxm - 14, base - foot_h - 21)
    lantern(cv, cxm + 12, base - foot_h - 21)
    gx0, gx1 = bx0 - 4, bx1 + 4
    gable_fill(cv, gx0, gx1, bay_top, 0.72, lambda x, y: cv.set(x, y, pal[tone(pal, 0.7 - 0.2 * (x - gx0) / bw)]), bx0, bx1)
    vy = bay_top - 7
    for y in range(vy - 2, vy + 3):
        for x in range(cxm - 3, cxm + 4):
            d = (x - cxm) ** 2 + (y - vy) ** 2
            if d <= 6:
                cv.set(x, y, GLASS_DARK if d <= 2 else DARKWOOD[3])
    roof_gable(cv, spec.get("seed", 1) + 7, gx0, gx1, bay_top, 14, roof)
    eave_shadow(cv, bx0, bx1, bay_top + 1, rows=4, strength=0.6)
    # potted bay trees
    for px in (cxm - 22, cxm + 18):
        for y in range(base - 4, base + 1):
            for x in range(px, px + 5):
                cv.set(x, y, "#9a5a36" if x < px + 3 else "#6e3e24")
        for y in range(base - 12, base - 4):
            for x in range(px - 1, px + 6):
                d = (x - px - 2) ** 2 + (y - (base - 8)) ** 2
                if d <= 12:
                    cv.set(x, y, "#5fa047" if x + y < px + base - 7 else "#3f7a37" if d > 4 else "#2d5a2c")
    cv.outline()
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -32, wall_w, 32], cxm, door_w=18, chimneys=chims)


GLASS_DARK = "#2a3a4e"


def tower(spec):
    """A round stone tower: courses curving round it, arched windows climbing a spiral stair,
    corbels under a cone roof of slate with a flag on top, ivy up one side."""
    rnd = random.Random(spec.get("seed", 1))
    W = 56
    body_hw, body_h = 17, 84
    roof_hw, roof_h = 23, 40
    cxm = W // 2
    roof_top = 14
    eave = roof_top + roof_h
    base = eave + body_h
    cv = Canvas(W, base + 6)
    ramp = STONE

    def bulge(x, hw):  # how much a ring round the tower dips toward us at x (3/4 view)
        u = (x - cxm) / hw
        return math.sqrt(max(0.0, 1 - u * u))

    for x in range(cxm - body_hw, cxm + body_hw + 1):
        u = (x - cxm) / body_hw
        lit = 0.85 - 0.6 * (u + 1) / 2 - 0.2 * abs(u) ** 3
        dip = round(3 * bulge(x, body_hw))
        for y in range(eave - 2, base + dip - 3):
            yy = y - dip
            row = math.floor(yy / 5)
            k = yy - row * 5
            joint = k == 4 or (x * 2 + row * 5) % 11 == 0
            v = lit + ((row * 13 + x // 5) % 7 - 3) * 0.025
            c = ramp[1] if joint else ramp[tone(ramp, v)]
            if k == 0 and not joint:
                c = ramp[min(len(ramp) - 1, tone(ramp, v) + 1)]
            cv.set(x, y, c)
    # the door at the foot and the arched windows climbing round
    door(cv, rnd, cxm - 1, base - 1, w=12, h=19, style="arched", wood=DARKWOOD, step_at=base - 1)
    for i, (dx, wy) in enumerate(((7, base - 38), (-6, base - 58), (5, base - 78))):
        window(cv, rnd, cxm + dx, wy, w=7, h=10, arch=True)
    # corbels under the roof
    for x in range(cxm - body_hw - 1, cxm + body_hw + 2):
        dip = round(3 * bulge(x, body_hw + 1))
        cv.set(x, eave + dip - 1, ramp[5] if x < cxm else ramp[3])
        cv.set(x, eave + dip, ramp[3] if x < cxm else ramp[2])
        if (x - cxm) % 4 == 0:
            cv.set(x, eave + dip + 1, ramp[2])
            cv.set(x, eave + dip + 2, ramp[1])
    # ivy climbing the left side
    vx = cxm - body_hw + 3
    for y in range(base - 46, base - 1):
        x = vx + round(2.5 * math.sin(y * 0.22))
        for dxl in (-1, 0, 1):
            if rnd.random() < 0.55:
                cv.set(x + dxl, y, ("#2d5a2c", "#3f7a37", "#5fa047")[rnd.randint(0, 2)])
    # cone roof: slate rows curving round, lit on the left, a flag on the spire
    roof = ROOFS[spec.get("roof_colour", "slate")]
    for y in range(roof_top, eave + 4):
        t = (y - roof_top) / (eave - roof_top)
        hw = roof_hw * min(1.0, t) ** 1.1
        for x in range(round(cxm - hw), round(cxm + hw) + 1):
            s = (x - cxm) / max(1.0, hw)
            dip = round(4 * math.sqrt(max(0.0, 1 - s * s)) * min(1.0, t))
            if y > round(roof_top + (eave - roof_top) * min(1.0, t)) + dip and t >= 1.0:
                continue
            yy = y - dip
            band = (yy - roof_top) % 4
            v = 0.75 - 0.5 * (s + 1) / 2
            if band == 3:
                v -= 0.22
            cv.set(x, y, roof[tone(roof, v)])
    for x in range(cxm - roof_hw, cxm + roof_hw + 1):  # eave line, curving
        s = (x - cxm) / roof_hw
        dip = round(4 * math.sqrt(max(0.0, 1 - s * s)))
        cv.set(x, eave + dip, TRIM[2] if x < cxm else TRIM[1])
    for y in range(roof_top - 10, roof_top + 1):  # spire and flag
        cv.set(cxm, y, IRON[2])
    pennant(cv, cxm, roof_top - 9, CLOTH[spec.get("flag", "red")], right=True)
    cv.outline()
    return _result(cv, "house", (W // 2, base), [-body_hw, -22, 2 * body_hw + 1, 22], cxm - 1, door_w=12)


DESIGNS = {"barn": barn, "windmill": windmill, "smithy": smithy, "manor": manor, "tower": tower}
