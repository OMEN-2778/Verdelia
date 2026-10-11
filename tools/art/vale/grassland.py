#!/usr/bin/env python3
"""Import objects from the "Grassland Top Down Tileset Pixel Art" pack into art/third_party/grassland/,
shifting its yellow-greens toward the Stardust-Vale meadow greens so both sets sit together.

    python3 tools/art/vale/grassland.py <path to the extracted pack>
"""
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pixeltool  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art/third_party/grassland"
KEEP = (["Ruin1_grass_shadow", "Ruin2_grass_shadow", "Ruin3_grass_shadow", "Ruin4_grass_shadow", "Ruin5_grass_shadow"]
        + [f"Stone{i}_grass_shadow" for i in range(1, 6)] + [f"Rpck_grass{i}" for i in range(1, 6)]
        + [f"Bush{i}" for i in range(1, 20)] + [f"Broken_tree{i}" for i in (1, 2, 4, 5)]
        + [f"Flower{i}" for i in range(1, 12)] + ["grass_element1", "grass_element2", "grass_element3"]
        + [f"Rock_grass_element{i}" for i in (11, 12, 13, 14)])


def lch(c):
    L, a, b = pixeltool.srgb_to_oklab(c)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def from_lch(L, C, h):
    r = math.radians(h)
    return pixeltool.oklab_to_srgb((L, C * math.cos(r), C * math.sin(r)))


def main(src):
    src = Path(src) / "PNG" / "Objects_separated"
    target_h = lch((0x6f, 0xbf, 0x55))[2]  # meadow mid green
    greens = []
    for name in KEEP:
        im = Image.open(src / f"{name}.png").convert("RGBA")
        for (r, g, b, a) in im.getdata():
            if a:
                L, C, h = lch((r, g, b))
                if C > 0.05 and 95 < h < 160:
                    greens.append(h)
    shift = target_h - sum(greens) / len(greens)
    OUT.mkdir(parents=True, exist_ok=True)
    cache = {}
    for name in KEEP:
        im = Image.open(src / f"{name}.png").convert("RGBA")
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if not a:
                    continue
                if (r, g, b) not in cache:
                    L, C, h = lch((r, g, b))
                    w = max(0.0, 1 - abs(h - 128) / 45) if C > 0.03 else 0.0  # fade out away from green
                    cache[(r, g, b)] = from_lch(L, C * (1 - 0.1 * w), h + shift * w) if w else (r, g, b)
                px[x, y] = (*cache[(r, g, b)], a)
        im.save(OUT / f"{name}.png")
    print(f"imported {len(KEEP)} objects, green hue shift {shift:+.1f} deg")


if __name__ == "__main__":
    main(sys.argv[1])
