#!/usr/bin/env python3
"""Fetches the Universal LPC Spritesheet Character Generator (a pinned commit) into
tools/art/lpc/.cache/ulpc, with only the spritesheets our characters use (the whole repository is
gigabytes), and installs its packages so export.mjs can run it.

Which sheets are needed is read from characters.json: each "type=Name_colour" in a character's hash
is looked up among the generator's sheet definitions and the folders its layers draw from for
that body type are checked out. Run it again after adding a character or changing an outfit.

    python3 tools/art/lpc/fetch.py
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE / ".cache" / "ulpc"
REPO = "https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator.git"
COMMIT = "58ce1aa479e4df32845a73a5d0afc221c3a893c2"
BASE = [
    "/*.md", "/*.csv", "/*.js", "/*.mjs", "/*.ts", "/LICENSE*", "/package.json", "/package-lock.json",
    "/index.html", "/vite*", "/vite/", "/tsconfig*", "/styles/", "/scripts/", "/tools/", "/sources/",
    "/sheet_definitions/", "/palette_definitions/",
    # the page starts on a default character before it reads ours
    "/spritesheets/body/bodies/", "/spritesheets/head/heads/human/",
]


def git(*args):
    subprocess.run(["git", "-C", str(DEST), *args], check=True)


def definitions():
    defs = []
    for f in (DEST / "sheet_definitions").rglob("*.json"):
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(d, dict) and "layer_1" in d and d.get("type_name"):
            defs.append(d)
    return defs


def sheet_folders(hash_, defs):
    """The spritesheet folders a character's hash needs."""
    pairs = dict(p.split("=", 1) for p in hash_.split("&"))
    body = pairs.pop("sex", "male")
    out = set()
    for key, value in pairs.items():
        match = None
        for d in defs:
            name = d["name"].replace(" ", "_")
            if d["type_name"] == key and value.startswith(name + "_") and (not match or len(name) > len(match["name"])):
                match = d
        if match is None:
            continue  # a colour for another item's part (the handle of a tool, the eyes)
        for k, layer in match.items():
            if k.startswith("layer_") and layer.get(body):
                out.add("/spritesheets/" + layer[body].strip("/") + "/")
    return out


def main():
    if not DEST.exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO, str(DEST)], check=True)
        git("sparse-checkout", "init", "--no-cone")
        git("sparse-checkout", "set", "--no-cone", *BASE)
        git("checkout", COMMIT)
    specs = json.loads((HERE / "characters.json").read_text())
    defs = definitions()
    folders = set()
    for cid, spec in specs.items():
        folders |= sheet_folders(spec["hash"], defs)
    # the watering can's own sheets (build.py colours its thrust frames itself)
    folders.add("/spritesheets/tools/watering_can/")
    git("sparse-checkout", "add", *sorted(folders))
    if not (DEST / "node_modules").exists():
        subprocess.run(["npm", "ci", "--ignore-scripts"], cwd=DEST, check=True)
    print("LPC generator ready in", DEST.relative_to(HERE.parents[2]), f"({len(folders)} sheet folders)")


if __name__ == "__main__":
    main()
