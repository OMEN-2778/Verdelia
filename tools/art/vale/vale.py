#!/usr/bin/env python3
"""Verdelia farm in the Stardust Vale style (ported from OMEN-2778/stardust-vale, game/p2.js, p3.js, p5.js).

Bakes the static layers (dithered grass and dirt, tilled plot, cliff with the ruin cave, side and
front bushes, baked shadows) plus the sprites (tree trunks/crowns, pillars, the placeholder mage)
and writes art/vale/layout.json for the live parts that Godot animates (tufts, trees, flies).

    python3 tools/art/vale/vale.py
"""
import json
import math
import random
from pathlib import Path

from PIL import Image

import flora

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art/vale"
W, H = 426, 240  # one screen at 3x for 1280x720

# "meadow" theme from stardust-vale; ramps go dark -> light
TH = {
    "grass": ["#3f8f3f", "#55a748", "#6fbf55", "#8fd168"],
    "dirt": ["#a7834f", "#c39d63", "#8a6a3e"],
    "tuft": ["#357a36", "#5fae4a", "#a6de72", "#e4f7a8"],
    "bush": ["#1b3a20", "#2c6532", "#3f8a3e", "#66b152"],
    "leaf": ["#1b3a20", "#2f6b35", "#4a9a42", "#7cc85c"],
    "trunk": ["#6b4a2e", "#8c6440"],
    "cliff": ["#f2dca6", "#dcbb80", "#bb9159", "#82603a"],
    "marble": ["#4b5160", "#aab2c4", "#d6dce8", "#eef1f7", "#ffffff"],
    "flowers": ["#ffffff", "#ffe066", "#ffc4e1"],
    "flower_rate": 0.12,
}
MAGE_PAL = {"k": "#160f24", "p": "#5a36a0", "P": "#8e66db", "y": "#ffd166", "s": "#f4c8a3", "S": "#d79b7c",
            "e": "#160f24", "h": "#e9e3ff", "r": "#3550c7", "R": "#5d84f0", "d": "#232c78"}
MAGE_TOP = ["......kkk...", ".....kPPk...", ".....kPpk...", "....kPppk...", "....kPpppk..", "...kyyyyyk..",
            ".kkppppppppk", "..khssssshk.", "..khsesesk..", "...kssSSk...", "..kRrrrrrk..", ".kRRrrrrrdk.",
            ".ksRrrrrdsk.", "..kRrrrrdk..", "..kRrrrrdk..", "..kddddddk.."]
MAGE_FEET = ["...kk..kk...", "..kk....kk..", "...kkkkk....", "....kkkk...."]

BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
CLIFF_TOP, FACE = 40, 30  # upper meadow above y=40, cliff face below it
CAVE = (86, CLIFF_TOP + FACE)  # bottom-centre of the ruin cave mouth
PLOT = (150, 104, 292, 168)  # tilled farm plot (x0, y0, x1, y1)
PATH = [(CAVE[0], CAVE[1] - 2), (110, 96), (150, 112), (221, 168), (221, 250)]

rnd = random.Random(2778)


def rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def make_noise(w, h, cell):
    gw, gh = math.ceil(w / cell) + 2, math.ceil(h / cell) + 2
    g = [rnd.random() for _ in range(gw * gh)]

    def f(x, y):
        fx, fy = x / cell, y / cell
        ix, iy = math.floor(fx), math.floor(fy)
        tx, ty = fx - ix, fy - iy
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        i0 = iy * gw + ix
        a, b, c, d = g[i0], g[i0 + 1], g[i0 + gw], g[i0 + gw + 1]
        return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy

    return f


