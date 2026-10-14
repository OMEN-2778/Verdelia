"""The hero's home: pieces for its rooms that the general interior set (interior3d.py) doesn't
have, in the same light, calm palette.

- The hero's own bed is a double bed turned sideways, its head against the left wall, and in
  the dark under it lives the little monster the hero keeps secret: a soft black blob whose eyes
  blink (an animated part, "eyes").
- Grandmother's room has been cleared since she died: her bed is bare with the bedding folded
  on it, her things are packed in tied boxes, her armchair and cabinet wait under dust sheets,
  and her portrait hangs on the wall.
- The sitting room, hardly used: a sofa, an armchair, a low table, a cold fireplace.
- The tiny kitchen: a little table for two.
- A doorway wall segment (its opening is walkable), the hero's desk, a doormat.
"""
import math
import random

import interior3d as I
import materials as M
from buildings import BRASS, IRON, LIT, item
from interior3d import (BRASSR, CLOTH, DARKWOOD, LINEN, SEG, WALL_H, WALL_T, WOOD, _chair, _panel, _quilt_mat, _r7,
                        _spindles, _wall_scene, done, fp)
from market import candle, jug
from oblique import Mat, Scene, box, hsh, prism, prism_x
from PIL import Image

GROUP = "室内"
SAGE = ["#3c4b40", "#56685a", "#6f8372", "#879a89", "#a0b2a0", "#bccbb9", "#d6e0d1"]  # sofa upholstery
ROSE = ["#5e3c3a", "#7e5450", "#9c6e68", "#b48a82", "#c9a69d", "#dcc1b8", "#ece0d8"]
SHEET = ["#7d776c", "#a49d90", "#c4bdb0", "#d8d2c6", "#e6e1d7", "#f0ece4", "#f8f6f1"]  # dust sheets
CARD = ["#5a4430", "#7d6246", "#9c8060", "#b49a77", "#c8b08e", "#d9c4a5", "#e8d8bf"]  # cardboard
TICKING = ["#8a8478", "#b0a998", "#cfc8b8", "#e2dccf", "#eeeae0"]


def _fabric(ramp, bias=0.1, seed=1):
    """Upholstery: soft, a faint weave, darker in the creases."""
    def f(u, v, kind, light, P, s):
        g = (hsh(math.floor(u), math.floor(v), seed) - 0.5) * 0.08
        return I._t(ramp, light + bias + g)
    return Mat(f)


def _sheet_mat(seed=1):
    """A dust sheet draped over furniture: pale, with long soft folds hanging down the sides."""
    def f(u, v, kind, light, P, s):
        if kind == "top":
            return I._t(SHEET, light + 0.06 + (hsh(math.floor(P[0] / 3), math.floor(P[1] / 3), seed) - 0.5) * 0.06)
        k = (u + 2 * math.sin(v * 0.4 + seed)) % 6
        lv = light - 0.06 + (0.1 if k < 1.5 else -0.14 if k > 4.5 else 0)
        return I._t(SHEET, lv)
    return Mat(f)


# ================================================================ the hero's bed

EYE_W, EYE_H = 12, 5
EYE_FRAMES = 12


def _eyes_frame(f):
    """Two round eyes in the dark: open most of the time, a blink, a glance left and right."""
    im = Image.new("RGBA", (EYE_W, EYE_H))
    px = im.load()
    look = {9: -1, 10: 1}.get(f, 0)
    lid = {6: 1, 7: 2, 8: 1}.get(f, 0)  # 0 open, 1 half shut, 2 shut
    for cx in (3, 8):
        if lid == 2:
            for dx in (-1, 0, 1):
                px[cx + dx, 3] = (196, 188, 170, 255)
            continue
        for dy in range(-1 if lid == 0 else 0, 2):
            for dx in (-1, 0, 1):
                if dx * dx + dy * dy <= 2:
                    px[cx + dx, 2 + dy] = (246, 242, 230, 255)
        px[cx + look, 2] = (24, 18, 30, 255)  # pupil
        if lid == 0:
            px[cx - 1, 1] = (255, 255, 255, 255)  # a glint
    return im


