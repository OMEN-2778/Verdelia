#!/usr/bin/env python3
"""Terrain mask for the demo world (one texel per 8px cell; R=dirt, G=tilled, B=watered).

In real levels this is painted in the Godot editor with terrain_brushes.tres; the demo builds
it from a few splines so it can be regenerated.
"""
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
CELL = 8
MAP = (960, 480)
PATHS = [  # (points, half width px)
    ([(150, 92), (162, 120), (196, 150), (250, 176), (300, 196)], 7.5),
    ([(470, 300), (478, 340), (460, 380), (476, 430), (468, 490)], 7.5),
    ([(640, 250), (700, 262), (780, 250), (860, 270), (970, 262)], 6.5),
]
PLOT = (470, 248, 150, 46)  # centre x/y, half width/height
WATERED_X = 420  # left part of the plot is watered


def catmull(points, step=2.0):
    pts = [points[0]] + points + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(2, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    return out


def main():
    w, h = MAP[0] // CELL, MAP[1] // CELL
    im = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    px = im.load()
    for pts, half in PATHS:
        samples = catmull(pts)
        for k, (sx, sy) in enumerate(samples):
            hw = half + 1.8 * math.sin(k * 0.21)  # width wanders
            for cy in range(h):
                for cx in range(w):
                    x, y = (cx + 0.5) * CELL, (cy + 0.5) * CELL
                    if abs(x - sx) < 16 and abs(y - sy) < 16 and math.hypot(x - sx, y - sy) <= hw:
                        px[cx, cy] = (255, px[cx, cy][1], px[cx, cy][2], 255)
    pcx, pcy, pa, pb = PLOT
    for cy in range(h):
        for cx in range(w):
            x, y = (cx + 0.5) * CELL, (cy + 0.5) * CELL
            v = (abs((x - pcx) / pa) ** 3 + abs((y - pcy) / pb) ** 3) ** (1 / 3) + 0.08 * math.sin(x * 0.07 + y * 0.05)
            if v < 1.0:
                wet = x + 22 * math.sin(y * 0.09) + 14 * math.sin(y * 0.23 + 1) < WATERED_X
                px[cx, cy] = (255, 255, 255 if wet else 0, 255)
            elif v < 1.18:
                px[cx, cy] = (255, 0, 0, 255)  # a dirt margin around the plot
    im.save(ROOT / "art/demo_world/terrain_mask.png")
    print("mask", im.size)


if __name__ == "__main__":
    main()
