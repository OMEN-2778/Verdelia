#!/usr/bin/env python3
"""Pixel-art post-processing for Verdelia: bring third-party sprites into the project palette.

Subcommands:
  palette   write the project palette (hue-shifted ramps) as .gpl + swatch .png
  remap     map every opaque pixel to the nearest project-palette colour (OKLab distance)
  selout    recolour the black outline with a darkened version of the colour it borders
  soften    lower contrast / lift shadows / desaturate a sheet, colour by colour (keeps pixels crisp)
  preview   nearest-neighbour upscale (and optional side-by-side before/after)

Typical use:  remap in.png out.png --selout && preview in.png --after out.png -o cmp.png
Requires Pillow.
"""
import argparse
import colorsys
import math
from pathlib import Path

from PIL import Image

# Palette presets. Each ramp is (name, hue in degrees, saturation 0-1) and gets len(steps) steps.
# Shadows drift toward blue/purple, highlights toward warm yellow (hue shifting keeps colours alive
# without cranking saturation).
#   sunlit: the project default. Bright and airy but natural: muted, earthy hues, lifted shadows,
#           soft outlines that are only a little darker than the fill. Avoids the cartoon look.
#   vivid:  saturated toy-like look, kept only for comparison.
PRESETS = {
    "sunlit": {
        "ramps": [
            ("grass", 88, 0.38),
            ("leaf", 115, 0.28),
            ("water", 192, 0.38),
            ("sky", 205, 0.40),
            ("blossom", 348, 0.40),
            ("berry", 8, 0.46),
            ("petal", 30, 0.55),
            ("sun", 45, 0.65),
            ("soil", 28, 0.28),
            ("wood", 32, 0.22),
            ("stone", 40, 0.07),
            ("slate", 220, 0.10),
            ("magic", 265, 0.25),
            ("skin", 24, 0.38),
        ],
        "steps": [0.26, 0.39, 0.52, 0.64, 0.76, 0.87],
        "ink": (0x4a, 0x3c, 0x44),
        "paper": (0xf6, 0xf0, 0xe2),
        "outline": "soft",
    },
    "vivid": {
        "ramps": [
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
        ],
        "steps": [0.18, 0.31, 0.45, 0.59, 0.73, 0.87],
        "ink": (0x3a, 0x2a, 0x3e),
        "paper": (0xfb, 0xf5, 0xe6),
        "outline": "dark",
    },
}
DEFAULT_PRESET = "sunlit"


def hue_shift(h, step_index, n):
    t = step_index / (n - 1) - 0.5  # -0.5 (shadow) .. +0.5 (highlight)
    target = 60 if t > 0 else 260  # warm yellow vs cool violet
    d = ((target - h + 540) % 360) - 180
    return (h + d * abs(t) * 0.35) % 360


def build_palette(preset):
    steps = preset["steps"]
    colours = [preset["ink"], preset["paper"]]
    for _, hue, sat in preset["ramps"]:
        for i, light in enumerate(steps):
            h = hue_shift(hue, i, len(steps))
            mid = (len(steps) - 1) / 2
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


def selout(im, preset, dark_threshold=0.22):
    """Selective outline: dark outline pixels take a darkened tint of the neighbouring fill.

    "dark" keeps a strong outline; "soft" keeps it only a step or two darker than the fill,
    which reads as shading rather than an ink line and is much less cartoon-like.
    """
    soft = preset["outline"] == "soft"
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
                px[x, y] = (*preset["ink"], a)
                continue
            mr, mg, mb = (sum(c[i] for c in neigh) / len(neigh) for i in range(3))
            h, l, s = colorsys.rgb_to_hls(mr / 255, mg / 255, mb / 255)
            h = hue_shift(h * 360, 0, len(preset["steps"])) / 360  # push toward violet like other shadows
            if soft:
                light, sat = max(0.22, l * 0.62), s * 0.75
            else:
                light, sat = 0.17, min(1.0, s * 0.8 + 0.1)
            nr, ng, nb = colorsys.hls_to_rgb(h, light, sat)
            px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def oklab_to_srgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )

    def enc(v):
        v = min(1.0, max(0.0, v))
        return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055

    return tuple(round(enc(v) * 255) for v in rgb)