def eyes_sheet():
    sheet = Image.new("RGBA", (EYE_W * EYE_FRAMES, EYE_H))
    for f in range(EYE_FRAMES):
        sheet.alpha_composite(_eyes_frame(f), (f * EYE_W, 0))
    return sheet


def bed_side(spec):
    """A double bed turned sideways along the left wall: the headboard at the left end, a low
    footboard at the right, the long side facing the room with the quilt hanging over it and the
    sheet turned down by the pillows. It stands high on its legs, and in the dark under it sits a
    soft black blob, peeping out, with blinking eyes."""
    L, D, leg = 25, 26, 8  # half length along x, depth, height of the space under it
    fw = M.wood(WOOD, bias=0.12)
    S = Scene(pad_top=3)
    S.add(box(-L + 2, L - 2, 1, D - 1, 0, 0.4, M.flat(["#120e16", "#120e16", "#18131d", "#1d1823", "#231d2a"])))  # the dark under it
    for x in (-L, L - 2):
        for y in (0, D - 2):
            S.add(box(x, x + 2, y, y + 2, 0, leg, fw))  # legs
    S.add(box(-L, L, 0, D, leg, leg + 3, M.planks(WOOD, h=3, seed=3)))  # side rails
    S.add(box(-L + 0.5, L - 0.5, 1, D - 1, leg + 3, leg + 6, M.flat(LINEN)))  # mattress
    quilt = _quilt_mat(spec.get("quilt", "blue"), spec.get("seed", 1))
    S.add(box(-L + 12, L + 0.5, -0.8, D + 0.5, leg + 2, leg + 7, quilt))  # quilt, hanging over the side
    S.add(box(-L + 10, -L + 12.5, -0.5, D, leg + 5.5, leg + 7.5, M.flat(LINEN, 0.15)))  # the sheet turned down over it
    pil = M.flat(["#8a8478", "#b8b0a2", "#ddd6c8", "#eeeae0", "#f8f6f0", "#ffffff"])
    for y0 in (1.5, 13.5):  # two pillows at the head, one behind the other
        S.add(prism(-L + 5.5, y0 + 5.5, 5, leg + 6, leg + 8.5, pil, sides=12))
    S.add(box(-L - 3, -L, 0, D, 0, leg + 16, M.planks(WOOD, h=5, seed=5)))  # headboard
    for y in (-0.5, D - 2.5):
        S.add(box(-L - 3.5, -L + 0.5, y, y + 3, 0, leg + 18, fw))
        S.add(prism(-L - 1.5, y + 1.5, 1.7, leg + 18, leg + 20.5, fw, sides=8))
    S.add(box(L, L + 3, 0, D, 0, leg + 9, M.planks(WOOD, h=4, seed=6)))  # footboard
    for y in (-0.5, D - 2.5):
        S.add(box(L - 0.5, L + 3.5, y, y + 3, 0, leg + 11, fw))
        S.add(prism(L + 1.5, y + 1.5, 1.6, leg + 11, leg + 13, fw, sides=8))
    cv = S.render()
    # the blob: a soft heap of black, a little purple on top, peeping out from under the rail
    cx, gy = S.sx(3), S.sy(0, 0) + 2  # it sits just out from under the edge
    for dy in range(0, 9):
        half = round(9.5 * math.sqrt(max(0.0, 1 - (dy / 9.0) ** 2)))
        for dx in range(-half, half + 1):
            x, y = cx + dx, gy - dy
            if abs(dx) == half or dy == 8 or dy == 0:
                c = "#0a080d"  # its outline
            elif dy >= 6 and dx < 0:
                c = "#3a3046"  # soft light on its crown
            elif dy >= 5:
                c = "#2a2234"
            else:
                c = "#1c1724"
            if 0 <= y < cv.h and (cv.get(x, y)[3] == 0 or S.sid[y, x] in (-1, 0)):
                cv.set(x, y, c)
    S.finish(cv)
    im, night, info = I._result(cv, "prop", (S.ox, S.base), fp(-L - 3.5, L + 3.5, D + 0.5))
    info["eyes"] = [cx - S.ox, gy - 5 - S.base]
    info["eyes_frames"] = EYE_FRAMES
    info["eyes_fps"] = 5
    return im, night, info, {"eyes": eyes_sheet()}


