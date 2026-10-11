#!/usr/bin/env python3
"""Pixel-art post-processing for Verdelia: bring third-party sprites into the project palette.

Subcommands:
  palette   write the project palette (hue-shifted ramps) as .gpl + swatch .png
  remap     map every opaque pixel to the nearest project-palette colour (OKLab distance)
  selout    recolour the black outline with a darkened version of the colour it borders
  preview   nearest-neighbour upscale (and optional side-by-side before/after)

Typical use:  remap in.png out.png --selout && preview in.png --after out.png -o cmp.png
Requires Pillow.
"""
import argparse
import colorsys
import math
from pathlib import Path

from PIL import Image

# Base ramps for the Verdelia palette: (name, hue in degrees, saturation 0-1).
# Each ramp gets len(STEPS) steps. Shadows drift toward blue/purple, highlights toward warm yellow,
# which is the classic hue-shifting trick that keeps pixel art from looking muddy.
RAMPS = [
    ("grass", 100, 0.48),
    ("leaf", 140, 0.45),
    ("water", 195, 0.55),
    ("sky", 215, 0.40),
    ("blossom", 340, 0.55),
    ("berry", 2, 0.65),
    ("petal", 22, 0.75),
    ("sun", 42, 0.80),
    ("soil", 25, 0.40),
    ("wood", 30, 0.30),
    ("stone", 230, 0.12),
    ("magic", 275, 0.45),
    ("skin", 22, 0.45),
]
STEPS = [0.18, 0.31, 0.45, 0.59, 0.73, 0.87]  # HSL lightness per step
INK = (0x3a, 0x2a, 0x3e)  # outline colour: a warm plum instead of pure black
PAPER = (0xfb, 0xf5, 0xe6)  # warm off-white


def hue_shift(h, step_index, n):
    t = step_index / (n - 1) - 0.5  # -0.5 (shadow) .. +0.5 (highlight)
    target = 60 if t > 0 else 260  # warm yellow vs cool violet
    d = ((target - h + 540) % 360) - 180
    return (h + d * abs(t) * 0.35) % 360


def build_palette():
    colours = [INK, PAPER]
    for _, hue, sat in RAMPS:
        for i, light in enumerate(STEPS):
            h = hue_shift(hue, i, len(STEPS))
            mid = (len(STEPS) - 1) / 2
            s = sat * (0.75 + 0.5 * (1 - abs(i - mid) / mid))  # mid-tones most saturated
            r, g, b = colorsys.hls_to_rgb(h / 360, light, min(s, 1.0))
            colours.append((round(r * 255), round(g * 255), round(b * 255)))
    return colours


def srgb_to_oklab(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in c)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def nearest(c, pal_lab, pal):
    lab = srgb_to_oklab(c)
    best = min(range(len(pal)), key=lambda i: sum((a - b) ** 2 for a, b in zip(lab, pal_lab[i])))
    return pal[best]


def remap(im, pal, warmth=0.0):
    pal_lab = [srgb_to_oklab(c) for c in pal]
    cache = {}
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            key = (r, g, b)
            if key not in cache:
                src = key
                if warmth:
                    src = (min(255, r + 12 * warmth), g, max(0, b - 10 * warmth))
                cache[key] = nearest(src, pal_lab, pal)
            px[x, y] = (*cache[key], a)
    return out


def selout(im, dark_threshold=0.22):
    """Selective outline: dark outline pixels take a darkened tint of the neighbouring fill."""
    src = im.load()
    out = im.copy()
    px = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = src[x, y]
            if a == 0 or (0.299 * r + 0.587 * g + 0.114 * b) / 255 > dark_threshold:
                continue
            neigh = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < im.width and 0 <= ny < im.height:
                    nr, ng, nb, na = src[nx, ny]
                    if na and (0.299 * nr + 0.587 * ng + 0.114 * nb) / 255 > dark_threshold:
                        neigh.append((nr, ng, nb))
            if not neigh:
                px[x, y] = (*INK, a)
                continue
            mr, mg, mb = (sum(c[i] for c in neigh) / len(neigh) for i in range(3))
            h, l, s = colorsys.rgb_to_hls(mr / 255, mg / 255, mb / 255)
            h = hue_shift(h * 360, 0, len(STEPS)) / 360  # push toward violet like other shadows
            nr, ng, nb = colorsys.hls_to_rgb(h, 0.17, min(1.0, s * 0.8 + 0.1))
            px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def upscale(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def cmd_palette(args):
    pal = build_palette()
    out = Path(args.out)
    n = len(STEPS)
    lines = ["GIMP Palette", "Name: Verdelia", f"Columns: {n}", "#"]
    lines.append(f"{INK[0]:3d} {INK[1]:3d} {INK[2]:3d}\tink")
    lines.append(f"{PAPER[0]:3d} {PAPER[1]:3d} {PAPER[2]:3d}\tpaper")
    for (name, _, _), i in zip(RAMPS, range(len(RAMPS))):
        for j, c in enumerate(pal[2 + i * n : 2 + (i + 1) * n]):
            lines.append(f"{c[0]:3d} {c[1]:3d} {c[2]:3d}\t{name}-{j}")
    out.with_suffix(".gpl").write_text("\n".join(lines) + "\n")
    sw = Image.new("RGBA", (n, len(RAMPS) + 1))
    sw.putpixel((0, 0), (*INK, 255))
    sw.putpixel((1, 0), (*PAPER, 255))
    for i in range(len(RAMPS)):
        for j in range(n):
            sw.putpixel((j, i + 1), (*pal[2 + i * n + j], 255))
    upscale(sw, 16).save(out.with_suffix(".png"))


def cmd_remap(args):
    im = Image.open(args.input).convert("RGBA")
    im = remap(im, build_palette(), args.warmth)
    if args.selout:
        im = selout(im)
    im.save(args.output)


def cmd_selout(args):
    selout(Image.open(args.input).convert("RGBA")).save(args.output)


def cmd_preview(args):
    a = upscale(Image.open(args.input).convert("RGBA"), args.scale)
    if args.after:
        b = upscale(Image.open(args.after).convert("RGBA"), args.scale)
        gap = 2 * args.scale
        canvas = Image.new("RGBA", (a.width + gap + b.width, max(a.height, b.height)), (*PAPER, 255))
        canvas.alpha_composite(a, (0, 0))
        canvas.alpha_composite(b, (a.width + gap, 0))
        a = canvas
    a.save(args.output)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("palette")
    s.add_argument("out", help="output path without extension, e.g. art/palette/verdelia")
    s.set_defaults(func=cmd_palette)

    s = sub.add_parser("remap")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--warmth", type=float, default=1.0, help="0 = neutral, 1 = default warm grade")
    s.add_argument("--selout", action="store_true", help="also apply selective outline")
    s.set_defaults(func=cmd_remap)

    s = sub.add_parser("selout")
    s.add_argument("input")
    s.add_argument("output")
    s.set_defaults(func=cmd_selout)

    s = sub.add_parser("preview")
    s.add_argument("input")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--after", help="second image to place side by side")
    s.add_argument("--scale", type=int, default=4)
    s.set_defaults(func=cmd_preview)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
