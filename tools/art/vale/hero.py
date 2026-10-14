#!/usr/bin/env python3
"""Candidates for the hero (a young man), drawn pixel by pixel from the text grids below: each
letter is one pixel in a colour from the candidate's palette ("." is transparent). Light comes
from the top left like everywhere else, with a dark warm outline round the whole figure.

A figure is 20 x 31 px (about 16 wide and 30 tall inside), half as big again as the old mage, to
match the rooms and buildings (a door is 16 px wide, a wall 40 px tall). The grids are split into
a head (rows 0-14) and a body (rows 15-30), so heads and outfits can be mixed; each comes in a
front and a back view.

Writes docs/art/hero-candidates.png (all candidates, front and back, at 1x and 4x) and
art/hero/candidates/<id>.png (front and back side by side).

    python3 tools/art/vale/hero.py
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
W, H = 20, 31

# ------------------------------------------------------------------ heads (rows 0-14)
# shared lower face for the open-faced styles (rows 9-14; col 3 and 16 are side hair)
FACE = [
    "..ohSSSSSSSSSSSsho..",
    "..ohSSwESSSSwESsho..",
    "..ohSSEESSSSEESsho..",
    "..ohSmSSSSSSSSmsho..",
    "...oSSSSSkkSSSSso...",
    "....osSSSSSSSSso....",
]
HEADS = {
    # messy brown hair, light catching the top left, short strands falling over the forehead
    "messy": {
        "front": [
            "....................",
            ".......oooooo.......",
            ".....ooHHLLHHoo.....",
            "....oHHLLHHHHHho....",
            "...oHLLHHHHHHHHho...",
            "...oHLHHHHHHHHHho...",
            "..oHHHHHHHHHHHHHho..",
            "..oHHHhHHHHhHHHhho..",
            "..oHHSHhSSHhSSHhho..",
        ] + FACE,
        "back": [
            "....................",
            ".......oooooo.......",
            ".....ooHHLLHHoo.....",
            "....oHHLLHHHHHho....",
            "...oHLLHHHHHHHHho...",
            "...oHLHHHHHHHHHho...",
            "..oHHHHHHHHHHHHHho..",
            "..oHHHhHHHHhHHHhho..",
            "..oHHHhHHHhHHHhhho..",
            "..oHHHhHHHhHHHhhho..",
            "..ohHHhHHHhHHHhhho..",
            "..ohHHhHHHhHHhhhho..",
            "..ohhHhHHhhHHhhhho..",
            "...ohhhHhhhHhhhho...",
            "....okkkkkkkkkko....",
        ],
    },
    # neat dark hair with a side parting, the fringe swept across, a tuft sticking up at the crown
    "tuft": {
        "front": [
            "..........oo........",
            ".......oooHLooo.....",
            ".....ooHHHHHHoo.....",
            "....oLLHHHHHHHho....",
            "...oLLHHHHHHHHHho...",
            "...oLHHHHHHHHHHho...",
            "..oHHHHHHHHHHHHHho..",
            "..oHHHHHHHHHHhhhho..",
            "..oHHHHHHHhhSSSSho..",
        ] + FACE,
        "back": [
            "..........oo........",
            ".......oooHLooo.....",
            ".....ooHHHHHHoo.....",
            "....oLLHHHHHHHho....",
            "...oLLHHHHHHHHHho...",
            "...oLHHHHHHHHHHho...",
            "..oHHHHHHHHHHHHHho..",
            "..oHHHHHHHHHHHHhho..",
            "..oHHHHHHHHHHHHhho..",
            "..oHHHHHHHHHHHhhho..",
            "..ohHHHHHHHHHHhhho..",
            "..ohHHHHHHHHHhhhho..",
            "..ohhHHHHHHHHhhhho..",
            "...ohhhhhhhhhhhho...",
            "....okkkkkkkkkko....",
        ],
    },
    # a straw hat with a red band over sandy hair, the brim's shade across the brow
    "straw": {
        "front": [
            "....................",
            "......oooooooo......",
            ".....oYZZYYYYyo.....",
            ".....oYZYYYYYyo.....",
            ".....oRRRRRRRro.....",
            ".ooYYYZZYYYYYYyyoo..",
            "oYYYYYYYYYYYYYYYYyyo",
            ".oyyyyyyyyyyyyyyyyo.",
            "..oHhsssssssssshho..",
        ] + FACE,
        "back": [
            "....................",
            "......oooooooo......",
            ".....oYZZYYYYyo.....",
            ".....oYZYYYYYyo.....",
            ".....oRRRRRRRro.....",
            ".ooYYYZZYYYYYYyyoo..",
            "oYYYYYYYYYYYYYYYYyyo",
            ".oyyyyyyyyyyyyyyyyo.",
            "..ohhhhhhhhhhhhhho..",
            "..oHHHhHHHhHHHhhho..",
            "..ohHHhHHHhHHHhhho..",
            "..ohHHhHHHhHHhhhho..",
            "..ohhHhHHhhHHhhhho..",
            "...ohhhHhhhHhhhho...",
            "....okkkkkkkkkko....",
        ],
    },
    # a teal hood with two little round ears (like his secret friend's), ginger fringe peeking out
    "hood": {
        "front": [
            "....oo........oo....",
            "...oDCo......oCco...",
            "...oDCooooooooCco...",
            "...oDCCDDCCCCCCco...",
            "..oDDCCCCCCCCCCcco..",
            "..oDCCCCCCCCCCCcco..",
            "..oDCQQQQQQQQQQcco..",
            "..oDQHLLHHHHHHhQco..",
            "..oDQHSHhSSHhShQco..",
            "..oDQSSSSSSSSSsQco..",
            "..oDQSwESSSSwEsQco..",
            "..oDQSEESSSSEEsQco..",
            "..oDQmSSSSSSSSmQco..",
            "..oDQSSSSkkSSSsQco..",
            "...oDQQssssssQQco...",
        ],
        "back": [
            "....oo........oo....",
            "...oDCo......oCco...",
            "...oDCooooooooCco...",
            "...oDCCDDCCCCCCco...",
            "..oDDCCCCCCCCCCcco..",
            "..oDCCCCCCcCCCCcco..",
            "..oDCCCCCCcCCCCcco..",
            "..oDCCCCCCcCCCCcco..",
            "..oDCCCCCCcCCCCcco..",
            "..oDCCCCCCcCCCccco..",
            "..oDCCCCCCcCCCccco..",
            "..oDCCCCCCcCCCccco..",
            "..ocCCCCCCcCCcccco..",
            "...occCCCCcCCccco...",
            "....occcccccccco....",
        ],
    },
}

# ------------------------------------------------------------------ bodies (rows 15-30)
LEGS = [
    "...oooPPPpPPPpooo...",
    ".....oPPPpPPPpo.....",
    ".....oPPPpPPPpo.....",
    ".....oPPPpPPPpo.....",
    ".....oPPPpPPPpo.....",
    ".....oBBBbBBBbo.....",
    "....oBBBbbBBBbbo....",
    "....oooooooooooo....",
]
BODIES = {
    # a green work shirt with a cream collar and placket, a leather belt with a brass buckle
    "shirt": {
        "front": [
            "....oAAAkkkkAAAo....",
            "..oDDCCCAAAACCCcco..",
            "..oDCcCCCAACCCcCco..",
            "..oDCcCCCAACCCcCco..",
            "..oDCcCCCAACCCcCco..",
            "..oDCcCCCAACCcccco..",
            "..oSScTTTYYTTTcSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
        "back": [
            "....oAAAAAAAAAAo....",
            "..oDDCCCCCCCCCCcco..",
            "..oDCcCCCCCCCCcCco..",
            "..oDCcCCCCCCCCcCco..",
            "..oDCcCCCCCCCcccco..",
            "..oDCcCCCCCCccccco..",
            "..oSScTTTTTTTTcSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
    },
    # a chunky knitted sweater (grandmother's), a red scarf with its end hanging down the front
    "sweater": {
        "front": [
            "....oRRRRRRRRrro....",
            "..oDDCRRRRRRRCCcco..",
            "..oDCcRRCCCCCCcCco..",
            "..oDCcRrCCDCCCcCco..",
            "..oDCcrRCCCCCCcCco..",
            "..oDCcCCDCCDCccCco..",
            "..oSScCcCcCcCccSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
        "back": [
            "....oRRRRRRRRrro....",
            "..oDDCCCCCCCCCCcco..",
            "..oDCcCDCCDCCCcCco..",
            "..oDCcCCCCCCCCcCco..",
            "..oDCcCCDCCDCccCco..",
            "..oDCcCCCCCCCccCco..",
            "..oSScCcCcCcCccSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
    },
    # a white shirt with the sleeves rolled up under blue dungarees, two brass buttons on the bib
    "overalls": {
        "front": [
            "....oCCCkkkkCCCo....",
            "..oDDCPCCCCCCPCcco..",
            "..oDCcPCCCCCCPcCco..",
            "..oSScPPPPPPPPpSso..",
            "..oSScPUPppPUPpSso..",
            "..oSscPPPppPPPpsso..",
            "..oSSpPPPPPPPPpSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
        "back": [
            "....oCCCCCCCCCCo....",
            "..oDDCPCCCCCCPCcco..",
            "..oDCcCPCCCCPCcCco..",
            "..oSScCCPPPPCCcSso..",
            "..oSScPPPPPPPPpSso..",
            "..oSscPPPPPPPPpsso..",
            "..oSSpPPPPPPPPpSso..",
            "..oSsoPPPPPPPpoSso..",
        ] + LEGS,
    },
    # a teal hoodie (the hood is up) with its drawstrings, a satchel strap across the chest
    "hoodie": {
        "front": [
            "....oCCcQCCQcCCo....",
            "..oDDGCCQCCQCCCcco..",
            "..oDCcGGCCCCCCcCco..",
            "..oDCcCCGGCCCCcCco..",
            "..oDCccccccGGccCco..",
            "..oDCcCCCCCCCGGcco..",
            "..oSScccccccccWWWo..",
            "..oSsoPPPPPPPpoWWo..",
        ] + LEGS,
        "back": [
            "....oCCCCCCCCCCo....",
            "..oDDCCCCCCCCGGcco..",
            "..oDCcCCCCCCGGcCco..",
            "..oDCcCCCCGGCCcCco..",
            "..oDCcCCGGCCCccCco..",
            "..oDCcGGCCCCCccCco..",
            "..oSWWWcccccccccSso.",
            "..oWWoPPPPPPPpoSso..",
        ] + LEGS,
    },
}

# ------------------------------------------------------------------ the candidates
SKIN = {"S": "#f2c9a0", "s": "#d9a27e", "k": "#c08566", "m": "#e8978a", "E": "#2b1e26", "w": "#ffffff",
        "o": "#2b1e26"}
CANDIDATES = [
    ("forest", "林间少年", "messy", "shirt", {
        "H": "#7a4a2c", "h": "#5a3320", "L": "#a26a3d",
        "C": "#5f8f4e", "c": "#456e3c", "D": "#7fae5f", "A": "#efe2c4",
        "T": "#5a3b2a", "Y": "#d9a93a", "P": "#6a5240", "p": "#4e3b2e", "B": "#3b2a22", "b": "#2e211b"}),
    ("sweater", "奶奶织的毛衣", "tuft", "sweater", {
        "H": "#3a3a52", "h": "#2a2a3c", "L": "#5c5c80",
        "C": "#d9a43c", "c": "#b5822a", "D": "#ecc265", "R": "#c8454a", "r": "#9c3036",
        "P": "#4a5e8a", "p": "#38476b", "B": "#6a4530", "b": "#4b3022"}),
    ("farmer", "草帽农夫", "straw", "overalls", {
        "H": "#d8b06a", "h": "#b08a4a", "L": "#ecca8a",
        "Y": "#e8cf8a", "y": "#c4a45e", "Z": "#f6e4b0", "R": "#b5443c", "r": "#8c3029",
        "C": "#f1ece0", "c": "#cfc6b3", "D": "#ffffff", "U": "#e8c060",
        "P": "#5577a8", "p": "#3f5b86", "B": "#6a4a32", "b": "#4d3424"}),
    ("hood", "兜帽少年", "hood", "hoodie", {
        "H": "#d0703a", "h": "#a8532a", "L": "#ea9a5a",
        "C": "#4f8c88", "c": "#3b6c69", "D": "#6eaba5", "Q": "#9bcfc6", "G": "#7a5236", "W": "#9a6a44",
        "P": "#5e5f6b", "p": "#46474f", "B": "#8a3b35", "b": "#652a27"}),
]


def rgba(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def figure(head, body, view, pal):
    rows = HEADS[head][view] + BODIES[body][view]
    assert len(rows) == H, (head, body, view, len(rows))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        assert len(r) == W, (head, body, view, y, len(r), r)
        for x, ch in enumerate(r):
            if ch != ".":
                im.putpixel((x, y), rgba(pal.get(ch) or SKIN[ch]))
    return im


def main():
    out = ROOT / "art/hero/candidates"
    out.mkdir(parents=True, exist_ok=True)
    figs = []
    for cid, name, head, body, colours in CANDIDATES:
        pal = dict(SKIN, **colours)
        f, b = figure(head, body, "front", pal), figure(head, body, "back", pal)
        pair = Image.new("RGBA", (W * 2, H), (0, 0, 0, 0))
        pair.alpha_composite(f, (0, 0))
        pair.alpha_composite(b, (W, 0))
        pair.save(out / f"{cid}.png")
        figs.append((cid, name, f, b))
    print("hero candidates ->", out.relative_to(ROOT), [c[0] for c in CANDIDATES])
    return figs


if __name__ == "__main__":
    main()