# ================================================================ walls

def wall_door(spec):
    """A back-wall segment with a doorway: a plain timber frame round the opening; the room
    beyond shows through it, and the opening is walkable (passage)."""
    ox0, ox1, oz1 = -8, 8, 28
    S = _wall_scene(spec, (ox0, ox1, 0, oz1))
    fw = M.wood(DARKWOOD, bias=0.15)
    S.add(box(ox0 - 1.5, ox0, -0.5, WALL_T + 0.5, 0, oz1 + 1.5, fw))
    S.add(box(ox1, ox1 + 1.5, -0.5, WALL_T + 0.5, 0, oz1 + 1.5, fw))
    S.add(box(ox0 - 1.5, ox1 + 1.5, -0.5, WALL_T + 0.5, oz1, oz1 + 2, fw))
    cv = S.render()
    return done(S, cv, "wall", fp(-SEG / 2 + 1, SEG / 2 - 1, WALL_T), passage=[ox0, ox1])


def wall_portrait(spec):
    """A back-wall segment with grandmother's portrait: an oval frame of gilt wood, her grey
    hair in a bun, a lace collar, a sprig of dried lavender tucked in the frame."""
    S = _wall_scene(spec)
    cv = S.render()
    cv.on_wall(0)
    cx, cy = S.sx(0), S.sy(0, 26)
    for y in range(cy - 8, cy + 9):
        for x in range(cx - 6, cx + 7):
            d = ((x - cx) / 6.2) ** 2 + ((y - cy) / 8.2) ** 2
            if d > 1.0:
                continue
            if d > 0.62:
                c = BRASSR[4] if (x - cx) + (y - cy) < 0 else BRASSR[2]
                if d > 0.86:
                    c = BRASSR[1]
            else:
                c = "#c9c2ae" if y < cy else "#b9b29e"  # the painted background
            cv.set(x, y, c)
    face = ["....hhh....", "...hhhhh...", "..hhsssh...", "..hssssh...", "...ssss....", "....ss.....",
            "..wwllww...", ".dddwwddd..", "ddddddddd.."]
    pal = {"h": "#a8a4a0", "s": "#e2c2a8", "w": "#f4f0e6", "l": "#d8d2c4", "d": "#5d5368"}
    for j, row in enumerate(face):
        for i, ch in enumerate(row):
            if ch in pal:
                cv.set(cx - 5 + i, cy - 5 + j, pal[ch])
    cv.set(cx - 4, cy - 6, "#a8a4a0")  # the bun
    cv.set(cx - 5, cy - 6, "#8e8a86")
    for k in range(4):  # lavender tucked into the frame
        cv.set(cx + 5 + (k % 2), cy - 7 + k, "#7d6a9e" if k < 3 else "#6f8a5e")
    return I._wall_done(S, cv)


# ================================================================ sitting room

def _sofa(S, x0, x1, ramp, y=0, seats=3):
    """Solids of an upholstered sofa (or armchair, seats=1) from x0 to x1 facing the room: turned
    feet, a base, a seat cushion per place, back cushions, rolled arms."""
    fab = _fabric(ramp, 0.06)
    for x in (x0 + 1, x1 - 3):
        for yy in (y + 1, y + 10):
            S.add(box(x, x + 2, yy, yy + 2, 0, 3, M.wood(DARKWOOD, bias=0.1)))
    S.add(box(x0, x1, y, y + 14, 3, 8, fab))  # base
    S.add(box(x0 + 1, x1 - 1, y + 10, y + 14, 8, 18, _fabric(ramp, 0.0, 5)))  # back frame
    w = (x1 - x0 - 8) / seats
    for k in range(seats):
        a = x0 + 4 + k * w
        S.add(box(a + 0.3, a + w - 0.3, y + 0.5, y + 10.5, 8, 10.5, _fabric(ramp, 0.2, 3 + k)))  # seat cushion
        S.add(box(a + 0.5, a + w - 0.5, y + 8.5, y + 11, 10.5, 18.5, _fabric(ramp, 0.12, 7 + k)))  # back cushion
    for xa in (x0, x1 - 4):
        S.add(box(xa, xa + 4, y, y + 14, 8, 13, fab))  # arms
        S.add(prism_x(xa, xa + 4, y + 7, 13, 7, _fabric(ramp, 0.14, 11), sides=10, upper=True))