def soften(im, contrast=0.85, lift=0.04, chroma=0.9, warmth=0.01, pivot=0.62):
    """Soft, bright grade applied per unique colour in OKLab, so every pixel stays a flat colour."""
    cache = {}
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, alpha = px[x, y]
            if alpha == 0:
                continue
            if (r, g, b) not in cache:
                L, A, B = srgb_to_oklab((r, g, b))
                L = (L - pivot) * contrast + pivot + lift
                cache[(r, g, b)] = oklab_to_srgb((L, A * chroma + warmth, B * chroma + warmth))
            px[x, y] = (*cache[(r, g, b)], alpha)
    return out


def upscale(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def cmd_palette(args):
    preset = PRESETS[args.preset]
    pal = build_palette(preset)
    ramps, n = preset["ramps"], len(preset["steps"])
    ink, paper = preset["ink"], preset["paper"]
    out = Path(args.out)
    lines = ["GIMP Palette", f"Name: Verdelia ({args.preset})", f"Columns: {n}", "#"]
    lines.append(f"{ink[0]:3d} {ink[1]:3d} {ink[2]:3d}\tink")
    lines.append(f"{paper[0]:3d} {paper[1]:3d} {paper[2]:3d}\tpaper")
    for i, (name, _, _) in enumerate(ramps):
        for j, c in enumerate(pal[2 + i * n : 2 + (i + 1) * n]):
            lines.append(f"{c[0]:3d} {c[1]:3d} {c[2]:3d}\t{name}-{j}")
    out.with_suffix(".gpl").write_text("\n".join(lines) + "\n")
    sw = Image.new("RGBA", (n, len(ramps) + 1))
    sw.putpixel((0, 0), (*ink, 255))
    sw.putpixel((1, 0), (*paper, 255))
    for i in range(len(ramps)):
        for j in range(n):
            sw.putpixel((j, i + 1), (*pal[2 + i * n + j], 255))
    upscale(sw, 16).save(out.with_suffix(".png"))


def cmd_remap(args):
    preset = PRESETS[args.preset]
    im = Image.open(args.input).convert("RGBA")
    if args.selout:
        # Outline first, so the recoloured outline is also snapped onto the palette.
        im = selout(im, preset)
    remap(im, build_palette(preset), args.warmth).save(args.output)


def cmd_selout(args):
    selout(Image.open(args.input).convert("RGBA"), PRESETS[args.preset]).save(args.output)


def cmd_soften(args):
    im = Image.open(args.input).convert("RGBA")
    soften(im, args.contrast, args.lift, args.chroma, args.warmth).save(args.output)


def cmd_preview(args):
    images = [upscale(Image.open(path).convert("RGBA"), args.scale) for path in [args.input, *args.after]]
    gap = 2 * args.scale
    width = sum(im.width for im in images) + gap * (len(images) - 1)
    canvas = Image.new("RGBA", (width, max(im.height for im in images)), (*PRESETS[DEFAULT_PRESET]["paper"], 255))
    x = 0
    for im in images:
        canvas.alpha_composite(im, (x, 0))
        x += im.width + gap
    canvas.save(args.output)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("palette")
    s.add_argument("out", help="output path without extension, e.g. art/palette/verdelia")
    s.add_argument("--preset", choices=PRESETS, default=DEFAULT_PRESET)
    s.set_defaults(func=cmd_palette)

    s = sub.add_parser("remap")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--warmth", type=float, default=1.0, help="0 = neutral, 1 = default warm grade")
    s.add_argument("--preset", choices=PRESETS, default=DEFAULT_PRESET)
    s.add_argument("--selout", action="store_true", help="also apply selective outline")
    s.set_defaults(func=cmd_remap)

    s = sub.add_parser("selout")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--preset", choices=PRESETS, default=DEFAULT_PRESET)
    s.set_defaults(func=cmd_selout)

    s = sub.add_parser("soften")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--contrast", type=float, default=0.85, help="<1 flattens light/dark differences")
    s.add_argument("--lift", type=float, default=0.04, help="raise overall lightness (OKLab L)")
    s.add_argument("--chroma", type=float, default=0.9, help="<1 desaturates")
    s.add_argument("--warmth", type=float, default=0.01, help="push toward warm yellow")
    s.set_defaults(func=cmd_soften)

    s = sub.add_parser("preview")
    s.add_argument("input")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--after", nargs="*", default=[], help="more images to place side by side")
    s.add_argument("--scale", type=int, default=4)
    s.set_defaults(func=cmd_preview)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
