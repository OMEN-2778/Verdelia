#!/usr/bin/env python3
"""Compose a demo scene from the Mana Seed summer forest sample and generate scenes/manaseed_demo.tscn.

The vendor sheets are licensed (no redistribution), so they and everything derived from them stay
in art/vendor/, which is git-ignored. Expects:
    art/vendor/manaseed/summer_sample.png

    python3 tools/art/draw/manaseed_demo.py [--soften]   # --soften: lower contrast before composing
"""
import random
import sys

from PIL import Image

import character
import export_demo
from common import ROOT, TILE

sys.path.insert(0, str(ROOT / "tools/art"))
import pixeltool  # noqa: E402

VENDOR = ROOT / "art/vendor/manaseed"
OUT = ROOT / "art/vendor/demo"
COLS, ROWS = 21, 12

# '.' grass, 'd' dirt path / farm plot
DIRT = [
    ".....................",
    ".....................",
    ".....................",
    ".....................",
    "..dd.................",
    "..dddddddddd.........",
    "..dddddddddd.........",
    "....dddddddd.........",
    "....dddddddd.........",
    "......dd.............",
    "......dd.............",
    "......dd.............",
]


def load():
    sheet = Image.open(VENDOR / "summer_sample.png").convert("RGBA")
    return sheet


def tile(sheet, c, r, w=1, h=1):
    return sheet.crop((c * TILE, r * TILE, (c + w) * TILE, (r + h) * TILE))


def dirt_tile(cells, i, j, rnd):
    """Pick the Mana Seed dirt tile (sheet col, row) for cell (i, j) from its neighbours."""

    def d(x, y):
        return 0 <= y < ROWS and 0 <= x < COLS and cells[y][x] == "d"

    n, s, e, w = d(i, j - 1), d(i, j + 1), d(i + 1, j), d(i - 1, j)
    if not n and not w:
        return 1, 0
    if not n and not e:
        return 3, 0
    if not s and not w:
        return 1, 2
    if not s and not e:
        return 3, 2
    if not n:
        return 2, 0
    if not s:
        return 2, 2
    if not w:
        return 1, 1
    if not e:
        return 3, 1
    if not d(i + 1, j - 1):
        return 1, 4  # grass pokes in at the top-right
    if not d(i - 1, j - 1):
        return 2, 4
    if not d(i + 1, j + 1):
        return 1, 3
    if not d(i - 1, j + 1):
        return 2, 3
    return rnd.choice([(2, 1), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)])


def compose(sheet):
    rnd = random.Random(7)
    ground = Image.new("RGBA", (COLS * TILE, ROWS * TILE))
    for j in range(ROWS):
        for i in range(COLS):
            if DIRT[j][i] == "d":
                c, r = dirt_tile(DIRT, i, j, rnd)
            elif rnd.random() < 0.14:
                c, r = rnd.randrange(4), rnd.choice((6, 7))  # flowers
            else:
                c, r = 0, rnd.randrange(1, 6)
            ground.alpha_composite(tile(sheet, c, r), (i * TILE, j * TILE))

    def stamp(c, r, w, h, x, y):
        ground.alpha_composite(tile(sheet, c, r, w, h), (x * TILE, y * TILE))

    stamp(11, 7, 5, 4, 0, 0)  # cliff with the ruin cave
    stamp(2, 10, 3, 3, 5, 1)  # crumbled stone wall
    stamp(12, 6, 3, 1, 15, 6)  # roots of tree A (trunk and canopy are a sprite)
    stamp(12, 6, 3, 1, 18, 11)  # roots of tree B
    stamp(4, 6, 1, 1, 4, 10)  # pebbles
    stamp(4, 7, 1, 1, 13, 4)  # rock
    stamp(0, 9, 1, 1, 10, 10)  # fern
    stamp(0, 9, 1, 1, 12, 2)

    # Props that sway or need y-sorting; anchors are bottom-centre pixels.
    tree = tile(sheet, 11, 0, 5, 6)
    props = [
        ((16 * TILE + 8, 6 * TILE), "tree", tree),
        ((19 * TILE + 8, 11 * TILE), "tree", tree),
        ((13 * TILE, 11 * TILE), "bush_round", tile(sheet, 2, 8, 2, 2)),
        ((12 * TILE + 8, 6 * TILE), "bush_tall", tile(sheet, 1, 8, 1, 2)),
        ((1 * TILE + 8, 9 * TILE), "bush_small", tile(sheet, 0, 8, 1, 1)),
        ((1 * TILE, 12 * TILE), "boulder", tile(sheet, 3, 14, 2, 2)),
        ((7 * TILE, 11 * TILE), "protagonist", character.front()),
    ]
    return ground, props


def main(soften=False):
    sheet = load()
    if soften:
        sheet = pixeltool.soften(sheet, contrast=0.84, lift=0.05, chroma=1.0, warmth=0.0)
    ground, props = compose(sheet)
    (OUT / "props").mkdir(parents=True, exist_ok=True)
    ground.save(OUT / "ground.png")
    names = {}
    for _a, name, sprite in props:
        if name not in names:
            names[name] = sprite
            sprite.save(OUT / "props" / f"{name}.png")

    extra = [f"""[node name="RuinGlow" type="PointLight2D" parent="." groups=["night_lights"]]
position = Vector2({2 * TILE + 8}, {3 * TILE})
color = Color(0.78, 0.7, 1, 1)
texture = SubResource("light_tex")
texture_scale = 1.6
metadata/day_energy = 0.35
metadata/night_energy = 1.6"""]
    export_demo.SWAY.update({"tree": 0.9, "bush": 0.5})
    path = export_demo.tscn(ground.size, names, props=props, out_path="scenes/manaseed_demo.tscn",
                            art_dir="res://art/vendor/demo", water=False, extra_nodes=extra,
                            grade={"contrast": 0.92, "lift": 0.03, "saturation": 1.05,
                                   "tint": "Color(1, 1, 0.98, 1)", "bloom_strength": 0.4})
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main(soften="--soften" in sys.argv)
