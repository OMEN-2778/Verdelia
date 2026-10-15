"""Shrinking Universal LPC characters to the world's scale, layer by layer.

An LPC frame is 64 x 64 px with a figure about 52 px tall; ours are about 33 px. Scaling the whole
picture down smears the outline and the shading into mud, so each layer (body, trousers, shirt,
hair...) is shrunk on its own: its colours form a little ramp sorted by brightness (the darkest is
its outline), each target pixel takes the commonest tone in the box of source pixels it covers
(the outline only where it fills most of the box), lone specks are smoothed away, the layers are
stacked in their z order and a fresh outline is drawn round the whole figure, each rim pixel in
the darkest tone of the layer it belongs to.

The eyes come out of the head layer before shrinking (at this size they would turn into blobs) and
small hand-drawn ones go back in afterwards, where the eyes were in that frame, in the mood asked
for (see FACES).
"""
from collections import Counter

from PIL import Image

DARK = (43, 30, 38)  # eye and mouth lines
WHITE = (246, 241, 232)
MOUTH = (142, 59, 59)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def ramp_of(img):
    """The layer's colours, darkest first."""
    cols = Counter(c[:3] for c in img.getdata() if c[3] > 128)
    return sorted(cols, key=lum)


class Frame:
    """Where an LPC frame lands in ours: `size` px source frames (64, or 128 for the oversized tool
    animations) with the figure's feet at (cx, base); ours are ow x oh px with the feet at the
    bottom middle, scaled by sx, sy."""

    def __init__(self, size, ow, oh, sx, sy):
        self.size, self.ow, self.oh, self.sx, self.sy = size, ow, oh, sx, sy
        pad = (size - 64) // 2
        self.cx, self.base = 32 + pad, 61 + pad

    def box(self, tx, ty):
        x0 = self.cx + (tx - self.ow / 2) / self.sx
        x1 = self.cx + (tx + 1 - self.ow / 2) / self.sx
        y0 = self.base + 1 + (ty - self.oh) / self.sy
        y1 = self.base + 1 + (ty + 1 - self.oh) / self.sy
        return x0, y0, x1, y1

    def target(self, x, y):
        """Our pixel for the source point (x, y) (pixel centres)."""
        return (int(self.ow / 2 + (x + 0.5 - self.cx) * self.sx),
                int(self.oh - (self.base + 1 - (y + 0.5)) * self.sy))


