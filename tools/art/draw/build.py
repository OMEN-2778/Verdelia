#!/usr/bin/env python3
"""Regenerate every hand-made sheet under art/ and the farm mock-up under docs/art/.

    python3 tools/art/draw/build.py
"""
import character
import objects
import scene
import terrain
from common import ROOT, save, upscale


def main():
    written = [
        save(terrain.base_sheet(), "tiles/terrain_base.png"),
        save(terrain.grass_over(), "tiles/grass_over.png"),
        save(terrain.dirt_over_water(), "tiles/dirt_over_water.png"),
        save(terrain.tilled_over(False), "tiles/tilled_dry_over.png"),
        save(terrain.tilled_over(True), "tiles/tilled_wet_over.png"),
        save(objects.sheet(), "sprites/props.png"),
        save(objects.tree(1), "sprites/tree.png"),
        save(objects.bush(), "sprites/bush.png"),
        save(character.front(), "sprites/protagonist_front.png"),
    ]
    mock = ROOT / "docs/art/farm-mockup.png"
    mock.parent.mkdir(parents=True, exist_ok=True)
    upscale(scene.render(scene.MAP), 4).save(mock)
    written.append(mock)
    for path in written:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
