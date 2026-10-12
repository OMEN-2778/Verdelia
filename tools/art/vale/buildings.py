"""Town buildings, drawn procedurally in the vale style: cabins, a stone cottage under thatch,
half-timbered townhouses, shops with awnings and display windows, an inn with a porch, and
market stalls.

Everything is seen from the front at the usual top-down 3/4 angle and lit from the upper left
like the flora. A building is put together from parts (walls of planks, boards, plaster with a
timber frame or stone; shingle, thatch or gable roofs; doors, windows, shop windows, awnings,
signs, lanterns, a porch, crates and barrels), so each design is a short function and they all
look like they belong to one town.

Each building also gets a night image holding only what glows (window glass, lanterns). Its
colours all have blue = 3/255: the mark the screen grade (shaders/grade.gdshader) looks for to keep
lamplight bright at night, while characters walking past still hide it correctly.
"""
import math
import random

from PIL import Image

from flora import hexc

# ---------------------------------------------------------------- palettes (dark -> light)
WOOD = ["#2a1a12", "#4a2f1f", "#6b4529", "#8a5d36", "#a87545", "#c38f5a", "#dcae7a"]
DARKWOOD = ["#1d120d", "#33211a", "#4b3022", "#62402c", "#7b5236", "#946743", "#ad7f55"]
TRIM = ["#3a271a", "#7d5a3a", "#a98057", "#c9a272", "#e3c597"]
STONE = ["#2b2726", "#47413e", "#655d57", "#837a71", "#a1978b", "#bdb4a6", "#d8d0c2"]
FIELDSTONE = ["#2a2622", "#4a433b", "#6a6156", "#887e70", "#a59a8a", "#c0b6a5", "#d9d1c1"]
PLASTER = ["#3b2f2a", "#8f7f6a", "#c4b394", "#ddcfb2", "#ece2ca", "#f6f0e1", "#fdfaf2"]
GLASS = ["#253447", "#36597a", "#5b8fb0", "#93c6dd", "#d9f1f8"]
LIT = ["#7a4a03", "#d98903", "#f5b003", "#ffd403", "#fff003"]  # blue 3 marks lamplight
IRON = ["#1c1a1f", "#33313a", "#55525e"]
BRASS = "#e8c15a"
ROOFS = {
    "rust": ["#2e1a1c", "#4d2a28", "#6e3a31", "#8f4d3b", "#ad6449", "#c8815f", "#e0a37f"],
    "slate": ["#1c2130", "#2f374b", "#434e66", "#596782", "#73829d", "#93a2ba", "#b8c5d7"],
    "moss": ["#1c2921", "#2c3f32", "#3e5643", "#546f55", "#6d8a65", "#8ca57c", "#b0c39a"],
    "bark": ["#24170f", "#3b261a", "#553723", "#6f4a2e", "#8a5f3b", "#a6794f", "#c49a6c"],
    "teal": ["#14262a", "#1f3c40", "#2b5457", "#3b6d6c", "#518884", "#71a39b", "#9cc2b6"],
    "plum": ["#24182a", "#3b2740", "#533758", "#6c4a6e", "#866185", "#a27d9e", "#c1a2bb"],
    "thatch": ["#3a2a14", "#5e4520", "#86652c", "#a8843a", "#c7a24e", "#dcbf6e", "#efdc9c"],
}
PAINT = {
    "sage": ["#1f2a24", "#33473b", "#4a6453", "#62806b", "#7e9c85", "#a2baa5", "#c6d6c5"],
    "blue": ["#1b2433", "#2c3c55", "#405677", "#567196", "#738db0", "#97adc8", "#bfcfe0"],
    "cream": PLASTER,
    "rose": ["#2e1b1f", "#563238", "#7c4a4f", "#9c6366", "#b98281", "#d1a4a0", "#e8c9c3"],
}
SHUTTERS = {
    "green": ["#1c3330", "#2a4e46", "#3a6a5c", "#4f8673", "#6fa38c"],
    "blue": ["#1d2a3d", "#2d4361", "#3f5d82", "#5779a0", "#7b98bb"],
    "red": ["#33191a", "#572a29", "#7a3b36", "#9a5047", "#b86c5c"],
}
CANVAS = {  # awning / canopy stripes: (colour, white)
    "red": (["#5a1f22", "#8c2f30", "#b9443e", "#d65d50"], ["#9a8c80", "#cfc3b4", "#ece4d6", "#fbf7ee"]),
    "blue": (["#1d2c4c", "#2d4777", "#3f63a0", "#5a82c0"], ["#9a8c80", "#cfc3b4", "#ece4d6", "#fbf7ee"]),
    "green": (["#1f3a26", "#2f5a36", "#447a48", "#5f9a5c"], ["#9a8c74", "#cfc29e", "#e9dfbf", "#f7f1dc"]),
    "yellow": (["#6a4a12", "#a57418", "#d39d26", "#efc24a"], ["#9a8c80", "#cfc3b4", "#ece4d6", "#fbf7ee"]),
    "purple": (["#2e1f45", "#4a3170", "#664797", "#8463b8"], ["#9a8c80", "#cfc3b4", "#ece4d6", "#fbf7ee"]),
}
MOSS = ["#2f4a2a", "#46683a", "#62874a", "#85a85f"]
LEAF = ["#2d5a2c", "#3f7a37", "#5fa047"]
FLOWER = [("#ffffff", "#ffe066"), ("#ff9ec4", "#ffe066"), ("#ffe066", "#ffffff"), ("#c9b3ff", "#ffe066")]
GOODS = {  # small round produce: dark, mid, light
    "apple": ["#5e1a1a", "#b8332b", "#e66a4e"],
    "orange": ["#7a3d0e", "#de7f1f", "#f6b14c"],
    "cabbage": ["#24481f", "#4f8a36", "#90c25e"],
    "pumpkin": ["#7a3a10", "#d0701c", "#efa34a"],
    "grape": ["#2c1840", "#5c3a86", "#8f6cc0"],
    "bread": ["#6b3c17", "#b9773a", "#e2b06c"],
    "fish": ["#3a4a5c", "#7f97ad", "#c9d8e4"],
    "potion_r": ["#5a1424", "#b02e44", "#f07a8a"],
    "potion_b": ["#14305a", "#2e62b0", "#7ab0f0"],
    "potion_g": ["#1d4a24", "#3c9a48", "#8ce08a"],
}


def C(c):
    return hexc(c) if isinstance(c, str) else c