def shrink_layer(src, ramp, fr, keep_outline=0.6, cov_min=0.45):
    """{(x, y): tone} for one layer's frame; tone indexes `ramp`."""
    px = src.load()
    tone = {c: i for i, c in enumerate(ramp)}
    n = src.width
    out = {}
    for ty in range(fr.oh):
        for tx in range(fr.ow):
            x0, y0, x1, y1 = fr.box(tx, ty)
            tally = Counter()
            cov = 0.0
            for y in range(int(y0), int(y1 + 0.999)):
                for x in range(int(x0), int(x1 + 0.999)):
                    if 0 <= x < n and 0 <= y < n and px[x, y][3] > 128:
                        w = (min(x + 1, x1) - max(x, x0)) * (min(y + 1, y1) - max(y, y0))
                        if w > 0:
                            cov += w
                            tally[tone[px[x, y][:3]]] += w
            if cov < cov_min * (x1 - x0) * (y1 - y0):
                continue
            if tally[0] >= keep_outline * cov:
                out[(tx, ty)] = 0
            else:
                tally.pop(0, None)
                out[(tx, ty)] = tally.most_common(1)[0][0] if tally else 0
    # a lone pixel unlike its four neighbours, which agree, takes theirs
    for (x, y), t in list(out.items()):
        nb = [out.get((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if None not in nb and len(set(nb)) == 1 and nb[0] != t and t != 0:
            out[(x, y)] = nb[0]
    return out


def strip_eyes(src, skin):
    """Paints the eyes out of a head frame: whatever is not skin is an eye, and the box round each
    eye (its dark lids are the skin's outline colour) takes the skin's middle tone. Returns the
    cleaned frame and the eyes, each a list of source pixels, left to right."""
    skin_set = set(skin)
    mid = skin[len(skin) // 2]
    px = src.load()
    found = []
    for y in range(src.height):
        for x in range(src.width):
            c = px[x, y]
            if c[3] > 128 and c[:3] not in skin_set:
                found.append((x, y))
    eyes = []
    for x, y in sorted(found):
        if eyes and x - eyes[-1][-1][0] <= 2:
            eyes[-1].append((x, y))
        else:
            eyes.append([(x, y)])
    eyes = [e for e in eyes if len(e) >= 2]
    out = src.copy()
    o = out.load()
    for e in eyes:
        x0, x1 = min(x for x, _ in e), max(x for x, _ in e)
        y0, y1 = min(y for _, y in e), max(y for _, y in e)
        for y in range(y0 - 1, y1 + 2):
            for x in range(x0, x1 + 1):
                if px[x, y][3] > 128:
                    o[x, y] = mid + (255,)
    return out, eyes


# The faces. Each eye is drawn from a little pattern, rows from its top: "D" dark (lids, lashes),
# "W" the white, "e" the iris, "." left alone. Patterns are for the eye on the left of the face
# (its inner side, towards the nose, on the right), with the column that sits on the eye's spot
# marked by `at`; the right eye gets them mirrored. Seen from the side the one eye is drawn as a
# left eye looking right (mirrored when he faces left), so the iris is at the front.
# "brow": the two pixels of each brow, outer and inner end, in rows above the eye's top;
# "mouth": on the row two below the eye's top, centred between the eyes ("M" the inside of the
# mouth). Nothing is drawn where hair or a hat covers the face.
FACES = {
    "neutral": {"eye": ["DD", "We"], "at": 1, "brow": (2, 2), "mouth": ""},
    "blink": {"eye": ["..", "DD"], "at": 1, "brow": (2, 2), "mouth": ""},
    "happy": {"eye": [".D.", "D.D"], "at": 1, "brow": (3, 3), "mouth": "MM"},
    "smug": {"eye": ["DD", "De"], "at": 1, "brow": (2, 2), "brow_r": (3, 3), "mouth": ".DD"},
    "shock": {"eye": ["DD", "WD"], "at": 1, "brow": (3, 3), "mouth": "M"},
    "angry": {"eye": ["DD", ".e"], "at": 1, "brow": (2, 1), "mouth": "DD"},
    "sad": {"eye": ["DD", "We"], "at": 1, "brow": (1, 2), "mouth": "D"},
}
COLOURS = {"D": DARK, "W": (240, 240, 236), "M": MOUTH}


def draw_face(img, face_px, eyes, fr, face, iris, brow, facing=0):
    """eyes: the eye clusters from strip_eyes (source pixels); face_px: the pixels where the face
    shows (not under hair); brow: the eyebrows' colour; facing: 0 towards us, 1 right, -1 left."""
    spec = FACES[face]
    spots = []
    for cl in eyes:
        mx = sum(x for x, _ in cl) / len(cl)
        my = min(y for _, y in cl)
        spots.append(fr.target(mx, my))
    if not spots:
        return
    spots.sort()
    if facing == 0 and len(spots) != 2:
        return

    def put(x, y, c):
        if (x, y) in face_px and c is not None:
            img.putpixel((x, y), c + (255,))

    pat, at = spec["eye"], spec["at"]
    w = len(pat[0])
    for i, (tx, ty) in enumerate(spots):
        mirror = (i == 1) if facing == 0 else facing < 0
        for dy, row in enumerate(pat):
            for col, ch in enumerate(row):
                if ch == ".":
                    continue
                dx = col - at
                put(tx - dx if mirror else tx + dx, ty + dy, iris if ch == "e" else COLOURS[ch])
        if brow is not None:
            outer, inner = spec.get("brow_r", spec["brow"]) if (facing == 0 and i == 1) else spec["brow"]
            out = 1 if mirror else -1  # the outer side of this eye
            put(tx, ty - inner, brow)
            put(tx + out, ty - outer, brow)
    if facing == 0 and spec["mouth"]:
        mid = (spots[0][0] + spots[1][0]) / 2
        m = spec["mouth"]
        x0 = int(mid + 0.5 - len(m) / 2)
        for k, ch in enumerate(m):
            if ch != ".":
                put(x0 + k, spots[0][1] + 2, COLOURS[ch])


def brow_colour(ramp):
    """The eyebrows' tone: of their colours, the one nearest a middling dark, so they stand
    apart from the dark of the eyes."""
    return min(ramp, key=lambda c: abs(lum(c) - 80))


def compose(layers, fr, skin, iris=None, face="neutral", facing=0):
    """layers: [(z, item, frame image)] for one frame. Returns the small frame and which item
    each of its pixels shows."""
    img = Image.new("RGBA", (fr.ow, fr.oh), (0, 0, 0, 0))
    p = img.load()
    owner = {}
    eyes = []
    brow = None
    for z, item, src in sorted(layers, key=lambda t: t[0]):
        if not src.getbbox():
            continue
        if item.startswith("human_"):  # the head: its eyes come out, ours go in at the end
            src, eyes = strip_eyes(src, skin)
        ramp = ramp_of(src)
        if "eyebrows" in item:  # drawn by hand with the eyes, in the mood's shape
            brow = brow_colour(ramp)
            continue
        for xy, t in shrink_layer(src, ramp, fr).items():
            p[xy] = ramp[t] + (255,)
            owner[xy] = (item, ramp)
    out = img.copy()
    o = out.load()
    for (x, y), (item, ramp) in owner.items():
        if any(not (0 <= x + dx < fr.ow and 0 <= y + dy < fr.oh) or p[x + dx, y + dy][3] == 0
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            o[x, y] = ramp[0] + (255,)
    items = {xy: it for xy, (it, _) in owner.items()}
    if eyes and iris:
        face_px = {xy for xy, it in items.items() if it.startswith("human_") and o[xy][:3] != owner[xy][1][0]}
        draw_face(out, face_px, eyes, fr, face, iris, brow, facing)
    return out, items
