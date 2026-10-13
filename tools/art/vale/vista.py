#!/usr/bin/env python3
"""Paint the mountain vista: the far view beyond a map's north edge, in layers for parallax.

From the meadow's edge you look out over forested hills to a wide turquoise lake, a range of blue
mountains with snow on their peaks under a haze of low cloud, and big summer clouds in a deep blue
sky (after a photo of a mountain lake, mirrored: the hills come in from the right). Every layer
except the clouds tiles left to right, so it works for maps of any width.

Writes art/vista/mountains/:
  sky.png                      vertical gradient, stretched across the screen
  peaks_far.png, peaks.png     the far and near ranges (snow, lit and shaded faces, haze)
  haze.png                     the bank of low cloud along their feet
  lake.png                     the lake from the horizon down, lighter toward the shore
  hills_far.png, hills.png     rolling hills with belts of pine forest
  brink.png                    the meadow's lip at the map edge (blends into the ground's grass)
  cloud_<k>.png                cumulus clouds that drift across the sky

Re-run after changes:  python3 tools/art/vale/vista.py
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "art/vista/mountains"
BAYER = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4) / 16.0 - 0.5


def hexc(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def ramp(*cols):
    return np.array([hexc(c) for c in cols], dtype=np.uint8)


SKY = ramp("#2a62c4", "#3573d0", "#4686da", "#5b9ae2", "#78b0e8", "#9cc8ef", "#c4e0f5")
CLOUD = ramp("#7f95b8", "#9fb2cf", "#c2d1e5", "#dfe8f3", "#f4f8fc", "#ffffff")
PEAK = ramp("#2f4a78", "#3d5d8f", "#4f72a3", "#6589b6", "#7fa1c8", "#9cb9d9")
PEAK_FAR = ramp("#6b8bbb", "#7a9ac6", "#8aa8cf", "#9ab6d8", "#abc4e0")
SNOW = ramp("#9fb3d3", "#c3d3ea", "#e2ebf6", "#fbfdff")
SNOW_FAR = ramp("#a9bddb", "#c3d3ea", "#dbe6f3", "#eef4fb")
LAKE = ramp("#1a5aa6", "#1f6db5", "#2582c2", "#2b98cb", "#33aed2", "#4fc4d8", "#8fdcea")
HILL = ramp("#2c6a35", "#3b7f3d", "#4f9746", "#66ad50", "#84c35c", "#a3d56e")
HILL_FAR = ramp("#3f7a6a", "#4d8b72", "#5e9b7b", "#71ab85", "#86ba90")
PINE = ramp("#0f2e22", "#163d29", "#1f4f31", "#2b623a", "#3a7746")
GRASS = ramp("#3f8f3f", "#55a748", "#6fbf55", "#8fd168")  # the ground shader's grass tones


def pick(r, v, dither=0.6, xs=None, ys=None):
    """v (array, 0..1) -> colours from ramp r, ordered-dithered between steps."""
    n = len(r)
    if xs is not None:
        v = v + BAYER[ys % 4, xs % 4] * dither / n
    i = np.clip(np.floor(v * n), 0, n - 1).astype(int)
    return r[i]


def periodic(width, x, terms, seed):
    """A smooth curve over x that wraps around every `width` px: sum of sines of whole periods."""
    rnd = random.Random(seed)
    out = np.zeros_like(x, dtype=float)
    for k, amp in terms:
        out += amp * np.sin(2 * math.pi * k * x / width + rnd.uniform(0, 2 * math.pi))
    return out


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(OUT / name)


def rgba(h, w):
    return np.zeros((h, w, 4), dtype=np.uint8)


# ---------------------------------------------------------------- layers

def sky(h=300):
    img = rgba(h, 8)
    ys, xs = np.mgrid[0:h, 0:8]
    v = (ys / (h - 1)) ** 1.6  # deep at the top, pale toward the horizon
    img[..., :3] = pick(SKY, v, 0.6, xs, ys)
    img[..., 3] = 255
    return img


def range_layer(w, h, pal, snow, seed, n, tall, snow_from, haze_col, haze_amt):
    """A mountain range of `n` peaks across the tile (wrapping round), taller ones behind and
    lower ones in front. Each peak is a rough cone: its main ridge runs down from the summit,
    the face left of it lit and right of it in shade, spurs and gullies fanning out from the top;
    snow caps the peaks taller than `snow_from` (of h), reaching further down the spurs; haze
    thickens toward the foot by `haze_amt`."""
    rnd = random.Random(seed)
    img = rgba(h, w)
    yy, xx = np.mgrid[0:h, 0:w]
    peaks = []
    for i in range(n):
        x = (i + rnd.uniform(-0.3, 0.3)) * w / n
        hgt = rnd.uniform(0.35, 1.0) * tall * h
        peaks.append((hgt, x))
    for i in range(n // 2):  # foothills in front
        peaks.append((rnd.uniform(0.18, 0.4) * tall * h, rnd.uniform(0, w)))
    peaks.sort(reverse=True)  # tallest first, so lower ones are drawn in front
    for hgt, px in peaks:
        py = h - 1 - hgt
        sl, sr = rnd.uniform(0.55, 0.9), rnd.uniform(0.5, 0.85)  # flank steepness
        lean = rnd.uniform(-0.25, 0.25)  # the main ridge leans a little
        ph = rnd.uniform(0, 6.28)
        for shift in (-w, 0, w):
            cx = px + shift
            dx = xx - cx
            rough = 1.6 * np.sin(xx * 0.9 + ph) + 1.1 * np.sin(xx * 0.37 + ph * 2) + 0.8 * np.sin(xx * 2.3 + ph)
            top = py + np.where(dx < 0, -dx * sl, dx * sr) + np.abs(np.clip(rough, -2, 3)) * np.clip(np.abs(dx) / 10, 0, 1)
            inside = yy >= top
            if not inside.any():
                continue
            d = yy - py  # below the summit
            ridge = cx + d * lean + 1.5 * np.sin(d * 0.45 + ph)
            lit = xx < ridge
            # spurs fanning out from the summit: alternate light and dark wedges
            ang = (xx - ridge) / (d + 6.0)
            fan = np.sin(ang * 9.0 + ph + 0.6 * np.sin(d * 0.3)) + 0.4 * np.sin(ang * 23.0 + ph * 3)
            v = np.where(lit, 0.68, 0.3) + fan * 0.1 - (d / h) * 0.25
            v = np.where(lit & (xx > ridge - 2), v + 0.15, v)  # a bright edge along the ridge
            col = pick(pal, np.clip(v, 0, 0.999), 0.7, xx, yy)
            if hgt > snow_from * h:
                reach = (hgt - snow_from * h * 0.75) * (0.45 + 0.35 * np.clip(fan, -1, 1))
                is_snow = inside & (d < reach)
                sv = np.where(lit, 0.85, 0.35) + fan * 0.08
                col = np.where(is_snow[..., None], pick(snow, np.clip(sv, 0, 0.999), 0.8, xx, yy), col)
            img[inside, :3] = col[inside]
            img[inside, 3] = 255
    # haze toward the foot
    hz = (np.clip((yy - h * 0.35) / (h * 0.65), 0, 1) ** 1.4 * haze_amt)[..., None]
    img[..., :3] = (img[..., :3] * (1 - hz) + np.array(haze_col) * hz).astype(np.uint8)
    return img


def haze_bank(w, h, seed):
    """Low cloud lying along the feet of the mountains: a row of soft round puffs on a flat base,
    pale and a little see-through, thinning out downward into the lake's horizon."""
    rnd = random.Random(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    field = np.zeros((h, w))
    light = np.zeros((h, w))
    base = h - 4
    x = 0.0
    while x < w:
        r = rnd.uniform(3.5, 9.0) * (1.4 if rnd.random() < 0.2 else 1.0)
        cy = base - r * rnd.uniform(0.2, 0.6)
        for shift in (-w, 0, w):
            d = np.sqrt((xx - x - shift) ** 2 + ((yy - cy) * 1.3) ** 2) / r
            m = d < 1
            lit = np.clip(1 - d, 0, 1) * 0.5 + np.clip(-(yy - cy) / r, 0, 1) * 0.5
            light = np.where(m, np.maximum(light, lit), light)
            field = np.where(m, 1, field)
        x += r * rnd.uniform(0.7, 1.2)
    img = rgba(h, w)
    v = 0.45 + light * 0.5
    img[..., :3] = pick(CLOUD, np.clip(v, 0, 0.999), 0.9, xx, yy)
    fade = np.clip((base + 3 - yy) / (h * 0.45), 0, 1)
    a = field * (90 + 130 * fade)
    a = np.where((field > 0) & (light < 0.12) & (BAYER[yy % 4, xx % 4] > 0), a * 0.5, a)
    img[..., 3] = a.astype(np.uint8)
    return img


def lake(w, h, seed):
    """The lake from the horizon down: hazy pale at the horizon, deep blue, then turquoise
    toward the near shore, with long faint wave lines."""
    img = rgba(h, w)
    yy, xx = np.mgrid[0:h, 0:w]
    t = yy / (h - 1)
    v = np.where(t < 0.06, 0.9 - t * 4, 0.28 + t * 0.62)
    rnd = np.random.default_rng(seed)
    lines = np.zeros((h, w))
    for _ in range(int(w * h / 900)):
        y = int(rnd.integers(3, h))
        x = int(rnd.integers(0, w))
        ln = int(rnd.integers(6, 6 + y // 2))
        lines[y, (x + np.arange(ln)) % w] = 1
    v = v + lines * 0.12
    img[..., :3] = pick(LAKE, np.clip(v, 0, 0.999), 0.7, xx, yy)
    img[0, :, :3] = hexc("#cfe9f5")  # the horizon line
    img[..., 3] = 255
    return img


def hills(w, h, pal, seed, forest, tops, base_tone):
    """Rolling hills with belts of pine forest: tops wrap around, slopes lit on the left, a pale
    sandy shore where they meet the lake (pal == HILL), pines as little lit triangles."""
    xs = np.arange(w)
    ridge = periodic(w, xs, tops, seed)
    ridge = (ridge - ridge.min()) / (ridge.max() - ridge.min())
    top = np.round(6 + (1 - ridge) ** 1.3 * (h * 0.78)).astype(int)
    slope = np.gradient(ridge)
    img = rgba(h, w)
    yy, xx = np.mgrid[0:h, 0:w]
    inside = yy >= top[None, :]
    d = (yy - top[None, :]) / h
    v = base_tone + np.clip(slope[None, :] * 30, -0.3, 0.3) - d * 0.25 + 0.05 * np.sin(xx / 9.0 + yy / 4.0)
    col = pick(pal, np.clip(v, 0, 0.999), 0.8, xx, yy)
    img[..., :3] = col
    img[..., 3] = np.where(inside, 255, 0)
    rnd = random.Random(seed + 9)
    # forest belts: pines down the slopes in bands that wander
    belt = periodic(w, xs, [(w // 60, 1.0), (w // 25, 0.5)], seed + 3)
    belt = (belt - belt.min()) / (belt.max() - belt.min())
    for x in range(0, w, 2):
        if belt[x] < 1 - forest:
            continue
        y0 = top[x] + rnd.randint(1, 6)
        depth = int(4 + belt[x] * 26 * forest)
        y = y0
        while y < min(h - 2, y0 + depth):
            if rnd.random() < 0.55:
                ph = rnd.randint(4, 7)
                for j in range(ph):
                    half = j // 2
                    for i in range(-half, half + 1):
                        px, py = (x + i) % w, y - ph + j
                        if 0 <= py < h and img[py, px, 3]:
                            c = 3 if i < 0 else 2 if i == 0 else 1
                            if j == 0:
                                c = 4
                            img[py, px, :3] = PINE[c]
            y += rnd.randint(2, 4)
    # a lit rim on the hill tops
    rim = (yy == top[None, :])
    img[rim, :3] = np.minimum(255, img[rim, :3].astype(int) + 22)
    return img


FADE = 6  # the brink's bottom rows that overlap the map


def brink(w=256, h=26, seed=7):
    """The meadow's edge: an uneven lip of blades and wild flowers along the top, a little shade
    just under it, and grass coloured like the ground's below, dissolving (dithered) over the
    bottom FADE rows, which overlap the map, so the lip grows out of the map's own grass."""
    rnd = random.Random(seed)
    img = rgba(h, w)
    xs = np.arange(w)
    lip = periodic(w, xs, [(w // 64, 1.0), (w // 23, 0.6), (w // 9, 0.35)], seed)
    lip = np.round(12 + (lip - lip.min()) / (lip.max() - lip.min()) * 6).astype(int)
    yy, xx = np.mgrid[0:h, 0:w]
    v = 0.2 + 0.14 * np.sin(xx / 13.0) * np.cos(yy / 5.0)
    col = pick(GRASS, np.clip(v, 0, 0.999), 0.9, xx, yy)
    inside = yy >= lip[None, :]
    img[..., :3] = col
    img[..., 3] = np.where(inside, 255, 0)
    # the shaded underside of the lip just above it (the ground falling away)
    for x in range(w):
        for k in range(1, 3):
            y = lip[x] + k
            img[y, x, :3] = (img[y, x, :3] * (0.72 + 0.1 * k)).astype(np.uint8)
    # blades and flowers along the lip
    flowers = [hexc("#ffd84a"), hexc("#ffe98a"), hexc("#a77be0"), hexc("#c8a4f0"), hexc("#ffffff")]
    for x in range(w):
        if rnd.random() < 0.7:
            bh = rnd.randint(2, 6)
            for j in range(bh):
                y = lip[x] - j
                if y >= 0:
                    img[y, x, :3] = GRASS[3] if j == bh - 1 else GRASS[1 + (j & 1)]
                    img[y, x, 3] = 255
        if rnd.random() < 0.06:
            fy = lip[x] - rnd.randint(4, 7)
            c = flowers[rnd.randrange(len(flowers))]
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                px, py = (x + dx) % w, fy + dy
                if 0 <= py < h:
                    img[py, px, :3] = c if (dx, dy) != (0, 0) else hexc("#fff3a0")
                    img[py, px, 3] = 255
            for y in range(fy + 2, lip[x]):
                img[y, x, :3] = GRASS[0]
                img[y, x, 3] = 255
    keep = (h - 1 - yy) / FADE + BAYER[yy % 4, xx % 4] * 0.9 > 0.05
    img[..., 3] = np.where((yy >= h - FADE) & ~keep, 0, img[..., 3])
    return img


def cloud(seed, w, h):
    """A cumulus cloud: overlapping round puffs piled on a flat-ish base, lit from above-left,
    shaded underneath, a soft dithered rim."""
    rnd = random.Random(seed)
    W, H = w + 8, h + 8
    field = np.zeros((H, W))
    light = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    base = H - 5
    n = int(w / 7)
    for i in range(n):
        u = (i + 0.5) / n
        cx = 4 + u * w + rnd.uniform(-3, 3)
        hump = math.sin(u * math.pi) ** 0.8
        r = (h * 0.28) * (0.55 + hump * 0.7) * rnd.uniform(0.8, 1.15)
        cy = base - r * 0.6 - hump * h * 0.38 * rnd.uniform(0.7, 1.1)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        m = d < 1
        nz = np.sqrt(np.clip(1 - d ** 2, 0, 1))
        lit = np.clip(((xx - cx) * -0.45 + (yy - cy) * -0.85) / r * 0.6 + nz * 0.5, 0, 1)
        upd = m & ((field == 0) | (cy - r < 0) | (lit > light))
        light = np.where(upd & m, np.maximum(light, lit), light)
        field = np.where(m, 1, field)
    field[yy > base] = 0
    v = 0.25 + light * 0.75 - np.clip((yy - (base - h * 0.25)) / (h * 0.25), 0, 1) * 0.35
    img = rgba(H, W)
    img[..., :3] = pick(CLOUD, np.clip(v, 0, 0.999), 0.9, xx, yy)
    alpha = field * 255
    # soften: the outermost ring of pixels half see-through, dithered
    edge = (field > 0) & ((np.roll(field, 1, 0) == 0) | (np.roll(field, -1, 0) == 0) | (np.roll(field, 1, 1) == 0) | (np.roll(field, -1, 1) == 0))
    alpha = np.where(edge & (BAYER[yy % 4, xx % 4] > 0), 150, alpha)
    img[..., 3] = alpha.astype(np.uint8)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    save(sky(), "sky.png")
    save(range_layer(1024, 84, PEAK_FAR, SNOW_FAR, 11, 11, 1.0, 0.45, hexc("#b8cfe6"), 0.75), "peaks_far.png")
    save(range_layer(1024, 66, PEAK, SNOW, 23, 9, 0.95, 0.55, hexc("#a9c4e0"), 0.7), "peaks.png")
    save(haze_bank(1024, 24, 31), "haze.png")
    save(lake(256, 100, 41), "lake.png")
    save(hills(1024, 80, HILL_FAR, 51, 0.55, [(3, 1.0), (7, 0.5), (12, 0.25)], 0.55), "hills_far.png")
    save(hills(1024, 104, HILL, 61, 0.75, [(2, 1.0), (5, 0.6), (11, 0.25)], 0.6), "hills.png")
    save(brink(), "brink.png")
    for k, (w, h) in enumerate(((140, 54), (96, 40), (120, 46), (70, 28), (160, 60), (84, 34))):
        save(cloud(100 + k, w, h), f"cloud_{k}.png")
    print("vista: mountains ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