class Canvas:
    """Tiny fillRect/alpha canvas over a PIL image, mirroring the 2D-context calls of the original."""

    def __init__(self, w, h):
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.im.load()
        self.w, self.h = w, h

    def put(self, x, y, col):
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        r, g, b, a = col
        if a == 255:
            self.px[x, y] = col
            return
        br, bg, bb, ba = self.px[x, y]
        k = a / 255
        out_a = a + ba * (1 - k)
        if out_a == 0:
            return
        mix = lambda s, d: round((s * a + d * ba * (1 - k)) / out_a)
        self.px[x, y] = (mix(r, br), mix(g, bg), mix(b, bb), round(out_a))

    def rect(self, x, y, w, h, col):
        for j in range(int(h)):
            for i in range(int(w)):
                self.put(x + i, y + j, col)

    def get(self, x, y):
        x, y = int(x), int(y)
        return self.px[x, y] if 0 <= x < self.w and 0 <= y < self.h else (0, 0, 0, 0)

    def set(self, x, y, col):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = col

    def blend(self, x, y, col):
        self.put(x, y, col)

    def paste(self, im, x, y):
        self.im.alpha_composite(im, (int(x), int(y))) if x >= 0 and y >= 0 else self._paste_clipped(im, int(x), int(y))

    def _paste_clipped(self, im, x, y):
        sx, sy = max(0, -x), max(0, -y)
        crop = im.crop((sx, sy, im.width, im.height))
        self.im.alpha_composite(crop, (x + sx, y + sy))


def build_pillar(variant):
    """0: whole column, 1: with vines, 2: broken stump. 16x40, bottom-centre anchored."""
    w, h, M = 16, 40, TH["marble"]
    cv = Canvas(w, h)
    cv.rect(0, 0, w, 7, rgb(M[0]))
    cv.rect(1, 1, w - 2, 5, rgb(M[3]))
    cv.rect(1, 1, w - 2, 1, rgb(M[4]))
    cv.rect(1, 5, w - 2, 1, rgb(M[2]))
    cv.rect(3, 3, w - 6, 1, rgb(M[2]))
    cv.rect(2, 7, w - 4, h - 12, rgb(M[0]))
    for i in range(3, w - 3):
        t = (i - 3) / (w - 7)
        cv.rect(i, 7, 1, h - 13, rgb(M[4] if t < 0.2 else M[3] if t < 0.45 else M[2] if t < 0.75 else M[1]))
    for fx in (5, 8, 11):
        cv.rect(fx, 8, 1, h - 15, rgb(M[1], 115))
    for _ in range(3):  # marble veins
        vx, vy = rnd.randint(4, 11), rnd.randint(10, 28)
        for _ in range(6):
            cv.put(vx, vy, rgb(M[2]))
            vx += rnd.randint(-1, 1)
            vy += 1
            if vx < 3 or vx > w - 4:
                break
    cv.rect(0, h - 6, w, 6, rgb(M[0]))
    cv.rect(1, h - 5, w - 2, 4, rgb(M[2]))
    cv.rect(1, h - 5, w - 2, 1, rgb(M[3]))
    cv.rect(1, h - 2, w - 2, 1, rgb(M[1]))
    if variant == 1:
        for _ in range(26):
            vy = rnd.randint(6, h - 4)
            vx = 3 + round((math.sin(vy * 0.5) + 1) * 4.5)
            col = rgb(TH["tuft"][2] if rnd.random() < 0.3 else TH["tuft"][0])
            cv.put(vx, vy, col)
            if rnd.random() < 0.3:
                cv.put(vx + 1, vy, col)
    if variant == 2:
        for i in range(w):
            cut = 14 + ((i * 7) % 5) + (2 if i > 8 else 0)
            for y in range(cut):
                cv.px[i, y] = (0, 0, 0, 0)
            if 2 <= i < w - 2:
                cv.put(i, cut, rgb(M[0]))
                cv.put(i, cut + 1, rgb(M[4]))
    return cv.im


def build_mage():
    frames = []
    for feet in MAGE_FEET:
        rows = MAGE_TOP + [feet]
        cv = Canvas(12, len(rows))
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    cv.put(i, j, rgb(MAGE_PAL[ch]))
        frames.append(cv.im)
    sheet = Image.new("RGBA", (12 * 4, frames[0].height))
    for k, f in enumerate(frames):
        sheet.alpha_composite(f, (k * 12, 0))
    return sheet


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - (ax + vx * t), py - (ay + vy * t))


