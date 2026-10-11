#!/usr/bin/env python3
"""Bake the reusable flora library for the Godot world systems.

Writes art/library/:
  trees/<id>_trunk.png, <id>_crown_<k>.png   per variant (crown layers sway independently)
  bushes/<id>.png, rocks/<id>.png
  tufts.png                                  grass tuft atlas (8x16 cells), see TUFT_* below
  manifest.json                              everything Godot needs: anchors, sizes, sway, groups

Re-run after changing flora.py:  python3 tools/art/vale/library.py
"""
import json
import math
import random
from pathlib import Path

from PIL import Image

import flora

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art/library"

TREES = {  # species: (variants, scale range)
    "oak": (10, (0.75, 1.05)),
    "birch": (6, (0.75, 1.0)),
    "pine": (6, (0.75, 1.05)),
    "blossom": (5, (0.7, 0.95)),
    "sapling": (5, (0.85, 1.1)),
    "oak_far": (8, (0.4, 0.55)),  # small, for distant rows
    "pine_far": (6, (0.4, 0.55)),
}
BUSHES = {"green": 6, "flower": 4, "berry": 4, "pink": 3, "violet": 3}
ROCKS = 8

# grass tufts, ported from stardust-vale's per-blade drawing (3 tones by height, tip highlight)
TUFT_COLOURS = ["#357a36", "#5fae4a", "#a6de72", "#e4f7a8"]
CROP_COLOURS = ["#5fae4a", "#a6de72", "#d6f39a", "#f0fbd0"]
FLOWERS = ["#ffffff", "#ffe066", "#ffc4e1"]
CELL_W, CELL_H = 9, 16
TIP_ALPHA = 250  # tip pixels carry this alpha so the shader can light them in gusts


def hexc(h, a=255):
    return flora.hexc(h, a)


def draw_tuft(img, ox, oy, h, n, colours, flower=None):
    """Blades grow up from the cell's bottom centre; returns nothing, draws into img."""
    base_x, base_y = ox + CELL_W // 2, oy + CELL_H - 1
    for b in range(n):
        bx = base_x + b * 2 - n + 1
        hh = h - (b & 1)
        for k in range(hh):
            lvl = 2 if k == hh - 1 else 1 if k >= hh / 2 else 0
            r, g, bb, _ = hexc(colours[lvl])
            img.putpixel((bx, base_y - k), (r, g, bb, TIP_ALPHA if k == hh - 1 else 255))
    if flower:
        fx, fy = base_x, base_y - h - 1
        c = hexc(flower)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            img.putpixel((fx + dx, fy + dy), c)
        img.putpixel((fx, fy), hexc("#ffffff" if flower == "#ffe066" else "#ffe066"))


