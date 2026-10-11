"""Terrain tiles: seamless base textures plus dual-grid transition sets.

Dual-grid transition sheets are 4x4 tiles. Tile index = tl*1 + tr*2 + bl*4 + br*8, where each
bit says whether that corner of the tile belongs to the overlay terrain. Tiles are placed
offset by half a cell from the logic grid, so 16 tiles cover every combination.
"""
import random

from common import C, CLEAR, TILE, new, periodic_noise, stamp

SHADOW = C("ink", 80)


def grass(seed=0, flowers=0):
    img = new(TILE, TILE, C("grass-2"))
    px = img.load()
    for y in range(TILE):
        for x in range(TILE):
            n = periodic_noise(x, y, seed * 31 + 7, cells=(8, 4), weights=(0.75, 0.25))
            if n > 0.62 or (n > 0.48 and (x * 3 + y) % 4 == 0):
                px[x, y] = C("grass-3")
            elif n < -0.62 and (x + y) % 2:
                px[x, y] = C("grass-1")
    rnd = random.Random(seed)
    pal = {"d": C("grass-1"), "l": C("grass-3"), "h": C("grass-4")}
    blades = [["d.d", ".d."], [".l.", "l.l"], ["d..", ".d."], ["..d", ".d."], ["l", "d"], ["h", "l"]]
    for _ in range(9):
        stamp(img, rnd.randrange(TILE), rnd.randrange(TILE), rnd.choice(blades), pal, wrap=True)
    flower_pal = [
        {"p": C("blossom-4"), "c": C("sun-3")},
        {"p": C("sky-4"), "c": C("sun-4")},
        {"p": C("paper"), "c": C("sun-3")},
    ]
    for _ in range(flowers):
        fp = dict(rnd.choice(flower_pal), s=C("grass-1"))
        stamp(img, rnd.randrange(TILE), rnd.randrange(TILE), [".p.", "pcp", ".p.", ".s."], fp, wrap=True)
    return img


def dirt(seed=0):
    img = new(TILE, TILE, C("soil-2"))
    px = img.load()
    for y in range(TILE):
        for x in range(TILE):
            n = periodic_noise(x, y, seed * 17 + 3)
            if n > 0.45:
                px[x, y] = C("soil-3")
            elif n < -0.55:
                px[x, y] = C("soil-1")
    rnd = random.Random(seed + 100)
    for _ in range(5):
        px[rnd.randrange(TILE), rnd.randrange(TILE)] = C("soil-1")
    pal = {"l": C("stone-3"), "m": C("stone-2"), "d": C("soil-1")}
    for pebble in (["l", "d"], ["lm", "dd"]):
        stamp(img, rnd.randrange(TILE), rnd.randrange(TILE), pebble, pal, wrap=True)
    return img


def furrows(wet=False, seed=0):
    """Seamless hoed-soil texture: horizontal furrows with lit ridges and a few clods."""
    base, ridge, furrow = ("soil-0", "soil-1", "wood-0") if wet else ("soil-1", "soil-2", "soil-0")
    img = new(TILE, TILE, C(base))
    px = img.load()
    rnd = random.Random(seed + (50 if wet else 0))
    for y in range(TILE):
        for x in range(TILE):
            row = y % 4
            if row == 1 and rnd.random() > 0.12:
                px[x, y] = C(furrow)
            elif row == 0 and rnd.random() > 0.55:
                px[x, y] = C(ridge)
    for _ in range(3):
        x, y = rnd.randrange(TILE), rnd.randrange(TILE)
        px[x, y] = C(ridge)
        px[x, (y + 1) % TILE] = C(furrow)
    return img


def water(frame=0):
    img = new(TILE, TILE, C("water-2"))
    px = img.load()
    for y in range(TILE):
        for x in range(TILE):
            n = periodic_noise(x + frame * 4, y, 91, cells=(8, 4), weights=(0.85, 0.15))
            if n > 0.45:
                px[x, y] = C("water-3")
            elif n < -0.55 and y % 2:
                px[x, y] = C("water-1")
    rnd = random.Random(40 + frame)
    for _ in range(3):
        x, y = rnd.randrange(TILE), rnd.randrange(TILE)
        for dx in range(rnd.choice((2, 3))):
            px[(x + dx) % TILE, y] = C("water-4")
    return img


