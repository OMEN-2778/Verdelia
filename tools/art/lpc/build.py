#!/usr/bin/env python3
"""Builds our small characters from Universal LPC exports (see export.mjs): for each character in
characters.json, every animation in four directions (LPC draws left and right separately, so
nothing is mirrored), shrunk layer by layer to about 33 px tall (see shrink.py) with hand-drawn
eyes, plus a few front-facing moods.

The bodies are LPC's "teen" body with the small male head: slim, with grown-up proportions, at
nearly the same scale across and down (0.60 x 0.63), so nothing is squashed.

Writes art/characters/<id>/sheet.png, frames.json and CREDITS.csv (the authors and licences of
every LPC part used, as the generator lists them), and the preview docs/art/characters.png.

frames.json: {"animations": {"walk_down": {"y": 40, "size": [32, 40], "anchor": [16, 39],
"frames": [[cell, seconds], ...], "loop": true}, ...}}; cell i of an animation is the frame at
x = i * width on the row at y; the anchor (the point between the feet) is where the character
stands.

    python3 tools/art/lpc/build.py [ids...]
"""
import csv
import glob
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shrink  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = HERE / ".cache"
SX, SY = 0.60, 0.63
SMALL = (32, 40)  # walking about
WIDE = (56, 40)  # swinging a tool
DIRS = ["up", "left", "down", "right"]  # LPC's rows, top to bottom
TOOLS = {"hammer", "handle", "watering_can", "hoe", "axe", "pickaxe", "shovel", "fishing_rod"}
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# name: (folder in the export, source frame px, our frame size, [(column, seconds, face)], loop,
#        tool layers to keep, directions). "work" and "water" are made only for the characters
#        whose "extras" ask for them.
ANIMS = {
    "idle": ("standard/idle", 64, SMALL,
             [(0, 1.0, None), (1, 0.5, None), (0, 1.4, None), (0, 0.12, "blink")], True, (), DIRS),
    "walk": ("standard/walk", 64, SMALL, [(c, 0.1, None) for c in range(1, 9)], True, (), DIRS),
    "run": ("standard/run", 64, SMALL, [(c, 0.075, None) for c in range(8)], True, (), DIRS),
    # LPC's own tool swings (tool_hammer, tool_axe) are drawn for the adult body and miss the teen
    # body's hands, so the hammer is our own, put in his hand (see hammer()): the slash's arm
    # raised, level, down
    "work": ("standard/slash", 64, WIDE,
             [(5, 0.32, None), (4, 0.06, None), (3, 0.38, "blink")], True, (), ["left", "right"]),
    # watering: LPC's thrust rows with the can, as the generator's own watering animation
    "water": ("standard/thrust", 64, WIDE,
              [(0, 0.12, None), (1, 0.12, None), (4, 0.7, None), (5, 0.18, None)], True, ("watering_can",), DIRS),
}
HAMMER_POSES = {5: "up", 4: "level", 3: "down"}
FACING = {"up": 0, "left": -1, "down": 0, "right": 1}
MOODS = ["happy", "smug", "shock", "angry", "sad"]  # front-facing, one frame each: mood_<name>


def item_of(path):
    """'035 longsleeve_2__white_.png' -> (35, 'longsleeve_2')"""
    z, rest = os.path.basename(path).split(" ", 1)
    return int(z), rest.split("__")[0]


def recolour_like(raw, raw_ref, done_ref):
    """Recolours `raw` (an uncoloured LPC sheet) the way `raw_ref` became `done_ref`."""
    m = {}
    a, b = raw_ref.load(), done_ref.load()
    for y in range(min(raw_ref.height, done_ref.height)):
        for x in range(raw_ref.width):
            if a[x, y][3] > 128 and b[x, y][3] > 128:
                m.setdefault(a[x, y][:3], b[x, y][:3])
    out = raw.copy()
    o = out.load()
    for y in range(out.height):
        for x in range(out.width):
            c = o[x, y]
            if c[3] > 128 and c[:3] in m:
                o[x, y] = m[c[:3]] + (c[3],)
    return out


def layers_for(export, anim, lpc):
    folder, size, _, _, _, keep, _ = ANIMS[anim]
    out = []
    for f in sorted(glob.glob(str(export / folder / "*.png"))):
        z, item = item_of(f)
        if item == "eye_color":
            continue
        if item in TOOLS and item not in keep:
            continue
        out.append((z, item, Image.open(f).convert("RGBA")))
    if anim == "water":  # the generator leaves the can out of its thrust sheets: colour LPC's own
        for f in glob.glob(str(export / "standard/walk/* watering_can__*.png")):
            z, item = item_of(f)
            part = "bg" if z < 100 else "fg"
            raw = lpc / "spritesheets/tools/watering_can" / part
            sheet = recolour_like(Image.open(raw / "thrust.png").convert("RGBA"),
                                  Image.open(raw / "walk.png").convert("RGBA"), Image.open(f).convert("RGBA"))
            out.append((z, item, sheet))
    return out


