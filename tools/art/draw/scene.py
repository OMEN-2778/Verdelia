"""Compose a mock-up farm scene from the generated sheets, to judge the art in context."""
from common import TILE, new, upscale

import character
import objects
import terrain

# g = grass, d = dirt, w = water, t = tilled (dry), T = tilled (watered)
MAP = [
    "gggggggggggggggggggggg",
    "gggggggggggggggggggggg",
    "ggggddddddddggggggggww",
    "gggddttTTttdddgggggwww",
    "gggddttTTttddgggggwwww",
    "ggggdttttttddgggggwwww",
    "ggggddddddddddggggwwww",
    "gggggggddddggggggggwww",
    "ggggggggddgggggggggggw",
    "ggggggggddgggggggggggg",
    "ggggggggddgggggggggggg",
    "gggggggggggggggggggggg",
    "gggggggggggggggggggggg",
]


def tile_of(sheet, mask):
    x, y = (mask % 4) * TILE, (mask // 4) * TILE
    return sheet.crop((x, y, x + TILE, y + TILE))


def render(cells):
    rows, cols = len(cells), len(cells[0])
    w, h = (cols - 1) * TILE, (rows - 1) * TILE
    img = new(w, h)
    water = [terrain.water(f) for f in range(3)]
    for j in range(rows - 1):
        for i in range(cols - 1):
            img.alpha_composite(water[(i * 7 + j * 3) % 3], (i * TILE, j * TILE))

    def blit_layer(sheet, kinds):
        tiles = [tile_of(sheet, m) for m in range(16)]
        for j in range(rows - 1):
            for i in range(cols - 1):
                corners = (cells[j][i], cells[j][i + 1], cells[j + 1][i], cells[j + 1][i + 1])
                mask = sum(bit for bit, c in zip((1, 2, 4, 8), corners) if c in kinds)
                if mask:
                    img.alpha_composite(tiles[mask], (i * TILE, j * TILE))

    blit_layer(terrain.dirt_over_water(), set("dgtT"))
    # break up repetition: re-texture fully dirt or grass display tiles with random variants
    dirts = [terrain.dirt(k) for k in range(1, 4)]
    grasses = [terrain.grass(k, flowers=f) for k, f in ((1, 0), (2, 0), (3, 0), (4, 1), (5, 0), (6, 2), (7, 0))]
    blit_layer(terrain.grass_over(), set("g"))
    for j in range(rows - 1):
        for i in range(cols - 1):
            corners = (cells[j][i], cells[j][i + 1], cells[j + 1][i], cells[j + 1][i + 1])
            h = (i * 73856093) ^ (j * 19349663)
            if all(c == "g" for c in corners) and h % 3:
                img.alpha_composite(grasses[h % 7], (i * TILE, j * TILE))
    blit_layer(terrain.tilled_over(False), set("tT"))
    blit_layer(terrain.tilled_over(True), set("T"))

    # Props, anchored by their bottom-centre at a cell; drawn back to front.
    def cell(i, j):
        return i * TILE, j * TILE + TILE // 2  # bottom-centre of logic cell (i, j)

    props = []
    for (i, j), cropstage in zip(
        [(5, 3), (6, 3), (9, 3), (10, 3), (5, 4), (6, 4), (9, 4), (10, 4), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5)],
        [3, 3, 3, 2, 2, 3, 1, 2, 1, 2, 1, 0, 1, 0],
    ):
        props.append((cell(i, j), objects.turnip(cropstage)))
    for (i, j), stage in zip([(7, 3), (8, 3), (7, 4), (8, 4)], [2, 1, 1, 0]):
        props.append((cell(i, j), objects.lumen_bloom(stage)))
    for i in range(3, 13):
        props.append((cell(i, 1), objects.fence()))
    props += [
        (cell(2, 6), objects.tree(1)),
        (cell(15, 3), objects.tree(2)),
        (cell(1, 11), objects.tree(3)),
        (cell(16, 10), objects.bush()),
        (cell(13, 8), objects.rock(0)),
        (cell(15, 7), objects.weed(0)),
        (cell(4, 9), objects.weed(1)),
        (cell(6, 11), objects.rock(1)),
        (cell(18, 6), objects.glow_flower()),
        (cell(17, 8), objects.glow_flower()),
        (cell(9, 8), character.front()),
    ]
    props.sort(key=lambda p: p[0][1])
    for (bx, by), sprite in props:
        img.alpha_composite(sprite, (bx - sprite.width // 2, by - sprite.height))
    return img


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "scene.png"
    upscale(render(MAP), 4).save(out)