def _sharpen(t, k):
    return min(1.0, max(0.0, (t - 0.5) * k + 0.5))


def _field(mask, x, y, seed, sharp, wobble):
    tl, tr, bl, br = (1.0 if mask & b else -1.0 for b in (1, 2, 4, 8))
    u = _sharpen((x + 0.5) / TILE, sharp)
    v = _sharpen((y + 0.5) / TILE, sharp)
    top = tl + (tr - tl) * u
    bot = bl + (br - bl) * u
    return top + (bot - top) * v + wobble * periodic_noise(x, y, seed)


def transition(mask, texture, seed, *, sharp=1.3, wobble=0.6, bottom=None, top=None, side=None,
               cliff=(), shadow=True):
    """Overlay tile for one corner mask; `texture` is a seamless tile sampled for filled pixels.

    bottom/top/side: optional rim colours for overlay pixels on that kind of edge.
    cliff: colours drawn as rows below a bottom edge (e.g. a dirt bank above water).
    shadow: cast a translucent 1px shadow below bottom edges.
    """
    inside = [[_field(mask, x, y, seed, sharp, wobble) > 0 for x in range(TILE)] for y in range(TILE)]

    def at(x, y):
        # outside the tile, extend the edge row/column (good enough for rim detection)
        return inside[min(max(y, 0), TILE - 1)][min(max(x, 0), TILE - 1)]

    img = new(TILE, TILE)
    px = img.load()
    tex = texture.load()
    for y in range(TILE):
        for x in range(TILE):
            if not inside[y][x]:
                continue
            colour = tex[x, y]
            if side and (not at(x - 1, y) or not at(x + 1, y)):
                colour = side
            if top and not at(x, y - 1):
                colour = top
            if bottom and not at(x, y + 1):
                colour = bottom
            px[x, y] = colour
    for x in range(TILE):
        for y in range(TILE - 1):
            if inside[y][x] and not inside[y + 1][x]:
                yy = y + 1
                for colour in cliff:
                    if yy < TILE and not inside[yy][x]:
                        px[x, yy] = colour
                        yy += 1
                if shadow and yy < TILE and not inside[yy][x]:
                    px[x, yy] = SHADOW
    return img


def transition_sheet(texture, seed, **kw):
    sheet = new(TILE * 4, TILE * 4)
    for mask in range(16):
        sheet.alpha_composite(transition(mask, texture, seed, **kw), ((mask % 4) * TILE, (mask // 4) * TILE))
    return sheet


# Grass and the dirt bank share one edge seed so a grass edge over water keeps its bank visible.
EDGE_SEED = 5


def grass_over():
    return transition_sheet(grass(0), EDGE_SEED, bottom=C("grass-1"))


def dirt_over_water():
    return transition_sheet(dirt(0), EDGE_SEED, bottom=C("soil-3"), cliff=(C("soil-1"), C("soil-0")))


def tilled_over(wet=False):
    """Hoed soil as an overlay: adjacent tilled cells merge into one patch with rounded corners."""
    if wet:
        rims = dict(top=C("ink"), bottom=C("soil-1"), side=C("wood-0"))
    else:
        rims = dict(top=C("soil-0"), bottom=C("soil-2"), side=C("soil-0"))
    return transition_sheet(furrows(wet), 13, sharp=4.0, wobble=0.12, shadow=False, **rims)


def base_sheet():
    tiles = [grass(k) for k in range(4)] + [grass(4, flowers=1), grass(5, flowers=2), dirt(0), dirt(1),
             furrows(False), furrows(True), water(0), water(1), water(2), water(3)]
    sheet = new(TILE * len(tiles), TILE)
    for i, t in enumerate(tiles):
        sheet.alpha_composite(t, (i * TILE, 0))
    return sheet