def has_anim(export, anim, spec):
    folder, _, _, _, _, keep, _ = ANIMS[anim]
    if anim in ("work", "water") and anim not in spec.get("extras", []):
        return False
    files = glob.glob(str(export / folder / "*.png"))
    if not files:
        return False
    if not keep:
        return True
    if anim == "water":
        return bool(glob.glob(str(export / "standard/walk/* watering_can__*.png")))
    return any(item_of(f)[1] == keep[0] for f in files)


def build(cid, spec, lpc):
    export = CACHE / "export" / cid / "x"
    iris = tuple(int(spec["iris"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    body = glob.glob(str(export / "standard/walk/* body_color__*.png"))[0]
    skin = shrink.ramp_of(Image.open(body).convert("RGBA"))
    rows = []  # (name, size, cells, frames, loop)
    for anim in ANIMS:
        if not has_anim(export, anim, spec):
            continue
        folder, size, osize, seq, loop, _, dirs = ANIMS[anim]
        layers = layers_for(export, anim, lpc)
        fr = shrink.Frame(size, osize[0], osize[1], SX, SY)
        for r, d in enumerate(DIRS):
            if d not in dirs:
                continue
            cells, frames, made = [], [], {}
            for col, secs, face in seq:
                key = (col, face)
                if key not in made:
                    crop = [(z, it, s.crop((col * size, r * size, (col + 1) * size, (r + 1) * size))) for z, it, s in layers]
                    made[key] = len(cells)
                    cell, items = shrink.compose(crop, fr, skin, iris, face or "neutral", FACING[d])
                    if anim == "work":
                        hammer(cell, items, 1 if d == "right" else -1, HAMMER_POSES[col])
                    cells.append(cell)
                frames.append([made[key], secs])
            rows.append((f"{anim}_{d}", osize, cells, frames, loop))
        if anim == "idle":  # the moods, facing us
            layers_d = [(z, it, s.crop((0, 2 * size, size, 3 * size))) for z, it, s in layers]
            for mood in MOODS:
                rows.append((f"mood_{mood}", osize, [shrink.compose(layers_d, fr, skin, iris, mood)[0]], [[0, 1.0]], True))
    width = max(sz[0] * len(cells) for _, sz, cells, _, _ in rows)
    height = sum(sz[1] for _, sz, _, _, _ in rows)
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    anims = {}
    y = 0
    for name, sz, cells, frames, loop in rows:
        for i, c in enumerate(cells):
            sheet.alpha_composite(c, (i * sz[0], y))
        anims[name] = {"y": y, "size": list(sz), "anchor": [sz[0] // 2, sz[1] - 1], "frames": frames, "loop": loop}
        y += sz[1]
    out = ROOT / "art/characters" / cid
    out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / "sheet.png")
    meta = {"name": spec["name"], "lpc": spec["hash"], "animations": anims}
    (out / "frames.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    credits(CACHE / "export" / cid / "credits.csv", out / "CREDITS.md", spec["name"])
    print(cid, sheet.size, len(anims), "animations")
    return sheet, anims


# The hammer in the fixer's hand, facing right (mirrored for the left), from his grip: "h" the
# handle, "S"/"s" the head lit and in shade (outlined in dark), "*" sparks where it strikes
HAMMER = {
    "up": {"h": [(0, -1), (0, -2), (0, -3), (0, -4)],
           "S": [(-1, -7), (0, -7), (1, -7), (2, -7)], "s": [(-1, -6), (0, -6), (1, -6), (2, -6)]},
    "level": {"h": [(1, -1), (2, -2), (3, -3)],
              "S": [(3, -6), (4, -6), (5, -6), (3, -5)], "s": [(4, -5), (5, -5), (4, -4), (5, -4)]},
    "down": {"h": [(1, 0), (2, 0), (3, 0), (4, 0)],
             "S": [(5, -2), (5, -1), (5, 0), (5, 1)], "s": [(6, -2), (6, -1), (6, 0), (6, 1)],
             "*": [(9, -3), (9, 2), (10, -1), (10, 1)]},
}
HAMMER_COL = {"h": (140, 92, 52), "S": (196, 202, 212), "s": (112, 118, 132), "*": (255, 226, 130)}


def hammer(img, items, facing, pose):
    """Puts the hammer in the hand that reaches furthest the way he faces."""
    hands = [xy for xy, it in items.items() if it.startswith("body_color")]
    if not hands:
        return
    tip = max(hands, key=lambda p: (p[0] * facing, p[1]))
    grip = [p for p in hands if abs(p[0] - tip[0]) <= 1 and abs(p[1] - tip[1]) <= 1]
    gx = round(sum(x for x, _ in grip) / len(grip))
    gy = round(sum(y for _, y in grip) / len(grip))
    px = {}
    for k, pts in HAMMER[pose].items():
        for dx, dy in pts:
            px[(gx + dx * facing, gy + dy)] = HAMMER_COL[k]
    head = [xy for xy, c in px.items() if c in (HAMMER_COL["S"], HAMMER_COL["s"])]
    for x, y in head:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            q = (x + dx, y + dy)
            if q not in px:
                px[q] = shrink.DARK
    for (x, y), c in px.items():
        if 0 <= x < img.width and 0 <= y < img.height:
            img.putpixel((x, y), c + (255,))


def credits(src, dst, name):
    """The generator's credits for the parts used, one row per sheet. (Markdown, not CSV: Godot
    would take a CSV for a translation table.)"""
    with open(src, newline="") as f:
        rows = list(csv.DictReader(f))
    lines = [f"# {name}: credits", "",
             "Drawn from the Universal LPC Spritesheet Character Generator "
             "(https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator), "
             "shrunk and partly redrawn (the eyes, brows and mouths; the fixer's hammer) by tools/art/lpc. "
             "The sprites here are under the same licences as the parts they come from, listed below; "
             "credit the authors when using them.", "",
             "| Sheet | Authors | Licences | Links |", "| --- | --- | --- | --- |"]
    for r in rows:
        cell = [r.get(k, "").replace("|", "/").replace("\n", " ").strip() for k in ("filename", "authors", "licenses", "urls")]
        lines.append("| " + " | ".join(cell) + " |")
    Path(dst).write_text("\n".join(lines) + "\n")


def cells(cid, anim):
    """The frames of one animation of a built character, in playing order (unique cells)."""
    meta = json.loads((ROOT / "art/characters" / cid / "frames.json").read_text())
    sheet = Image.open(ROOT / "art/characters" / cid / "sheet.png")
    a = meta["animations"][anim]
    w, h = a["size"]
    order = []
    for c, _ in a["frames"]:
        if c not in order:
            order.append(c)
    return [sheet.crop((c * w, a["y"], (c + 1) * w, a["y"] + h)) for c in order]


def previews(specs):
    """docs/art/characters.png: each character standing four ways, a walk, the moods and its
    work; docs/art/characters.gif: all of them walking round, the fixer at work."""
    k = 4
    groups = [["idle_down", "idle_left", "idle_right", "idle_up"], ["walk_right"],
              ["mood_happy", "mood_smug", "mood_shock", "mood_angry", "mood_sad"], ["work_right", "water_right"]]
    rows = []
    for cid, spec in specs.items():
        row = []
        for g in groups:
            part = []
            for anim in g:
                try:
                    part += cells(cid, anim)[:1] if anim.startswith(("idle", "mood")) else cells(cid, anim)
                except KeyError:
                    pass
            row.append(part)
        rows.append((spec["name"], row))
    width = max(sum(sum(c.width + 2 for c in part) + 10 for part in row) for _, row in rows) + 70
    img = Image.new("RGBA", (width * k, len(rows) * 44 * k + 8 * k), (126, 158, 96, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 7 * k) if os.path.exists(FONT) else None
    for i, (name, row) in enumerate(rows):
        y = 4 + i * 44
        if font:
            d.text((4 * k, (y + 16) * k), name, font=font, fill=(255, 255, 255, 255), stroke_width=k, stroke_fill=(35, 26, 36, 255))
        x = 66
        for part in row:
            for c in part:
                img.alpha_composite(c.resize((c.width * k, c.height * k), Image.NEAREST), (x * k, y * k))
                x += c.width + 2
            x += 10
    img.convert("RGB").save(ROOT / "docs/art/characters.png")
    # the GIF: everyone walking down, right, up and left, eight frames each, the fixer hammering
    frames = []
    walkers = list(specs)
    for d_ in ["down", "right", "up", "left"]:
        for f in range(8):
            im = Image.new("RGBA", ((len(walkers) * 34 + 60) * k, 44 * k), (126, 158, 96, 255))
            for i, cid in enumerate(walkers):
                c = cells(cid, "walk_" + d_)[f]
                im.alpha_composite(c.resize((32 * k, 40 * k), Image.NEAREST), ((2 + i * 34) * k, 2 * k))
            work = cells("fixer", "work_right")
            c = work[min(2, f * 3 // 8)]
            im.alpha_composite(c.resize((c.width * k, c.height * k), Image.NEAREST), ((len(walkers) * 34) * k, 2 * k))
            frames.append(im.convert("RGB"))
    frames[0].save(ROOT / "docs/art/characters.gif", save_all=True, append_images=frames[1:], duration=100, loop=0)


def main():
    specs = json.loads((HERE / "characters.json").read_text())
    ids = sys.argv[1:] or list(specs)
    lpc = CACHE / "ulpc"
    for cid in ids:
        build(cid, specs[cid], lpc)
    previews(specs)


if __name__ == "__main__":
    main()
