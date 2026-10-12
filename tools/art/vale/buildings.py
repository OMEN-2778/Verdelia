"""Palettes and the small 2D parts of the town buildings: doors, windows, shop windows, flower
boxes, signs with icons, lanterns, goods, sacks. The 3D models (town3d.py, market3d.py) draw them
onto the walls and tops they belong to after rendering.

What glows at night (window glass, lanterns) is also drawn into the canvas's night image, in
colours whose blue is exactly 3/255: the mark the screen grade (shaders/grade.gdshader) looks for
to keep lamplight bright at night, while characters walking past still hide it correctly.
"""
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


