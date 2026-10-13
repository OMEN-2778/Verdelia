#!/usr/bin/env python3
"""Paint the wild flowers scattered over the meadows (the map editor's 野花): small clumps of
leaves and stems with a few blooms each, lit from the top left like everything else, in the
ground's grass greens so they sit in the grass. Original art, drawn here pixel by pixel.

Writes art/library/flowers/<id>.png (16x16, the clump's base at the bottom middle):
  daisy, buttercup, bluebell, clover, poppy, forgetmenot, lavender, dandelion

Re-run after changes:  python3 tools/art/vale/wildflowers.py
"""
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art/library/flowers"
W = H = 16


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


LEAF = [hexc(c) for c in ("#173f22", "#215230", "#2c6a35", "#3d8240", "#5aa04a")]  # dark .. light
STEM = hexc("#2c6a35")


class Clump:
    def __init__(self, seed):
        self.img = Image.new("RGBA", (W, H))
        self.px = self.img.load()
        self.rnd = random.Random(seed)

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[x, y] = c

    def leaves(self, n=5, spread=5, height=(3, 6)):
        """A low mound of leaves at the base (darker than the grass round it, so the clump reads),
        with blades poking up out of it; lighter toward the top left."""
        cx = W // 2
        for x in range(cx - spread, cx + spread + 1):
            d = abs(x - cx + 0.5) / (spread + 0.5)
            h = max(1, round((1 - d * d) * (height[0] + 0.5) + self.rnd.uniform(-0.6, 0.6)))
            for j in range(h):
                t = (j + 1) / h
                tone = 0 if t < 0.34 else (1 if t < 0.7 else 2)
                if x < cx and tone > 0:
                    tone += 1
                self.put(x, H - 1 - j, LEAF[tone])
        for i in range(n):  # blades
            x0 = cx + self.rnd.randint(-spread + 1, spread - 1)
            lean = (x0 - cx) / max(1, spread) * 0.7 + self.rnd.uniform(-0.3, 0.3)
            h = self.rnd.randint(*height)
            for j in range(height[0] - 1, h):
                x = round(x0 + lean * j * 0.6)
                self.put(x, H - 1 - j, LEAF[4 if j == h - 1 else (3 if lean < 0 else 2)])

    def stem(self, x0, top_x, top_y, curve=0.0):
        """A stem from the base (x0, bottom) up to (top_x, top_y), slightly curved."""
        n = H - 1 - top_y
        for j in range(n + 1):
            t = j / max(1, n)
            x = round(x0 + (top_x - x0) * t + curve * t * (1 - t) * 4)
            self.put(x, H - 1 - j, STEM)

    def bloom(self, cx, cy, petal, centre, shape="star"):
        """A bloom seen from the front and above: petals (lit top left, shaded bottom right)
        round a centre."""
        p0, p1, p2 = petal  # shade, mid, light
        if shape == "star":  # five-ish petals: a plus with a lit top-left
            for dx, dy, c in ((-1, 0, p1), (1, 0, p0), (0, -1, p2), (0, 1, p0), (-1, -1, p2)):
                self.put(cx + dx, cy + dy, c)
            self.put(cx, cy, centre)
        elif shape == "wide":  # a bigger open flower, 3 px across with a dark heart
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = p2 if dx + dy < 0 else (p0 if dx + dy > 0 else p1)
                    self.put(cx + dx, cy + dy, c)
            for dx, dy in ((-2, 0), (0, -2)):
                self.put(cx + dx, cy + dy, p1)
            for dx, dy in ((2, 0), (0, 2)):
                self.put(cx + dx, cy + dy, p0)
            self.put(cx, cy, centre)
        elif shape == "dot":  # a tiny two-pixel bud
            self.put(cx, cy, p2)
            self.put(cx + 1, cy, p1)
        elif shape == "ball":  # a round head (clover, dandelion clock)
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1), (1, -1), (-1, 1), (1, 1), (-1, -1)):
                c = p2 if dx + dy < 0 else (p0 if dx + dy > 0 else p1)
                if (dx, dy) in ((1, 1), (-1, -1)) and centre is None:
                    continue
                self.put(cx + dx, cy + dy, c)
        elif shape == "bell":  # a bell hanging from the tip, open at the bottom
            self.put(cx, cy, p2)
            self.put(cx, cy + 1, p1)
            self.put(cx - 1, cy + 1, p2)
            self.put(cx + 1, cy + 1, p0)
            self.put(cx - 1, cy + 2, p1)
            self.put(cx + 1, cy + 2, p0)
        elif shape == "spike":  # a spike of tiny buds up the stem
            for j in range(4):
                self.put(cx, cy + j, p2 if j % 2 == 0 else p1)
                self.put(cx + (1 if j % 2 else -1), cy + j, p0 if j % 2 else p1)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.img.save(OUT / f"{name}.png")