def tone(ramp, v):
    """v in [0,1] -> an index into ramp[2:-1] (keeps the darkest tones for edges, the lightest
    for highlights)."""
    return max(2, min(len(ramp) - 2, round(2 + v * (len(ramp) - 4))))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.im.load()
        self.night = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.npx = self.night.load()

    def inb(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, c):
        if self.inb(x, y):
            self.px[x, y] = C(c)

    def get(self, x, y):
        return self.px[x, y] if self.inb(x, y) else (0, 0, 0, 0)

    def clear(self, x, y):
        if self.inb(x, y):
            self.px[x, y] = (0, 0, 0, 0)
            self.npx[x, y] = (0, 0, 0, 0)

    def lit(self, x, y, c):
        if self.inb(x, y):
            self.npx[x, y] = C(c)

    def unlit(self, x, y):
        if self.inb(x, y):
            self.npx[x, y] = (0, 0, 0, 0)

    def darken(self, x, y, k):
        r, g, b, a = self.get(x, y)
        if a:  # cool, slightly blue shadow rather than plain black
            self.px[x, y] = (round(r * (1 - k) + 22 * k), round(g * (1 - k) + 18 * k), round(b * (1 - k) + 34 * k), a)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, c)

    def outline(self, colour=WOOD[0]):
        src = self.im.copy().load()
        dark = C(colour)
        for y in range(self.h):
            for x in range(self.w):
                if src[x, y][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < self.w and 0 <= yy < self.h and src[xx, yy][3]:
                        self.px[x, y] = dark
                        break


# ================================================================ walls

def planks(cv, rnd, x0, x1, y0, y1, ramp=WOOD):
    """Horizontal boards: one flat tone per board, a lit top edge, a dark seam, butt joints."""
    plank = 5
    for row in range((y1 - y0 + plank - 1) // plank):
        ry0 = y0 + row * plank
        x = x0 - rnd.randint(0, 20)
        while x < x1:
            ln = rnd.randint(18, 34)
            u = (max(x, x0) + ln / 2 - x0) / max(1, x1 - x0)
            idx = tone(ramp, 0.62 - 0.16 * u + rnd.uniform(-0.07, 0.07))
            for xx in range(max(x, x0), min(x + ln, x1)):
                for k in range(plank):
                    y = ry0 + k
                    if y >= y1:
                        break
                    c = ramp[1] if k == plank - 1 else ramp[idx + 1] if k == 0 else ramp[idx]
                    if xx == x + ln - 1:
                        c = ramp[1]
                    elif xx == x + ln - 2 and k < plank - 1:
                        c = ramp[idx + 1]
                    cv.set(xx, y, c)
            for _ in range(ln // 10):  # grain and the odd knot
                gx, gy = rnd.randint(x + 2, x + ln - 4), ry0 + rnd.randint(1, plank - 2)
                if gy >= y1:
                    continue
                if rnd.random() < 0.15:
                    if x0 + 2 <= gx < x1 - 3:
                        cv.set(gx, gy, ramp[1])
                        cv.set(gx + 1, gy, ramp[2])
                else:
                    for i in range(rnd.randint(2, 5)):
                        if x0 + 2 <= gx + i < min(x + ln - 2, x1 - 2):
                            cv.set(gx + i, gy, ramp[max(1, idx - 1)])
            x += ln


def boards(cv, rnd, x0, x1, y0, y1, ramp):
    """Vertical board-and-batten (painted or plain)."""
    x = x0
    while x < x1:
        bw = 5
        u = (x - x0) / max(1, x1 - x0)
        idx = tone(ramp, 0.6 - 0.18 * u + rnd.uniform(-0.05, 0.05))
        for xx in range(x, min(x + bw, x1)):
            k = xx - x
            for y in range(y0, y1):
                c = ramp[idx + 1] if k == 0 else ramp[1] if k == bw - 1 else ramp[idx]
                cv.set(xx, y, c)
        for _ in range(2):  # a few marks in the paint
            gy = rnd.randint(y0 + 2, y1 - 3)
            gx = x + rnd.randint(1, 2)
            cv.set(gx, gy, ramp[idx - 1])
            cv.set(gx, gy + 1, ramp[idx - 1])
        x += bw
    for y in range(y0, y1):  # bottom rail
        if y >= y1 - 2:
            for xx in range(x0, x1):
                cv.set(xx, y, ramp[2] if y == y1 - 1 else ramp[idx])


def plaster(cv, rnd, x0, x1, y0, y1, ramp=PLASTER):
    for y in range(y0, y1):
        for x in range(x0, x1):
            u = (x - x0) / max(1, x1 - x0)
            idx = tone(ramp, 0.75 - 0.2 * u)
            cv.set(x, y, ramp[idx])
    for _ in range((x1 - x0) * (y1 - y0) // 30):  # speckle and wear
        x, y = rnd.randint(x0, x1 - 1), rnd.randint(y0, y1 - 1)
        cv.set(x, y, ramp[3] if rnd.random() < 0.7 else ramp[2])


def stones(cv, rnd, x0, x1, y0, y1, ramp=FIELDSTONE, row_h=(4, 6)):
    """Rounded fieldstones in rough courses, with mortar between."""
    y = y1
    while y > y0:
        h = rnd.randint(*row_h)
        top = max(y0, y - h)
        x = x0 - rnd.randint(0, 5)
        while x < x1:
            w = rnd.randint(5, 10)
            u = (x + w / 2 - x0) / max(1, x1 - x0)
            idx = tone(ramp, rnd.uniform(0.35, 0.8) - 0.18 * u)
            for xx in range(max(x, x0), min(x + w, x1)):
                for yy in range(top, y):
                    lx, ly = xx - x, yy - top
                    corner = (lx in (0, w - 1)) and (ly in (0, y - top - 1))
                    if lx == w - 1 or yy == y - 1 or corner:
                        c = ramp[1]
                    elif ly == 0 or lx == 0:
                        c = ramp[min(len(ramp) - 1, idx + 1)]
                    elif lx == w - 2 or yy == y - 2:
                        c = ramp[idx - 1]
                    else:
                        c = ramp[idx]
                    cv.set(xx, yy, c)
            x += w
        y = top


def footing(cv, rnd, x0, x1, y0, y1):
    x = x0
    while x < x1:
        bw = rnd.randint(5, 9)
        idx = tone(STONE, rnd.uniform(0.3, 0.7) - 0.15 * (x - x0) / max(1, x1 - x0))
        for xx in range(x, min(x + bw, x1)):
            for y in range(y0, y1):
                if xx == x + bw - 1 or y == y1 - 1:
                    c = STONE[1]
                elif y == y0 + 1 or xx == x:
                    c = STONE[idx + 1]
                else:
                    c = STONE[idx]
                cv.set(xx, y, c)
        x += bw
    for xx in range(x0, x1):  # the wall above throws a thin shadow on the stones
        cv.darken(xx, y0, 0.35)


def timber(cv, x0, x1, y0, y1, studs=(), braces=(), ramp=DARKWOOD):
    """Half-timbering over plaster: beams round the panel, studs at `studs` (x), and diagonal
    braces in the panels listed in `braces` as (xa, xb, rising)."""
    def beam_v(x):
        for y in range(y0, y1):
            cv.set(x, y, ramp[4])
            cv.set(x + 1, y, ramp[3])
            cv.set(x + 2, y, ramp[1])

    def beam_h(y):
        for x in range(x0, x1):
            cv.set(x, y, ramp[4])
            cv.set(x, y + 1, ramp[3])
            cv.set(x, y + 2, ramp[1])

    for xa, xb, rising in braces:
        for x in range(xa, xb):
            t = (x - xa) / max(1, xb - xa - 1)
            yy = round(y1 - 3 - t * (y1 - y0 - 6)) if rising else round(y0 + 3 + t * (y1 - y0 - 6))
            cv.set(x, yy - 1, ramp[4])
            cv.set(x, yy, ramp[3])
            cv.set(x, yy + 1, ramp[1])
    for x in (x0, x1 - 3, *studs):
        beam_v(x)
    beam_h(y0)
    beam_h(y1 - 3)


def eave_shadow(cv, x0, x1, y0, rows=7, strength=1.0):
    ks = [0.62, 0.55, 0.45, 0.32, 0.2, 0.1, 0.04]
    for i in range(min(rows, len(ks))):
        for x in range(x0, x1):
            cv.darken(x, y0 + i, ks[i] * strength)


# ================================================================ openings

def door(cv, rnd, cx, bottom, w=14, h=22, style="plank", wood=WOOD, step=True, step_at=None):
    """A door in its frame standing on `bottom`; style: plank, glazed, double, arched. The stone
    step in front takes four rows from `step_at` (default: just below the door)."""
    dx0, dx1 = cx - w // 2, cx - w // 2 + w
    dy0 = bottom - h
    arch = style == "arched"

    def inside_arch(x, y, grow=0):
        if not arch or y >= dy0 + w // 2:
            return True
        r = w / 2 + grow
        return (x + 0.5 - cx) ** 2 + (y + 0.5 - (dy0 + w / 2)) ** 2 <= r * r

    for y in range(dy0 - 2, bottom):  # frame
        for x in range(dx0 - 2, dx1 + 2):
            if not inside_arch(x, y, 2):
                continue
            if dx0 <= x < dx1 and y >= dy0 and inside_arch(x, y):
                continue
            c = TRIM[3] if (x < dx0 - 1 or y < dy0 - 1) else TRIM[2]
            if x >= dx1 + 1:
                c = TRIM[1]
            cv.set(x, y, c)
    for y in range(dy0, bottom):  # leaf
        for x in range(dx0, dx1):
            if not inside_arch(x, y):
                continue
            k = (x - dx0) % 4
            board = wood[3] if (x - dx0) < w * 0.6 else wood[2]
            c = wood[1] if k == 3 else (wood[4] if k == 0 and x < dx1 - 4 else board)
            if style != "glazed" and y in (dy0 + 4 + (3 if arch else 0), bottom - 5):
                c = wood[4] if x < dx1 - 1 else wood[3]
            if style != "glazed" and y in (dy0 + 5 + (3 if arch else 0), bottom - 4):
                c = wood[1]
            if style == "double" and x == cx:
                c = wood[0]
            cv.set(x, y, c)
    if style == "glazed":  # four panes in the top half
        gx0, gx1, gy0, gy1 = dx0 + 2, dx1 - 2, dy0 + 2, dy0 + h // 2
        for y in range(gy0, gy1):
            for x in range(gx0, gx1):
                lx, ly = x - gx0, y - gy0
                if lx == (gx1 - gx0) // 2 or ly == (gy1 - gy0) // 2:
                    cv.set(x, y, wood[2])
                    continue
                cv.set(x, y, GLASS[4] if (lx + ly) % 7 == 2 else GLASS[2] if ly < 3 else GLASS[1])
                cv.lit(x, y, LIT[3] if ly < 3 else LIT[2])
        for x in range(dx0, dx1):
            cv.set(x, bottom - 6, wood[4])
            cv.set(x, bottom - 5, wood[1])
    for x in range(dx0, dx1):  # recessed: the lintel shades the top of the leaf
        cv.darken(x, dy0 + (w // 2 - 2 if arch else 0), 0.55)
        cv.darken(x, dy0 + 1 + (w // 2 - 2 if arch else 0), 0.3)
    for y in range(dy0, bottom):
        if inside_arch(dx0, y):
            cv.darken(dx0, y, 0.3)
    hy = dy0 + h // 2 + 1
    handles = (cx - 2, cx + 1) if style == "double" else (dx1 - 3,)
    for hx in handles:
        cv.set(hx, hy, BRASS)
        cv.set(hx, hy + 1, TRIM[1])
    if step:
        sy = bottom if step_at is None else step_at
        for y in range(sy, sy + 4):
            for x in range(dx0 - 3, dx1 + 3):
                c = STONE[1] if y == sy + 3 or x in (dx0 - 3, dx1 + 2) else STONE[5] if y == sy else STONE[4] if x < cx + 2 else STONE[3]
                cv.set(x, y, c)
    return dx0, dx1, dy0


def window(cv, rnd, cx, y0, w=12, h=11, shutters=None, box=None, arch=False, frame=TRIM):
    x0, x1, y1 = cx - w // 2, cx - w // 2 + w, y0 + h

    def inside(x, y, grow=0):
        if not arch or y >= y0 + w // 2:
            return True
        r = w / 2 + grow
        return (x + 0.5 - (x0 + w / 2)) ** 2 + (y + 0.5 - (y0 + w / 2)) ** 2 <= r * r

    if shutters:
        sh = SHUTTERS[shutters]
        for side in (x0 - 5, x1 + 1):
            for y in range(y0, y1):
                for i in range(4):
                    c = sh[3] if i == 0 else sh[1] if i == 3 else sh[2]
                    if (y - y0) in (2, h - 3):
                        c = sh[4] if i < 3 else sh[2]
                    cv.set(side + i, y, c)
                cv.set(side + 4 if side < x0 else side - 1, y, WOOD[1])
    for y in range(y0 - 1, y1 + 1):
        for x in range(x0 - 1, x1 + 1):
            if inside(x, y, 1):
                cv.set(x, y, frame[3] if (x == x0 - 1 or y == y0 - 1) else frame[1])
    for y in range(y0, y1):
        for x in range(x0, x1):
            if not inside(x, y):
                continue
            lx, ly = x - x0, y - y0
            if lx in (w // 2 - 1, w // 2) or ly == h // 2:
                cv.set(x, y, frame[2] if lx == w // 2 - 1 or ly == h // 2 else frame[1])
                continue
            glint = (lx + ly) % 9 in (3, 4) and ly < h // 2 + 3
            v = 0.62 - 0.4 * ly / h + 0.08 * (1 - lx / w)
            c = GLASS[4] if glint else GLASS[max(1, min(3, round(1 + v * 2.4)))]
            if ly == 0 or ly == h // 2 + 1 or not inside(x, y - 1):
                c = GLASS[0]
            cv.set(x, y, c)
            cv.lit(x, y, LIT[3] if ly < h * 0.45 else LIT[2])
    sill = y1 + 1
    for x in range(x0 - 2, x1 + 2):
        cv.set(x, sill, frame[4] if x < x1 else frame[3])
        cv.set(x, sill + 1, frame[1])
    if box:
        flower_box(cv, rnd, x0 - 1, x1 + 1, sill)


def flower_box(cv, rnd, x0, x1, sill):
    for x in range(x0, x1):
        for y in range(sill + 2, sill + 5):
            c = WOOD[4] if y == sill + 2 else WOOD[2]
            cv.set(x, y, WOOD[1] if x == x1 - 1 else c)
    pal = FLOWER[rnd.randrange(len(FLOWER))]
    for x in range(x0 + 1, x1 - 1):
        for i in range(rnd.randint(1, 3)):
            cv.set(x, sill + 1 - i, LEAF[min(2, i + rnd.randint(0, 1))])
    for _ in range((x1 - x0) // 3):
        fx, fy = rnd.randint(x0 + 1, x1 - 2), sill - rnd.randint(1, 2)
        cv.set(fx, fy, pal[0])
        cv.set(fx, fy - 1, pal[0])
        if rnd.random() < 0.5:
            cv.set(fx + 1, fy, pal[0])
        if rnd.random() < 0.3:
            cv.set(fx, fy, pal[1])


def item(cv, x, y, kind, size=2):
    """A small round thing (fruit, loaf, bottle...) with its bottom at y."""
    d, m, l = GOODS[kind]
    if kind.startswith("potion"):
        for yy in range(y - 4, y):
            cv.set(x, yy, m)
            cv.set(x + 1, yy, d)
        cv.set(x, y - 3, l)
        cv.set(x, y - 5, "#d8d0c2")
        cv.set(x + 1, y - 5, "#a1978b")
        return
    if kind == "bread":
        for xx in range(x - 1, x + 3):
            cv.set(xx, y - 1, m)
            cv.set(xx, y - 2, l if xx < x + 2 else m)
        cv.set(x - 1, y - 2, m)
        cv.set(x, y - 3, l)
        cv.set(x + 1, y - 3, m)
        cv.set(x, y - 2, d)
        cv.set(x + 2, y - 1, d)
        return
    if kind == "fish":
        for xx in range(x - 2, x + 3):
            cv.set(xx, y - 1, m)
        cv.set(x - 2, y - 2, l)
        cv.set(x - 1, y - 2, l)
        cv.set(x + 2, y - 2, d)
        cv.set(x + 3, y - 1, d)
        cv.set(x - 2, y - 1, "#1c1a1f")
        return
    cv.set(x, y - 1, m)
    cv.set(x + 1, y - 1, d)
    cv.set(x, y - 2, l)
    cv.set(x + 1, y - 2, m)
    if size > 2:
        cv.set(x - 1, y - 1, m)
        cv.set(x - 1, y - 2, m)
        cv.set(x, y - 3, m)
    if kind == "apple":
        cv.set(x + 1, y - 3, LEAF[1])
    if kind == "pumpkin":
        cv.set(x, y - 3, LEAF[0])


def shop_window(cv, rnd, x0, x1, y0, y1, goods, frame=TRIM):
    """A wide display window with a shelf of goods behind small panes."""
    for y in range(y0 - 2, y1 + 2):
        for x in range(x0 - 2, x1 + 2):
            cv.set(x, y, frame[3] if (x < x0 - 1 or y < y0 - 1) else frame[2] if (x < x0 or y < y0) else frame[1])
    shelf = y0 + (y1 - y0) * 5 // 9
    for y in range(y0, y1):
        for x in range(x0, x1):
            ly = y - y0
            c = GLASS[1] if ly > 2 else GLASS[0]
            if ly > (y1 - y0) // 3:
                c = "#2c3a48"  # the dim shop behind the glass
            cv.set(x, y, c)
            cv.lit(x, y, LIT[3] if ly < (y1 - y0) * 0.5 else LIT[2])
    for x in range(x0, x1):
        cv.set(x, shelf, WOOD[4])
        cv.set(x, shelf + 1, WOOD[1])
        cv.set(x, y1 - 1, WOOD[3])
    for row_y in (shelf, y1 - 1):
        x = x0 + 1
        while x < x1 - 2:
            item(cv, x, row_y, goods[rnd.randrange(len(goods))])
            x += rnd.randint(3, 4)
    mull = [x0 + (x1 - x0) * i // 3 for i in (1, 2)]
    for mx in mull:  # mullions and a glint
        for y in range(y0, y1):
            cv.set(mx, y, frame[2])
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x - x0 + y - y0) % 13 in (4, 5) and y - y0 < (y1 - y0) // 2 and x not in mull:
                cv.set(x, y, GLASS[3])
    glass = {C(c) for c in (GLASS[0], GLASS[1], GLASS[3], "#2c3a48")}
    frames = {C(frame[2]), C(WOOD[1])}
    for y in range(y0, y1):  # at night the glass glows and the goods on the shelves catch the light
        for x in range(x0, x1):
            px = cv.get(x, y)
            if px in frames:
                cv.unlit(x, y)
            elif px not in glass:
                cv.lit(x, y, LIT[1] if sum(px[:3]) > 330 else LIT[0])
    for x in range(x0 - 2, x1 + 2):  # sill
        cv.set(x, y1 + 2, frame[4] if x < x1 else frame[3])
        cv.set(x, y1 + 3, frame[1])


def awning(cv, x0, x1, y0, depth, colour, scallop=True):
    """A striped canvas awning sloping out from the wall: from y0 down to y0+depth on screen."""
    col, white = CANVAS[colour]
    stripe = 4
    for y in range(y0, y0 + depth):
        t = (y - y0) / max(1, depth - 1)
        for x in range(x0, x1):
            k = ((x - x0) // stripe) % 2
            ramp = col if k == 0 else white
            lx = (x - x0) % stripe
            i = 2 if t < 0.75 else 1
            if lx == 0 and t > 0.1:
                i = min(3, i + 1)
            if y == y0:
                i = 3
            if y == y0 + depth - 1:
                i = 1
            cv.set(x, y, ramp[i])
    vy = y0 + depth  # valance with a scalloped edge
    for x in range(x0, x1):
        k = ((x - x0) // stripe) % 2
        ramp = col if k == 0 else white
        lx = (x - x0) % stripe
        for i in range(3):
            if scallop and i == 2 and lx in (0, stripe - 1):
                continue
            cv.set(x, vy + i, ramp[2] if i == 0 else ramp[1] if i == 2 else ramp[2 if lx else 3])
    for i in range(4):  # shadow under it on the wall
        for x in range(x0 + 1, x1 - 1):
            cv.darken(x, vy + 3 + i, [0.5, 0.35, 0.2, 0.08][i])
    for y in range(y0, vy + 2):  # iron rod at the ends
        cv.set(x0 - 1, y, IRON[1])
        cv.set(x1, y, IRON[1])


ICONS = {  # 7x6 sign icons: . clear, d dark, m mid, l light, g green, w white
    "bread": ["......", ".lll..", "lmmml.", "mdmdmm", "mmmmmd", ".dddd."],
    "apple": ["...g..", "..g...", ".mmlm.", "mmmllm", "mmmmmd", ".mddd."],
    "potion": ["..ww..", "..dd..", "..ml..", ".mmlm.", "mmmmmd", ".dddd."],
    "mug": ["wwwww.", "lllll.", "mmmmmdd", "mlmmmd.d", "mlmmmdd", "mmmmmd."],
    "hammer": ["dddd..", "dmmmd.", "dddd..", "..m...", "..m...", "..m..."],
    "fish": ["......", ".mm..m", "mllmmm", "mmmmdm", ".dd..d", "......"],
}
ICON_COL = {
    "bread": GOODS["bread"], "apple": GOODS["apple"], "potion": GOODS["potion_b"],
    "mug": ["#6b3c17", "#c9862e", "#f0c35a"], "hammer": IRON, "fish": GOODS["fish"],
}


def icon(cv, x, y, name):
    d, m, l = ICON_COL[name]
    for j, row in enumerate(ICONS[name]):
        for i, ch in enumerate(row):
            c = {"d": d, "m": m, "l": l, "g": LEAF[1], "w": "#fbf7ee"}.get(ch)
            if c:
                cv.set(x + i, y + j, c)


def hanging_sign(cv, x_wall, y, name, side=1):
    """An iron bracket out from the wall with a board hanging under it."""
    for i in range(10):
        cv.set(x_wall + side * i, y, IRON[1])
    cv.set(x_wall + side * 9, y - 1, IRON[2])
    bx = x_wall + side * 2 if side > 0 else x_wall - 11
    for cx in (bx + 1, bx + 8):
        cv.set(cx, y + 1, IRON[2])
    for yy in range(y + 2, y + 12):
        for xx in range(bx, bx + 10):
            edge = xx in (bx, bx + 9) or yy in (y + 2, y + 11)
            cv.set(xx, yy, TRIM[1] if edge else WOOD[5] if yy == y + 3 else WOOD[4])
    icon(cv, bx + 2, y + 4, name)


def board_sign(cv, x0, x1, y, name):
    """A signboard over a door: wood with a border, an icon and painted lettering."""
    for yy in range(y, y + 9):
        for xx in range(x0, x1):
            edge = xx in (x0, x1 - 1) or yy in (y, y + 8)
            cv.set(xx, yy, TRIM[1] if edge else TRIM[3] if yy == y + 1 else TRIM[2])
    cx = (x0 + x1) // 2
    icon(cv, cx - 3, y + 2, name)
    for xx in list(range(x0 + 3, cx - 5)) + list(range(cx + 5, x1 - 3)):
        if (xx * 7) % 5 != 0:
            cv.set(xx, y + 4, WOOD[1])
            if (xx * 3) % 4 == 0:
                cv.set(xx, y + 5, WOOD[1])


def lantern(cv, x, y):
    """A small wall lantern; its glass glows at night."""
    cv.set(x - 2, y, IRON[1])
    cv.set(x - 1, y, IRON[1])
    for yy in range(y, y + 6):
        for xx in range(x, x + 3):
            frame = yy in (y, y + 5) or xx in (x, x + 2)
            cv.set(xx, yy, IRON[1] if frame else "#f3dc9a")
            if not frame:
                cv.lit(xx, yy, LIT[4] if yy < y + 3 else LIT[3])
    cv.set(x + 1, y - 1, IRON[2])


def crate(cv, rnd, x, bottom, w=10, h=7, goods=None):
    for y in range(bottom - h, bottom):
        for xx in range(x, x + w):
            edge = xx in (x, x + w - 1) or y in (bottom - h, bottom - 1)
            mid = y == bottom - h // 2 - 1
            c = WOOD[1] if edge else WOOD[5] if y == bottom - h + 1 else WOOD[3] if mid else WOOD[4]
            if xx > x + w * 0.6 and not edge:
                c = WOOD[3] if c == WOOD[4] else c
            cv.set(xx, y, c)
    if goods:
        x2 = x + 1
        while x2 < x + w - 2:
            item(cv, x2, bottom - h + 1, goods)
            x2 += 2 + rnd.randint(0, 1)
        x2 = x + 2
        while x2 < x + w - 3:
            item(cv, x2, bottom - h - 1, goods)
            x2 += 3


def barrel(cv, x, bottom, w=8, h=10):
    for y in range(bottom - h, bottom):
        bulge = 1 if bottom - h + 2 <= y < bottom - 2 else 0
        for xx in range(x - bulge, x + w + bulge):
            u = (xx - x + bulge) / (w + 2 * bulge)
            c = DARKWOOD[5] if u < 0.25 else DARKWOOD[4] if u < 0.6 else DARKWOOD[3]
            if xx in (x - bulge, x + w + bulge - 1):
                c = DARKWOOD[1]
            if y in (bottom - h + 2, bottom - 3):
                c = IRON[2] if u < 0.5 else IRON[1]
            cv.set(xx, y, c)
    for xx in range(x, x + w):  # lid seen from above
        cv.set(xx, bottom - h, DARKWOOD[6] if xx < x + w - 2 else DARKWOOD[5])
        cv.set(xx, bottom - h - 1, DARKWOOD[3])


def sack(cv, x, bottom):
    rows = [(1, 4), (0, 6), (0, 6), (0, 6), (1, 5)]
    for j, (a, b) in enumerate(rows):
        y = bottom - len(rows) + j
        for xx in range(x + a, x + b):
            c = "#cdb487" if xx < x + 3 else "#a98e60"
            if j == 0:
                c = "#8a7148"
            cv.set(xx, y, c)
    cv.set(x + 2, bottom - 6, "#8a7148")


# ================================================================ roofs

def roof_shingles(cv, seed, rx0, rx1, ridge_y, eave_y, ramp, ridge=True):
    """Front slope of wooden shingles from the ridge (cap above ridge_y) down to eave_y, with the
    fascia board at the bottom and barge boards up the ends."""
    row_h = 5
    roof_bot = eave_y - 3
    roof_h = roof_bot - ridge_y
    nrows = (roof_h + row_h - 1) // row_h
    for row in range(nrows):
        yb = roof_bot - 1 - row * row_h
        ry = random.Random(seed * 977 + row)
        x = rx0 - ry.randint(0, 6)
        while x < rx1:
            sw = ry.randint(4, 7)
            u = (x + sw / 2 - rx0) / (rx1 - rx0)
            depth = (yb - ridge_y) / max(1, roof_h)
            idx = tone(ramp, 0.7 - 0.2 * u - 0.12 * depth + ry.uniform(-0.07, 0.07))
            drop = 1 if ry.random() < 0.25 and row > 0 else 0
            for xx in range(max(x, rx0), min(x + sw, rx1)):
                for k in range(row_h + drop):
                    y = yb - k + drop
                    if y < ridge_y or y >= roof_bot:
                        continue
                    if k == row_h - 1 + drop:
                        c = ramp[2] if idx > 2 else ramp[1]
                    elif k == 0:
                        c = ramp[idx] if xx in (x, x + sw - 1) else ramp[idx + 1]
                    elif xx == x:
                        c = ramp[max(1, idx - 1)] if k > 1 else ramp[max(1, idx - 2)]
                    elif xx == x + 1 and k > 1:
                        c = ramp[idx + 1] if ry.random() < 0.5 else ramp[idx]
                    else:
                        c = ramp[idx]
                    cv.set(xx, y, c)
            x += sw
    for x in range(rx0, rx1):  # fascia
        cv.set(x, eave_y - 3, TRIM[3])
        cv.set(x, eave_y - 2, TRIM[2])
        cv.set(x, eave_y - 1, TRIM[1])
    top = ridge_y - (4 if ridge else 0)
    for y in range(top, eave_y):  # barge boards
        cv.set(rx0, y, TRIM[3])
        cv.set(rx0 + 1, y, TRIM[2])
        cv.set(rx1 - 2, y, TRIM[2])
        cv.set(rx1 - 1, y, TRIM[1])
    if ridge:
        for x in range(rx0, rx1):
            right = (x - rx0) / (rx1 - rx0) > 0.62
            cv.set(x, ridge_y - 4, ramp[4] if right else ramp[5])
            cv.set(x, ridge_y - 3, ramp[3] if right else ramp[4])
            cv.set(x, ridge_y - 2, ramp[2] if right else ramp[3])
            cv.set(x, ridge_y - 1, ramp[1])
            if (x - rx0) % 12 == 5:
                cv.set(x, ridge_y - 3, ramp[2])
                cv.set(x, ridge_y - 2, ramp[1])
            for i, k in enumerate((0.4, 0.22, 0.1)):
                cv.darken(x, ridge_y + i, k)


def roof_moss(cv, rnd, rx0, rx1, y_low, n):
    for _ in range(n):
        mx, my = rnd.randint(rx0 + 4, rx1 - 8), y_low - rnd.randint(0, 9)
        for i in range(rnd.randint(2, 5)):
            if cv.get(mx + i, my)[3]:
                cv.set(mx + i, my, MOSS[rnd.randint(1, 3)])
            if rnd.random() < 0.4 and cv.get(mx + i, my - 1)[3]:
                cv.set(mx + i, my - 1, MOSS[2])


def roof_thatch(cv, rnd, rx0, rx1, top, eave_y, ramp=ROOFS["thatch"]):
    """A thick straw roof: soft rounded corners, courses of straw whose lumpy, lit lower fringes
    overhang the course below (which is shaded just under them), vertical strands, a heavy
    rounded eave and a woven ridge band."""
    w = rx1 - rx0
    n = w + 8
    streak = [rnd.uniform(-0.1, 0.1) for _ in range(n)]
    lumps = {}
    course = 6
    rc_top, rc_bot = 4, 7

    def lump(c, i):  # the lower edge of a course: rounded straw bundles, a little uneven
        if c not in lumps:
            off = rnd.randint(0, 4)
            jit = [rnd.choice((0, 0, 0, 1)) for _ in range(n)]
            lumps[c] = [2 - abs((j + off) % 5 - 2) + jit[j] for j in range(n)]
        return lumps[c][i]

    dash = {(rnd.randint(rx0, rx1), rnd.randint(top, eave_y)) for _ in range(w * (eave_y - top) // 9)}

    def inside(x, y):
        for cx, cy, r, side in ((rx0 + rc_top, top + rc_top, rc_top, "tl"), (rx1 - 1 - rc_top, top + rc_top, rc_top, "tr"),
                                (rx0 + rc_bot, eave_y - rc_bot, rc_bot, "bl"), (rx1 - 1 - rc_bot, eave_y - rc_bot, rc_bot, "br")):
            if ((side[1] == "l" and x < cx) or (side[1] == "r" and x > cx)) and ((side[0] == "t" and y < cy) or (side[0] == "b" and y > cy)):
                if (x - cx) ** 2 + (y - cy) ** 2 > r * r + 1:
                    return False
        return True

    eave_top = eave_y - 6
    for y in range(top, eave_y + 2):
        for x in range(rx0, rx1):
            i = x - rx0
            u = i / w
            if not inside(x, min(y, eave_y)):
                continue
            ends = 0.12 * max(0.0, abs(u - 0.45) * 2 - 0.6)  # the hipped ends turn away a little
            base_v = 0.74 - 0.24 * u - ends + streak[i]
            strand = -0.12 if (x, y) in dash or (x, y - 1) in dash else 0.0
            if y >= eave_top:  # the heavy eave roll: lit on top, shaded under, ragged ends
                ly = y - eave_top
                if y > eave_y - 1 + lump(99, i) - 1:
                    continue
                v = base_v + (0.14 if ly < 2 else -0.05 if ly < 5 else -0.3) + strand
                cv.set(x, y, ramp[tone(ramp, v)] if ly < 6 else ramp[1])
                continue
            fy = eave_top - y  # rows above the eave roll
            c = fy // course
            k = fy % course  # 0 = bottom row of the course
            edge = lump(c, i)
            if k <= edge:
                v = base_v + 0.16 + strand  # lit fringe of this course
            elif k == edge + 1:
                v = base_v - 0.28  # this course in the shade of the fringe above it
            else:
                v = base_v - 0.06 * (k - edge - 2) / course + strand
            cv.set(x, y, ramp[tone(ramp, v)])
    for y in range(top, top + 6):  # woven ridge band
        for x in range(rx0, rx1):
            if not inside(x, y) or not cv.get(x, y)[3]:
                continue
            ly = y - top
            zig = (x - rx0 + (ly if (x // 6) % 2 else 5 - ly)) % 6 == 0
            c = ramp[2] if zig else ramp[4] if ly < 2 else ramp[3]
            if ly == 5:
                c = ramp[1]
            cv.set(x, y, c)
    for x in range(rx0, rx1):  # the band throws a little shadow
        for i, k in enumerate((0.3, 0.12)):
            cv.darken(x, top + 6 + i, k)


def roof_gable(cv, seed, x0, x1, ey, depth, ramp, slope=0.72):
    """A roof whose gable faces the viewer: two planes running back from the front gable, the
    left one lit, the right one in shade, with the ridge running up the middle. x0..x1 are the
    eave corners; ey their height. Returns the apex (x, y) of the front gable."""
    cx = (x0 + x1 - 1) / 2
    half = (x1 - x0) / 2
    ay = ey - half * slope
    rnd = random.Random(seed)
    for y in range(int(ay - depth) - 1, ey + 1):
        for x in range(x0, x1):
            dx = abs(x + 0.5 - (x0 + x1) / 2)
            yf = ey - (half - dx) * slope  # front edge of the plane at this x
            if y > yf or y < yf - depth:
                continue
            left = x < cx
            s = (half - dx) / half  # 0 at the eave .. 1 at the ridge
            t = yf - y  # 0 at the front .. depth at the back
            ci = int(s * half / 4)  # course index (courses run front to back)
            pos = (s * half) % 4
            off = (ci * 3) % 7
            joint = int((t + off) % 7) == 0
            base = 0.72 if left else 0.4
            idx = tone(ramp, base - 0.1 * (t / depth) + ((ci * 37) % 5 - 2) * 0.025)
            if pos < 1:
                c = ramp[min(len(ramp) - 1, idx + 1)]  # lit butt edge of the course
            elif pos >= 3:
                c = ramp[max(1, idx - 1)]
            elif joint:
                c = ramp[max(1, idx - 2)]
            else:
                c = ramp[idx]
            cv.set(x, y, c)
    for y in range(int(ay - depth), int(ay) + 1):  # ridge cap up the middle
        cv.set(int(cx), y, ramp[5])
        cv.set(int(cx) + 1, y, ramp[3])
        if int(cx) + 2 < x1:
            cv.set(int(cx) + 2, y, ramp[2])
    for x in range(x0, x1):  # barge boards along the front gable
        dx = abs(x + 0.5 - (x0 + x1) / 2)
        yf = round(ey - (half - dx) * slope)
        left = x < cx
        cv.set(x, yf, TRIM[3] if left else TRIM[2])
        cv.set(x, yf - 1, TRIM[4] if left else TRIM[3])
        cv.set(x, yf + 1, TRIM[1])
        yb = round(ey - (half - dx) * slope - depth)  # back edge of the planes
        cv.set(x, yb, ramp[5] if left else ramp[4])
    _ = rnd
    return cx, ay


def gable_fill(cv, x0, x1, ey, slope, fill, xmin, xmax):
    """Fill the front gable under the barge boards of a roof_gable(x0, x1, ey, slope) with
    fill(x, y), between the walls xmin..xmax."""
    half = (x1 - x0) / 2
    for y in range(int(ey - half * slope) + 1, ey + 1):
        for x in range(xmin, xmax):
            dx = abs(x + 0.5 - (x0 + x1) / 2)
            if y > ey - (half - dx) * slope + 1.5:
                fill(x, y)


def chimney(cv, cx0, top, base, cw=10):
    for y in range(base - 6, base + 4):  # shadow on the roof, down and to the right
        for x in range(cx0 + cw, cx0 + cw + 4 - max(0, y - base)):
            cv.darken(x, y, 0.4)
    for y in range(top + 2, base):
        k = (y - top - 2) % 4
        for x in range(cx0, cx0 + cw):
            lx = x - cx0
            v = 0.62 - 0.35 * lx / cw
            c = STONE[1] if (k == 3 or (lx + (y // 4) * 3) % 5 == 4) else STONE[tone(STONE, v)]
            if lx == 0:
                c = STONE[5]
            cv.set(x, y, c)
    for x in range(cx0 - 1, cx0 + cw + 1):
        cv.set(x, top, STONE[5])
        cv.set(x, top + 1, STONE[3])
        cv.set(x, top + 2, STONE[2])
    for x in range(cx0 + 2, cx0 + cw - 2):
        cv.set(x, top, "#1b1716")
    for x in range(cx0, cx0 + cw):
        cv.set(x, base, STONE[2])
    return cx0 + cw // 2, top


def porch(cv, seed, x0, x1, y_top, y_bot, posts, base, ramp):
    """A lean-to porch roof along the front on posts, with a board deck in front."""
    roof_shingles(cv, seed, x0, x1, y_top, y_bot, ramp, ridge=False)
    for x in range(x0, x1):  # flashing against the wall above
        cv.set(x, y_top - 1, TRIM[1])
    eave_shadow(cv, x0 + 2, x1 - 2, y_bot, rows=7, strength=0.9)
    for px in posts:
        for y in range(y_bot, base):
            cv.set(px, y, TRIM[3])
            cv.set(px + 1, y, TRIM[2])
            cv.set(px + 2, y, TRIM[1])
        cv.set(px - 1, y_bot, TRIM[2])  # brackets under the beam
        cv.set(px + 3, y_bot, TRIM[1])
    for y in range(base - 1, base + 4):  # deck
        for x in range(x0 + 1, x1 - 1):
            k = (x - x0) % 5
            c = WOOD[1] if y == base + 3 or k == 4 else WOOD[5] if y == base - 1 else WOOD[4] if k == 0 else WOOD[3]
            cv.set(x, y, c)


# ================================================================ designs

def _result(cv, kind, anchor, footprint, door_x=None, door_w=14, chimneys=()):
    W = cv.w
    info = {
        "kind": kind,
        "anchor": [anchor[0], anchor[1]],
        "footprint": footprint,
        "door": [door_x - anchor[0], 0] if door_x is not None else None,
        "door_size": [door_w, 22] if door_x is not None else None,
        "chimney": [[c[0] - anchor[0], c[1] - anchor[1]] for c in chimneys],
        "size": [W, cv.h],
    }
    return cv.im, cv.night, info


def cabin(spec):
    """Plain log cabin: plank walls, shingle roof, shuttered windows, a chimney."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, wall_h, foot_h, roof_h, over = spec.get("width", 80), 30, 5, spec.get("roof", 40), 5
    roof = ROOFS[spec.get("roof_colour", "rust")]
    chim = spec.get("chimney", 0.72)
    W = wall_w + over * 2 + 4
    ridge_y = 2 + (12 if chim is not None else 0) + 4
    eave_y = ridge_y + roof_h
    wall_top = eave_y - 4
    base = eave_y + wall_h + foot_h
    cv = Canvas(W, base + 5)
    wx0, wx1 = 2 + over, 2 + over + wall_w
    planks(cv, rnd, wx0, wx1, wall_top, base - foot_h)
    _corner_posts(cv, wx0, wx1, wall_top, base - foot_h)
    footing(cv, rnd, wx0 - 1, wx1 + 1, base - foot_h, base)
    dcx = wx0 + round(wall_w * spec.get("door_at", 0.5))
    door(cv, rnd, dcx, base - foot_h, style=spec.get("door", "plank"), step_at=base - 1)
    for wf in spec.get("windows", (0.2, 0.8)):
        window(cv, rnd, wx0 + round(wall_w * wf), base - foot_h - 19, shutters=spec.get("shutters"), box=spec.get("flowers"))
    eave_shadow(cv, wx0, wx1, wall_top)
    roof_shingles(cv, spec.get("seed", 1), 2, W - 2, ridge_y, eave_y, roof)
    roof_moss(cv, rnd, 2, W - 2, eave_y - 4, spec.get("moss", 0))
    chims = []
    if chim is not None:
        chims.append(chimney(cv, 2 + round((W - 4) * chim) - 5, 2, ridge_y + 8))
    cv.outline()
    fh = roof_h // 2 + 10
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -fh, wall_w, fh], dcx, chimneys=chims)


def _corner_posts(cv, wx0, wx1, y0, y1):
    for px0, light in ((wx0, True), (wx1 - 4, False)):
        for y in range(y0, y1):
            cols = [TRIM[3], TRIM[1], TRIM[1], WOOD[1]] if light else [TRIM[2], TRIM[1], WOOD[2], WOOD[1]]
            for i, c in enumerate(cols):
                cv.set(px0 + i, y, c)


def cottage(spec):
    """Low fieldstone cottage under a thick thatched roof, arched door and small windows."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, wall_h, roof_h, over = spec.get("width", 64), 26, 34, 6
    W = wall_w + over * 2 + 4
    top = 2 + 12
    eave_y = top + roof_h
    wall_top = eave_y - 5
    base = eave_y + wall_h
    cv = Canvas(W, base + 5)
    wx0, wx1 = 2 + over, 2 + over + wall_w
    stones(cv, rnd, wx0, wx1, wall_top, base)
    for y in range(wall_top, base):  # rounder, bigger corner stones
        cv.set(wx0, y, FIELDSTONE[4] if (y // 5) % 2 else FIELDSTONE[3])
        cv.set(wx1 - 1, y, FIELDSTONE[2] if (y // 5) % 2 else FIELDSTONE[1])
    dcx = wx0 + round(wall_w * 0.66)
    door(cv, rnd, dcx, base, w=14, h=21, style="arched", wood=DARKWOOD)
    window(cv, rnd, wx0 + round(wall_w * 0.25), base - 18, w=10, h=10, box=True)
    eave_shadow(cv, wx0, wx1, wall_top + 1)
    roof_thatch(cv, rnd, 2, W - 2, top, eave_y)
    cxm = chimney(cv, 2 + round((W - 4) * 0.22) - 5, 2, top + 6)
    # a climbing rose on the corner
    for y in range(base - 22, base - 1):
        x = wx1 - 3 + round(math.sin(y * 0.6))
        cv.set(x, y, LEAF[rnd.randint(0, 2)])
        if rnd.random() < 0.25:
            cv.set(x + rnd.choice((-1, 1)), y, "#ff9ec4")
    cv.outline()
    fh = 26
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -fh, wall_w, fh], dcx, chimneys=[cxm])


def townhouse(spec):
    """Two storeys with the gable to the street: stone below, plaster and timber above, a small
    jetty, flower boxes."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, low_h, up_h, over, depth, slope = spec.get("width", 54), 28, 24, 4, 14, 0.72
    roof = ROOFS[spec.get("roof_colour", "slate")]
    half = (wall_w + 2 * (over + 2)) / 2
    gable_h = math.ceil(half * slope)
    side = 10 if spec.get("sign") else 0  # room for a hanging sign
    W = wall_w + 2 * (over + 2) + 4 + 2 * side
    ey = 2 + depth + gable_h + 2
    up_top = ey
    up_bot = up_top + up_h
    base = up_bot + low_h
    cv = Canvas(W, base + 5)
    wx0, wx1 = side + 2 + over + 2, side + 2 + over + 2 + wall_w
    # ground floor: stone; upper floor: plaster in a timber frame, jettied out a little
    lower = spec.get("lower", "stone")
    if lower == "stone":
        stones(cv, rnd, wx0, wx1, up_bot, base)
    else:
        planks(cv, rnd, wx0, wx1, up_bot, base)
        _corner_posts(cv, wx0, wx1, up_bot, base)
    plaster(cv, rnd, wx0 - 2, wx1 + 2, up_top, up_bot, PAINT[spec.get("plaster", "cream")])
    timber(cv, wx0 - 2, wx1 + 2, up_top, up_bot, studs=(wx0 + wall_w // 2 - 1,))
    for x in range(wx0 - 2, wx1 + 2):  # jetty beam and its shadow on the wall below
        cv.set(x, up_bot, DARKWOOD[4])
        cv.set(x, up_bot + 1, DARKWOOD[2])
        for i, k in enumerate((0.5, 0.3, 0.12)):
            if wx0 <= x < wx1:
                cv.darken(x, up_bot + 2 + i, k)
    for frac in (0.25, 0.75):
        window(cv, rnd, wx0 + round(wall_w * frac), up_top + 6, w=10, h=10, box=spec.get("flowers", True))
    dcx = wx0 + round(wall_w * spec.get("door_at", 0.3))
    door(cv, rnd, dcx, base, style=spec.get("door", "plank"), wood=DARKWOOD)
    win2 = 0.75 if spec.get("door_at", 0.3) < 0.5 else 0.25
    window(cv, rnd, wx0 + round(wall_w * win2), base - 20, w=12, h=11, shutters=spec.get("shutters"))
    if spec.get("sign"):
        hanging_sign(cv, wx1 if win2 < 0.5 else wx0, up_bot + 4, spec["sign"], 1 if win2 < 0.5 else -1)
    # roof with the gable to the front
    gx0, gx1 = side + 2, W - 2 - side
    pal = PAINT[spec.get("plaster", "cream")]
    gable_fill(cv, gx0, gx1, ey, slope, lambda x, y: cv.set(x, y, pal[tone(pal, 0.7 - 0.2 * (x - gx0) / W)]), wx0 - 2, wx1 + 2)
    cxg = (gx0 + gx1) // 2
    for y in range(int(ey - half * slope) + 4, ey):  # king post and collar beam in the gable
        cv.set(cxg - 1, y, DARKWOOD[4])
        cv.set(cxg, y, DARKWOOD[3])
        cv.set(cxg + 1, y, DARKWOOD[1])
    for y in range(ey - 3, ey):
        for x in range(wx0 - 2, wx1 + 2):
            cv.set(x, y, DARKWOOD[4] if y == ey - 3 else DARKWOOD[3] if y == ey - 2 else DARKWOOD[1])
    vy = ey - gable_h // 2 - 1  # a little round vent
    for y in range(vy - 2, vy + 3):
        for x in range(cxg - 3, cxg + 4):
            d = (x - cxg) ** 2 + (y - vy) ** 2
            if d <= 6:
                cv.set(x, y, "#2c2622" if d <= 2 else DARKWOOD[3])
    roof_gable(cv, spec.get("seed", 1), gx0, gx1, ey, depth, roof, slope)
    eave_shadow(cv, wx0 - 2, wx1 + 2, ey + 1, rows=4, strength=0.6)
    cv.outline()
    fh = 30
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -fh, wall_w, fh], dcx)


def shop(spec):
    """A shop: painted boards, a display window under a striped awning, a glazed door with a
    signboard over it, goods set out in front."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, wall_h, foot_h, roof_h, over = spec.get("width", 84), 36, 4, 30, 5
    roof = ROOFS[spec.get("roof_colour", "slate")]
    paint = PAINT[spec.get("paint", "sage")]
    W = wall_w + over * 2 + 4
    ridge_y = 2 + 12 + 4
    eave_y = ridge_y + roof_h
    wall_top = eave_y - 4
    base = eave_y + wall_h + foot_h
    cv = Canvas(W, base + 5)
    wx0, wx1 = 2 + over, 2 + over + wall_w
    if spec.get("paint") == "cream":
        plaster(cv, rnd, wx0, wx1, wall_top, base - foot_h, PLASTER)
        timber(cv, wx0, wx1, wall_top, base - foot_h, studs=(wx0 + wall_w // 2 - 1,))
    else:
        boards(cv, rnd, wx0, wx1, wall_top, base - foot_h, paint)
    _corner_posts(cv, wx0, wx1, wall_top, base - foot_h)
    footing(cv, rnd, wx0 - 1, wx1 + 1, base - foot_h, base)
    door_left = spec.get("door_at", 0.72) > 0.5
    dcx = wx0 + round(wall_w * spec.get("door_at", 0.72))
    sx0 = wx0 + 7 if door_left else dcx + 12
    sx1 = dcx - 12 if door_left else wx1 - 7
    shop_window(cv, rnd, sx0, sx1, base - foot_h - 22, base - foot_h - 6, spec["goods"])
    door(cv, rnd, dcx, base - foot_h, style="glazed", step_at=base - 1)
    board_sign(cv, dcx - 11, dcx + 11, wall_top + 5, spec["sign"])
    awning(cv, sx0 - 3, sx1 + 3, base - foot_h - 30, 6, spec.get("awning", "red"))
    lantern(cv, dcx + 10, base - foot_h - 20)
    eave_shadow(cv, wx0, wx1, wall_top)
    roof_shingles(cv, spec.get("seed", 1), 2, W - 2, ridge_y, eave_y, roof)
    roof_moss(cv, rnd, 2, W - 2, eave_y - 4, spec.get("moss", 2))
    chims = [chimney(cv, 2 + round((W - 4) * (0.18 if door_left else 0.8)) - 5, 2, ridge_y + 8)]
    # goods set out in front of the window
    gx = sx0 + 1
    crate(cv, rnd, gx, base + 1, goods=spec["goods"][0] if spec["goods"][0] in GOODS and not spec["goods"][0].startswith("potion") else None)
    if spec.get("barrel", True):
        barrel(cv, sx1 - 9, base + 1)
    if spec.get("sack"):
        sack(cv, gx + 11, base + 1)
    cv.outline()
    fh = 26
    return _result(cv, "shop", (W // 2, base), [wx0 - W // 2, -fh, wall_w, fh], dcx, chimneys=chims)


def inn(spec):
    """The inn: two storeys of planks under a long shingle roof, a porch on posts along the
    front, double doors, a hanging sign and lanterns either side."""
    rnd = random.Random(spec.get("seed", 1))
    wall_w, low_h, up_h, foot_h, roof_h, over = spec.get("width", 100), 30, 24, 4, 34, 5
    roof = ROOFS[spec.get("roof_colour", "rust")]
    W = wall_w + over * 2 + 4
    ridge_y = 2 + 12 + 4
    eave_y = ridge_y + roof_h
    wall_top = eave_y - 4
    floor_y = wall_top + up_h
    base = floor_y + low_h + foot_h
    cv = Canvas(W, base + 6)
    wx0, wx1 = 2 + over, 2 + over + wall_w
    planks(cv, rnd, wx0, wx1, wall_top, base - foot_h, DARKWOOD if spec.get("dark") else WOOD)
    _corner_posts(cv, wx0, wx1, wall_top, base - foot_h)
    footing(cv, rnd, wx0 - 1, wx1 + 1, base - foot_h, base)
    for frac in (0.17, 0.39, 0.61, 0.83):  # upper windows
        window(cv, rnd, wx0 + round(wall_w * frac), wall_top + 7, w=10, h=10, shutters=spec.get("shutters", "green"),
               box=frac in (0.39, 0.61))
    dcx = wx0 + wall_w // 2
    door(cv, rnd, dcx, base - foot_h, w=18, h=22, style="double", wood=DARKWOOD, step=False)
    for frac in (0.2, 0.8):
        window(cv, rnd, wx0 + round(wall_w * frac), base - foot_h - 20, w=14, h=12)
    lantern(cv, dcx - 15, base - foot_h - 21)
    lantern(cv, dcx + 13, base - foot_h - 21)
    eave_shadow(cv, wx0, wx1, wall_top)
    porch(cv, spec.get("seed", 1) + 5, wx0 - 3, wx1 + 3, floor_y - 2, floor_y + 8, (wx0, wx0 + wall_w // 3 - 2, wx1 - wall_w // 3 - 1, wx1 - 3),
          base, roof)
    board_sign(cv, dcx - 15, dcx + 15, floor_y - 1, spec.get("sign", "mug"))
    roof_shingles(cv, spec.get("seed", 1), 2, W - 2, ridge_y, eave_y, roof)
    roof_moss(cv, rnd, 2, W - 2, eave_y - 4, spec.get("moss", 4))
    chims = [chimney(cv, 2 + round((W - 4) * 0.2) - 5, 2, ridge_y + 8), chimney(cv, 2 + round((W - 4) * 0.8) - 5, 2, ridge_y + 8)]
    barrel(cv, wx0 + 2, base + 3)
    barrel(cv, wx0 + 11, base + 3, w=7, h=9)
    cv.outline()
    fh = 32
    return _result(cv, "house", (W // 2, base), [wx0 - W // 2, -fh, wall_w, fh], dcx, door_w=18, chimneys=chims)


def stall(spec):
    """A market stall: a striped canopy on four posts over a wooden counter piled with goods."""
    rnd = random.Random(spec.get("seed", 1))
    w = spec.get("width", 44)
    canopy_d, counter_h = 14, 11
    W = w + 8
    top = 2
    can_bot = top + canopy_d
    base = can_bot + 30
    cv = Canvas(W, base + 3)
    x0, x1 = 4, 4 + w
    # back posts (seen above the counter, under the canopy)
    for px in (x0 + 2, x1 - 4):
        for y in range(can_bot, base - counter_h):
            cv.set(px, y, DARKWOOD[4])
            cv.set(px + 1, y, DARKWOOD[2])
    # open behind: only the shade of the canopy on the ground, and a rail of hanging goods
    for y in range(can_bot, base - counter_h):
        a = max(0, 90 - (y - can_bot) * 6)
        for x in range(x0 + 2, x1 - 2):
            if a and not cv.get(x, y)[3]:
                cv.set(x, y, (16, 30, 26, a))
    rail = can_bot + 3
    for x in range(x0 + 2, x1 - 2):
        cv.set(x, rail, DARKWOOD[4])
        cv.set(x, rail + 1, DARKWOOD[2])
    hang = spec.get("hang")
    if hang:
        for hx in range(x0 + 6, x1 - 6, 6):
            cv.set(hx, rail + 2, "#cdb487")
            item(cv, hx, rail + 5 + (hx // 6) % 2, hang)
    # counter: a top board with goods on it, front panel of vertical boards
    cy = base - counter_h
    for y in range(cy, base):
        for x in range(x0 + 1, x1 - 1):
            if y < cy + 2:
                c = WOOD[5] if y == cy else WOOD[4]
            else:
                k = (x - x0) % 5
                c = WOOD[1] if k == 4 or y == base - 1 else WOOD[4] if k == 0 else WOOD[3]
                if x > x1 - w * 0.35 and c == WOOD[3]:
                    c = WOOD[2]
            cv.set(x, y, c)
    goods = spec["goods"]
    x = x0 + 3
    slot = 0
    while x < x1 - 9:  # baskets / trays of goods on the counter
        g = goods[slot % len(goods)]
        bw = 9
        for xx in range(x, x + bw):
            cv.set(xx, cy - 1, "#a07a46" if xx < x + bw - 2 else "#7a5a32")
            cv.set(xx, cy, "#6b4e2a")
        for row in range(2):
            gx = x + 1 + row
            while gx < x + bw - 2:
                item(cv, gx, cy - 1 - row * 2, g)
                gx += 2 if row == 0 else 3
        x += bw + 1
        slot += 1
    # front posts
    for px in (x0, x1 - 2):
        for y in range(can_bot, base):
            cv.set(px, y, DARKWOOD[5])
            cv.set(px + 1, y, DARKWOOD[3])
    # canopy: striped cloth sloping toward the viewer, scalloped valance
    awning(cv, x0 - 1, x1 + 1, top + 1, canopy_d - 3, spec.get("canopy", "red"))
    for x in range(x0 - 1, x1 + 1):  # ridge pole
        cv.set(x, top, DARKWOOD[4])
    if spec.get("crate", True):
        crate(cv, rnd, x1 - 13, base + 2, w=9, h=6, goods=goods[-1] if not goods[-1].startswith("potion") else None)
    cv.outline()
    fh = 12
    return _result(cv, "stall", (W // 2, base), [x0 - W // 2, -fh, w, fh])


DESIGNS = {"cabin": cabin, "cottage": cottage, "townhouse": townhouse, "shop": shop, "inn": inn, "stall": stall}
