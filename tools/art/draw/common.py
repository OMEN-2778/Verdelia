"""Shared helpers for the hand-made Verdelia art: palette lookup, seeded noise, outlines.

All sprites are drawn in code so they can be tweaked and regenerated. Colours always come
from the project palette (art/palette/verdelia.gpl) so every sheet stays consistent.
"""
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pixeltool  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art"
TILE = 16

_preset = pixeltool.PRESETS[pixeltool.DEFAULT_PRESET]
_pal = pixeltool.build_palette(_preset)
_n = len(_preset["steps"])
COLOURS = {"ink": _pal[0], "paper": _pal[1]}
for _i, (_name, _, _) in enumerate(_preset["ramps"]):
    for _j in range(_n):
        COLOURS[f"{_name}-{_j}"] = _pal[2 + _i * _n + _j]


def C(name, alpha=255):
    """Palette colour by name, e.g. C('grass-2')."""
    return (*COLOURS[name], alpha)


CLEAR = (0, 0, 0, 0)


def new(w, h, fill=CLEAR):
    return Image.new("RGBA", (w, h), fill)


def periodic_noise(x, y, seed, period=TILE, cells=(4, 8), weights=(0.65, 0.35)):
    """Smooth value noise in about [-1, 1] that wraps every `period` pixels, so tile edges line up.

    `cells` are lattice sizes in pixels (must divide `period`); blobs, not stripes.
    """
    v = 0.0
    for k, (cell, weight) in enumerate(zip(cells, weights)):
        n = period // cell
        rnd = random.Random(seed * 1000 + k)
        lattice = [[rnd.uniform(-1, 1) for _ in range(n)] for _ in range(n)]
        gx, gy = (x % period) / cell, (y % period) / cell
        x0, y0 = int(gx), int(gy)
        fx, fy = gx - x0, gy - y0
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = lattice[y0 % n][x0 % n]
        b = lattice[y0 % n][(x0 + 1) % n]
        c = lattice[(y0 + 1) % n][x0 % n]
        d = lattice[(y0 + 1) % n][(x0 + 1) % n]
        v += weight * (a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy)
    return v


def stamp(img, x, y, rows, palette, wrap=False):
    """Draw a small pattern. rows: list of strings, '.' = skip, other chars index `palette`."""
    w, h = img.size
    px = img.load()
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == "." or ch == " ":
                continue
            tx, ty = x + dx, y + dy
            if wrap:
                tx, ty = tx % w, ty % h
            elif not (0 <= tx < w and 0 <= ty < h):
                continue
            px[tx, ty] = palette[ch]


def outline(img, colour_for):
    """Add a 1px outline around opaque pixels. colour_for(neighbour_rgba) picks the outline colour."""
    src = img.load()
    out = img.copy()
    px = out.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            neigh = [
                src[nx, ny]
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3]
            ]
            if neigh:
                px[x, y] = colour_for(neigh[0])
    return out


def ramp_outline(ramp):
    """Outline colour = the darkest step of the ramp the sprite is drawn in (Stardew-style coloured lines)."""
    return lambda _rgba: C(f"{ramp}-0")


def upscale(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def save(img, rel):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