def sofa(spec):
    """A three-seat sofa in soft sage with turned feet, rolled arms, plump cushions and two
    throw pillows; neat, as if nobody sits on it much."""
    S = Scene(pad_top=3)
    _sofa(S, -24, 24, SAGE)
    for x, r in ((-18, ROSE), (12, _r7(CLOTH["ochre"]))):  # throw pillows against the back
        S.add(box(x, x + 6, 6.5, 8.5, 10.5, 16, _fabric(r, 0.15, 9)))
    cv = S.render()
    return done(S, cv, "prop", fp(-24, 24, 15))


def armchair(spec):
    """A deep armchair to match the sofa, a crocheted blanket folded over one arm."""
    S = Scene(pad_top=3)
    _sofa(S, -12, 12, ROSE if spec.get("cloth") == "rose" else SAGE, seats=1)
    S.add(box(8, 12.5, 1.5, 12.5, 13, 14.2, _quilt_mat("patch", 4)))  # a blanket over the arm
    cv = S.render()
    return done(S, cv, "prop", fp(-12, 12, 15))


def coffee_table(spec):
    """A low oak table with a lace doily, a vase of dried flowers and a closed book."""
    S = Scene(pad_top=8)
    tw = M.wood(WOOD, bias=0.1)
    for x in (-14, 12):
        for y in (1, 9):
            S.add(box(x, x + 2, y, y + 2, 0, 7, tw))
    S.add(box(-15, 15, 0, 12, 7, 9, M.planks(WOOD, h=4, seed=8)))
    S.add(box(-6, 6, 2, 10, 9, 9.3, M.flat(LINEN, 0.15)))  # doily
    S.add(prism(0, 6, 2.2, 9.3, 15, M.flat(_r7(CLOTH["blue"]), 0.1), sides=12))  # vase
    S.add(box(-13, -6, 3, 9, 9, 10.5, M.flat(_r7(CLOTH["red"]), 0.05)))  # a book
    cv = S.render()
    cv.at_depth(6)
    tx, ty = S.sx(0), S.sy(6, 15)
    for k, (dx, h, c) in enumerate(((-2, 5, "#c9b07e"), (0, 7, "#b48a82"), (1, 6, "#a7b48e"), (2, 4, "#d6c39a"))):
        for j in range(h):
            cv.set(tx + dx + (j // 4) * (1 if dx > 0 else -1 if dx < 0 else 0), ty - j, "#8a7a5a")
        cv.set(tx + dx + (h // 4) * (1 if dx > 0 else -1 if dx < 0 else 0), ty - h, c)
    return done(S, cv, "prop", fp(-15, 15, 12))


def fireplace_cold(spec):
    """The fireplace with no fire lit: ash and a couple of logs on the firedogs."""
    im, night, info, _extra = I.fireplace(spec)
    for k in [k for k in info if k.startswith("fire")]:
        info.pop(k)
    px = night.load()
    for y in range(night.height // 2, night.height):  # no firelight in the hearth, only the mantel candles
        for x in range(night.width):
            px[x, y] = (0, 0, 0, 0)
    return im, night, info


# ================================================================ the hero's room

def desk(spec):
    """The hero's writing desk under the window: drawers down one side, a lamp (lit at night),
    a neat stack of books, papers squared up, an ink pot and quill, a little cactus; a chair
    pushed in with its back to the room."""
    rnd = random.Random(spec.get("seed", 3))
    S = Scene(pad_top=10)
    tw = M.wood(WOOD, bias=0.1)
    S.add(box(-16, -4, 1, 13, 0, 13, M.wood(WOOD, bias=0.12)))  # drawer pedestal
    for x in (12, 14):
        S.add(box(x, x + 2, 1, 13, 0, 13, tw))
    S.add(box(-17, 17, 0, 14, 13, 15, M.planks(WOOD, h=4, seed=9)))  # top
    # the chair, back to the room
    cw = M.wood(WOOD, bias=0.15)
    for lx in (2, 9.5):
        for ly in (-6, 1):
            S.add(box(lx, lx + 1.5, ly, ly + 1.5, 0, 8, cw))
    S.add(box(1.5, 11.5, -6.5, 2.5, 8, 9.5, M.planks(WOOD, h=3, seed=2, bias=0.15)))
    for lx in (2, 9.5):
        S.add(box(lx, lx + 1.5, -6.5, -5, 9.5, 21, cw))
    S.add(box(1.5, 11.5, -7, -5, 18.5, 21.5, cw))
    S.add(box(2, 11, -6.5, -5, 12.5, 14, cw))
    # books, a lamp
    S.add(box(-15, -8, 6, 12, 15, 17, M.flat(_r7(CLOTH["blue"]), 0.05)))
    S.add(box(-14.5, -8.5, 6.5, 11.5, 17, 18.5, M.flat(_r7(CLOTH["teal"]), 0.05)))
    S.add(box(-15, -9, 6, 12, 18.5, 20, M.flat(ROSE, 0.05)))
    S.add(prism(13, 9, 2.5, 15, 16, M.flat(IRON + ["#6b6974", "#83818c"], 0.1), sides=10))  # lamp foot
    S.add(box(12.6, 13.4, 8.6, 9.4, 16, 23, M.flat(["#5e3f0e", "#5e3f0e", "#8f6418", "#bb8a2c", "#ddb04a"])))
    shade = S.add(prism(13, 9, 3.5, 22, 26, M.flat(_r7(CLOTH["ochre"]), 0.2), sides=12))
    cv = S.render()
    cv.on_wall(1)
    for y0 in (S.sy(1, 12), S.sy(1, 8), S.sy(1, 4)):
        _panel(cv, S.sx(-15.5), S.sx(-4.5), y0, y0 + 4, WOOD)
        cv.set(S.sx(-10), y0 + 2, BRASS)
    cv.at_depth(4)
    b = S.sy(4, 15)
    for i in range(9):  # papers squared up
        cv.set(S.sx(-4) + i, b - 1, "#f4f0e6")
        cv.set(S.sx(-4) + i, b - 2, "#ece6d8" if i % 3 else "#d8d0c0")
    for i in range(3):  # quill
        cv.set(S.sx(5) + i, b - 2 - i, "#f6f2ea")
    cv.set(S.sx(4), b - 1, "#2a2230")  # ink pot
    cv.set(S.sx(4), b - 2, "#3d3346")
    cv.set(S.sx(9), b - 1, "#b85e3a")  # cactus in a pot
    cv.set(S.sx(9), b - 2, "#5d7262")
    cv.set(S.sx(9), b - 3, "#7b917e")
    cv.free()
    si = S.solids.index(shade)
    for y in range(cv.h):
        for x in range(cv.w):
            if S.sid[y, x] == si:
                cv.lit(x, y, LIT[3] if y < S.sy(9, 24.5) else LIT[2])
    return done(S, cv, "prop", fp(-17, 17, 14, back=-7))


# ================================================================ grandmother's room

def boxes_packed(spec):
    """Grandmother's things, packed: cardboard boxes and a wooden crate tied with twine, a
    folded quilt and a hatbox on top, a label on each."""
    S = Scene(pad_top=4)
    card = M.flat(CARD, 0.12)
    b1 = S.add(box(-15, -2, 1, 13, 0, 11, card))
    b2 = S.add(box(-1, 13, 2, 13, 0, 9, M.crate(WOOD)))
    b3 = S.add(box(-13, -3, 2, 11, 11, 19, M.flat(CARD, 0.18)))
    S.add(box(0, 12, 3, 12, 9, 12, _quilt_mat("patch", 5)))
    S.add(prism(7, 8, 3.4, 12, 16, M.flat(ROSE, 0.15), sides=12))  # hatbox
    S.add(prism(7, 8, 3.7, 16, 17, M.flat(ROSE, 0.25), sides=12))
    cv = S.render()
    for sol, (x0, x1, y, z0, z1) in ((b1, (-15, -2, 1, 0, 11)), (b3, (-13, -3, 2, 11, 19))):
        cv.on_wall(y, tol=1.0)
        xm = S.sx((x0 + x1) / 2)
        for yy in range(S.sy(y, z1), S.sy(y, z0)):  # twine round it
            cv.set(xm, yy, "#d8c8a0")
        for x in range(S.sx(x0), S.sx(x1)):
            cv.set(x, S.sy(y, (z0 + z1) / 2), "#d8c8a0")
        lx, ly = S.sx(x0) + 2, S.sy(y, z1) + 2  # a paper label
        for dx in range(4):
            for dy in range(3):
                cv.set(lx + dx, ly + dy, "#f4f0e6" if dy != 1 or dx == 0 else "#8a8478")
    cv.free()
    return done(S, cv, "prop", fp(-15, 13, 13))


def covered_chair(spec):
    """Grandmother's armchair under a dust sheet: its rolled arms and high back show through the
    folds, the hem pooling on the floor."""
    S = Scene(pad_top=3)
    sh = _sheet_mat(1)
    S.add(box(-12, 12, 0, 14, 0, 9, sh))
    S.add(box(-12, 12, 10, 15, 9, 24, _sheet_mat(2)))
    for xa in (-12, 8):
        S.add(box(xa, xa + 4, 0, 15, 9, 14, sh))
        S.add(prism_x(xa, xa + 4, 7.5, 14, 7.5, _sheet_mat(3), sides=10, upper=True))
    S.add(prism_x(-12, 12, 12.5, 24, 2.5, _sheet_mat(4), sides=10, upper=True))
    cv = S.render()
    return done(S, cv, "prop", fp(-12, 12, 15))


def covered_cabinet(spec):
    """A tall cabinet under a dust sheet, a corner of dark wood and one brass handle peeping out."""
    S = Scene(pad_top=3)
    S.add(box(-11, 11, 1, 12, 0, 3, M.wood(DARKWOOD, bias=0.1)))
    S.add(box(-12, 12, 0, 13, 3, 36, _sheet_mat(5)))
    S.add(prism_x(-12, 12, 6.5, 36, 6.5, _sheet_mat(6), sides=8, upper=True))
    cv = S.render()
    cv.on_wall(0)
    cv.set(S.sx(8), S.sy(0, 6), BRASS)
    return done(S, cv, "prop", fp(-12, 12, 13))


def bed_bare(spec):
    """Grandmother's bed, stripped: the striped ticking of the bare mattress, the bedding folded
    in a neat pile at the foot, the pillows stacked on it."""
    hw, L = 12, 34
    frame = DARKWOOD
    fw = M.wood(frame, bias=0.12)
    S = Scene(pad_top=3)
    for x in (-hw, hw - 2):
        S.add(box(x, x + 2, 0, 2, 0, 3, fw))
    S.add(box(-hw, hw, 0, L - 3, 2.5, 6, M.planks(frame, h=4, seed=3)))

    def ticking(u, v, kind, light, P, s):
        return I._t(_r7(TICKING) if False else TICKING + [TICKING[-1]] * 2, light + 0.1) if (math.floor(P[0]) % 3) else "#9aa6b6"
    S.add(box(-hw + 0.5, hw - 0.5, 1, L - 3, 6, 9, Mat(ticking)))
    S.add(box(-hw + 2, hw - 2, 2, 12, 9, 12, _quilt_mat("patch", 6)))  # folded quilt
    S.add(box(-hw + 3, hw - 3, 3, 11, 12, 13.5, M.flat(LINEN, 0.1)))  # folded sheets
    S.add(box(-hw + 3, hw - 3, 3.5, 10.5, 13.5, 16, M.flat(["#8a8478", "#b8b0a2", "#ddd6c8", "#eeeae0", "#f8f6f0", "#ffffff"])))
    S.add(box(-hw, hw, L - 3, L, 0, 19, M.planks(frame, h=5, seed=5)))  # headboard
    for x in (-hw - 1, hw - 2):
        S.add(box(x, x + 3, L - 3.5, L + 0.5, 0, 22, fw))
        S.add(prism(x + 1.5, L - 1.5, 1.7, 22, 24.5, fw, sides=8))
    cv = S.render()
    return done(S, cv, "prop", fp(-hw - 1, hw + 1, L + 0.5))


# ================================================================ kitchen and door

def table_small(spec):
    """A little square kitchen table for two: a chair each side, a teapot and two cups."""
    S = Scene(pad_top=4)
    tw = M.wood(WOOD, bias=0.1)
    for x in (-9, 7):
        for y in (1, 9):
            S.add(box(x, x + 2, y, y + 2, 0, 10, tw))
    S.add(box(-10, 10, 0, 12, 10, 12, M.planks(WOOD, h=4, seed=11)))
    _chair(S, -15, 2, "left")
    _chair(S, 15, 2, "right")
    cv = S.render()
    cv.at_depth(6)
    b = S.sy(6, 12)
    jug(cv, S.sx(-2), b, ("#5a6c82", "#7a8ea4", "#c6d2dd"))
    for cx in (S.sx(3), S.sx(6)):
        cv.set(cx, b - 1, "#e4dfd3")
        cv.set(cx + 1, b - 1, "#cfc9bc")
        cv.set(cx, b - 2, "#f2eee5")
    return done(S, cv, "prop", fp(-19, 19, 12))


def doormat(spec):
    """A coir doormat inside the front door: bristly, with a darker border."""
    S = Scene(pad=2, pad_top=2, pad_bottom=2, outline="#5a4436")

    def coir(u, v, kind, light, P, s):
        x0, x1, y0, y1 = s.bbox[:4]
        if min(P[0] - x0, x1 - P[0], P[1] - y0, y1 - P[1]) < 1.6:
            return "#7d6246"
        return "#b49a77" if hsh(math.floor(P[0]), math.floor(P[1] * 1.2), 3) < 0.5 else "#c8b08e"
    S.add(box(-10, 10, 0, 9, 0, 0.6, Mat(coir)))
    cv = S.render()
    return done(S, cv, "rug", fp(-10, 10, 9), solid=False)


DESIGNS = {
    "bed_side": bed_side, "wall_door": wall_door, "wall_portrait": wall_portrait, "sofa": sofa, "armchair": armchair,
    "coffee_table": coffee_table, "fireplace_cold": fireplace_cold, "desk": desk, "boxes_packed": boxes_packed,
    "covered_chair": covered_chair, "covered_cabinet": covered_cabinet, "bed_bare": bed_bare, "table_small": table_small,
    "doormat": doormat,
}
ENTRIES = [
    {"id": "bed_side", "name": "横放双人床", "group": GROUP, "type": "bed_side", "seed": 1, "quilt": "blue"},
    {"id": "wall_door", "name": "门洞墙", "group": GROUP, "type": "wall_door", "seed": 1, "paper": "linen"},
    {"id": "wall_portrait", "name": "肖像墙", "group": GROUP, "type": "wall_portrait", "seed": 1, "paper": "linen"},
    {"id": "sofa", "name": "沙发", "group": GROUP, "type": "sofa", "seed": 1},
    {"id": "armchair", "name": "扶手椅", "group": GROUP, "type": "armchair", "seed": 1},
    {"id": "coffee_table", "name": "茶几", "group": GROUP, "type": "coffee_table", "seed": 1},
    {"id": "fireplace_cold", "name": "壁炉（未生火）", "group": GROUP, "type": "fireplace_cold", "seed": 1},
    {"id": "desk", "name": "书桌", "group": GROUP, "type": "desk", "seed": 3},
    {"id": "boxes_packed", "name": "打包的箱子", "group": GROUP, "type": "boxes_packed", "seed": 1},
    {"id": "covered_chair", "name": "盖布的扶手椅", "group": GROUP, "type": "covered_chair", "seed": 1},
    {"id": "covered_cabinet", "name": "盖布的柜子", "group": GROUP, "type": "covered_cabinet", "seed": 1},
    {"id": "bed_bare", "name": "空床", "group": GROUP, "type": "bed_bare", "seed": 1},
    {"id": "table_small", "name": "小餐桌", "group": GROUP, "type": "table_small", "seed": 1},
    {"id": "doormat", "name": "门垫", "group": GROUP, "type": "doormat", "seed": 1},
]