def dirt_field(x, y):
    """1 inside the path or plot, fading to 0 over a few pixels outside."""
    d = min(seg_dist(x, y, *PATH[i], *PATH[i + 1]) - 7 for i in range(len(PATH) - 1))
    x0, y0, x1, y1 = PLOT
    dx, dy = max(x0 - 6 - x, 0, x - x1 - 6), max(y0 - 6 - y, 0, y - y1 - 6)
    d = min(d, math.hypot(dx, dy))
    return max(0.0, min(1.0, 1 - d / 7))


def build_ground():
    cv = Canvas(W, H)
    n1, n2, nd = make_noise(W, H, 30), make_noise(W, H, 8), make_noise(W, H, 46)
    GR, DR = [rgb(c) for c in TH["grass"]], [rgb(c) for c in TH["dirt"]]
    dirt = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            b = (BAYER[(y & 3) * 4 + (x & 3)] / 16 - 0.5) * 0.11
            t = n1(x, y) * 0.78 + n2(x, y) * 0.22 + b
            col = GR[0 if t < 0.3 else 1 if t < 0.54 else 2 if t < 0.74 else 3]
            if y > CLIFF_TOP + FACE:
                dd = 0.5 + dirt_field(x, y) * 0.45 + (nd(x, y) - 0.5) * 0.2 + b * 0.8
                if dd > 0.82:
                    col = DR[1 if dd > 0.87 else 2 if t < 0.5 else 0]
                    dirt[y][x] = True
            cv.px[x, y] = col

    # tilled plot: furrow rows inside the farm plot
    x0, y0, x1, y1 = PLOT
    furrow, ridge = rgb("#7d5f38"), rgb(TH["dirt"][1])
    nf = make_noise(W, H, 5)
    for y in range(y0 + 4, y1 - 3):
        row = (y - y0 - 4) % 7
        for x in range(x0 + 6, x1 - 6):
            if nf(x, y) < 0.22:  # crumbled gaps break up the rows
                continue
            if row == 0 and rnd.random() > 0.12:
                cv.put(x, y, furrow)
            elif row == 1 and rnd.random() > 0.25:
                cv.put(x, y, rgb("#6e5232"))
            elif row == 5 and rnd.random() > 0.55:
                cv.put(x, y, ridge)

    # blade strokes and pebbles for texture
    for _ in range(W * H // 380):
        x, y = rnd.randrange(W), rnd.randrange(CLIFF_TOP + FACE + 2, H)
        if dirt[y][x]:
            continue
        cv.rect(x, y, 1, 2, rgb(TH["tuft"][0]))
        cv.put(x, y - 1, rgb(TH["tuft"][2]))
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(CLIFF_TOP + FACE + 4, H)
        cv.rect(x + 1, y + 1, 3, 1, (20, 40, 20, 90))
        cv.rect(x, y, 3, 1, rgb("#9d9a88"))
        cv.put(x, y, rgb("#d9d6c4"))

    # layered sandstone cliff between the upper meadow and the farm
    cols = flora.paint_cliff(cv, CLIFF_TOP, FACE, 41, cave_x=CAVE[0])
    for x in range(W):  # the cliff shades the meadow right below it
        for i in range(6):
            cv.put(x, cols[x][1] + 1 + i, (20, 40, 25, round((0.26 - i * 0.04) * 255)))

    draw_cave(cv)

    # bushes framing the sides, all different
    kinds = ["green", "green", "flower", "berry", "pink", "violet"]
    y, k = CLIFF_TOP + FACE - 6, 0
    while y < H + 14:
        for side in (0, 1):
            b = flora.bush(500 + k, rnd.choice(kinds), rnd.uniform(0.75, 1.05))
            x = -b.width // 2 + rnd.randint(-2, 4) if side == 0 else W - b.width // 2 + rnd.randint(-4, 2)
            cv.paste(b, x, y - b.height + 6)
            k += 1
        y += rnd.randint(13, 18)
    return cv, dirt


def draw_cave(cv):
    """A ruin doorway cut into the cliff: dark arch, marble frame and a worn step."""
    cx, by = CAVE
    M = TH["marble"]
    for y in range(by - 24, by):
        for x in range(cx - 13, cx + 14):
            nx, ny = (x - cx) / 12.5, (y - (by - 9)) / 15
            if nx * nx + min(0, ny) ** 2 * 1.0 <= 1 and y >= by - 24:
                depth = (y - (by - 24)) / 24
                cv.put(x, y, rgb("#1d1428") if depth < 0.6 else rgb("#2a1d3a"))
    for side in (-1, 1):  # marble jambs
        x = cx + side * 14 - (1 if side > 0 else 0)
        cv.rect(x - 1, by - 18, 3, 18, rgb(M[0]))
        cv.rect(x, by - 17, 1, 16, rgb(M[3] if side < 0 else M[2]))
    for a in range(0, 181, 6):  # arch stones
        r = math.radians(a)
        x, y = round(cx + math.cos(r) * 14), round(by - 18 - math.sin(r) * 9)
        cv.rect(x - 1, y - 1, 3, 3, rgb(M[0]))
        cv.put(x, y, rgb(M[3] if a > 90 else M[2]))
    cv.rect(cx - 15, by, 31, 3, rgb(M[0]))
    cv.rect(cx - 14, by, 29, 2, rgb(M[2]))
    cv.rect(cx - 14, by, 29, 1, rgb(M[3]))


def save_fx():
    """Soft textures for the sky light: cloud shadow blob, light shaft, contact shadow."""
    fx = OUT / "fx"
    fx.mkdir(exist_ok=True)
    cloud = Image.new("RGBA", (200, 120), (10, 38, 32, 0))
    acc = [[0.0] * 200 for _ in range(120)]
    for _ in range(8):
        cx, cy, r = rnd.uniform(50, 150), rnd.uniform(40, 80), rnd.uniform(24, 44)
        for y in range(120):
            for x in range(200):
                d = math.hypot(x - cx, y - cy) / r
                if d < 1:
                    a = 0.9 - 0.4 * d / 0.6 if d < 0.6 else 0.5 * (1 - (d - 0.6) / 0.4)
                    acc[y][x] = acc[y][x] + a * (1 - acc[y][x])
    for y in range(120):
        for x in range(200):
            cloud.putpixel((x, y), (10, 38, 32, round(acc[y][x] * 255)))
    cloud.save(fx / "cloud.png")
    shaft = Image.new("RGBA", (64, 256))
    for y in range(256):
        v = y / 255
        va = v / 0.2 if v < 0.2 else 1 - 0.45 * (v - 0.2) / 0.55 if v < 0.75 else 0.55 * (1 - (v - 0.75) / 0.25)
        for x in range(64):
            ha = 1 - abs(x / 63 - 0.5) * 2
            shaft.putpixel((x, y), (255, 255, 255, round(ha * va * 255)))
    shaft.save(fx / "shaft.png")
    shadow = Image.new("RGBA", (13, 5))
    for y in range(5):
        for x in range(13):
            if ((x - 6) / 6.5) ** 2 + ((y - 2) / 2.5) ** 2 <= 1:
                shadow.putpixel((x, y), (13, 36, 20, 92))
    shadow.save(fx / "shadow.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "props").mkdir(exist_ok=True)
    cv, dirt = build_ground()

    # trees: every one generated with its own seed; species and size vary
    trees = []
    x = -16
    while x < W + 24:  # upper meadow, two loose depth rows
        kind = rnd.choices(["oak", "pine", "birch", "blossom"], [5, 3, 2, 1])[0]
        trees.append({"x": x + rnd.uniform(-5, 5), "y": CLIFF_TOP - rnd.uniform(2, 9), "kind": kind,
                      "scale": rnd.uniform(0.6, 0.85)})
        x += rnd.randint(22, 34)
    for tx, ty, kind, sc in [(16, 150, "oak", 0.9), (6, 226, "pine", 0.85), (404, 132, "oak", 0.85),
                             (414, 212, "birch", 0.9), (346, 102, "blossom", 0.75), (372, 120, "sapling", 1.0),
                             (60, 236, "sapling", 0.9), (300, 104, "birch", 0.65)]:
        trees.append({"x": tx, "y": ty, "kind": kind, "scale": sc})
    (OUT / "props" / "trees").mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(trees):
        trunk_im, crown_im, (ax, ay), sway = flora.tree(t["kind"], 1000 + i, t["scale"])
        trunk_im.save(OUT / "props" / "trees" / f"tree_{i}_trunk.png")
        crown_im.save(OUT / "props" / "trees" / f"tree_{i}_crown.png")
        t.update({"i": i, "ax": ax, "ay": ay, "sway": sway, "ph": rnd.random() * math.tau})
        half_w = crown_im.width * 0.32
        for j in range(-4, 5):  # baked ground shadow, cast to the lower right
            half = round(math.sqrt(1 - (j / 5) ** 2) * half_w)
            cv.rect(round(t["x"] + half_w * 0.4 - half), round(t["y"] + j), half * 2, 1, (15, 45, 25, 77))

    # mossy boulders
    rocks = []
    for rx, ry, rw, rh in [(132, 206, 22, 15), (312, 150, 16, 11), (382, 176, 20, 14), (30, 186, 14, 10)]:
        im = flora.rock(rx * 7 + ry, rw, rh)
        for j in range(3):
            cv.rect(rx - rw // 2 + 2 + j, ry + j - 1, rw, 1, (15, 45, 25, 70 - j * 18))
        cv.paste(im, rx - im.width // 2, ry - im.height + 2)
        rocks.append((rx, ry, rw))

    pillars = [{"x": 40, "y": 112, "v": 0}, {"x": 122, "y": 92, "v": 2}, {"x": 58, "y": 98, "v": 1},
               {"x": 318, "y": 182, "v": 2}]
    for p in pillars:
        length = 14 if p["v"] == 2 else 28
        for k in range(length):
            cv.rect(round(p["x"] - 6 + k * 0.9), round(p["y"] + 1 + k * 0.35), 12, 1, (15, 45, 25, 82))

    # front layer: a row of bushes along the bottom edge
    front = Canvas(W, H)
    x, k = -14, 0
    while x < W + 14:
        b = flora.bush(800 + k, rnd.choice(["green", "green", "flower", "berry"]), rnd.uniform(0.65, 0.9))
        front.paste(b, x, H - b.height + 14 + rnd.randint(-2, 3))
        x += rnd.randint(22, 34)
        k += 1

    # living grass tufts (drawn and swayed by Godot), sprouts in the plot
    tufts = []
    x0, y0, x1, y1 = PLOT
    for _ in range(W * H // 150):
        x, y = rnd.randint(4, W - 4), rnd.randint(CLIFF_TOP + FACE + 4, H - 2)
        if dirt[y][x] or any(abs(p["x"] - x) < 9 and abs(p["y"] - y) < 5 for p in pillars) \
                or any(abs(rx - x) < rw / 2 + 2 and ry - 10 < y < ry + 3 for rx, ry, rw in rocks):
            continue
        fl = rnd.choice(TH["flowers"]) if rnd.random() < TH["flower_rate"] else None
        tufts.append({"x": x, "y": y, "h": rnd.randint(3, 7), "n": rnd.randint(2, 3), "fl": fl})
    for y in range(y0 + 9, y1 - 4, 7):  # crop seedlings on the ridges
        for x in range(x0 + 12, x1 - 10, 9):
            if rnd.random() < 0.8:
                tufts.append({"x": x + rnd.randint(-1, 1), "y": y, "h": rnd.randint(3, 5), "n": 2, "fl": None, "crop": 1})
    for _ in range(60):  # tufts on the upper meadow too
        x, y = rnd.randint(4, W - 4), rnd.randint(6, CLIFF_TOP - 4)
        tufts.append({"x": x, "y": y, "h": rnd.randint(3, 6), "n": rnd.randint(2, 3), "fl": None})
    tufts.sort(key=lambda t: t["y"])

    cv.im.save(OUT / "ground.png")
    front.im.save(OUT / "front.png")
    for v in (0, 1, 2):
        build_pillar(v).save(OUT / "props" / f"pillar_{v}.png")
    build_mage().save(OUT / "props" / "mage.png")
    save_fx()
    layout = {"size": [W, H], "tuft_colours": TH["tuft"], "cave": CAVE, "trees": trees, "pillars": pillars,
              "tufts": tufts, "player": [221, 196]}
    (OUT / "layout.json").write_text(json.dumps(layout))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(tufts)} tufts, {len(trees)} trees")


if __name__ == "__main__":
    main()