WHITE = (hexc("#c9d3df"), hexc("#eef3f7"), hexc("#ffffff"))
YELLOW = (hexc("#d99a1e"), hexc("#f5c430"), hexc("#ffe680"))
BLUE = (hexc("#3d5fb8"), hexc("#5b86de"), hexc("#9cc0f5"))
VIOLET = (hexc("#5b3f9e"), hexc("#7d5cc9"), hexc("#aa8ff0"))
PINK = (hexc("#b04a7a"), hexc("#dc6f9e"), hexc("#f5a6c6"))
RED = (hexc("#a8242c"), hexc("#d93c35"), hexc("#ff7a5c"))
LAVENDER = (hexc("#6a4aa8"), hexc("#9a78d6"), hexc("#c7b0f2"))
SEED = (hexc("#b9c2cc"), hexc("#e3e8ee"), hexc("#ffffff"))
GOLD = hexc("#f2b632")
DARK = hexc("#3a2418")


def daisy():
    c = Clump(1)
    c.leaves(5, 6, (2, 4))
    for x0, tx, ty in ((7, 3, 8), (7, 6, 5), (8, 9, 3), (9, 12, 6), (8, 10, 9)):
        c.stem(x0, tx, ty + 1, 0.3)
        c.bloom(tx, ty, WHITE, GOLD, "star")
    c.save("daisy")


def buttercup():
    c = Clump(2)
    c.leaves(6, 6, (2, 4))
    for x0, tx, ty in ((6, 3, 9), (7, 5, 6), (8, 8, 4), (8, 10, 7), (9, 13, 9), (8, 7, 9)):
        c.stem(x0, tx, ty + 1)
        c.bloom(tx, ty, YELLOW, YELLOW[2], "star")
    c.save("buttercup")


def bluebell():
    c = Clump(3)
    c.leaves(5, 4, (3, 6))
    for x0, tx, ty, curve in ((7, 5, 4, -0.6), (9, 11, 5, 0.6)):
        c.stem(x0, tx, ty, curve)
        for k, (dx, dy) in enumerate(((0, 0), (-2 if tx < 8 else 2, 3), (-1 if tx < 8 else 1, 6))):
            if dy < 7:
                c.bloom(tx + dx, ty + dy, BLUE if k % 2 == 0 else VIOLET, None, "bell")
    c.save("bluebell")


def clover():
    c = Clump(4)
    # trefoil leaves low down
    c.leaves(0, 6, (3, 3))
    for x, y in ((4, 12), (8, 13), (11, 11), (6, 10), (10, 14)):
        for dx, dy, t in ((0, 0, 3), (-1, 0, 2), (1, 0, 2), (0, -1, 4), (0, 1, 1)):
            c.put(x + dx, y + dy, LEAF[t])
    for x0, tx, ty in ((7, 5, 6), (9, 10, 7), (8, 8, 3)):
        c.stem(x0, tx, ty + 1)
        c.bloom(tx, ty, PINK, True, "ball")
    c.save("clover")


def poppy():
    c = Clump(5)
    c.leaves(4, 6, (3, 5))
    c.stem(7, 5, 6, -0.4)
    c.bloom(5, 5, RED, DARK, "wide")
    c.stem(9, 11, 8, 0.4)
    c.bloom(11, 7, RED, DARK, "star")
    c.put(9, 4, RED[0])  # a bud
    c.stem(8, 9, 5)
    c.save("poppy")


def forgetmenot():
    c = Clump(6)
    c.leaves(6, 7, (2, 4))
    for x0, tx, ty in ((6, 3, 8), (7, 5, 5), (8, 8, 7), (8, 9, 3), (9, 11, 5), (9, 13, 8), (7, 6, 9)):
        c.stem(x0, tx, ty + 1)
        c.bloom(tx, ty, BLUE, hexc("#ffe680"), "star" if ty < 8 else "dot")
    c.save("forgetmenot")


def lavender():
    c = Clump(7)
    c.leaves(6, 5, (3, 5))
    for x0, tx, ty in ((6, 3, 4), (7, 5, 2), (8, 8, 1), (9, 11, 2), (9, 13, 5)):
        c.stem(x0, tx, ty + 4)
        c.bloom(tx, ty, LAVENDER, None, "spike")
    c.save("lavender")


def dandelion():
    c = Clump(8)
    # rosette of toothed leaves flat on the ground
    for x in range(2, 14):
        y = 15 - (1 if x in (4, 7, 10, 12) else 0)
        c.put(x, y, LEAF[2 if x < 8 else 1])
        c.put(x, 15, LEAF[3 if x < 8 else 2])
    c.stem(7, 5, 7)
    c.bloom(5, 6, YELLOW, YELLOW[1], "wide")
    c.stem(8, 8, 10)
    c.bloom(8, 9, YELLOW, YELLOW[1], "star")
    c.stem(9, 11, 5, 0.3)
    c.bloom(11, 4, SEED, None, "ball")  # a seed clock
    c.save("dandelion")


IDS = ["daisy", "buttercup", "bluebell", "clover", "poppy", "forgetmenot", "lavender", "dandelion"]


def main():
    for f in (daisy, buttercup, bluebell, clover, poppy, forgetmenot, lavender, dandelion):
        f()
    print("wildflowers ->", OUT.relative_to(ROOT), len(IDS))


if __name__ == "__main__":
    main()