def build_tufts(rnd):
    groups = {"short": [], "meadow": [], "flower": [], "tall": [], "crop": []}
    specs = []
    for _ in range(14):
        specs.append(("meadow", rnd.randint(3, 7), rnd.randint(2, 3), None, TUFT_COLOURS))
    for f in FLOWERS * 2:
        specs.append(("flower", rnd.randint(4, 7), rnd.randint(2, 3), f, TUFT_COLOURS))
    for _ in range(8):
        specs.append(("short", rnd.randint(2, 4), 2, None, TUFT_COLOURS))
    for _ in range(14):
        specs.append(("tall", rnd.randint(8, 13), rnd.randint(2, 4), None, TUFT_COLOURS))
    for f in FLOWERS:
        specs.append(("tall", rnd.randint(9, 12), 3, f, TUFT_COLOURS))
    for _ in range(8):
        specs.append(("crop", rnd.randint(3, 6), rnd.choice((2, 3)), None, CROP_COLOURS))
    cols = 16
    rows = (len(specs) + cols - 1) // cols
    atlas = Image.new("RGBA", (cols * CELL_W, rows * CELL_H))
    for i, (group, h, n, fl, colours) in enumerate(specs):
        draw_tuft(atlas, (i % cols) * CELL_W, (i // cols) * CELL_H, h, n, colours, fl)
        groups[group].append(i)
    atlas.save(OUT / "tufts.png")
    return {"cell": [CELL_W, CELL_H], "columns": cols, "rows": rows, "groups": groups}



# ---------------------------------------------------------------- ported from the first vale demo
# marble ruin pillars, the placeholder mage and the soft sky-light textures

TH = {"tuft": TUFT_COLOURS, "trunk": ["#6b4a2e", "#8c6440"],
      "marble": ["#4b5160", "#aab2c4", "#d6dce8", "#eef1f7", "#ffffff"]}
rnd = random.Random(2778)


def rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


MAGE_PAL = {"k": "#160f24", "p": "#5a36a0", "P": "#8e66db", "y": "#ffd166", "s": "#f4c8a3", "S": "#d79b7c",
            "e": "#160f24", "h": "#e9e3ff", "r": "#3550c7", "R": "#5d84f0", "d": "#232c78"}
MAGE_TOP = ["......kkk...", ".....kPPk...", ".....kPpk...", "....kPppk...", "....kPpppk..", "...kyyyyyk..",
            ".kkppppppppk", "..khssssshk.", "..khsesesk..", "...kssSSk...", "..kRrrrrrk..", ".kRRrrrrrdk.",
            ".ksRrrrrdsk.", "..kRrrrrdk..", "..kRrrrrdk..", "..kddddddk.."]
MAGE_FEET = ["...kk..kk...", "..kk....kk..", "...kkkkk....", "....kkkk...."]

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
    leaf = Image.new("RGBA", (3, 2))  # white leaf, tinted per tree in Godot
    for x, y, a in ((0, 0, 255), (1, 0, 255), (1, 1, 255), (2, 1, 180)):
        leaf.putpixel((x, y), (255, 255, 255, a))
    leaf.save(fx / "leaf.png")



def main():
    rnd = random.Random(2778)
    for sub in ("trees", "bushes", "rocks"):
        d = OUT / sub
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.png*"):
            old.unlink()
    manifest = {"trees": {}, "bushes": {}, "rocks": []}
    leaf = {"oak": "#5ba044", "birch": "#a6cf62", "blossom": "#f5b5cd", "sapling": "#5ba044", "pine": "#3d784c"}
    seed = 10000
    for species, (count, (lo, hi)) in TREES.items():
        kind = species.replace("_far", "")
        entries = []
        for v in range(count):
            seed += 1
            scale = round(rnd.uniform(lo, hi), 3)
            trunk, layers, (ax, ay) = flora.tree(kind, seed, scale)
            vid = f"{species}_{v}"
            trunk.save(OUT / "trees" / f"{vid}_trunk.png")
            union, crowns = None, []
            for k, (im, sway) in enumerate(layers):
                im.save(OUT / "trees" / f"{vid}_crown_{k}.png")
                crowns.append({"file": f"trees/{vid}_crown_{k}.png", "sway": round(sway, 3)})
                union = im if union is None else Image.alpha_composite(union, im)
            x0, y0, x1, y1 = union.getbbox()
            entries.append({"id": vid, "trunk": f"trees/{vid}_trunk.png", "crowns": crowns, "anchor": [ax, ay],
                            "crown_rect": [x0 - ax, y0 - ay, x1 - ax, y1 - ay], "scale": scale, "leaf": leaf[kind]})
        manifest["trees"][species] = entries
    for kind, count in BUSHES.items():
        entries = []
        for v in range(count):
            seed += 1
            im = flora.bush(seed, kind, rnd.uniform(0.6, 1.05))
            vid = f"{kind}_{v}"
            im.save(OUT / "bushes" / f"{vid}.png")
            entries.append({"id": vid, "file": f"bushes/{vid}.png", "size": [im.width, im.height]})
        manifest["bushes"][kind] = entries
    for v in range(ROCKS):
        seed += 1
        w = rnd.randint(12, 24)
        im = flora.rock(seed, w, int(w * rnd.uniform(0.6, 0.75)))
        im.save(OUT / "rocks" / f"rock_{v}.png")
        manifest["rocks"].append({"id": f"rock_{v}", "file": f"rocks/rock_{v}.png", "size": [im.width, im.height]})
    manifest["tufts"] = build_tufts(rnd)
    (OUT / "props").mkdir(exist_ok=True)
    for v in (0, 1, 2):
        build_pillar(v).save(OUT / "props" / f"pillar_{v}.png")
    build_mage().save(OUT / "props" / "mage.png")
    save_fx()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    n = sum(len(v) for v in manifest["trees"].values())
    print(f"library: {n} trees, {sum(BUSHES.values())} bushes, {ROCKS} rocks, "
          f"{sum(len(g) for g in manifest['tufts']['groups'].values())} tuft variants")


if __name__ == "__main__":
    main()
